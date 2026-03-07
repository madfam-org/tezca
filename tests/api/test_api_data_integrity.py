"""
API data integrity tests: UTF-8 preservation, response structure, special
characters, and search snippet handling.

All tests use mocked Elasticsearch to run without a live ES instance.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import Law, LawVersion


def _build_es_search_response(hits, total=None):
    """Build a realistic ES search response dict."""
    if total is None:
        total = len(hits)
    return {
        "hits": {
            "total": {"value": total},
            "hits": hits,
        },
    }


def _make_article_hit(law_id, article_id, text, highlight=None):
    """Build a single ES hit for the law_articles endpoint."""
    hit = {
        "_source": {
            "law_id": law_id,
            "article": article_id,
            "text": text,
        },
    }
    if highlight:
        hit["highlight"] = highlight
    return hit


def _make_search_hit(doc_id, law_id, text, score=5.0, highlight=None):
    """Build a single ES hit for the search endpoint."""
    source = {
        "law_id": law_id,
        "law_name": f"Ley {law_id}",
        "article": "1",
        "text": text,
        "publication_date": "2024-01-01",
        "tier": "federal",
        "law_type": None,
        "state": None,
        "municipality": None,
        "hierarchy": [],
        "book": None,
        "title": None,
        "chapter": None,
    }
    hit = {
        "_id": doc_id,
        "_score": score,
        "_source": source,
    }
    if highlight:
        hit["highlight"] = highlight
    else:
        hit["highlight"] = {"text": [text[:200]]}
    return hit


@pytest.mark.django_db
class TestApiDataIntegrity(TestCase):
    """Verify data integrity through API response layer."""

    def setUp(self):
        self.client = APIClient()
        self.uid = uuid.uuid4().hex[:8]

    # ------------------------------------------------------------------
    # 1. Search snippet preserves multibyte characters
    # ------------------------------------------------------------------

    @patch("apps.api.search_views.es_client")
    def test_search_snippet_preserves_multibyte(self, mock_es):
        """Search API must return valid UTF-8 snippets with accented chars."""
        mock_es.ping.return_value = True

        # Text with accented characters at position ~200 (near snippet boundary)
        accented_text = (
            "A" * 195 + "constitucion politica de los estados unidos mexicanos"
        )

        hit = _make_search_hit(
            doc_id="doc-utf8",
            law_id="cpeum-utf8",
            text=accented_text,
            highlight={"text": [accented_text[:200]]},
        )

        mock_es.search.return_value = {
            "hits": {"total": {"value": 1}, "hits": [hit]},
            "aggregations": {
                "by_tier": {"buckets": []},
                "by_category": {"buckets": []},
                "by_status": {"buckets": []},
                "by_law_type": {"buckets": []},
                "by_state": {"buckets": []},
            },
        }

        url = reverse("search")
        response = self.client.get(url, {"q": "constitucion"})

        assert response.status_code == 200
        snippet = response.json()["results"][0]["snippet"]

        # Verify the snippet is valid UTF-8 (no broken multibyte sequences)
        encoded = snippet.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert decoded == snippet, "Snippet round-trip through UTF-8 failed"

        # Verify accented characters survived
        assert "\ufffd" not in snippet, "Snippet contains U+FFFD replacement chars"

    # ------------------------------------------------------------------
    # 2. Law articles response structure
    # ------------------------------------------------------------------

    @patch("apps.api.law_views.es_client")
    def test_law_articles_response_structure(self, mock_es):
        """law_articles endpoint returns expected structure: total + articles list."""
        law = Law.objects.create(
            official_id=f"test-arts-struct-{self.uid}",
            name="Ley de Estructura",
            tier="federal",
        )
        LawVersion.objects.create(law=law, publication_date="2024-01-01")

        mock_es.count.return_value = {"count": 2}
        mock_es.search.return_value = _build_es_search_response(
            [
                _make_article_hit(law.official_id, "1", "Articulo primero."),
                _make_article_hit(law.official_id, "2", "Articulo segundo."),
            ]
        )

        url = reverse("law-articles", args=[law.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert "total" in data, "Response must include 'total' key"
        assert "articles" in data, "Response must include 'articles' key"
        assert data["total"] == 2
        assert len(data["articles"]) == 2
        assert data["articles"][0]["article_id"] == "1"

    # ------------------------------------------------------------------
    # 3. Long law name returned fully
    # ------------------------------------------------------------------

    def test_long_law_name_returned_fully(self):
        """Law detail endpoint must return a 499-char name without truncation."""
        long_name = "Ley " + "A" * 495  # 499 chars total
        law = Law.objects.create(
            official_id=f"test-longname-{self.uid}",
            name=long_name,
            tier="federal",
        )
        LawVersion.objects.create(law=law, publication_date="2024-06-01")

        url = reverse("law-detail", args=[law.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.json()["name"] == long_name
        assert len(response.json()["name"]) == 499

    # ------------------------------------------------------------------
    # 4. Special characters preserved in response
    # ------------------------------------------------------------------

    def test_special_chars_preserved_in_response(self):
        """Law detail must preserve special Unicode characters in names."""
        special_name = "Codigo Fiscal \u2014 \u00a72.1 (Regimen)"
        law = Law.objects.create(
            official_id=f"test-special-{self.uid}",
            name=special_name,
            tier="federal",
        )
        LawVersion.objects.create(law=law, publication_date="2024-03-15")

        url = reverse("law-detail", args=[law.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        returned_name = response.json()["name"]

        assert "\u2014" in returned_name, "Em dash was stripped from response"
        assert "\u00a7" in returned_name, "Section sign was stripped from response"
        assert returned_name == special_name

    # ------------------------------------------------------------------
    # 5. Zero-article law returns empty list
    # ------------------------------------------------------------------

    @patch("apps.api.law_views.es_client")
    def test_zero_article_law_returns_empty(self, mock_es):
        """A law with 0 ES articles returns total: 0 and empty articles list."""
        law = Law.objects.create(
            official_id=f"test-zero-art-{self.uid}",
            name="Ley Sin Articulos",
            tier="federal",
        )
        LawVersion.objects.create(law=law, publication_date="2024-01-01")

        mock_es.count.return_value = {"count": 0}
        mock_es.search.return_value = _build_es_search_response([], total=0)

        url = reverse("law-articles", args=[law.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["articles"] == []

    # ------------------------------------------------------------------
    # 6. Search <em> tags in snippet
    # ------------------------------------------------------------------

    @patch("apps.api.search_views.es_client")
    def test_search_em_tags_in_snippet(self, mock_es):
        """Search API must pass through ES highlight <em> tags in snippets."""
        mock_es.ping.return_value = True

        highlight_text = (
            "El juicio de <em>amparo</em> protege los derechos fundamentales"
        )
        hit = _make_search_hit(
            doc_id="doc-em",
            law_id="ley-amparo",
            text="El juicio de amparo protege los derechos fundamentales",
            highlight={"text": [highlight_text]},
        )

        mock_es.search.return_value = {
            "hits": {"total": {"value": 1}, "hits": [hit]},
            "aggregations": {
                "by_tier": {"buckets": []},
                "by_category": {"buckets": []},
                "by_status": {"buckets": []},
                "by_law_type": {"buckets": []},
                "by_state": {"buckets": []},
            },
        }

        url = reverse("search")
        response = self.client.get(url, {"q": "amparo"})

        assert response.status_code == 200
        snippet = response.json()["results"][0]["snippet"]

        assert (
            "<em>amparo</em>" in snippet
        ), f"Expected <em> highlight tags in snippet, got: {snippet!r}"
