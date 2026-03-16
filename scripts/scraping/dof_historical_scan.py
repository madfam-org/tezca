#!/usr/bin/env python3
"""
DOF Historical Scan Script (W6 — Phase 17)

Scans DOF (Diario Oficial de la Federación) daily editions from 2000-2026
to find legal instruments published in DOF but missing from the Tezca corpus.

Three modes:
  1. Gap scan: Cross-reference DOF entries against DB to find missing laws
  2. NOM detection: Find NOM publications in DOF (keyword: NOM-, Norma Oficial)
  3. State gazette pilot: Probe state periódicos oficiales for law publications

Usage:
    python scripts/scraping/dof_historical_scan.py --year 2025 --dry-run
    python scripts/scraping/dof_historical_scan.py --range 2020-2026 --mode noms
    python scripts/scraping/dof_historical_scan.py --mode gazette --states jalisco nuevo_leon
"""

import argparse
import datetime
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import requests
from lxml import html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOF_BASE_URL = "https://dof.gob.mx"
DOF_INDEX_URL = f"{DOF_BASE_URL}/index.php"
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1.0  # seconds between DOF requests
USER_AGENT = "Tezca-DOFScan/1.0 (+https://tezca.mx)"

OUTPUT_DIR = Path("data/dof_historical")

# Keywords for legal instrument detection
LEGAL_KEYWORDS = [
    "DECRETO",
    "LEY",
    "REGLAMENTO",
    "CODIGO",
    "CÓDIGO",
    "CONSTITUCIÓN",
    "CONSTITUCION",
    "ESTATUTO",
    "ACUERDO",
    "LINEAMIENTO",
    "CIRCULAR",
    "NORMA",
    "CONVENIO",
]

NOM_PATTERN = re.compile(
    r"NOM-\d{3}-[A-Z0-9]{2,10}-\d{4}|" r"NORMA\s+OFICIAL\s+MEXICANA",
    re.IGNORECASE,
)

REFORM_KEYWORDS = ["REFORMA", "ADICIONA", "MODIFICA"]
ABROGATION_KEYWORDS = ["DEROGA", "ABROGA"]
NEW_LAW_KEYWORDS = ["EXPIDE", "SE CREA", "LEY GENERAL DE", "LEY FEDERAL DE"]

# State gazette (periódico oficial) URL patterns
STATE_GAZETTE_URLS = {
    "jalisco": "https://periodicooficial.jalisco.gob.mx/",
    "nuevo_leon": "https://po.nl.gob.mx/",
    "cdmx": "https://data.consejeria.cdmx.gob.mx/portal_old/gaceta.php",
    "estado_de_mexico": "https://legislacion.edomex.gob.mx/gaceta",
    "guanajuato": "https://periodicooficial.guanajuato.gob.mx/",
}


# ---------------------------------------------------------------------------
# HTTP session
# ---------------------------------------------------------------------------


def _setup_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


# ---------------------------------------------------------------------------
# DOF daily edition fetching
# ---------------------------------------------------------------------------


def fetch_dof_index(
    session: requests.Session, date: datetime.date
) -> List[Dict[str, str]]:
    """Fetch and parse a single DOF daily index page.

    Returns:
        List of entry dicts with keys: title, section, category, url, date.
    """
    url = (
        f"{DOF_INDEX_URL}"
        f"?year={date.year}"
        f"&month={date.month:02d}"
        f"&day={date.day:02d}"
    )

    try:
        time.sleep(REQUEST_DELAY)
        resp = session.get(url, timeout=REQUEST_TIMEOUT, verify=False)
        if resp.status_code != 200:
            return []
    except requests.RequestException:
        return []

    entries: List[Dict[str, str]] = []

    try:
        tree = html.fromstring(resp.content)
    except Exception:
        return []

    # Strategy 1: Section-based div containers
    entries = _extract_from_divs(tree, date)

    # Strategy 2: Table rows
    if not entries:
        entries = _extract_from_tables(tree, date)

    # Strategy 3: Flat link scan
    if not entries:
        entries = _extract_from_links(tree, date)

    return entries


def _extract_from_divs(tree, date: datetime.date) -> List[Dict[str, str]]:
    """Extract entries from section-based div containers."""
    entries = []
    current_section = ""
    current_category = ""

    section_pattern = re.compile(
        r"(PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA)\s+SECCI[OÓ]N",
        re.IGNORECASE,
    )

    for div in tree.iter("div"):
        text = (div.text_content() or "").strip()

        # Check for section headers
        section_match = section_pattern.search(text)
        if section_match and len(text) < 50:
            current_section = text.upper().replace("Ó", "O")
            continue

        # Check for category headers (uppercase, short)
        if text.isupper() and 10 < len(text) < 100 and "SECRETARIA" in text:
            current_category = text
            continue

        # Look for entry links
        for link in div.iter("a"):
            href = link.get("href", "")
            title = (link.text_content() or "").strip()

            if not title or len(title) < 15:
                continue
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue

            entry_url = (
                href
                if href.startswith("http")
                else f"{DOF_BASE_URL}/{href.lstrip('/')}"
            )

            entries.append(
                {
                    "title": title,
                    "section": current_section,
                    "category": current_category,
                    "url": entry_url,
                    "date": date.isoformat(),
                }
            )

    return entries


def _extract_from_tables(tree, date: datetime.date) -> List[Dict[str, str]]:
    """Extract entries from table-based DOF layouts."""
    entries = []
    for row in tree.iter("tr"):
        cells = list(row.iter("td"))
        if len(cells) < 1:
            continue

        for link in row.iter("a"):
            href = link.get("href", "")
            title = (link.text_content() or "").strip()

            if not title or len(title) < 15 or not href:
                continue

            entry_url = (
                href
                if href.startswith("http")
                else f"{DOF_BASE_URL}/{href.lstrip('/')}"
            )
            entries.append(
                {
                    "title": title,
                    "section": "",
                    "category": "",
                    "url": entry_url,
                    "date": date.isoformat(),
                }
            )

    return entries


def _extract_from_links(tree, date: datetime.date) -> List[Dict[str, str]]:
    """Fallback: extract all links that look like legal entries."""
    entries = []
    for link in tree.iter("a"):
        href = link.get("href", "")
        title = (link.text_content() or "").strip()

        if not title or len(title) < 20:
            continue
        if not href or href.startswith("#"):
            continue

        upper_title = title.upper()
        if any(kw in upper_title for kw in LEGAL_KEYWORDS):
            entry_url = (
                href
                if href.startswith("http")
                else f"{DOF_BASE_URL}/{href.lstrip('/')}"
            )
            entries.append(
                {
                    "title": title,
                    "section": "",
                    "category": "",
                    "url": entry_url,
                    "date": date.isoformat(),
                }
            )

    return entries


# ---------------------------------------------------------------------------
# Analysis modes
# ---------------------------------------------------------------------------


def classify_entry(entry: Dict[str, str]) -> Dict[str, str]:
    """Classify a DOF entry by change type and legal instrument type."""
    title = entry.get("title", "").upper()

    # Change type — check in priority order (reform/abrogation before new_law)
    change_type = "other"
    if any(kw in title for kw in REFORM_KEYWORDS):
        change_type = "reform"
    elif any(kw in title for kw in ABROGATION_KEYWORDS):
        change_type = "abrogation"
    elif any(kw in title for kw in NEW_LAW_KEYWORDS):
        change_type = "new_law"

    # Instrument type
    instrument = "other"
    if "NOM-" in title or "NORMA OFICIAL" in title:
        instrument = "nom"
    elif "REGLAMENTO" in title:
        instrument = "reglamento"
    elif "LEY" in title:
        instrument = "ley"
    elif "DECRETO" in title:
        instrument = "decreto"
    elif "ACUERDO" in title:
        instrument = "acuerdo"
    elif "LINEAMIENTO" in title:
        instrument = "lineamiento"
    elif any(k in title for k in ("CODIGO", "CÓDIGO")):
        instrument = "codigo"

    entry["change_type"] = change_type
    entry["instrument_type"] = instrument

    # Extract NOM number if present
    nom_match = re.search(r"NOM-\d{3}-[A-Z0-9]{2,10}-\d{4}", title)
    if nom_match:
        entry["nom_number"] = nom_match.group()

    return entry


CHECKPOINT_FILE = "dof_scan_checkpoint.json"
PARTIAL_FILE = "dof_entries_partial.json"
NOM_CATALOG_PATH = Path("data/federal/noms/discovered_noms.json")


def _load_checkpoint(output_dir: Path) -> Optional[Dict[str, Any]]:
    """Load scan checkpoint if it exists."""
    cp_path = output_dir / CHECKPOINT_FILE
    if cp_path.exists():
        try:
            return json.loads(cp_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _save_checkpoint(
    output_dir: Path,
    last_date: datetime.date,
    entries_count: int,
    mode: str,
) -> None:
    """Save scan checkpoint."""
    cp = {
        "last_date": last_date.isoformat(),
        "entries_count": entries_count,
        "mode": mode,
        "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (output_dir / CHECKPOINT_FILE).write_text(
        json.dumps(cp, indent=2), encoding="utf-8"
    )


def _delete_checkpoint(output_dir: Path) -> None:
    """Remove checkpoint file on completion."""
    cp_path = output_dir / CHECKPOINT_FILE
    if cp_path.exists():
        cp_path.unlink()


def scan_date_range(
    session: requests.Session,
    start_date: datetime.date,
    end_date: datetime.date,
    mode: str = "all",
    resume: bool = False,
    output_dir: Optional[Path] = None,
) -> List[Dict[str, str]]:
    """Scan DOF editions over a date range.

    Args:
        session: HTTP session.
        start_date: First date to scan.
        end_date: Last date to scan.
        mode: "all", "noms", "new_laws", or "gap"
        resume: If True, attempt to resume from checkpoint.
        output_dir: Directory for checkpoint files.

    Returns:
        List of classified DOF entries.
    """
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    all_entries: List[Dict[str, str]] = []
    effective_start = start_date

    # Resume from checkpoint
    if resume:
        cp = _load_checkpoint(out)
        if cp:
            last_date = datetime.date.fromisoformat(cp["last_date"])
            effective_start = last_date + datetime.timedelta(days=1)
            logger.info(
                "Resuming from checkpoint: %s (%d entries so far)",
                last_date,
                cp["entries_count"],
            )
            # Load partial results
            partial = out / PARTIAL_FILE
            if partial.exists():
                try:
                    all_entries = json.loads(partial.read_text(encoding="utf-8"))
                    logger.info("Loaded %d partial entries", len(all_entries))
                except (json.JSONDecodeError, OSError):
                    pass

    current = effective_start
    days_scanned = 0
    total_days = (end_date - start_date).days + 1

    while current <= end_date:
        # Skip weekends (DOF doesn't publish)
        if current.weekday() in (5, 6):
            current += datetime.timedelta(days=1)
            continue

        entries = fetch_dof_index(session, current)

        for entry in entries:
            classified = classify_entry(entry)

            # Filter by mode
            if mode == "noms" and classified.get("instrument_type") != "nom":
                continue
            if mode == "new_laws" and classified.get("change_type") != "new_law":
                continue

            all_entries.append(classified)

        days_scanned += 1
        if days_scanned % 30 == 0:
            logger.info(
                "Progress: %d/%d days scanned, %d entries found",
                days_scanned,
                total_days,
                len(all_entries),
            )
            # Save checkpoint every 30 days
            _save_checkpoint(out, current, len(all_entries), mode)
            with open(out / PARTIAL_FILE, "w", encoding="utf-8") as f:
                json.dump(all_entries, f, indent=2, ensure_ascii=False)

        current += datetime.timedelta(days=1)

    # Clean up checkpoint on completion
    _delete_checkpoint(out)
    partial_path = out / PARTIAL_FILE
    if partial_path.exists():
        partial_path.unlink()

    logger.info(
        "Scan complete: %d days scanned, %d entries found",
        days_scanned,
        len(all_entries),
    )
    return all_entries


# ---------------------------------------------------------------------------
# NOM cross-reference
# ---------------------------------------------------------------------------


def cross_reference_noms(
    dof_noms: List[Dict],
    catalog_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Cross-reference DOF-discovered NOMs against the existing catalog.

    Args:
        dof_noms: List of NOM dicts from DOF scan (must have 'nom_number').
        catalog_path: Path to discovered_noms.json (default: NOM_CATALOG_PATH).

    Returns:
        Dict with new_noms, existing_noms, new_count, existing_count.
    """
    cat_path = catalog_path or NOM_CATALOG_PATH
    known_numbers: Set[str] = set()

    if cat_path.exists():
        try:
            catalog = json.loads(cat_path.read_text(encoding="utf-8"))
            for entry in catalog:
                nom_num = entry.get("nom_number") or entry.get("nom_id") or ""
                if nom_num:
                    known_numbers.add(nom_num.upper())
            logger.info("Loaded %d known NOMs from catalog", len(known_numbers))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load NOM catalog: %s", e)

    new_noms: List[Dict] = []
    existing_noms: List[Dict] = []

    for nom in dof_noms:
        nom_number = (nom.get("nom_number") or "").upper()
        if not nom_number:
            continue
        if nom_number in known_numbers:
            existing_noms.append(nom)
        else:
            new_noms.append(nom)

    result = {
        "new_noms": new_noms,
        "existing_noms": existing_noms,
        "new_count": len(new_noms),
        "existing_count": len(existing_noms),
        "catalog_size": len(known_numbers),
    }

    # Save new NOMs if any
    if new_noms:
        new_path = OUTPUT_DIR / "dof_new_noms.json"
        with open(new_path, "w", encoding="utf-8") as f:
            json.dump(new_noms, f, indent=2, ensure_ascii=False)
        logger.info(
            "Found %d new NOMs not in catalog, saved to %s", len(new_noms), new_path
        )

    return result


# ---------------------------------------------------------------------------
# State gazette probing
# ---------------------------------------------------------------------------


def probe_state_gazettes(
    session: requests.Session,
    states: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Probe state periódicos oficiales for accessibility.

    Args:
        states: State keys to probe (None = all configured).

    Returns:
        Dict mapping state key to probe results.
    """
    target_states = states or list(STATE_GAZETTE_URLS.keys())
    results: Dict[str, Dict[str, Any]] = {}

    for state_key in target_states:
        url = STATE_GAZETTE_URLS.get(state_key)
        if not url:
            logger.warning("No gazette URL for %s", state_key)
            continue

        result: Dict[str, Any] = {
            "url": url,
            "accessible": False,
            "has_law_content": False,
            "has_pdf_links": False,
        }

        try:
            time.sleep(REQUEST_DELAY)
            resp = session.get(
                url, timeout=REQUEST_TIMEOUT, verify=False, allow_redirects=True
            )
            result["status_code"] = resp.status_code
            result["accessible"] = resp.status_code == 200

            if resp.status_code == 200:
                text = resp.text.lower()
                result["has_law_content"] = any(
                    kw in text
                    for kw in ["decreto", "ley", "reglamento", "periódico oficial"]
                )
                result["has_pdf_links"] = ".pdf" in text

        except requests.RequestException as e:
            result["error"] = str(e)[:100]

        results[state_key] = result
        logger.info("Gazette %s: %s", state_key, result)

    return results


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_historical_scan(
    year: Optional[int] = None,
    date_range: Optional[str] = None,
    mode: str = "all",
    dry_run: bool = False,
    states: Optional[List[str]] = None,
    resume: bool = False,
    cross_ref_only: bool = False,
) -> Dict[str, Any]:
    """Run DOF historical scan.

    Args:
        year: Single year to scan.
        date_range: Date range "YYYY-YYYY".
        mode: "all", "noms", "new_laws", "gap", "gazette".
        dry_run: Only report counts without full analysis.
        states: States for gazette mode.
        resume: Resume from checkpoint if available.
        cross_ref_only: Only run NOM cross-reference on existing results.

    Returns:
        Summary dict.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Cross-reference only mode
    if cross_ref_only:
        # Find the most recent noms results file
        nom_files = sorted(OUTPUT_DIR.glob("dof_noms_*.json"), reverse=True)
        if not nom_files:
            logger.warning("No DOF NOM results found for cross-reference")
            return {"error": "no_nom_results_found"}
        noms_path = nom_files[0]
        logger.info("Cross-referencing NOMs from %s", noms_path)
        dof_noms = json.loads(noms_path.read_text(encoding="utf-8"))
        xref = cross_reference_noms(dof_noms)
        logger.info(
            "Cross-reference: %d new, %d existing (catalog: %d)",
            xref["new_count"],
            xref["existing_count"],
            xref["catalog_size"],
        )
        return {
            "mode": "cross_ref",
            "cross_reference": {
                "new_count": xref["new_count"],
                "existing_count": xref["existing_count"],
                "catalog_size": xref["catalog_size"],
            },
        }

    session = _setup_session()

    # State gazette mode
    if mode == "gazette":
        results = probe_state_gazettes(session, states)
        report_path = OUTPUT_DIR / "gazette_probe_results.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info("Gazette probe saved to %s", report_path)
        return {"mode": "gazette", "results": results}

    # Determine date range
    if year:
        start_date = datetime.date(year, 1, 1)
        end_date = min(datetime.date(year, 12, 31), datetime.date.today())
    elif date_range:
        parts = date_range.split("-")
        start_date = datetime.date(int(parts[0]), 1, 1)
        end_date = min(datetime.date(int(parts[1]), 12, 31), datetime.date.today())
    else:
        # Default: last 2 years
        end_date = datetime.date.today()
        start_date = datetime.date(end_date.year - 2, 1, 1)

    logger.info("Scanning DOF from %s to %s (mode=%s)", start_date, end_date, mode)

    if dry_run:
        total_days = (end_date - start_date).days + 1
        weekdays = sum(
            1
            for i in range(total_days)
            if (start_date + datetime.timedelta(days=i)).weekday() < 5
        )
        logger.info("DRY RUN: would scan %d weekdays", weekdays)
        return {
            "dry_run": True,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "estimated_weekdays": weekdays,
            "estimated_time_hours": weekdays * REQUEST_DELAY / 3600,
        }

    entries = scan_date_range(
        session, start_date, end_date, mode=mode, resume=resume, output_dir=OUTPUT_DIR
    )

    # Analyze results
    summary: Dict[str, Any] = {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "mode": mode,
        "total_entries": len(entries),
    }

    # Group by instrument type
    by_instrument: Dict[str, int] = {}
    by_change: Dict[str, int] = {}
    noms_found: List[Dict] = []

    for entry in entries:
        inst = entry.get("instrument_type", "other")
        by_instrument[inst] = by_instrument.get(inst, 0) + 1

        change = entry.get("change_type", "other")
        by_change[change] = by_change.get(change, 0) + 1

        if entry.get("nom_number"):
            noms_found.append(
                {
                    "nom_number": entry["nom_number"],
                    "title": entry["title"],
                    "date": entry["date"],
                    "url": entry["url"],
                }
            )

    summary["by_instrument"] = by_instrument
    summary["by_change_type"] = by_change
    summary["noms_found"] = len(noms_found)

    # Save results
    entries_path = OUTPUT_DIR / f"dof_entries_{start_date.year}_{end_date.year}.json"
    with open(entries_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    if noms_found:
        noms_path = OUTPUT_DIR / f"dof_noms_{start_date.year}_{end_date.year}.json"
        with open(noms_path, "w", encoding="utf-8") as f:
            json.dump(noms_found, f, indent=2, ensure_ascii=False)
        logger.info(
            "Found %d NOM publications, saved to %s", len(noms_found), noms_path
        )

        # Auto cross-reference NOMs against catalog
        xref = cross_reference_noms(noms_found)
        summary["nom_cross_reference"] = {
            "new_count": xref["new_count"],
            "existing_count": xref["existing_count"],
            "catalog_size": xref["catalog_size"],
        }
        logger.info(
            "NOM cross-reference: %d new, %d existing",
            xref["new_count"],
            xref["existing_count"],
        )

    report_path = OUTPUT_DIR / "dof_scan_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info("=== DOF Historical Scan Summary ===")
    logger.info("Total entries: %d", len(entries))
    logger.info("By instrument: %s", by_instrument)
    logger.info("By change type: %s", by_change)
    logger.info("NOMs found: %d", len(noms_found))

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DOF historical scan for gap-filling (Phase 17 W6).",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Single year to scan",
    )
    parser.add_argument(
        "--range",
        type=str,
        default=None,
        dest="date_range",
        help="Date range YYYY-YYYY (e.g. 2020-2026)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["all", "noms", "new_laws", "gap", "gazette"],
        default="all",
        help="Scan mode (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report scan scope without fetching",
    )
    parser.add_argument(
        "--states",
        type=str,
        nargs="+",
        default=None,
        help="States for gazette mode",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint if available",
    )
    parser.add_argument(
        "--cross-ref",
        action="store_true",
        dest="cross_ref",
        help="Run NOM cross-reference on existing results without re-scanning",
    )

    args = parser.parse_args()

    result = run_historical_scan(
        year=args.year,
        date_range=args.date_range,
        mode=args.mode,
        dry_run=args.dry_run,
        states=args.states,
        resume=args.resume,
        cross_ref_only=args.cross_ref,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
