"""Search analytics admin endpoints."""

from datetime import timedelta

from django.db.models import Avg, Count
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import SearchQuery


@api_view(["GET"])
def search_analytics(request):
    """
    Search analytics dashboard for admins.

    Returns top queries, zero-result queries, average response time,
    and volume by day for the last 30 days.
    """
    days = min(int(request.query_params.get("days", 30)), 90)
    since = timezone.now() - timedelta(days=days)
    qs = SearchQuery.objects.filter(created_at__gte=since)

    # Top queries
    top_queries = list(
        qs.values("query")
        .annotate(count=Count("id"), avg_results=Avg("result_count"))
        .order_by("-count")[:20]
    )

    # Zero-result queries
    zero_result = list(
        qs.filter(result_count=0)
        .values("query")
        .annotate(count=Count("id"))
        .order_by("-count")[:20]
    )

    # Average response time
    avg_response = qs.aggregate(avg_ms=Avg("response_time_ms"))

    # Volume by day
    from django.db.models.functions import TruncDate

    volume_by_day = list(
        qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"), avg_ms=Avg("response_time_ms"))
        .order_by("day")
    )

    # Serialize dates
    for entry in volume_by_day:
        entry["day"] = entry["day"].isoformat() if entry["day"] else None
        entry["avg_ms"] = round(entry["avg_ms"]) if entry["avg_ms"] else None

    for entry in top_queries:
        entry["avg_results"] = (
            round(entry["avg_results"], 1) if entry["avg_results"] else 0
        )

    return Response(
        {
            "period_days": days,
            "total_searches": qs.count(),
            "avg_response_time_ms": (
                round(avg_response["avg_ms"]) if avg_response["avg_ms"] else None
            ),
            "top_queries": top_queries,
            "zero_result_queries": zero_result,
            "volume_by_day": volume_by_day,
        }
    )
