#!/usr/bin/env python3
"""
Bulk Non-Legislative State Law Scraper (OJN Poderes 1/3/4)

Scrapes all state-level executive, judicial, and autonomous body regulations
from the Orden Juridico Nacional (OJN) portal for all 32 Mexican states.

This script uses OJNScraper.scrape_state_comprehensive() with power_ids=[1, 3, 4],
skipping power 2 (Legislativo) which is already scraped by bulk_state_scraper.py.

Expected yield: ~23,660 laws (doubles the existing corpus).
Expected runtime: 12-24 hours for all 32 states.

Usage:
    python bulk_non_legislative_scraper.py              # Scrape all states
    python bulk_non_legislative_scraper.py --limit 5    # Limit laws per state (testing)
    python bulk_non_legislative_scraper.py --resume      # Resume from last checkpoint
    python bulk_non_legislative_scraper.py --state 16    # Scrape single state by ID

Post-scrape steps (manual):
    1. Update data/universe_registry.json state_non_legislativo.scraped_count
    2. Run ingestion pipeline to parse + load into DB
    3. Re-index Elasticsearch
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from ojn_scraper import OJNScraper

# OJN Power IDs: 1=Ejecutivo, 2=Legislativo, 3=Judicial, 4=Organismos Autonomos
NON_LEGISLATIVE_POWER_IDS = [1, 3, 4]


def load_state_registry(project_root: Path) -> list:
    """Load state list from data/state_registry.json."""
    registry_path = project_root / "data/state_registry.json"
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
    return registry["states"]


def load_progress(progress_file: Path) -> dict:
    """Load scraping progress from checkpoint file."""
    if progress_file.exists():
        with open(progress_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(progress_file: Path, progress: dict):
    """Save scraping progress to checkpoint file."""
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def is_state_completed(state_name: str, output_dir: Path) -> bool:
    """Check if a state already has metadata JSON (already scraped)."""
    state_dir = output_dir / state_name.lower().replace(" ", "_")
    metadata_file = state_dir / f"{state_name.lower()}_metadata.json"
    return metadata_file.exists()


def main():
    parser = argparse.ArgumentParser(
        description="Bulk scraper for OJN non-legislative laws (poderes 1/3/4)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of laws per state (for testing)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint, skipping completed states",
    )
    parser.add_argument(
        "--state",
        type=int,
        default=None,
        help="Scrape a single state by ID (1-32)",
    )
    args = parser.parse_args()

    # Paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / "data/state_laws_non_legislative"
    output_dir.mkdir(parents=True, exist_ok=True)
    progress_file = output_dir / "scraping_progress.json"
    log_file = output_dir / "scraping_log.txt"

    def log(message: str):
        """Log to both console and file."""
        print(message)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} - {message}\n")

    # Load states
    states = load_state_registry(project_root)

    # Filter to single state if requested
    if args.state:
        states = [s for s in states if s["id"] == args.state]
        if not states:
            print(f"Error: No state found with ID {args.state}")
            sys.exit(1)

    # Initialize scraper
    scraper = OJNScraper(output_dir=str(output_dir))

    # Initialize or load progress
    if args.resume:
        progress = load_progress(progress_file)
        log("Resuming from previous checkpoint.")
    else:
        progress = {}

    total_stats = progress.get(
        "total_stats",
        {
            "states_completed": 0,
            "states_skipped": 0,
            "states_failed": 0,
            "total_laws_found": 0,
            "total_laws_downloaded": 0,
            "total_laws_failed": 0,
            "start_time": datetime.now().isoformat(),
            "state_results": [],
        },
    )

    completed_state_ids = {
        r["state_id"] for r in total_stats.get("state_results", []) if "error" not in r
    }

    log("=" * 80)
    log("OJN NON-LEGISLATIVE BULK SCRAPER (Poderes 1/3/4)")
    log(f"Powers: {NON_LEGISLATIVE_POWER_IDS} (Ejecutivo, Judicial, Autonomos)")
    log(f"States to process: {len(states)}")
    log(f"Output directory: {output_dir}")
    if args.limit:
        log(f"Limit per state: {args.limit}")
    if args.resume:
        log(f"States already completed: {len(completed_state_ids)}")
    log(f"Start time: {datetime.now().isoformat()}")
    log("=" * 80)

    for i, state in enumerate(states, 1):
        state_id = state["id"]
        state_name = state["name"]

        # Skip if already completed (resume mode or metadata exists)
        if args.resume and (
            state_id in completed_state_ids
            or is_state_completed(state_name, output_dir)
        ):
            log(f"\n[{i}/{len(states)}] Skipping {state_name} (already completed)")
            total_stats["states_skipped"] += 1
            continue

        log(f"\n[{i}/{len(states)}] Starting: {state_name} (ID: {state_id})")

        try:
            results = scraper.scrape_state_comprehensive(
                state_id=state_id,
                state_name=state_name,
                power_ids=NON_LEGISLATIVE_POWER_IDS,
                limit=args.limit,
            )

            total_stats["states_completed"] += 1
            total_stats["total_laws_found"] += results["total_found"]
            total_stats["total_laws_downloaded"] += results["successful"]
            total_stats["total_laws_failed"] += results["failed"]

            state_result = {
                "state_id": state_id,
                "state_name": state_name,
                "found": results["total_found"],
                "downloaded": results["successful"],
                "failed": results["failed"],
                "success_rate": (
                    f"{results['successful'] / results['total_found'] * 100:.1f}%"
                    if results["total_found"] > 0
                    else "0%"
                ),
            }
            total_stats["state_results"].append(state_result)

            log(
                f"Completed {state_name}: "
                f"{results['successful']}/{results['total_found']} laws downloaded"
            )

        except Exception as e:
            log(f"FAILED {state_name}: {e}")
            total_stats["states_failed"] += 1
            total_stats["state_results"].append(
                {"state_id": state_id, "state_name": state_name, "error": str(e)}
            )

        # Save progress after each state
        progress["total_stats"] = total_stats
        save_progress(progress_file, progress)

    # Final summary
    total_stats["end_time"] = datetime.now().isoformat()
    progress["total_stats"] = total_stats
    save_progress(progress_file, progress)

    log("\n" + "=" * 80)
    log("BULK NON-LEGISLATIVE SCRAPING COMPLETE")
    log("=" * 80)
    log(f"States completed: {total_stats['states_completed']}/{len(states)}")
    log(f"States skipped:   {total_stats['states_skipped']}")
    log(f"States failed:    {total_stats['states_failed']}")
    log(f"Total laws found: {total_stats['total_laws_found']}")
    log(f"Total downloaded: {total_stats['total_laws_downloaded']}")
    log(f"Total failed:     {total_stats['total_laws_failed']}")
    if total_stats["total_laws_found"] > 0:
        rate = (
            total_stats["total_laws_downloaded"] / total_stats["total_laws_found"] * 100
        )
        log(f"Success rate:     {rate:.1f}%")
    log(f"End time:         {total_stats['end_time']}")
    log("=" * 80)

    # Per-state summary table
    log("\nPer-State Results:")
    log(f"{'State':<25} {'Found':>8} {'Downloaded':>12} {'Failed':>8} {'Rate':>8}")
    log("-" * 65)
    for r in total_stats["state_results"]:
        if "error" in r:
            log(f"{r['state_name']:<25} {'ERROR':>8} {r['error'][:30]:>12}")
        else:
            log(
                f"{r['state_name']:<25} {r['found']:>8} {r['downloaded']:>12} "
                f"{r['failed']:>8} {r['success_rate']:>8}"
            )

    log(f"\nProgress saved to: {progress_file}")
    log(f"Log saved to: {log_file}")
    log("\nNext steps:")
    log("  1. Update data/universe_registry.json state_non_legislativo.scraped_count")
    log("  2. Run ingestion pipeline to parse + load into DB")
    log("  3. Re-index Elasticsearch")


if __name__ == "__main__":
    main()
