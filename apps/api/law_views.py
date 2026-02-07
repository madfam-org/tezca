import json
import os
import re

from django.db.models import Count
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Law, LawVersion
from .schema import (
    ErrorSchema,
    LawArticlesSchema,
    LawDetailSchema,
    LawListItemSchema,
    LawStatsSchema,
    LawStructureSchema,
    StatesListSchema,
)


def _natural_sort_key(text: str):
    """Generate a sort key that orders numbers numerically within strings.

    'Art. 2' < 'Art. 10' (instead of alphanumeric '10' < '2')
    """
    parts = re.split(r"(\d+)", text or "")
    return [int(p) if p.isdigit() else p.lower() for p in parts]


from .config import ES_HOST, INDEX_NAME, es_client


class LawDetailView(APIView):
    @extend_schema(
        tags=["Laws"],
        summary="Get law detail",
        description="Retrieve full metadata for a single law including versions.",
        responses={200: LawDetailSchema, 404: ErrorSchema},
    )
    def get(self, request, law_id):
        # 1. Get Law
        law = get_object_or_404(Law, official_id=law_id)

        # 2. Get Versions
        versions = law.versions.all().order_by("-publication_date")

        # 3. Extract state from official_id (for state laws)
        state = None
        if law.tier == "state" and "_" in law_id:
            state = law_id.split("_")[0].replace("_", " ").title()

        # 4. Get article count from Elasticsearch
        article_count = 0
        es_degraded = False
        try:
            es = es_client
            if es.ping():
                count_res = es.count(
                    index=INDEX_NAME,
                    body={"query": {"match_phrase": {"law_id": law.official_id}}},
                )
                article_count = count_res.get("count", 0)
            else:
                es_degraded = True
        except Exception:
            import logging

            logging.getLogger(__name__).warning(
                "ES unavailable for law detail %s", law_id, exc_info=True
            )
            es_degraded = True

        # 5. Format Response
        data = {
            "id": law.official_id,
            "name": law.name,
            "short_name": law.short_name,
            "category": law.category,
            "tier": law.tier,
            "law_type": law.law_type,
            "state": state,
            "status": law.status,
            "last_verified": law.last_verified,
            "source_url": law.source_url,
            "versions": [
                {
                    "publication_date": v.publication_date,
                    "valid_from": v.valid_from,
                    "dof_url": v.dof_url,
                    "xml_file": (
                        v.xml_file_path.split("/")[-1] if v.xml_file_path else None
                    ),
                }
                for v in versions
            ],
            "articles": article_count,
            "grade": None,
            "score": None,
        }

        if es_degraded:
            data["degraded"] = True

        response = Response(data)
        response["Cache-Control"] = "public, max-age=3600"
        return response


class LawListPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class LawListView(APIView):
    pagination_class = LawListPagination

    @extend_schema(
        tags=["Laws"],
        summary="List all laws",
        description="Returns paginated list of laws with basic metadata. Supports filtering by tier, state, category, status, and name search.",
        responses={200: LawListItemSchema(many=True)},
    )
    def get(self, request):
        qs = Law.objects.annotate(version_count=Count("versions"))

        # Sort param
        sort = request.query_params.get("sort", "name_asc")
        sort_map = {
            "name_asc": "official_id",
            "name_desc": "-official_id",
            "date_desc": "-versions__publication_date",
            "date_asc": "versions__publication_date",
            "article_count": "-version_count",
        }
        ordering = sort_map.get(sort, "official_id")
        qs = qs.order_by(ordering)

        # Filtering
        tier = request.query_params.get("tier")
        if tier:
            qs = qs.filter(tier=tier)

        state = request.query_params.get("state")
        if state:
            qs = qs.filter(state__iexact=state)

        category = request.query_params.get("category")
        if category:
            qs = qs.filter(category__iexact=category)

        law_status = request.query_params.get("status")
        if law_status:
            qs = qs.filter(status=law_status)

        law_type = request.query_params.get("law_type")
        if law_type and law_type != "all":
            qs = qs.filter(law_type=law_type)

        q = request.query_params.get("q")
        if q:
            qs = qs.filter(name__icontains=q)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)

        data = [
            {
                "id": law.official_id,
                "name": law.short_name or law.name,
                "tier": law.tier,
                "law_type": law.law_type,
                "category": law.category,
                "status": law.status,
                "versions": law.version_count,
            }
            for law in page
        ]
        return paginator.get_paginated_response(data)


class RelatedLawsView(APIView):
    @extend_schema(
        tags=["Laws"],
        summary="Get related laws",
        description="Find thematically related laws using Elasticsearch more_like_this.",
        responses={200: dict, 404: ErrorSchema},
    )
    def get(self, request, law_id):
        law = get_object_or_404(Law, official_id=law_id)

        related = []
        try:
            es = es_client
            if es.ping():
                # Get first 3 article texts for similarity context
                articles_body = {
                    "query": {"match_phrase": {"law_id": law.official_id}},
                    "sort": [{"article": "asc"}],
                    "_source": ["text"],
                    "size": 3,
                }
                articles_res = es.search(index=INDEX_NAME, body=articles_body)
                article_texts = [
                    hit["_source"]["text"][:500]
                    for hit in articles_res["hits"]["hits"]
                    if hit["_source"].get("text")
                ]

                like_text = f"{law.name} {' '.join(article_texts)}"

                mlt_body = {
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "more_like_this": {
                                        "fields": ["law_name", "text"],
                                        "like": like_text,
                                        "min_term_freq": 1,
                                        "min_doc_freq": 1,
                                        "max_query_terms": 25,
                                    }
                                }
                            ],
                            "must_not": [
                                {"match_phrase": {"law_id": law.official_id}}
                            ],
                        }
                    },
                    "aggs": {
                        "by_law": {
                            "terms": {"field": "law_id", "size": 8},
                            "aggs": {
                                "top_hit": {
                                    "top_hits": {
                                        "_source": [
                                            "law_name",
                                            "tier",
                                            "category",
                                            "state",
                                        ],
                                        "size": 1,
                                    }
                                }
                            },
                        }
                    },
                    "size": 0,
                }

                mlt_res = es.search(index=INDEX_NAME, body=mlt_body)
                buckets = (
                    mlt_res.get("aggregations", {})
                    .get("by_law", {})
                    .get("buckets", [])
                )

                for bucket in buckets:
                    top = bucket["top_hit"]["hits"]["hits"]
                    if not top:
                        continue
                    src = top[0]["_source"]
                    related.append(
                        {
                            "law_id": bucket["key"],
                            "name": src.get("law_name", bucket["key"]),
                            "tier": src.get("tier", ""),
                            "category": src.get("category", ""),
                            "state": src.get("state"),
                            "score": round(bucket["doc_count"], 1),
                        }
                    )
        except Exception:
            import logging

            logging.getLogger(__name__).warning(
                "ES unavailable for related laws %s", law_id, exc_info=True
            )

        # Fallback: if ES returned nothing, use DB same-category same-tier laws
        if not related:
            fallback_qs = (
                Law.objects.filter(category=law.category, tier=law.tier)
                .exclude(official_id=law.official_id)
                .order_by("name")[:8]
            )
            related = [
                {
                    "law_id": r.official_id,
                    "name": r.short_name or r.name,
                    "tier": r.tier,
                    "category": r.category,
                    "state": None,
                    "score": 0,
                }
                for r in fallback_qs
            ]

        response = Response({"law_id": law_id, "related": related})
        response["Cache-Control"] = "public, max-age=3600"
        return response


@api_view(["GET"])
def categories_list(request):
    """Get all categories with law counts."""
    CATEGORY_LABELS = {
        "civil": "Derecho Civil",
        "penal": "Derecho Penal",
        "mercantil": "Derecho Mercantil",
        "fiscal": "Derecho Fiscal",
        "laboral": "Derecho Laboral",
        "administrativo": "Derecho Administrativo",
        "constitucional": "Derecho Constitucional",
    }

    rows = (
        Law.objects.exclude(category__isnull=True)
        .exclude(category="")
        .values("category")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    data = [
        {
            "category": row["category"],
            "count": row["count"],
            "label": CATEGORY_LABELS.get(row["category"], row["category"].title()),
        }
        for row in rows
    ]

    response = Response(data)
    response["Cache-Control"] = "public, max-age=3600"
    return response


@extend_schema(
    tags=["Laws"],
    summary="Search within a law",
    description="Full-text search within a specific law's articles, with highlighting.",
    responses={200: dict, 404: ErrorSchema, 500: ErrorSchema},
)
@api_view(["GET"])
def law_search(request, law_id):
    """Search within a specific law's articles."""
    q = request.query_params.get("q", "").strip()
    if not q:
        return Response(
            {"error": "Query parameter 'q' is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    law = get_object_or_404(Law, official_id=law_id)

    try:
        es = es_client
        body = {
            "query": {
                "bool": {
                    "must": [
                        {"match_phrase": {"law_id": law.official_id}},
                        {"match": {"text": {"query": q, "fuzziness": "AUTO"}}},
                    ]
                }
            },
            "highlight": {"fields": {"text": {"fragment_size": 200}}},
            "size": 50,
        }

        res = es.search(index=INDEX_NAME, body=body)

        results = []
        for hit in res["hits"]["hits"]:
            source = hit["_source"]
            highlights = hit.get("highlight", {}).get("text", [])
            results.append(
                {
                    "article_id": source.get("article"),
                    "snippet": (
                        highlights[0] if highlights else source.get("text", "")[:200]
                    ),
                    "score": hit["_score"],
                }
            )

        return Response(
            {
                "law_id": law_id,
                "query": q,
                "total": res["hits"]["total"]["value"],
                "results": results,
            }
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception("law_search failed for %s", law_id)
        return Response(
            {"error": "An internal error occurred while searching."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    tags=["Laws"],
    summary="Get law articles",
    description="Retrieve all articles for a law from the search index.",
    responses={200: LawArticlesSchema, 500: ErrorSchema},
)
@api_view(["GET"])
def law_articles(request, law_id):
    """Get all articles for a law from Elasticsearch."""
    try:
        # Verify law exists
        law = get_object_or_404(Law, official_id=law_id)

        # Pagination params
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(max(1, int(request.query_params.get("page_size", 500))), 1000)
        offset = (page - 1) * page_size

        # Query Elasticsearch
        es = es_client

        body = {
            "query": {"match_phrase": {"law_id": law.official_id}},
            "sort": [{"article": {"order": "asc"}}],
            "from": offset,
            "size": page_size,
        }

        res = es.search(index=INDEX_NAME, body=body)

        articles = []
        seen = set()
        for hit in res["hits"]["hits"]:
            source = hit["_source"]
            aid = source.get("article")
            if aid in seen:
                continue
            seen.add(aid)
            articles.append(
                {
                    "article_id": aid,
                    "text": source.get("text"),
                }
            )

        articles.sort(key=lambda a: _natural_sort_key(a.get("article_id", "")))

        response = Response(
            {
                "law_id": law_id,
                "law_name": law.name,
                "total": len(articles),
                "articles": articles,
            }
        )
        response["Cache-Control"] = "public, max-age=3600"
        return response

    except Exception:
        import logging

        logging.getLogger(__name__).exception("law_articles failed for %s", law_id)
        return Response(
            {"error": "An internal error occurred while retrieving articles."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    tags=["Laws"],
    summary="Get law structure",
    description="Get the hierarchical structure (Book > Title > Chapter) of a law as a tree.",
    responses={200: LawStructureSchema, 500: ErrorSchema},
)
@api_view(["GET"])
def law_structure(request, law_id):
    """
    Get the hierarchical structure (Book > Title > Chapter) of a law.
    Returns a tree: [{ "label": "Title I", "children": [...] }]
    """
    try:
        law = get_object_or_404(Law, official_id=law_id)
        es = es_client

        # Fetch all articles with hierarchy data
        # Sort by metadata order if available, otherwise we rely on ES default which is not reliable for order.
        # Ideally we re-index with an 'index_order' field.
        # For now, we fetch large size and trust the parser order if we could.
        # Actually, standard ES search might return random order if scoring is identical.
        # We will use 'article' sort as a fallback, but it is alphanumeric (1, 10, 2).
        # Fix: We will rely on simple aggregation? No, aggregation buckets keys are sorted alphanumeric.

        # Strategy: Fetch *all* hits (up to 10k), and build tree.
        body = {
            "query": {"match_phrase": {"law_id": law.official_id}},
            "sort": [{"article": "asc"}],  # Imperfect but needed for consistency
            "_source": ["hierarchy", "text", "article"],
            "size": 10000,
        }

        res = es.search(index=INDEX_NAME, body=body)

        # Build Tree
        root = []

        for hit in res["hits"]["hits"]:
            source = hit["_source"]
            breadcrumbs = source.get("hierarchy", [])

            # Navigate/Create tree nodes
            current_level = root
            for crumb in breadcrumbs:
                # Find existing node for this crumb
                found = next(
                    (node for node in current_level if node["label"] == crumb), None
                )
                if not found:
                    found = {"label": crumb, "children": []}
                    current_level.append(found)
                current_level = found["children"]

        def _sort_tree(nodes):
            nodes.sort(key=lambda n: _natural_sort_key(n["label"]))
            for node in nodes:
                _sort_tree(node["children"])

        _sort_tree(root)

        response = Response({"law_id": law_id, "structure": root})
        response["Cache-Control"] = "public, max-age=3600"
        return response

    except Exception:
        import logging

        logging.getLogger(__name__).exception("law_structure failed for %s", law_id)
        return Response(
            {"error": "An internal error occurred while retrieving structure."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    tags=["Laws"],
    summary="List states",
    description="Get sorted list of all Mexican states that have indexed laws.",
    responses={200: StatesListSchema},
)
@api_view(["GET"])
def states_list(request):
    """Get list of all states with law counts."""
    from .constants import KNOWN_STATES

    # Get all state law IDs
    state_law_ids = Law.objects.filter(tier="state").values_list(
        "official_id", flat=True
    )

    found_states = set()

    for official_id in state_law_ids:
        # Check for multi-word states first (longer matches)
        # We sort keys by length descending to match 'baja_california_sur' before 'baja_california'
        for slug in sorted(KNOWN_STATES.keys(), key=len, reverse=True):
            if official_id.startswith(f"{slug}_"):
                found_states.add(KNOWN_STATES[slug])
                break

    return Response({"states": sorted(list(found_states))})


@api_view(["GET"])
def municipalities_list(request):
    """Distinct municipalities with law counts, optionally filtered by state."""
    state = request.query_params.get("state")
    qs = Law.objects.exclude(municipality__isnull=True).exclude(municipality="")
    if state:
        qs = qs.filter(state=state)
    municipalities = (
        qs.values("municipality", "state")
        .annotate(count=Count("id"))
        .order_by("state", "municipality")
    )
    return Response(list(municipalities))


@api_view(["GET"])
def suggest(request):
    """Lightweight law-name autocomplete. Returns top 8 matches."""
    q = request.query_params.get("q", "").strip()
    if len(q) < 2:
        return Response({"suggestions": []})

    laws = (
        Law.objects.filter(name__icontains=q)
        .values("official_id", "name", "tier")
        .order_by("name")[:8]
    )
    response = Response(
        {
            "suggestions": [
                {"id": law["official_id"], "name": law["name"], "tier": law["tier"]}
                for law in laws
            ]
        }
    )
    response["Cache-Control"] = "public, max-age=300"
    return response


def _safe_pct(count, universe):
    """Calculate coverage percentage, returning None if universe is None or 0."""
    if not universe:
        return None
    return round(min(count / universe * 100, 100), 1)


# Universe registry cache (file-mtime based)
_registry_cache = {"data": None, "mtime": 0}

REGISTRY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "universe_registry.json",
)


def _load_universe_registry():
    """Load universe_registry.json with file-mtime caching."""
    try:
        mtime = os.path.getmtime(REGISTRY_PATH)
        if _registry_cache["data"] is not None and _registry_cache["mtime"] == mtime:
            return _registry_cache["data"]
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _registry_cache["data"] = data
        _registry_cache["mtime"] = mtime
        return data
    except (OSError, json.JSONDecodeError):
        return None


@extend_schema(
    tags=["Laws"],
    summary="Dashboard statistics",
    description="Get global statistics for the homepage dashboard including recent laws.",
    responses={200: LawStatsSchema},
)
@api_view(["GET"])
def law_stats(request):
    """Get global statistics for the dashboard."""
    total_laws = Law.objects.count()
    federal_count = Law.objects.filter(tier="federal").count()
    state_count = Law.objects.filter(tier="state").count()
    municipal_count = Law.objects.filter(tier="municipal").count()
    legislative_count = Law.objects.filter(law_type="legislative").count()
    non_legislative_count = Law.objects.filter(law_type="non_legislative").count()

    # Article count from Elasticsearch
    total_articles = 0
    es_degraded = False
    try:
        es = es_client
        if es.ping():
            count_res = es.count(index=INDEX_NAME)
            total_articles = count_res.get("count", 0)
        else:
            es_degraded = True
    except Exception:
        import logging

        logging.getLogger(__name__).warning(
            "ES unavailable for law_stats", exc_info=True
        )
        es_degraded = True

    # Load universe registry for honest coverage numbers
    registry = _load_universe_registry()

    if registry:
        src = registry.get("sources", {})
        fed_src = src.get("federal_leyes_vigentes", {})
        state_src = src.get("state_legislativo", {})
        state_all_src = src.get("state_non_legislativo", {})
        muni_src = src.get("municipal", {})

        fed_universe = fed_src.get("known_count")
        state_universe = state_src.get("known_count")
        state_all_universe = (state_universe or 0) + (
            state_all_src.get("known_count") or 0
        )

        leyes_vigentes_universe = (fed_universe or 0) + (state_universe or 0)
        leyes_vigentes_count = federal_count + state_count

        coverage = {
            "leyes_vigentes": {
                "label": "Leyes Legislativas Vigentes",
                "count": leyes_vigentes_count,
                "universe": leyes_vigentes_universe,
                "percentage": _safe_pct(leyes_vigentes_count, leyes_vigentes_universe),
                "description": "Leyes federales + estatales del Poder Legislativo",
            },
            "federal": {
                "count": federal_count,
                "universe": fed_universe,
                "percentage": _safe_pct(federal_count, fed_universe),
                "source": fed_src.get("source_name"),
                "last_verified": fed_src.get("last_verified"),
            },
            "state": {
                "count": state_count,
                "universe": state_universe,
                "percentage": _safe_pct(state_count, state_universe),
                "source": state_src.get("source_name"),
                "permanent_gaps": state_src.get("permanent_gaps"),
            },
            "state_all_powers": {
                "count": state_count + non_legislative_count,
                "universe": state_all_universe,
                "percentage": _safe_pct(
                    state_count + non_legislative_count, state_all_universe
                ),
                "non_legislative_count": non_legislative_count,
                "description": f"Incluye {non_legislative_count:,} leyes de otros poderes ya indexadas",
            },
            "municipal": {
                "count": municipal_count,
                "universe": muni_src.get("known_count"),
                "percentage": None,
                "cities_covered": muni_src.get("cities_covered"),
                "total_municipalities": muni_src.get("total_municipalities"),
                "description": f"{municipal_count} leyes de {muni_src.get('cities_covered', 0)} municipios",
            },
        }

        # Backward-compatible coverage fields
        federal_coverage = _safe_pct(federal_count, fed_universe) or 0
        state_coverage = _safe_pct(state_count, state_universe) or 0
        municipal_coverage = 0  # No known universe
        total_coverage = _safe_pct(leyes_vigentes_count, leyes_vigentes_universe) or 0
    else:
        # Fallback if registry is missing
        coverage = None
        federal_coverage = 0
        state_coverage = 0
        municipal_coverage = 0
        total_coverage = 0

    # Get recent laws (most recent version publication date)
    recent_versions = LawVersion.objects.select_related("law").order_by(
        "-publication_date"
    )[:5]
    recent_laws = []
    for v in recent_versions:
        recent_laws.append(
            {
                "id": v.law.official_id,
                "name": v.law.short_name or v.law.name,
                "date": v.publication_date,
                "tier": v.law.tier,
                "category": v.law.category,
            }
        )

    last_update = recent_versions[0].publication_date if recent_versions else None

    response_data = {
        "total_laws": total_laws,
        "federal_count": federal_count,
        "state_count": state_count,
        "municipal_count": municipal_count,
        "legislative_count": legislative_count,
        "non_legislative_count": non_legislative_count,
        "total_articles": total_articles,
        "federal_coverage": federal_coverage,
        "state_coverage": state_coverage,
        "municipal_coverage": municipal_coverage,
        "total_coverage": total_coverage,
        "last_update": last_update,
        "recent_laws": recent_laws,
    }

    if coverage is not None:
        response_data["coverage"] = coverage

    if es_degraded:
        response_data["degraded"] = True

    return Response(response_data)
