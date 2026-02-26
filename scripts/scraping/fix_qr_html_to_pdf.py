#!/usr/bin/env python3
"""
Fix Quintana Roo scraper output: extract actual PDF URLs from HTML pages
and download the real law PDFs.

The QR congress portal serves HTML law pages at /leyes/NNN/, not direct PDFs.
Each page contains links to the actual PDF files at documentos.congresoqroo.gob.mx.

Usage:
    python scripts/scraping/fix_qr_html_to_pdf.py
    python scripts/scraping/fix_qr_html_to_pdf.py --dry-run
"""

import json
import logging
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def setup_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=3, backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; TezcaBot/1.0; +https://leyes.mx)",
    })
    return session


def extract_pdf_url(html_path: Path) -> str | None:
    """Extract the first law PDF URL from a QR HTML law page."""
    try:
        html = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    if not html.startswith("\n<!DOCTYPE") and not html.startswith("<!DOCTYPE"):
        return None  # Already a real PDF

    soup = BeautifulSoup(html, "html.parser")

    # Strategy 1: Look for "Click para abrir el archivo de Ley" links
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        href = a["href"].strip()
        if "click para abrir" in text and href.endswith(".pdf"):
            return href

    # Strategy 2: Any PDF link from documentos.congresoqroo.gob.mx
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "documentos.congresoqroo.gob.mx" in href and href.endswith(".pdf"):
            return href

    # Strategy 3: Any .pdf link
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.endswith(".pdf") and len(href) > 20:
            return href

    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix QR HTML files to actual PDFs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    qr_dir = PROJECT_ROOT / "data" / "state_laws" / "quintana_roo"
    meta_path = qr_dir / "quintana roo_metadata.json"

    if not meta_path.exists():
        logger.error("Metadata not found: %s", meta_path)
        return

    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    laws = metadata.get("laws", [])

    session = setup_session()
    last_request_time = 0.0
    fixed = 0
    failed = 0
    skipped = 0

    for i, law in enumerate(laws):
        local_path = Path(law.get("local_path", ""))
        if not local_path.exists():
            logger.warning("[%d] File not found: %s", i, local_path)
            failed += 1
            continue

        # Check if already a real PDF
        with open(local_path, "rb") as f:
            header = f.read(10)
        if header.startswith(b"%PDF"):
            skipped += 1
            continue

        # Extract PDF URL from HTML
        pdf_url = extract_pdf_url(local_path)
        if not pdf_url:
            logger.warning("[%d] No PDF URL found in %s", i, local_path.name)
            failed += 1
            continue

        if args.dry_run:
            logger.info("[%d] Would download: %s", i, pdf_url[:80])
            fixed += 1
            continue

        # Rate limit
        elapsed = time.time() - last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        last_request_time = time.time()

        # Download real PDF
        try:
            resp = session.get(pdf_url, timeout=60)
            resp.raise_for_status()

            if resp.headers.get("Content-Type", "").startswith("text/html"):
                logger.warning("[%d] Got HTML instead of PDF: %s", i, pdf_url[:60])
                failed += 1
                continue

            local_path.write_bytes(resp.content)
            law["url"] = pdf_url  # Update URL to direct PDF
            fixed += 1
            logger.info("[%d/%d] Fixed: %s (%dKB)", i + 1, len(laws), law["law_name"][:50], len(resp.content) // 1024)

        except Exception as e:
            logger.error("[%d] Download failed: %s - %s", i, pdf_url[:60], e)
            failed += 1

        if (i + 1) % 50 == 0:
            logger.info("Progress: %d/%d (fixed=%d, skipped=%d, failed=%d)", i + 1, len(laws), fixed, skipped, failed)

    # Update metadata
    if not args.dry_run and fixed > 0:
        metadata["laws"] = laws
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info("Updated metadata: %s", meta_path)

    print(f"\nQR PDF fix complete: fixed={fixed}, skipped={skipped}, failed={failed}")


if __name__ == "__main__":
    main()
