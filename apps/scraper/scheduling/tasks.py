"""
Celery tasks for scheduled data operations.

These tasks are registered with Celery Beat via CELERY_BEAT_SCHEDULE
in settings.py.
"""

import logging
import shlex

from celery import shared_task
from django.utils import timezone

from apps.scraper.scheduling.dof_ingest import check_dof_daily

logger = logging.getLogger(__name__)

# Cap for AcquisitionLog.error_summary persisted in DB
MAX_ERROR_LENGTH = 2000


def _start_log(operation, parameters=None):
    """Create AcquisitionLog entry at task start.

    Returns None on any DB failure so callers can no-op cleanly. The
    operational pipeline must not be blocked by AcquisitionLog plumbing
    failures, but we still log them so they're visible in the worker output.
    """
    try:
        from apps.scraper.dataops.models import AcquisitionLog

        return AcquisitionLog.objects.create(
            operation=operation,
            parameters=parameters or {},
            started_at=timezone.now(),
        )
    except Exception:
        logger.exception("Failed to create AcquisitionLog for %s", operation)
        return None


def _finish_log(log_entry, found=0, downloaded=0, failed=0, ingested=0, error=""):
    """Update AcquisitionLog on task completion."""
    if log_entry is None:
        return
    try:
        log_entry.finished_at = timezone.now()
        log_entry.found = found
        log_entry.downloaded = downloaded
        log_entry.failed = failed
        log_entry.ingested = ingested
        if error:
            log_entry.error_summary = error[:MAX_ERROR_LENGTH]
        log_entry.save()
    except Exception:
        # Never raise from log finalization — the work is already done.
        logger.exception("Failed to finalize AcquisitionLog %s", log_entry.pk)


@shared_task(name="dataops.run_health_checks")
def run_health_checks(sources="critical"):
    """Run health checks on data sources.

    Args:
        sources: "critical" for daily checks, "all" for full audit
    """
    from apps.scraper.dataops.health_monitor import HealthMonitor

    monitor = HealthMonitor()
    critical_only = sources == "critical"
    results = monitor.check_all(critical_only=critical_only)

    summary = monitor.get_summary()
    down_sources = [r.source_name for r in results if r.status == "down"]

    if down_sources:
        logger.warning("Sources DOWN: %s", ", ".join(down_sources))

    logger.info(
        "Health check complete (%s): %d healthy, %d degraded, %d down",
        sources,
        summary["healthy"],
        summary["degraded"],
        summary["down"],
    )
    return summary


@shared_task(name="dataops.detect_staleness")
def detect_staleness(max_age_days=90):
    """Find laws with stale source verification."""
    from apps.scraper.dataops.health_monitor import HealthMonitor

    monitor = HealthMonitor()
    stale = monitor.detect_staleness(max_age_days=max_age_days)
    count = stale.count()

    logger.info("Staleness check: %d laws older than %d days", count, max_age_days)
    return {"stale_count": count, "max_age_days": max_age_days}


@shared_task(
    name="dataops.retry_transient_failures",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def retry_transient_failures(self):
    """Retry gaps that are still at Tier 0 (transient failures).

    Attempts to re-verify source URLs. If the URL responds, marks the gap
    as resolved. If it fails again, escalates the tier.

    Uses Celery's built-in retry on infrastructure-level errors (DB down,
    Redis lost). Per-gap errors are handled inline without task-level retry.
    """
    import requests
    from django.utils import timezone as tz

    from apps.scraper.dataops.models import GapRecord

    try:
        transient_gaps = list(
            GapRecord.objects.filter(
                status="open",
                current_tier=0,
                gap_type="dead_link",
            )
        )
    except Exception as exc:
        raise self.retry(exc=exc)

    count = len(transient_gaps)
    logger.info("Found %d transient failures to retry", count)

    resolved = 0
    escalated = 0
    errors = 0

    for gap in transient_gaps:
        now_iso = tz.now().isoformat()
        try:
            if gap.source_url:
                resp = requests.head(gap.source_url, timeout=15, allow_redirects=True)
                if resp.status_code < 400:
                    gap.status = "resolved"
                    gap.attempts.append(
                        {
                            "tier": 0,
                            "action": "URL verified accessible",
                            "date": now_iso,
                            "result": "resolved",
                        }
                    )
                    gap.save(update_fields=["status", "attempts", "updated_at"])
                    resolved += 1
                    continue

            # URL still dead — escalate to tier 1
            gap.current_tier = 1
            gap.attempts.append(
                {
                    "tier": 1,
                    "action": "Escalated after retry failure",
                    "date": now_iso,
                    "result": "escalated",
                }
            )
            gap.save(update_fields=["current_tier", "attempts", "updated_at"])
            escalated += 1

        except Exception as exc:
            errors += 1
            gap.attempts.append(
                {
                    "tier": 0,
                    "action": f"Retry error: {str(exc)[:200]}",
                    "date": now_iso,
                    "result": "error",
                }
            )
            gap.save(update_fields=["attempts", "updated_at"])

    logger.info(
        "Retry complete: %d resolved, %d escalated, %d errors (of %d)",
        resolved,
        escalated,
        errors,
        count,
    )
    return {
        "total": count,
        "resolved": resolved,
        "escalated": escalated,
        "errors": errors,
    }


@shared_task(name="dataops.generate_coverage_report")
def generate_coverage_report():
    """Generate and log monthly coverage metrics."""
    from apps.scraper.dataops.coverage_dashboard import CoverageDashboard

    dashboard = CoverageDashboard()
    report = dashboard.full_report()

    summary = report["summary"]
    logger.info(
        "Monthly coverage: %d in DB, %d scraped, %d gaps (%d actionable)",
        summary["total_in_db"],
        summary["total_scraped"],
        summary["total_gaps"],
        summary["actionable_gaps"],
    )
    return summary


@shared_task(name="dataops.run_state_scraper")
def run_state_scraper(state_key):
    """Run a state congress scraper by key.

    Args:
        state_key: State scraper key (e.g. 'baja_california', 'guerrero')
    """
    from pathlib import Path

    scrapers = {
        "baja_california": "apps.scraper.state.baja_california.BajaCaliforniaScraper",
        "durango": "apps.scraper.state.durango.DurangoScraper",
        "quintana_roo": "apps.scraper.state.quintana_roo.QuintanaRooScraper",
        "guerrero": "apps.scraper.state.guerrero.GuerreroScraper",
        "nuevo_leon": "apps.scraper.state.nuevo_leon.NuevoLeonScraper",
        # Backfill: existing modules that weren't registered in the dispatch
        # table. Adding here makes them invokable via `enclii jobs run
        # state-<key>` without implying a Beat schedule (those land per-state
        # after the first manual run validates the URL guesses).
        "cdmx": "apps.scraper.state.cdmx.CDMXScraper",
        "estado_de_mexico": "apps.scraper.state.estado_de_mexico.EstadoDeMexicoScraper",
        "michoacan": "apps.scraper.state.michoacan.MichoacanScraper",
        "san_luis_potosi": "apps.scraper.state.san_luis_potosi.SanLuisPotosiScraper",
        "zacatecas": "apps.scraper.state.zacatecas.ZacatecasScraper",
        # Wave 1A — new scrapers from FEATURE_PARITY_PLAN_2026-04-27 §3.5
        "aguascalientes": "apps.scraper.state.aguascalientes.AguascalientesScraper",
        "hidalgo": "apps.scraper.state.hidalgo.HidalgoScraper",
        "morelos": "apps.scraper.state.morelos.MorelosScraper",
        "yucatan": "apps.scraper.state.yucatan.YucatanScraper",
    }

    if state_key not in scrapers:
        logger.error("Unknown state scraper: %s", state_key)
        return {"error": f"Unknown state: {state_key}"}

    module_path, class_name = scrapers[state_key].rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    scraper_cls = getattr(module, class_name)
    scraper = scraper_cls()

    catalog = scraper.scrape_catalog()
    logger.info("State scraper %s: found %d laws", state_key, len(catalog))

    # Save catalog
    import json

    output_dir = Path("data") / "state_laws" / state_key
    output_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = output_dir / "catalog.json"
    catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    # Log to AcquisitionLog
    try:
        from apps.scraper.dataops.models import AcquisitionLog

        AcquisitionLog.objects.create(
            operation=f"state_scraper_{state_key}",
            parameters={"state": state_key},
            found=len(catalog),
            downloaded=0,
            failed=0,
            ingested=0,
        )
    except Exception:
        logger.exception(
            "Failed to persist AcquisitionLog for state_scraper_%s", state_key
        )

    return {"state": state_key, "laws_found": len(catalog)}


@shared_task(name="dataops.run_conamer_scraper")
def run_conamer_scraper(max_pages=None, resume_from_page=0):
    """Run CONAMER CNARTyS scraper in batch mode.

    Args:
        max_pages: Max pages to scrape (None for all)
        resume_from_page: Page to resume from
    """
    from apps.scraper.federal.conamer_scraper import ConamerScraper

    scraper = ConamerScraper()
    result = scraper.run(
        output_dir="data/conamer",
        max_pages=max_pages,
        resume_from_page=resume_from_page,
    )

    logger.info(
        "CONAMER scraper: %d total, %d unique",
        result.get("total_scraped", 0),
        result.get("unique_after_dedup", result.get("total_scraped", 0)),
    )

    try:
        from apps.scraper.dataops.models import AcquisitionLog

        AcquisitionLog.objects.create(
            operation="conamer_cnartys_scrape",
            parameters={"max_pages": max_pages, "resume_from": resume_from_page},
            found=result.get("total_scraped", 0),
            downloaded=result.get("total_scraped", 0),
            failed=0,
            ingested=0,
        )
    except Exception:
        logger.exception("Failed to persist AcquisitionLog for conamer_cnartys_scrape")

    return result


@shared_task(name="dataops.run_nom_scraper")
def run_nom_scraper(priority_only=True, max_results=500):
    """Run NOM scraper.

    Args:
        priority_only: Only scrape priority health/safety NOMs
        max_results: Max results per search query
    """
    from apps.scraper.federal.nom_scraper import NomScraper

    scraper = NomScraper()
    result = scraper.run(
        output_dir="data/noms",
        priority_only=priority_only,
        max_results=max_results,
    )

    logger.info("NOM scraper: %d NOMs found", result.get("total", 0))
    return result


@shared_task(name="dataops.run_treaty_scraper")
def run_treaty_scraper(fetch_details=False, max_details=50):
    """Run international treaties scraper.

    Args:
        fetch_details: Whether to fetch individual treaty pages
        max_details: Max treaty details to fetch
    """
    from apps.scraper.federal.treaty_scraper import TreatyScraper

    scraper = TreatyScraper()
    result = scraper.run(
        output_dir="data/treaties",
        fetch_details=fetch_details,
        max_details=max_details,
    )

    logger.info("Treaty scraper: %d treaties found", result.get("total", 0))
    return result


@shared_task(name="dataops.run_rmf_scraper")
def run_rmf_scraper(year=None, include_annexes=True, download_documents=True):
    """Run SAT Resolución Miscelánea Fiscal scraper.

    Karafiel's compliance use case (per FEATURE_PARITY_PLAN_2026-04-27 §3.6)
    depends on this feed being fresh — RMF + quarterly modifications +
    annexes carry the SAT-administrative rules that implement CFF.

    Args:
        year: Fiscal year (default: current year).
        include_annexes: Walk the annexes index too.
        download_documents: When True, fetch each document's bytes. The
            quarterly Beat schedule sets this to True so we have the
            source files on disk; manual reruns can pass False to do a
            fast catalog-only sweep.
    """
    import datetime

    from apps.scraper.federal.rmf_scraper import RmfScraper

    target_year = year if year is not None else datetime.date.today().year

    log_entry = _start_log(
        "rmf_scrape",
        {
            "year": target_year,
            "include_annexes": include_annexes,
            "download_documents": download_documents,
        },
    )
    try:
        scraper = RmfScraper()
        result = scraper.run(
            year=target_year,
            include_annexes=include_annexes,
            download_documents=download_documents,
        )

        logger.info(
            "RMF scraper (year=%d): %d documents (%s)",
            target_year,
            result.get("total", 0),
            result.get("by_type", {}),
        )

        _finish_log(
            log_entry,
            found=result.get("total", 0),
            downloaded=result.get("downloaded", 0),
            failed=result.get("errors", 0),
        )
        return result

    except Exception as exc:
        logger.exception("RMF scraper failed for year=%s", target_year)
        _finish_log(log_entry, error=str(exc))
        return {"error": str(exc), "year": target_year}


@shared_task(name="dataops.replicate_batch")
def replicate_batch(prefix, ingest_command=None):
    """Replicate a scraped batch to R2 and trigger prod ingestion.

    Wraps the replication protocol:
    1. migrate_to_r2.py --prefix <batch>
    2. Optionally trigger ingest command

    Args:
        prefix: R2 prefix path (e.g. 'state_laws/baja_california/')
        ingest_command: Optional management command to run after R2 sync
    """
    import subprocess

    # Step 1: Sync to R2
    r2_result = subprocess.run(
        ["python", "scripts/migrate_to_r2.py", "--prefix", prefix],
        capture_output=True,
        text=True,
        timeout=600,
    )

    if r2_result.returncode != 0:
        logger.error("R2 sync failed for %s: %s", prefix, r2_result.stderr[:500])
        return {"success": False, "stage": "r2_sync", "error": r2_result.stderr[:500]}

    logger.info("R2 sync complete for %s", prefix)

    # Step 2: Trigger ingestion if specified
    if ingest_command:
        # Use shlex.split() to safely tokenize the command — handles quoted
        # arguments and prevents naive .split() from breaking on paths with
        # spaces or shell-significant characters that an operator might pass.
        try:
            ingest_argv = shlex.split(ingest_command)
        except ValueError as exc:
            logger.error("Invalid ingest_command for %s: %s", prefix, exc)
            return {
                "success": False,
                "stage": "ingestion",
                "error": f"Invalid ingest_command: {exc}",
            }
        ingest_result = subprocess.run(
            ["python", "manage.py", *ingest_argv],
            capture_output=True,
            text=True,
            timeout=1800,
        )
        if ingest_result.returncode != 0:
            logger.error(
                "Ingestion failed for %s: %s", prefix, ingest_result.stderr[:500]
            )
            return {
                "success": False,
                "stage": "ingestion",
                "error": ingest_result.stderr[:500],
            }

    return {"success": True, "prefix": prefix, "ingest_command": ingest_command}


@shared_task(name="dataops.run_parser_pipeline")
def run_parser_pipeline(new_only=True):
    """Run the parser V2 pipeline for text extraction and cross-reference detection.

    Args:
        new_only: If True, only process laws not yet parsed (default).
    """
    import subprocess

    cmd = ["python", "manage.py", "run_pipeline", "--skip-scrape", "--workers", "4"]
    if new_only:
        cmd.append("--new-only")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=28800,  # 8 hour max for full corpus
    )

    if result.returncode != 0:
        logger.error("Parser pipeline failed: %s", result.stderr[:500])
        return {"success": False, "error": result.stderr[:500]}

    logger.info("Parser pipeline complete: %s", result.stdout[-200:])
    return {"success": True, "output": result.stdout[-500:]}


@shared_task(name="dataops.run_conamer_playwright")
def run_conamer_playwright(max_pages=None, resume_from_page=0):
    """Run CONAMER Playwright scraper for WAF-protected catalog.

    Args:
        max_pages: Max pages to scrape (None for all)
        resume_from_page: Page to resume from
    """
    log_entry = _start_log(
        "conamer_playwright_scrape",
        {"max_pages": max_pages, "resume_from": resume_from_page},
    )
    try:
        from apps.scraper.federal.conamer_playwright import ConamerPlaywrightScraper

        scraper = ConamerPlaywrightScraper(headless=True)
        result = scraper.run(
            max_pages=max_pages,
            resume_from_page=resume_from_page,
        )

        logger.info(
            "CONAMER Playwright: %d total, %d after dedup",
            result.get("total_items", 0),
            result.get("total_after_dedup", 0),
        )

        _finish_log(
            log_entry,
            found=result.get("total_items", 0),
            downloaded=result.get("total_after_dedup", 0),
        )
        return result

    except Exception as e:
        logger.error("CONAMER Playwright scraper failed: %s", e)
        _finish_log(log_entry, error=str(e))
        return {"error": str(e)}


@shared_task(name="dataops.scrape_scjn_playwright")
def scrape_scjn_playwright(max_items=5000, epoca=11, tipo="jurisprudencia"):
    """Run SCJN Playwright scraper for JS-rendered SJF portal.

    Args:
        max_items: Max items to scrape
        epoca: Judicial epoch (default: 11)
        tipo: "jurisprudencia" or "tesis_aislada"
    """
    log_entry = _start_log(
        f"scjn_playwright_{tipo}",
        {"max_items": max_items, "epoca": epoca, "tipo": tipo},
    )
    try:
        from apps.scraper.judicial.scjn_playwright import ScjnPlaywrightScraper

        scraper = ScjnPlaywrightScraper(headless=True)
        result = scraper.run(
            epoca=epoca,
            tipo=tipo,
            max_items=max_items,
        )

        logger.info(
            "SCJN Playwright (%s, epoca=%d): %d items",
            tipo,
            epoca,
            result.get("total_items", 0),
        )

        _finish_log(
            log_entry,
            found=result.get("total_items", 0),
            downloaded=result.get("total_items", 0),
        )
        return result

    except Exception as e:
        logger.error("SCJN Playwright scraper failed: %s", e)
        _finish_log(log_entry, error=str(e))
        return {"error": str(e)}


@shared_task(name="dataops.run_ojn_recovery")
def run_ojn_recovery(paths="ab", scope="all", limit=500):
    """Run OJN multi-path recovery for failed downloads.

    Args:
        paths: Recovery paths to run ("a", "ab", "abc")
        scope: "non_leg", "leg", or "all"
        limit: Max items per path
    """
    import subprocess

    cmd = [
        "python",
        "scripts/scraping/ojn_multipath_recovery.py",
        "--path",
        paths,
        "--scope",
        scope,
        "--limit",
        str(limit),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=14400,  # 4 hours
    )

    if result.returncode != 0:
        logger.error("OJN recovery failed: %s", result.stderr[:500])
        return {"success": False, "error": result.stderr[:500]}

    logger.info("OJN recovery complete: %s", result.stdout[-300:])
    return {"success": True, "output": result.stdout[-500:]}


@shared_task(name="dataops.run_wayback_recovery")
def run_wayback_recovery(domains=None, limit=200):
    """Run Wayback Machine bulk recovery for dead domains.

    Args:
        domains: List of domains (None = all configured)
        limit: Max records per domain
    """
    import subprocess

    cmd = [
        "python",
        "scripts/scraping/wayback_bulk_recovery.py",
        "--all",
        "--limit",
        str(limit),
    ]
    if domains:
        cmd = (
            [
                "python",
                "scripts/scraping/wayback_bulk_recovery.py",
                "--domain",
            ]
            + domains
            + ["--limit", str(limit)]
        )

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=7200,  # 2 hours
    )

    if result.returncode != 0:
        logger.error("Wayback recovery failed: %s", result.stderr[:500])
        return {"success": False, "error": result.stderr[:500]}

    logger.info("Wayback recovery complete: %s", result.stdout[-300:])
    return {"success": True, "output": result.stdout[-500:]}


@shared_task(name="dataops.run_dof_historical")
def run_dof_historical(mode="noms", year=None, date_range=None):
    """Run DOF historical scan for gap-filling.

    Args:
        mode: "all", "noms", "new_laws", "gazette"
        year: Single year to scan
        date_range: "YYYY-YYYY" range
    """
    import subprocess

    cmd = ["python", "scripts/scraping/dof_historical_scan.py", "--mode", mode]
    if year:
        cmd.extend(["--year", str(year)])
    elif date_range:
        cmd.extend(["--range", date_range])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=28800,  # 8 hours
    )

    if result.returncode != 0:
        logger.error("DOF historical scan failed: %s", result.stderr[:500])
        return {"success": False, "error": result.stderr[:500]}

    logger.info("DOF historical scan complete: %s", result.stdout[-300:])
    return {"success": True, "output": result.stdout[-500:]}


@shared_task(name="dataops.scrape_scjn")
def scrape_scjn(max_items=5000, epoca=10, mode="jurisprudencia"):
    """Run SCJN judicial scraper for jurisprudencia and tesis.

    Args:
        max_items: Maximum items to scrape per run (default: 5000)
        epoca: Epoca filter (default: 10 for Décima Época)
        mode: "jurisprudencia" or "tesis"
    """
    log_entry = _start_log(
        f"scjn_{mode}_scrape",
        {"max_items": max_items, "epoca": epoca, "mode": mode},
    )
    try:
        from apps.scraper.judicial.scjn_scraper import ScjnScraper

        scraper = ScjnScraper()
        result = scraper.run(
            output_dir="data/judicial/batches",
            max_items=max_items,
            epoca=epoca,
            mode=mode,
        )

        logger.info(
            "SCJN scraper (%s): %d items scraped",
            mode,
            result.get("total_scraped", 0),
        )

        _finish_log(
            log_entry,
            found=result.get("total_scraped", 0),
            downloaded=result.get("total_scraped", 0),
            failed=result.get("failed", 0),
        )
        return result

    except Exception as e:
        logger.error("SCJN scraper failed: %s", e)
        _finish_log(log_entry, error=str(e))
        return {"error": str(e)}


@shared_task(name="dataops.ingest_judicial_batches")
def ingest_judicial_batches():
    """Auto-ingest SCJN judicial records from the judicial data directory.

    The Playwright scraper writes batches under per-type subdirectories
    (``data/judicial/jurisprudencia/``, ``data/judicial/tesis_aisladas/``),
    but this task previously read a flat ``data/judicial/batches/`` that no
    scraper writes to — so it always short-circuited on ``no_files`` and the
    JudicialRecord table stayed empty. Read the judicial root and let the
    ingest command recurse into the subdirectories.
    """
    from pathlib import Path

    from django.core.management import call_command

    batch_dir = Path("data/judicial")
    if not batch_dir.exists() or not list(batch_dir.rglob("*.json")):
        logger.info("No judicial batch files to ingest")
        return {"status": "no_files"}

    log_entry = _start_log("judicial_batch_ingest")
    try:
        call_command("ingest_judicial", dir=str(batch_dir), batch_size=500)
        _finish_log(log_entry, ingested=1)
        return {"status": "completed"}
    except Exception as e:
        logger.error("Judicial batch ingest failed: %s", e)
        _finish_log(log_entry, error=str(e))
        return {"status": "error", "error": str(e)}


@shared_task(name="dataops.ingest_conamer_catalog")
def ingest_conamer_catalog():
    """Auto-ingest scraped CONAMER regulations into the database.

    The CONAMER scrapers (``run_conamer_scraper`` / ``run_conamer_playwright``)
    only write JSON to ``data/conamer/`` — nothing was wired to the
    ``ingest_conamer`` management command, so even a successful scrape left the
    DB at 0 CONAMER rows. This closes the gap, mirroring
    ``ingest_judicial_batches``. Scheduled to run after both weekly scrapes.
    """
    from pathlib import Path

    from django.core.management import call_command

    catalog = Path("data/conamer/discovered_conamer.json")
    batch_dir = Path("data/conamer")
    has_batches = batch_dir.exists() and bool(list(batch_dir.glob("batch_*.json")))
    if not catalog.exists() and not has_batches:
        logger.info("No CONAMER catalog to ingest")
        return {"status": "no_files"}

    log_entry = _start_log("conamer_catalog_ingest")
    try:
        call_command("ingest_conamer", all=True)
        _finish_log(log_entry, ingested=1)
        return {"status": "completed"}
    except Exception as e:
        logger.error("CONAMER catalog ingest failed: %s", e)
        _finish_log(log_entry, error=str(e))
        return {"status": "error", "error": str(e)}


@shared_task(name="dataops.ingest_rmf_catalog")
def ingest_rmf_catalog():
    """Auto-ingest the scraped RMF catalog into the database.

    ``run_rmf_scraper`` (quarterly, day 8) only writes
    ``data/rmf/catalog.json`` — nothing scheduled ``ingest_rmf``, so SAT
    resolutions never reached the Law table (and Karafiel's fiscal
    webhook feed never fired) despite green scrapes. Same wiring-gap
    class as the CONAMER/judicial/DOF fixes; mirrors
    ``ingest_conamer_catalog``. Scheduled day 9, the day after the
    quarterly scrape.
    """
    from pathlib import Path

    from django.core.management import call_command

    catalog = Path("data/rmf/catalog.json")
    if not catalog.exists():
        logger.info("No RMF catalog to ingest")
        return {"status": "no_files"}

    log_entry = _start_log("rmf_catalog_ingest")
    try:
        call_command("ingest_rmf", catalog=str(catalog))
        _finish_log(log_entry, ingested=1)
        return {"status": "completed"}
    except Exception as e:
        logger.error("RMF catalog ingest failed: %s", e)
        _finish_log(log_entry, error=str(e))
        return {"status": "error", "error": str(e)}


@shared_task(name="dataops.ingest_treaty_catalog")
def ingest_treaty_catalog():
    """Auto-ingest discovered treaties into the database.

    ``run_treaty_scraper`` (weekly, Wednesday 02:00) only writes
    ``data/treaties/discovered_treaties.json`` — the ``ingest_treaties``
    command reads exactly that file but was only invoked manually (or by
    the unscheduled overnight script), so treaties never landed
    automatically. Mirrors ``ingest_conamer_catalog``; scheduled
    Wednesday 05:00, after the weekly scrape.
    """
    from pathlib import Path

    from django.core.management import call_command

    catalog = Path("data/treaties/discovered_treaties.json")
    if not catalog.exists():
        logger.info("No treaty catalog to ingest")
        return {"status": "no_files"}

    log_entry = _start_log("treaty_catalog_ingest")
    try:
        call_command("ingest_treaties", all=True)
        _finish_log(log_entry, ingested=1)
        return {"status": "completed"}
    except Exception as e:
        logger.error("Treaty catalog ingest failed: %s", e)
        _finish_log(log_entry, error=str(e))
        return {"status": "error", "error": str(e)}


@shared_task(name="dataops.classify_law_domains")
def classify_law_domains_task():
    """Weekly domain classification for newly added laws."""
    from django.core.management import call_command

    call_command("classify_law_domains", all=True, batch_size=500)
    return {"status": "completed"}


# Expected run intervals (hours) for staleness detection
_EXPECTED_INTERVALS = {
    "dof_daily_check": 24,
    "conamer_cnartys_scrape": 7 * 24,
    "conamer_playwright_scrape": 7 * 24,
    "scjn_jurisprudencia_scrape": 7 * 24,
    "scjn_playwright_jurisprudencia": 7 * 24,
}


@shared_task(name="dataops.check_scraper_health")
def check_scraper_health():
    """Check scraper health: flag stale and failing scrapers.

    Logs WARNING for scrapers with no run in 2x expected interval
    or 3+ failures in the last 7 days.
    """
    from datetime import timedelta

    from django.db.models import Count, Q
    from django.utils import timezone

    try:
        from apps.scraper.dataops.models import AcquisitionLog
    except ImportError:
        logger.warning("AcquisitionLog not available — skipping scraper health check")
        return {"error": "AcquisitionLog not available"}

    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    results = {}

    # Check all known operations
    operations = (
        AcquisitionLog.objects.values_list("operation", flat=True)
        .distinct()
        .order_by("operation")
    )

    for op in operations:
        last_run = (
            AcquisitionLog.objects.filter(operation=op).order_by("-started_at").first()
        )
        recent_failures = (
            AcquisitionLog.objects.filter(
                operation=op,
                started_at__gte=seven_days_ago,
            )
            .filter(Q(error_summary__isnull=False) & ~Q(error_summary=""))
            .count()
        )

        is_stale = False
        expected_hours = _EXPECTED_INTERVALS.get(op)
        if expected_hours and last_run and last_run.started_at:
            staleness_threshold = now - timedelta(hours=expected_hours * 2)
            is_stale = last_run.started_at < staleness_threshold

        if is_stale:
            logger.warning(
                "Scraper STALE: %s — last run %s (expected every %dh)",
                op,
                last_run.started_at.isoformat() if last_run else "never",
                expected_hours or 0,
            )

        if recent_failures >= 3:
            logger.warning(
                "Scraper FAILING: %s — %d failures in last 7 days",
                op,
                recent_failures,
            )

        results[op] = {
            "last_run": last_run.started_at.isoformat() if last_run else None,
            "is_stale": is_stale,
            "recent_failures": recent_failures,
        }

    logger.info("Scraper health check complete: %d operations checked", len(results))
    return results
