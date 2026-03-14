"""
API views for the legal knowledge graph.

Transforms CrossReference data into node+edge payloads for Sigma.js visualization.
"""

from collections import defaultdict

from django.db.models import Avg, Count, F, Q, Value
from django.db.models.functions import Coalesce
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.api.middleware.tier_permissions import RequireFeature
from apps.api.models import CrossReference, Law
from apps.api.schema import LawGraphResponseSchema

# ── Helpers ──────────────────────────────────────────────────────────────

_LAW_FIELDS = (
    "official_id",
    "name",
    "short_name",
    "tier",
    "category",
    "status",
    "law_type",
    "state",
)


def _aggregate_edges(queryset, source_field, target_field):
    """Aggregate cross-references into weighted edges between law pairs."""
    return (
        queryset.values(source=F(source_field), target=F(target_field))
        .annotate(
            weight=Count("id"),
            avg_confidence=Avg("confidence"),
        )
        .filter(weight__gte=1)
        .order_by("-weight")
    )


def _enrich_nodes(slugs, ref_counts, focal_slug=None):
    """Build enriched node dicts from a set of law slugs."""
    laws = Law.objects.filter(official_id__in=list(slugs)).values(*_LAW_FIELDS)
    law_map = {law["official_id"]: law for law in laws}

    nodes = []
    for slug in slugs:
        law = law_map.get(slug, {})
        nodes.append(
            {
                "id": slug,
                "label": law.get("name", slug),
                "short_name": law.get("short_name"),
                "tier": law.get("tier"),
                "category": law.get("category"),
                "status": law.get("status"),
                "law_type": law.get("law_type"),
                "state": law.get("state"),
                "ref_count": ref_counts.get(slug, 0),
                "is_focal": slug == focal_slug,
            }
        )
    return nodes


def _format_edges(edges_list):
    """Format edges for the response payload."""
    return [
        {
            "id": f"{e['source']}->{e['target']}",
            "source": e["source"],
            "target": e["target"],
            "weight": e["weight"],
            "avg_confidence": round(e["avg_confidence"], 3),
        }
        for e in edges_list
    ]


def _build_graph(focal_law_slug, depth, min_confidence, max_nodes, direction):
    """
    BFS expansion from a focal law, returning nodes and edges.

    Args:
        focal_law_slug: Starting law slug (or None for overview).
        depth: Number of BFS hops (1-3).
        min_confidence: Minimum average confidence for edges.
        max_nodes: Maximum nodes to return.
        direction: 'both', 'outgoing', or 'incoming'.

    Returns:
        (nodes_list, edges_list, meta_dict)
    """
    visited_slugs = set()
    all_edges = []
    frontier = {focal_law_slug}
    truncated = False

    for current_depth in range(depth):
        if not frontier:
            break

        visited_slugs.update(frontier)
        next_frontier = set()

        for slug in frontier:
            qs_base = CrossReference.objects.filter(confidence__gte=min_confidence)

            # Outgoing edges
            if direction in ("both", "outgoing"):
                outgoing = _aggregate_edges(
                    qs_base.filter(source_law_slug=slug).exclude(
                        target_law_slug__isnull=True
                    ),
                    "source_law_slug",
                    "target_law_slug",
                )
                for edge in outgoing:
                    all_edges.append(edge)
                    if edge["target"] not in visited_slugs:
                        next_frontier.add(edge["target"])

            # Incoming edges
            if direction in ("both", "incoming"):
                incoming = _aggregate_edges(
                    qs_base.filter(target_law_slug=slug),
                    "source_law_slug",
                    "target_law_slug",
                )
                for edge in incoming:
                    all_edges.append(edge)
                    if edge["source"] not in visited_slugs:
                        next_frontier.add(edge["source"])

        frontier = next_frontier

        # Check node cap
        if len(visited_slugs) + len(frontier) > max_nodes:
            # Keep only highest-weight new nodes
            remaining = max_nodes - len(visited_slugs)
            if remaining > 0:
                # Score frontier nodes by total edge weight
                node_weights = defaultdict(int)
                for e in all_edges:
                    if e["source"] in frontier:
                        node_weights[e["source"]] += e["weight"]
                    if e["target"] in frontier:
                        node_weights[e["target"]] += e["weight"]
                sorted_frontier = sorted(
                    frontier, key=lambda s: node_weights.get(s, 0), reverse=True
                )
                frontier = set(sorted_frontier[:remaining])
            else:
                frontier = set()
            truncated = True
            visited_slugs.update(frontier)
            break

    visited_slugs.update(frontier)

    # Deduplicate edges
    edge_map = {}
    for e in all_edges:
        key = (e["source"], e["target"])
        if key not in edge_map or e["weight"] > edge_map[key]["weight"]:
            edge_map[key] = e

    # Filter edges to only include nodes in visited set
    final_edges = [
        e
        for e in edge_map.values()
        if e["source"] in visited_slugs and e["target"] in visited_slugs
    ]

    # Compute per-node reference counts from edges
    ref_counts = defaultdict(int)
    for e in final_edges:
        ref_counts[e["source"]] += e["weight"]
        ref_counts[e["target"]] += e["weight"]

    nodes = _enrich_nodes(visited_slugs, ref_counts, focal_slug=focal_law_slug)
    edges_out = _format_edges(final_edges)

    depth_reached = min(depth, current_depth + 1) if all_edges else 0

    meta = {
        "total_nodes": len(nodes),
        "total_edges": len(edges_out),
        "depth_reached": depth_reached,
        "truncated": truncated,
    }

    return nodes, edges_out, meta


def _build_overview(tier=None, category=None, min_weight=3, max_nodes=300):
    """Build the global graph overview. Used by both authenticated and showcase endpoints."""
    qs = CrossReference.objects.exclude(target_law_slug__isnull=True)

    # Apply tier/category filters via Law joins
    if tier or category:
        law_filter = Q()
        if tier:
            law_filter &= Q(tier=tier)
        if category:
            law_filter &= Q(category=category)
        law_slugs = set(
            Law.objects.filter(law_filter).values_list("official_id", flat=True)
        )
        qs = qs.filter(
            Q(source_law_slug__in=law_slugs) | Q(target_law_slug__in=law_slugs)
        )

    # Single aggregate query
    edges_raw = (
        qs.values(source=F("source_law_slug"), target=F("target_law_slug"))
        .annotate(weight=Count("id"), avg_confidence=Avg("confidence"))
        .filter(weight__gte=min_weight)
        .order_by("-weight")
    )

    # Collect all slugs and apply node cap
    ref_counts = defaultdict(int)
    edges_list = []
    all_slugs = set()

    for e in edges_raw:
        all_slugs.add(e["source"])
        all_slugs.add(e["target"])
        ref_counts[e["source"]] += e["weight"]
        ref_counts[e["target"]] += e["weight"]
        edges_list.append(e)

    truncated = False
    if len(all_slugs) > max_nodes:
        # Keep highest-connected nodes
        sorted_slugs = sorted(
            all_slugs, key=lambda s: ref_counts.get(s, 0), reverse=True
        )
        all_slugs = set(sorted_slugs[:max_nodes])
        edges_list = [
            e
            for e in edges_list
            if e["source"] in all_slugs and e["target"] in all_slugs
        ]
        # Recompute ref_counts
        ref_counts = defaultdict(int)
        for e in edges_list:
            ref_counts[e["source"]] += e["weight"]
            ref_counts[e["target"]] += e["weight"]
        truncated = True

    nodes = _enrich_nodes(all_slugs, ref_counts)
    edges_out = _format_edges(edges_list)

    meta = {
        "total_nodes": len(nodes),
        "total_edges": len(edges_out),
        "depth_reached": 0,
        "truncated": truncated,
    }

    return nodes, edges_out, meta


# ── Endpoints ────────────────────────────────────────────────────────────


@extend_schema(
    tags=["Graph"],
    summary="Get law ego graph",
    description=(
        "Returns nodes and edges for the cross-reference network around a focal law. "
        "Supports BFS expansion up to depth 3."
    ),
    parameters=[
        OpenApiParameter("depth", int, description="BFS hops (1-3, default 1)"),
        OpenApiParameter(
            "min_confidence",
            float,
            description="Minimum edge confidence (default 0.5)",
        ),
        OpenApiParameter(
            "max_nodes", int, description="Maximum nodes (default 150, max 500)"
        ),
        OpenApiParameter(
            "direction",
            str,
            description="Edge direction: both, outgoing, incoming",
            enum=["both", "outgoing", "incoming"],
        ),
    ],
    responses={200: LawGraphResponseSchema},
)
@api_view(["GET"])
@permission_classes([RequireFeature.of("graph_api")])
def law_graph(request, law_id):
    """Per-law ego graph for Sigma.js visualization."""
    depth = min(int(request.query_params.get("depth", 1)), 3)
    min_confidence = float(request.query_params.get("min_confidence", 0.5))
    max_nodes = min(int(request.query_params.get("max_nodes", 150)), 500)
    direction = request.query_params.get("direction", "both")
    if direction not in ("both", "outgoing", "incoming"):
        direction = "both"

    nodes, edges, meta = _build_graph(
        law_id, depth, min_confidence, max_nodes, direction
    )

    return Response(
        {
            "focal_law": law_id,
            "nodes": nodes,
            "edges": edges,
            "meta": meta,
        }
    )


@extend_schema(
    tags=["Graph"],
    summary="Get global graph overview",
    description=(
        "Returns the global law cross-reference network, optionally filtered by "
        "tier or category. Uses a single aggregate query."
    ),
    parameters=[
        OpenApiParameter(
            "tier", str, description="Filter by tier (federal, state, municipal)"
        ),
        OpenApiParameter("category", str, description="Filter by legal domain"),
        OpenApiParameter(
            "min_weight", int, description="Minimum edge weight (default 3)"
        ),
        OpenApiParameter(
            "max_nodes", int, description="Maximum nodes (default 300, max 500)"
        ),
    ],
    responses={200: LawGraphResponseSchema},
)
@api_view(["GET"])
@permission_classes([RequireFeature.of("graph_api")])
def graph_overview(request):
    """Global law network for the universe map page."""
    tier = request.query_params.get("tier")
    category = request.query_params.get("category")
    min_weight = int(request.query_params.get("min_weight", 3))
    max_nodes = min(int(request.query_params.get("max_nodes", 300)), 500)

    nodes, edges, meta = _build_overview(tier, category, min_weight, max_nodes)

    return Response(
        {
            "focal_law": None,
            "nodes": nodes,
            "edges": edges,
            "meta": meta,
        }
    )


@extend_schema(
    tags=["Graph"],
    summary="Public graph showcase",
    description=(
        "Returns a curated subset of the global law network for unauthenticated users. "
        "Top 50 most-connected nodes with min_weight=5."
    ),
    responses={200: LawGraphResponseSchema},
)
@api_view(["GET"])
def graph_public_showcase(request):
    """Public showcase graph — no auth required. Capped at 50 nodes."""
    nodes, edges, meta = _build_overview(
        tier=None, category=None, min_weight=5, max_nodes=50
    )

    return Response(
        {
            "focal_law": None,
            "nodes": nodes,
            "edges": edges,
            "meta": meta,
        }
    )
