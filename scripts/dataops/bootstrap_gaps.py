#!/usr/bin/env python
"""
Bootstrap script: Seeds the DataSource and GapRecord tables with all known
sources and gaps from existing metadata files.

Usage:
    python scripts/dataops/bootstrap_gaps.py
"""

import os
import sys
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.indigo.settings")

import django  # noqa: E402

django.setup()

from apps.scraper.dataops.gap_registry import GapRegistry  # noqa: E402
from apps.scraper.dataops.models import DataSource  # noqa: E402

DATA_DIR = BASE_DIR / "data"

# ── Known data sources ──────────────────────────────────────────────────

KNOWN_SOURCES = [
    # Federal
    {
        "name": "Diputados Catalog",
        "source_type": "scraper",
        "level": "federal",
        "base_url": "https://www.diputados.gob.mx/LeyesBiblio/index.htm",
        "scraper_class": "apps.scraper.federal.diputados.DiputadosScraper",
        "notes": "336 laws, 338 XML files. Primary federal source.",
    },
    {
        "name": "DOF Daily",
        "source_type": "scraper",
        "level": "federal",
        "base_url": "https://www.diariooficial.gob.mx/",
        "notes": "Daily official gazette. dof_daily.py is a TODO stub.",
    },
    # State - OJN
    {
        "name": "OJN Compilacion (State Laws)",
        "source_type": "scraper",
        "level": "state",
        "base_url": "https://compilacion.ordenjuridico.gob.mx/",
        "scraper_class": "apps.scraper.discovery.ojn_state_scraper.OJNStateScraper",
        "notes": "11,337 state laws scraped from power=2. 782 permanent dead links.",
    },
    {
        "name": "OJN Powers 1/3/4 (Undiscovered)",
        "source_type": "scraper",
        "level": "state",
        "base_url": "https://compilacion.ordenjuridico.gob.mx/",
        "notes": "23,660 laws in Ejecutivo/Judicial/Autónomos powers. Not yet downloaded.",
    },
    # State - CDMX
    {
        "name": "CDMX Portal",
        "source_type": "scraper",
        "level": "state",
        "base_url": "https://data.consejeria.cdmx.gob.mx/index.php/leyes/leyes",
        "state": "Ciudad de México",
        "scraper_class": "apps.scraper.municipal.cdmx_scraper.CDMXScraper",
        "notes": "26 laws scraped. Separate from OJN.",
    },
    # Municipal
    {
        "name": "Guadalajara Transparencia",
        "source_type": "scraper",
        "level": "municipal",
        "base_url": "https://transparencia.guadalajara.gob.mx/",
        "state": "Jalisco",
        "municipality": "Guadalajara",
        "notes": "104 laws scraped.",
    },
    {
        "name": "Monterrey Transparencia",
        "source_type": "scraper",
        "level": "municipal",
        "base_url": "https://portal.monterrey.gob.mx/",
        "state": "Nuevo León",
        "municipality": "Monterrey",
        "notes": "78 laws scraped. Stub scraper.",
    },
    {
        "name": "Puebla Municipal",
        "source_type": "scraper",
        "level": "municipal",
        "base_url": "",
        "state": "Puebla",
        "municipality": "Puebla",
        "notes": "5 laws scraped. Planned scraper.",
    },
    {
        "name": "Tijuana Municipal",
        "source_type": "scraper",
        "level": "municipal",
        "base_url": "",
        "state": "Baja California",
        "municipality": "Tijuana",
        "notes": "4 laws scraped. Planned scraper.",
    },
    {
        "name": "Leon Municipal",
        "source_type": "scraper",
        "level": "municipal",
        "base_url": "",
        "state": "Guanajuato",
        "municipality": "León",
        "notes": "1 law found, 0 downloaded. Broken scraper.",
    },
]


def seed_data_sources():
    """Create DataSource entries for all known sources."""
    created = 0
    for src in KNOWN_SOURCES:
        _, was_created = DataSource.objects.get_or_create(
            name=src["name"],
            defaults={k: v for k, v in src.items() if k != "name"},
        )
        if was_created:
            created += 1
    return created


def main():
    print("=" * 60)
    print("DataOps Bootstrap: Seeding sources and gaps")
    print("=" * 60)

    # 1. Seed DataSources
    sources_created = seed_data_sources()
    print(
        f"\n[DataSources] Created {sources_created} new sources "
        f"({DataSource.objects.count()} total)"
    )

    # 2. Import gaps
    registry = GapRegistry()

    gap_report_path = DATA_DIR / "state_laws" / "gap_report.json"
    ojn_probe_path = DATA_DIR / "ojn_municipal_probe.json"

    from_gaps = registry.import_from_gap_report(gap_report_path)
    print(f"[Gap Report] Created {from_gaps} gap records (782 dead links)")

    from_probe = registry.import_from_ojn_probe(ojn_probe_path)
    print(f"[OJN Probe] Created {from_probe} gap records (23,660 undiscovered)")

    from_low = registry.import_low_count_states()
    print(f"[Low Count] Flagged {from_low} states with suspiciously low counts")

    from_missing = registry.import_missing_sources()
    print(
        f"[Missing Sources] Created {from_missing} gap records for missing categories"
    )

    # 3. Summary
    stats = registry.get_dashboard_stats()
    print(f"\n{'=' * 60}")
    print(f"TOTAL GAP RECORDS: {stats['total']}")
    print(f"  By status: {stats['by_status']}")
    print(f"  By level:  {stats['by_level']}")
    print(f"  By type:   {stats['by_type']}")
    print(f"  Actionable: {stats['actionable']}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
