"""
Management command to ingest international treaties into database.
Creates Law and LawVersion records from discovered_treaties.json.

Usage:
    python manage.py ingest_treaties --all
    python manage.py ingest_treaties --all --dry-run
    python manage.py ingest_treaties --all --limit 50
"""

import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.api.models import Law, LawVersion

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
TREATIES_PATH = PROJECT_ROOT / "data" / "treaties" / "discovered_treaties.json"


def _slugify(text: str) -> str:
    """Create a safe slug from treaty name."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    return text[:150]


class Command(BaseCommand):
    help = "Ingest international treaties into database from discovered_treaties.json"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--all", action="store_true", help="Ingest all treaties")

        parser.add_argument(
            "--dry-run", action="store_true", help="Dry run (no database writes)"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size for transactions (default: 100)",
        )
        parser.add_argument(
            "--limit", type=int, help="Limit number of treaties to process"
        )
        parser.add_argument(
            "--catalog",
            type=str,
            default=str(TREATIES_PATH),
            help=f"Path to discovered_treaties.json (default: {TREATIES_PATH})",
        )

    def create_law_and_version(self, treaty, dry_run=False):
        """Create Law and LawVersion records from a treaty entry."""
        try:
            # Build official_id
            treaty_id = treaty.get("id", "")
            if treaty_id:
                official_id = f"treaty_{treaty_id}"
            else:
                official_id = f"treaty_{_slugify(treaty.get('name', 'unknown'))}"
            official_id = official_id[:200]

            law_name = treaty.get("name", "")[:500]
            if not law_name:
                return {
                    "success": False,
                    "official_id": official_id,
                    "error": "No treaty name",
                }

            treaty_type = treaty.get("treaty_type", "unknown")
            source_url = (treaty.get("url", "") or "")[:500]
            date_signed = treaty.get("date_signed", "")
            date_ratified = treaty.get("date_ratified", "")

            if dry_run:
                return {
                    "success": True,
                    "official_id": official_id,
                    "action": "dry_run",
                    "law_name": law_name,
                }

            # Check if law already exists
            existing_law = Law.objects.filter(official_id=official_id).first()

            defaults = {
                "name": law_name,
                "tier": "federal",
                "law_type": "non_legislative",
                "category": treaty_type or "treaty",
                "source_url": source_url,
                "status": Law.Status.VIGENTE,
            }

            if existing_law:
                for key, value in defaults.items():
                    setattr(existing_law, key, value)
                existing_law.save()
                law = existing_law
                action = "updated"
            else:
                law = Law.objects.create(official_id=official_id, **defaults)
                action = "created"

            # Publication date: prefer date_ratified, then date_signed
            pub_date = None
            for date_str in [date_ratified, date_signed]:
                if date_str:
                    pub_date = parse_date(date_str)
                    if pub_date:
                        break
            if not pub_date:
                pub_date = parse_date("2020-01-01")

            version, v_created = LawVersion.objects.get_or_create(
                law=law,
                publication_date=pub_date,
                defaults={
                    "dof_url": source_url,
                    "xml_file_path": "",
                },
            )
            if not v_created:
                version.dof_url = source_url
                version.save()
                action = "updated"

            return {
                "success": True,
                "official_id": official_id,
                "action": action,
                "law_id": law.id,
                "version_id": version.id,
                "version_created": v_created,
                "law_name": law_name,
            }

        except Exception as e:
            return {
                "success": False,
                "official_id": treaty.get("id", "unknown"),
                "error": str(e),
            }

    def handle(self, *args, **options):
        catalog_path = Path(options["catalog"])

        self.stdout.write(f"Loading treaty catalog from {catalog_path}...")

        if not catalog_path.exists():
            self.stdout.write(self.style.ERROR(f"Catalog not found: {catalog_path}"))
            self.stdout.write("   Run the treaty scraper first!")
            return

        with open(catalog_path, "r", encoding="utf-8") as f:
            all_treaties = json.load(f)

        if not isinstance(all_treaties, list):
            self.stdout.write(
                self.style.ERROR("Expected a JSON array of treaty objects")
            )
            return

        if options["limit"]:
            all_treaties = all_treaties[: options["limit"]]

        if not all_treaties:
            self.stdout.write(self.style.ERROR("No treaties found in catalog"))
            return

        self.stdout.write("=" * 70)
        self.stdout.write("TREATY INGESTION PLAN")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Treaties to ingest: {len(all_treaties):,}")
        self.stdout.write(f"Batch size: {options['batch_size']}")
        self.stdout.write(f"Dry run: {options['dry_run']}")
        self.stdout.write("=" * 70)

        self.stdout.write("Starting treaty ingestion...\n")

        results = []
        batch_count = 0

        for i in range(0, len(all_treaties), options["batch_size"]):
            batch = all_treaties[i : i + options["batch_size"]]
            batch_count += 1

            if not options["dry_run"]:
                with transaction.atomic():
                    for treaty in batch:
                        result = self.create_law_and_version(treaty, options["dry_run"])
                        results.append(result)
            else:
                for treaty in batch:
                    result = self.create_law_and_version(treaty, options["dry_run"])
                    results.append(result)

            processed = len(results)
            success_so_far = sum(1 for r in results if r["success"])
            self.stdout.write(
                f"  Batch {batch_count}: {processed:,}/{len(all_treaties):,} "
                f"({success_so_far}/{processed} successful)"
            )

        # Summary
        success_count = sum(1 for r in results if r["success"])
        failed = [r for r in results if not r["success"]]

        action_counts = {}
        for r in results:
            if r["success"]:
                action = r.get("action", "unknown")
                action_counts[action] = action_counts.get(action, 0) + 1

        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write("TREATY INGESTION SUMMARY")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Total treaties:  {len(results):,}")
        self.stdout.write(
            f"Success:         {success_count:,} "
            f"({success_count/len(results)*100:.1f}%)"
            if results
            else ""
        )
        self.stdout.write(f"Failed:          {len(failed):,}")

        if action_counts:
            self.stdout.write("\nActions:")
            for action, count in sorted(action_counts.items()):
                self.stdout.write(f"  {action:15} {count:5,}")

        if failed and len(failed) <= 20:
            self.stdout.write(f"\nFailed treaties ({len(failed)}):")
            for result in failed[:20]:
                self.stdout.write(f"  - {result['official_id']}: {result['error']}")
        elif failed:
            self.stdout.write(f"\n{len(failed)} treaties failed")

        self.stdout.write("=" * 70)

        if not options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nIngested {success_count:,} international treaties!"
                )
            )
