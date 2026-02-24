"""
Celery tasks for scheduled data operations.

These tasks are registered with Celery Beat via CELERY_BEAT_SCHEDULE
in settings.py.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


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


@shared_task(name="dataops.check_dof_daily")
def check_dof_daily():
    """Check today's DOF edition for law changes.

    Runs daily at 7 AM via Celery Beat. Fetches the DOF index,
    detects reforms/new laws/abrogations, and logs findings.
    """
    import datetime

    from apps.scraper.federal.dof_daily import DofScraper

    scraper = DofScraper(date=datetime.date.today())
    results = scraper.run()

    entries = results.get("entries", [])
    changes = results.get("changes", [])

    # Log to AcquisitionLog
    try:
        from apps.scraper.dataops.models import AcquisitionLog

        log_entry = AcquisitionLog.objects.create(
            operation="dof_daily_check",
            parameters={"date": str(datetime.date.today())},
            found=len(entries),
            downloaded=0,
            failed=0,
            ingested=0,
        )
        if changes:
            log_entry.error_summary = (
                f"{len(changes)} law changes detected: "
                + ", ".join(c.get("change_type", "unknown") for c in changes[:5])
            )
        log_entry.finish()
    except Exception:
        pass

    if changes:
        logger.warning(
            "DOF daily: %d entries, %d law changes detected",
            len(entries),
            len(changes),
        )
        for change in changes[:10]:
            logger.warning(
                "  [%s] %s", change.get("change_type", "?"), change.get("title", "?")
            )
    else:
        logger.info("DOF daily: %d entries, no law changes detected", len(entries))

    return {
        "date": str(datetime.date.today()),
        "total_entries": len(entries),
        "law_changes": len(changes),
        "changes": changes[:20],
    }
