"""Tests for cross-reference API endpoints."""

import uuid

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import CrossReference, Law


@pytest.mark.django_db
class TestArticleCrossReferences:
    """Tests for GET /laws/<law_id>/articles/<article_id>/references/"""

    def setup_method(self):
        self.client = APIClient()
        uid = uuid.uuid4().hex[:8]
        self.law = Law.objects.create(
            official_id=f"test-xref-{uid}",
            name=f"Ley de Pruebas {uid}",
            tier="federal",
            status="vigente",
        )
        self.other_law = Law.objects.create(
            official_id=f"test-xref-other-{uid}",
            name=f"Otra Ley {uid}",
            tier="federal",
            status="vigente",
        )
        # Outgoing reference: this law's article 1 → other law's article 5
        self.outgoing_ref = CrossReference.objects.create(
            source_law_slug=self.law.official_id,
            source_article_id="1",
            target_law_slug=self.other_law.official_id,
            target_article_num="5",
            reference_text="artículo 5 de la Otra Ley",
            confidence=0.95,
            start_position=10,
            end_position=40,
        )
        # Incoming reference: other law's article 3 → this law's article 1
        self.incoming_ref = CrossReference.objects.create(
            source_law_slug=self.other_law.official_id,
            source_article_id="3",
            target_law_slug=self.law.official_id,
            target_article_num="1",
            reference_text="artículo 1 de la Ley de Pruebas",
            confidence=0.88,
            start_position=5,
            end_position=35,
        )

    def test_happy_path_returns_outgoing_and_incoming(self):
        url = reverse(
            "article-references",
            args=[self.law.official_id, "1"],
        )
        resp = self.client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_outgoing"] == 1
        assert data["total_incoming"] == 1
        assert data["outgoing"][0]["targetArticle"] == "5"
        assert data["incoming"][0]["sourceArticle"] == "3"

    def test_outgoing_contains_target_url(self):
        url = reverse(
            "article-references",
            args=[self.law.official_id, "1"],
        )
        resp = self.client.get(url)
        data = resp.json()
        assert data["outgoing"][0]["targetUrl"] is not None
        assert self.other_law.official_id in data["outgoing"][0]["targetUrl"]

    def test_empty_results_for_unknown_article(self):
        url = reverse(
            "article-references",
            args=[self.law.official_id, "999"],
        )
        resp = self.client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_outgoing"] == 0
        assert data["total_incoming"] == 0

    def test_response_shape(self):
        url = reverse(
            "article-references",
            args=[self.law.official_id, "1"],
        )
        resp = self.client.get(url)
        data = resp.json()
        assert set(data.keys()) == {
            "outgoing",
            "incoming",
            "total_outgoing",
            "total_incoming",
        }
        out = data["outgoing"][0]
        assert "text" in out
        assert "confidence" in out
        assert "startPos" in out
        assert "endPos" in out

    def test_outgoing_without_target_slug_has_no_url(self):
        CrossReference.objects.create(
            source_law_slug=self.law.official_id,
            source_article_id="2",
            target_law_slug=None,
            target_article_num=None,
            reference_text="referencia genérica",
            confidence=0.5,
            start_position=0,
            end_position=20,
        )
        url = reverse(
            "article-references",
            args=[self.law.official_id, "2"],
        )
        resp = self.client.get(url)
        data = resp.json()
        assert data["outgoing"][0]["targetUrl"] is None

    def test_incoming_has_source_url(self):
        url = reverse(
            "article-references",
            args=[self.law.official_id, "1"],
        )
        resp = self.client.get(url)
        data = resp.json()
        assert "sourceUrl" in data["incoming"][0]
        assert self.other_law.official_id in data["incoming"][0]["sourceUrl"]

    def test_outgoing_ordered_by_start_position(self):
        CrossReference.objects.create(
            source_law_slug=self.law.official_id,
            source_article_id="1",
            target_law_slug=self.other_law.official_id,
            target_article_num="10",
            reference_text="artículo 10",
            confidence=0.8,
            start_position=5,
            end_position=15,
        )
        url = reverse(
            "article-references",
            args=[self.law.official_id, "1"],
        )
        resp = self.client.get(url)
        data = resp.json()
        positions = [r["startPos"] for r in data["outgoing"]]
        assert positions == sorted(positions)


@pytest.mark.django_db
class TestLawCrossReferences:
    """Tests for GET /laws/<law_id>/references/"""

    def setup_method(self):
        self.client = APIClient()
        uid = uuid.uuid4().hex[:8]
        self.law = Law.objects.create(
            official_id=f"test-lawxref-{uid}",
            name=f"Ley Refs {uid}",
            tier="federal",
            status="vigente",
        )
        self.target_law = Law.objects.create(
            official_id=f"test-target-{uid}",
            name=f"Ley Destino {uid}",
            tier="federal",
            status="vigente",
        )
        # Create outgoing refs
        for i in range(3):
            CrossReference.objects.create(
                source_law_slug=self.law.official_id,
                source_article_id=str(i + 1),
                target_law_slug=self.target_law.official_id,
                target_article_num=str(i + 10),
                reference_text=f"ref {i}",
                confidence=0.9,
                start_position=i * 10,
                end_position=i * 10 + 8,
            )
        # Create incoming ref
        CrossReference.objects.create(
            source_law_slug=self.target_law.official_id,
            source_article_id="5",
            target_law_slug=self.law.official_id,
            target_article_num="1",
            reference_text="ref back",
            confidence=0.85,
            start_position=0,
            end_position=10,
        )

    def test_aggregated_stats(self):
        url = reverse("law-references", args=[self.law.official_id])
        resp = self.client.get(url)
        assert resp.status_code == 200
        stats = resp.json()["statistics"]
        assert stats["total_outgoing"] == 3
        assert stats["total_incoming"] == 1

    def test_most_referenced_laws_ordering(self):
        url = reverse("law-references", args=[self.law.official_id])
        resp = self.client.get(url)
        stats = resp.json()["statistics"]
        assert len(stats["most_referenced_laws"]) == 1
        assert stats["most_referenced_laws"][0]["slug"] == self.target_law.official_id
        assert stats["most_referenced_laws"][0]["count"] == 3

    def test_null_target_slug_filtered(self):
        CrossReference.objects.create(
            source_law_slug=self.law.official_id,
            source_article_id="99",
            target_law_slug=None,
            target_article_num=None,
            reference_text="vague ref",
            confidence=0.3,
            start_position=0,
            end_position=10,
        )
        url = reverse("law-references", args=[self.law.official_id])
        resp = self.client.get(url)
        stats = resp.json()["statistics"]
        # The null-slug ref should not appear in most_referenced_laws
        for entry in stats["most_referenced_laws"]:
            assert entry["slug"] is not None

    def test_empty_law(self):
        uid = uuid.uuid4().hex[:8]
        empty_law = Law.objects.create(
            official_id=f"test-empty-{uid}",
            name="Empty Law",
            tier="federal",
            status="vigente",
        )
        url = reverse("law-references", args=[empty_law.official_id])
        resp = self.client.get(url)
        assert resp.status_code == 200
        stats = resp.json()["statistics"]
        assert stats["total_outgoing"] == 0
        assert stats["total_incoming"] == 0

    def test_response_shape(self):
        url = reverse("law-references", args=[self.law.official_id])
        resp = self.client.get(url)
        data = resp.json()
        assert "statistics" in data
        stats = data["statistics"]
        assert set(stats.keys()) == {
            "total_outgoing",
            "total_incoming",
            "most_referenced_laws",
            "most_citing_laws",
        }
