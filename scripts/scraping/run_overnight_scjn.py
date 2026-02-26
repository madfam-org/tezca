#!/usr/bin/env python3
"""
SCJN Open Data Probe + Fallback Scrape.

Phase A: Probe datos.scjn.gob.mx and sjf.scjn.gob.mx for APIs/bulk data.
Phase B: If search endpoint found, scrape iteratively overnight.
Phase C: If bulk download URLs found, fetch them.

Usage:
    poetry run python scripts/scraping/run_overnight_scjn.py
"""

import json
import logging
import sys
import time
import urllib3
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.scraper.judicial.scjn_scraper import ScjnScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = PROJECT_ROOT / "data" / "judicial"
PROBE_PATH = OUTPUT_DIR / "probe_results.json"
BULK_DIR = OUTPUT_DIR / "bulk"
BATCH_SIZE = 50


def save_json(path, data):
    """Save JSON to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def phase_a_probe(scraper):
    """Probe for open data and search APIs."""
    logger.info("=== Phase A: Probing SCJN portals ===")

    probe_results = {
        "open_data": None,
        "search_api": None,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    # 1. Probe open data portal
    logger.info("Probing datos.scjn.gob.mx...")
    try:
        open_data = scraper.check_open_data()
        probe_results["open_data"] = open_data
        if open_data["found"]:
            logger.info("Open data FOUND: %s", open_data["endpoint"])
            logger.info("  Datasets: %d", len(open_data.get("datasets", [])))
            logger.info("  Downloads: %d", len(open_data.get("download_urls", [])))
        else:
            logger.info("No open data found (probed %d paths)", len(open_data.get("probed", [])))
    except Exception as e:
        logger.error("Open data probe failed: %s", e)
        probe_results["open_data"] = {"found": False, "error": str(e)}

    # 2. Probe search API
    logger.info("Probing sjf.scjn.gob.mx search API...")
    try:
        search_api = scraper.probe_search_api()
        probe_results["search_api"] = search_api
        if search_api["found"]:
            logger.info("Search API FOUND: %s", search_api["endpoint"])
        elif search_api.get("search_form"):
            logger.info("HTML search form found: %s", search_api["search_form"].get("action"))
        else:
            logger.info("No search API found (probed %d paths)", len(search_api.get("probed", [])))
    except Exception as e:
        logger.error("Search API probe failed: %s", e)
        probe_results["search_api"] = {"found": False, "error": str(e)}

    save_json(PROBE_PATH, probe_results)
    logger.info("Probe results saved to %s", PROBE_PATH)
    return probe_results


def phase_b_scrape(scraper):
    """Scrape iteratively if search endpoint was found."""
    logger.info("=== Phase B: Iterative Scrape ===")

    # Count existing batches for resume support
    existing_batches = sorted(OUTPUT_DIR.glob("batch_*.json"))
    resume_from = len(existing_batches) * BATCH_SIZE
    if resume_from > 0:
        logger.info("Resuming from item %d (%d batches exist)", resume_from, len(existing_batches))

    total_items = 0
    batch_num = len(existing_batches)

    # Scrape jurisprudencia first, then tesis aisladas
    for tipo, generator_fn in [
        ("jurisprudencia", scraper.scrape_jurisprudencia),
        ("tesis_aislada", scraper.scrape_tesis_aisladas),
    ]:
        logger.info("Scraping %s...", tipo)
        tipo_items = 0

        try:
            for batch in generator_fn(epoca=10, resume_from=0):
                batch_num += 1
                batch_path = OUTPUT_DIR / f"batch_{batch_num:04d}.json"

                if batch_path.exists():
                    logger.info("Batch %d already exists, skipping", batch_num)
                    continue

                save_json(batch_path, {
                    "tipo": tipo,
                    "batch_num": batch_num,
                    "count": len(batch),
                    "items": batch,
                })

                tipo_items += len(batch)
                total_items += len(batch)
                logger.info(
                    "Batch %d: %d items (%s total: %d, overall: %d)",
                    batch_num, len(batch), tipo, tipo_items, total_items,
                )

        except Exception as e:
            logger.error("Scrape error for %s: %s", tipo, e)

        logger.info("%s complete: %d items", tipo, tipo_items)

    logger.info("Phase B complete: %d total items in %d batches", total_items, batch_num)
    return total_items


def phase_c_bulk_download(scraper, probe_results):
    """Download bulk data files if found."""
    open_data = probe_results.get("open_data", {})
    download_urls = open_data.get("download_urls", [])

    if not download_urls:
        logger.info("=== Phase C: No bulk downloads available ===")
        return 0

    logger.info("=== Phase C: Downloading %d bulk files ===", len(download_urls))
    BULK_DIR.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    for url in download_urls:
        filename = url.split("/")[-1] or f"bulk_{downloaded}.dat"
        filepath = BULK_DIR / filename

        if filepath.exists():
            logger.info("Already downloaded: %s", filename)
            downloaded += 1
            continue

        logger.info("Downloading: %s", url)
        try:
            resp = scraper._get(url)
            if resp is not None:
                filepath.write_bytes(resp.content)
                size_mb = len(resp.content) / (1024 * 1024)
                logger.info("Saved %s (%.1f MB)", filename, size_mb)
                downloaded += 1
            else:
                logger.warning("Failed to download: %s", url)
        except Exception as e:
            logger.error("Download error for %s: %s", url, e)

    logger.info("Phase C complete: %d/%d files downloaded", downloaded, len(download_urls))
    return downloaded


def main():
    start = time.time()
    logger.info("=== SCJN Overnight Scrape Starting ===")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    scraper = ScjnScraper()
    # Disable SSL verification for government sites
    scraper.session.verify = False

    # Phase A: Probe
    probe_results = phase_a_probe(scraper)

    # Phase B: Scrape if API found
    has_search = (
        probe_results.get("search_api", {}).get("found", False)
        or probe_results.get("search_api", {}).get("search_form") is not None
    )

    total_scraped = 0
    if has_search:
        total_scraped = phase_b_scrape(scraper)
    else:
        logger.info("No search endpoint found, skipping Phase B")
        # Still try HTML scraping — the scraper falls back to HTML automatically
        logger.info("Attempting HTML fallback scrape...")
        total_scraped = phase_b_scrape(scraper)

    # Phase C: Bulk downloads
    total_bulk = phase_c_bulk_download(scraper, probe_results)

    elapsed = time.time() - start
    logger.info("=== SCJN Overnight Scrape Complete ===")
    logger.info("Scraped items: %d", total_scraped)
    logger.info("Bulk files: %d", total_bulk)
    logger.info("Duration: %.1f minutes", elapsed / 60)


if __name__ == "__main__":
    main()
