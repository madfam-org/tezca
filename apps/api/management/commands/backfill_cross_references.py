"""
Backfill cross-references for existing laws.

Runs cross-reference detection on all laws with XML files and stores
the results in the CrossReference model. Builds the slug index ONCE
and reuses it across all laws for efficiency.

Usage:
    python manage.py backfill_cross_references --all --dry-run
    python manage.py backfill_cross_references --all --batch-size 50
    python manage.py backfill_cross_references --law-id cpeum
    python manage.py backfill_cross_references --all --tier federal
"""

from django.core.management.base import BaseCommand

from apps.api.models import LawVersion
from apps.api.utils.paths import resolve_data_path_or_none
from apps.parsers.cross_reference_integration import (
    _build_law_slug_index,
    detect_and_store_cross_references,
)
from apps.parsers.cross_references import CrossReferenceDetector


class Command(BaseCommand):
    help = "Backfill cross-references for laws with XML files."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--all",
            action="store_true",
            help="Process all laws with XML files.",
        )
        group.add_argument(
            "--law-id",
            type=str,
            help="Process a single law by official_id.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Detect references but do not save to DB.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Number of laws to process between progress reports (default: 50).",
        )
        parser.add_argument(
            "--tier",
            type=str,
            choices=["federal", "state", "municipal", "all"],
            default="all",
            help="Filter by law tier (default: all).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        tier = options["tier"]
        law_id = options.get("law_id")

        # Get latest version per law (with XML)
        qs = (
            LawVersion.objects.filter(xml_file_path__isnull=False)
            .exclude(xml_file_path="")
            .select_related("law")
            .order_by("law_id", "-publication_date")
            .distinct("law_id")
        )

        if law_id:
            qs = qs.filter(law__official_id=law_id)

        if tier != "all":
            qs = qs.filter(law__tier=tier)

        total = qs.count()
        self.stdout.write(f"Found {total} laws with XML to process.")
        if dry_run:
            self.stdout.write("DRY RUN — no changes will be saved.")

        # Build slug index ONCE
        self.stdout.write("Building law slug index...")
        slug_index = _build_law_slug_index()
        self.stdout.write(f"Slug index: {len(slug_index)} entries.")

        detector = CrossReferenceDetector()
        processed = 0
        total_refs = 0
        skipped = 0
        errors = 0

        for version in qs.iterator(chunk_size=batch_size):
            xml_path = resolve_data_path_or_none(version.xml_file_path)
            if xml_path is None:
                skipped += 1
                continue

            try:
                if dry_run:
                    # Just count without persisting
                    from lxml import etree

                    tree = etree.parse(str(xml_path))
                    root = tree.getroot()
                    ns = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}
                    articles = root.findall(".//akn:article", ns)
                    ref_count = 0
                    for article in articles:
                        paragraphs = article.findall(".//akn:p", ns)
                        text = " ".join([p.text or "" for p in paragraphs])
                        refs = detector.detect(text)
                        ref_count += len(refs)
                    total_refs += ref_count
                else:
                    n = detect_and_store_cross_references(
                        version.law.official_id,
                        xml_path,
                        detector=detector,
                        slug_index=slug_index,
                    )
                    total_refs += n
            except Exception as e:
                self.stderr.write(f"  Error processing {version.law.official_id}: {e}")
                errors += 1

            processed += 1
            if processed % batch_size == 0:
                self.stdout.write(
                    f"  Processed {processed}/{total} laws "
                    f"({total_refs} refs so far)..."
                )

        self.stdout.write("\n--- Summary ---")
        self.stdout.write(f"Total:       {total}")
        self.stdout.write(f"Processed:   {processed}")
        self.stdout.write(f"Skipped:     {skipped}")
        self.stdout.write(f"Errors:      {errors}")
        self.stdout.write(f"Total refs:  {total_refs}")

        if dry_run:
            self.stdout.write("\nDRY RUN — no changes were saved.")
