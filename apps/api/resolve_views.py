"""
Resolve endpoint — combined article + judicial search.

Given a problem description and optional domain hint, returns the most
relevant legislative articles (via Elasticsearch) and judicial records
(via Django ORM) in a single response.  Designed for AI agent and
programmatic consumption.

Public endpoint — no authentication required.
"""

import logging
import time

from elasticsearch.exceptions import ConnectionError as ESConnectionError
from elasticsearch.exceptions import ConnectionTimeout
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .config import INDEX_NAME, es_client
from .constants import DOMAIN_MAP
from .models import JudicialRecord

logger = logging.getLogger(__name__)


@api_view(["GET"])
def resolve(request):
    """
    Combined legal resolution search.

    Query params:
        q           (required)  Problem description or search query.
        domain      (optional)  Legal domain hint (e.g. "labor", "fiscal").
                                Mapped via DOMAIN_MAP for composite domains.
        max_articles (optional) Max article results to return (default 3, max 10).
        max_judicial (optional) Max judicial results to return (default 2, max 10).
    """
    query = request.query_params.get("q", "").strip()
    if not query:
        return Response(
            {"error": "Query parameter 'q' is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    domain = request.query_params.get("domain", "").strip() or None

    try:
        max_articles = min(10, max(1, int(request.query_params.get("max_articles", 3))))
    except (ValueError, TypeError):
        max_articles = 3

    try:
        max_judicial = min(10, max(1, int(request.query_params.get("max_judicial", 2))))
    except (ValueError, TypeError):
        max_judicial = 2

    _t0 = time.monotonic()

    # ── 1. Elasticsearch article search ──────────────────────────────
    articles = []
    articles_degraded = False

    try:
        es = es_client
        if not es.ping():
            articles_degraded = True
        else:
            must_clauses = [
                {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "law_name^3",
                            "law_name.keyword^5",
                            "text^1",
                            "tags^0.5",
                        ],
                        "fuzziness": "AUTO",
                    }
                }
            ]

            should_clauses = [
                {"term": {"status": {"value": "vigente", "boost": 1.5}}},
                {"match_phrase": {"text": {"query": query, "boost": 3.0, "slop": 1}}},
            ]

            filter_clauses = []
            if domain:
                target_domains = DOMAIN_MAP.get(domain, [domain])
                filter_clauses.append({"terms": {"domains": target_domains}})

            es_query = {
                "bool": {
                    "must": must_clauses,
                    "should": should_clauses,
                }
            }
            if filter_clauses:
                es_query["bool"]["filter"] = filter_clauses

            res = es.search(
                index=INDEX_NAME,
                query=es_query,
                highlight={
                    "fields": {
                        "text": {"number_of_fragments": 1, "fragment_size": 250},
                    }
                },
                size=max_articles,
            )

            for hit in res["hits"]["hits"]:
                source = hit["_source"]
                highlight = hit.get("highlight", {}).get(
                    "text", [source.get("text", "")[:250]]
                )
                articles.append(
                    {
                        "law_id": source.get("law_id"),
                        "law_name": source.get("law_name", source.get("law_id")),
                        "article": f"Art. {source.get('article', source.get('article_id'))}",
                        "snippet": highlight[0] if highlight else "",
                        "score": hit["_score"],
                        "tier": source.get("tier"),
                        "domains": source.get("domains", []),
                    }
                )

    except (ESConnectionError, ConnectionTimeout):
        logger.warning("Resolve: ES unavailable", exc_info=True)
        articles_degraded = True

    # ── 2. Django ORM judicial search ────────────────────────────────
    from django.db.models import Q

    judicial_qs = JudicialRecord.objects.filter(
        Q(rubro__icontains=query) | Q(texto__icontains=query)
    )

    if domain:
        judicial_qs = judicial_qs.filter(materia__icontains=domain)

    judicial_records = judicial_qs[:max_judicial]

    judicial = [
        {
            "registro": rec.registro,
            "tipo": rec.tipo,
            "materia": rec.materia,
            "rubro": rec.rubro,
            "epoca": rec.epoca,
            "instancia": rec.instancia,
        }
        for rec in judicial_records
    ]

    # ── 3. Build response ────────────────────────────────────────────
    elapsed_ms = int((time.monotonic() - _t0) * 1000)

    response_data = {
        "articles": articles,
        "judicial": judicial,
        "query": query,
        "domain": domain,
        "response_time_ms": elapsed_ms,
    }

    if articles_degraded:
        response_data["degraded"] = True

    response = Response(response_data)
    response["Cache-Control"] = "public, max-age=60"
    return response
