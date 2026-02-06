#!/usr/bin/env python3
"""
Ingest state laws into Django database.
Creates Law and LawVersion records from processed text + metadata.

Usage:
    # Ingest specific state
    python scripts/state_laws/ingest_state_laws.py --state colima

    # Ingest all states
    python scripts/state_laws/ingest_state_laws.py --all

    # Dry run (no database writes)
    python scripts/state_laws/ingest_state_laws.py --all --dry-run
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import django

# Setup Django
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "indigo.settings")
django.setup()

from api.models import Law, LawVersion
from django.db import transaction


def create_law_and_version(metadata: Dict, dry_run: bool = False) -> Dict:
    """Create Law and LawVersion records from metadata.

    Args:
        metadata: Law metadata from extraction
        dry_run: If True, don't actually create records

    Returns:
        Result dictionary
    """
    try:
        official_id = metadata["official_id"]
        law_name = metadata["law_name"]
        category = metadata.get("category", "Otros")
        tier = metadata.get("tier", "state")
        state = metadata.get("state", "Unknown")
        publication_date = metadata.get("publication_date")
        text_file = metadata.get("text_file")

        # Read law text
        if not text_file or not Path(text_file).exists():
            return {
                "success": False,
                "official_id": official_id,
                "error": f"Text file not found: {text_file}",
            }

        text_content = Path(text_file).read_text(encoding="utf-8", errors="ignore")

        if dry_run:
            return {
                "success": True,
                "official_id": official_id,
                "action": "dry_run",
                "law_name": law_name,
                "category": category,
            }

        # Check if law already exists
        existing_law = Law.objects.filter(official_id=official_id).first()

        if existing_law:
            # Update existing
            existing_law.name = law_name
            existing_law.tier = tier
            existing_law.category = category
            existing_law.save()

            law = existing_law
            action = "updated"
        else:
            # Create new law
            law = Law.objects.create(
                official_id=official_id, name=law_name, tier=tier, category=category
            )
            action = "created"

        # Create or update law version (idempotent)
        pub_date = publication_date if publication_date else "2023-01-01"

        version, v_created = LawVersion.objects.get_or_create(
            law=law,
            publication_date=pub_date,
            defaults={
                "dof_url": metadata.get("url", ""),
                "xml_file_path": text_file,
            },
        )
        if not v_created:
            version.dof_url = metadata.get("url", "")
            version.xml_file_path = text_file
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


def main():
    parser = argparse.ArgumentParser(
        description="Ingest state laws into database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Ingest all state laws")
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

    args = parser.parse_args()

    # Load metadata
    print("📚 Loading state law metadata...")
    metadata_file = Path("data/state_laws_metadata.json")

    if not metadata_file.exists():
        print(f"❌ Metadata file not found: {metadata_file}")
        print("   Run extract_metadata.py first!")
        return 1

    metadata = json.loads(metadata_file.read_text())
    all_laws = metadata.get("laws", [])

    # Filter by state if requested
    if args.state:
        state_name = args.state.replace("_", " ").title()
        all_laws = [law for law in all_laws if law.get("state") == state_name]
        selection_desc = f"state: {args.state}"
    else:
        selection_desc = "all states"

    if args.limit:
        all_laws = all_laws[: args.limit]

    if not all_laws:
        print(f"❌ No laws found for {selection_desc}")
        return 1

    # Display plan
    print()
    print("=" * 70)
    print("DATABASE INGESTION PLAN")
    print("=" * 70)
    print(f"Selection: {selection_desc}")
    print(f"Laws to ingest: {len(all_laws):,}")
    print(f"Batch size: {args.batch_size}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 70)
    print()

    if not args.dry_run:
        response = input(f"Create {len(all_laws):,} database records? [y/N]: ")
        if response.lower() != "y":
            print("Cancelled.")
            return 0

    # Process laws in batches
    start_time = datetime.now()
    print("🚀 Starting database ingestion...")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = []
    batch_count = 0

    for i in range(0, len(all_laws), args.batch_size):
        batch = all_laws[i : i + args.batch_size]
        batch_count += 1

        # Process batch in transaction
        if not args.dry_run:
            with transaction.atomic():
                for law_metadata in batch:
                    result = create_law_and_version(law_metadata, args.dry_run)
                    results.append(result)
        else:
            for law_metadata in batch:
                result = create_law_and_version(law_metadata, args.dry_run)
                results.append(result)

        # Progress
        processed = len(results)
        success_so_far = sum(1 for r in results if r["success"])
        print(
            f"  Batch {batch_count}: {processed:,}/{len(all_laws):,} "
            f"({success_so_far}/{processed} successful)"
        )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Analyze results
    success_count = sum(1 for r in results if r["success"])
    failed = [r for r in results if not r["success"]]

    # Action distribution
    action_counts = {}
    for r in results:
        if r["success"]:
            action = r.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1

    # Category distribution
    category_counts = {}
    for r in results:
        if r["success"]:
            cat = r.get("category", "Unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1

    # Print summary
    print()
    print("=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)
    print(f"Duration:       {duration:.1f}s ({duration/60:.1f} min)")
    print(f"Total laws:     {len(results):,}")
    print(f"Success:        {success_count:,} ({success_count/len(results)*100:.1f}%)")
    print(f"Failed:         {len(failed):,}")
    print()

    if action_counts:
        print("Actions:")
        for action, count in sorted(action_counts.items()):
            print(f"  {action:15} {count:5,}")
        print()

    if category_counts:
        print("Categories:")
        for cat in sorted(category_counts.keys()):
            count = category_counts[cat]
            print(f"  {cat:20} {count:5,}")

    # Failed laws detail
    if failed and len(failed) <= 20:
        print(f"\n❌ Failed laws ({len(failed)}):")
        for result in failed[:20]:
            print(f"  • {result['official_id']}: {result['error']}")
    elif failed:
        print(f"\n❌ {len(failed)} laws failed (see details above)")

    print("=" * 70)

    if not args.dry_run:
        print(f"\n✅ Successfully ingested {success_count:,} state laws into database!")

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
