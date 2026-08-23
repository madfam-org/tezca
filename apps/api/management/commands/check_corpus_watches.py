"""
On-demand corpus-watch check: scan DOF editions for yearly-reissued
instruments (SEP calendario escolar, JCF Reglas de Operación, …).

The same scan runs automatically inside ``check_dof_daily`` every day. This
command exists to run it for an *arbitrary* date or window — the intended use
is back-checking the month a yearly acuerdo was expected but not yet ingested
(e.g. "did the 2027-2028 SEP calendario land in June/July 2027?"), so the
year-over-year loop has a manual trigger as well as the daily one.

Detection only: a hit tells an operator a new edition of a pinned instrument
was published and what to do (see each watch's ``action``). It never mutates
the corpus — pinning a DOF codigo requires the identity-verification step the
fetchers enforce, which is a human decision.

Usage::

    python manage.py check_corpus_watches --date 2027-07-15
    python manage.py check_corpus_watches --from 2027-05-01 --to 2027-07-31
    python manage.py check_corpus_watches --watch sep_calendario_escolar --json
"""

import datetime
import json

from django.core.management.base import BaseCommand, CommandError

from apps.scraper.federal.dof_daily import DofScraper
from apps.scraper.scheduling.corpus_watch import (
    CORPUS_WATCHES,
    CORPUS_WATCHES_BY_KEY,
    scan_entries,
)


class Command(BaseCommand):
    help = (
        "Scan DOF editions for yearly-reissued corpus instruments "
        "(SEP calendario, JCF ROP). Detection only."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Single date to check (YYYY-MM-DD). Defaults to today.",
        )
        parser.add_argument(
            "--from",
            type=str,
            default=None,
            dest="date_from",
            help="Start of an inclusive date range (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--to",
            type=str,
            default=None,
            dest="date_to",
            help="End of an inclusive date range (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--watch",
            type=str,
            default=None,
            help=(
                "Only report hits for this watch key "
                f"({', '.join(w.key for w in CORPUS_WATCHES)})."
            ),
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="output_json",
            help="Output structured JSON.",
        )

    def handle(self, *args, **options):
        dates = self._resolve_dates(options)
        watch_key = options.get("watch")
        if watch_key and watch_key not in CORPUS_WATCHES_BY_KEY:
            raise CommandError(
                f"Unknown watch {watch_key!r}. Known: "
                f"{', '.join(CORPUS_WATCHES_BY_KEY)}"
            )

        all_hits = []
        for day in dates:
            scraper = DofScraper(date=day)
            entries = scraper.fetch_daily_edition()
            for hit in scan_entries(entries):
                if watch_key and hit.watch_key != watch_key:
                    continue
                record = hit.to_dict()
                record["date"] = day.isoformat()
                all_hits.append(record)

        if options["output_json"]:
            self.stdout.write(
                json.dumps(
                    {
                        "dates_checked": [d.isoformat() for d in dates],
                        "watch": watch_key,
                        "hits": all_hits,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return

        window = (
            dates[0].isoformat()
            if len(dates) == 1
            else f"{dates[0].isoformat()}..{dates[-1].isoformat()}"
        )
        if not all_hits:
            self.stdout.write(
                self.style.SUCCESS(
                    f"No corpus-watch hits over {window} "
                    f"({len(dates)} DOF edition(s) checked)."
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(f"{len(all_hits)} corpus-watch hit(s) over {window}:")
        )
        for hit in all_hits:
            self.stdout.write(
                f"\n  [{hit['watch_key']}] {hit['date']}\n"
                f"    {hit['title']}\n"
                f"    {hit['url']}\n"
                f"    → {hit['action']}"
            )

    def _resolve_dates(self, options):
        """Return the list of dates to check (single, range, or today)."""
        date_from = options.get("date_from")
        date_to = options.get("date_to")
        single = options.get("date")

        if (date_from or date_to) and single:
            raise CommandError("Use either --date or --from/--to, not both.")

        if date_from or date_to:
            if not (date_from and date_to):
                raise CommandError("--from and --to must be given together.")
            start = _parse_date(date_from)
            end = _parse_date(date_to)
            if end < start:
                raise CommandError("--to must not be before --from.")
            span = (end - start).days
            if span > 366:
                raise CommandError("Range too large (max 366 days).")
            return [start + datetime.timedelta(days=i) for i in range(span + 1)]

        return [_parse_date(single) if single else datetime.date.today()]


def _parse_date(value: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise CommandError(f"Invalid date {value!r} (expected YYYY-MM-DD)") from exc
