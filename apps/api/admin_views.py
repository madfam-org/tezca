import json
import logging
import os

from django.conf import settings as django_settings
from django.db import connection
from django.db.models import Count, Max
from django.db.utils import OperationalError
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from elasticsearch.exceptions import ConnectionError as ESConnectionError
from elasticsearch.exceptions import ConnectionTimeout
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .config import ES_HOST, es_client
from .ingestion_manager import IngestionManager
from .models import FeatureInterest, Law, LawVersion
from .schema import (
    ErrorSchema,
    HealthCheckSchema,
    JobListSchema,
    JobStatusSchema,
    PipelineStatusSchema,
    SystemConfigSchema,
    SystemMetricsSchema,
)
from .tasks import PIPELINE_STATUS_FILE

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Admin"],
    summary="Health check",
    description="Simple health check verifying database connectivity.",
    responses={200: HealthCheckSchema, 503: HealthCheckSchema},
)
@api_view(["GET"])
def health_check(request):
    """
    Health check endpoint.
    Checks database, Elasticsearch, and Redis connectivity.
    """
    services = {}

    # Database check
    try:
        Law.objects.first()
        services["database"] = "connected"
    except (OperationalError, ConnectionError):
        services["database"] = "error"

    # Elasticsearch check
    try:
        es = es_client
        if es.ping():
            services["elasticsearch"] = "connected"
        else:
            services["elasticsearch"] = "unreachable"
    except (ESConnectionError, ConnectionTimeout, ConnectionError):
        services["elasticsearch"] = "error"

    # Redis check (via Django cache or Celery broker)
    try:
        from django.core.cache import cache

        cache.set("_health", "ok", 5)
        if cache.get("_health") == "ok":
            services["redis"] = "connected"
        else:
            services["redis"] = "error"
    except (ConnectionError, OSError):
        services["redis"] = "error"

    is_healthy = services["database"] == "connected"
    http_status = (
        status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return Response(
        {
            "status": "healthy" if is_healthy else "unhealthy",
            "services": services,
            "timestamp": timezone.now().isoformat(),
        },
        status=http_status,
    )


@extend_schema(
    tags=["Admin"],
    summary="System metrics",
    description="Aggregated system metrics including law counts by jurisdiction and category.",
    responses={200: SystemMetricsSchema, 500: ErrorSchema},
)
@api_view(["GET"])
def system_metrics(request):
    """
    Returns aggregated system metrics for the dashboard.
    """
    try:
        # Aggregate counts in a single query
        tier_counts = dict(
            Law.objects.values_list("tier")
            .annotate(count=Count("id"))
            .values_list("tier", "count")
        )
        federal_count = tier_counts.get("federal", 0)
        state_count = tier_counts.get("state", 0)
        municipal_count = tier_counts.get("municipal", 0)
        total_laws = sum(tier_counts.values())

        # Law type breakdown
        type_counts = dict(
            Law.objects.values_list("law_type")
            .annotate(count=Count("id"))
            .values_list("law_type", "count")
        )
        legislative_count = type_counts.get("legislative", 0)
        non_legislative_count = type_counts.get("non_legislative", 0)

        # Breakdown by category (top 5)
        categories = list(
            Law.objects.values("category")
            .annotate(count=Count("category"))
            .order_by("-count")[:5]
        )

        # Quality distribution — law_type breakdown serves as a quality proxy
        quality_distribution = {
            "legislative": legislative_count,
            "non_legislative": non_legislative_count,
        }

        return Response(
            {
                "total_laws": total_laws,
                "counts": {
                    "federal": federal_count,
                    "state": state_count,
                    "municipal": municipal_count,
                },
                "law_type_counts": {
                    "legislative": legislative_count,
                    "non_legislative": non_legislative_count,
                },
                "top_categories": categories,
                "quality_distribution": quality_distribution,
                "last_updated": timezone.now().isoformat(),
            }
        )
    except (OperationalError, ConnectionError):
        logger.exception("system_metrics failed")
        return Response(
            {"error": "An internal error occurred while fetching metrics."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    tags=["Admin"],
    summary="Job status",
    description="Current status of the ingestion job.",
    responses={200: JobStatusSchema, 500: ErrorSchema},
)
@api_view(["GET"])
def job_status(request):
    """
    Returns the current status of the ingestion job.
    Uses IngestionManager to read the status file.
    """
    try:
        status_data = IngestionManager.get_status()
        return Response(status_data)
    except (json.JSONDecodeError, FileNotFoundError, OSError) as exc:
        logger.warning("job_status failed: %s", exc)
        return Response(
            {
                "status": "error",
                "message": "An internal error occurred while fetching job status.",
                "timestamp": timezone.now().isoformat(),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    tags=["Admin"],
    summary="List jobs",
    description="List of recent ingestion jobs.",
    responses={200: JobListSchema, 500: ErrorSchema},
)
@api_view(["GET"])
def list_jobs(request):
    """
    Returns a list of recent pipeline runs.
    Reads from AcquisitionLog (if available) and falls back to current status.
    """
    try:
        jobs = []

        # Try to read real job history from AcquisitionLog
        try:
            from apps.scraper.dataops.models import AcquisitionLog

            logs = AcquisitionLog.objects.order_by("-started_at")[:20]
            for log in logs:
                duration = None
                if log.started_at and log.finished_at:
                    delta = log.finished_at - log.started_at
                    duration = f"{delta.total_seconds():.0f}s"

                jobs.append(
                    {
                        "id": str(log.id),
                        "operation": log.operation,
                        "status": "completed" if log.finished_at else "running",
                        "message": log.error_summary or log.operation,
                        "timestamp": (
                            log.started_at.isoformat() if log.started_at else ""
                        ),
                        "finished_at": (
                            log.finished_at.isoformat() if log.finished_at else None
                        ),
                        "duration": duration,
                        "found": log.found,
                        "downloaded": log.downloaded,
                        "failed": log.failed,
                    }
                )
        except (
            Exception
        ):  # noqa: broad-except — import may fail if dataops app is not installed
            pass

        # Always include current ingestion status as first entry if no logs
        if not jobs:
            current = IngestionManager.get_status()
            jobs = [{"id": "current", **current}]

        return Response({"jobs": jobs})
    except (OperationalError, json.JSONDecodeError, FileNotFoundError, OSError):
        logger.exception("list_jobs failed")
        return Response(
            {"error": "An internal error occurred while listing jobs."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    tags=["Admin"],
    summary="System configuration",
    description="Read-only system configuration and service status.",
    responses={200: SystemConfigSchema},
)
@api_view(["GET"])
def system_config(request):
    """
    Returns read-only system configuration and service status.
    """
    db_engine = django_settings.DATABASES["default"]["ENGINE"]

    # Elasticsearch status
    es_host = ES_HOST
    es_status = "unknown"
    try:
        es = es_client
        if es.ping():
            es_status = "connected"
        else:
            es_status = "unreachable"
    except (ESConnectionError, ConnectionTimeout, ConnectionError):
        es_status = "unavailable"

    # Database status
    db_status = "unknown"
    try:
        connection.ensure_connection()
        db_status = "connected"
    except (OperationalError, ConnectionError):
        db_status = "error"

    # Latest version date
    latest_version = LawVersion.objects.aggregate(latest=Max("publication_date"))
    latest_date = latest_version["latest"]

    return Response(
        {
            "environment": {
                "debug": django_settings.DEBUG,
                "allowed_hosts": django_settings.ALLOWED_HOSTS,
                "language": django_settings.LANGUAGE_CODE,
                "timezone": django_settings.TIME_ZONE,
            },
            "database": {
                "engine": db_engine.rsplit(".", 1)[-1],
                "status": db_status,
                "name": django_settings.DATABASES["default"].get("NAME", ""),
            },
            "elasticsearch": {
                "host": es_host,
                "status": es_status,
            },
            "data": {
                "total_laws": Law.objects.count(),
                "total_versions": LawVersion.objects.count(),
                "latest_publication": str(latest_date) if latest_date else None,
            },
        }
    )


@extend_schema(
    tags=["Admin"],
    summary="Pipeline status",
    description="Current status of the data collection pipeline.",
    responses={200: PipelineStatusSchema, 500: ErrorSchema},
)
@api_view(["GET"])
def pipeline_status(request):
    """
    Returns the current status of the data collection pipeline.
    Reads from the pipeline_status.json file written by the Celery task.
    """
    try:
        if not PIPELINE_STATUS_FILE.exists():
            return Response(
                {
                    "status": "idle",
                    "message": "No pipeline has been run yet.",
                    "timestamp": timezone.now().isoformat(),
                }
            )

        with open(PIPELINE_STATUS_FILE, "r") as f:
            data = json.load(f)

        return Response(data)
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        logger.exception("pipeline_status failed")
        return Response(
            {"error": "An internal error occurred while fetching pipeline status."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def coverage_summary(request):
    """DataOps coverage report across federal, state, and municipal tiers."""
    from apps.scraper.dataops.coverage_dashboard import CoverageDashboard

    dashboard = CoverageDashboard()
    return Response(dashboard.full_report())


@api_view(["GET"])
def health_sources(request):
    """DataOps source health summary."""
    from apps.scraper.dataops.health_monitor import HealthMonitor

    monitor = HealthMonitor()
    return Response(monitor.get_summary())


@api_view(["GET"])
def gap_records(request):
    """DataOps gap registry dashboard stats."""
    from apps.scraper.dataops.gap_registry import GapRegistry

    registry = GapRegistry()
    return Response(registry.get_dashboard_stats())


@api_view(["GET"])
def coverage_dashboard(request):
    """Consolidated coverage dashboard with tier progress, state coverage, gaps, and health."""
    from apps.scraper.dataops.coverage_dashboard import CoverageDashboard

    dashboard = CoverageDashboard()
    return Response(dashboard.dashboard_report())


@api_view(["GET"])
def dof_summary(request):
    """DOF daily summary: latest entries and detected law changes."""
    from apps.scraper.dataops.models import AcquisitionLog

    latest_dof = (
        AcquisitionLog.objects.filter(operation="dof_daily_check")
        .order_by("-started_at")
        .first()
    )

    if not latest_dof:
        return Response(
            {
                "status": "no_data",
                "message": "No DOF checks have been run yet.",
                "timestamp": timezone.now().isoformat(),
            }
        )

    return Response(
        {
            "status": "ok",
            "date": (
                latest_dof.parameters.get("date") if latest_dof.parameters else None
            ),
            "total_entries": latest_dof.found,
            "law_changes_summary": latest_dof.error_summary or "No changes detected",
            "checked_at": (
                latest_dof.started_at.isoformat() if latest_dof.started_at else None
            ),
            "finished_at": (
                latest_dof.finished_at.isoformat() if latest_dof.finished_at else None
            ),
        }
    )


@extend_schema(
    tags=["Admin"],
    summary="Quarantined laws",
    description="List laws with D/F quality grades (quarantined from indexing).",
    responses={200: None},
)
@api_view(["GET"])
def quarantined_laws(request):
    """List laws whose latest version has a quarantined quality grade."""
    quarantine_grades = getattr(
        django_settings, "QUALITY_QUARANTINE_GRADES", ["D", "F"]
    )
    quarantined = (
        LawVersion.objects.filter(quality_grade__in=quarantine_grades)
        .select_related("law")
        .order_by("-created_at")[:100]
    )
    results = [
        {
            "law_id": v.law.official_id,
            "name": v.law.name,
            "grade": v.quality_grade,
            "score": v.quality_score,
            "publication_date": str(v.publication_date),
            "created_at": v.created_at.isoformat(),
        }
        for v in quarantined
    ]
    return Response({"count": len(results), "quarantined": results})


@api_view(["GET", "PATCH"])
def roadmap(request):
    """Expansion roadmap: GET returns all phases/items, PATCH updates a single item."""
    from django.utils import timezone

    from apps.scraper.dataops.models import RoadmapItem

    if request.method == "PATCH":
        item_id = request.data.get("id")
        if not item_id:
            return Response(
                {"error": "Missing 'id' field"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            item = RoadmapItem.objects.get(id=item_id)
        except RoadmapItem.DoesNotExist:
            return Response(
                {"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND
            )

        update_fields = ["updated_at"]
        if "status" in request.data:
            new_status = request.data["status"]
            if new_status not in dict(RoadmapItem.STATUS_CHOICES):
                return Response(
                    {"error": f"Invalid status: {new_status}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            item.status = new_status
            update_fields.append("status")
            if new_status == "in_progress" and not item.started_at:
                item.started_at = timezone.now()
                update_fields.append("started_at")
            elif new_status == "completed":
                item.completed_at = timezone.now()
                item.progress_pct = 100
                update_fields.extend(["completed_at", "progress_pct"])

        if "progress_pct" in request.data:
            item.progress_pct = max(0, min(100, int(request.data["progress_pct"])))
            if "progress_pct" not in update_fields:
                update_fields.append("progress_pct")

        if "notes" in request.data:
            item.notes = request.data["notes"]
            update_fields.append("notes")

        item.save(update_fields=update_fields)
        return Response(
            {
                "ok": True,
                "id": item.id,
                "status": item.status,
                "progress_pct": item.progress_pct,
            }
        )

    # GET — return all phases
    items = RoadmapItem.objects.all()
    phase_labels = dict(RoadmapItem.PHASE_CHOICES)
    phases = {}
    for item in items:
        p = item.phase
        if p not in phases:
            phases[p] = {
                "phase": p,
                "label": phase_labels.get(p, f"Phase {p}"),
                "items": [],
                "total": 0,
                "completed": 0,
                "in_progress": 0,
                "estimated_laws": 0,
            }
        phases[p]["items"].append(
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "category": item.category,
                "status": item.status,
                "estimated_laws": item.estimated_laws,
                "estimated_effort": item.estimated_effort,
                "priority": item.priority,
                "progress_pct": item.progress_pct,
                "notes": item.notes,
                "started_at": item.started_at.isoformat() if item.started_at else None,
                "completed_at": (
                    item.completed_at.isoformat() if item.completed_at else None
                ),
            }
        )
        phases[p]["total"] += 1
        phases[p]["estimated_laws"] += item.estimated_laws
        if item.status == "completed":
            phases[p]["completed"] += 1
        elif item.status == "in_progress":
            phases[p]["in_progress"] += 1

    phase_list = sorted(phases.values(), key=lambda x: x["phase"])

    summary = {
        "total_items": items.count(),
        "completed": items.filter(status="completed").count(),
        "in_progress": items.filter(status="in_progress").count(),
        "total_estimated_laws": sum(i.estimated_laws for i in items),
    }

    return Response({"summary": summary, "phases": phase_list})


# Expected run intervals (hours) — mirrors tasks.py for staleness detection
_TASK_EXPECTED_INTERVALS = {
    "dof_daily_check": 24,
    "conamer_cnartys_scrape": 7 * 24,
    "conamer_playwright_scrape": 7 * 24,
    "scjn_jurisprudencia_scrape": 7 * 24,
    "scjn_playwright_jurisprudencia": 7 * 24,
    "state_scraper_guerrero": 30 * 24,
    "state_scraper_nuevo_leon": 30 * 24,
}


@api_view(["GET"])
def task_health(request):
    """Per-operation scraper health: last_run, run_count, success_rate, staleness."""
    from datetime import timedelta

    from django.db.models import Avg, Count, Q

    try:
        from apps.scraper.dataops.models import AcquisitionLog
    except ImportError:
        return Response(
            {"error": "AcquisitionLog not available"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)

    operations = (
        AcquisitionLog.objects.values("operation")
        .annotate(
            run_count=Count("id"),
            avg_found=Avg("found"),
            last_run=Max("started_at"),
        )
        .order_by("operation")
    )

    tasks = []
    for op in operations:
        op_name = op["operation"]
        last_run = op["last_run"]

        recent_failures = (
            AcquisitionLog.objects.filter(
                operation=op_name,
                started_at__gte=seven_days_ago,
            )
            .filter(Q(error_summary__isnull=False) & ~Q(error_summary=""))
            .count()
        )

        expected_hours = _TASK_EXPECTED_INTERVALS.get(op_name)
        is_stale = False
        if expected_hours and last_run:
            staleness_threshold = now - timedelta(hours=expected_hours * 2)
            is_stale = last_run < staleness_threshold

        # Success rate: runs with finished_at and no error_summary
        total_runs = op["run_count"]
        successful_runs = (
            AcquisitionLog.objects.filter(
                operation=op_name,
                finished_at__isnull=False,
            )
            .filter(Q(error_summary__isnull=True) | Q(error_summary=""))
            .count()
        )
        success_rate = (
            round(successful_runs / total_runs * 100, 1) if total_runs > 0 else 0
        )

        tasks.append(
            {
                "operation": op_name,
                "run_count": total_runs,
                "last_run": last_run.isoformat() if last_run else None,
                "avg_items_found": round(op["avg_found"] or 0, 1),
                "success_rate": success_rate,
                "recent_failures": recent_failures,
                "is_stale": is_stale,
                "expected_interval_hours": expected_hours,
            }
        )

    # Report known Beat tasks that have never run (0 AcquisitionLog entries)
    known_ops = set(_TASK_EXPECTED_INTERVALS.keys())
    logged_ops = {t["operation"] for t in tasks}
    never_run = sorted(known_ops - logged_ops)

    return Response(
        {
            "tasks": tasks,
            "never_run": [
                {
                    "operation": op,
                    "run_count": 0,
                    "expected_interval_hours": _TASK_EXPECTED_INTERVALS.get(op),
                    "is_stale": True,
                }
                for op in never_run
            ],
            "checked_at": now.isoformat(),
        }
    )


@api_view(["GET"])
def interest_stats(request):
    """Feature interest counts by feature_key."""
    stats = list(
        FeatureInterest.objects.values("feature_key")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    total = sum(s["count"] for s in stats)
    wishlist_count = FeatureInterest.objects.exclude(wishlist="").count()
    return Response(
        {"total": total, "by_feature": stats, "wishlist_count": wishlist_count}
    )
