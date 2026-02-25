# Scraper Module

This module handles fetching legal texts from official Mexican government sources.

## Architecture

```
apps/scraper/
├── federal/          # Federal-level scrapers
│   ├── catalog_spider.py      # Cámara de Diputados law catalog
│   ├── reglamentos_spider.py  # Federal reglamentos (150 scraped)
│   ├── dof_daily.py           # DOF daily edition monitor
│   ├── dof_api_client.py      # DOF API integration
│   ├── conamer_scraper.py     # CONAMER CNARTyS (113K+ regulations)
│   ├── nom_scraper.py         # NOMs from DOF archive (~4,000)
│   └── treaty_scraper.py      # SRE international treaties (~1,500)
├── state/            # State congress scrapers
│   ├── base.py                # StateCongressScraper base class
│   ├── baja_california.py     # BC ~340 laws
│   ├── durango.py             # Durango ~160 laws
│   └── quintana_roo.py        # QR ~356 laws (CSV/XLS exports)
├── judicial/         # Judicial corpus scrapers
│   └── scjn_scraper.py        # SCJN jurisprudencia + tesis (~500K)
├── municipal/        # Municipal regulation scrapers
│   ├── base.py                # MunicipalScraper base class
│   ├── config.py              # All 21 city configs (tier 0/1/2)
│   ├── generic.py             # Config-driven generic scraper
│   ├── cdmx.py                # Ciudad de México
│   ├── guadalajara.py         # Guadalajara
│   ├── monterrey.py           # Monterrey
│   ├── puebla.py              # Puebla
│   ├── tijuana.py             # Tijuana
│   └── leon.py                # León
├── dataops/          # Data operations and monitoring
│   ├── coverage_dashboard.py  # Coverage metrics and reporting
│   ├── gap_registry.py        # Gap lifecycle management
│   ├── health_monitor.py      # Source health checks
│   ├── source_discovery.py    # Alternative source discovery
│   └── models.py              # DataSource, GapRecord, AcquisitionLog
├── scheduling/       # Celery tasks
│   └── tasks.py               # All scheduled scraper tasks
├── discovery/        # Law discovery and validation
└── utils/            # Shared utilities
```

## Tools

- **Juriscraper**: Core library for scraping court and legislative data.
- **Requests + BeautifulSoup**: For HTML scraping where Juriscraper isn't suitable.
- **pdfplumber**: PDF text extraction (with OCR fallback in pipeline.py).

## Running Scrapers

### Federal

```bash
# DOF daily check (also runs via Celery Beat at 7 AM)
poetry run python apps/scraper/federal/dof_daily.py --date=2026-02-24

# CONAMER CNARTyS
poetry run python apps/scraper/federal/conamer_scraper.py --max-pages 10

# NOMs (priority health NOMs)
poetry run python apps/scraper/federal/nom_scraper.py --priority-only

# International treaties
poetry run python apps/scraper/federal/treaty_scraper.py
```

### State

```bash
# Baja California
poetry run python -c "from apps.scraper.state.baja_california import BajaCaliforniaScraper; s=BajaCaliforniaScraper(); print(len(s.scrape_catalog()))"

# Durango
poetry run python -c "from apps.scraper.state.durango import DurangoScraper; s=DurangoScraper(); print(len(s.scrape_catalog()))"

# Quintana Roo (with structured data export)
poetry run python -c "from apps.scraper.state.quintana_roo import QuintanaRooScraper; s=QuintanaRooScraper(); print(len(s.scrape_catalog()))"
```

### Municipal

```bash
# Any configured city (21 total)
poetry run python -m apps.scraper.municipal.generic --city merida

# List all configured cities
poetry run python -c "from apps.scraper.municipal.config import list_municipalities; print(list_municipalities())"
```

### Judicial (SCJN)

```bash
# Probe for open data first
poetry run python apps/scraper/judicial/scjn_scraper.py --check-only

# Scrape jurisprudencia (limited)
poetry run python apps/scraper/judicial/scjn_scraper.py --tipo jurisprudencia --max-items 100

# Import partnership bulk data
poetry run python apps/scraper/judicial/scjn_scraper.py --import-dump /path/to/dump.json
```

## Celery Tasks

All scrapers have corresponding Celery tasks in `scheduling/tasks.py`:

| Task | Schedule | Description |
|------|----------|-------------|
| `dataops.check_dof_daily` | Daily 7 AM | DOF edition monitor |
| `dataops.run_health_checks` | Daily | Source health verification |
| `dataops.detect_staleness` | Weekly | Find stale law records |
| `dataops.retry_transient_failures` | Weekly | Retry dead link tier 0 gaps |
| `dataops.generate_coverage_report` | Monthly | Coverage metrics |
| `dataops.run_state_scraper` | On-demand | State congress scraper |
| `dataops.run_conamer_scraper` | On-demand | CONAMER CNARTyS |
| `dataops.run_nom_scraper` | On-demand | Federal NOMs |
| `dataops.run_treaty_scraper` | On-demand | International treaties |
| `dataops.replicate_batch` | On-demand | R2 sync + prod ingestion |

## Replication Protocol

After each scraping batch:

```bash
# 1. Sync to R2
python scripts/migrate_to_r2.py --prefix state_laws/baja_california/

# 2. Ingest to prod DB (idempotent)
python manage.py ingest_laws --source state --state "Baja California"

# 3. Reindex Elasticsearch
python manage.py index_laws --all
```

Or use the Celery task:

```python
from apps.scraper.scheduling.tasks import replicate_batch
replicate_batch.delay("state_laws/baja_california/", "ingest_laws --source state")
```

## Optional Dependencies

```bash
# OCR pipeline (for scanned PDFs)
poetry install -E ocr
# Also requires system: apt-get install tesseract-ocr tesseract-ocr-spa

# Excel parsing (for QR state scraper)
poetry install -E scraping

# All production deps
poetry install -E production
```
