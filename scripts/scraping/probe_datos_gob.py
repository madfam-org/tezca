#!/usr/bin/env python3
"""
datos.gob.mx Open Data Probe (W7 — Phase 17)

Queries Mexico's CKAN-based open data portal for legal datasets:
legislation, regulations, NOMs, municipal ordinances, and judicial records.

Uses the CKAN API at https://datos.gob.mx/api/3/

Usage:
    python scripts/scraping/probe_datos_gob.py
    python scripts/scraping/probe_datos_gob.py --query "normas oficiales"
    python scripts/scraping/probe_datos_gob.py --download --limit 10
"""

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CKAN_BASE = "https://www.datos.gob.mx/api/3/action"
OUTPUT_DIR = Path("data/datos_gob")
REQUEST_DELAY = 1.0
USER_AGENT = "Tezca-DatosGob/1.0 (+https://tezca.mx)"

# Search queries for legal datasets
LEGAL_QUERIES = [
    "legislacion",
    "reglamento federal",
    "norma oficial mexicana",
    "codigo federal",
    "ley federal",
    "tratados internacionales",
    "jurisprudencia",
    "marco juridico",
    "regulacion",
    "normatividad",
    "decreto",
    "diario oficial",
    "municipio reglamento",
    "constitucion",
]

# Organizations likely to publish legal data
LEGAL_ORGS = [
    "consejeria-juridica-del-ejecutivo-federal",
    "secretaria-de-gobernacion",
    "suprema-corte-de-justicia-de-la-nacion",
    "comision-nacional-de-mejora-regulatoria",
    "diario-oficial-de-la-federacion",
    "instituto-de-investigaciones-juridicas-unam",
]


# ---------------------------------------------------------------------------
# CKAN API client
# ---------------------------------------------------------------------------


def _setup_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
    )
    return session


def ckan_search(
    session: requests.Session,
    query: str,
    rows: int = 50,
    start: int = 0,
) -> Dict[str, Any]:
    """Search CKAN for packages matching a query.

    Args:
        session: HTTP session.
        query: Search string.
        rows: Results per page.
        start: Offset.

    Returns:
        CKAN response dict with 'results' and 'count'.
    """
    url = f"{CKAN_BASE}/package_search"
    params = {"q": query, "rows": rows, "start": start}

    try:
        time.sleep(REQUEST_DELAY)
        resp = session.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return data.get("result", {})
    except (requests.RequestException, json.JSONDecodeError) as e:
        logger.warning("CKAN search error for '%s': %s", query, e)

    return {"count": 0, "results": []}


def ckan_show_package(session: requests.Session, package_id: str) -> Optional[Dict]:
    """Get full details for a CKAN package."""
    url = f"{CKAN_BASE}/package_show"
    try:
        time.sleep(REQUEST_DELAY)
        resp = session.get(url, params={"id": package_id}, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return data.get("result")
    except (requests.RequestException, json.JSONDecodeError) as e:
        logger.debug("Package show error: %s", e)
    return None


def ckan_org_show(session: requests.Session, org_id: str) -> Optional[Dict]:
    """Get organization details and dataset count."""
    url = f"{CKAN_BASE}/organization_show"
    try:
        time.sleep(REQUEST_DELAY)
        resp = session.get(
            url, params={"id": org_id, "include_datasets": "true"}, timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return data.get("result")
    except (requests.RequestException, json.JSONDecodeError):
        pass
    return None


# ---------------------------------------------------------------------------
# Resource analysis
# ---------------------------------------------------------------------------


def analyze_resources(package: Dict) -> List[Dict[str, Any]]:
    """Extract downloadable resource info from a CKAN package.

    Returns:
        List of resource dicts with download_url, format, size.
    """
    resources = []
    for res in package.get("resources", []):
        fmt = (res.get("format") or "").upper()
        url = res.get("url") or ""
        name = res.get("name") or res.get("description") or ""
        size = res.get("size")

        if not url:
            continue

        # Prioritize structured formats
        is_structured = fmt in ("CSV", "JSON", "XML", "XLSX", "XLS", "ZIP", "GEOJSON")

        resources.append(
            {
                "name": name,
                "url": url,
                "format": fmt,
                "size": size,
                "is_structured": is_structured,
            }
        )

    return resources


# ---------------------------------------------------------------------------
# Main probe
# ---------------------------------------------------------------------------


def run_probe(
    queries: Optional[List[str]] = None,
    check_orgs: bool = True,
    download_metadata: bool = False,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Run the datos.gob.mx probe.

    Args:
        queries: Search queries (None = all default legal queries).
        check_orgs: Also check known legal organizations.
        download_metadata: Save full metadata for found packages.
        limit: Max results per query.

    Returns:
        Summary dict.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    session = _setup_session()

    target_queries = queries or LEGAL_QUERIES
    rows_per_query = limit or 50

    summary: Dict[str, Any] = {
        "queries_run": len(target_queries),
        "total_datasets": 0,
        "total_resources": 0,
        "structured_resources": 0,
        "datasets": [],
        "by_query": {},
    }

    seen_ids: set = set()
    all_datasets: List[Dict] = []

    # Search by queries
    for query in target_queries:
        logger.info("Searching: '%s'", query)
        result = ckan_search(session, query, rows=rows_per_query)
        count = result.get("count", 0)
        packages = result.get("results", [])

        summary["by_query"][query] = {
            "total_count": count,
            "returned": len(packages),
        }

        for pkg in packages:
            pkg_id = pkg.get("id") or pkg.get("name")
            if pkg_id in seen_ids:
                continue
            seen_ids.add(pkg_id)

            resources = analyze_resources(pkg)
            structured = [r for r in resources if r["is_structured"]]

            dataset_info = {
                "id": pkg_id,
                "title": pkg.get("title", ""),
                "organization": pkg.get("organization", {}).get("title", ""),
                "notes": (pkg.get("notes") or "")[:200],
                "num_resources": len(resources),
                "structured_resources": len(structured),
                "formats": list(set(r["format"] for r in resources)),
                "matched_query": query,
                "url": f"https://datos.gob.mx/busca/dataset/{pkg_id}",
            }

            if structured:
                dataset_info["download_urls"] = [r["url"] for r in structured[:5]]

            all_datasets.append(dataset_info)
            summary["total_resources"] += len(resources)
            summary["structured_resources"] += len(structured)

    # Check known legal organizations
    org_results: Dict[str, Any] = {}
    if check_orgs:
        logger.info("Checking %d known legal organizations...", len(LEGAL_ORGS))
        for org_id in LEGAL_ORGS:
            org_data = ckan_org_show(session, org_id)
            if org_data:
                org_results[org_id] = {
                    "title": org_data.get("title", ""),
                    "package_count": org_data.get("package_count", 0),
                    "description": (org_data.get("description") or "")[:200],
                }
                logger.info(
                    "  %s: %d datasets",
                    org_data.get("title", org_id),
                    org_data.get("package_count", 0),
                )

                # Add organization datasets not already seen
                for pkg in org_data.get("packages", []):
                    pkg_id = pkg.get("id") or pkg.get("name")
                    if pkg_id not in seen_ids:
                        seen_ids.add(pkg_id)
                        all_datasets.append(
                            {
                                "id": pkg_id,
                                "title": pkg.get("title", ""),
                                "organization": org_data.get("title", ""),
                                "notes": (pkg.get("notes") or "")[:200],
                                "num_resources": len(pkg.get("resources", [])),
                                "matched_query": f"org:{org_id}",
                            }
                        )

    summary["total_datasets"] = len(all_datasets)
    summary["organizations"] = org_results
    summary["datasets"] = all_datasets

    # Save results
    report_path = OUTPUT_DIR / "datos_gob_probe_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info("Report saved to %s", report_path)

    # Save full dataset list
    datasets_path = OUTPUT_DIR / "discovered_datasets.json"
    with open(datasets_path, "w", encoding="utf-8") as f:
        json.dump(all_datasets, f, indent=2, ensure_ascii=False)

    logger.info("=== datos.gob.mx Probe Summary ===")
    logger.info("Queries run: %d", len(target_queries))
    logger.info("Total datasets: %d", len(all_datasets))
    logger.info(
        "Total resources: %d (structured: %d)",
        summary["total_resources"],
        summary["structured_resources"],
    )
    if org_results:
        total_org_packages = sum(
            o.get("package_count", 0) for o in org_results.values()
        )
        logger.info("Organization datasets: %d", total_org_packages)

    # Highlight high-value finds
    high_value = [d for d in all_datasets if d.get("structured_resources", 0) > 0]
    if high_value:
        logger.info("\n=== High-Value Datasets (with structured data) ===")
        for d in high_value[:20]:
            logger.info(
                "  %s — %s (%d structured resources)",
                d.get("title", "")[:60],
                d.get("organization", ""),
                d.get("structured_resources", 0),
            )

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe datos.gob.mx for legal datasets (Phase 17 W7).",
    )
    parser.add_argument(
        "--query",
        type=str,
        nargs="+",
        default=None,
        help="Custom search queries (default: all legal queries)",
    )
    parser.add_argument(
        "--no-orgs",
        action="store_true",
        help="Skip organization checks",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Save full metadata for found packages",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max results per query",
    )

    args = parser.parse_args()

    result = run_probe(
        queries=args.query,
        check_orgs=not args.no_orgs,
        download_metadata=args.download,
        limit=args.limit,
    )

    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "datasets"},
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
