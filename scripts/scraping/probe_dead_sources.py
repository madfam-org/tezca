#!/usr/bin/env python3
"""
Probe decommissioned government data sources for availability.

Checks DNS resolution, HTTP reachability, Wayback Machine archives,
and known successor URLs for portals that went offline.

Current targets:
  - cnartys.conamer.gob.mx  (CONAMER CNARTyS - 113K regulatory instruments)
  - tratados.sre.gob.mx     (SRE Treaties - 1.5K treaties)

Usage:
    python scripts/scraping/probe_dead_sources.py
    python scripts/scraping/probe_dead_sources.py --output data/probe_results.json
"""

import argparse
import json
import logging
import socket
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests

from apps.scraper.http import government_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Source definitions
# -----------------------------------------------------------------------

DEAD_SOURCES: dict[str, dict[str, Any]] = {
    "conamer_cnartys": {
        "url": "https://cnartys.conamer.gob.mx/",
        "description": "CONAMER CNARTyS - National Catalog of Regulations",
        "expected_items": "150K+ regulatory instruments",
        "last_known_alive": "2025-06",
        "confirmed_dead": True,
        "successor_urls": [
            # Confirmed successor (Feb 2026) — returns 403 to automated HTTP
            "https://catalogonacional.gob.mx",
            # Legacy alt — expired SSL cert as of Feb 2026
            "https://conamer.gob.mx/cnartys-t/Login",
            "https://www.gob.mx/conamer",
        ],
        "recovery_note": (
            "Successor is catalogonacional.gob.mx (CNARTyS migrated). "
            "WAF blocks automated requests (403). Needs browser-based scraping. "
            "Scraper updated: apps/scraper/federal/conamer_scraper.py."
        ),
    },
    "sre_treaties": {
        "url": "https://tratados.sre.gob.mx/",
        "description": "SRE Treaties Portal - International treaties of Mexico",
        "expected_items": "1,509 treaties",
        "last_known_alive": "2025-06",
        "confirmed_dead": True,
        "successor_urls": [
            # Confirmed successor (Feb 2026) — Biblioteca Virtual, live
            "https://cja.sre.gob.mx/tratadosmexico/home",
            "https://cja.sre.gob.mx/tratadosmexico/buscador",
            # Alternative databases
            "https://aplicaciones.sre.gob.mx/tratados/depositario.php",
            "https://www.senado.gob.mx/65/tratados_internacionales_aprobados",
        ],
        "recovery_note": (
            "Successor is cja.sre.gob.mx/tratadosmexico/ (live, 1,509 treaties). "
            "Server-rendered HTML at /buscador?page=N, 151 pages. "
            "Scraper updated and ready: apps/scraper/federal/treaty_scraper.py."
        ),
    },
}

PROBE_TIMEOUT = 10  # seconds
WAYBACK_TIMEMAP_URL = "https://web.archive.org/web/timemap/json"


# -----------------------------------------------------------------------
# DNS probe
# -----------------------------------------------------------------------


def probe_dns(hostname: str) -> bool:
    """Return True if *hostname* resolves via DNS."""
    try:
        socket.getaddrinfo(hostname, 443, proto=socket.IPPROTO_TCP)
        return True
    except (socket.gaierror, OSError):
        return False


# -----------------------------------------------------------------------
# HTTP probe
# -----------------------------------------------------------------------


def probe_http(url: str) -> Optional[int]:
    """Try GET *url* and return the HTTP status code, or None on failure."""
    try:
        session = government_session(url)
        resp = session.get(url, timeout=PROBE_TIMEOUT, allow_redirects=True)
        return resp.status_code
    except requests.RequestException as exc:
        logger.debug("HTTP probe failed for %s: %s", url, exc)
        return None


# -----------------------------------------------------------------------
# Wayback Machine probe
# -----------------------------------------------------------------------


def probe_wayback(url: str) -> dict[str, Any]:
    """Check Wayback Machine for archived snapshots of *url*.

    Returns a dict with ``available`` (bool), ``snapshot_count`` (int),
    and ``latest_date`` (str or None, YYYY-MM-DD).
    """
    result: dict[str, Any] = {
        "available": False,
        "snapshot_count": 0,
        "latest_date": None,
    }
    try:
        resp = requests.get(
            WAYBACK_TIMEMAP_URL,
            params={
                "url": url,
                "limit": 5,
                "output": "json",
            },
            timeout=PROBE_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.debug("Wayback timemap returned %d for %s", resp.status_code, url)
            return result

        data = resp.json()
        # The timemap JSON response is an array of arrays.  The first row
        # is a header row; subsequent rows are snapshots.
        if not isinstance(data, list) or len(data) <= 1:
            return result

        snapshots = data[1:]  # skip header row
        result["available"] = True
        result["snapshot_count"] = len(snapshots)

        # Each snapshot row: [urlkey, timestamp, original, mimetype, statuscode,
        #                     digest, length]
        # The timestamp is in yyyyMMddHHmmss format.
        latest_ts = max(row[1] for row in snapshots if len(row) > 1)
        try:
            dt = datetime.strptime(latest_ts, "%Y%m%d%H%M%S")
            result["latest_date"] = dt.strftime("%Y-%m-%d")
        except (ValueError, IndexError):
            result["latest_date"] = latest_ts[:10] if len(latest_ts) >= 10 else None

    except (requests.RequestException, json.JSONDecodeError, KeyError) as exc:
        logger.debug("Wayback probe failed for %s: %s", url, exc)

    return result


# -----------------------------------------------------------------------
# Successor URL probe
# -----------------------------------------------------------------------


def probe_successor(url: str) -> dict[str, Any]:
    """Probe a potential successor URL and report status + final URL."""
    result: dict[str, Any] = {"status": None, "redirects_to": None, "error": None}
    try:
        session = government_session(url)
        resp = session.get(url, timeout=PROBE_TIMEOUT, allow_redirects=True)
        result["status"] = resp.status_code
        if resp.url != url:
            result["redirects_to"] = resp.url
    except requests.ConnectionError:
        result["error"] = "connection_refused"
    except socket.gaierror:
        result["error"] = "dns_failure"
    except requests.Timeout:
        result["error"] = "timeout"
    except requests.RequestException as exc:
        result["error"] = str(exc)[:120]
    return result


# -----------------------------------------------------------------------
# Recommendation engine
# -----------------------------------------------------------------------


def generate_recommendation(report: dict[str, Any]) -> str:
    """Produce a short recommendation string from the probe results."""
    parts: list[str] = []

    if report.get("dns_resolves") and report.get("http_status") in range(200, 400):
        return "Source appears to be back online -- re-run the scraper"

    # Check successors
    live_successors = [
        url
        for url, info in report.get("successor_urls", {}).items()
        if isinstance(info, dict) and info.get("status") in range(200, 400)
    ]
    if live_successors:
        parts.append(f"Successor URL(s) live: {', '.join(live_successors)}")

    # Check Wayback
    wb = report.get("wayback", {})
    if wb.get("available"):
        parts.append(
            f"Wayback Machine has archives (latest: {wb.get('latest_date', 'unknown')})"
        )

    if not parts:
        return "No alternative sources found -- manual investigation required"

    return "; ".join(parts)


# -----------------------------------------------------------------------
# Full probe for a single source
# -----------------------------------------------------------------------


def probe_source(key: str, source: dict[str, Any]) -> dict[str, Any]:
    """Run all checks against one source definition.  Returns a result dict."""
    url = source["url"]
    hostname = url.split("//")[-1].split("/")[0]

    logger.info("--- Probing %s (%s) ---", key, hostname)

    report: dict[str, Any] = {
        "url": url,
        "description": source["description"],
        "expected_items": source["expected_items"],
        "last_known_alive": source["last_known_alive"],
    }

    # 1. DNS resolution
    dns_ok = probe_dns(hostname)
    report["dns_resolves"] = dns_ok
    logger.info("  DNS resolves: %s", dns_ok)

    # 2. HTTP probe (only if DNS worked)
    if dns_ok:
        status = probe_http(url)
        report["http_status"] = status
        logger.info("  HTTP status: %s", status)
    else:
        report["http_status"] = None
        logger.info("  HTTP status: skipped (DNS failed)")

    # 3. Wayback Machine
    wb = probe_wayback(url)
    report["wayback_available"] = wb["available"]
    report["wayback_latest"] = wb["latest_date"]
    report["wayback_snapshot_count"] = wb["snapshot_count"]
    logger.info(
        "  Wayback: available=%s, latest=%s, snapshots=%d",
        wb["available"],
        wb["latest_date"],
        wb["snapshot_count"],
    )

    # 4. Successor URLs
    successor_results: dict[str, dict[str, Any]] = {}
    for succ_url in source.get("successor_urls", []):
        logger.info("  Probing successor: %s", succ_url)
        successor_results[succ_url] = probe_successor(succ_url)
        status_info = successor_results[succ_url]
        logger.info(
            "    status=%s, redirect=%s, error=%s",
            status_info.get("status"),
            status_info.get("redirects_to"),
            status_info.get("error"),
        )
    report["successor_urls"] = successor_results

    # 5. Recommendation
    report["recommendation"] = generate_recommendation(report)
    logger.info("  Recommendation: %s", report["recommendation"])

    return report


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------


def run_probes() -> dict[str, Any]:
    """Execute all probes and return the full report dict."""
    results: dict[str, Any] = {
        "probe_date": date.today().isoformat(),
        "sources": {},
    }
    for key, source in DEAD_SOURCES.items():
        results["sources"][key] = probe_source(key, source)
    return results


def print_summary(report: dict[str, Any]) -> None:
    """Print a human-readable summary to stdout."""
    print()
    print("=" * 72)
    print(f"  Dead Source Probe Report  --  {report['probe_date']}")
    print("=" * 72)

    for key, src in report["sources"].items():
        print()
        print(f"  [{key}]  {src['url']}")
        print(f"  Description:    {src['description']}")
        print(f"  Expected data:  {src['expected_items']}")
        print(f"  Last alive:     {src['last_known_alive']}")
        print()
        print(f"  DNS resolves:   {src['dns_resolves']}")
        print(f"  HTTP status:    {src['http_status']}")
        print(
            f"  Wayback:        {'YES' if src['wayback_available'] else 'NO'}"
            f"  (latest: {src['wayback_latest'] or 'n/a'},"
            f" snapshots: {src['wayback_snapshot_count']})"
        )
        print()

        succ = src.get("successor_urls", {})
        if succ:
            print("  Successor URLs:")
            for url, info in succ.items():
                status = info.get("status") or info.get("error", "unknown")
                redir = info.get("redirects_to")
                line = f"    {url}  ->  {status}"
                if redir:
                    line += f"  (redirects to {redir})"
                print(line)
            print()

        print(f"  >> {src['recommendation']}")
        print("-" * 72)

    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe decommissioned government data sources."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "probe_results.json",
        help="Path for JSON report (default: data/probe_results.json)",
    )
    args = parser.parse_args()

    report = run_probes()

    # Write JSON report
    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    logger.info("JSON report written to %s", output_path)

    # Print summary
    print_summary(report)


if __name__ == "__main__":
    main()
