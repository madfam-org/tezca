from django.urls import path
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
from .analytics_views import search_analytics
from .annotation_views import annotation_detail, annotation_list
from .apikey_views import create_api_key, list_api_keys, revoke_api_key, update_api_key
from .billing_views import billing_webhook
from .bulk_views import bulk_articles
from .changelog_views import changelog
from .contribution_views import (
    list_contributions,
    submit_contribution,
    submit_expert_contact,
)
from .coverage_views import public_coverage
from .cross_reference_views import (
    article_cross_references,
    batch_article_cross_references,
    law_cross_references,
)
from .export_views import (
    export_docx,
    export_epub,
    export_json,
    export_latex,
    export_pdf,
    export_quota,
    export_txt,
)
from .graph_views import graph_overview, graph_public_showcase, law_graph
from .judicial_views import (
    judicial_detail,
    judicial_list,
    judicial_search,
    judicial_stats,
)
from .law_views import (
    LawDetailView,
    LawListView,
    RelatedLawsView,
    categories_list,
    law_articles,
    law_search,
    law_stats,
    law_structure,
    laws_exist,
    municipalities_list,
    states_list,
    suggest,
)
from .middleware.admin_permission import IsTezcaAdmin
from .middleware.janua_auth import JanuaJWTAuthentication
from .newsletter_views import newsletter_subscribe, newsletter_unsubscribe
from .notification_views import (
    alert_delete,
    alert_list,
    notification_list,
    notification_mark_read,
)
from .preference_views import user_bookmarks, user_preferences, user_recently_viewed
from .search_views import SearchView
from .views import IngestionView
from .webhook_views import create_webhook, delete_webhook, list_webhooks, test_webhook


def _protected(view_func):
    """Apply Janua JWT authentication and admin check to an admin view.

    Sets class-level attributes on the WrappedAPIView created by @api_view,
    so DRF's dispatch actually enforces them.  The rest_framework.decorators
    helpers only set func-level attrs, which DRF ignores.
    """
    view_func.cls.authentication_classes = [JanuaJWTAuthentication]
    view_func.cls.permission_classes = [IsAuthenticated, IsTezcaAdmin]
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
    path(
        "admin/analytics/search/",
        _protected(search_analytics),
        name="admin-search-analytics",
    ),
    # API Key management (Janua-protected)
    path("admin/apikeys/", _protected(create_api_key), name="admin-apikey-create"),
    path("admin/apikeys/list/", _protected(list_api_keys), name="admin-apikey-list"),
    path(
        "admin/apikeys/<str:prefix>/",
        _protected(update_api_key),
        name="admin-apikey-update",
    ),
    path(
        "admin/apikeys/<str:prefix>/revoke/",
        _protected(revoke_api_key),
        name="admin-apikey-revoke",
    ),
    path("ingest/", _protected(IngestionView.as_view()), name="ingest"),
    # ── Public endpoints (no auth) ────────────────────────────────────
    path("search/", SearchView.as_view(), name="search"),
    path("stats/", law_stats, name="law-stats"),
    path("laws/exists/", laws_exist, name="laws-exist"),
    path("laws/", LawListView.as_view(), name="law-list"),
    path("laws/<str:law_id>/", LawDetailView.as_view(), name="law-detail"),
    path("laws/<str:law_id>/search/", law_search, name="law-search"),
    path("laws/<str:law_id>/articles/", law_articles, name="law-articles"),
    path(
        "laws/<str:law_id>/articles/references/batch/",
        batch_article_cross_references,
        name="batch-article-references",
    ),
    path(
        "laws/<str:law_id>/articles/<str:article_id>/references/",
        article_cross_references,
        name="article-references",
    ),
    path("laws/<str:law_id>/structure/", law_structure, name="law-structure"),
    path("laws/<str:law_id>/references/", law_cross_references, name="law-references"),
    path("laws/<str:law_id>/graph/", law_graph, name="law-graph"),
    path("laws/<str:law_id>/related/", RelatedLawsView.as_view(), name="law-related"),
    path("laws/<str:law_id>/export/pdf/", export_pdf, name="law-export-pdf"),
    path("laws/<str:law_id>/export/txt/", export_txt, name="law-export-txt"),
    path("laws/<str:law_id>/export/latex/", export_latex, name="law-export-latex"),
    path("laws/<str:law_id>/export/docx/", export_docx, name="law-export-docx"),
    path("laws/<str:law_id>/export/epub/", export_epub, name="law-export-epub"),
    path("laws/<str:law_id>/export/json/", export_json, name="law-export-json"),
    path("laws/<str:law_id>/export/quota/", export_quota, name="law-export-quota"),
    path("categories/", categories_list, name="categories-list"),
    path("states/", states_list, name="states-list"),
    path("municipalities/", municipalities_list, name="municipalities-list"),
    path("suggest/", suggest, name="law-suggest"),
    # ── Bulk data access (API key required) ──────────────────────────────
    path("bulk/articles/", bulk_articles, name="bulk-articles"),
    path("changelog/", changelog, name="changelog"),
    path("coverage/", public_coverage, name="public-coverage"),
    path("graph/overview/", graph_overview, name="graph-overview"),
    path("graph/showcase/", graph_public_showcase, name="graph-showcase"),
    # ── Contributions (public submission) ──────────────────────────────
    path("contributions/", submit_contribution, name="contribution-submit"),
    path("contributions/expert/", submit_expert_contact, name="expert-contact"),
    path(
        "admin/contributions/",
        _protected(list_contributions),
        name="admin-contributions",
    ),
    # ── User endpoints (auth required) ─────────────────────────────────
    path("user/preferences/", user_preferences, name="user-preferences"),
    path("user/bookmarks/", user_bookmarks, name="user-bookmarks"),
    path("user/recently-viewed/", user_recently_viewed, name="user-recently-viewed"),
    path("user/annotations/", annotation_list, name="annotation-list"),
    path(
        "user/annotations/<int:annotation_id>/",
        annotation_detail,
        name="annotation-detail",
    ),
    path("user/notifications/", notification_list, name="notification-list"),
    path(
        "user/notifications/mark-read/",
        notification_mark_read,
        name="notification-mark-read",
    ),
    path("user/alerts/", alert_list, name="alert-list"),
    path("user/alerts/<int:alert_id>/", alert_delete, name="alert-delete"),
    # ── Newsletter (public) ────────────────────────────────────────────
    path("newsletter/subscribe/", newsletter_subscribe, name="newsletter-subscribe"),
    path(
        "newsletter/unsubscribe/",
        newsletter_unsubscribe,
        name="newsletter-unsubscribe",
    ),
    # ── Billing (server-to-server) ──────────────────────────────────────
    path("billing/webhook/", billing_webhook, name="billing-webhook"),
    # ── Webhooks (API key required) ──────────────────────────────────────
    path("webhooks/", create_webhook, name="webhook-create"),
    path("webhooks/list/", list_webhooks, name="webhook-list"),
    path("webhooks/<int:webhook_id>/", delete_webhook, name="webhook-delete"),
    path("webhooks/<int:webhook_id>/test/", test_webhook, name="webhook-test"),
    # ── Judicial records (public) ─────────────────────────────────────
    path("judicial/", judicial_list, name="judicial-list"),
    path("judicial/search/", judicial_search, name="judicial-search"),
    path("judicial/stats/", judicial_stats, name="judicial-stats"),
    path("judicial/<str:registro>/", judicial_detail, name="judicial-detail"),
]
