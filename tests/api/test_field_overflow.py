"""
Spot-check tests for model field length constraints.

These tests document the behavior of CharField max_length enforcement
across database backends. SQLite silently accepts over-length strings,
while PostgreSQL raises DataError. Both behaviors are tested here to
surface data integrity risks during development.
"""

import uuid

import pytest
from django.db import connection
from django.test import TestCase

from apps.api.models import CrossReference, Law


@pytest.mark.spotcheck
class TestFieldOverflow(TestCase):
    """Verify field length constraints on Law and CrossReference models."""

    def _unique_id(self, prefix: str = "overflow") -> str:
        return f"{prefix}-{uuid.uuid4().hex[:8]}"

    def test_law_name_at_max_length(self):
        """A Law with exactly 500-char name saves and retrieves correctly."""
        name_500 = "A" * 500
        official_id = self._unique_id()

        law = Law.objects.create(
            official_id=official_id,
            name=name_500,
            tier="federal",
            status="vigente",
        )

        law.refresh_from_db()
        assert law.name == name_500
        assert len(law.name) == 500

    def test_law_name_over_max_length(self):
        """
        A Law with 501-char name: Postgres raises DataError, SQLite allows it.

        This documents a data integrity risk when running on SQLite -- the
        max_length constraint is only enforced at the Django form/serializer
        layer, not at the database level. Production must use Postgres.
        """
        name_501 = "B" * 501
        official_id = self._unique_id()

        law = Law(
            official_id=official_id,
            name=name_501,
            tier="federal",
            status="vigente",
        )

        if connection.vendor == "sqlite":
            # SQLite silently accepts over-length strings.
            # This is a known data integrity risk -- max_length is only
            # enforced by Django forms/serializers, not by the DB engine.
            law.save()
            law.refresh_from_db()
            assert (
                len(law.name) == 501
            ), "SQLite does not enforce CharField max_length at the DB level"
        else:
            # PostgreSQL enforces varchar(500) and raises DataError.
            with self.assertRaises(Exception):
                law.save()

    def test_crossreference_target_article_at_and_over_max(self):
        """
        CrossReference.target_article_num at 100 chars saves fine.
        At 101 chars, SQLite allows it; Postgres would reject it.
        """
        uid = self._unique_id("xref")

        # -- At max length (100 chars) --
        xref = CrossReference.objects.create(
            source_law_slug=f"source-{uid}",
            source_article_id="1",
            target_law_slug=f"target-{uid}",
            target_article_num="C" * 100,
            reference_text="articulo 100-char test",
            confidence=0.90,
            start_position=0,
            end_position=50,
        )
        xref.refresh_from_db()
        assert len(xref.target_article_num) == 100

        # -- Over max length (101 chars) --
        over_xref = CrossReference(
            source_law_slug=f"source-over-{uid}",
            source_article_id="2",
            target_law_slug=f"target-over-{uid}",
            target_article_num="D" * 101,
            reference_text="articulo 101-char test",
            confidence=0.85,
            start_position=0,
            end_position=50,
        )

        if connection.vendor == "sqlite":
            over_xref.save()
            over_xref.refresh_from_db()
            assert (
                len(over_xref.target_article_num) == 101
            ), "SQLite does not enforce CharField max_length at the DB level"
        else:
            with self.assertRaises(Exception):
                over_xref.save()
