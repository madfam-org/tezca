from django.urls import path
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated

from .admin_views import (
    coverage_dashboard,
    coverage_summary,
    dof_summary,
    gap_records,
    health_check,
    health_sources,
    job_status,
    list_jobs,
    pipeline_status,
    roadmap,
    system_config,
    system_metrics,
)
from .cross_reference_views import article_cross_references, law_cross_references
from .law_views import (
    LawDetailView,
    LawListView,
    RelatedLawsView,
    categories_list,
    law_articles,
    law_search,
    law_stats,
    law_structure,
    municipalities_list,
    states_list,
    suggest,
)
from .middleware.janua_auth import JanuaJWTAuthentication
from .search_views import SearchView
from .views import IngestionView


def _protected(view_func):
    """Apply Janua JWT authentication to an admin view."""
    view_func = authentication_classes([JanuaJWTAuthentication])(view_func)
    view_func = permission_classes([IsAuthenticated])(view_func)
    return view_func


urlpatterns = [
    # ── Admin endpoints (Janua-protected) ─────────────────────────────
    # Health check stays open for K8s liveness probes
    path("admin/health/", health_check, name="admin-health"),
    # Protected admin endpoints
    path("admin/metrics/", _protected(system_metrics), name="admin-metrics"),
    path("admin/jobs/", _protected(list_jobs), name="admin-jobs-list"),
    path("admin/jobs/status/", _protected(job_status), name="admin-job-status"),
    path("admin/config/", _protected(system_config), name="admin-config"),
    path(
        "admin/pipeline/status/",
        _protected(pipeline_status),
        name="admin-pipeline-status",
    ),
    path("admin/coverage/", _protected(coverage_summary), name="admin-coverage"),
    path(
        "admin/health-sources/", _protected(health_sources), name="admin-health-sources"
    ),
    path("admin/gaps/", _protected(gap_records), name="admin-gaps"),
    path(
        "admin/coverage/dashboard/",
        _protected(coverage_dashboard),
        name="admin-coverage-dashboard",
    ),
    path("admin/dof/", _protected(dof_summary), name="admin-dof-summary"),
    path("admin/roadmap/", _protected(roadmap), name="admin-roadmap"),
    path("ingest/", _protected(IngestionView.as_view()), name="ingest"),
    # ── Public endpoints (no auth) ────────────────────────────────────
    path("search/", SearchView.as_view(), name="search"),
    path("stats/", law_stats, name="law-stats"),
    path("laws/", LawListView.as_view(), name="law-list"),
    path("laws/<str:law_id>/", LawDetailView.as_view(), name="law-detail"),
    path("laws/<str:law_id>/search/", law_search, name="law-search"),
    path("laws/<str:law_id>/articles/", law_articles, name="law-articles"),
    path(
        "laws/<str:law_id>/articles/<str:article_id>/references/",
        article_cross_references,
        name="article-references",
    ),
    path("laws/<str:law_id>/structure/", law_structure, name="law-structure"),
    path("laws/<str:law_id>/references/", law_cross_references, name="law-references"),
    path("laws/<str:law_id>/related/", RelatedLawsView.as_view(), name="law-related"),
    path("categories/", categories_list, name="categories-list"),
    path("states/", states_list, name="states-list"),
    path("municipalities/", municipalities_list, name="municipalities-list"),
    path("suggest/", suggest, name="law-suggest"),
]
