"""
Ingest the RMF catalog produced by ``apps/scraper/federal/rmf_scraper.py``
into Law + LawVersion rows.

This is the SAT-side analogue to ``ingest_non_legislative_laws.py``, but for
federal regulations rather than state ones. It walks ``data/rmf/catalog.json``
(or whatever path is given), creates one ``Law`` per RMF artifact (annual
RMF, quarterly modification, or annex), and tags each with
``law_type="non_legislative"``, ``category="resolución_miscelánea_fiscal"``,
``domains=["fiscal"]`` so Karafiel's compliance webhook filter
(``domain_filter: ["fiscal"]``) sees these events.

Usage::

    python manage.py ingest_rmf --catalog data/rmf/catalog.json
    python manage.py ingest_rmf --catalog data/rmf/catalog.json --dry-run

After running, ``index_laws`` (existing command) takes over the ES side.
"""

import datetime
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.api.models import Law, LawVersion
from apps.scraper.federal.rmf_scraper import RMF_CATEGORY, RMF_DOMAINS


class Command(BaseCommand):
    help = (
        "Ingest RMF catalog (apps/scraper/federal/rmf_scraper output) into Law records"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--catalog",
            type=str,
            default="data/rmf/catalog.json",
            help="Path to catalog.json produced by RmfScraper (default: data/rmf/catalog.json)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created/updated without writing to the DB",
        )

    def handle(self, *args, **options):
        catalog_path = Path(options["catalog"])
        if not catalog_path.exists():
            self.stderr.write(self.style.ERROR(f"Catalog not found: {catalog_path}"))
            return

        with catalog_path.open(encoding="utf-8") as fh:
            documents = json.load(fh)

        if not documents:
            self.stdout.write(
                self.style.WARNING("Catalog is empty — nothing to ingest")
            )
            return

        self.stdout.write(f"Loaded {len(documents)} RMF documents from {catalog_path}")

        created = 0
        updated = 0
        errors = 0
        dry_run = options["dry_run"]

        for doc in documents:
            try:
                with transaction.atomic():
                    result = self._upsert(doc, dry_run=dry_run)
                if result == "created":
                    created += 1
                elif result == "updated":
                    updated += 1
            except Exception as exc:
                errors += 1
                self.stderr.write(
                    self.style.ERROR(f"Failed {doc.get('official_id', '?')}: {exc}")
                )

        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}RMF ingest complete: {created} created, {updated} updated, "
                f"{errors} errors"
            )
        )

    def _upsert(self, doc: dict, dry_run: bool) -> str:
        """Upsert a single RmfDocument dict into Law + LawVersion.

        Returns "created" or "updated" so the caller can tally.
        """
        official_id = doc["official_id"]
        name = doc["name"]
        url = doc["url"]
        document_type = doc["document_type"]
        year = int(doc["year"])
        category = doc.get("category", RMF_CATEGORY)
        domains = doc.get("domains", list(RMF_DOMAINS))

        publication_date = doc.get("publication_date")
        # When SAT didn't expose a publication date, fall back to Jan 1 of
        # the fiscal year — RMF rules formally take effect on Jan 1 absent
        # a more specific date. Better than `None` because LawVersion
        # requires a date.
        if not publication_date:
            publication_date = f"{year}-01-01"

        if dry_run:
            return (
                "updated"
                if Law.objects.filter(official_id=official_id).exists()
                else "created"
            )

        defaults = {
            "name": name,
            "tier": "federal",
            "category": category,
            "domains": domains,
            "law_type": "non_legislative",
            "source_url": url,
            "last_verified": datetime.datetime.now(datetime.timezone.utc),
            # SAT publishes the RMF text on portal pages; we don't currently
            # parse a rich short_name, but `document_type` gives operators
            # a quick filter.
            "short_name": _short_name(document_type, year, doc),
        }

        law, created = Law.objects.update_or_create(
            official_id=official_id,
            defaults=defaults,
        )
        action = "created" if created else "updated"

        # Always upsert a LawVersion for this publication date
        LawVersion.objects.update_or_create(
            law=law,
            publication_date=publication_date,
            defaults={
                "dof_url": url,
            },
        )

        return action


def _short_name(document_type: str, year: int, doc: dict) -> str:
    """Friendly short_name for the admin UI / search snippets."""
    if document_type == "annex":
        return f"Anexo {doc.get('annex_number', '?')} RMF {year}"
    if document_type == "modification":
        return f"{doc.get('modification_number', '?')}ª Mod. RMF {year}"
    return f"RMF {year}"
