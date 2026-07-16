"""
Ingest the NOM catalog produced by ``apps/scraper/federal/nom_scraper.py``
into Law + LawVersion rows.

This is the management-command counterpart to
``scripts/ingestion/ingest_noms.py`` (which additionally downloads and
OCRs PDFs). This command only walks the discovered-NOM catalog written by
``NomScraper.run()`` — ``data/noms/discovered_noms.json`` by default — and
upserts one ``Law`` per NOM entry, tagged ``law_type="non_legislative"``
and ``category="norma_oficial_mexicana"`` so NOMs are distinguishable from
CONAMER's generic ``"norma"`` regulation-type bucket.

Mapping logic (official_id construction, status mapping, date fallback) is
ported from the standalone script so both stay in sync; the standalone
script is left untouched for its download/OCR responsibilities.

Usage::

    python manage.py ingest_noms
    python manage.py ingest_noms --catalog data/noms/discovered_noms.json
    python manage.py ingest_noms --dry-run
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.api.models import Law, LawVersion

# Distinguishes NOM entries from CONAMER's generic "norma" regulation_type
# bucket (see apps/api/management/commands/ingest_conamer.py _CATEGORY_MAP)
# and from RMF's "resolución_miscelánea_fiscal". No prior NOM-specific
# category constant exists in the codebase (checked constants.py, models.py,
# nom_scraper.py, and the standalone ingest_noms.py script, which falls back
# to a bare "norma_oficial").
NOM_CATEGORY = "norma_oficial_mexicana"

DEFAULT_CATALOG = Path("data") / "noms" / "discovered_noms.json"
DEFAULT_PUB_DATE = "2020-01-01"

_STATUS_MAP = {
    "vigente": Law.Status.VIGENTE,
    "abrogada": Law.Status.ABROGADA,
    "derogada": Law.Status.DEROGADA,
}


def build_official_id(nom: dict) -> str:
    """Build the official_id for a NOM entry (mirrors the standalone script)."""
    nom_number = nom.get("nom_number", "")
    if nom_number:
        return f"nom_{nom_number}"
    return f"nom_{nom.get('id', 'unknown')}"


class Command(BaseCommand):
    help = (
        "Ingest NOM catalog (apps/scraper/federal/nom_scraper output) into Law records"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--catalog",
            type=str,
            default=str(DEFAULT_CATALOG),
            help=f"Path to discovered_noms.json (default: {DEFAULT_CATALOG})",
        )
        parser.add_argument(
            "--dir",
            type=str,
            default=None,
            help=(
                "Directory containing discovered_noms.json — alternative to "
                "--catalog for consistency with sister commands that accept "
                "a directory."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created/updated without writing to the DB",
        )

    def handle(self, *args, **options):
        if options.get("dir"):
            catalog_path = Path(options["dir"]) / "discovered_noms.json"
        else:
            catalog_path = Path(options["catalog"])

        if not catalog_path.exists():
            self.stderr.write(self.style.ERROR(f"Catalog not found: {catalog_path}"))
            return

        with catalog_path.open(encoding="utf-8") as fh:
            noms = json.load(fh)

        if not noms:
            self.stdout.write(
                self.style.WARNING("Catalog is empty — nothing to ingest")
            )
            return

        self.stdout.write(f"Loaded {len(noms)} NOMs from {catalog_path}")

        created = 0
        updated = 0
        errors = 0
        dry_run = options["dry_run"]

        for nom in noms:
            official_id = build_official_id(nom)[:200]
            try:
                with transaction.atomic():
                    result = self._upsert(nom, official_id, dry_run=dry_run)
                if result == "created":
                    created += 1
                elif result == "updated":
                    updated += 1
            except Exception as exc:
                errors += 1
                self.stderr.write(self.style.ERROR(f"Failed {official_id}: {exc}"))

        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}NOM ingest complete: {created} created, {updated} updated, "
                f"{errors} errors"
            )
        )

    def _upsert(self, nom: dict, official_id: str, dry_run: bool) -> str:
        """Upsert a single NOM dict into Law + LawVersion.

        Returns "created" or "updated" so the caller can tally.
        """
        if dry_run:
            return (
                "updated"
                if Law.objects.filter(official_id=official_id).exists()
                else "created"
            )

        law_name = nom.get("name", "") or nom.get("nom_number", official_id)
        nom_number = nom.get("nom_number", "")
        source_url = (nom.get("url", "") or "")[:500]
        status = _STATUS_MAP.get(nom.get("status", "vigente"), Law.Status.UNKNOWN)

        defaults = {
            "name": law_name[:500],
            "short_name": nom_number[:200] if nom_number else law_name[:200],
            "category": NOM_CATEGORY,
            "tier": "federal",
            "law_type": "non_legislative",
            "source_url": source_url,
            "status": status,
        }

        law, created = Law.objects.update_or_create(
            official_id=official_id,
            defaults=defaults,
        )
        action = "created" if created else "updated"

        pub_date_str = nom.get("date_published", "")
        pub_date = parse_date(pub_date_str) if pub_date_str else None
        if not pub_date:
            pub_date = parse_date(DEFAULT_PUB_DATE)

        LawVersion.objects.get_or_create(
            law=law,
            publication_date=pub_date,
            defaults={"dof_url": source_url},
        )

        return action
