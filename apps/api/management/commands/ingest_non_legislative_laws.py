"""
Management command to ingest non-legislative state laws into database.
Creates Law and LawVersion records from OJN Poderes 1/3/4 metadata.

These are state-level executive, judicial, and autonomous body regulations
scraped by bulk_non_legislative_scraper.py.

Usage:
    # Ingest all non-legislative laws
    python apps/manage.py ingest_non_legislative_laws --all

    # Ingest specific state
    python apps/manage.py ingest_non_legislative_laws --state colima

    # Dry run
    python apps/manage.py ingest_non_legislative_laws --all --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.api.models import Law, LawVersion
from apps.api.utils.paths import data_exists, read_data_content, read_metadata_json


class Command(BaseCommand):
    help = "Ingest non-legislative state laws (OJN Poderes 1/3/4) into database"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--all", action="store_true", help="Ingest all non-legislative laws"
        )
        group.add_argument("--state", type=str, help="Ingest specific state")

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
            "--limit", type=int, help="Limit number of laws to process (for testing)"
        )

    def create_law_and_version(self, metadata, dry_run=False):
        """Create Law and LawVersion records from metadata."""
        try:
            official_id = metadata["official_id"]
            law_name = metadata["law_name"]
            category = metadata.get("category", "Otros")
            tier = metadata.get("tier", "state")
            state = metadata.get("state", "Unknown")
            publication_date = metadata.get("publication_date")
            text_file = metadata.get("text_file")

            # Read law text (local filesystem or R2)
            text_content = read_data_content(text_file) if text_file else None
            if not text_content:
                return {
                    "success": False,
                    "official_id": official_id,
                    "error": f"Text file not found: {text_file}",
                }

            if dry_run:
                return {
                    "success": True,
                    "official_id": official_id,
                    "action": "dry_run",
                    "law_name": law_name,
                    "category": category,
                }

            # Determine best file path for xml_file_path
            akn_file = metadata.get("akn_file_path", "")
            akn_found = data_exists(akn_file) if akn_file else False
            stored_path = akn_file if akn_found else (text_file or "")

            # Check if law already exists
            existing_law = Law.objects.filter(official_id=official_id).first()

            if existing_law:
                existing_law.name = law_name
                existing_law.tier = tier
                existing_law.category = category
                existing_law.state = state
                existing_law.law_type = "non_legislative"
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
                    law_type="non_legislative",
                    source_url=metadata.get("url", "") or "",
                )
                action = "created"

            # Create or update law version
            pub_date = publication_date if publication_date else "2023-01-01"

            version, v_created = LawVersion.objects.get_or_create(
                law=law,
                publication_date=pub_date,
                defaults={
                    "dof_url": metadata.get("url", ""),
                    "xml_file_path": stored_path,
                },
            )
            if not v_created:
                version.dof_url = metadata.get("url", "")
                version.xml_file_path = stored_path
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
                "category": category,
                "text_length": len(text_content),
            }

        except Exception as e:
            return {
                "success": False,
                "official_id": metadata.get("official_id", "unknown"),
                "error": str(e),
            }

    def handle(self, *args, **options):
        self.stdout.write("Loading non-legislative state law metadata...")
        metadata = read_metadata_json("state_laws_non_legislative_metadata.json")

        if not metadata:
            self.stdout.write(
                self.style.ERROR(
                    "Metadata file not found: state_laws_non_legislative_metadata.json"
                )
            )
            self.stdout.write("   Run consolidate_non_legislative_metadata.py first!")
            return

        all_laws = metadata.get("laws", [])

        if options["state"]:
            state_name = options["state"].replace("_", " ").title()
            all_laws = [law for law in all_laws if law.get("state") == state_name]
            selection_desc = f"state: {options['state']}"
        else:
            selection_desc = "all states (non-legislative)"

        if options["limit"]:
            all_laws = all_laws[: options["limit"]]

        if not all_laws:
            self.stdout.write(self.style.ERROR(f"No laws found for {selection_desc}"))
            return

        self.stdout.write("=" * 70)
        self.stdout.write("NON-LEGISLATIVE LAW INGESTION PLAN")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Selection: {selection_desc}")
        self.stdout.write(f"Laws to ingest: {len(all_laws):,}")
        self.stdout.write(f"Batch size: {options['batch_size']}")
        self.stdout.write(f"Dry run: {options['dry_run']}")
        self.stdout.write("=" * 70)
        self.stdout.write("")

        self.stdout.write("Starting database ingestion...\n")

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

        success_count = sum(1 for r in results if r["success"])
        failed = [r for r in results if not r["success"]]

        action_counts = {}
        for r in results:
            if r["success"]:
                action = r.get("action", "unknown")
                action_counts[action] = action_counts.get(action, 0) + 1

        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write("INGESTION SUMMARY")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Total laws:     {len(results):,}")
        self.stdout.write(
            f"Success:        {success_count:,} ({success_count/len(results)*100:.1f}%)"
        )
        self.stdout.write(f"Failed:         {len(failed):,}")
        self.stdout.write("")

        if action_counts:
            self.stdout.write("Actions:")
            for action, count in sorted(action_counts.items()):
                self.stdout.write(f"  {action:15} {count:5,}")

        if failed and len(failed) <= 20:
            self.stdout.write(f"\nFailed laws ({len(failed)}):")
            for result in failed[:20]:
                self.stdout.write(f"  - {result['official_id']}: {result['error']}")
        elif failed:
            self.stdout.write(f"\n{len(failed)} laws failed")

        self.stdout.write("=" * 70)

        if not options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully ingested {success_count:,} non-legislative laws!"
                )
            )
