"""
Spot-check tests for CrossReference slug integrity.

CrossReference records use source_law_slug and target_law_slug as plain
CharField values without a ForeignKey constraint to Law.official_id.
This means orphaned references can accumulate silently. These tests
document the integrity gap and verify detection of orphans.
"""

import uuid

import pytest
from django.test import TestCase

from apps.api.models import CrossReference, Law


def _uid(prefix: str = "slug") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _make_xref(source_slug: str, target_slug: str, **kwargs) -> CrossReference:
    """Create a CrossReference with sensible defaults."""
    defaults = {
        "source_law_slug": source_slug,
        "source_article_id": kwargs.pop("source_article_id", "1"),
        "target_law_slug": target_slug,
        "target_article_num": kwargs.pop("target_article_num", "5"),
        "reference_text": kwargs.pop("reference_text", f"referencia a {target_slug}"),
        "confidence": kwargs.pop("confidence", 0.90),
        "start_position": kwargs.pop("start_position", 0),
        "end_position": kwargs.pop("end_position", 40),
    }
    defaults.update(kwargs)
    return CrossReference.objects.create(**defaults)


@pytest.mark.spotcheck
class TestXrefSlugIntegrity(TestCase):
    """Verify referential integrity between CrossReference slugs and Law records."""

    def setUp(self):
        self.law_a = Law.objects.create(
            official_id=_uid("law-a"),
            name="Ley A de Pruebas",
            tier="federal",
            status="vigente",
        )
        self.law_b = Law.objects.create(
            official_id=_uid("law-b"),
            name="Ley B de Pruebas",
            tier="federal",
            status="vigente",
        )

    def test_target_slugs_exist_in_law_table(self):
        """
        All target_law_slug values in CrossReference should correspond to
        a Law.official_id. This test creates valid references and confirms
        zero orphans.
        """
        _make_xref(self.law_a.official_id, self.law_b.official_id)
        _make_xref(
            self.law_b.official_id,
            self.law_a.official_id,
            source_article_id="3",
            target_article_num="10",
        )

        all_law_ids = set(Law.objects.values_list("official_id", flat=True))
        target_slugs = set(
            CrossReference.objects.values_list("target_law_slug", flat=True)
        )
        # Exclude None/blank targets (general references without a specific law)
        target_slugs.discard(None)
        target_slugs.discard("")

        orphaned = target_slugs - all_law_ids
        assert orphaned == set(), f"Orphaned target_law_slug values found: {orphaned}"

    def test_source_slugs_exist_in_law_table(self):
        """
        All source_law_slug values in CrossReference should correspond to
        a Law.official_id. This test creates valid references and confirms
        zero orphans.
        """
        _make_xref(self.law_a.official_id, self.law_b.official_id)

        all_law_ids = set(Law.objects.values_list("official_id", flat=True))
        source_slugs = set(
            CrossReference.objects.values_list("source_law_slug", flat=True)
        )
        source_slugs.discard(None)
        source_slugs.discard("")

        orphaned = source_slugs - all_law_ids
        assert orphaned == set(), f"Orphaned source_law_slug values found: {orphaned}"

    def test_orphaned_reference_count(self):
        """
        CrossReferences with target_law_slug pointing to non-existent Laws
        are orphans. This documents the data integrity gap caused by the
        lack of a ForeignKey constraint between CrossReference and Law.
        """
        ghost_slug = _uid("ghost-law")

        # Valid reference
        _make_xref(self.law_a.official_id, self.law_b.official_id)

        # Orphaned references -- target_law_slug does not exist in Law table
        _make_xref(
            self.law_a.official_id,
            ghost_slug,
            source_article_id="7",
            target_article_num="12",
            reference_text=f"referencia fantasma a {ghost_slug}",
        )
        _make_xref(
            self.law_b.official_id,
            ghost_slug,
            source_article_id="2",
            target_article_num="3",
            reference_text=f"otra referencia fantasma a {ghost_slug}",
        )

        all_law_ids = set(Law.objects.values_list("official_id", flat=True))
        target_slugs = (
            CrossReference.objects.exclude(target_law_slug__isnull=True)
            .exclude(target_law_slug="")
            .values_list("target_law_slug", flat=True)
        )

        orphan_count = sum(1 for slug in target_slugs if slug not in all_law_ids)

        assert orphan_count == 2, (
            f"Expected 2 orphaned cross-references, got {orphan_count}. "
            "CrossReference.target_law_slug lacks a FK constraint to "
            "Law.official_id, allowing dangling references."
        )
