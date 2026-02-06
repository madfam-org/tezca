#!/usr/bin/env python
"""
CLI script to batch-parse state/municipal laws to Akoma Ntoso XML.

Reads state_laws_metadata.json (or municipal_laws_metadata.json), runs each
law through StateLawParser, and updates metadata with akn_file_path.

Usage:
    # Parse all state laws
    python scripts/ingestion/parse_state_laws.py --all

    # Parse specific state
    python scripts/ingestion/parse_state_laws.py --state colima --limit 5

    # Parse municipal laws
    python scripts/ingestion/parse_state_laws.py --municipal --all

    # Parallel workers
    python scripts/ingestion/parse_state_laws.py --all --workers 4
"""

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_single_law(law_metadata):
    """Parse a single law (designed for process pool execution)."""
    # Must import inside function for multiprocessing
    from apps.parsers.state_parser import StateLawParser

    parser = StateLawParser(base_dir=PROJECT_ROOT)
    result = parser.parse_law(law_metadata)

    return {
        "official_id": result.official_id,
        "success": result.success,
        "error": result.error,
        "akn_path": str(result.akn_path) if result.akn_path else None,
        "article_count": result.article_count,
        "duration": result.duration_seconds,
        "grade": (result.quality_metrics.grade if result.quality_metrics else "N/A"),
    }


def load_metadata(metadata_path):
    """Load metadata JSON file."""
    if not metadata_path.exists():
        print(f"Metadata file not found: {metadata_path}")
        return []
    data = json.loads(metadata_path.read_text())
    return data.get("laws", [])


def save_metadata(metadata_path, laws, original_data):
    """Save updated metadata back to file."""
    original_data["laws"] = laws
    metadata_path.write_text(
        json.dumps(original_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main():
    arg_parser = argparse.ArgumentParser(
        description="Parse state/municipal laws to Akoma Ntoso XML"
    )

    group = arg_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Parse all laws")
    group.add_argument("--state", type=str, help="Parse specific state")

    arg_parser.add_argument(
        "--municipal",
        action="store_true",
        help="Parse municipal laws instead of state laws",
    )
    arg_parser.add_argument("--limit", type=int, help="Limit number of laws")
    arg_parser.add_argument(
        "--workers", type=int, default=1, help="Number of parallel workers (default: 1)"
    )
    arg_parser.add_argument(
        "--force", action="store_true", help="Re-parse even if AKN XML already exists"
    )
    arg_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be parsed without doing it",
    )

    args = arg_parser.parse_args()

    # Determine metadata file
    if args.municipal:
        metadata_filename = "municipal_laws_metadata.json"
        label = "municipal"
    else:
        metadata_filename = "state_laws_metadata.json"
        label = "state"

    metadata_path = PROJECT_ROOT / "data" / metadata_filename
    print(f"Loading {label} law metadata from {metadata_path}...")

    original_data = (
        json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    )
    all_laws = original_data.get("laws", [])

    if not all_laws:
        print(f"No laws found in {metadata_path}")
        return

    # Filter by state
    if args.state:
        state_name = args.state.replace("_", " ").title()
        all_laws = [
            l for l in all_laws if l.get("state", "").lower() == state_name.lower()
        ]
        print(f"Filtered to state: {state_name} ({len(all_laws)} laws)")

    # Skip laws that already have AKN XML (unless --force)
    if not args.force:
        from apps.api.utils.paths import resolve_data_path_or_none

        to_parse = []
        already_parsed = 0
        for law in all_laws:
            akn_file = law.get("akn_file_path", "")
            if akn_file and resolve_data_path_or_none(akn_file):
                already_parsed += 1
            else:
                to_parse.append(law)
        if already_parsed:
            print(
                f"Skipping {already_parsed} laws with existing AKN XML (use --force to re-parse)"
            )
        all_laws = to_parse

    # Filter laws without text files
    parseable = [l for l in all_laws if l.get("text_file")]
    skipped_no_text = len(all_laws) - len(parseable)
    if skipped_no_text:
        print(f"Skipping {skipped_no_text} laws without text_file")

    # Apply limit
    if args.limit:
        parseable = parseable[: args.limit]

    print(f"\nWill parse {len(parseable)} {label} laws (workers={args.workers})")
    print("=" * 70)

    if args.dry_run:
        for law in parseable[:10]:
            print(
                f"  Would parse: {law.get('official_id', '?')} - {law.get('law_name', '?')[:60]}"
            )
        if len(parseable) > 10:
            print(f"  ... and {len(parseable) - 10} more")
        return

    # Build a lookup from official_id -> index in original_data["laws"]
    law_index_map = {}
    for i, law in enumerate(original_data.get("laws", [])):
        law_index_map[law.get("official_id", "")] = i

    start_time = time.time()
    success_count = 0
    fail_count = 0
    total_articles = 0

    if args.workers > 1:
        # Parallel execution
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(parse_single_law, law): law for law in parseable}
            for future in as_completed(futures):
                result = future.result()
                _print_result(result)

                if result["success"]:
                    success_count += 1
                    total_articles += result["article_count"]
                    # Update metadata with AKN path
                    _update_metadata(original_data, law_index_map, result)
                else:
                    fail_count += 1
    else:
        # Sequential execution
        for law in parseable:
            result = parse_single_law(law)
            _print_result(result)

            if result["success"]:
                success_count += 1
                total_articles += result["article_count"]
                _update_metadata(original_data, law_index_map, result)
            else:
                fail_count += 1

    # Save updated metadata
    if success_count > 0:
        save_metadata(metadata_path, original_data.get("laws", []), original_data)
        print(f"\nUpdated {metadata_path} with AKN file paths")

    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print("PARSE SUMMARY")
    print("=" * 70)
    print(f"Total:    {len(parseable)}")
    print(f"Success:  {success_count}")
    print(f"Failed:   {fail_count}")
    print(f"Articles: {total_articles:,}")
    print(f"Time:     {elapsed:.1f}s")
    if success_count:
        print(f"Avg:      {elapsed / success_count:.1f}s per law")
    print("=" * 70)


def _print_result(result):
    """Print a single parse result."""
    if result["success"]:
        print(
            f"  OK  {result['official_id']}: "
            f"{result['article_count']} articles, "
            f"Grade {result['grade']} "
            f"({result['duration']:.1f}s)"
        )
    else:
        print(f"  FAIL {result['official_id']}: {result['error']}")


def _update_metadata(original_data, law_index_map, result):
    """Update metadata entry with AKN file path."""
    official_id = result["official_id"]
    idx = law_index_map.get(official_id)
    if idx is not None and result["akn_path"]:
        laws = original_data.get("laws", [])
        if idx < len(laws):
            # Store path relative to project root
            akn_path = result["akn_path"]
            project_root = str(PROJECT_ROOT) + "/"
            if akn_path.startswith(project_root):
                akn_path = akn_path[len(project_root) :]
            laws[idx]["akn_file_path"] = akn_path


if __name__ == "__main__":
    main()
