#!/usr/bin/env python3
"""
Wayback Machine Bulk Recovery Script (W5 — Phase 17)

Uses the Internet Archive CDX API to comprehensively mine archived content
from dead Mexican legal domains.

Target domains:
  - sinec.gob.mx              → NOM standards catalog (~3,500 NOMs)
  - congresoguerrero.gob.mx   → Guerrero legislation (~200-400 laws)
  - consultapublica.plataformadetransparencia.org.mx → PNT municipal data
  - cnartys.conamer.gob.mx    → Old CONAMER portal (~50K regulations)
  - tratados.sre.gob.mx       → Legacy treaty portal (already recovered)

Process: CDX query → filter by status/mimetype → download from
  web.archive.org/web/{timestamp}/{url} → extract text → save.

Usage:
    python scripts/scraping/wayback_bulk_recovery.py --domain sinec.gob.mx --dry-run
    python scripts/scraping/wayback_bulk_recovery.py --all --limit 500
    python scripts/scraping/wayback_bulk_recovery.py --domain congresoguerrero.gob.mx
"""

import argparse
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

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

CDX_API_URL = "https://web.archive.org/cdx/search/cdx"
WAYBACK_PREFIX = "https://web.archive.org/web"

OUTPUT_DIR = Path("data/wayback_recovery")

REQUEST_DELAY = 1.0  # seconds between Wayback requests
DOWNLOAD_DELAY = 0.5  # seconds between archive downloads
CDX_PAGE_SIZE = 10_000  # CDX API pagination limit

USER_AGENT = "Tezca-WaybackRecovery/1.0 (+https://tezca.mx)"

# Target domains and their expected content types
DOMAINS: Dict[str, Dict[str, Any]] = {
    "sinec.gob.mx": {
        "description": "SINEC NOM standards catalog",
        "expected_items": 3_500,
        "url_filters": [
            r"\.pdf$",
            r"\.doc[x]?$",
            r"nom-\d+",
            r"norma",
            r"catalogo",
            r"ficha",
        ],
        "mime_filters": [
            "application/pdf",
            "application/msword",
            "text/html",
            "application/vnd.openxmlformats",
        ],
        "category": "noms",
    },
    "congresoguerrero.gob.mx": {
        "description": "Guerrero state legislation",
        "expected_items": 400,
        "url_filters": [
            r"\.pdf$",
            r"\.doc[x]?$",
            r"ley",
            r"codigo",
            r"reglamento",
            r"decreto",
            r"legislacion",
        ],
        "mime_filters": [
            "application/pdf",
            "application/msword",
            "text/html",
        ],
        "category": "state_laws",
    },
    "consultapublica.plataformadetransparencia.org.mx": {
        "description": "PNT SIPOT municipal transparency data",
        "expected_items": 10_000,
        "url_filters": [
            r"\.pdf$",
            r"\.doc[x]?$",
            r"\.xls[x]?$",
            r"reglamento",
            r"bando",
            r"normativ",
            r"sipot",
        ],
        "mime_filters": [
            "application/pdf",
            "application/msword",
            "text/html",
            "application/json",
        ],
        "category": "municipal",
    },
    "cnartys.conamer.gob.mx": {
        "description": "Old CONAMER regulatory catalog",
        "expected_items": 50_000,
        "url_filters": [
            r"\.pdf$",
            r"\.doc[x]?$",
            r"regulacion",
            r"norma",
            r"tramite",
            r"catalogo",
        ],
        "mime_filters": [
            "application/pdf",
            "application/msword",
            "text/html",
            "application/json",
        ],
        "category": "conamer",
    },
    "tratados.sre.gob.mx": {
        "description": "Legacy treaty portal (mostly recovered)",
        "expected_items": 1_500,
        "url_filters": [
            r"\.pdf$",
            r"tratado",
            r"convenio",
            r"acuerdo",
        ],
        "mime_filters": [
            "application/pdf",
            "text/html",
        ],
        "category": "treaties",
    },
}


# ---------------------------------------------------------------------------
# HTTP Session
# ---------------------------------------------------------------------------


def _setup_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


# ---------------------------------------------------------------------------
# CDX API querying
# ---------------------------------------------------------------------------


def query_cdx(
    session: requests.Session,
    domain: str,
    url_match: str = "*",
    limit: Optional[int] = None,
    from_timestamp: Optional[str] = None,
    to_timestamp: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Query Wayback CDX API for all archived URLs under a domain.

    Args:
        session: HTTP session.
        domain: Target domain (e.g. "sinec.gob.mx").
        url_match: URL pattern suffix (default: "*" for all).
        limit: Max results.
        from_timestamp: Start date (YYYYMMDD).
        to_timestamp: End date (YYYYMMDD).

    Returns:
        List of CDX record dicts with keys: timestamp, original, statuscode, mimetype, length.
    """
    params: Dict[str, Any] = {
        "url": f"{domain}/{url_match}" if url_match != "*" else f"{domain}/*",
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype,length",
        "filter": "statuscode:200",
        "collapse": "urlkey",  # Deduplicate by URL
    }

    if limit:
        params["limit"] = limit
    else:
        params["limit"] = CDX_PAGE_SIZE

    if from_timestamp:
        params["from"] = from_timestamp
    if to_timestamp:
        params["to"] = to_timestamp

    all_records: List[Dict[str, str]] = []
    page = 0

    while True:
        params["page"] = page
        logger.info("CDX query: domain=%s, page=%d", domain, page)

        try:
            time.sleep(REQUEST_DELAY)
            resp = session.get(CDX_API_URL, params=params, timeout=60)

            if resp.status_code != 200:
                logger.warning("CDX API returned %d for %s", resp.status_code, domain)
                break

            rows = resp.json()
            if not rows or len(rows) <= 1:  # header row only or empty
                break

            # First row is header
            header = rows[0]
            for row in rows[1:]:
                record = dict(zip(header, row))
                all_records.append(record)

            logger.info(
                "CDX page %d: %d records (total: %d)",
                page,
                len(rows) - 1,
                len(all_records),
            )

            # If we got fewer than limit, we're done
            if len(rows) - 1 < params["limit"]:
                break

            if limit and len(all_records) >= limit:
                all_records = all_records[:limit]
                break

            page += 1

        except (requests.RequestException, json.JSONDecodeError) as e:
            logger.error("CDX query error: %s", e)
            break

    logger.info("CDX total for %s: %d unique URLs", domain, len(all_records))
    return all_records


def filter_cdx_records(
    records: List[Dict[str, str]],
    domain_config: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Filter CDX records to likely legal documents.

    Args:
        records: Raw CDX records.
        domain_config: Domain configuration with url_filters and mime_filters.

    Returns:
        Filtered records matching legal document patterns.
    """
    url_patterns = [
        re.compile(p, re.IGNORECASE) for p in domain_config.get("url_filters", [])
    ]
    mime_filters = set(domain_config.get("mime_filters", []))

    filtered: List[Dict[str, str]] = []
    seen_urls: Set[str] = set()

    for record in records:
        url = record.get("original", "")
        mimetype = record.get("mimetype", "")

        # Deduplicate
        if url in seen_urls:
            continue

        # Skip non-useful mimetypes
        if mime_filters and not any(m in mimetype for m in mime_filters):
            continue

        # Skip common non-document URLs
        lower_url = url.lower()
        if any(
            skip in lower_url
            for skip in (".css", ".js", ".png", ".jpg", ".gif", ".ico", ".svg", ".woff")
        ):
            continue

        # Match at least one URL pattern (if patterns defined)
        if url_patterns:
            if not any(p.search(url) for p in url_patterns):
                continue

        seen_urls.add(url)
        filtered.append(record)

    logger.info(
        "Filtered %d → %d records for legal documents",
        len(records),
        len(filtered),
    )
    return filtered


# ---------------------------------------------------------------------------
# Download from Wayback
# ---------------------------------------------------------------------------


def download_archived_documents(
    session: requests.Session,
    records: List[Dict[str, str]],
    output_dir: Path,
    domain: str,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Download documents from the Wayback Machine archive.

    Args:
        session: HTTP session.
        records: Filtered CDX records.
        output_dir: Where to save files.
        domain: Source domain for organizing.
        dry_run: Report without downloading.
        limit: Max documents to download.

    Returns:
        Summary dict with download statistics.
    """
    if limit:
        records = records[:limit]

    domain_dir = output_dir / domain.replace(".", "_")
    domain_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "domain": domain,
        "total_candidates": len(records),
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "total_bytes": 0,
        "files": [],
    }

    if dry_run:
        # Report what we'd download
        by_mime: Dict[str, int] = {}
        for r in records:
            mime = r.get("mimetype", "unknown")
            by_mime[mime] = by_mime.get(mime, 0) + 1
        summary["mime_breakdown"] = by_mime
        logger.info("DRY RUN: would download %d files from %s", len(records), domain)
        logger.info("MIME breakdown: %s", by_mime)
        return summary

    for i, record in enumerate(records, 1):
        timestamp = record.get("timestamp", "")
        original_url = record.get("original", "")
        mimetype = record.get("mimetype", "")

        # Determine filename from URL
        parsed = urlparse(original_url)
        path_parts = parsed.path.strip("/").split("/")
        filename = path_parts[-1] if path_parts else f"doc_{i}"

        # Clean filename
        filename = re.sub(r"[^\w\s.\-]", "_", filename)[:150]
        if not filename or filename == "_":
            filename = f"doc_{timestamp}_{i}"

        # Add extension based on mimetype if missing
        if "." not in filename:
            ext_map = {
                "application/pdf": ".pdf",
                "application/msword": ".doc",
                "text/html": ".html",
                "application/json": ".json",
            }
            for mime_key, ext in ext_map.items():
                if mime_key in mimetype:
                    filename += ext
                    break
            else:
                filename += ".bin"

        file_path = domain_dir / filename

        # Skip if already downloaded
        if file_path.exists() and file_path.stat().st_size > 100:
            summary["skipped"] += 1
            continue

        archive_url = f"{WAYBACK_PREFIX}/{timestamp}id_/{original_url}"

        try:
            time.sleep(DOWNLOAD_DELAY)
            resp = session.get(archive_url, timeout=60)

            if resp.status_code == 200 and len(resp.content) > 100:
                file_path.write_bytes(resp.content)
                summary["downloaded"] += 1
                summary["total_bytes"] += len(resp.content)
                summary["files"].append(
                    {
                        "path": str(file_path),
                        "original_url": original_url,
                        "timestamp": timestamp,
                        "size": len(resp.content),
                    }
                )
            else:
                summary["failed"] += 1

        except requests.RequestException as e:
            summary["failed"] += 1
            logger.debug("Download failed for %s: %s", archive_url, e)

        if i % 100 == 0:
            logger.info(
                "Download progress: %d/%d (downloaded: %d, failed: %d)",
                i,
                len(records),
                summary["downloaded"],
                summary["failed"],
            )

    logger.info(
        "Downloads complete for %s: %d downloaded, %d skipped, %d failed",
        domain,
        summary["downloaded"],
        summary["skipped"],
        summary["failed"],
    )
    return summary


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_bulk_recovery(
    domains: Optional[List[str]] = None,
    dry_run: bool = False,
    limit: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Run Wayback Machine bulk recovery for dead legal domains.

    Args:
        domains: List of domains to query (None = all configured).
        dry_run: Report without downloading.
        limit: Max records per domain.
        from_date: CDX from timestamp (YYYYMMDD).
        to_date: CDX to timestamp (YYYYMMDD).

    Returns:
        Summary dict with per-domain statistics.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    session = _setup_session()

    target_domains = domains or list(DOMAINS.keys())
    summary: Dict[str, Any] = {
        "domains_queried": target_domains,
        "dry_run": dry_run,
        "results": {},
        "total_discovered": 0,
        "total_filtered": 0,
        "total_downloaded": 0,
    }

    for domain in target_domains:
        if domain not in DOMAINS:
            logger.warning("Unknown domain: %s (skipping)", domain)
            continue

        config = DOMAINS[domain]
        logger.info("=== Processing: %s (%s) ===", domain, config["description"])

        # Step 1: Query CDX
        raw_records = query_cdx(
            session,
            domain,
            limit=limit,
            from_timestamp=from_date,
            to_timestamp=to_date,
        )
        summary["total_discovered"] += len(raw_records)

        if not raw_records:
            summary["results"][domain] = {
                "cdx_records": 0,
                "filtered": 0,
                "downloaded": 0,
            }
            continue

        # Step 2: Filter to legal documents
        filtered = filter_cdx_records(raw_records, config)
        summary["total_filtered"] += len(filtered)

        # Step 3: Download
        dl_result = download_archived_documents(
            session,
            filtered,
            OUTPUT_DIR,
            domain,
            dry_run=dry_run,
            limit=limit,
        )
        summary["total_downloaded"] += dl_result.get("downloaded", 0)

        summary["results"][domain] = {
            "cdx_records": len(raw_records),
            "filtered": len(filtered),
            "downloaded": dl_result.get("downloaded", 0),
            "skipped": dl_result.get("skipped", 0),
            "failed": dl_result.get("failed", 0),
            "total_bytes": dl_result.get("total_bytes", 0),
        }
        if dry_run:
            summary["results"][domain]["mime_breakdown"] = dl_result.get(
                "mime_breakdown", {}
            )

    # Save report
    report_path = OUTPUT_DIR / "wayback_recovery_report.json"
    # Strip file lists from report for readability
    report_summary = json.loads(json.dumps(summary))
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_summary, f, indent=2, ensure_ascii=False)
    logger.info("Report saved to %s", report_path)

    logger.info("=== Wayback Bulk Recovery Summary ===")
    logger.info("Domains: %d", len(target_domains))
    logger.info("CDX records discovered: %d", summary["total_discovered"])
    logger.info("Filtered to legal docs: %d", summary["total_filtered"])
    logger.info("Downloaded: %d", summary["total_downloaded"])

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wayback Machine bulk recovery for dead Mexican legal domains (Phase 17 W5).",
    )
    parser.add_argument(
        "--domain",
        type=str,
        nargs="+",
        default=None,
        help="Specific domains to query (default: all configured)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Query all configured domains",
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
        help="Max records per domain",
    )
    parser.add_argument(
        "--from-date",
        type=str,
        default=None,
        help="CDX from timestamp (YYYYMMDD)",
    )
    parser.add_argument(
        "--to-date",
        type=str,
        default=None,
        help="CDX to timestamp (YYYYMMDD)",
    )
    parser.add_argument(
        "--list-domains",
        action="store_true",
        help="List all configured domains and exit",
    )

    args = parser.parse_args()

    if args.list_domains:
        for domain, config in DOMAINS.items():
            print(
                f"  {domain:55s} {config['description']} (~{config['expected_items']:,} items)"
            )
        return

    domains = (
        args.domain if args.domain else (list(DOMAINS.keys()) if args.all else None)
    )

    if not domains:
        parser.error("Specify --domain <name> or --all")

    result = run_bulk_recovery(
        domains=domains,
        dry_run=args.dry_run,
        limit=args.limit,
        from_date=args.from_date,
        to_date=args.to_date,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
