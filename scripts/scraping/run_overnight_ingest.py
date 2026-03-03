#!/usr/bin/env python3
"""
Overnight Data Ingestion Orchestrator.

Ingests already-scraped data (state laws, municipal laws, NOMs) into the DB,
runs the treaty scraper against a live source, and optionally re-indexes ES.

Usage:
    nohup poetry run python scripts/scraping/run_overnight_ingest.py \
        > logs/overnight_ingest.log 2>&1 &

    # Quick run (skip extended NOM search + ES re-index):
    poetry run python scripts/scraping/run_overnight_ingest.py \
        --skip-nom-search --skip-es-index

    # Dry run:
    poetry run python scripts/scraping/run_overnight_ingest.py --dry-run
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.indigo.settings")

import django

django.setup()

from django.core.management import call_command
from django.db.models import Count

from apps.api.models import Law

LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("overnight_ingest")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_db_counts():
    """Return a dict of law counts by tier."""
    counts = {}
    for row in Law.objects.values("tier").annotate(c=Count("id")).order_by("-c"):
        counts[row["tier"]] = row["c"]
    counts["total"] = Law.objects.count()
    return counts


def print_counts(label, counts):
    """Print a formatted summary of DB counts."""
    logger.info("--- %s ---", label)
    for tier, count in sorted(counts.items()):
        if tier != "total":
            logger.info("  %-20s %6d", tier, count)
    logger.info("  %-20s %6d", "TOTAL", counts.get("total", 0))


def timed_phase(name):
    """Decorator/context manager for timing phases."""

    class Timer:
        def __init__(self):
            self.start = None
            self.elapsed = 0

        def __enter__(self):
            logger.info("=" * 70)
            logger.info("PHASE: %s", name)
            logger.info("=" * 70)
            self.start = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.elapsed = time.time() - self.start
            if exc_type:
                logger.error(
                    "PHASE %s FAILED after %.1fs: %s", name, self.elapsed, exc_val
                )
            else:
                logger.info("PHASE %s completed in %.1fs", name, self.elapsed)
            return True  # suppress exceptions so subsequent phases run

    return Timer()


# ---------------------------------------------------------------------------
# Phases
# ---------------------------------------------------------------------------


def phase_1_db_ingest(dry_run=False):
    """Phase 1: Ingest already-scraped state, municipal, and NOM data."""
    extra = []
    if dry_run:
        extra = ["--dry-run"]

    # 1a. State laws (BC/DGO/QR from metadata)
    logger.info("[Phase 1a] Ingesting state laws...")
    try:
        call_command("ingest_state_laws", all=True, dry_run=dry_run)
    except Exception as e:
        logger.error("[Phase 1a] State law ingestion failed: %s", e)

    # 1b. Municipal laws (León/GDL/MTY/Zapopan)
    logger.info("[Phase 1b] Ingesting municipal laws...")
    try:
        call_command("ingest_municipal_laws", all=True, dry_run=dry_run)
    except Exception as e:
        logger.error("[Phase 1b] Municipal law ingestion failed: %s", e)

    # 1c. NOMs (skip download, use existing PDFs)
    logger.info("[Phase 1c] Ingesting NOMs...")
    nom_script = PROJECT_ROOT / "scripts" / "ingestion" / "ingest_noms.py"
    catalog = DATA_DIR / "federal" / "noms" / "discovered_noms.json"
    cmd = [
        sys.executable,
        str(nom_script),
        "--skip-download",
        "--catalog",
        str(catalog),
    ]
    if dry_run:
        cmd.append("--dry-run")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                logger.info("[NOM] %s", line)
        if result.returncode != 0 and result.stderr:
            logger.error("[NOM stderr] %s", result.stderr[-500:])
    except Exception as e:
        logger.error("[Phase 1c] NOM ingestion failed: %s", e)


def phase_2_treaties(dry_run=False):
    """Phase 2: Run treaty scraper then ingest."""
    # 2a. Scrape treaties
    logger.info("[Phase 2a] Running treaty scraper...")
    try:
        from apps.scraper.federal.treaty_scraper import TreatyScraper

        scraper = TreatyScraper()
        summary = scraper.run(output_dir="data/treaties")
        logger.info(
            "[Phase 2a] Scraper finished: %d treaties (%d bilateral, %d multilateral)",
            summary.get("total_treaties", 0),
            summary.get("bilateral", 0),
            summary.get("multilateral", 0),
        )
    except Exception as e:
        logger.error("[Phase 2a] Treaty scraping failed: %s", e)
        # If scraping fails, try ingesting whatever catalog exists
        catalog = DATA_DIR / "treaties" / "discovered_treaties.json"
        if not catalog.exists():
            logger.warning("[Phase 2] No treaty catalog found, skipping ingestion.")
            return

    # 2b. Ingest treaties
    logger.info("[Phase 2b] Ingesting treaties...")
    try:
        call_command("ingest_treaties", all=True, dry_run=dry_run)
    except Exception as e:
        logger.error("[Phase 2b] Treaty ingestion failed: %s", e)


def phase_3_extended_noms(dry_run=False):
    """Phase 3: Extended NOM search (optional, 2-4 hours)."""
    logger.info("[Phase 3] Running extended NOM search...")
    nom_script = PROJECT_ROOT / "scripts" / "scraping" / "run_overnight_noms.py"
    if not nom_script.exists():
        logger.warning("[Phase 3] run_overnight_noms.py not found, skipping.")
        return

    log_path = LOGS_DIR / "overnight_noms_extended.log"
    cmd = [sys.executable, str(nom_script)]
    try:
        with open(log_path, "w") as log_file:
            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                timeout=14400,  # 4 hour timeout
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
        logger.info(
            "[Phase 3] NOM search finished (exit code %d). Log: %s",
            result.returncode,
            log_path,
        )
    except subprocess.TimeoutExpired:
        logger.warning("[Phase 3] NOM search timed out after 4 hours.")
    except Exception as e:
        logger.error("[Phase 3] Extended NOM search failed: %s", e)

    # Re-run NOM ingestion for newly discovered entries
    if not dry_run:
        logger.info("[Phase 3] Re-ingesting NOMs after extended search...")
        nom_ingest = PROJECT_ROOT / "scripts" / "ingestion" / "ingest_noms.py"
        catalog = DATA_DIR / "federal" / "noms" / "discovered_noms.json"
        cmd = [
            sys.executable,
            str(nom_ingest),
            "--skip-download",
            "--catalog",
            str(catalog),
        ]
        try:
            subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=600,
            )
        except Exception as e:
            logger.error("[Phase 3] NOM re-ingestion failed: %s", e)


def phase_4_es_reindex():
    """Phase 4: Re-index all laws in Elasticsearch."""
    logger.info("[Phase 4] Re-indexing laws in Elasticsearch...")
    try:
        call_command("index_laws", all=True, create_indices=True)
        logger.info("[Phase 4] ES re-index complete.")
    except Exception as e:
        logger.error("[Phase 4] ES re-index failed: %s", e)


def phase_5_update_registry(before_counts, after_counts):
    """Phase 5: Update universe_registry.json with new counts."""
    registry_path = DATA_DIR / "universe_registry.json"
    if not registry_path.exists():
        logger.warning("[Phase 5] universe_registry.json not found, skipping.")
        return

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)

        sources = registry.get("sources", {})
        today = datetime.now().strftime("%Y-%m-%d")

        # Query actual DB counts by category
        federal_count = Law.objects.filter(tier="federal").count()
        state_leg = Law.objects.filter(tier="state", law_type="legislative").count()
        state_non_leg = Law.objects.filter(
            tier="state", law_type="non_legislative"
        ).count()
        municipal_count = Law.objects.filter(tier="municipal").count()

        # Count NOMs and treaties specifically
        nom_count = Law.objects.filter(official_id__startswith="nom_").count()
        treaty_count = Law.objects.filter(official_id__startswith="treaty_").count()

        # Update scraped_count fields
        if "international_treaties" in sources:
            sources["international_treaties"]["scraped_count"] = treaty_count
            sources["international_treaties"]["last_verified"] = today

        if "federal_noms" in sources:
            sources["federal_noms"]["scraped_count"] = nom_count
            sources["federal_noms"]["last_verified"] = today

        if "municipal" in sources:
            sources["municipal"]["scraped_count"] = municipal_count
            sources["municipal"]["last_verified"] = today

        if "state_legislativo" in sources:
            sources["state_legislativo"]["scraped_count"] = state_leg
            sources["state_legislativo"]["last_verified"] = today

        if "state_non_legislativo" in sources:
            sources["state_non_legislativo"]["scraped_count"] = state_non_leg
            sources["state_non_legislativo"]["last_verified"] = today

        registry["last_updated"] = today

        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
            f.write("\n")

        logger.info("[Phase 5] Updated universe_registry.json (date: %s)", today)
        logger.info(
            "  Treaties: %d, NOMs: %d, Municipal: %d, State leg: %d, State non-leg: %d",
            treaty_count,
            nom_count,
            municipal_count,
            state_leg,
            state_non_leg,
        )

    except Exception as e:
        logger.error("[Phase 5] Registry update failed: %s", e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Overnight data ingestion orchestrator."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pass --dry-run to all ingestion commands.",
    )
    parser.add_argument(
        "--skip-nom-search",
        action="store_true",
        help="Skip Phase 3 (extended NOM search, 2-4 hrs).",
    )
    parser.add_argument(
        "--skip-es-index",
        action="store_true",
        help="Skip Phase 4 (ES re-index).",
    )
    args = parser.parse_args()

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    logger.info("=" * 70)
    logger.info("OVERNIGHT DATA INGESTION ORCHESTRATOR")
    logger.info("Started: %s", datetime.now().isoformat())
    logger.info(
        "Flags: dry_run=%s skip_nom=%s skip_es=%s",
        args.dry_run,
        args.skip_nom_search,
        args.skip_es_index,
    )
    logger.info("=" * 70)

    # Record before counts
    before_counts = get_db_counts()
    print_counts("BEFORE", before_counts)

    # Phase 1: Quick wins — ingest already-scraped data
    with timed_phase("1 — DB ingest (state + municipal + NOMs)"):
        phase_1_db_ingest(dry_run=args.dry_run)

    # Phase 2: Treaty scraping + ingestion
    with timed_phase("2 — Treaty scraping + ingestion"):
        phase_2_treaties(dry_run=args.dry_run)

    # Phase 3: Extended NOM search (optional)
    if not args.skip_nom_search:
        with timed_phase("3 — Extended NOM search"):
            phase_3_extended_noms(dry_run=args.dry_run)
    else:
        logger.info("Skipping Phase 3 (--skip-nom-search)")

    # Phase 4: ES re-index (optional)
    if not args.skip_es_index:
        with timed_phase("4 — ES re-index"):
            phase_4_es_reindex()
    else:
        logger.info("Skipping Phase 4 (--skip-es-index)")

    # Phase 5: Update registry + summary
    after_counts = get_db_counts()
    with timed_phase("5 — Update registry + summary"):
        phase_5_update_registry(before_counts, after_counts)

    # Final summary
    elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 70)
    logger.info("OVERNIGHT INGESTION COMPLETE")
    logger.info("=" * 70)
    print_counts("BEFORE", before_counts)
    print_counts("AFTER", after_counts)
    logger.info("--- DELTA ---")
    for tier in sorted(set(list(before_counts.keys()) + list(after_counts.keys()))):
        before = before_counts.get(tier, 0)
        after = after_counts.get(tier, 0)
        delta = after - before
        if delta != 0:
            logger.info("  %-20s %+6d  (%d -> %d)", tier, delta, before, after)
    logger.info("Total elapsed: %.1f minutes (%.0f seconds)", elapsed / 60, elapsed)
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
