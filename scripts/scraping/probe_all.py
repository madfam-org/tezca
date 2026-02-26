#!/usr/bin/env python3
"""
Probe all municipal + federal scrapers: catalog-only discovery.
Reports which portals respond and how many items each returns.

Usage:
    python scripts/scraping/probe_all.py
    python scripts/scraping/probe_all.py --municipal-only
    python scripts/scraping/probe_all.py --federal-only
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.scraper.http import government_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def probe_municipal():
    """Probe all configured municipal portals."""
    from apps.scraper.municipal.config import MUNICIPALITY_CONFIGS
    from apps.scraper.municipal.generic import GenericMunicipalScraper

    results = {}
    for city_key, config in MUNICIPALITY_CONFIGS.items():
        logger.info("=== Probing %s (%s) ===", config["name"], config["state"])
        try:
            scraper = GenericMunicipalScraper(city_key)
            catalog = scraper.scrape_catalog()
            count = len(catalog)
            results[city_key] = {
                "name": config["name"],
                "state": config["state"],
                "tier": config["tier"],
                "count": count,
                "status": "ok" if count > 0 else "empty",
                "sample": catalog[0]["name"] if catalog else None,
            }
            logger.info("[%s] Found %d items", city_key, count)
        except Exception as e:
            results[city_key] = {
                "name": config["name"],
                "state": config["state"],
                "tier": config["tier"],
                "count": 0,
                "status": f"error: {e}",
            }
            logger.error("[%s] Error: %s", city_key, e)
        time.sleep(2)  # Be polite between cities

    return results


def probe_federal():
    """Probe federal scrapers with SSL workarounds."""
    results = {}

    # --- NOMs (DOF) ---
    logger.info("=== Probing NOMs (DOF) ===")
    try:
        from apps.scraper.federal.nom_scraper import NomScraper

        scraper = NomScraper()
        scraper.session = government_session("https://dof.gob.mx")
        # Quick probe: search for 1 page of NOM results
        noms = scraper.scrape_dof_archive(search_term="NOM-001-SSA", max_pages=1)
        results["noms"] = {
            "count": len(noms),
            "status": "ok" if noms else "empty",
            "sample": noms[0].get("nom_id") if noms else None,
        }
        logger.info("[NOMs] Found %d items from DOF", len(noms))
    except Exception as e:
        results["noms"] = {"count": 0, "status": f"error: {e}"}
        logger.error("[NOMs] Error: %s", e)

    # --- CONAMER ---
    logger.info("=== Probing CONAMER ===")
    try:
        from apps.scraper.federal.conamer_scraper import ConamerScraper

        scraper = ConamerScraper()
        scraper.session = government_session("https://cnartys.conamer.gob.mx")
        probe_result = scraper.probe_api()
        results["conamer"] = {
            "count": 0,
            "status": "api_found" if probe_result.get("found") else "no_api",
            "probed": probe_result.get("probed", []),
            "endpoint": probe_result.get("endpoint"),
        }
        if probe_result.get("found"):
            logger.info("[CONAMER] API found: %s", probe_result["endpoint"])
        else:
            logger.warning(
                "[CONAMER] No API discovered, probed %d paths",
                len(probe_result.get("probed", [])),
            )
    except Exception as e:
        results["conamer"] = {"count": 0, "status": f"error: {e}"}
        logger.error("[CONAMER] Error: %s", e)

    # --- Treaties ---
    logger.info("=== Probing Treaties (SRE) ===")
    try:
        from apps.scraper.federal.treaty_scraper import TreatyScraper

        scraper = TreatyScraper()
        scraper.session = government_session("https://tratados.sre.gob.mx")
        # Try the base URL directly
        s = government_session("https://tratados.sre.gob.mx")
        try:
            r = s.get("https://tratados.sre.gob.mx", timeout=15)
            results["treaties"] = {
                "count": 0,
                "status": f"reachable (HTTP {r.status_code})",
                "content_length": len(r.text),
            }
            logger.info("[Treaties] SRE portal reachable, HTTP %d", r.status_code)
        except Exception as e2:
            results["treaties"] = {"count": 0, "status": f"unreachable: {e2}"}
            logger.error("[Treaties] SRE portal unreachable: %s", e2)
    except Exception as e:
        results["treaties"] = {"count": 0, "status": f"error: {e}"}
        logger.error("[Treaties] Error: %s", e)

    return results


def main():
    parser = argparse.ArgumentParser(description="Probe all scrapers")
    parser.add_argument("--municipal-only", action="store_true")
    parser.add_argument("--federal-only", action="store_true")
    args = parser.parse_args()

    all_results = {}

    if not args.federal_only:
        logger.info("=" * 60)
        logger.info("MUNICIPAL PROBES")
        logger.info("=" * 60)
        all_results["municipal"] = probe_municipal()

    if not args.municipal_only:
        logger.info("=" * 60)
        logger.info("FEDERAL PROBES")
        logger.info("=" * 60)
        all_results["federal"] = probe_federal()

    # Summary
    print("\n" + "=" * 70)
    print("PROBE SUMMARY")
    print("=" * 70)

    if "municipal" in all_results:
        print("\nMUNICIPAL:")
        total_muni = 0
        for city, info in sorted(all_results["municipal"].items()):
            status = "OK" if info["count"] > 0 else info.get("status", "?")
            print(f"  {info['name']:30s} | {info['count']:4d} items | {status}")
            total_muni += info["count"]
        print(f"  {'TOTAL':30s} | {total_muni:4d} items")

    if "federal" in all_results:
        print("\nFEDERAL:")
        for source, info in all_results["federal"].items():
            print(f"  {source:30s} | {info['count']:4d} items | {info['status']}")

    # Save results
    out_path = PROJECT_ROOT / "data" / "probe_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
