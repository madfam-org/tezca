#!/usr/bin/env python3
"""
OCR Recovery for empty/short-text PDFs.

Scans data/state_laws/ and data/federal/ for PDFs whose .txt companion
is missing or too short, and runs OCR via pytesseract + pdf2image.

Usage:
    poetry run python scripts/scraping/run_overnight_ocr.py
    poetry run python scripts/scraping/run_overnight_ocr.py --limit 100
"""

import argparse
import logging
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"
MIN_TEXT_LENGTH = 100  # Match pipeline.py threshold


def find_pdfs_needing_ocr():
    """Find PDFs with missing or too-short text files."""
    search_dirs = [
        DATA_DIR / "state_laws",
        DATA_DIR / "federal",
        DATA_DIR / "municipal",
    ]

    candidates = []
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for pdf_path in search_dir.rglob("*.pdf"):
            txt_path = pdf_path.with_suffix(".txt")
            needs_ocr = False

            if not txt_path.exists():
                needs_ocr = True
            else:
                try:
                    text = txt_path.read_text(encoding="utf-8", errors="replace")
                    if len(text.strip()) < MIN_TEXT_LENGTH:
                        needs_ocr = True
                except Exception:
                    needs_ocr = True

            if needs_ocr:
                candidates.append(pdf_path)

    return candidates


def ocr_extract(pdf_path):
    """Run OCR on a single PDF. Returns extracted text or empty string."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError as e:
        logger.error("Missing OCR dependency: %s", e)
        return ""

    try:
        images = convert_from_path(pdf_path, dpi=200)
        text_parts = []
        for image in images:
            page_text = pytesseract.image_to_string(image, lang="spa")
            if page_text and page_text.strip():
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.error("OCR failed for %s: %s", pdf_path.name, e)
        return ""


def try_pdfplumber_first(pdf_path):
    """Try pdfplumber extraction before OCR (faster)."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts)
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser(description="OCR recovery for empty PDFs")
    parser.add_argument("--limit", type=int, default=0, help="Max PDFs to process (0=all)")
    args = parser.parse_args()

    start = time.time()
    logger.info("=== OCR Recovery Starting ===")

    # Check dependencies
    try:
        import pytesseract
        import pdf2image
        logger.info("OCR dependencies available")
    except ImportError as e:
        logger.error("Missing OCR dependency: %s — aborting", e)
        sys.exit(1)

    candidates = find_pdfs_needing_ocr()
    logger.info("Found %d PDFs needing text extraction", len(candidates))

    if args.limit > 0:
        candidates = candidates[:args.limit]
        logger.info("Limited to %d PDFs", len(candidates))

    success_count = 0
    fail_count = 0
    skip_count = 0
    total_chars = 0

    for i, pdf_path in enumerate(candidates, 1):
        if i % 50 == 0 or i == 1:
            elapsed = time.time() - start
            rate = i / elapsed * 60 if elapsed > 0 else 0
            logger.info(
                "Progress: %d/%d (%.0f/min) — %d success, %d fail, %d skip",
                i, len(candidates), rate, success_count, fail_count, skip_count,
            )

        txt_path = pdf_path.with_suffix(".txt")

        # Try pdfplumber first (much faster than OCR)
        text = try_pdfplumber_first(pdf_path)

        if len(text.strip()) >= MIN_TEXT_LENGTH:
            txt_path.write_text(text, encoding="utf-8")
            success_count += 1
            total_chars += len(text)
            continue

        # Fall back to OCR
        text = ocr_extract(pdf_path)

        if len(text.strip()) >= MIN_TEXT_LENGTH:
            txt_path.write_text(text, encoding="utf-8")
            success_count += 1
            total_chars += len(text)
        elif text.strip():
            # Some text but below threshold — save anyway
            txt_path.write_text(text, encoding="utf-8")
            skip_count += 1
        else:
            fail_count += 1

    elapsed = time.time() - start
    logger.info("=== OCR Recovery Complete ===")
    logger.info("Processed: %d PDFs", len(candidates))
    logger.info("OCR success (>=%d chars): %d", MIN_TEXT_LENGTH, success_count)
    logger.info("OCR partial (<threshold): %d", skip_count)
    logger.info("OCR failed (empty): %d", fail_count)
    logger.info("Total chars extracted: %s", f"{total_chars:,}")
    logger.info("Duration: %.1f minutes", elapsed / 60)


if __name__ == "__main__":
    main()
