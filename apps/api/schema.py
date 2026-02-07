"""
OpenAPI schema definitions for drf-spectacular.

Inline serializers used by @extend_schema decorators on API views.
"""

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes
from rest_framework import serializers

# ── Law endpoints ────────────────────────────────────────────────────────


class LawVersionSchema(serializers.Serializer):
    publication_date = serializers.DateField(allow_null=True)
    valid_from = serializers.DateField(allow_null=True)
    dof_url = serializers.URLField(allow_null=True)
    xml_file = serializers.CharField(allow_null=True)


class LawDetailSchema(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    short_name = serializers.CharField(allow_null=True)
    category = serializers.CharField()
    tier = serializers.CharField()
    law_type = serializers.CharField()
    state = serializers.CharField(allow_null=True)
    status = serializers.CharField(allow_null=True)
    last_verified = serializers.DateTimeField(allow_null=True)
    source_url = serializers.URLField(allow_null=True)
    versions = LawVersionSchema(many=True)
    articles = serializers.IntegerField()
    grade = serializers.CharField(allow_null=True)
    score = serializers.FloatField(allow_null=True)
    degraded = serializers.BooleanField(required=False)


class LawListItemSchema(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    tier = serializers.CharField(allow_null=True)
    law_type = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    status = serializers.CharField(allow_null=True)
    versions = serializers.IntegerField()


class ArticleSchema(serializers.Serializer):
    article_id = serializers.CharField()
    text = serializers.CharField()


class LawArticlesSchema(serializers.Serializer):
    law_id = serializers.CharField()
    law_name = serializers.CharField()
    total = serializers.IntegerField()
    articles = ArticleSchema(many=True)


class StructureNodeSchema(serializers.Serializer):
    label = serializers.CharField()
    children = serializers.ListField(child=serializers.DictField(), default=[])


class LawStructureSchema(serializers.Serializer):
    law_id = serializers.CharField()
    structure = StructureNodeSchema(many=True)


class StatesListSchema(serializers.Serializer):
    states = serializers.ListField(child=serializers.CharField())


class RecentLawSchema(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    date = serializers.DateField()
    tier = serializers.CharField()
    category = serializers.CharField()


class LawStatsSchema(serializers.Serializer):
    total_laws = serializers.IntegerField()
    federal_count = serializers.IntegerField()
    state_count = serializers.IntegerField()
    municipal_count = serializers.IntegerField()
    legislative_count = serializers.IntegerField()
    non_legislative_count = serializers.IntegerField()
    total_articles = serializers.IntegerField()
    federal_coverage = serializers.FloatField()
    state_coverage = serializers.FloatField()
    municipal_coverage = serializers.FloatField()
    total_coverage = serializers.FloatField()
    last_update = serializers.DateField(allow_null=True)
    recent_laws = RecentLawSchema(many=True)
    coverage = serializers.DictField(required=False, allow_null=True)
    degraded = serializers.BooleanField(required=False)


# ── Related laws ────────────────────────────────────────────────────────


class RelatedLawSchema(serializers.Serializer):
    law_id = serializers.CharField()
    name = serializers.CharField()
    tier = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    state = serializers.CharField(allow_null=True)
    score = serializers.FloatField()


class RelatedLawsResponseSchema(serializers.Serializer):
    law_id = serializers.CharField()
    related = RelatedLawSchema(many=True)


# ── Categories ──────────────────────────────────────────────────────────


class CategoryListItemSchema(serializers.Serializer):
    category = serializers.CharField()
    count = serializers.IntegerField()
    label = serializers.CharField()


# ── Search endpoint ──────────────────────────────────────────────────────


class SearchResultSchema(serializers.Serializer):
    id = serializers.CharField()
    law_id = serializers.CharField()
    law_name = serializers.CharField()
    article = serializers.CharField()
    snippet = serializers.CharField()
    date = serializers.DateField(allow_null=True)
    score = serializers.FloatField(allow_null=True)
    tier = serializers.CharField(allow_null=True)
    law_type = serializers.CharField(allow_null=True)
    state = serializers.CharField(allow_null=True)
    municipality = serializers.CharField(allow_null=True)
    hierarchy = serializers.ListField(child=serializers.CharField(), default=[])
    book = serializers.CharField(allow_null=True)
    title = serializers.CharField(allow_null=True)
    chapter = serializers.CharField(allow_null=True)


class SearchResponseSchema(serializers.Serializer):
    results = SearchResultSchema(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()


SEARCH_PARAMETERS = [
    OpenApiParameter("q", str, required=True, description="Search query text"),
    OpenApiParameter(
        "jurisdiction", str, description="Comma-separated: federal,state,municipal"
    ),
    OpenApiParameter("category", str, description="Law category filter"),
    OpenApiParameter("state", str, description="State name filter"),
    OpenApiParameter("municipality", str, description="Municipality name filter"),
    OpenApiParameter(
        "status",
        str,
        description="Law status filter",
        enum=["all", "vigente", "abrogado"],
    ),
    OpenApiParameter(
        "sort",
        str,
        description="Sort order",
        enum=["relevance", "date_desc", "date_asc", "name"],
    ),
    OpenApiParameter(
        "date_range",
        str,
        description="Date range filter",
        enum=["all", "this_year", "last_year", "last_5_years", "older"],
    ),
    OpenApiParameter("title", str, description="Filter by structural title"),
    OpenApiParameter("chapter", str, description="Filter by structural chapter"),
    OpenApiParameter(
        "law_type",
        str,
        description="Filter by law type",
        enum=["all", "legislative", "non_legislative"],
    ),
    OpenApiParameter("page", int, description="Page number (default: 1)"),
    OpenApiParameter("page_size", int, description="Results per page (default: 10)"),
]


# ── Cross-reference endpoints ────────────────────────────────────────────


class OutgoingRefSchema(serializers.Serializer):
    text = serializers.CharField()
    targetLawSlug = serializers.CharField(allow_null=True)
    targetArticle = serializers.CharField(allow_null=True)
    fraction = serializers.CharField(allow_null=True)
    confidence = serializers.FloatField()
    startPos = serializers.IntegerField()
    endPos = serializers.IntegerField()
    targetUrl = serializers.CharField(allow_null=True)


class IncomingRefSchema(serializers.Serializer):
    sourceLawSlug = serializers.CharField()
    sourceArticle = serializers.CharField()
    text = serializers.CharField()
    confidence = serializers.FloatField()
    sourceUrl = serializers.CharField()


class ArticleCrossRefsSchema(serializers.Serializer):
    outgoing = OutgoingRefSchema(many=True)
    incoming = IncomingRefSchema(many=True)
    total_outgoing = serializers.IntegerField()
    total_incoming = serializers.IntegerField()


class RefCountSchema(serializers.Serializer):
    slug = serializers.CharField()
    count = serializers.IntegerField()


class LawRefStatsSchema(serializers.Serializer):
    total_outgoing = serializers.IntegerField()
    total_incoming = serializers.IntegerField()
    most_referenced_laws = RefCountSchema(many=True)
    most_citing_laws = RefCountSchema(many=True)


class LawCrossRefsSchema(serializers.Serializer):
    statistics = LawRefStatsSchema()


# ── Admin endpoints ─────────────────────────────────────────────────────


class HealthCheckSchema(serializers.Serializer):
    status = serializers.ChoiceField(choices=["healthy", "unhealthy"])
    database = serializers.CharField()
    timestamp = serializers.DateTimeField()


class MetricsCountsSchema(serializers.Serializer):
    federal = serializers.IntegerField()
    state = serializers.IntegerField()
    municipal = serializers.IntegerField()


class CategoryCountSchema(serializers.Serializer):
    category = serializers.CharField(allow_null=True)
    count = serializers.IntegerField()


class SystemMetricsSchema(serializers.Serializer):
    total_laws = serializers.IntegerField()
    counts = MetricsCountsSchema()
    top_categories = CategoryCountSchema(many=True)
    quality_distribution = serializers.DictField(allow_null=True)
    last_updated = serializers.DateTimeField()


class JobStatusSchema(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    progress = serializers.IntegerField(required=False)
    timestamp = serializers.CharField()


class JobListSchema(serializers.Serializer):
    jobs = JobStatusSchema(many=True)


class EnvironmentConfigSchema(serializers.Serializer):
    debug = serializers.BooleanField()
    allowed_hosts = serializers.ListField(child=serializers.CharField())
    language = serializers.CharField()
    timezone = serializers.CharField()


class DatabaseConfigSchema(serializers.Serializer):
    engine = serializers.CharField()
    status = serializers.CharField()
    name = serializers.CharField()


class ElasticsearchConfigSchema(serializers.Serializer):
    host = serializers.CharField()
    status = serializers.CharField()


class DataConfigSchema(serializers.Serializer):
    total_laws = serializers.IntegerField()
    total_versions = serializers.IntegerField()
    latest_publication = serializers.CharField(allow_null=True)


class SystemConfigSchema(serializers.Serializer):
    environment = EnvironmentConfigSchema()
    database = DatabaseConfigSchema()
    elasticsearch = ElasticsearchConfigSchema()
    data = DataConfigSchema()


class IngestionRequestSchema(serializers.Serializer):
    mode = serializers.ChoiceField(
        choices=["all", "priority", "specific", "tier"],
        default="all",
        required=False,
    )
    priority_level = serializers.IntegerField(default=1, required=False)
    laws = serializers.CharField(required=False)
    tier = serializers.CharField(required=False)
    skip_download = serializers.BooleanField(default=False, required=False)
    workers = serializers.IntegerField(default=4, required=False)


class IngestionResponseSchema(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()


# ── Pipeline endpoints ─────────────────────────────────────────────────


class PhaseResultSchema(serializers.Serializer):
    phase = serializers.CharField()
    phase_number = serializers.IntegerField()
    returncode = serializers.IntegerField()
    status = serializers.CharField()
    duration = serializers.CharField()
    output_tail = serializers.ListField(
        child=serializers.CharField(), required=False, default=[]
    )
    error = serializers.CharField(required=False, allow_null=True)


class PipelineSummarySchema(serializers.Serializer):
    total_phases = serializers.IntegerField()
    succeeded = serializers.IntegerField()
    failed = serializers.IntegerField()


class PipelineStatusSchema(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["idle", "running", "completed", "completed_with_errors", "error"]
    )
    message = serializers.CharField()
    phase = serializers.CharField(required=False, allow_null=True)
    phase_number = serializers.IntegerField(required=False, allow_null=True)
    total_phases = serializers.IntegerField(required=False, allow_null=True)
    progress = serializers.IntegerField(required=False, allow_null=True)
    started_at = serializers.CharField(required=False, allow_null=True)
    completed_at = serializers.CharField(required=False, allow_null=True)
    duration_human = serializers.CharField(required=False, allow_null=True)
    timestamp = serializers.CharField()
    task_id = serializers.CharField(required=False, allow_null=True)
    phase_results = PhaseResultSchema(many=True, required=False, default=[])
    summary = PipelineSummarySchema(required=False, allow_null=True)


# ── Error schema ─────────────────────────────────────────────────────────


class ErrorSchema(serializers.Serializer):
    error = serializers.CharField()
