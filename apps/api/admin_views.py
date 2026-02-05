import os

from django.conf import settings as django_settings
from django.db import connection
from django.db.models import Count, Max
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .ingestion_manager import IngestionManager
from .models import Law, LawVersion
from .schema import (
    ErrorSchema,
    HealthCheckSchema,
    JobListSchema,
    JobStatusSchema,
    SystemConfigSchema,
    SystemMetricsSchema,
)


@extend_schema(
    tags=["Admin"],
    summary="Health check",
    description="Simple health check verifying database connectivity.",
    responses={200: HealthCheckSchema, 503: HealthCheckSchema},
)
@api_view(["GET"])
def health_check(request):
    """
    Simple health check endpoint.
    Checks database connectivity.
    """
    try:
        # Simple DB check
        Law.objects.first()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        return Response(
            {"status": "unhealthy", "database": db_status},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {
            "status": "healthy",
            "database": db_status,
            "timestamp": timezone.now().isoformat(),
        }
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
        # Total laws
        total_laws = Law.objects.count()

        # Breakdown by jurisdiction (tier)
        # Federal (tier=0/federal), State (tier=1/state), Municipal (tier=2/municipal)
        # Note: Model uses string values for 'tier' typically

        federal_count = Law.objects.filter(tier__in=["0", "federal"]).count()
        state_count = Law.objects.filter(tier__in=["1", "state"]).count()
        municipal_count = Law.objects.filter(tier__in=["2", "municipal"]).count()

        # Breakdown by category (top 5)
        categories = list(
            Law.objects.values("category")
            .annotate(count=Count("category"))
            .order_by("-count")[:5]
        )

        # Quality distribution - not yet tracked per-law in the database.
        # Returns null to signal the frontend that real data is unavailable.
        quality_distribution = None

        return Response(
            {
                "total_laws": total_laws,
                "counts": {
                    "federal": federal_count,
                    "state": state_count,
                    "municipal": municipal_count,
                },
                "top_categories": categories,
                "quality_distribution": quality_distribution,
                "last_updated": timezone.now().isoformat(),
            }
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
    except Exception as e:
        return Response(
            {
                "status": "error",
                "message": str(e),
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
    Returns a list of recent jobs.
    Currently returns a single-item list with the current status
    since we don't have a persistent job history table yet.
    """
    try:
        current = IngestionManager.get_status()
        # Mocking a 'list' format for the frontend
        jobs = [{"id": "current", **current}]
        return Response({"jobs": jobs})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
    es_host = os.getenv("ES_HOST", "http://elasticsearch:9200")
    es_status = "unknown"
    try:
        from elasticsearch import Elasticsearch

        es = Elasticsearch([es_host])
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
