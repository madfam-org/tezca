"""
Management command to ingest municipal laws into database.
Creates Law and LawVersion records from municipal_laws_metadata.json.

Usage:
    python manage.py ingest_municipal_laws --all
    python manage.py ingest_municipal_laws --municipality cdmx
    python manage.py ingest_municipal_laws --all --dry-run
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.api.models import Law, LawVersion
from apps.api.utils.paths import resolve_data_path_or_none, resolve_metadata_file


class Command(BaseCommand):
    help = "Ingest municipal laws into database from consolidated metadata"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--all", action="store_true", help="Ingest all municipal laws"
        )
        group.add_argument(
            "--municipality", type=str, help="Ingest specific municipality"
        )

        parser.add_argument(
            "--dry-run", action="store_true", help="Dry run (no database writes)"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size for transactions (default: 100)",
        )
        parser.add_argument("--limit", type=int, help="Limit number of laws to process")

    def create_law_and_version(self, metadata, dry_run=False):
        """Create Law and LawVersion records from metadata."""
        try:
            official_id = metadata["official_id"]
            law_name = metadata["law_name"]
            category = metadata.get("category", "Otros")
            tier = "municipal"
            state = metadata.get("state", "")
            municipality = metadata.get("municipality", "")
            publication_date = metadata.get("publication_date")
            text_file = metadata.get("text_file")

            if dry_run:
                return {
                    "success": True,
                    "official_id": official_id,
                    "action": "dry_run",
                    "law_name": law_name,
                }

            # Determine best file path for xml_file_path:
            # Prefer AKN XML if it exists, fall back to raw text
            akn_file = metadata.get("akn_file_path", "")
            akn_path = resolve_data_path_or_none(akn_file) if akn_file else None
            stored_path = akn_file if akn_path else (text_file or "")

            # Check if law already exists
            existing_law = Law.objects.filter(official_id=official_id).first()

            if existing_law:
                existing_law.name = law_name
                existing_law.tier = tier
                existing_law.category = category
                existing_law.state = state
                existing_law.municipality = municipality
                existing_law.source_url = metadata.get("url", "") or ""
                existing_law.save()
                law = existing_law
                action = "updated"
            else:
                law = Law.objects.create(
                    official_id=official_id,
                    name=law_name,
                    tier=tier,
                    category=category,
                    state=state,
                    municipality=municipality,
                    source_url=metadata.get("url", "") or "",
                )
                action = "created"

            pub_date = publication_date if publication_date else "2023-01-01"

            version = LawVersion.objects.create(
                law=law,
                publication_date=pub_date,
                dof_url=metadata.get("url", ""),
                xml_file_path=stored_path,
            )

            return {
                "success": True,
                "official_id": official_id,
                "action": action,
                "law_id": law.id,
                "version_id": version.id,
                "law_name": law_name,
            }

        except Exception as e:
            return {
                "success": False,
                "official_id": metadata.get("official_id", "unknown"),
                "error": str(e),
            }

    def handle(self, *args, **options):
        self.stdout.write("🏘️  Loading municipal law metadata...")
        metadata_file = resolve_metadata_file("municipal_laws_metadata.json")

        if not metadata_file.exists():
            self.stdout.write(
                self.style.ERROR(f"Metadata file not found: {metadata_file}")
            )
            self.stdout.write("   Run consolidate_municipal_metadata.py first!")
            return

        metadata = json.loads(metadata_file.read_text())
        all_laws = metadata.get("laws", [])

        # Filter by municipality if requested
        if options["municipality"]:
            muni = options["municipality"].lower()
            all_laws = [
                law
                for law in all_laws
                if muni in (law.get("municipality") or "").lower()
                or muni in (law.get("state") or "").lower()
            ]
            selection_desc = f"municipality: {options['municipality']}"
        else:
            selection_desc = "all municipalities"

        if options["limit"]:
            all_laws = all_laws[: options["limit"]]

        if not all_laws:
            self.stdout.write(self.style.ERROR(f"No laws found for {selection_desc}"))
            return

        self.stdout.write("=" * 70)
        self.stdout.write("MUNICIPAL INGESTION PLAN")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Selection: {selection_desc}")
        self.stdout.write(f"Laws to ingest: {len(all_laws):,}")
        self.stdout.write(f"Batch size: {options['batch_size']}")
        self.stdout.write(f"Dry run: {options['dry_run']}")
        self.stdout.write("=" * 70)

        self.stdout.write("🚀 Starting municipal ingestion...\n")

        results = []
        batch_count = 0

        for i in range(0, len(all_laws), options["batch_size"]):
            batch = all_laws[i : i + options["batch_size"]]
            batch_count += 1

            if not options["dry_run"]:
                with transaction.atomic():
                    for law_metadata in batch:
                        result = self.create_law_and_version(
                            law_metadata, options["dry_run"]
                        )
                        results.append(result)
            else:
                for law_metadata in batch:
                    result = self.create_law_and_version(
                        law_metadata, options["dry_run"]
                    )
                    results.append(result)

            processed = len(results)
            success_so_far = sum(1 for r in results if r["success"])
            self.stdout.write(
                f"  Batch {batch_count}: {processed:,}/{len(all_laws):,} "
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
        self.stdout.write("MUNICIPAL INGESTION SUMMARY")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Total laws:     {len(results):,}")
        self.stdout.write(
            f"Success:        {success_count:,} "
            f"({success_count/len(results)*100:.1f}%)"
            if results
            else ""
        )
        self.stdout.write(f"Failed:         {len(failed):,}")

        if action_counts:
            self.stdout.write("\nActions:")
            for action, count in sorted(action_counts.items()):
                self.stdout.write(f"  {action:15} {count:5,}")

        if failed and len(failed) <= 20:
            self.stdout.write(f"\n❌ Failed laws ({len(failed)}):")
            for result in failed[:20]:
                self.stdout.write(f"  - {result['official_id']}: {result['error']}")
        elif failed:
            self.stdout.write(f"\n❌ {len(failed)} laws failed")

        self.stdout.write("=" * 70)

        if not options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Ingested {success_count:,} municipal laws!")
            )
