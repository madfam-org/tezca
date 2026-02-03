from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from .models import Law, LawVersion
from django.shortcuts import get_object_or_404
from elasticsearch import Elasticsearch

# Elasticsearch config
ES_HOST = "http://elasticsearch:9200"
INDEX_NAME = "articles"

class LawDetailView(APIView):
    def get(self, request, law_id):
        # 1. Get Law
        law = get_object_or_404(Law, official_id=law_id)
        
        # 2. Get Versions
        versions = law.versions.all().order_by('-publication_date')
        
        # 3. Extract state from official_id (for state laws)
        state = None
        if law.tier == 'state' and '_' in law_id:
            state = law_id.split('_')[0].replace('_', ' ').title()
        
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
                    "xml_file": v.xml_file_path.split('/')[-1] if v.xml_file_path else None
                }
                for v in versions
            ],
             # Fallback stats for UI compatibility
            "articles": 0, # To be filled by ES count ideally
            "grade": "A",
            "score": 100
        }
        
        return Response(data)

class LawListView(APIView):
    def get(self, request):
        laws = Law.objects.all().order_by('official_id')
        data = [
            {
                "id": law.official_id,
                "name": law.short_name or law.name,
                "versions": law.versions.count()
            }
            for law in laws
        ]
        return Response(data)


@api_view(['GET'])
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
            "query": {
                "match_phrase": {"law_id": law.official_id}
            },
            "sort": [
                {"article.keyword": {"order": "asc"}}
            ],
            "size": 10000  # Max articles per law
        }
        
        res = es.search(index=INDEX_NAME, body=body)
        
        articles = []
        for hit in res['hits']['hits']:
            source = hit['_source']
            articles.append({
                'article_id': source.get('article'),
                'text': source.get('text'),
            })
        
        return Response({
            'law_id': law_id,
            'law_name': law.name,
            'total': len(articles),
            'articles': articles
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def states_list(request):
    """Get list of all states with law counts."""
    # Known state slugs and their proper names
    KNOWN_STATES = {
        'aguascalientes': 'Aguascalientes',
        'baja_california_sur': 'Baja California Sur',
        'baja_california': 'Baja California',
        'campeche': 'Campeche',
        'chiapas': 'Chiapas',
        'chihuahua': 'Chihuahua',
        'ciudad_de_mexico': 'Ciudad de México',
        'coahuila': 'Coahuila',
        'colima': 'Colima',
        'durango': 'Durango',
        'estado_de_mexico': 'Estado de México',
        'guanajuato': 'Guanajuato',
        'guerrero': 'Guerrero',
        'hidalgo': 'Hidalgo',
        'jalisco': 'Jalisco',
        'michoacan': 'Michoacán',
        'morelos': 'Morelos',
        'nayarit': 'Nayarit',
        'nuevo_leon': 'Nuevo León',
        'oaxaca': 'Oaxaca',
        'puebla': 'Puebla',
        'queretaro': 'Querétaro',
        'quintana_roo': 'Quintana Roo',
        'san_luis_potosi': 'San Luis Potosí',
        'sinaloa': 'Sinaloa',
        'sonora': 'Sonora',
        'tabasco': 'Tabasco',
        'tamaulipas': 'Tamaulipas',
        'tlaxcala': 'Tlaxcala',
        'veracruz': 'Veracruz',
        'yucatan': 'Yucatán',
        'zacatecas': 'Zacatecas'
    }

    # Get all state law IDs
    state_law_ids = Law.objects.filter(tier='state').values_list('official_id', flat=True)
    
    found_states = set()
    
    for official_id in state_law_ids:
        # Check for multi-word states first (longer matches)
        # We sort keys by length descending to match 'baja_california_sur' before 'baja_california'
        for slug in sorted(KNOWN_STATES.keys(), key=len, reverse=True):
            if official_id.startswith(f"{slug}_"):
                found_states.add(KNOWN_STATES[slug])
                break
    
    return Response({
        'states': sorted(list(found_states))
    })

@api_view(['GET'])
def law_stats(request):
    """Get global statistics for the dashboard."""
    total_laws = Law.objects.count()
    federal_count = Law.objects.filter(tier='federal').count()
    state_count = Law.objects.filter(tier='state').count()
    
    # Get recent laws (most recent version publication date)
    recent_versions = LawVersion.objects.select_related('law').order_by('-publication_date')[:5]
    recent_laws = []
    for v in recent_versions:
        recent_laws.append({
            'id': v.law.official_id,
            'name': v.law.short_name or v.law.name,
            'date': v.publication_date,
            'tier': v.law.tier,
            'category': v.law.category
        })

    last_update = recent_versions[0].publication_date if recent_versions else None

    return Response({
        'total_laws': total_laws,
        'federal_count': federal_count,
        'state_count': state_count,
        'last_update': last_update,
        'recent_laws': recent_laws
    })
