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
import csv
import io
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
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

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
# Resource download and assessment
# ---------------------------------------------------------------------------

LEGAL_COLUMN_KEYWORDS = [
    "ley",
    "reglamento",
    "norma",
    "decreto",
    "articulo",
    "código",
    "codigo",
    "legislacion",
    "regulacion",
    "ordenamiento",
    "disposicion",
    "jurisprudencia",
    "constitución",
    "constitucion",
]


def download_resources(
    datasets_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Download structured resources from discovered datasets.

    Args:
        datasets_path: Path to discovered_datasets.json.
        output_dir: Root directory for downloaded resources.
        limit: Max datasets to process.

    Returns:
        Summary with download counts and any errors.
    """
    ds_path = datasets_path or (OUTPUT_DIR / "discovered_datasets.json")
    out_dir = output_dir or (OUTPUT_DIR / "resources")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not ds_path.exists():
        logger.warning("No discovered datasets at %s", ds_path)
        return {"error": "no_datasets_file"}

    datasets = json.loads(ds_path.read_text(encoding="utf-8"))
    session = _setup_session()

    downloaded = 0
    skipped = 0
    errors = 0
    processed = 0

    for dataset in datasets:
        if limit and processed >= limit:
            break

        urls = dataset.get("download_urls", [])
        if not urls:
            continue

        processed += 1
        ds_id = dataset.get("id", "unknown")
        ds_dir = out_dir / ds_id
        ds_dir.mkdir(parents=True, exist_ok=True)

        for url in urls:
            # Derive filename from URL
            filename = url.split("/")[-1].split("?")[0]
            if not filename or len(filename) < 3:
                filename = f"resource_{downloaded}.dat"
            file_path = ds_dir / filename

            # Skip existing files (idempotent)
            if file_path.exists() and file_path.stat().st_size > 0:
                skipped += 1
                continue

            try:
                time.sleep(REQUEST_DELAY)
                resp = session.get(url, timeout=60, stream=True)
                if resp.status_code == 200:
                    with open(file_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    downloaded += 1
                    logger.info("Downloaded: %s (%s)", filename, ds_id)
                else:
                    errors += 1
                    logger.debug("HTTP %d for %s", resp.status_code, url)
            except requests.RequestException as e:
                errors += 1
                logger.debug("Download error for %s: %s", url, e)

    summary = {
        "datasets_processed": processed,
        "downloaded": downloaded,
        "skipped_existing": skipped,
        "errors": errors,
        "output_dir": str(out_dir),
    }
    logger.info("Download complete: %s", summary)
    return summary


def assess_resources(
    resources_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Assess downloaded resources for legal relevance.

    Reads CSV headers from downloaded files and flags those with
    legal-related column names.

    Args:
        resources_dir: Directory containing downloaded resources.

    Returns:
        Dict with high_relevance and low_relevance lists.
    """
    res_dir = resources_dir or (OUTPUT_DIR / "resources")
    if not res_dir.exists():
        return {"error": "resources_dir_not_found"}

    high_relevance: List[Dict[str, Any]] = []
    low_relevance: List[Dict[str, Any]] = []

    for ds_dir in sorted(res_dir.iterdir()):
        if not ds_dir.is_dir():
            continue

        for file_path in ds_dir.iterdir():
            if file_path.suffix.lower() not in (".csv", ".tsv"):
                continue

            try:
                raw = file_path.read_bytes()[:4096]
                text = raw.decode("utf-8", errors="replace")
                reader = csv.reader(io.StringIO(text))
                headers = next(reader, [])
                headers_lower = [h.lower().strip() for h in headers]

                has_legal = any(
                    kw in col for col in headers_lower for kw in LEGAL_COLUMN_KEYWORDS
                )

                entry = {
                    "file": str(file_path),
                    "dataset_id": ds_dir.name,
                    "columns": headers[:20],
                    "num_columns": len(headers),
                }

                if has_legal:
                    entry["matched_keywords"] = [
                        kw
                        for col in headers_lower
                        for kw in LEGAL_COLUMN_KEYWORDS
                        if kw in col
                    ]
                    high_relevance.append(entry)
                else:
                    low_relevance.append(entry)

            except Exception as e:
                logger.debug("Error reading %s: %s", file_path, e)

    result = {
        "high_relevance": high_relevance,
        "low_relevance": low_relevance,
        "high_count": len(high_relevance),
        "low_count": len(low_relevance),
    }

    # Save assessment
    assess_path = OUTPUT_DIR / "resource_assessment.json"
    with open(assess_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    logger.info(
        "Assessment: %d high relevance, %d low relevance",
        len(high_relevance),
        len(low_relevance),
    )

    return result


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

    parser.add_argument(
        "--assess",
        action="store_true",
        help="Assess downloaded resources for legal relevance",
    )

    args = parser.parse_args()

    # Download mode: download structured resources from discovered datasets
    if args.download:
        dl_result = download_resources(limit=args.limit)
        print(json.dumps(dl_result, indent=2, ensure_ascii=False))
        if args.assess:
            assess_result = assess_resources()
            print(json.dumps(assess_result, indent=2, ensure_ascii=False))
        return

    # Assess-only mode
    if args.assess:
        assess_result = assess_resources()
        print(json.dumps(assess_result, indent=2, ensure_ascii=False))
        return

    result = run_probe(
        queries=args.query,
        check_orgs=not args.no_orgs,
        download_metadata=False,
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
