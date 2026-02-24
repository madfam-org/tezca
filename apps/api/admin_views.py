import json
import os

from django.conf import settings as django_settings
from django.db import connection
from django.db.models import Count, Max
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .config import ES_HOST, es_client
from .ingestion_manager import IngestionManager
from .models import Law, LawVersion
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
    except Exception:
        services["database"] = "error"

    # Elasticsearch check
    try:
        es = es_client
        if es.ping():
            services["elasticsearch"] = "connected"
        else:
            services["elasticsearch"] = "unreachable"
    except Exception:
        services["elasticsearch"] = "error"

    # Redis check (via Django cache or Celery broker)
    try:
        from django.core.cache import cache

        cache.set("_health", "ok", 5)
        if cache.get("_health") == "ok":
            services["redis"] = "connected"
        else:
            services["redis"] = "error"
    except Exception:
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
    except Exception:
        import logging

        logging.getLogger(__name__).exception("system_metrics failed")
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
    except Exception:
        import logging

        logging.getLogger(__name__).exception("job_status failed")
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
                        "processed": log.processed,
                        "errors": log.errors,
                    }
                )
        except Exception:
            # AcquisitionLog not available — fall back to current status
            pass

        # Always include current ingestion status as first entry if no logs
        if not jobs:
            current = IngestionManager.get_status()
            jobs = [{"id": "current", **current}]

        return Response({"jobs": jobs})
    except Exception:
        import logging

        logging.getLogger(__name__).exception("list_jobs failed")
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
    except Exception:
        es_status = "unavailable"

    # Database status
    db_status = "unknown"
    try:
        connection.ensure_connection()
        db_status = "connected"
    except Exception:
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
    except Exception:
        import logging

        logging.getLogger(__name__).exception("pipeline_status failed")
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
