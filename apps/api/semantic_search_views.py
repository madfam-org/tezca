"""
Semantic search endpoint using Elasticsearch kNN with embeddings.

Returns results in the same format as SearchView for API compatibility.
"""

import logging

from elasticsearch.exceptions import ApiError
from elasticsearch.exceptions import ConnectionError as ESConnectionError
from elasticsearch.exceptions import ConnectionTimeout
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .config import es_client

logger = logging.getLogger(__name__)

INDEX_ARTICLES = "articles"


@api_view(["GET"])
def semantic_search(request):
    """
    GET /api/v1/search/semantic/?q={query}&limit=10

    Generates a query embedding and runs ES kNN search against the
    text_embedding field. Returns the same response format as the
    keyword search endpoint for API compatibility.
    """
    query = request.query_params.get("q", "").strip()
    if not query:
        return Response({"error": "Query parameter 'q' is required"}, status=400)

    limit = min(int(request.query_params.get("limit", 10)), 50)

    # Generate query embedding
    try:
        from apps.parsers.embeddings import EmbeddingGenerator

        generator = EmbeddingGenerator()
        query_embedding = generator.generate(query)
    except ImportError:
        return Response(
            {
                "error": "Semantic search is not available — embedding model not installed"
            },
            status=503,
        )
    except Exception as e:
        logger.error("Failed to generate query embedding: %s", e)
        return Response({"error": "Failed to generate query embedding"}, status=500)

    # Run kNN search
    try:
        body = {
            "knn": {
                "field": "text_embedding",
                "query_vector": query_embedding,
                "k": limit,
                "num_candidates": limit * 10,
            },
            "_source": [
                "law_id",
                "law_name",
                "article",
                "text",
                "tier",
                "category",
                "domains",
                "state",
                "municipality",
                "hierarchy",
                "book",
                "title",
                "chapter",
                "publication_date",
                "law_type",
                "status",
            ],
        }

        response = es_client.search(index=INDEX_ARTICLES, body=body)

        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            results.append(
                {
                    "id": hit["_id"],
                    "law_id": source.get("law_id"),
                    "law_name": source.get("law_name"),
                    "article": source.get("article"),
                    "snippet": (source.get("text") or "")[:300],
                    "text": (source.get("text") or "")[:500],
                    "date": source.get("publication_date"),
                    "score": hit.get("_score", 0),
                    "tier": source.get("tier"),
                    "law_type": source.get("law_type"),
                    "state": source.get("state"),
                    "municipality": source.get("municipality"),
                    "hierarchy": source.get("hierarchy", []),
                    "book": source.get("book"),
                    "title": source.get("title"),
                    "chapter": source.get("chapter"),
                }
            )

        return Response(
            {
                "results": results,
                "total": len(results),
                "page": 1,
                "page_size": limit,
                "total_pages": 1,
            }
        )

    except (ApiError, ESConnectionError, ConnectionTimeout) as e:
        logger.error("Semantic search failed: %s", e)
        return Response({"error": "Search service unavailable"}, status=503)
