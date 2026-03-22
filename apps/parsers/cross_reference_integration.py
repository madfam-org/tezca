"""
Helper functions for integrating cross-reference detection into the ingestion pipeline.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from lxml import etree

from apps.parsers.cross_references import CrossReferenceDetector

logger = logging.getLogger(__name__)


def _build_law_slug_index() -> Dict[str, str]:
    """
    Build a mapping of normalized law names to their slugs from the database.

    Returns:
        Dict mapping normalized law name -> official_id slug
    """
    from apps.api.models import Law

    slug_index = {}
    for law in Law.objects.only("official_id", "name", "short_name"):
        detector = CrossReferenceDetector()
        # Index both full name and short name
        if law.name:
            normalized = detector._normalize_law_name(law.name)
            slug_index[normalized] = law.official_id
        if law.short_name:
            normalized = detector._normalize_law_name(law.short_name)
            slug_index[normalized] = law.official_id

    return slug_index


def detect_and_store_cross_references(
    law_slug: str,
    xml_path: Path,
    detector: CrossReferenceDetector = None,
    slug_index: Dict[str, str] = None,
) -> int:
    """
    Detect cross-references in a parsed law's XML and store them in the database.

    Args:
        law_slug: The law's slug identifier
        xml_path: Path to the Akoma Ntoso XML file
        detector: Optional detector instance (will create if not provided)
        slug_index: Optional pre-built slug index (avoids rebuilding per call)

    Returns:
        Number of cross-references detected and stored
    """
    from apps.api.models import CrossReference

    if detector is None:
        detector = CrossReferenceDetector()

    if slug_index is None:
        slug_index = _build_law_slug_index()

    # Parse XML
    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    ns = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}

    # Find all articles
    articles = root.findall(".//akn:article", ns)

    refs_to_create = []

    for article in articles:
        article_id = article.get("id", "").replace("art-", "")
        if not article_id:
            continue

        # Get article text content
        paragraphs = article.findall(".//akn:p", ns)
        article_text = " ".join([p.text or "" for p in paragraphs])

        # Detect references in this article
        refs = detector.detect(article_text)

        for ref in refs:
            target_slug = detector.resolve_law_slug(ref.law_name, slug_index)

            refs_to_create.append(
                CrossReference(
                    source_law_slug=law_slug,
                    source_article_id=article_id,
                    target_law_slug=target_slug,
                    target_article_num=ref.article_num,
                    reference_text=ref.text,
                    fraction=ref.fraction,
                    confidence=ref.confidence,
                    start_position=ref.start_pos,
                    end_position=ref.end_pos,
                )
            )

    if refs_to_create:
        # Delete old references for this law before inserting new ones
        CrossReference.objects.filter(source_law_slug=law_slug).delete()
        CrossReference.objects.bulk_create(refs_to_create, batch_size=500)
        logger.info(f"Stored {len(refs_to_create)} cross-references for {law_slug}")

    return len(refs_to_create)


def detect_cross_references_from_articles(
    law_slug: str,
    articles: List[Dict],
    detector: CrossReferenceDetector = None,
    persist: bool = False,
) -> List[Dict]:
    """
    Detect cross-references from a list of article dictionaries.

    Args:
        law_slug: The law's slug identifier
        articles: List of article dicts with 'article_id' and 'text' keys
        detector: Optional detector instance
        persist: If True, save detected references to the database

    Returns:
        List of reference dicts ready to be stored
    """
    if detector is None:
        detector = CrossReferenceDetector()

    slug_index = _build_law_slug_index()

    all_references = []

    for article in articles:
        article_id = article.get("article_id")
        text = article.get("text", "")

        if not article_id or not text:
            continue

        refs = detector.detect(text)

        for ref in refs:
            target_slug = detector.resolve_law_slug(ref.law_name, slug_index)

            ref_dict = {
                "source_law_slug": law_slug,
                "source_article_id": article_id,
                "target_law_slug": target_slug,
                "target_article_num": ref.article_num,
                "reference_text": ref.text,
                "fraction": ref.fraction,
                "confidence": ref.confidence,
                "start_position": ref.start_pos,
                "end_position": ref.end_pos,
            }
            all_references.append(ref_dict)

    if persist and all_references:
        _persist_references(law_slug, all_references)

    return all_references


def _persist_references(law_slug: str, ref_dicts: List[Dict]) -> int:
    """Save a list of reference dicts to the CrossReference model."""
    from apps.api.models import CrossReference

    # Clear old references for this law
    CrossReference.objects.filter(source_law_slug=law_slug).delete()

    objs = [CrossReference(**rd) for rd in ref_dicts]
    CrossReference.objects.bulk_create(objs, batch_size=500)
    logger.info(f"Persisted {len(objs)} cross-references for {law_slug}")
    return len(objs)
