"""
API views for cross-references.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from apps.api.models import CrossReference


@api_view(['GET'])
def article_cross_references(request, law_slug, article_id):
    """
    Get cross-references for a specific article.
    
    Returns both:
    - outgoing: References this article makes to other laws/articles
    - incoming: References from other articles to this article
    
    Example: GET /api/v1/laws/amparo/articles/107/references/
    """
    # Get outgoing references (references this article makes)
    outgoing_refs = CrossReference.objects.filter(
        source_law_slug=law_slug,
        source_article_id=article_id
    ).order_by('start_position')
    
    # Get incoming references (references to this article)
    incoming_refs = CrossReference.objects.filter(
        target_law_slug=law_slug,
        target_article_num=article_id
    ).order_by('-confidence')
    
    # Format outgoing references
    outgoing_data = [
        {
            'text': ref.reference_text,
            'targetLawSlug': ref.target_law_slug,
            'targetArticle': ref.target_article_num,
            'fraction': ref.fraction,
            'confidence': ref.confidence,
            'startPos': ref.start_position,
            'endPos': ref.end_position,
            'targetUrl': ref.target_url() if ref.target_law_slug else None,
        }
        for ref in outgoing_refs
    ]
    
    # Format incoming references
    incoming_data = [
        {
            'sourceLawSlug': ref.source_law_slug,
            'sourceArticle': ref.source_article_id,
            'text': ref.reference_text,
            'confidence': ref.confidence,
            'sourceUrl': f"/laws/{ref.source_law_slug}#article-{ref.source_article_id}",
        }
        for ref in incoming_refs
    ]
    
    return Response({
        'outgoing': outgoing_data,
        'incoming': incoming_data,
        'total_outgoing': len(outgoing_data),
        'total_incoming': len(incoming_data),
    })


@api_view(['GET'])
def law_cross_references(request, law_slug):
    """
    Get all cross-references for a law.
    
    Returns statistics and top references.
    
    Example: GET /api/v1/laws/amparo/references/
    """
    # Get all outgoing references for this law
    outgoing = CrossReference.objects.filter(
        source_law_slug=law_slug
    ).select_related()
    
    # Get all incoming references to this law
    incoming = CrossReference.objects.filter(
        target_law_slug=law_slug
    ).select_related()
    
    # Calculate statistics
    total_outgoing = outgoing.count()
    total_incoming = incoming.count()
    
    # Get top referenced laws (outgoing)
    from django.db.models import Count
    top_targets = outgoing.values('target_law_slug').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Get top citing laws (incoming)
    top_sources = incoming.values('source_law_slug').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    return Response({
        'statistics': {
            'total_outgoing': total_outgoing,
            'total_incoming': total_incoming,
            'most_referenced_laws': [
                {'slug': item['target_law_slug'], 'count': item['count']}
                for item in top_targets if item['target_law_slug']
            ],
            'most_citing_laws': [
                {'slug': item['source_law_slug'], 'count': item['count']}
                for item in top_sources
            ],
        }
    })
