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

            # Jurisdiction filter (via law_id prefix - federal laws are lowercase)
            # Note: This is a simple heuristic. You may need to query the Law model
            # for more accurate jurisdiction filtering
            if jurisdiction and jurisdiction != "all":
                jurisdictions = jurisdiction.split(',')
                if 'federal' in jurisdictions and 'state' not in jurisdictions:
                    # Only federal - law IDs are typically lowercase abbreviations
                    # This is a placeholder - you may want to query Law model instead
                    pass  # For now, return all (most are federal anyway)
                elif 'state' in jurisdictions and 'federal' not in jurisdictions:
                    # Only state laws - would need Law model query
                    pass

            # Category filter (would need to join with Law model - skipping for now)
            # In a production system, you'd want to:
            # 1. Query Law model for laws matching category
            # 2. Filter by those law_ids
            # For now, we'll skip category filtering at ES level

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
                    "law": source.get('law_id'),
                    "article": f"Art. {source.get('article_id')}",
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
