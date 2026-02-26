#!/usr/bin/env python3
"""
Exhaustive NOM search via DOF archive.

Searches for every NOM number prefix (NOM-001 through NOM-260), plus
per-secretaria and per-year queries, deduplicating by nom_number.
Merges with existing discovered_noms.json.

Usage:
    poetry run python scripts/scraping/run_overnight_noms.py
"""

import json
import logging
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.scraper.http import government_session

from apps.scraper.federal.nom_scraper import NomScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

OUTPUT_PATH = PROJECT_ROOT / "data" / "federal" / "noms" / "discovered_noms.json"

# ---------------------------------------------------------------------------
# Search matrix
# ---------------------------------------------------------------------------


def build_search_queries():
    """Build the full search matrix (~290 queries)."""
    queries = []

    # Per-number: NOM-001 through NOM-260
    for i in range(1, 261):
        queries.append(f"NOM-{i:03d}")

    # Per-secretaria
    secretarias = [
        "NOM SSA",
        "NOM SEMARNAT",
        "NOM STPS",
        "NOM SCT",
        "NOM SE",
        "NOM SAGARPA",
        "NOM SENER",
        "NOM CONAGUA",
        "NOM SCFI",
        "NOM SEDATU",
    ]
    queries.extend(secretarias)

    # Per-year
    for year in range(2015, 2027):
        queries.append(f"NOM {year}")

    # By keyword
    keywords = [
        "Norma Oficial Mexicana salud",
        "Norma Oficial Mexicana seguridad",
        "Norma Oficial Mexicana alimentos",
        "Norma Oficial Mexicana construccion",
        "Norma Oficial Mexicana ambiental",
    ]
    queries.extend(keywords)

    return queries


def load_existing():
    """Load existing NOMs from disk."""
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def merge_noms(existing, new_noms):
    """Merge new NOMs into existing, dedup by nom_number."""
    seen = {n["nom_number"] for n in existing}
    merged = list(existing)
    added = 0
    for nom in new_noms:
        key = nom.get("nom_number", "")
        if key and key not in seen:
            seen.add(key)
            merged.append(nom)
            added += 1
    return merged, added


def save_noms(noms):
    """Save NOMs to disk."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(noms, f, indent=2, ensure_ascii=False)


def main():
    start = time.time()
    logger.info("=== Exhaustive NOM Search Starting ===")

    scraper = NomScraper()
    scraper.session = government_session("https://dof.gob.mx")

    existing = load_existing()
    logger.info("Loaded %d existing NOMs", len(existing))

    queries = build_search_queries()
    logger.info("Search matrix: %d queries", len(queries))

    all_new = []
    seen_numbers = {n["nom_number"] for n in existing}
    queries_completed = 0
    queries_with_results = 0

    for i, query in enumerate(queries, 1):
        logger.info("[%d/%d] Searching: %s", i, len(queries), query)
        try:
            results = scraper.scrape_dof_archive(
                search_term=query,
                max_results=100,
            )
            new_in_query = 0
            for nom in results:
                key = nom.get("nom_number", "")
                if key and key not in seen_numbers:
                    seen_numbers.add(key)
                    all_new.append(nom)
                    new_in_query += 1

            if new_in_query > 0:
                queries_with_results += 1
                logger.info(
                    "  -> %d new NOMs (running total new: %d)",
                    new_in_query,
                    len(all_new),
                )

        except Exception as e:
            logger.error("  -> Error on query '%s': %s", query, e)

        queries_completed += 1

        # Checkpoint every 50 queries
        if queries_completed % 50 == 0:
            merged, _ = merge_noms(existing, all_new)
            save_noms(merged)
            logger.info("Checkpoint: %d total NOMs saved", len(merged))

    # Final save
    merged, added = merge_noms(existing, all_new)
    save_noms(merged)

    elapsed = time.time() - start
    logger.info("=== Exhaustive NOM Search Complete ===")
    logger.info(
        "Queries: %d total, %d with new results", len(queries), queries_with_results
    )
    logger.info(
        "NOMs: %d existing + %d new = %d total", len(existing), added, len(merged)
    )
    logger.info("Duration: %.1f minutes", elapsed / 60)


if __name__ == "__main__":
    main()
