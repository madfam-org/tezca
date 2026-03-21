"""
Tests for search relevance tuning: field boosting, vigente status boost, highlighting.

Covers:
  - law_name field boosting is applied in multi_match query
  - vigente status boost is present as a should clause
  - Highlighting includes both text and law_name fields
  - law_name.keyword exact match boost is configured
"""

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


def _build_es_response(hits, total=None, aggregations=None):
    """Helper to build a realistic ES search response."""
    if total is None:
        total = len(hits)
    response = {
        "hits": {
            "total": {"value": total},
            "hits": hits,
        },
    }
    if aggregations is None:
        aggregations = {
            "by_tier": {"buckets": []},
            "by_category": {"buckets": []},
            "by_status": {"buckets": []},
            "by_law_type": {"buckets": []},
            "by_state": {"buckets": []},
        }
    response["aggregations"] = aggregations
    return response


def _make_hit(doc_id, law_id, law_name, article, text, score=5.0, status="vigente"):
    """Helper to build a single ES hit document."""
    return {
        "_id": doc_id,
        "_score": score,
        "_source": {
            "law_id": law_id,
            "law_name": law_name,
            "article": article,
            "text": text,
            "publication_date": "2024-01-01",
            "tier": "federal",
            "law_type": "legislative",
            "state": None,
            "municipality": None,
            "hierarchy": [],
            "book": None,
            "title": None,
            "chapter": None,
            "status": status,
        },
        "highlight": {"text": [f"<em>{text[:50]}</em>"]},
    }


def _extract_es_kwargs(mock_search):
    """Extract ES search kwargs from mock call."""
    kwargs = mock_search.call_args[1]
    body = {}
    for key in ("query", "from_", "size", "aggs", "sort", "highlight"):
        if key in kwargs:
            body[key] = kwargs[key]
    return body


def _unwrap_bool_query(body):
    """Unwrap bool query from a function_score wrapper if present."""
    query = body["query"]
    if "function_score" in query:
        return query["function_score"]["query"]["bool"]
    return query["bool"]


@pytest.mark.django_db
class TestSearchRelevanceBoosting:
    """Verify field boosting configuration in ES queries."""

    def setup_method(self):
        self.client = APIClient()

    @patch("apps.api.search_views.es_client")
    def test_law_name_boosted_in_multi_match(self, mock_es):
        """multi_match query should include law_name with boost."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([], total=0)

        url = reverse("search")
        self.client.get(url, {"q": "ley de amparo"})

        body = _extract_es_kwargs(mock_es.search)
        bool_query = _unwrap_bool_query(body)
        multi_match = bool_query["must"][0]["multi_match"]

        # Verify boosted fields are present
        fields = multi_match["fields"]
        assert "law_name^3" in fields
        assert "law_name.keyword^5" in fields
        assert "text^1" in fields
        assert "tags^0.5" in fields

    @patch("apps.api.search_views.es_client")
    def test_vigente_status_boost_in_should(self, mock_es):
        """Query should include a should clause boosting vigente status."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([], total=0)

        url = reverse("search")
        self.client.get(url, {"q": "impuestos"})

        body = _extract_es_kwargs(mock_es.search)
        bool_query = _unwrap_bool_query(body)
        should = bool_query["should"]

        # Find the vigente boost clause
        vigente_clauses = [
            c
            for c in should
            if c.get("term", {}).get("status", {}).get("value") == "vigente"
        ]
        assert len(vigente_clauses) == 1
        assert vigente_clauses[0]["term"]["status"]["boost"] == 1.5

    @patch("apps.api.search_views.es_client")
    def test_highlight_includes_law_name(self, mock_es):
        """Highlight config should include both text and law_name fields."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([], total=0)

        url = reverse("search")
        self.client.get(url, {"q": "constitución"})

        body = _extract_es_kwargs(mock_es.search)
        highlight = body["highlight"]
        fields = highlight["fields"]

        assert "text" in fields
        assert "law_name" in fields
        assert fields["text"]["fragment_size"] == 200
        assert fields["text"]["number_of_fragments"] == 2

    @patch("apps.api.search_views.es_client")
    def test_vigente_law_ranks_above_abrogado(self, mock_es):
        """When ES returns vigente law with higher score, it appears first."""
        mock_es.ping.return_value = True

        hits = [
            _make_hit(
                "doc-1",
                "fed_ley_amparo",
                "Ley de Amparo",
                "1",
                "Artículo sobre amparo vigente.",
                score=12.0,
                status="vigente",
            ),
            _make_hit(
                "doc-2",
                "fed_ley_amparo_old",
                "Ley de Amparo (Abrogada)",
                "1",
                "Artículo sobre amparo abrogado.",
                score=8.0,
                status="abrogado",
            ),
        ]
        mock_es.search.return_value = _build_es_response(hits, total=2)

        url = reverse("search")
        response = self.client.get(url, {"q": "ley de amparo"})

        data = response.json()
        assert data["total"] == 2
        results = data["results"]
        assert results[0]["score"] > results[1]["score"]
        assert results[0]["law_id"] == "fed_ley_amparo"

    @patch("apps.api.search_views.es_client")
    def test_law_name_match_returns_in_top_results(self, mock_es):
        """A law whose name exactly matches the query should appear in results."""
        mock_es.ping.return_value = True

        hits = [
            _make_hit(
                "doc-1",
                "fed_ley_amparo",
                "Ley de Amparo, Reglamentaria de los artículos 103 y 107",
                "1",
                "El juicio de amparo tiene por objeto resolver...",
                score=15.0,
            ),
            _make_hit(
                "doc-2",
                "fed_cpeum",
                "Constitución Política de los Estados Unidos Mexicanos",
                "103",
                "Los Tribunales de la Federación resolverán...",
                score=9.0,
            ),
        ]
        mock_es.search.return_value = _build_es_response(hits, total=2)

        url = reverse("search")
        response = self.client.get(url, {"q": "ley de amparo"})

        data = response.json()
        # The Ley de Amparo should be the top result (exact name match boosted)
        assert data["results"][0]["law_name"].startswith("Ley de Amparo")


@pytest.mark.django_db
class TestFunctionScoreAndPhraseBoost:
    """Verify function_score recency wrapper and phrase matching."""

    def setup_method(self):
        self.client = APIClient()

    @patch("apps.api.search_views.es_client")
    def test_function_score_wraps_query(self, mock_es):
        """Relevance sort wraps query in function_score with gauss decay."""
        mock_es.ping.return_value = True
        # Return at least 1 hit so zero-result rescue doesn't overwrite the query
        hits = [_make_hit("doc-1", "cpeum", "Ley de Amparo", "1", "Art.", score=5.0)]
        mock_es.search.return_value = _build_es_response(hits, total=1)

        url = reverse("search")
        self.client.get(url, {"q": "amparo"})

        body = _extract_es_kwargs(mock_es.search)
        query = body["query"]
        assert "function_score" in query
        fs = query["function_score"]
        assert "gauss" in fs["functions"][0]
        assert "publication_date" in fs["functions"][0]["gauss"]
        assert fs["boost_mode"] == "multiply"

    @patch("apps.api.search_views.es_client")
    def test_no_function_score_on_date_sort(self, mock_es):
        """Date sort should NOT wrap query in function_score."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([], total=0)

        url = reverse("search")
        self.client.get(url, {"q": "amparo", "sort": "date_desc"})

        body = _extract_es_kwargs(mock_es.search)
        query = body["query"]
        assert "function_score" not in query
        assert "bool" in query

    @patch("apps.api.search_views.es_client")
    def test_phrase_boost_in_should(self, mock_es):
        """Should clauses include match_phrase for text and law_name."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([], total=0)

        url = reverse("search")
        self.client.get(url, {"q": "codigo penal"})

        body = _extract_es_kwargs(mock_es.search)
        bool_query = _unwrap_bool_query(body)
        should = bool_query["should"]

        phrase_text = [
            c for c in should if "match_phrase" in c and "text" in c["match_phrase"]
        ]
        phrase_name = [
            c for c in should if "match_phrase" in c and "law_name" in c["match_phrase"]
        ]
        assert len(phrase_text) == 1
        assert phrase_text[0]["match_phrase"]["text"]["boost"] == 3.0
        assert len(phrase_name) == 1
        assert phrase_name[0]["match_phrase"]["law_name"]["boost"] == 5.0
