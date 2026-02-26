import hashlib
import logging
import math
import time

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .config import INDEX_NAME, es_client
from .constants import DOMAIN_MAP
from .schema import SEARCH_PARAMETERS, ErrorSchema, SearchResponseSchema

logger = logging.getLogger(__name__)


def _log_search_query(query, filters, result_count, response_time_ms, request):
    """Fire-and-forget search query logging."""
    try:
        from .models import SearchQuery

        ip = request.META.get("REMOTE_ADDR", "")
        session_id = hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else ""
        SearchQuery.objects.create(
            query=query[:500],
            filters=filters,
            result_count=result_count,
            response_time_ms=response_time_ms,
            session_id=session_id,
        )
    except Exception:
        logger.debug("Failed to log search query", exc_info=True)


class SearchView(APIView):

    @extend_schema(
        tags=["Search"],
        summary="Search articles",
        description="Full-text search across all indexed law articles with filtering and pagination.",
        parameters=SEARCH_PARAMETERS,
        responses={200: SearchResponseSchema, 400: ErrorSchema, 500: ErrorSchema},
    )
    def get(self, request):
        query = request.query_params.get("q", "")
        if not query:
            return Response({"results": [], "total": 0})

        _t0 = time.monotonic()
        try:
            es = es_client
            if not es.ping():
                # Fallback for dev/demo if ES is down
                return Response(
                    {"results": [], "warning": "Search Engine offline"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            # Get filter parameters
            jurisdiction = request.query_params.get("jurisdiction", "all")
            category = request.query_params.get("category", None)
            search_status = request.query_params.get("status", "all")
            sort_by = request.query_params.get("sort", "relevance")
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(max(1, int(request.query_params.get("page_size", 10))), 100)

            # Build Elasticsearch query
            must_clauses = [
                {
                    "multi_match": {
                        "query": query,
                        "fields": ["text", "tags"],
                        "fuzziness": "AUTO",
                    }
                }
            ]

            # Add filter clauses
            filter_clauses = []

            # Domain filter (maps to multiple categories)
            domain = request.query_params.get("domain")
            if domain and domain in DOMAIN_MAP:
                filter_clauses.append({"terms": {"category": DOMAIN_MAP[domain]}})

            # Category filter (supports comma-separated)
            if category and category != "all":
                cats = [c.strip() for c in category.split(",") if c.strip()]
                if len(cats) > 1:
                    filter_clauses.append({"terms": {"category": cats}})
                else:
                    filter_clauses.append({"term": {"category": cats[0]}})

            # Municipality filter
            municipality = request.query_params.get("municipality", None)
            if municipality and municipality != "all":
                filter_clauses.append({"term": {"municipality": municipality}})

            # Jurisdiction filter (Enhanced for municipal)
            if jurisdiction and jurisdiction != "all":
                jurisdictions = jurisdiction.split(",")

                # Build should clauses for selected jurisdictions
                tier_should = []
                if "federal" in jurisdictions:
                    tier_should.append({"term": {"tier": "federal"}})
                if "state" in jurisdictions:
                    tier_should.append({"term": {"tier": "state"}})
                if "municipal" in jurisdictions:
                    tier_should.append({"term": {"tier": "municipal"}})

                # If we have specific tiers selected, enforce at least one matches
                if tier_should:
                    filter_clauses.append(
                        {"bool": {"should": tier_should, "minimum_should_match": 1}}
                    )

            # Structural/Hierarchy Filters (New in V2)
            # Example: ?title=Titulo Primero&chapter=Capitulo I
            structural_title = request.query_params.get("title", None)
            structural_chapter = request.query_params.get("chapter", None)

            if structural_title:
                filter_clauses.append({"match": {"title": structural_title}})
            if structural_chapter:
                filter_clauses.append({"match": {"chapter": structural_chapter}})

            # State filter
            state_filter = request.query_params.get("state", None)
            if state_filter and state_filter != "all":
                # State ID prefix (e.g., "Colima" -> "colima_")
                prefix = f"{state_filter.lower()}_"
                filter_clauses.append({"prefix": {"law_id": prefix}})

            # Date Range Filter
            date_range = request.query_params.get("date_range", None)
            if date_range and date_range != "all":
                from datetime import timedelta

                from django.utils import timezone

                now = timezone.now()

                if date_range == "this_year":
                    current_year = now.year
                    start_date = f"{current_year}-01-01"
                    end_date = f"{current_year}-12-31"
                    filter_clauses.append(
                        {
                            "range": {
                                "publication_date": {"gte": start_date, "lte": end_date}
                            }
                        }
                    )

                elif date_range == "last_year":
                    last_year = now.year - 1
                    start_date = f"{last_year}-01-01"
                    end_date = f"{last_year}-12-31"
                    filter_clauses.append(
                        {
                            "range": {
                                "publication_date": {"gte": start_date, "lte": end_date}
                            }
                        }
                    )

                elif date_range == "last_5_years":
                    start_year = now.year - 5
                    start_date = f"{start_year}-01-01"
                    filter_clauses.append(
                        {"range": {"publication_date": {"gte": start_date}}}
                    )

                elif date_range == "older":
                    # Older than 5 years
                    end_year = now.year - 5
                    end_date = f"{end_year}-01-01"
                    filter_clauses.append(
                        {"range": {"publication_date": {"lt": end_date}}}
                    )

            # Search status (vigente/abrogado)
            if search_status and search_status != "all":
                filter_clauses.append({"term": {"status": search_status}})

            # Law type filter (legislative / non_legislative)
            law_type = request.query_params.get("law_type", "all")
            if law_type and law_type != "all":
                filter_clauses.append({"term": {"law_type": law_type}})

            # Build the full query
            es_query = {"bool": {"must": must_clauses}}

            if filter_clauses:
                es_query["bool"]["filter"] = filter_clauses

            # Determine sort order
            sort_option = []
            if sort_by == "date_desc":
                sort_option = [{"publication_date": {"order": "desc"}}]
            elif sort_by == "date_asc":
                sort_option = [{"publication_date": {"order": "asc"}}]
            elif sort_by == "name":
                sort_option = [{"law_id": {"order": "asc"}}]
            # Default to relevance (no explicit sort, uses _score)

            # Calculate pagination
            offset = (page - 1) * page_size

            # Build search kwargs (ES 8 keyword args)
            search_kwargs = {
                "index": INDEX_NAME,
                "query": es_query,
                "highlight": {"fields": {"text": {}}},
                "from_": offset,
                "size": page_size,
                "aggs": {
                    "by_tier": {"terms": {"field": "tier"}},
                    "by_category": {"terms": {"field": "category", "size": 20}},
                    "by_status": {"terms": {"field": "status"}},
                    "by_law_type": {"terms": {"field": "law_type"}},
                    "by_state": {"terms": {"field": "state", "size": 35}},
                },
            }

            if sort_option:
                search_kwargs["sort"] = sort_option

            # Execute search
            res = es.search(**search_kwargs)
            hits = res["hits"]["hits"]
            total = res["hits"]["total"]["value"]

            # Parse aggregation facets
            facets = {
                key: [
                    {"key": b["key"], "count": b["doc_count"]} for b in agg["buckets"]
                ]
                for key, agg in res.get("aggregations", {}).items()
            }

            # Format results
            results = []
            for hit in hits:
                source = hit["_source"]
                highlight = hit.get("highlight", {}).get(
                    "text", [source["text"][:200]]
                )[0]
                results.append(
                    {
                        "id": hit["_id"],
                        "law_id": source.get("law_id"),
                        "law_name": source.get(
                            "law_name", source.get("law_id")
                        ),  # Fallback to ID if name missing
                        "article": f"Art. {source.get('article', source.get('article_id'))}",
                        "snippet": highlight,
                        "date": source.get("publication_date"),
                        "score": hit["_score"],
                        "tier": source.get("tier"),
                        "law_type": source.get("law_type"),
                        "state": source.get("state"),
                        "municipality": source.get("municipality"),
                        # V2 Hierarchy fields
                        "hierarchy": source.get("hierarchy", []),
                        "book": source.get("book"),
                        "title": source.get("title"),
                        "chapter": source.get("chapter"),
                    }
                )

            # Calculate pagination metadata
            total_pages = math.ceil(total / page_size) if total > 0 else 0

            response = Response(
                {
                    "results": results,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "facets": facets,
                }
            )
            response["Cache-Control"] = "public, max-age=300"

            # Log search query for analytics (fire-and-forget)
            _elapsed_ms = int((time.monotonic() - _t0) * 1000)
            _filters = {}
            if jurisdiction and jurisdiction != "all":
                _filters["jurisdiction"] = jurisdiction
            if category:
                _filters["category"] = category
            if state_filter:
                _filters["state"] = state_filter
            if law_type and law_type != "all":
                _filters["law_type"] = law_type
            _log_search_query(query, _filters, total, _elapsed_ms, request)

            return response

        except ValueError:
            return Response(
                {
                    "error": "Invalid parameter value. Check page and page_size are valid numbers."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("SearchView failed")
            return Response(
                {"error": "An internal error occurred while searching."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
