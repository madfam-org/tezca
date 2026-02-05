from django.urls import path

from .admin_views import (
    health_check,
    job_status,
    list_jobs,
    system_config,
    system_metrics,
)
from .cross_reference_views import article_cross_references, law_cross_references
from .law_views import (
    LawDetailView,
    LawListView,
    law_articles,
    law_stats,
    law_structure,
    states_list,
)
from .search_views import SearchView
from .views import CalculationView, IngestionView

urlpatterns = [
    path("admin/health/", health_check, name="admin-health"),
    path("admin/metrics/", system_metrics, name="admin-metrics"),
    path("admin/jobs/", list_jobs, name="admin-jobs-list"),
    path("admin/jobs/status/", job_status, name="admin-job-status"),
    path("admin/config/", system_config, name="admin-config"),
    path("calculate/", CalculationView.as_view(), name="calculate"),
    path("search/", SearchView.as_view(), name="search"),
    path("ingest/", IngestionView.as_view(), name="ingest"),
    path("stats/", law_stats, name="law-stats"),
    path("laws/", LawListView.as_view(), name="law-list"),
    path("laws/<str:law_id>/", LawDetailView.as_view(), name="law-detail"),
    path("laws/<str:law_id>/articles/", law_articles, name="law-articles"),
    path(
        "laws/<str:law_id>/articles/<str:article_id>/references/",
        article_cross_references,
        name="article-references",
    ),
    path("laws/<str:law_id>/structure/", law_structure, name="law-structure"),
    path("laws/<str:law_id>/references/", law_cross_references, name="law-references"),
    path("states/", states_list, name="states-list"),
]
