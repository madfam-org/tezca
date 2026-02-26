#!/usr/bin/env python3
"""
Ingest cataloged NOMs (Normas Oficiales Mexicanas) into the database.

Downloads PDFs from DOF, extracts text, and creates Law + LawVersion records
for each NOM in the discovered_noms.json catalog.

Usage:
    python scripts/ingestion/ingest_noms.py
    python scripts/ingestion/ingest_noms.py --dry-run
    python scripts/ingestion/ingest_noms.py --skip-download --limit 10
    python scripts/ingestion/ingest_noms.py --workers 4
"""

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.indigo.settings")

import django

django.setup()

from django.utils.dateparse import parse_date

from apps.api.models import Law, LawVersion

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATALOG_PATH = PROJECT_ROOT / "data" / "noms" / "discovered_noms.json"
PDF_DIR = PROJECT_ROOT / "data" / "noms" / "pdfs"
DOWNLOAD_DELAY = 1.0  # seconds between downloads
DEFAULT_PUB_DATE = "2020-01-01"
REQUEST_TIMEOUT = 60  # seconds — NOM PDFs can be large


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def _create_download_session():
    """Create an HTTP session with SSL bypass for dof.gob.mx."""
    from apps.scraper.http import government_session

    return government_session("https://dof.gob.mx")


def download_pdf(
    session, nom: Dict[str, Any], output_dir: Path
) -> Tuple[str, Optional[Path]]:
    """
    Download a single NOM PDF from DOF.

    Returns:
        Tuple of (nom_id, pdf_path or None on failure).
    """
    nom_id = nom.get("id", "unknown")
    url = nom.get("url", "")

    if not url:
        logger.warning("[%s] No URL in catalog, skipping download.", nom_id)
        return nom_id, None

    pdf_path = output_dir / f"{nom_id}.pdf"

    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        logger.debug("[%s] PDF already exists, skipping.", nom_id)
        return nom_id, pdf_path

    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        resp.raise_for_status()

        # Check content type — DOF sometimes returns HTML instead of PDF
        content_type = resp.headers.get("Content-Type", "")
        is_pdf = (
            "application/pdf" in content_type
            or url.endswith(".pdf")
            or resp.content[:5] == b"%PDF-"
        )

        output_dir.mkdir(parents=True, exist_ok=True)

        if is_pdf:
            with open(pdf_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(
                "[%s] Downloaded PDF (%d bytes).", nom_id, pdf_path.stat().st_size
            )
            return nom_id, pdf_path
        else:
            # Save the HTML content as .html for later inspection
            html_path = output_dir / f"{nom_id}.html"
            with open(html_path, "wb") as f:
                f.write(resp.content)
            logger.warning(
                "[%s] URL returned HTML instead of PDF, saved as %s.",
                nom_id,
                html_path.name,
            )
            return nom_id, None

    except Exception as exc:
        logger.error("[%s] Download failed: %s", nom_id, exc)
        return nom_id, None


def download_all(
    noms: List[Dict[str, Any]],
    output_dir: Path,
    workers: int = 1,
) -> Dict[str, Optional[Path]]:
    """
    Download PDFs for all NOMs with rate limiting.

    Args:
        noms: List of NOM catalog entries.
        output_dir: Directory to save PDFs.
        workers: Number of concurrent download threads.

    Returns:
        Dict mapping nom_id to pdf_path (or None on failure).
    """
    results: Dict[str, Optional[Path]] = {}
    output_dir.mkdir(parents=True, exist_ok=True)

    if workers <= 1:
        # Sequential with rate limiting
        session = _create_download_session()
        for i, nom in enumerate(noms, 1):
            nom_id, pdf_path = download_pdf(session, nom, output_dir)
            results[nom_id] = pdf_path
            if i < len(noms):
                time.sleep(DOWNLOAD_DELAY)
            if i % 10 == 0:
                print(f"  Downloaded {i}/{len(noms)}...")
    else:
        # Parallel downloads — each worker gets its own session
        def _download_with_session(nom: Dict[str, Any]) -> Tuple[str, Optional[Path]]:
            thread_session = _create_download_session()
            result = download_pdf(thread_session, nom, output_dir)
            time.sleep(DOWNLOAD_DELAY)
            return result

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_download_with_session, nom): nom for nom in noms
            }
            done_count = 0
            for future in as_completed(futures):
                nom_id, pdf_path = future.result()
                results[nom_id] = pdf_path
                done_count += 1
                if done_count % 10 == 0:
                    print(f"  Downloaded {done_count}/{len(noms)}...")

    return results


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract text content from a PDF file.

    Tries pdfplumber first, falls back to basic PyPDF2/pypdf, then OCR.
    Returns empty string if extraction fails entirely.
    """
    text = ""

    # Strategy 1: pdfplumber (best for text-based PDFs)
    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            pages = []
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages.append(page_text)
            text = "\n\n".join(pages)
            if len(text.strip()) > 100:
                return text
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("pdfplumber failed for %s: %s", pdf_path.name, exc)

    # Strategy 2: pypdf
    try:
        from pypdf import PdfReader

        reader = PdfReader(pdf_path)
        pages = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text)
        text = "\n\n".join(pages)
        if len(text.strip()) > 100:
            return text
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("pypdf failed for %s: %s", pdf_path.name, exc)

    # Strategy 3: OCR fallback (pytesseract + pdf2image)
    try:
        import pytesseract
        from pdf2image import convert_from_path

        images = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=10)
        pages = []
        for img in images:
            page_text = pytesseract.image_to_string(img, lang="spa")
            if page_text.strip():
                pages.append(page_text)
        text = "\n\n".join(pages)
        if len(text.strip()) > 100:
            return text
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("OCR failed for %s: %s", pdf_path.name, exc)

    return text


# ---------------------------------------------------------------------------
# Database ingestion
# ---------------------------------------------------------------------------


def build_official_id(nom: Dict[str, Any]) -> str:
    """Build the official_id for a NOM entry."""
    nom_number = nom.get("nom_number", "")
    if nom_number:
        return f"nom_{nom_number}"
    return f"nom_{nom.get('id', 'unknown')}"


def ingest_nom(nom: Dict[str, Any], pdf_path: Optional[Path]) -> str:
    """
    Insert or update a single NOM in the database.

    Returns:
        One of "created", "updated", "error".
    """
    official_id = build_official_id(nom)[:200]
    law_name = nom.get("name", "")
    if not law_name:
        law_name = nom.get("nom_number", official_id)

    nom_number = nom.get("nom_number", "")
    secretaria = nom.get("secretaria", "")
    category = secretaria if secretaria else "norma_oficial"
    source_url = (nom.get("url", "") or "")[:500]
    status_raw = nom.get("status", "vigente")

    # Map status to model choices
    status_map = {
        "vigente": Law.Status.VIGENTE,
        "abrogada": Law.Status.ABROGADA,
        "derogada": Law.Status.DEROGADA,
    }
    status = status_map.get(status_raw, Law.Status.UNKNOWN)

    try:
        defaults = {
            "name": law_name[:500],
            "short_name": nom_number[:200] if nom_number else law_name[:200],
            "category": category[:100],
            "tier": "federal",
            "law_type": "non_legislative",
            "source_url": source_url,
            "status": status,
        }

        law, created = Law.objects.get_or_create(
            official_id=official_id,
            defaults=defaults,
        )

        if not created:
            for key, value in defaults.items():
                setattr(law, key, value)
            law.save()

        # Parse publication date
        pub_date_str = nom.get("date_published", "")
        pub_date = parse_date(pub_date_str) if pub_date_str else None
        if not pub_date:
            pub_date = parse_date(DEFAULT_PUB_DATE)

        # Build xml_file_path from PDF location (relative to data/)
        xml_file_path = ""
        if pdf_path and pdf_path.exists():
            try:
                xml_file_path = str(pdf_path.relative_to(PROJECT_ROOT / "data"))[:500]
            except ValueError:
                xml_file_path = str(pdf_path)[:500]

        LawVersion.objects.get_or_create(
            law=law,
            publication_date=pub_date,
            defaults={
                "dof_url": source_url,
                "xml_file_path": xml_file_path,
            },
        )

        return "created" if created else "updated"

    except Exception as exc:
        logger.error("[%s] Ingestion failed: %s", official_id, exc)
        return "error"


def ingest_batch(
    noms: List[Dict[str, Any]],
    pdf_map: Dict[str, Optional[Path]],
) -> Dict[str, int]:
    """
    Ingest all NOMs into the database.

    Args:
        noms: List of NOM catalog entries.
        pdf_map: Mapping of nom_id to downloaded PDF path.

    Returns:
        Summary dict with created, updated, error counts.
    """
    summary = {"created": 0, "updated": 0, "error": 0}

    for i, nom in enumerate(noms, 1):
        nom_id = nom.get("id", "unknown")
        pdf_path = pdf_map.get(nom_id)
        result = ingest_nom(nom, pdf_path)
        summary[result] += 1

        if i % 20 == 0:
            print(
                f"  [{i}/{len(noms)}] "
                f"created={summary['created']} "
                f"updated={summary['updated']} "
                f"errors={summary['error']}"
            )

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Download and ingest cataloged NOMs into the database.",
    )
    parser.add_argument(
        "--catalog",
        type=str,
        default=str(CATALOG_PATH),
        help=f"Path to discovered_noms.json (default: {CATALOG_PATH}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load catalog and report what would happen without writing to DB.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only the first N NOMs (0 = all).",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip PDF downloads, use existing files in data/noms/pdfs/.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of concurrent download workers (default: 1).",
    )
    args = parser.parse_args()

    # --- Load catalog ---
    catalog_path = Path(args.catalog)
    if not catalog_path.exists():
        print(f"ERROR: Catalog not found at {catalog_path}")
        sys.exit(1)

    with open(catalog_path, "r", encoding="utf-8") as f:
        noms: List[Dict[str, Any]] = json.load(f)

    print(f"Loaded {len(noms)} NOMs from {catalog_path}")

    if args.limit > 0:
        noms = noms[: args.limit]
        print(f"Limited to first {args.limit} NOMs.")

    if not noms:
        print("No NOMs to process.")
        return

    # --- Dry run ---
    if args.dry_run:
        print("\n--- DRY RUN ---")
        for i, nom in enumerate(noms, 1):
            official_id = build_official_id(nom)
            nom_number = nom.get("nom_number", "?")
            secretaria = nom.get("secretaria", "?")
            url = nom.get("url", "?")
            pdf_path = PDF_DIR / f"{nom.get('id', 'unknown')}.pdf"
            pdf_exists = "[exists]" if pdf_path.exists() else "[missing]"
            print(
                f"  {i:3d}. {official_id:<40s} "
                f"{nom_number:<25s} "
                f"{secretaria[:30]:<30s} "
                f"PDF {pdf_exists}"
            )
            # Check if already in DB
            existing = Law.objects.filter(official_id=official_id[:200]).exists()
            if existing:
                print(f"       -> Already in DB (would update)")
            else:
                print(f"       -> New (would create)")

        existing_count = sum(
            1
            for nom in noms
            if Law.objects.filter(official_id=build_official_id(nom)[:200]).exists()
        )
        new_count = len(noms) - existing_count
        pdf_count = sum(
            1 for nom in noms if (PDF_DIR / f"{nom.get('id', 'unknown')}.pdf").exists()
        )
        print(
            f"\nSummary: {len(noms)} total, {new_count} new, {existing_count} existing, {pdf_count} PDFs on disk"
        )
        return

    # --- Download PDFs ---
    pdf_map: Dict[str, Optional[Path]] = {}

    if args.skip_download:
        print("\nSkipping downloads, checking existing PDFs...")
        for nom in noms:
            nom_id = nom.get("id", "unknown")
            pdf_path = PDF_DIR / f"{nom_id}.pdf"
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                pdf_map[nom_id] = pdf_path
            else:
                pdf_map[nom_id] = None
        found = sum(1 for p in pdf_map.values() if p is not None)
        print(f"  Found {found}/{len(noms)} existing PDFs.")
    else:
        print(f"\nDownloading PDFs to {PDF_DIR} (workers={args.workers})...")
        pdf_map = download_all(noms, PDF_DIR, workers=args.workers)
        downloaded = sum(1 for p in pdf_map.values() if p is not None)
        print(f"  Downloaded/found {downloaded}/{len(noms)} PDFs.")

    # --- Ingest to DB ---
    print("\nIngesting NOMs into database...")
    summary = ingest_batch(noms, pdf_map)

    # --- Final summary ---
    pdf_success = sum(1 for p in pdf_map.values() if p is not None)
    print("\n" + "=" * 60)
    print("NOM Ingestion Complete")
    print("=" * 60)
    print(f"  Total NOMs:    {len(noms)}")
    print(f"  PDFs on disk:  {pdf_success}")
    print(f"  DB created:    {summary['created']}")
    print(f"  DB updated:    {summary['updated']}")
    print(f"  DB errors:     {summary['error']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
