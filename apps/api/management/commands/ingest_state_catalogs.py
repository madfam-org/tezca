"""
Ingest state congress scraper catalogs (apps/scraper/state/*.py output) into
Law records.

``run_state_scraper`` (apps/scraper/scheduling/tasks.py) writes a bare
catalog — ``name``/``url``/``state``/``tier``/``category``/``law_type`` —
to ``data/state_laws/<state_key>/catalog.json``. None of the 14 registered
state scrapers download law text (``scrape_law_content`` exists on the base
class but is never invoked by the scheduled task), so the rich
``state_laws_metadata.json`` format that ``ingest_state_laws`` expects
(``official_id``, ``text_file``, ``akn_file_path``, ``publication_date``)
never gets produced from this pipeline.

This command bridges the gap at the level the scrapers actually support:
it upserts one ``Law`` per discovered catalog entry directly from
``catalog.json``, with ``tier="state"`` and no ``LawVersion`` (there is no
law text to attach yet). This gets discovery into the DB so the row-growth
guard can see it; full-text ingestion remains a separate, future pipeline
that would need the scrapers to actually download and store law documents.

Usage::

    python manage.py ingest_state_catalogs --state guerrero
    python manage.py ingest_state_catalogs --all
    python manage.py ingest_state_catalogs --all --dry-run
"""

import json
import re
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.api.models import Law

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
STATE_LAWS_ROOT = PROJECT_ROOT / "data" / "state_laws"


def _strip_accents(text: str) -> str:
    """Remove diacritical marks from text."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _slugify(text: str) -> str:
    """Create a safe slug from a law name (mirrors ingest_conamer/ingest_treaties)."""
    text = _strip_accents(text.lower().strip())
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    return text[:150]


def build_official_id(state_key: str, entry: dict) -> str:
    """Build a stable official_id from the state key and law name/URL.

    Catalog entries have no upstream ID (unlike NOMs or treaties), so the
    slug is derived from the law name. Falls back to a slug of the URL if
    the name is missing, since ``name`` and ``url`` are both required by
    ``StateCongressScraper.validate_law_data``.
    """
    name = entry.get("name") or entry.get("url", "")
    return f"state_{state_key}_{_slugify(name)}"[:200]


class Command(BaseCommand):
    help = (
        "Ingest state congress scraper catalogs "
        "(data/state_laws/<state>/catalog.json) into Law records"
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--all", action="store_true", help="Ingest catalogs for every state"
        )
        group.add_argument(
            "--state", type=str, help="Ingest a single state (e.g. guerrero)"
        )

        parser.add_argument(
            "--dry-run", action="store_true", help="Show counts without writing to DB"
        )
        parser.add_argument(
            "--state-laws-root",
            type=str,
            default=str(STATE_LAWS_ROOT),
            help=f"Root directory containing per-state catalog.json files "
            f"(default: {STATE_LAWS_ROOT})",
        )

    def handle(self, *args, **options):
        state_laws_root = Path(options["state_laws_root"])

        if options["state"]:
            catalogs = [
                (options["state"], state_laws_root / options["state"] / "catalog.json")
            ]
        else:
            if not state_laws_root.exists():
                self.stdout.write(
                    self.style.ERROR(f"No state catalogs found under {state_laws_root}")
                )
                return
            catalogs = sorted(
                (path.parent.name, path)
                for path in state_laws_root.glob("*/catalog.json")
            )

        catalogs = [(key, path) for key, path in catalogs if path.exists()]
        if not catalogs:
            self.stdout.write(self.style.ERROR("No catalog.json files found to ingest"))
            return

        dry_run = options["dry_run"]
        total_created = 0
        total_updated = 0
        total_errors = 0
        total_entries = 0

        for state_key, catalog_path in catalogs:
            with catalog_path.open(encoding="utf-8") as fh:
                entries = json.load(fh)

            if not entries:
                self.stdout.write(f"{state_key}: catalog empty, skipping")
                continue

            total_entries += len(entries)
            self.stdout.write(
                f"{state_key}: {len(entries)} entries from {catalog_path}"
            )

            created = 0
            updated = 0
            errors = 0

            for entry in entries:
                official_id = build_official_id(state_key, entry)
                try:
                    with transaction.atomic():
                        result = self._upsert(state_key, entry, official_id, dry_run)
                    if result == "created":
                        created += 1
                    elif result == "updated":
                        updated += 1
                except Exception as exc:
                    errors += 1
                    self.stderr.write(self.style.ERROR(f"Failed {official_id}: {exc}"))

            prefix = "[DRY-RUN] " if dry_run else ""
            self.stdout.write(
                f"  {prefix}{state_key}: {created} created, {updated} updated, "
                f"{errors} errors"
            )
            total_created += created
            total_updated += updated
            total_errors += errors

        self.stdout.write("")
        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}State catalog ingest complete: {total_entries} entries, "
                f"{total_created} created, {total_updated} updated, "
                f"{total_errors} errors"
            )
        )

    def _upsert(
        self, state_key: str, entry: dict, official_id: str, dry_run: bool
    ) -> str:
        """Upsert a single catalog entry into Law. Returns "created" or "updated"."""
        if dry_run:
            return (
                "updated"
                if Law.objects.filter(official_id=official_id).exists()
                else "created"
            )

        law_name = (entry.get("name") or "")[:2000]
        state_name = entry.get("state") or state_key.replace("_", " ").title()
        source_url = (entry.get("url", "") or "")[:500]
        category = entry.get("category") or "Otro"

        # Base scraper law_type values (ley, codigo, decreto...) don't match
        # Law.LawType choices (legislative/non_legislative) — catalog entries
        # are always legislative-branch documents (laws, codes, decrees), so
        # normalize to the model's choice field instead of passing the
        # scraper's finer-grained classification straight through.
        defaults = {
            "name": law_name,
            "tier": "state",
            "category": category,
            "state": state_name,
            "source_url": source_url,
            "law_type": Law.LawType.LEGISLATIVE,
        }

        _, created = Law.objects.update_or_create(
            official_id=official_id,
            defaults=defaults,
        )
        return "created" if created else "updated"
