"""
Bulk data access endpoints for API consumers.

GET /api/v1/bulk/articles/ — cursor-paginated articles with full law metadata.
Requires API key with 'bulk' scope.
"""

import base64
import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .config import INDEX_NAME, es_client
from .constants import DOMAIN_MAP

logger = logging.getLogger(__name__)


def _check_scope(request, required_scope: str):
    """Check that the authenticated user has the required scope."""
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return Response(
            {"error": "Authentication required. Provide an API key with X-API-Key header."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    scopes = getattr(user, "scopes", [])
    if required_scope not in scopes:
        return Response(
            {
                "error": f"Insufficient scope. Required: '{required_scope}'",
                "your_scopes": scopes,
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def _check_domain_access(request, categories: list[str]) -> Response | None:
    """If API key has allowed_domains, ensure requested categories are permitted."""
    user = getattr(request, "user", None)
    if not user:
        return None
    allowed = getattr(user, "allowed_domains", [])
    if not allowed:
        return None  # No restriction
    # Resolve allowed_domains to categories
    allowed_categories = set()
    for domain in allowed:
        if domain in DOMAIN_MAP:
            allowed_categories.update(DOMAIN_MAP[domain])
        else:
            allowed_categories.add(domain)
    # Check if requested categories are all within allowed
    for cat in categories:
        if cat not in allowed_categories:
            return Response(
                {
                    "error": f"Domain restriction: category '{cat}' is not in your allowed domains",
                    "allowed_domains": allowed,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
    return None


def _resolve_domain(request) -> list[str] | None:
    """Resolve ?domain= and ?category= params into a list of category slugs."""
    domain = request.query_params.get("domain")
    category = request.query_params.get("category")

    if domain and domain in DOMAIN_MAP:
        return DOMAIN_MAP[domain]
    if category:
        return [c.strip() for c in category.split(",") if c.strip()]
    return None


@extend_schema(
    tags=["Bulk"],
    summary="Bulk articles feed",
    description=(
        "Cursor-paginated bulk article feed with full law metadata. "
        "Requires API key with 'bulk' scope. "
        "Supports domain/category, tier, state, status, and updated_since filters."
    ),
)
@api_view(["GET"])
def bulk_articles(request):
    """Cursor-paginated bulk article endpoint for data consumers."""
    # Auth + scope check
    scope_error = _check_scope(request, "bulk")
    if scope_error:
        return scope_error

    # Resolve categories from domain/category param
    categories = _resolve_domain(request)

    # Domain access check
    if categories:
        domain_error = _check_domain_access(request, categories)
        if domain_error:
            return domain_error

    # Build ES query
    filter_clauses = []

    if categories:
        filter_clauses.append({"terms": {"category": categories}})

    tier = request.query_params.get("tier")
    if tier:
        filter_clauses.append({"term": {"tier": tier}})

    state = request.query_params.get("state")
    if state:
        filter_clauses.append({"prefix": {"law_id": f"{state.lower()}_"}})

    law_status = request.query_params.get("status")
    if law_status:
        filter_clauses.append({"term": {"status": law_status}})

    updated_since = request.query_params.get("updated_since")
    if updated_since:
        filter_clauses.append({"range": {"publication_date": {"gte": updated_since}}})

    es_query = {"match_all": {}}
    if filter_clauses:
        es_query = {"bool": {"filter": filter_clauses}}

    # Pagination
    page_size = min(max(1, int(request.query_params.get("page_size", 500))), 5000)
    cursor = request.query_params.get("cursor")

    # Decode cursor (base64-encoded search_after value)
    search_after = None
    if cursor:
        try:
            import json
            search_after = json.loads(base64.urlsafe_b64decode(cursor).decode())
        except Exception:
            return Response(
                {"error": "Invalid cursor"}, status=status.HTTP_400_BAD_REQUEST
            )

    try:
        es = es_client
        body = {
            "query": es_query,
            "sort": [{"law_id": "asc"}, {"article": "asc"}],
            "size": page_size,
            "_source": [
                "law_id", "law_name", "category", "tier", "status",
                "law_type", "state", "article", "text", "publication_date",
            ],
        }

        if search_after:
            body["search_after"] = search_after

        res = es.search(index=INDEX_NAME, body=body)
        hits = res["hits"]["hits"]
        total = res["hits"]["total"]["value"]

        results = []
        last_sort = None
        for hit in hits:
            src = hit["_source"]
            results.append({
                "law_id": src.get("law_id"),
                "law_name": src.get("law_name"),
                "category": src.get("category"),
                "tier": src.get("tier"),
                "status": src.get("status"),
                "law_type": src.get("law_type"),
                "state": src.get("state"),
                "article_id": src.get("article"),
                "text": src.get("text"),
                "last_updated": src.get("publication_date"),
            })
            last_sort = hit.get("sort")

        # Build next cursor
        next_cursor = None
        if last_sort and len(results) == page_size:
            import json
            next_cursor = base64.urlsafe_b64encode(
                json.dumps(last_sort).encode()
            ).decode()

        return Response({
            "count": total,
            "next_cursor": next_cursor,
            "page_size": page_size,
            "results": results,
        })

    except Exception:
        logger.exception("bulk_articles failed")
        return Response(
            {"error": "An internal error occurred."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
