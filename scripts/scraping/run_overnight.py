#!/usr/bin/env python3
"""
Overnight Data Collection Orchestrator.

Launches 6 parallel data collection jobs and monitors them to completion.
Jobs 1-5 run in parallel; Job 6 (NOM PDF download) starts after Job 1 completes.

Usage:
    nohup poetry run python scripts/scraping/run_overnight.py > logs/overnight_master.log 2>&1 &

    # Check progress:
    tail -f logs/overnight_master.log
    tail -5 logs/overnight_*.log
"""

import json
import logging
import os
import subprocess
import sys
import time
import urllib3
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
SCRIPTS_DIR = PROJECT_ROOT / "scripts" / "scraping"
DATA_DIR = PROJECT_ROOT / "data"

sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("overnight")


# ---------------------------------------------------------------------------
# Job definitions
# ---------------------------------------------------------------------------

def launch_subprocess(script_name, log_name, extra_args=None):
    """Launch a Python script as a subprocess with output to log file."""
    script_path = SCRIPTS_DIR / script_name
    log_path = LOGS_DIR / log_name

    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)

    log_file = open(log_path, "w")
    proc = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    return proc, log_file, log_path


def run_cdmx_retry():
    """Job 3: Retry CDMX municipal scraper with SSL disabled."""
    logger.info("[Job 3] CDMX retry starting")
    try:
        from apps.scraper.municipal.generic import GenericMunicipalScraper

        scraper = GenericMunicipalScraper("cdmx")
        scraper.session.verify = False
        scraper.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })

        catalog = scraper.scrape_catalog()
        logger.info("[Job 3] CDMX catalog: %d items", len(catalog))

        if not catalog:
            logger.info("[Job 3] CDMX returned no items")
            return 0

        # Download discovered items
        output_dir = DATA_DIR / "municipal" / "cdmx"
        output_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0
        for item in catalog:
            url = item.get("url", "")
            if not url:
                continue
            try:
                result = scraper.download_law_content(url, str(output_dir))
                if result:
                    downloaded += 1
            except Exception as e:
                logger.warning("[Job 3] Download failed %s: %s", url[:80], e)

        # Save metadata
        meta_path = output_dir / "cdmx_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)

        logger.info("[Job 3] CDMX complete: %d/%d downloaded", downloaded, len(catalog))
        return downloaded

    except Exception as e:
        logger.error("[Job 3] CDMX failed: %s", e)
        return 0


def run_municipal_retry():
    """Job 4: Retry all failed municipal cities with SSL disabled + Chrome UA."""
    logger.info("[Job 4] Municipal retry sweep starting")

    # Cities that returned 0 in previous probes (excluding already-downloaded and blocked)
    already_done = {"guadalajara", "monterrey", "leon", "zapopan", "merida", "cdmx"}
    blocked = set()  # merida is in already_done

    from apps.scraper.municipal.config import MUNICIPALITY_CONFIGS
    from apps.scraper.municipal.generic import GenericMunicipalScraper

    retry_cities = [k for k in MUNICIPALITY_CONFIGS if k not in already_done and k not in blocked]
    logger.info("[Job 4] Retrying %d cities: %s", len(retry_cities), retry_cities)

    total_items = 0
    for city_key in retry_cities:
        try:
            scraper = GenericMunicipalScraper(city_key)
            scraper.session.verify = False
            scraper.session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            })

            catalog = scraper.scrape_catalog()
            if not catalog:
                logger.info("[Job 4] %s: 0 items", city_key)
                continue

            logger.info("[Job 4] %s: %d items found!", city_key, len(catalog))

            # Download
            output_dir = DATA_DIR / "municipal" / city_key
            output_dir.mkdir(parents=True, exist_ok=True)

            downloaded = 0
            for item in catalog:
                url = item.get("url", "")
                if not url:
                    continue
                try:
                    result = scraper.download_law_content(url, str(output_dir))
                    if result:
                        downloaded += 1
                except Exception as e:
                    logger.warning("[Job 4] %s download fail: %s", city_key, e)

            # Save metadata
            meta_path = output_dir / f"{city_key}_metadata.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(catalog, f, indent=2, ensure_ascii=False)

            total_items += downloaded
            logger.info("[Job 4] %s: %d/%d downloaded", city_key, downloaded, len(catalog))

        except Exception as e:
            logger.error("[Job 4] %s failed: %s", city_key, e)

    logger.info("[Job 4] Municipal retry complete: %d total items", total_items)
    return total_items


def run_nom_pdf_download():
    """Job 6: Download actual PDF documents for cataloged NOMs."""
    logger.info("[Job 6] NOM PDF download starting")

    noms_path = DATA_DIR / "federal" / "noms" / "discovered_noms.json"
    if not noms_path.exists():
        logger.error("[Job 6] No discovered_noms.json found")
        return 0

    with open(noms_path, "r", encoding="utf-8") as f:
        noms = json.load(f)

    logger.info("[Job 6] %d NOMs to process", len(noms))

    pdf_dir = DATA_DIR / "federal" / "noms" / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    import requests
    from bs4 import BeautifulSoup

    session = requests.Session()
    session.verify = False
    session.headers.update({
        "User-Agent": "Tezca/1.0 (+https://github.com/madfam-org/tezca)",
        "Accept": "text/html, application/xhtml+xml, */*",
    })

    downloaded = 0
    skipped = 0
    failed = 0

    for i, nom in enumerate(noms, 1):
        nom_number = nom.get("nom_number", "unknown")
        detail_url = nom.get("url", "")

        if not detail_url:
            continue

        # Check if already downloaded
        safe_name = nom_number.replace("/", "_").replace(" ", "_")
        pdf_path = pdf_dir / f"{safe_name}.pdf"
        if pdf_path.exists() and pdf_path.stat().st_size > 1024:
            skipped += 1
            continue

        if i % 20 == 0:
            logger.info("[Job 6] Progress: %d/%d (%d downloaded, %d skipped)", i, len(noms), downloaded, skipped)

        try:
            # Fetch detail page
            time.sleep(1.0)
            resp = session.get(detail_url, timeout=30)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for PDF links on the detail page
            pdf_url = None
            for link in soup.find_all("a", href=True):
                href = link["href"].lower()
                if "nota_to_doc" in href or href.endswith(".pdf"):
                    pdf_url = link["href"]
                    if not pdf_url.startswith("http"):
                        pdf_url = f"https://dof.gob.mx/{pdf_url.lstrip('/')}"
                    break

            if not pdf_url:
                # Try nota_to_doc.php with the same codigo
                import re
                code_match = re.search(r"codigo=(\d+)", detail_url)
                if code_match:
                    pdf_url = f"https://dof.gob.mx/nota_to_doc.php?codnota={code_match.group(1)}"

            if pdf_url:
                time.sleep(1.0)
                pdf_resp = session.get(pdf_url, timeout=60)
                if pdf_resp.status_code == 200 and len(pdf_resp.content) > 1024:
                    # Verify it looks like a PDF or DOC
                    content_type = pdf_resp.headers.get("Content-Type", "")
                    if "pdf" in content_type or "octet" in content_type or pdf_resp.content[:4] == b"%PDF":
                        pdf_path.write_bytes(pdf_resp.content)
                        downloaded += 1
                    else:
                        # Save as HTML if that's what we got
                        html_path = pdf_dir / f"{safe_name}.html"
                        html_path.write_bytes(pdf_resp.content)
                        downloaded += 1
                else:
                    failed += 1
            else:
                failed += 1

        except Exception as e:
            logger.warning("[Job 6] Failed %s: %s", nom_number, e)
            failed += 1

    logger.info("[Job 6] NOM PDF download complete: %d downloaded, %d skipped, %d failed", downloaded, skipped, failed)
    return downloaded


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def main():
    start = time.time()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info("OVERNIGHT DATA COLLECTION ORCHESTRATOR")
    logger.info("Started: %s", time.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 70)

    # Launch subprocess jobs
    jobs = {}

    # Job 1: Exhaustive NOM search (subprocess)
    logger.info("Launching Job 1: Exhaustive NOM search")
    proc1, log1, logpath1 = launch_subprocess("run_overnight_noms.py", "overnight_noms.log")
    jobs["nom_search"] = {"proc": proc1, "log": log1, "logpath": logpath1, "start": time.time()}

    # Job 2: SCJN probe + scrape (subprocess)
    logger.info("Launching Job 2: SCJN probe + scrape")
    proc2, log2, logpath2 = launch_subprocess("run_overnight_scjn.py", "overnight_scjn.log")
    jobs["scjn"] = {"proc": proc2, "log": log2, "logpath": logpath2, "start": time.time()}

    # Job 5: OCR recovery (subprocess — CPU-bound)
    logger.info("Launching Job 5: OCR recovery")
    proc5, log5, logpath5 = launch_subprocess("run_overnight_ocr.py", "overnight_ocr.log")
    jobs["ocr"] = {"proc": proc5, "log": log5, "logpath": logpath5, "start": time.time()}

    # Jobs 3 & 4 run in-process (lightweight, share imports)
    logger.info("Running Job 3: CDMX retry (in-process)")
    cdmx_start = time.time()
    cdmx_count = run_cdmx_retry()
    cdmx_elapsed = time.time() - cdmx_start
    logger.info("Job 3 done: %d items in %.1f min", cdmx_count, cdmx_elapsed / 60)

    logger.info("Running Job 4: Municipal retry sweep (in-process)")
    muni_start = time.time()
    muni_count = run_municipal_retry()
    muni_elapsed = time.time() - muni_start
    logger.info("Job 4 done: %d items in %.1f min", muni_count, muni_elapsed / 60)

    # Wait for Job 1 to complete before starting Job 6
    logger.info("Waiting for Job 1 (NOM search) to complete before launching Job 6...")
    proc1.wait()
    jobs["nom_search"]["log"].close()
    nom_elapsed = time.time() - jobs["nom_search"]["start"]
    logger.info("Job 1 (NOM search) completed in %.1f min (exit code: %d)", nom_elapsed / 60, proc1.returncode)

    # Job 6: NOM PDF download (depends on Job 1)
    logger.info("Launching Job 6: NOM PDF download (in-process)")
    pdf_start = time.time()
    pdf_count = run_nom_pdf_download()
    pdf_elapsed = time.time() - pdf_start
    logger.info("Job 6 done: %d PDFs in %.1f min", pdf_count, pdf_elapsed / 60)

    # Wait for remaining subprocess jobs
    for name in ["scjn", "ocr"]:
        job = jobs[name]
        if job["proc"].poll() is None:
            logger.info("Waiting for %s to complete...", name)
        job["proc"].wait()
        job["log"].close()
        elapsed = time.time() - job["start"]
        logger.info(
            "%s completed in %.1f min (exit code: %d)",
            name, elapsed / 60, job["proc"].returncode,
        )

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    total_elapsed = time.time() - start
    logger.info("")
    logger.info("=" * 70)
    logger.info("OVERNIGHT COLLECTION COMPLETE")
    logger.info("=" * 70)
    logger.info("Total duration: %.1f hours", total_elapsed / 3600)
    logger.info("")
    logger.info("Job 1 (NOM search):        exit=%d  log=%s", proc1.returncode, jobs["nom_search"]["logpath"])
    logger.info("Job 2 (SCJN):              exit=%d  log=%s", jobs["scjn"]["proc"].returncode, jobs["scjn"]["logpath"])
    logger.info("Job 3 (CDMX):              %d items", cdmx_count)
    logger.info("Job 4 (Municipal retry):    %d items", muni_count)
    logger.info("Job 5 (OCR recovery):       exit=%d  log=%s", jobs["ocr"]["proc"].returncode, jobs["ocr"]["logpath"])
    logger.info("Job 6 (NOM PDFs):           %d PDFs", pdf_count)
    logger.info("")

    # Quick data summary
    try:
        noms_path = DATA_DIR / "federal" / "noms" / "discovered_noms.json"
        if noms_path.exists():
            noms = json.load(open(noms_path))
            logger.info("NOMs cataloged: %d", len(noms))

        nom_pdfs = list((DATA_DIR / "federal" / "noms" / "pdfs").glob("*")) if (DATA_DIR / "federal" / "noms" / "pdfs").exists() else []
        logger.info("NOM PDFs: %d", len(nom_pdfs))

        scjn_batches = list((DATA_DIR / "judicial").glob("batch_*.json")) if (DATA_DIR / "judicial").exists() else []
        logger.info("SCJN batches: %d", len(scjn_batches))

        cdmx_files = list((DATA_DIR / "municipal" / "cdmx").glob("*")) if (DATA_DIR / "municipal" / "cdmx").exists() else []
        logger.info("CDMX files: %d", len(cdmx_files))
    except Exception as e:
        logger.warning("Summary data count failed: %s", e)

    logger.info("=" * 70)
    logger.info("Check detailed logs: tail -5 logs/overnight_*.log")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
