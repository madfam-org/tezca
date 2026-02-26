#!/usr/bin/env python3
"""
CDMX State Integration Script

Bridges CDMXScraper output into data/state_laws/ciudad_de_méxico/ using
OJN-compatible metadata format so consolidate_state_metadata.py picks it up.

CDMX is not in OJN — it has its own portal. This script:
1. Runs CDMXScraper.scrape_catalog() to discover laws
2. Downloads each PDF to data/state_laws/ciudad_de_méxico/
3. Writes ciudad_de_méxico_metadata.json in OJN format

Usage:
    python scripts/scraping/scrape_cdmx_state.py
    python scripts/scraping/scrape_cdmx_state.py --limit 5  # for testing
    python scripts/scraping/scrape_cdmx_state.py --dry-run
"""

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.scraper.http import government_session

from apps.scraper.municipal.cdmx import CDMXScraper

STATE_LAWS_DIR = PROJECT_ROOT / "data" / "state_laws"
CDMX_DIR = STATE_LAWS_DIR / "ciudad_de_méxico"


def url_to_file_id(url):
    """Generate a stable integer file_id from a URL hash."""
    return int(hashlib.sha256(url.encode()).hexdigest()[:8], 16)


def download_pdf(url, output_path, timeout=60):
    """Download a PDF with retry logic."""
    session = government_session(url)
    for attempt in range(3):
        try:
            time.sleep(1.0)  # Rate limiting
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            return True
        except requests.RequestException as e:
            print(f"   ⚠️  Download attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    return False


def main():
    parser = argparse.ArgumentParser(description="Scrape CDMX laws into state format")
    parser.add_argument("--limit", type=int, help="Limit number of laws")
    parser.add_argument("--dry-run", action="store_true", help="List catalog only")
    args = parser.parse_args()

    print("🏛️  CDMX State Integration")
    print("=" * 70)

    # 1. Scrape catalog
    print("📥 Running CDMXScraper.scrape_catalog()...")
    scraper = CDMXScraper()
    catalog = scraper.scrape_catalog()

    if not catalog:
        print("❌ No laws found in CDMX catalog")
        sys.exit(1)

    print(f"✅ Found {len(catalog)} laws in CDMX portal")

    if args.limit:
        catalog = catalog[: args.limit]
        print(f"⚠️  Limited to {args.limit} laws")

    if args.dry_run:
        print("\n[DRY RUN] First 5 entries:")
        for entry in catalog[:5]:
            print(f"  - {entry.get('name', 'Unknown')[:60]}")
            print(f"    URL: {entry.get('url', 'N/A')}")
        sys.exit(0)

    # 2. Download and build metadata
    CDMX_DIR.mkdir(parents=True, exist_ok=True)

    results = {
        "state_id": 9,
        "state_name": "Ciudad de México",
        "total_found": len(catalog),
        "successful": 0,
        "failed": 0,
        "laws": [],
        "failed_laws": [],
    }

    for i, entry in enumerate(catalog, 1):
        name = entry.get("name", "Unknown")
        url = entry.get("url", "")

        print(f"\n[{i}/{len(catalog)}] {name[:60]}...")

        if not url:
            print("   ⚠️  No URL")
            results["failed"] += 1
            results["failed_laws"].append(
                {
                    "file_id": 0,
                    "law_name": name,
                    "failure_reason": "no_download_url",
                    "download_url": "",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            continue

        file_id = url_to_file_id(url)

        # Safe filename
        safe_name = re.sub(r"[^\w\s-]", "", name)[:100]
        safe_name = safe_name.replace(" ", "_").lower()
        file_path = CDMX_DIR / f"{safe_name}_{file_id}.pdf"

        if download_pdf(url, file_path):
            metadata = {
                "file_id": file_id,
                "ambito": "ESTATAL",
                "url": url,
                "download_url": url,
                "format": "pdf",
                "local_path": str(file_path),
                "law_name": name,
            }
            results["successful"] += 1
            results["laws"].append(metadata)
            print(f"   ✅ Saved: {file_path.name}")
        else:
            results["failed"] += 1
            results["failed_laws"].append(
                {
                    "file_id": file_id,
                    "law_name": name,
                    "failure_reason": "download_failed",
                    "download_url": url,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    # 3. Write metadata
    metadata_file = CDMX_DIR / "ciudad_de_méxico_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*70}")
    print("✅ CDMX State Integration Complete")
    print(f"   Found: {results['total_found']}")
    print(f"   Downloaded: {results['successful']}")
    print(f"   Failed: {results['failed']}")
    print(f"   Metadata: {metadata_file}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
