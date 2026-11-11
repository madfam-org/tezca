"""
Report — and, for names, repair — ingestion debris in the stored corpus.

Fixing the scraper and the parser does not clean what is already stored. This
command measures three symptoms and repairs the one that lives in the
database:

1. **Law names carrying Diputados-catalog debris** — the index cell's DOF date
   and status marker stored inside ``Law.name``
   ("… \\t DOF 20/03/2025 \\t Nueva reforma"). REPAIRED here with ``--apply``.
2. **Article ids ending in ``-dupN``** — transitorios the legacy XML carries
   as ``Artículo N`` nodes. Reported only: the repair is a re-index, which
   resolves them to ``T-N`` / ``T-RK-N`` and prunes the stale docs.
3. **Article text containing the Cámara de Diputados page header**
   («Secretaría de Servicios Parlamentarios»). Reported only: a re-index
   strips it from the served text; a re-ingest also cleans the stored XML.

Dry run by default: without ``--apply`` nothing is written anywhere. The
Elasticsearch part only ever reads.

Usage:
    python manage.py clean_ingestion_debris
    python manage.py clean_ingestion_debris --law-id lfpdppp
    python manage.py clean_ingestion_debris --law-id lfpdppp --apply
    python manage.py clean_ingestion_debris --all-names --apply
    python manage.py clean_ingestion_debris --skip-es --output report.json

Follow-up for the two reported symptoms (see
docs/runbooks/lfpdppp-transitorio-reindex.md): ``dataops.reindex_law`` per
law, or ``dataops.ingest_law`` to re-download and re-parse it.
"""

import json

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.api.models import Law
from apps.scraper.utils.law_name import (
    has_catalog_debris,
    normalize_law_name,
    normalize_short_name,
)

INDEX_ARTICLES = "articles"
PAGE_HEADER_PHRASE = "Secretaría de Servicios Parlamentarios"
DUP_ID_REGEXP = ".*-dup[0-9]+"
SAMPLE_SIZE = 20


def name_fix(law):
    """``(name, short_name)`` the law should have, or ``None`` if it is clean."""
    if not has_catalog_debris(law.name):
        return None
    return (
        normalize_law_name(law.name),
        normalize_short_name(law.short_name, law.name),
    )


def laws_with_symptom_query(clause, sample_size=SAMPLE_SIZE):
    """ES body counting the distinct laws whose articles match ``clause``."""
    return {
        "size": 0,
        "track_total_hits": True,
        "query": clause,
        "aggs": {
            "laws": {"cardinality": {"field": "law_id", "precision_threshold": 40000}},
            "sample": {"terms": {"field": "law_id", "size": sample_size}},
        },
    }


DUP_ID_CLAUSE = {"regexp": {"article": {"value": DUP_ID_REGEXP}}}
PAGE_HEADER_CLAUSE = {"match_phrase": {"text": PAGE_HEADER_PHRASE}}


class Command(BaseCommand):
    help = (
        "Report laws with catalog debris in the name, -dupN article ids or "
        "Diputados page furniture in article text; repair names with --apply"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--law-id",
            action="append",
            default=[],
            help="official_id to repair (repeatable). The report always covers "
            "the whole corpus.",
        )
        parser.add_argument(
            "--all-names",
            action="store_true",
            help="Repair every law whose name carries catalog debris.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write the name repairs. Without it nothing is written.",
        )
        parser.add_argument(
            "--skip-es",
            action="store_true",
            help="Skip the Elasticsearch part of the report.",
        )
        parser.add_argument(
            "--output", type=str, default=None, help="Write the report as JSON."
        )

    def handle(self, *args, **options):
        law_ids = [i.strip() for i in options["law_id"] if i and i.strip()]
        apply_changes = options["apply"]
        if apply_changes and not (law_ids or options["all_names"]):
            raise CommandError("--apply needs --law-id <id> or --all-names")
        if law_ids and options["all_names"]:
            raise CommandError("use --law-id or --all-names, not both")

        report = {"dry_run": not apply_changes}
        report["names"] = self._report_names()
        report["elasticsearch"] = (
            {"skipped": True} if options["skip_es"] else self._report_es()
        )
        report["repaired"] = self._repair_names(
            law_ids, options["all_names"], apply_changes
        )

        self._print(report, law_ids)
        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as handle:
                json.dump(report, handle, ensure_ascii=False, indent=2)
            self.stdout.write(f"Report written to {options['output']}")

    # ── report ───────────────────────────────────────────────────────────────

    def _report_names(self):
        """Laws whose name has a tab or «Nueva reforma», and those repairable."""
        suspects = Law.objects.filter(
            Q(name__contains="\t") | Q(name__icontains="Nueva reforma")
        ).only("official_id", "name", "short_name")
        suspect_ids, repairable_ids = [], []
        for law in suspects.iterator():
            suspect_ids.append(law.official_id)
            if name_fix(law):
                repairable_ids.append(law.official_id)
        return {
            "with_tab_or_marker": len(suspect_ids),
            "repairable": len(repairable_ids),
            "sample": sorted(repairable_ids)[:SAMPLE_SIZE],
            # A marker with no cell layout left ("… Nueva reforma" after the
            # tabs were collapsed elsewhere) is not provably debris; listed so
            # a person can look.
            "not_repaired": sorted(set(suspect_ids) - set(repairable_ids)),
        }

    def _report_es(self):
        try:
            from apps.api.config import es_client

            if not es_client.ping():
                return {"error": "Elasticsearch unreachable"}
            out = {}
            for key, clause in (
                ("dup_article_ids", DUP_ID_CLAUSE),
                ("page_furniture", PAGE_HEADER_CLAUSE),
            ):
                res = es_client.search(
                    index=INDEX_ARTICLES, **laws_with_symptom_query(clause)
                )
                aggs = res["aggregations"]
                out[key] = {
                    "articles": res["hits"]["total"]["value"],
                    "laws": aggs["laws"]["value"],
                    "sample": [
                        {"law_id": b["key"], "articles": b["doc_count"]}
                        for b in aggs["sample"]["buckets"]
                    ],
                }
            return out
        except Exception as exc:  # noqa: BLE001 — the report must not abort
            return {"error": str(exc)}

    # ── repair ───────────────────────────────────────────────────────────────

    def _repair_names(self, law_ids, all_names, apply_changes):
        if law_ids:
            laws = list(Law.objects.filter(official_id__in=law_ids))
            missing = sorted(set(law_ids) - {law.official_id for law in laws})
            if missing:
                raise CommandError(f"unknown law id(s): {', '.join(missing)}")
        elif all_names:
            laws = Law.objects.filter(
                Q(name__contains="\t") | Q(name__icontains="Nueva reforma")
            ).iterator()
        else:
            return []

        changes = []
        for law in laws:
            fix = name_fix(law)
            if fix is None:
                continue
            name, short_name = fix
            changes.append(
                {
                    "law_id": law.official_id,
                    "from": law.name,
                    "to": name,
                    "short_name": short_name,
                }
            )
            if apply_changes:
                law.name = name
                law.short_name = short_name
                law.save(update_fields=["name", "short_name", "updated_at"])
        return changes

    # ── output ───────────────────────────────────────────────────────────────

    def _print(self, report, law_ids):
        names = report["names"]
        self.stdout.write(self.style.MIGRATE_HEADING("Law names (database)"))
        self.stdout.write(
            f"  with a tab or «Nueva reforma»: {names['with_tab_or_marker']}"
            f" | repairable: {names['repairable']}"
        )
        if names["not_repaired"]:
            self.stdout.write(
                f"  left for review: {', '.join(names['not_repaired'][:SAMPLE_SIZE])}"
            )

        es = report["elasticsearch"]
        self.stdout.write(self.style.MIGRATE_HEADING("Articles (Elasticsearch)"))
        if es.get("skipped"):
            self.stdout.write("  skipped (--skip-es)")
        elif es.get("error"):
            self.stdout.write(self.style.WARNING(f"  not measured: {es['error']}"))
        else:
            for key, label in (
                ("dup_article_ids", "article ids ending in -dupN"),
                ("page_furniture", f"text containing «{PAGE_HEADER_PHRASE}»"),
            ):
                self.stdout.write(
                    f"  {label}: {es[key]['laws']} laws, {es[key]['articles']} articles"
                )
                others = [s for s in es[key]["sample"] if s["law_id"] not in law_ids]
                if others:
                    self.stdout.write(
                        "    most affected: "
                        + ", ".join(f"{s['law_id']} ({s['articles']})" for s in others)
                    )

        verb = "Renamed" if not report["dry_run"] else "Would rename"
        self.stdout.write(self.style.MIGRATE_HEADING("Name repairs"))
        if not report["repaired"]:
            self.stdout.write("  none selected (use --law-id or --all-names)")
        for change in report["repaired"][:SAMPLE_SIZE]:
            self.stdout.write(f"  {verb} {change['law_id']}: {change['to']!r}")
        if len(report["repaired"]) > SAMPLE_SIZE:
            self.stdout.write(f"  … and {len(report['repaired']) - SAMPLE_SIZE} more")
        if report["dry_run"]:
            self.stdout.write(
                self.style.WARNING("Dry run: nothing written. Add --apply.")
            )
        elif report["repaired"]:
            self.stdout.write(
                "Names are also stored in Elasticsearch: re-index the renamed "
                "laws (dataops.reindex_law) so search shows them."
            )
