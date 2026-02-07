#!/usr/bin/env python3
"""
Convert state law .doc files to plain text using textutil (Mac).
Processes in parallel with progress tracking.

Usage:
    # Test on single state
    python scripts/state_laws/convert_docs.py --state colima

    # Run on all states
    python scripts/state_laws/convert_docs.py --all

    # Control parallelism
    python scripts/state_laws/convert_docs.py --all --workers 12
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from multiprocessing import Pool
from pathlib import Path


def convert_doc_to_text(args_tuple) -> dict:
    """Convert single .doc to .txt using textutil.

    Args:
        args_tuple: (doc_path, source_dir, output_dir) or just doc_path for backwards compat

    Returns:
        dict with conversion results
    """
    if isinstance(args_tuple, tuple):
        doc_path, source_dir, output_dir = args_tuple
    else:
        doc_path = args_tuple
        source_dir = Path("data/state_laws")
        output_dir = Path("data/state_laws_processed")

    # Create output directory structure
    relative_path = doc_path.relative_to(source_dir)
    txt_path = output_dir / relative_path.with_suffix(".txt")
    txt_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Convert using textutil
        result = subprocess.run(
            ["textutil", "-convert", "txt", "-output", str(txt_path), str(doc_path)],
            check=True,
            capture_output=True,
            timeout=30,
        )

        # Read and get stats
        text = txt_path.read_text(encoding="utf-8", errors="ignore")

        # Basic validation
        if len(text.strip()) < 100:
            return {
                "success": False,
                "doc_path": str(doc_path),
                "txt_path": str(txt_path),
                "error": "Text too short (likely empty document)",
            }

        return {
            "success": True,
            "doc_path": str(doc_path),
            "txt_path": str(txt_path),
            "char_count": len(text),
            "word_count": len(text.split()),
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "doc_path": str(doc_path),
            "error": "Conversion timeout (30s)",
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "doc_path": str(doc_path),
            "error": f"textutil error: {e.stderr.decode()}",
        }
    except Exception as e:
        return {"success": False, "doc_path": str(doc_path), "error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Convert state law .doc files to text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all", action="store_true", help="Process all state law .doc files"
    )
    group.add_argument(
        "--state", type=str, help="Process specific state (e.g., colima)"
    )

    parser.add_argument(
        "--workers", type=int, default=8, help="Number of parallel workers (default: 8)"
    )
    parser.add_argument(
        "--limit", type=int, help="Limit number of files to process (for testing)"
    )
    parser.add_argument(
        "--non-legislative",
        action="store_true",
        help="Convert non-legislative state laws (from data/state_laws_non_legislative/)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file for results",
    )

    args = parser.parse_args()

    # Determine source and output directories
    if args.non_legislative:
        source_dir = Path("data/state_laws_non_legislative")
        output_dir = Path("data/state_laws_non_legislative_processed")
        default_output = "data/conversion_results_non_legislative.json"
    else:
        source_dir = Path("data/state_laws")
        output_dir = Path("data/state_laws_processed")
        default_output = "data/conversion_results.json"

    output_file = args.output or default_output

    # Find .doc files
    if args.all:
        doc_files = list(source_dir.rglob("*.doc"))
        selection_desc = f"all states ({'non-legislative' if args.non_legislative else 'legislative'})"
    elif args.state:
        state_dir = source_dir / args.state.lower().replace(" ", "_")
        if not state_dir.exists():
            print(f"State directory not found: {state_dir}")
            return 1
        doc_files = list(state_dir.glob("*.doc"))
        selection_desc = f"state: {args.state} ({'non-legislative' if args.non_legislative else 'legislative'})"
    else:
        print("Error: Must specify --all or --state")
        return 1

    # Exclude metadata files
    doc_files = [f for f in doc_files if not f.name.endswith("_metadata.json")]

    if args.limit:
        doc_files = doc_files[: args.limit]

    if not doc_files:
        print(f"❌ No .doc files found for {selection_desc}")
        return 1

    # Display plan
    print("=" * 70)
    print("DOCUMENT CONVERSION PLAN")
    print("=" * 70)
    print(f"Selection: {selection_desc}")
    print(f"Files to convert: {len(doc_files):,}")
    print(f"Workers: {args.workers}")
    print(f"Output: {output_file}")
    print("=" * 70)
    print()

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Build args tuples for worker function
    work_items = [(f, source_dir, output_dir) for f in doc_files]

    # Process files
    start_time = datetime.now()
    print(f"Starting conversion...")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Use multiprocessing pool
    if args.workers > 1:
        with Pool(processes=args.workers) as pool:
            # Use imap for progress tracking
            results = []
            for i, result in enumerate(pool.imap(convert_doc_to_text, work_items), 1):
                results.append(result)

                # Progress indicator every 100 files
                if i % 100 == 0:
                    success_so_far = sum(1 for r in results if r["success"])
                    print(
                        f"  Processed: {i:,}/{len(doc_files):,} "
                        f"({success_so_far}/{i} successful)"
                    )
    else:
        # Single-threaded for debugging
        results = []
        for i, work_item in enumerate(work_items, 1):
            result = convert_doc_to_text(work_item)
            results.append(result)

            if i % 100 == 0:
                success_so_far = sum(1 for r in results if r["success"])
                print(
                    f"  Processed: {i:,}/{len(doc_files):,} "
                    f"({success_so_far}/{i} successful)"
                )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Analyze results
    success_count = sum(1 for r in results if r["success"])
    failed = [r for r in results if not r["success"]]

    # Calculate statistics
    total_chars = sum(r.get("char_count", 0) for r in results if r["success"])
    total_words = sum(r.get("word_count", 0) for r in results if r["success"])

    # Print summary
    print()
    print("=" * 70)
    print("CONVERSION SUMMARY")
    print("=" * 70)
    print(f"Start time:     {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End time:       {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration:       {duration:.1f}s ({duration/60:.1f} min)")
    print(f"Total files:    {len(results):,}")
    print(f"Success:        {success_count:,} ({success_count/len(results)*100:.1f}%)")
    print(f"Failed:         {len(failed):,}")
    print(f"Avg time:       {duration/len(results):.2f}s per file")
    print()
    print(f"Total chars:    {total_chars:,}")
    print(f"Total words:    {total_words:,}")
    print(
        f"Avg per file:   {total_words/success_count if success_count > 0 else 0:.0f} words"
    )

    # Failed files detail
    if failed and len(failed) <= 20:
        print(f"\n❌ Failed files ({len(failed)}):")
        for result in failed[:20]:
            doc_name = Path(result["doc_path"]).name
            print(f"  • {doc_name}: {result['error']}")
    elif failed:
        print(f"\n{len(failed)} files failed")
        print(f"   (First 20 errors saved to {output_file})")

    print("=" * 70)

    # Save results to JSON
    output_data = {
        "timestamp": start_time.isoformat(),
        "duration_seconds": duration,
        "total_files": len(results),
        "success_count": success_count,
        "failed_count": len(failed),
        "total_chars": total_chars,
        "total_words": total_words,
        "selection": selection_desc,
        "results": results,
    }

    output_path = Path(output_file)
    output_path.write_text(json.dumps(output_data, indent=2))
    print(f"\nResults saved to: {output_path}")

    # Return error code if any failures
    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
