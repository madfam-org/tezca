from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from elasticsearch import Elasticsearch
import os
import math

ES_HOST = os.getenv("ES_HOST", "http://elasticsearch:9200")
INDEX_NAME = "articles"

class SearchView(APIView):
    def get(self, request):
        query = request.query_params.get("q", "")
        if not query:
            return Response({"results": [], "total": 0})

        try:
            es = Elasticsearch([ES_HOST])
            if not es.ping():
                 # Fallback for dev/demo if ES is down
                 return Response({
                     "results": [], 
                     "warning": "Search Engine offline"
                 }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            # Get filter parameters
            jurisdiction = request.query_params.get("jurisdiction", "federal")
            category = request.query_params.get("category", None)
            search_status = request.query_params.get("status", "all")
            sort_by = request.query_params.get("sort", "relevance")
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))

            # Build Elasticsearch query
            must_clauses = [
                {
                    "multi_match": {
                        "query": query,
                        "fields": ["text", "tags"],
                        "fuzziness": "AUTO"
                    }
                }
            ]

            # Add filter clauses
            filter_clauses = []

            # Jurisdiction filter
            if jurisdiction and jurisdiction != "all":
                jurisdictions = jurisdiction.split(',')
                # If only one type is selected, filter by tier
                if 'federal' in jurisdictions and 'state' not in jurisdictions:
                    filter_clauses.append({"term": {"tier.keyword": "federal"}})
                elif 'state' in jurisdictions and 'federal' not in jurisdictions:
                    filter_clauses.append({"term": {"tier.keyword": "state"}})

            # Category filter
            if category and category != "all":
                filter_clauses.append({"term": {"category.keyword": category}})

            # State filter
            state_filter = request.query_params.get("state", None)
            if state_filter and state_filter != "all":
                # State ID prefix (e.g., "Colima" -> "colima_")
                prefix = f"{state_filter.lower()}_"
                filter_clauses.append({"prefix": {"law_id.keyword": prefix}})

            # Date Range Filter
            date_range = request.query_params.get("date_range", None)
            if date_range and date_range != "all":
                from datetime import datetime, timedelta
                now = datetime.now()
                
                if date_range == "2024":
                    # Current Year (Assuming 2024 context, or generic current year)
                    # Ideally dynamically get current year if "this_year"
                    start_date = "2024-01-01"
                    end_date = "2024-12-31"
                    filter_clauses.append({"range": {"publication_date": {"gte": start_date, "lte": end_date}}})
                
                elif date_range == "2023":
                    start_date = "2023-01-01"
                    end_date = "2023-12-31"
                    filter_clauses.append({"range": {"publication_date": {"gte": start_date, "lte": end_date}}})
                
                elif date_range == "last_5_years":
                    start_year = now.year - 5
                    start_date = f"{start_year}-01-01"
                    filter_clauses.append({"range": {"publication_date": {"gte": start_date}}})
                
                elif date_range == "older":
                    # Older than 5 years
                    end_year = now.year - 5
                    end_date = f"{end_year}-01-01"
                    filter_clauses.append({"range": {"publication_date": {"lt": end_date}}})

            # Search status (vigente/abrogado) - not fully indexed yet, placeholder
            # if search_status and search_status != "all": ...

            # Build the full query
            es_query = {
                "bool": {
                    "must": must_clauses
                }
            }

            if filter_clauses:
                es_query["bool"]["filter"] = filter_clauses

            # Determine sort order
            sort_option = []
            if sort_by == "date_desc":
                sort_option = [{"publication_date": {"order": "desc"}}]
            elif sort_by == "date_asc":
                sort_option = [{"publication_date": {"order": "asc"}}]
            elif sort_by == "name":
                sort_option = [{"law_id.keyword": {"order": "asc"}}]
            # Default to relevance (no explicit sort, uses _score)

            # Calculate pagination
            offset = (page - 1) * page_size

            # Build request body
            body = {
                "query": es_query,
                "highlight": {
                    "fields": {
                        "text": {}
                    }
                },
                "from": offset,
                "size": page_size
            }

            if sort_option:
                body["sort"] = sort_option
            
            # Execute search
            res = es.search(index=INDEX_NAME, body=body)
            hits = res['hits']['hits']
            total = res['hits']['total']['value']
            
            # Format results
            results = []
            for hit in hits:
                source = hit['_source']
                highlight = hit.get('highlight', {}).get('text', [source['text'][:200]])[0]
                results.append({
                    "id": hit['_id'],
                    "law_id": source.get('law_id'),
                    "law_name": source.get('law_name', source.get('law_id')), # Fallback to ID if name missing
                    "article": f"Art. {source.get('article', source.get('article_id'))}",
                    "snippet": highlight,
                    "date": source.get('publication_date'),
                    "score": hit['_score']
                })

            # Calculate pagination metadata
            total_pages = math.ceil(total / page_size) if total > 0 else 0

            return Response({
                "results": results,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            })
            
        except ValueError as e:
            return Response({
                "error": f"Invalid parameter: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
