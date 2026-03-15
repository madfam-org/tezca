#!/usr/bin/env python3
"""
Run GenericMunicipalScraper for all confirmed Tier-2 cities.

Reads probe results to determine which cities are reachable,
then scrapes catalog for each. Falls back to scraping all Tier-2
if no probe results exist.

Usage:
    python scripts/scraping/run_tier2_expansion.py
    python scripts/scraping/run_tier2_expansion.py --city merida --limit 50
    python scripts/scraping/run_tier2_expansion.py --dry-run
    python scripts/scraping/run_tier2_expansion.py --force-all  # skip probe check
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.scraper.municipal import get_scraper, list_available_scrapers
from apps.scraper.municipal.config import (
    MUNICIPALITY_CONFIGS,
    get_tier2_municipalities,
)

DATA_DIR = PROJECT_ROOT / "data"
PROBE_RESULTS = DATA_DIR / "municipal" / "tier2_probe_results.json"
OUTPUT_DIR = DATA_DIR / "municipal"


def load_confirmed_cities():
    """Load confirmed cities from probe results, or return all Tier-2 if none."""
    if PROBE_RESULTS.exists():
        with open(PROBE_RESULTS, "r", encoding="utf-8") as f:
            data = json.load(f)
        confirmed = data.get("confirmed", [])
        if confirmed:
            print(f"Loaded {len(confirmed)} confirmed cities from probe results")
            return confirmed

    print("No probe results found — using all Tier-2 cities")
    return get_tier2_municipalities()


def scrape_city(city_key: str, limit: int = None, dry_run: bool = False) -> dict:
    """Scrape a single city's catalog."""
    config = MUNICIPALITY_CONFIGS[city_key]
    result = {
        "city": city_key,
        "name": config["name"],
        "state": config["state"],
        "status": "pending",
        "total_found": 0,
        "downloaded": 0,
        "failed": 0,
        "laws": [],
        "error": None,
    }

    if dry_run:
        result["status"] = "dry_run"
        return result

    try:
        scraper = get_scraper(city_key)
        catalog = scraper.scrape_catalog()

        if limit:
            catalog = catalog[:limit]

        result["total_found"] = len(catalog)
        result["laws"] = catalog
        result["status"] = "success" if catalog else "empty"

        # Download PDFs for each law
        downloaded = 0
        failed = 0
        city_dir = OUTPUT_DIR / city_key
        city_dir.mkdir(parents=True, exist_ok=True)

        for law in catalog:
            url = law.get("url", "")
            if not url:
                continue
            try:
                content = scraper.scrape_law_content(url)
                if content:
                    downloaded += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

        result["downloaded"] = downloaded
        result["failed"] = failed

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:300]

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Run GenericMunicipalScraper for Tier-2 cities"
    )
    parser.add_argument("--city", type=str, help="Scrape specific city only")
    parser.add_argument("--limit", type=int, help="Limit laws per city")
    parser.add_argument(
        "--dry-run", action="store_true", help="List cities without scraping"
    )
    parser.add_argument(
        "--force-all", action="store_true", help="Scrape all Tier-2, ignore probe"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Only scrape catalogs, skip content download",
    )
    args = parser.parse_args()

    if args.city:
        cities = [args.city]
    elif args.force_all:
        cities = get_tier2_municipalities()
    else:
        cities = load_confirmed_cities()

    print(f"\n{'='*60}")
    print(f"TIER-2 MUNICIPAL EXPANSION")
    print(f"{'='*60}")
    print(f"Cities to scrape: {len(cities)}")
    print(f"Limit per city:   {args.limit or 'none'}")
    print(f"Dry run:          {args.dry_run}")
    print(f"{'='*60}\n")

    all_results = []
    total_found = 0
    total_downloaded = 0
    total_failed = 0

    for i, city_key in enumerate(cities, 1):
        if city_key not in MUNICIPALITY_CONFIGS:
            print(f"  [{i}/{len(cities)}] {city_key} — not configured, skipping")
            continue

        config = MUNICIPALITY_CONFIGS[city_key]
        print(
            f"  [{i}/{len(cities)}] {config['name']} ({config['state']})... ",
            end="",
            flush=True,
        )

        result = scrape_city(city_key, limit=args.limit, dry_run=args.dry_run)
        all_results.append(result)

        if result["status"] == "success":
            total_found += result["total_found"]
            total_downloaded += result["downloaded"]
            total_failed += result["failed"]
            print(
                f"✅ {result['total_found']} laws "
                f"({result['downloaded']} downloaded, {result['failed']} failed)"
            )
        elif result["status"] == "empty":
            print("⚠️  0 laws found")
        elif result["status"] == "dry_run":
            print("(dry run)")
        else:
            print(f"❌ {result.get('error', 'unknown')[:60]}")

        # Save per-city catalog
        if result["laws"]:
            city_dir = OUTPUT_DIR / city_key
            city_dir.mkdir(parents=True, exist_ok=True)
            catalog_path = city_dir / f"{city_key}_catalog.json"
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "city": city_key,
                        "scrape_date": datetime.now().isoformat(),
                        "total_found": result["total_found"],
                        "laws": result["laws"],
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

        time.sleep(1)  # Rate limit between cities

    # Summary
    print(f"\n{'='*60}")
    print("EXPANSION SUMMARY")
    print(f"{'='*60}")
    print(f"Cities scraped:   {len(all_results)}")
    print(f"Total laws found: {total_found:,}")
    print(f"Downloaded:       {total_downloaded:,}")
    print(f"Failed:           {total_failed:,}")

    success_cities = [r for r in all_results if r["status"] == "success"]
    empty_cities = [r for r in all_results if r["status"] == "empty"]
    error_cities = [r for r in all_results if r["status"] == "error"]

    print(
        f"\nSuccessful: {len(success_cities)}, Empty: {len(empty_cities)}, Errors: {len(error_cities)}"
    )

    if error_cities:
        print("\nFailed cities:")
        for r in error_cities:
            print(f"  - {r['city']}: {r.get('error', '')[:80]}")

    # Save summary
    summary_path = OUTPUT_DIR / "tier2_expansion_summary.json"
    summary = {
        "expansion_date": datetime.now().isoformat(),
        "total_cities": len(all_results),
        "total_laws_found": total_found,
        "total_downloaded": total_downloaded,
        "total_failed": total_failed,
        "results": [{k: v for k, v in r.items() if k != "laws"} for r in all_results],
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nSummary saved to {summary_path}")

    if total_found > 0:
        print(
            f"\nNext step: run consolidation + ingestion:\n"
            f"  python scripts/scraping/consolidate_municipal_metadata.py\n"
            f"  python manage.py ingest_municipal_laws --all"
        )


if __name__ == "__main__":
    main()
