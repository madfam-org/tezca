"""
Helper functions for integrating cross-reference detection into the ingestion pipeline.
"""

from pathlib import Path
from typing import Dict, List
from lxml import etree

from apps.parsers.cross_references import CrossReferenceDetector


def detect_and_store_cross_references(
    law_slug: str,
    xml_path: Path,
    detector: CrossReferenceDetector = None
) -> int:
    """
    Detect cross-references in a parsed law's XML and store them in the database.
    
    Args:
        law_slug: The law's slug identifier
        xml_path: Path to the Akoma Ntoso XML file
        detector: Optional detector instance (will create if not provided)
        
    Returns:
        Number of cross-references detected and stored
    """
    if detector is None:
        detector = CrossReferenceDetector()
    
    # Parse XML
    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    ns = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
    
    # Find all articles
    articles = root.findall('.//akn:article', ns)
    
    total_refs = 0
    
    for article in articles:
        article_id = article.get('id', '').replace('art-', '')
        if not article_id:
            continue
        
        # Get article text content
        paragraphs = article.findall('.//akn:p', ns)
        article_text = ' '.join([p.text or '' for p in paragraphs])
        
        # Detect references in this article
        refs = detector.detect(article_text)
        
        # Store in database
        for ref in refs:
            # Try to resolve law name to slug
            # TODO: Implement slug resolution with actual database lookup
            target_slug = None  # Will be None for now, can be resolved later
            
            # For now, we'll just print what we found
            # In production, this would save to CrossReference model
            print(f"   Found reference in {article_id}: {ref.text} (confidence: {ref.confidence:.2f})")
            total_refs += 1
    
    return total_refs


def detect_cross_references_from_articles(
    law_slug: str,
    articles: List[Dict],
    detector: CrossReferenceDetector = None
) -> List[Dict]:
    """
    Detect cross-references from a list of article dictionaries.
    
    Args:
        law_slug: The law's slug identifier
        articles: List of article dicts with 'article_id' and 'text' keys
        detector: Optional detector instance
        
    Returns:
        List of reference dicts ready to be stored
    """
    if detector is None:
        detector = CrossReferenceDetector()
    
    all_references = []
    
    for article in articles:
        article_id = article.get('article_id')
        text = article.get('text', '')
        
        if not article_id or not text:
            continue
        
        # Detect references
        refs = detector.detect(text)
        
        # Convert to dict format
        for ref in refs:
            ref_dict = {
                'source_law_slug': law_slug,
                'source_article_id': article_id,
                'target_law_slug': None,  # TODO: Resolve
                'target_article_num': ref.article_num,
                'reference_text': ref.text,
                'fraction': ref.fraction,
                'confidence': ref.confidence,
                'start_position': ref.start_pos,
                'end_position': ref.end_pos,
            }
            all_references.append(ref_dict)
    
    return all_references
