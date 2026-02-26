#!/usr/bin/env python3
"""
Download municipal regulatory documents from responsive city portals.

Usage:
    python scripts/scraping/scrape_municipal.py --city guadalajara
    python scripts/scraping/scrape_municipal.py --city all
    python scripts/scraping/scrape_municipal.py --city all --catalog-only
"""

import argparse
import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.scraper.http import government_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Cities that responded with items in probe
RESPONSIVE_CITIES = ["guadalajara", "monterrey", "leon", "zapopan", "merida"]


def _file_id(url: str) -> str:
    """Generate a stable file ID from URL."""
    h = hashlib.md5(url.encode()).hexdigest()[:10]
    return f"muni_{h}"


def _filename_from_url(url: str) -> str:
    """Extract a clean filename from URL."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    name = path.split("/")[-1]
    if not name:
        name = "document"
    name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in name)
    if len(name) > 120:
        name = name[:120]
    return name


def download_city(city_key: str, catalog_only: bool = False, resume: bool = True):
    """Download all regulatory documents for a city."""
    from apps.scraper.municipal.config import get_config
    from apps.scraper.municipal.generic import GenericMunicipalScraper

    config = get_config(city_key)
    logger.info("=== %s (%s) ===", config["name"], config["state"])

    scraper = GenericMunicipalScraper(city_key)
    scraper.session = government_session(config.get("base_url", ""))

    catalog = scraper.scrape_catalog()
    logger.info("[%s] Catalog: %d items", city_key, len(catalog))

    if not catalog:
        return {
            "city": city_key,
            "found": 0,
            "downloaded": 0,
            "failed": 0,
            "skipped": 0,
        }

    out_dir = PROJECT_ROOT / "data" / "municipal" / city_key
    out_dir.mkdir(parents=True, exist_ok=True)

    if catalog_only:
        cat_path = out_dir / "catalog.json"
        with open(cat_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
        logger.info("[%s] Catalog saved to %s", city_key, cat_path)
        return {
            "city": city_key,
            "found": len(catalog),
            "downloaded": 0,
            "failed": 0,
            "skipped": 0,
        }

    laws = []
    failed_laws = []
    skipped = 0
    last_request = 0.0

    for i, item in enumerate(catalog):
        url = item.get("url", "")
        name = item.get("name", "unknown")
        fid = _file_id(url)

        parsed_path = urlparse(url).path.lower()
        if parsed_path.endswith(".pdf"):
            ext = "pdf"
        elif parsed_path.endswith(".doc"):
            ext = "doc"
        elif parsed_path.endswith(".docx"):
            ext = "docx"
        else:
            ext = "pdf"

        local_filename = f"{fid}.{ext}"
        local_path = out_dir / local_filename

        # Resume: skip if already downloaded
        if resume and local_path.exists() and local_path.stat().st_size > 100:
            skipped += 1
            laws.append(
                {
                    "file_id": fid,
                    "law_name": name,
                    "url": url,
                    "local_path": str(local_path),
                    "format": ext,
                    "category": item.get("category", "Otro"),
                    "municipality": item.get("municipality", config["name"]),
                    "state": item.get("state", config["state"]),
                    "law_type": "non-legislative",
                    "tier": "municipal",
                }
            )
            continue

        # Rate limit
        elapsed = time.time() - last_request
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        last_request = time.time()

        try:
            resp = scraper.session.get(url, timeout=60)
            resp.raise_for_status()

            ct = resp.headers.get("Content-Type", "")
            if ct.startswith("text/html") and ext == "pdf":
                if len(resp.content) < 500:
                    failed_laws.append(
                        {"law_name": name, "url": url, "error": "HTML response"}
                    )
                    continue

            local_path.write_bytes(resp.content)
            size_kb = len(resp.content) // 1024

            laws.append(
                {
                    "file_id": fid,
                    "law_name": name,
                    "url": url,
                    "local_path": str(local_path),
                    "format": ext,
                    "category": item.get("category", "Otro"),
                    "municipality": item.get("municipality", config["name"]),
                    "state": item.get("state", config["state"]),
                    "law_type": "non-legislative",
                    "tier": "municipal",
                }
            )

            if (i + 1) % 50 == 0 or i == len(catalog) - 1:
                logger.info(
                    "[%d/%d] %s (%dKB) | ok=%d skip=%d fail=%d",
                    i + 1,
                    len(catalog),
                    name[:40],
                    size_kb,
                    len(laws),
                    skipped,
                    len(failed_laws),
                )

        except Exception as e:
            failed_laws.append({"law_name": name, "url": url, "error": str(e)})
            if (i + 1) % 50 == 0:
                logger.warning(
                    "[%d/%d] Failed: %s - %s", i + 1, len(catalog), name[:40], e
                )

    # Write metadata
    metadata = {
        "municipality": config["name"],
        "state": config["state"],
        "city_key": city_key,
        "tier": config.get("tier", 2),
        "total_found": len(catalog),
        "successful": len(laws),
        "failed": len(failed_laws),
        "skipped": skipped,
        "laws": laws,
        "failed_laws": failed_laws,
    }
    meta_path = out_dir / f"{city_key}_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(
        "[%s] Complete: %d downloaded, %d skipped, %d failed (of %d)",
        city_key,
        len(laws) - skipped,
        skipped,
        len(failed_laws),
        len(catalog),
    )
    return {
        "city": city_key,
        "found": len(catalog),
        "downloaded": len(laws) - skipped,
        "skipped": skipped,
        "failed": len(failed_laws),
    }


def main():
    parser = argparse.ArgumentParser(description="Download municipal regulations")
    parser.add_argument(
        "--city", default="all", help="City key or 'all' for responsive cities"
    )
    parser.add_argument("--catalog-only", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    cities = RESPONSIVE_CITIES if args.city == "all" else [args.city]
    results = []

    for city in cities:
        try:
            result = download_city(
                city, catalog_only=args.catalog_only, resume=not args.no_resume
            )
            results.append(result)
        except Exception as e:
            logger.error("[%s] Fatal error: %s", city, e)
            results.append(
                {
                    "city": city,
                    "found": 0,
                    "downloaded": 0,
                    "failed": 0,
                    "error": str(e),
                }
            )

    print("\n" + "=" * 60)
    print("MUNICIPAL DOWNLOAD SUMMARY")
    print("=" * 60)
    total_found = total_dl = total_skip = total_fail = 0
    for r in results:
        print(
            f"  {r['city']:20s} | found={r['found']:4d} dl={r['downloaded']:4d} skip={r.get('skipped',0):4d} fail={r['failed']:4d}"
        )
        total_found += r["found"]
        total_dl += r["downloaded"]
        total_skip += r.get("skipped", 0)
        total_fail += r["failed"]
    print(
        f"  {'TOTAL':20s} | found={total_found:4d} dl={total_dl:4d} skip={total_skip:4d} fail={total_fail:4d}"
    )


if __name__ == "__main__":
    main()
