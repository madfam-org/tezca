import json
import os
import re

from django.db.models import Count
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from elasticsearch import Elasticsearch
from rest_framework import status
from rest_framework.decorators import api_view
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


# Elasticsearch config
ES_HOST = os.getenv("ES_HOST", "http://elasticsearch:9200")
INDEX_NAME = "articles"


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

        # 4. Format Response
        data = {
            "id": law.official_id,
            "name": law.name,
            "short_name": law.short_name,
            "category": law.category,
            "tier": law.tier,
            "state": state,
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
            # Fallback stats for UI compatibility
            "articles": 0,
            "grade": None,
            "score": None,
        }

        return Response(data)


class LawListView(APIView):
    @extend_schema(
        tags=["Laws"],
        summary="List all laws",
        description="Returns all laws with basic metadata.",
        responses={200: LawListItemSchema(many=True)},
    )
    def get(self, request):
        laws = Law.objects.all().order_by("official_id")
        data = [
            {
                "id": law.official_id,
                "name": law.short_name or law.name,
                "versions": law.versions.count(),
            }
            for law in laws
        ]
        return Response(data)


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

        # Query Elasticsearch
        es = Elasticsearch([ES_HOST])

        # Query all articles for this law using canonical ID
        # Use match_phrase on text field to handle unicode normalization differences
        body = {
            "query": {"match_phrase": {"law_id": law.official_id}},
            "sort": [{"article": {"order": "asc"}}],
            "size": 10000,  # Max articles per law
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

        return Response(
            {
                "law_id": law_id,
                "law_name": law.name,
                "total": len(articles),
                "articles": articles,
            }
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        es = Elasticsearch([ES_HOST])

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

        return Response({"law_id": law_id, "structure": root})

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=["Laws"],
    summary="List states",
    description="Get sorted list of all Mexican states that have indexed laws.",
    responses={200: StatesListSchema},
)
@api_view(["GET"])
def states_list(request):
    """Get list of all states with law counts."""
    # Known state slugs and their proper names
    KNOWN_STATES = {
        "aguascalientes": "Aguascalientes",
        "baja_california_sur": "Baja California Sur",
        "baja_california": "Baja California",
        "campeche": "Campeche",
        "chiapas": "Chiapas",
        "chihuahua": "Chihuahua",
        "ciudad_de_mexico": "Ciudad de México",
        "coahuila": "Coahuila",
        "colima": "Colima",
        "durango": "Durango",
        "estado_de_mexico": "Estado de México",
        "guanajuato": "Guanajuato",
        "guerrero": "Guerrero",
        "hidalgo": "Hidalgo",
        "jalisco": "Jalisco",
        "michoacan": "Michoacán",
        "morelos": "Morelos",
        "nayarit": "Nayarit",
        "nuevo_leon": "Nuevo León",
        "oaxaca": "Oaxaca",
        "puebla": "Puebla",
        "queretaro": "Querétaro",
        "quintana_roo": "Quintana Roo",
        "san_luis_potosi": "San Luis Potosí",
        "sinaloa": "Sinaloa",
        "sonora": "Sonora",
        "tabasco": "Tabasco",
        "tamaulipas": "Tamaulipas",
        "tlaxcala": "Tlaxcala",
        "veracruz": "Veracruz",
        "yucatan": "Yucatán",
        "zacatecas": "Zacatecas",
    }

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

    # Article count from Elasticsearch
    total_articles = 0
    try:
        es = Elasticsearch([ES_HOST])
        if es.ping():
            count_res = es.count(index=INDEX_NAME)
            total_articles = count_res.get("count", 0)
    except Exception:
        pass

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
                "count": state_count,
                "universe": state_all_universe,
                "percentage": _safe_pct(state_count, state_all_universe),
                "description": "Incluye 23,660 leyes de otros poderes no descargadas aún",
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

    return Response(response_data)
