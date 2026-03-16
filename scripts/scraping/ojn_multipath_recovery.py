#!/usr/bin/env python3
"""
OJN Multi-Path Recovery Script (W1 — Phase 17)

Recovers failed OJN downloads using a three-path waterfall:
  Path A: Re-fetch OJN metadata (file_id → fichaOrdenamiento2.php) — download
          links may now be populated that were missing months ago.
  Path B: Wayback Machine CDX bulk recovery for items still missing after A.
  Path C: State congress portal cross-reference for heaviest failure states.

Parses failed_laws[] from:
  - data/state_laws_non_legislative/{state}/{state}_metadata.json (3,106 entries)
  - data/state_laws/{state}/*_metadata.json (792 legislative entries)

Usage:
    python scripts/scraping/ojn_multipath_recovery.py --dry-run
    python scripts/scraping/ojn_multipath_recovery.py --path a --states michoacan
    python scripts/scraping/ojn_multipath_recovery.py --all
    python scripts/scraping/ojn_multipath_recovery.py --path b --limit 100
"""

import argparse
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OJN_BASE = "http://compilacion.ordenjuridico.gob.mx"
OJN_METADATA_URL = f"{OJN_BASE}/fichaOrdenamiento2.php"
OJN_DOWNLOAD_PREFIX = f"{OJN_BASE}/obtenerdoc.php"

WAYBACK_CDX_URL = "https://web.archive.org/cdx/search/cdx"
WAYBACK_WEB_PREFIX = "https://web.archive.org/web"

# State directories
NON_LEG_DATA = Path("data/state_laws_non_legislative")
LEG_DATA = Path("data/state_laws")
RECOVERY_OUTPUT = Path("data/recovery")

# Rate limits
OJN_REQUEST_DELAY = 1.5  # seconds between OJN requests
OJN_TIMEOUT = 120  # seconds
WAYBACK_REQUEST_DELAY = 1.0  # seconds between Wayback API calls

# Heaviest failure states for Path C cross-reference
PATH_C_STATES = {
    "michoacán": "michoacan",
    "estado_de_méxico": "estado_de_mexico",
    "san_luis_potosí": "san_luis_potosi",
}

USER_AGENT = "Tezca-Recovery/1.0 (+https://tezca.mx)"


# ---------------------------------------------------------------------------
# HTTP Session
# ---------------------------------------------------------------------------


def _setup_session() -> requests.Session:
    """Configure session with OJN-hardened retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


# ---------------------------------------------------------------------------
# Failure record loading
# ---------------------------------------------------------------------------


def load_failed_records(
    scope: str = "all",
    states: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Load all failed law records from metadata files.

    Args:
        scope: "non_leg", "leg", or "all"
        states: Optional list of state directory names to filter

    Returns:
        List of failure dicts with added 'source_type' and 'state' keys.
    """
    records: List[Dict[str, Any]] = []

    if scope in ("non_leg", "all"):
        records.extend(_scan_metadata_dir(NON_LEG_DATA, "non_legislative", states))

    if scope in ("leg", "all"):
        records.extend(_scan_metadata_dir(LEG_DATA, "legislative", states))

    logger.info("Loaded %d failed records (scope=%s)", len(records), scope)
    return records


def _scan_metadata_dir(
    base_dir: Path,
    source_type: str,
    states: Optional[List[str]],
) -> List[Dict[str, Any]]:
    """Scan a data directory for metadata files and extract failed_laws."""
    records: List[Dict[str, Any]] = []

    if not base_dir.exists():
        logger.warning("Directory not found: %s", base_dir)
        return records

    for state_dir in sorted(base_dir.iterdir()):
        if not state_dir.is_dir():
            continue

        state_name = state_dir.name
        if states and state_name not in states:
            continue

        for meta_file in state_dir.glob("*_metadata.json"):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                failed = data.get("failed_laws", [])
                for entry in failed:
                    entry["state"] = state_name
                    entry["source_type"] = source_type
                    entry["metadata_file"] = str(meta_file)
                records.extend(failed)

            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Error reading %s: %s", meta_file, e)

    return records


# ---------------------------------------------------------------------------
# Path A: Re-fetch OJN metadata
# ---------------------------------------------------------------------------


def path_a_refetch_metadata(
    records: List[Dict[str, Any]],
    session: requests.Session,
    output_dir: Path,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> Tuple[List[Dict], List[Dict]]:
    """Re-fetch OJN metadata for failed items.

    For each file_id, hit fichaOrdenamiento2.php and look for a download URL.
    Download the document if URL is now available.

    Returns:
        (recovered, still_failed) tuple of record lists.
    """
    recovered: List[Dict] = []
    still_failed: List[Dict] = []

    # Filter to items where re-fetch might help
    refetchable = [
        r
        for r in records
        if r.get("failure_reason")
        in ("no_download_url", "no_metadata", "download_failed")
    ]

    if limit:
        refetchable = refetchable[:limit]

    logger.info("Path A: %d items to re-fetch metadata", len(refetchable))

    if dry_run:
        logger.info("DRY RUN: would re-fetch %d OJN metadata pages", len(refetchable))
        return [], refetchable

    from bs4 import BeautifulSoup

    for i, record in enumerate(refetchable, 1):
        file_id = record.get("file_id")
        if not file_id:
            still_failed.append(record)
            continue

        ambito = (
            "MUNICIPAL" if "municipal" in record.get("source_type", "") else "ESTATAL"
        )
        url = f"{OJN_METADATA_URL}?idArchivo={file_id}&ambito={ambito}"

        try:
            time.sleep(OJN_REQUEST_DELAY)
            resp = session.get(url, timeout=OJN_TIMEOUT)

            if resp.status_code != 200:
                record["path_a_result"] = f"http_{resp.status_code}"
                still_failed.append(record)
                continue

            soup = BeautifulSoup(resp.content, "html.parser")
            download_link = soup.find("a", href=re.compile(r"obtenerdoc\.php"))

            if not download_link:
                record["path_a_result"] = "still_no_download_url"
                still_failed.append(record)
                if i % 50 == 0:
                    logger.info(
                        "Path A progress: %d/%d (recovered: %d)",
                        i,
                        len(refetchable),
                        len(recovered),
                    )
                continue

            href = download_link.get("href", "")
            download_url = (
                href if href.startswith("http") else f"{OJN_BASE}/{href.lstrip('/')}"
            )

            # Download the file
            state = record.get("state", "unknown")
            state_dir = output_dir / state
            state_dir.mkdir(parents=True, exist_ok=True)

            law_name = record.get("law_name", f"law_{file_id}")
            safe_name = (
                re.sub(r"[^\w\s-]", "", law_name)[:100].replace(" ", "_").lower()
            )
            ext = "doc" if ".doc" in href.lower() else "pdf"
            file_path = state_dir / f"{safe_name}_{file_id}.{ext}"

            if file_path.exists() and file_path.stat().st_size > 1024:
                record["path_a_result"] = "already_exists"
                record["recovered_path"] = str(file_path)
                recovered.append(record)
                continue

            time.sleep(OJN_REQUEST_DELAY)
            dl_resp = session.get(download_url, timeout=OJN_TIMEOUT)

            if dl_resp.status_code == 200 and len(dl_resp.content) > 1024:
                file_path.write_bytes(dl_resp.content)
                record["path_a_result"] = "recovered"
                record["recovered_path"] = str(file_path)
                record["download_url"] = download_url
                recovered.append(record)
                logger.info(
                    "  Recovered: %s (%d bytes)", file_path.name, len(dl_resp.content)
                )
            else:
                record["path_a_result"] = "download_failed"
                still_failed.append(record)

        except requests.RequestException as e:
            record["path_a_result"] = f"error: {str(e)[:100]}"
            still_failed.append(record)

        if i % 50 == 0:
            logger.info(
                "Path A progress: %d/%d (recovered: %d)",
                i,
                len(refetchable),
                len(recovered),
            )

    logger.info(
        "Path A complete: %d recovered, %d still failed (of %d)",
        len(recovered),
        len(still_failed),
        len(refetchable),
    )
    return recovered, still_failed


# ---------------------------------------------------------------------------
# Path B: Wayback Machine CDX recovery
# ---------------------------------------------------------------------------


def path_b_wayback_cdx(
    records: List[Dict[str, Any]],
    session: requests.Session,
    output_dir: Path,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> Tuple[List[Dict], List[Dict]]:
    """Query Wayback Machine CDX API for archived OJN documents.

    For each file_id, search for archived snapshots of the download URL
    pattern and retrieve the document from the archive.

    Returns:
        (recovered, still_failed) tuple.
    """
    recovered: List[Dict] = []
    still_failed: List[Dict] = []

    if limit:
        records = records[:limit]

    logger.info("Path B: %d items to query Wayback CDX", len(records))

    if dry_run:
        logger.info("DRY RUN: would query CDX for %d items", len(records))
        return [], records

    for i, record in enumerate(records, 1):
        file_id = record.get("file_id")
        if not file_id:
            still_failed.append(record)
            continue

        # Try both known URL patterns for OJN documents
        # Use matchType=prefix in CDX params, no glob wildcards in URL
        url_patterns = [
            f"{OJN_BASE}/obtenerdoc.php?path={file_id}",
            f"{OJN_BASE}/fichaOrdenamiento2.php?idArchivo={file_id}",
        ]

        found_archive = False
        for pattern in url_patterns:
            try:
                time.sleep(WAYBACK_REQUEST_DELAY)
                cdx_resp = session.get(
                    WAYBACK_CDX_URL,
                    params={
                        "url": pattern,
                        "output": "json",
                        "fl": "timestamp,original,statuscode,mimetype",
                        "filter": "statuscode:200",
                        "limit": "5",
                        "matchType": "prefix",
                    },
                    timeout=30,
                    headers={"User-Agent": USER_AGENT},
                )

                if cdx_resp.status_code != 200:
                    continue

                rows = cdx_resp.json()
                if len(rows) <= 1:  # header row only
                    continue

                # Use the most recent snapshot
                for row in reversed(rows[1:]):
                    timestamp, original_url, status, mimetype = (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                    )

                    # Prefer document mimetypes
                    if mimetype not in (
                        "application/pdf",
                        "application/msword",
                        "application/octet-stream",
                        "text/html",
                    ):
                        continue

                    archive_url = f"{WAYBACK_WEB_PREFIX}/{timestamp}/{original_url}"

                    # Download from archive
                    state = record.get("state", "unknown")
                    state_dir = output_dir / state
                    state_dir.mkdir(parents=True, exist_ok=True)

                    law_name = record.get("law_name", f"law_{file_id}")
                    safe_name = (
                        re.sub(r"[^\w\s-]", "", law_name)[:100]
                        .replace(" ", "_")
                        .lower()
                    )
                    ext = "pdf" if "pdf" in mimetype else "doc"
                    file_path = state_dir / f"{safe_name}_{file_id}_wayback.{ext}"

                    if file_path.exists() and file_path.stat().st_size > 1024:
                        record["path_b_result"] = "already_exists"
                        record["recovered_path"] = str(file_path)
                        recovered.append(record)
                        found_archive = True
                        break

                    time.sleep(WAYBACK_REQUEST_DELAY)
                    dl_resp = session.get(archive_url, timeout=60)

                    if dl_resp.status_code == 200 and len(dl_resp.content) > 1024:
                        file_path.write_bytes(dl_resp.content)
                        record["path_b_result"] = "recovered"
                        record["recovered_path"] = str(file_path)
                        record["archive_url"] = archive_url
                        record["archive_timestamp"] = timestamp
                        recovered.append(record)
                        logger.info(
                            "  Wayback recovered: %s (%d bytes, %s)",
                            file_path.name,
                            len(dl_resp.content),
                            timestamp,
                        )
                        found_archive = True
                        break

                if found_archive:
                    break

            except (requests.RequestException, json.JSONDecodeError, IndexError) as e:
                logger.debug("CDX query error for file_id=%s: %s", file_id, e)
                continue

        if not found_archive:
            record["path_b_result"] = "not_in_archive"
            still_failed.append(record)

        if i % 50 == 0:
            logger.info(
                "Path B progress: %d/%d (recovered: %d)",
                i,
                len(records),
                len(recovered),
            )

        # Save partial results every 500 items
        if i % 500 == 0 and (recovered or still_failed):
            partial_path = output_dir / "path_b_partial.json"
            partial_path.parent.mkdir(parents=True, exist_ok=True)
            with open(partial_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"recovered": recovered, "still_failed_count": len(still_failed)},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            logger.info("Path B partial results saved at item %d", i)

    logger.info(
        "Path B complete: %d recovered, %d still failed (of %d)",
        len(recovered),
        len(still_failed),
        len(records),
    )
    return recovered, still_failed


# ---------------------------------------------------------------------------
# Path C: State congress cross-reference
# ---------------------------------------------------------------------------


def path_c_state_congress_xref(
    records: List[Dict[str, Any]],
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> Tuple[List[Dict], List[Dict]]:
    """Cross-reference failed laws against state congress scraper catalogs.

    For heavy-failure states (Michoacán, EdoMex, SLP), check if existing
    state congress scrapers have catalogs with matching law names.

    Returns:
        (matched, unmatched) tuple.
    """
    matched: List[Dict] = []
    unmatched: List[Dict] = []

    # Filter to heavy-failure states
    target_records = [r for r in records if r.get("state") in PATH_C_STATES]

    if limit:
        target_records = target_records[:limit]

    logger.info(
        "Path C: %d items to cross-reference against state congress catalogs",
        len(target_records),
    )

    if dry_run:
        # Group by state for reporting
        by_state: Dict[str, int] = {}
        for r in target_records:
            st = r.get("state", "unknown")
            by_state[st] = by_state.get(st, 0) + 1
        logger.info("DRY RUN: would cross-reference: %s", by_state)
        return [], target_records

    # Load existing state congress catalogs
    catalogs: Dict[str, List[Dict]] = {}
    for state_key in PATH_C_STATES.values():
        catalog_path = LEG_DATA / state_key / "catalog.json"
        if catalog_path.exists():
            try:
                catalogs[state_key] = json.loads(
                    catalog_path.read_text(encoding="utf-8")
                )
                logger.info(
                    "Loaded catalog for %s: %d entries",
                    state_key,
                    len(catalogs[state_key]),
                )
            except (json.JSONDecodeError, OSError):
                pass

    if not catalogs:
        logger.warning("No state congress catalogs found for cross-reference")
        return [], target_records

    for record in target_records:
        state = record.get("state", "")
        scraper_key = PATH_C_STATES.get(state)

        if not scraper_key or scraper_key not in catalogs:
            unmatched.append(record)
            continue

        law_name = (record.get("law_name") or "").lower().strip()
        if not law_name:
            unmatched.append(record)
            continue

        # Fuzzy match: check if law name appears as substring in catalog entries
        catalog = catalogs[scraper_key]
        best_match = None
        for entry in catalog:
            entry_name = (entry.get("name") or entry.get("law_name") or "").lower()
            if not entry_name:
                continue

            # Exact substring match or high overlap
            if law_name in entry_name or entry_name in law_name:
                best_match = entry
                break

            # Word overlap match
            law_words = set(law_name.split())
            entry_words = set(entry_name.split())
            overlap = len(law_words & entry_words)
            if overlap >= max(3, len(law_words) * 0.6):
                best_match = entry
                break

        if best_match:
            record["path_c_result"] = "matched"
            record["congress_match"] = {
                "name": best_match.get("name", ""),
                "url": best_match.get("url", ""),
            }
            matched.append(record)
        else:
            record["path_c_result"] = "no_match"
            unmatched.append(record)

    logger.info(
        "Path C complete: %d matched, %d unmatched (of %d)",
        len(matched),
        len(unmatched),
        len(target_records),
    )
    return matched, unmatched


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_recovery(
    paths: str = "abc",
    scope: str = "all",
    states: Optional[List[str]] = None,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Run the multi-path recovery pipeline.

    Args:
        paths: Which paths to run (e.g. "a", "ab", "abc")
        scope: "non_leg", "leg", or "all"
        states: Optional state filter
        dry_run: Report without downloading
        limit: Max items per path

    Returns:
        Summary dict with recovery statistics.
    """
    RECOVERY_OUTPUT.mkdir(parents=True, exist_ok=True)
    session = _setup_session()

    # Load all failed records
    all_failed = load_failed_records(scope=scope, states=states)

    if not all_failed:
        logger.info("No failed records found. Nothing to recover.")
        return {"total_failed": 0}

    # Group by failure reason for reporting
    by_reason: Dict[str, int] = {}
    for r in all_failed:
        reason = r.get("failure_reason", "unknown")
        by_reason[reason] = by_reason.get(reason, 0) + 1
    logger.info("Failure breakdown: %s", by_reason)

    summary: Dict[str, Any] = {
        "total_failed": len(all_failed),
        "failure_breakdown": by_reason,
        "paths_run": paths,
        "dry_run": dry_run,
    }

    remaining = all_failed
    all_recovered: List[Dict] = []

    # Path A: Re-fetch OJN metadata
    if "a" in paths:
        recovered_a, remaining = path_a_refetch_metadata(
            remaining, session, RECOVERY_OUTPUT / "path_a", dry_run=dry_run, limit=limit
        )
        all_recovered.extend(recovered_a)
        summary["path_a"] = {
            "recovered": len(recovered_a),
            "still_failed": len(remaining),
        }

    # Path B: Wayback CDX
    if "b" in paths:
        recovered_b, remaining = path_b_wayback_cdx(
            remaining, session, RECOVERY_OUTPUT / "path_b", dry_run=dry_run, limit=limit
        )
        all_recovered.extend(recovered_b)
        summary["path_b"] = {
            "recovered": len(recovered_b),
            "still_failed": len(remaining),
        }

    # Path C: State congress cross-reference
    if "c" in paths:
        matched_c, remaining = path_c_state_congress_xref(
            remaining, dry_run=dry_run, limit=limit
        )
        all_recovered.extend(matched_c)
        summary["path_c"] = {
            "matched": len(matched_c),
            "unmatched": len(remaining),
        }

    summary["total_recovered"] = len(all_recovered)
    summary["total_remaining"] = len(remaining)
    summary["recovery_rate"] = (
        f"{len(all_recovered) / len(all_failed) * 100:.1f}%" if all_failed else "N/A"
    )

    # Save recovery report
    report_path = RECOVERY_OUTPUT / "recovery_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info("Recovery report saved to %s", report_path)

    # Save recovered records
    if all_recovered and not dry_run:
        recovered_path = RECOVERY_OUTPUT / "recovered_records.json"
        with open(recovered_path, "w", encoding="utf-8") as f:
            json.dump(all_recovered, f, indent=2, ensure_ascii=False)
        logger.info("Recovered records saved to %s", recovered_path)

    # Save remaining failures
    if remaining:
        remaining_path = RECOVERY_OUTPUT / "remaining_failures.json"
        with open(remaining_path, "w", encoding="utf-8") as f:
            json.dump(remaining, f, indent=2, ensure_ascii=False)

    logger.info("=== Recovery Summary ===")
    logger.info("Total failed: %d", len(all_failed))
    logger.info("Total recovered: %d", len(all_recovered))
    logger.info("Recovery rate: %s", summary["recovery_rate"])

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OJN multi-path recovery for failed law downloads (Phase 17 W1).",
    )
    parser.add_argument(
        "--path",
        type=str,
        default="abc",
        help="Recovery paths to run: a, b, c, ab, abc (default: abc)",
    )
    parser.add_argument(
        "--scope",
        type=str,
        choices=["non_leg", "leg", "all"],
        default="all",
        help="Scope: non_leg, leg, or all (default: all)",
    )
    parser.add_argument(
        "--states",
        type=str,
        nargs="+",
        default=None,
        help="Filter to specific state directory names",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report without downloading",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max items per path (for testing)",
    )

    args = parser.parse_args()

    result = run_recovery(
        paths=args.path,
        scope=args.scope,
        states=args.states,
        dry_run=args.dry_run,
        limit=args.limit,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
