"""
Backfill quality_grade and quality_score for existing LawVersion records.

Iterates LawVersion records that have XML but no quality grade, runs
QualityCalculator on each, and bulk-updates the results.

Usage:
    python manage.py backfill_quality_scores --all --dry-run
    python manage.py backfill_quality_scores --all
    python manage.py backfill_quality_scores --law-id cpeum
    python manage.py backfill_quality_scores --all --force
    python manage.py backfill_quality_scores --all --tier federal
"""

from collections import Counter

from django.core.management.base import BaseCommand

from apps.api.models import Law, LawVersion
from apps.api.utils.paths import resolve_data_path_or_none
from apps.parsers.quality import QualityCalculator


class Command(BaseCommand):
    help = "Backfill quality_grade and quality_score for LawVersion records with XML."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--all",
            action="store_true",
            help="Process all LawVersion records with XML.",
        )
        group.add_argument(
            "--law-id",
            type=str,
            help="Process versions for a single law (by official_id / slug).",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Calculate scores but do not save to DB.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of records per bulk_update batch (default: 100).",
        )
        parser.add_argument(
            "--tier",
            type=str,
            choices=["federal", "state", "municipal", "all"],
            default="all",
            help="Filter by law tier (default: all).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-score even if quality_grade is already set.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        tier = options["tier"]
        force = options["force"]
        law_id = options.get("law_id")

        # Build queryset
        qs = LawVersion.objects.filter(
            xml_file_path__isnull=False,
        ).exclude(xml_file_path="")

        if not force:
            qs = qs.filter(quality_grade__isnull=True)

        if law_id:
            qs = qs.filter(law__official_id=law_id)

        if tier != "all":
            qs = qs.filter(law__tier=tier)

        qs = qs.select_related("law")
        total = qs.count()

        self.stdout.write(f"Found {total} LawVersion records to process.")
        if dry_run:
            self.stdout.write("DRY RUN — no changes will be saved.")

        calc = QualityCalculator()
        scored = 0
        skipped = 0
        errors = 0
        grade_dist = Counter()
        batch = []

        for version in qs.iterator(chunk_size=batch_size):
            xml_path = resolve_data_path_or_none(version.xml_file_path)
            if xml_path is None:
                skipped += 1
                continue

            try:
                metrics = calc.calculate(
                    xml_path=xml_path,
                    law_name=version.law.name,
                    law_slug=version.law.official_id,
                )
                version.quality_grade = metrics.grade
                version.quality_score = metrics.overall_score
            except Exception as e:
                self.stderr.write(
                    f"  Error scoring {version.law.official_id} "
                    f"(version {version.pk}): {e}"
                )
                version.quality_grade = "F"
                version.quality_score = 0.0
                errors += 1

            grade_dist[version.quality_grade] += 1
            scored += 1
            batch.append(version)

            if len(batch) >= batch_size and not dry_run:
                LawVersion.objects.bulk_update(
                    batch, ["quality_grade", "quality_score"], batch_size=batch_size
                )
                batch = []

        # Flush remaining
        if batch and not dry_run:
            LawVersion.objects.bulk_update(
                batch, ["quality_grade", "quality_score"], batch_size=batch_size
            )

        # Summary
        quarantined = grade_dist.get("D", 0) + grade_dist.get("F", 0)
        self.stdout.write("\n--- Summary ---")
        self.stdout.write(f"Total:       {total}")
        self.stdout.write(f"Scored:      {scored}")
        self.stdout.write(f"Skipped:     {skipped}")
        self.stdout.write(f"Errors:      {errors}")
        self.stdout.write(f"Quarantined: {quarantined}")
        self.stdout.write("Grade distribution:")
        for grade in ["A", "B", "C", "D", "F"]:
            count = grade_dist.get(grade, 0)
            if count:
                self.stdout.write(f"  {grade}: {count}")

        if dry_run:
            self.stdout.write("\nDRY RUN — no changes were saved.")
