"""
Management command to remove duplicate Law entries from the database.

Duplicates were introduced by earlier ingestion runs:
- 9,894 state laws with state=NULL (re-ingested without the state field)
- 330 federal laws with subject-matter tiers (e.g., tier="fiscal") instead of tier="federal"

All operations are wrapped in transaction.atomic() for rollback safety.
Use --dry-run to preview changes without writing.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.api.models import Law, LawVersion


class Command(BaseCommand):
    help = "Remove duplicate Law entries created by earlier ingestion runs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would change without writing to the database.",
        )
        parser.add_argument(
            "--fix-state-dupes",
            action="store_true",
            help="Delete state-tier laws that have state=NULL (duplicates from re-ingestion).",
        )
        parser.add_argument(
            "--fix-federal-tiers",
            action="store_true",
            help="Delete laws with subject-matter tiers (fiscal, labor, etc.) that duplicate tier=federal entries.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Run all dedup steps.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        run_all = options["all"]
        fix_state = options["fix_state_dupes"] or run_all
        fix_federal = options["fix_federal_tiers"] or run_all

        if not fix_state and not fix_federal:
            self.stderr.write(
                self.style.ERROR(
                    "No action specified. Use --fix-state-dupes, --fix-federal-tiers, or --all."
                )
            )
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN MODE ===\n"))

        # Print before counts
        self._print_counts("BEFORE")

        if fix_state:
            self._fix_state_dupes(dry_run)

        if fix_federal:
            self._fix_federal_tiers(dry_run)

        # Print after counts
        if not dry_run:
            self._print_counts("AFTER")

    def _print_counts(self, label):
        total = Law.objects.count()
        federal = Law.objects.filter(tier="federal").count()
        state = Law.objects.filter(tier="state").count()
        municipal = Law.objects.filter(tier="municipal").count()
        other = total - federal - state - municipal
        versions = LawVersion.objects.count()

        self.stdout.write(f"\n--- {label} ---")
        self.stdout.write(f"  Total laws:     {total}")
        self.stdout.write(f"  Federal:        {federal}")
        self.stdout.write(f"  State:          {state}")
        self.stdout.write(f"  Municipal:      {municipal}")
        self.stdout.write(f"  Other tiers:    {other}")
        self.stdout.write(f"  LawVersions:    {versions}")
        self.stdout.write("")

    def _fix_state_dupes(self, dry_run):
        """Delete state-tier laws where state field is NULL.

        These are duplicates created when state laws were re-ingested
        without the state field populated. The canonical entries have
        state != NULL.
        """
        self.stdout.write(
            self.style.MIGRATE_HEADING("Step 1: Fix state duplicates (state=NULL)")
        )

        dupes = Law.objects.filter(tier="state", state__isnull=True)
        dupe_count = dupes.count()
        version_count = LawVersion.objects.filter(law__in=dupes).count()

        self.stdout.write(f"  Found {dupe_count} state laws with state=NULL")
        self.stdout.write(f"  Associated LawVersions: {version_count}")

        if dupe_count == 0:
            self.stdout.write(self.style.SUCCESS("  Nothing to clean up."))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"  Would delete {dupe_count} laws and {version_count} versions."
                )
            )
            # Show a sample
            sample = dupes.values_list("official_id", flat=True)[:10]
            self.stdout.write(f"  Sample IDs: {list(sample)}")
        else:
            with transaction.atomic():
                deleted_versions = LawVersion.objects.filter(law__in=dupes).delete()
                deleted_laws = dupes.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Deleted {deleted_laws[0]} laws and {deleted_versions[0]} versions."
                    )
                )

    def _fix_federal_tiers(self, dry_run):
        """Delete laws with subject-matter tier values that are duplicates of tier=federal.

        Earlier ingestion assigned tiers like 'fiscal', 'labor', 'administrative', etc.
        The canonical entries have tier='federal' and were created by the pipeline
        with XML files.
        """
        self.stdout.write(
            self.style.MIGRATE_HEADING("Step 2: Fix federal tier duplicates")
        )

        # Known subject-matter tiers that are NOT valid jurisdiction tiers
        VALID_TIERS = {"federal", "state", "municipal"}
        invalid_tier_laws = Law.objects.exclude(tier__in=VALID_TIERS).exclude(
            tier__isnull=True
        )
        invalid_count = invalid_tier_laws.count()
        version_count = LawVersion.objects.filter(law__in=invalid_tier_laws).count()

        if invalid_count == 0:
            self.stdout.write(self.style.SUCCESS("  No invalid-tier laws found."))
            return

        # Show breakdown by tier
        tier_breakdown = {}
        for law in invalid_tier_laws.values("tier"):
            t = law["tier"]
            tier_breakdown[t] = tier_breakdown.get(t, 0) + 1
        self.stdout.write(f"  Found {invalid_count} laws with non-standard tiers:")
        for tier_name, count in sorted(tier_breakdown.items()):
            self.stdout.write(f"    tier='{tier_name}': {count}")
        self.stdout.write(f"  Associated LawVersions: {version_count}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"  Would delete {invalid_count} laws and {version_count} versions."
                )
            )
            sample = invalid_tier_laws.values_list("official_id", "tier")[:10]
            self.stdout.write(f"  Sample: {list(sample)}")
        else:
            with transaction.atomic():
                deleted_versions = LawVersion.objects.filter(
                    law__in=invalid_tier_laws
                ).delete()
                deleted_laws = invalid_tier_laws.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Deleted {deleted_laws[0]} laws and {deleted_versions[0]} versions."
                    )
                )
