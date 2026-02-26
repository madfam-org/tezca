#!/usr/bin/env python3
"""
Bridge between new state congress scrapers and the existing OJN-format ingest pipeline.

New state scrapers return catalog dicts: {name, url, state, tier, category, law_type}
Existing pipeline expects OJN-format metadata: {file_id, law_name, url, local_path, format, ...}

This script:
1. Instantiates the scraper, calls scrape_catalog()
2. Downloads each file to data/state_laws/{state_key}/
3. Writes per-state _metadata.json in OJN format
4. Then existing pipeline works: consolidate → parse → ingest

Usage:
    # Catalog probe only (no downloads)
    python scripts/scraping/scrape_and_prepare.py --scraper baja_california --catalog-only

    # Full download with resume support
    python scripts/scraping/scrape_and_prepare.py --scraper baja_california --resume

    # All three gap states
    python scripts/scraping/scrape_and_prepare.py --scraper all
"""

import argparse
import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.scraper.state.baja_california import BajaCaliforniaScraper
from apps.scraper.state.durango import DurangoScraper
from apps.scraper.state.quintana_roo import QuintanaRooScraper

logger = logging.getLogger(__name__)

# Map scraper key → (class, state_key for directory, OJN-compatible state_id)
SCRAPERS = {
    "baja_california": (BajaCaliforniaScraper, "baja_california", "BC"),
    "durango": (DurangoScraper, "durango", "DGO"),
    "quintana_roo": (QuintanaRooScraper, "quintana_roo", "QR"),
}

# Existing OJN state_id mapping (numeric) — we use string IDs for new scrapers
# to avoid collisions with the OJN numeric IDs.
STATE_NAMES = {
    "baja_california": "Baja California",
    "durango": "Durango",
    "quintana_roo": "Quintana Roo",
}


def _file_id_from_url(url: str, index: int) -> str:
    """Generate a stable file_id from URL hash + index."""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"sc_{url_hash}_{index:04d}"


def _file_ext_from_url(url: str) -> str:
    """Extract file extension from URL, default to 'pdf'."""
    path = urlparse(url).path.lower()
    for ext in (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv"):
        if path.endswith(ext):
            return ext.lstrip(".")
    return "pdf"


def scrape_state(scraper_key: str, catalog_only: bool = False, resume: bool = False):
    """Run scraper for a single state and produce OJN-format metadata."""
    if scraper_key not in SCRAPERS:
        logger.error("Unknown scraper: %s (available: %s)", scraper_key, list(SCRAPERS))
        return None

    scraper_cls, state_key, state_id = SCRAPERS[scraper_key]
    state_name = STATE_NAMES[scraper_key]
    output_dir = PROJECT_ROOT / "data" / "state_laws" / state_key

    logger.info("=== Scraping %s ===", state_name)

    # Step 1: Get catalog
    scraper = scraper_cls()
    catalog = scraper.scrape_catalog()
    logger.info("Catalog: %d items from %s", len(catalog), state_name)

    if not catalog:
        logger.warning("No catalog items found for %s — portal may be down", state_name)
        return {"state": state_name, "catalog_size": 0, "downloaded": 0, "failed": 0}

    if catalog_only:
        print(f"\n{state_name}: {len(catalog)} catalog items found")
        for i, item in enumerate(catalog[:10]):
            ext = _file_ext_from_url(item["url"])
            print(f"  [{i+1}] {item['name'][:80]} ({ext}) - {item['url'][:80]}")
        if len(catalog) > 10:
            print(f"  ... and {len(catalog) - 10} more")
        return {
            "state": state_name,
            "catalog_size": len(catalog),
            "downloaded": 0,
            "failed": 0,
        }

    # Step 2: Download files and build OJN-format metadata
    output_dir.mkdir(parents=True, exist_ok=True)
    laws = []
    failed_laws = []
    downloaded = 0
    skipped = 0

    for i, item in enumerate(catalog):
        file_id = _file_id_from_url(item["url"], i)
        ext = _file_ext_from_url(item["url"])
        filename = f"{file_id}.{ext}"
        local_path = output_dir / filename

        # Resume: skip already-downloaded files
        if resume and local_path.exists() and local_path.stat().st_size > 0:
            skipped += 1
            laws.append(
                {
                    "file_id": file_id,
                    "law_name": item["name"],
                    "url": item["url"],
                    "local_path": str(local_path),
                    "format": ext,
                    "category": item.get("category", ""),
                    "law_type": item.get("law_type", ""),
                }
            )
            continue

        # Download via scraper's built-in download (has rate limiting)
        logger.info("[%d/%d] Downloading: %s", i + 1, len(catalog), item["name"][:60])
        result = scraper.download_file(item["url"], str(output_dir))

        if result:
            # Rename to our standard filename
            downloaded_path = Path(result["file_path"])
            if downloaded_path.exists() and downloaded_path != local_path:
                downloaded_path.rename(local_path)

            laws.append(
                {
                    "file_id": file_id,
                    "law_name": item["name"],
                    "url": item["url"],
                    "local_path": str(local_path),
                    "format": ext,
                    "category": item.get("category", ""),
                    "law_type": item.get("law_type", ""),
                }
            )
            downloaded += 1
        else:
            failed_laws.append(
                {
                    "law_name": item["name"],
                    "url": item["url"],
                    "error": "Download failed",
                    "retry_result": "pending",
                }
            )

        if (i + 1) % 50 == 0:
            logger.info(
                "Progress: %d/%d (downloaded=%d, skipped=%d, failed=%d)",
                i + 1,
                len(catalog),
                downloaded,
                skipped,
                len(failed_laws),
            )

    # Step 3: Write OJN-format metadata
    metadata = {
        "state_name": state_name,
        "state_id": state_id,
        "total_found": len(catalog),
        "successful": len(laws),
        "failed": len(failed_laws),
        "laws": laws,
        "failed_laws": failed_laws,
    }

    # Use the same naming convention as existing metadata files
    metadata_path = output_dir / f"{state_name.lower()}_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(
        "%s complete: %d downloaded, %d skipped, %d failed → %s",
        state_name,
        downloaded,
        skipped,
        len(failed_laws),
        metadata_path,
    )

    return {
        "state": state_name,
        "catalog_size": len(catalog),
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": len(failed_laws),
        "metadata_path": str(metadata_path),
    }


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Bridge state congress scrapers to OJN-format ingest pipeline",
    )
    parser.add_argument(
        "--scraper",
        type=str,
        required=True,
        choices=list(SCRAPERS) + ["all"],
        help="Which state scraper to run (or 'all' for all gap states)",
    )
    parser.add_argument(
        "--catalog-only",
        action="store_true",
        help="Only probe the catalog, don't download files",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip already-downloaded files",
    )
    args = parser.parse_args()

    scrapers_to_run = list(SCRAPERS) if args.scraper == "all" else [args.scraper]
    results = []

    for key in scrapers_to_run:
        result = scrape_state(key, catalog_only=args.catalog_only, resume=args.resume)
        if result:
            results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("SCRAPING SUMMARY")
    print("=" * 60)
    for r in results:
        print(
            f"  {r['state']}: catalog={r['catalog_size']}, "
            f"downloaded={r.get('downloaded', 0)}, "
            f"skipped={r.get('skipped', 0)}, "
            f"failed={r.get('failed', 0)}"
        )
    print("=" * 60)


if __name__ == "__main__":
    main()
