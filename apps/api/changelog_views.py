"""
Changelog endpoint for data consumers.

GET /api/v1/changelog/ — laws updated since a given date.
Requires API key with 'read' scope.
"""

import logging

from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .constants import DOMAIN_MAP
from .models import Law, LawVersion

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Bulk"],
    summary="Changelog feed",
    description=(
        "Returns laws updated since a given date. "
        "Requires API key with 'read' scope. "
        "Use ?since=YYYY-MM-DD (required) with optional domain/category/tier filters."
    ),
)
@api_view(["GET"])
def changelog(request):
    """Return laws updated since a given date."""
    # Auth check
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return Response(
            {"error": "Authentication required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    scopes = getattr(user, "scopes", [])
    if "read" not in scopes:
        return Response(
            {"error": "Insufficient scope. Required: 'read'"},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Parse 'since' param (required)
    since_str = request.query_params.get("since")
    if not since_str:
        return Response(
            {"error": "'since' query parameter is required (YYYY-MM-DD format)"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    since_date = parse_date(since_str)
    if not since_date:
        return Response(
            {"error": "Invalid date format. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Filter versions created since the date
    versions_qs = LawVersion.objects.filter(
        created_at__date__gte=since_date
    ).select_related("law").order_by("-created_at")

    # Optional filters
    domain = request.query_params.get("domain")
    category = request.query_params.get("category")
    tier = request.query_params.get("tier")

    categories = None
    if domain and domain in DOMAIN_MAP:
        categories = DOMAIN_MAP[domain]
    elif category:
        categories = [c.strip() for c in category.split(",") if c.strip()]

    if categories:
        versions_qs = versions_qs.filter(law__category__in=categories)
    if tier:
        versions_qs = versions_qs.filter(law__tier=tier)

    # Domain access check for API keys
    allowed = getattr(user, "allowed_domains", [])
    if allowed:
        allowed_categories = set()
        for d in allowed:
            if d in DOMAIN_MAP:
                allowed_categories.update(DOMAIN_MAP[d])
            else:
                allowed_categories.add(d)
        versions_qs = versions_qs.filter(law__category__in=list(allowed_categories))

    # Limit to 500 results
    versions = versions_qs[:500]

    # Deduplicate by law (keep latest version per law)
    seen_laws = set()
    changes = []
    for v in versions:
        if v.law.official_id in seen_laws:
            continue
        seen_laws.add(v.law.official_id)

        # Get previous version
        prev = (
            LawVersion.objects.filter(law=v.law, created_at__lt=v.created_at)
            .order_by("-created_at")
            .first()
        )

        changes.append({
            "law_id": v.law.official_id,
            "law_name": v.law.name,
            "category": v.law.category,
            "tier": v.law.tier,
            "status": v.law.status,
            "change_type": "new_version",
            "publication_date": str(v.publication_date) if v.publication_date else None,
            "change_summary": v.change_summary,
            "previous_version_date": (
                str(prev.publication_date) if prev and prev.publication_date else None
            ),
            "updated_at": v.created_at.isoformat(),
        })

    return Response({
        "since": since_str,
        "total": len(changes),
        "changes": changes,
    })
