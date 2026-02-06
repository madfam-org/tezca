#!/usr/bin/env python3
"""
Tier-1 City Scraper Runner

Runs all 6 registered municipal scrapers: CDMX, Guadalajara, Monterrey,
Puebla, Tijuana, León.

Best effort — stubs may return 0 results, that's expected.
Each city is wrapped in try/except so failures don't stop the rest.

Output: data/municipal_laws/<city>/<city>_catalog.json
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.scraper.municipal import SCRAPERS, get_scraper

MUNICIPAL_DIR = PROJECT_ROOT / "data" / "municipal_laws"


def download_pdf(url, output_path, session=None, timeout=60):
    """Download a document with retry logic."""
    # Skip if file already exists and is valid (>1KB)
    if output_path.exists() and output_path.stat().st_size > 1024:
        return True

    session = session or requests.Session()
    for attempt in range(3):
        try:
            time.sleep(1.0)
            response = session.get(url, timeout=timeout, verify=False)
            response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            return True
        except requests.RequestException as e:
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    return False


def scrape_city(muni_id, limit=None):
    """Scrape a single city and return results dict."""
    print(f"\n🏙️  Scraping: {muni_id.upper()}")

    try:
        scraper = get_scraper(muni_id)
    except Exception as e:
        print(f"   ❌ Failed to load scraper: {e}")
        return {"city": muni_id, "error": str(e), "found": 0, "downloaded": 0}

    try:
        catalog = scraper.scrape_catalog()
    except Exception as e:
        print(f"   ❌ Scrape failed: {e}")
        return {"city": muni_id, "error": str(e), "found": 0, "downloaded": 0}

    if not catalog:
        print(f"   ⚠️  No laws found (stub scraper?)")
        return {"city": muni_id, "found": 0, "downloaded": 0}

    print(f"   ✅ Found {len(catalog)} laws")

    if limit:
        catalog = catalog[:limit]

    city_dir = MUNICIPAL_DIR / muni_id
    city_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    laws = []
    failed_laws = []

    for i, entry in enumerate(catalog, 1):
        name = entry.get("name", "Unknown")
        url = entry.get("url", "")

        if not url:
            failed_laws.append(
                {
                    "law_name": name,
                    "failure_reason": "no_url",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            continue

        # Safe filename
        safe_name = re.sub(r"[^\w\s-]", "", name)[:80]
        safe_name = safe_name.replace(" ", "_").lower()
        file_path = city_dir / f"{safe_name}.pdf"

        # Log skip for already-existing files
        if file_path.exists() and file_path.stat().st_size > 1024:
            print(f"   ⏭️  [{i}/{len(catalog)}] Already exists: {file_path.name}")

        if download_pdf(url, file_path, session=scraper.session):
            laws.append(
                {
                    "name": name,
                    "url": url,
                    "local_path": str(file_path),
                    "municipality": muni_id,
                }
            )
            downloaded += 1
        else:
            failed_laws.append(
                {
                    "law_name": name,
                    "failure_reason": "download_failed",
                    "download_url": url,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    # Save catalog
    catalog_file = city_dir / f"{muni_id}_catalog.json"
    catalog_data = {
        "city": muni_id,
        "scrape_date": datetime.now().isoformat(),
        "total_found": len(catalog),
        "downloaded": downloaded,
        "failed": len(failed_laws),
        "laws": laws,
        "failed_laws": failed_laws,
    }

    with open(catalog_file, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, indent=2, ensure_ascii=False)

    print(f"   📊 Downloaded: {downloaded}/{len(catalog)}")
    print(f"   💾 Catalog: {catalog_file}")

    return {
        "city": muni_id,
        "found": len(catalog),
        "downloaded": downloaded,
        "failed": len(failed_laws),
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape tier-1 cities")
    parser.add_argument("--limit", type=int, help="Limit per city")
    parser.add_argument("--city", type=str, help="Scrape specific city only")
    args = parser.parse_args()

    print("🏙️  TIER-1 CITY SCRAPER RUNNER")
    print("=" * 70)
    print(f"Registered scrapers: {', '.join(SCRAPERS.keys())}")
    print(f"Start: {datetime.now().isoformat()}")
    print("=" * 70)

    MUNICIPAL_DIR.mkdir(parents=True, exist_ok=True)

    cities = [args.city] if args.city else list(SCRAPERS.keys())
    results = []

    for muni_id in cities:
        try:
            result = scrape_city(muni_id, limit=args.limit)
            results.append(result)
        except Exception as e:
            print(f"   ❌ {muni_id} crashed: {e}")
            results.append(
                {"city": muni_id, "error": str(e), "found": 0, "downloaded": 0}
            )

    # Summary
    summary = {
        "scrape_date": datetime.now().isoformat(),
        "cities_attempted": len(cities),
        "results": results,
        "total_found": sum(r.get("found", 0) for r in results),
        "total_downloaded": sum(r.get("downloaded", 0) for r in results),
    }

    summary_file = MUNICIPAL_DIR / "tier1_scraping_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print("📊 TIER-1 CITY SCRAPING SUMMARY")
    print(f"{'='*70}")
    for r in results:
        status = "✅" if r.get("downloaded", 0) > 0 else "⚠️"
        err = f" (error: {r['error'][:40]})" if "error" in r else ""
        print(
            f"  {status} {r['city']:15s} "
            f"found={r.get('found', 0):4d} "
            f"downloaded={r.get('downloaded', 0):4d}{err}"
        )
    print(
        f"\nTotal: {summary['total_found']} found, {summary['total_downloaded']} downloaded"
    )
    print(f"Summary: {summary_file}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
