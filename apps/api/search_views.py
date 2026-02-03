from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from elasticsearch import Elasticsearch
import os

ES_HOST = os.getenv("ES_HOST", "http://elasticsearch:9200")
INDEX_NAME = "laws"

class SearchView(APIView):
    def get(self, request):
        query = request.query_params.get("q", "")
        if not query:
            return Response({"results": []})

        try:
            es = Elasticsearch([ES_HOST])
            if not es.ping():
                 # Fallback for dev/demo if ES is down
                 return Response({"results": [], "warning": "Search Engine offline"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            # Simple multi-match query
            body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["text", "law_title", "tags"],
                        "fuzziness": "AUTO"
                    }
                },
                "highlight": {
                    "fields": {
                        "text": {}
                    }
                }
            }
            
            res = es.search(index=INDEX_NAME, body=body)
            hits = res['hits']['hits']
            
            results = []
            for hit in hits:
                source = hit['_source']
                highlight = hit.get('highlight', {}).get('text', [source['text'][:200]])[0]
                results.append({
                    "id": hit['_id'],
                    "law": source['law_title'],
                    "article": f"Art. {source['article_num']}",
                    "snippet": highlight,
                    "score": hit['_score']
                })

            return Response({"results": results})
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
