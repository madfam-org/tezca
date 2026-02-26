"""
Tests for SearchView: query handling, filters, facets, pagination.

Covers:
  - Search with query returns results
  - Search with filters (tier, state, category, law_type, status)
  - Empty query returns empty results
  - Faceted search returns facet counts
  - Pagination works correctly
  - ES offline returns 503
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


def _extract_es_kwargs(mock_search):
    """Extract ES search kwargs, handling both body-based (ES 7) and keyword-based (ES 8) calls."""
    kwargs = mock_search.call_args[1]
    if "body" in kwargs:
        return kwargs["body"]
    # ES 8 keyword args: reconstruct a body-like dict
    body = {}
    if "query" in kwargs:
        body["query"] = kwargs["query"]
    if "from_" in kwargs:
        body["from"] = kwargs["from_"]
    elif "from" in kwargs:
        body["from"] = kwargs["from"]
    if "size" in kwargs:
        body["size"] = kwargs["size"]
    if "aggs" in kwargs:
        body["aggs"] = kwargs["aggs"]
    if "sort" in kwargs:
        body["sort"] = kwargs["sort"]
    return body


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
    if aggregations is not None:
        response["aggregations"] = aggregations
    return response


def _make_hit(
    doc_id,
    law_id,
    article,
    text,
    score=5.0,
    tier="federal",
    law_type=None,
    state=None,
    category=None,
    status=None,
    highlight=None,
):
    """Helper to build a single ES hit document."""
    source = {
        "law_id": law_id,
        "law_name": f"Ley {law_id}",
        "article": article,
        "text": text,
        "publication_date": "2024-01-01",
        "tier": tier,
        "law_type": law_type,
        "state": state,
        "municipality": None,
        "hierarchy": [],
        "book": None,
        "title": None,
        "chapter": None,
    }
    if category:
        source["category"] = category
    if status:
        source["status"] = status

    hit = {
        "_id": doc_id,
        "_score": score,
        "_source": source,
    }
    if highlight:
        hit["highlight"] = highlight
    else:
        hit["highlight"] = {"text": [f"<em>{text[:30]}</em>"]}
    return hit


@pytest.mark.django_db
class TestSearchViewBasic:
    """Basic search query and empty query tests."""

    def setup_method(self):
        self.client = APIClient()

    def test_empty_query_returns_empty_results(self):
        """GET /search/ with no q param returns empty results (not an error)."""
        url = reverse("search")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["total"] == 0

    def test_empty_string_query_returns_empty(self):
        """GET /search/?q= (empty string) returns empty results."""
        url = reverse("search")
        response = self.client.get(url, {"q": ""})

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["total"] == 0

    @patch("apps.api.search_views.es_client")
    def test_search_with_query_returns_results(self, mock_es):
        """Search with a valid query returns formatted results."""
        mock_es.ping.return_value = True
        hits = [
            _make_hit(
                "doc-1", "cpeum", "1", "Articulo sobre derechos humanos.", score=8.5
            ),
            _make_hit("doc-2", "cpeum", "2", "Articulo sobre garantias.", score=6.2),
        ]
        mock_es.search.return_value = _build_es_response(
            hits,
            total=2,
            aggregations={
                "by_tier": {"buckets": [{"key": "federal", "doc_count": 2}]},
                "by_category": {"buckets": []},
                "by_status": {"buckets": []},
                "by_law_type": {"buckets": []},
                "by_state": {"buckets": []},
            },
        )

        url = reverse("search")
        response = self.client.get(url, {"q": "derechos"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["results"]) == 2

        first = data["results"][0]
        assert first["id"] == "doc-1"
        assert first["law_id"] == "cpeum"
        assert first["article"] == "Art. 1"
        assert "snippet" in first
        assert first["score"] == 8.5

    @patch("apps.api.search_views.es_client")
    def test_search_es_offline_returns_503(self, mock_es):
        """When ES ping fails, returns 503."""
        mock_es.ping.return_value = False

        url = reverse("search")
        response = self.client.get(url, {"q": "derechos"})

        assert response.status_code == 503
        data = response.json()
        assert "offline" in data.get("warning", "").lower()


@pytest.mark.django_db
class TestSearchViewFilters:
    """Search filter tests: tier/jurisdiction, state, category, law_type, status."""

    def setup_method(self):
        self.client = APIClient()

    @patch("apps.api.search_views.es_client")
    def test_filter_by_jurisdiction(self, mock_es):
        """Passing jurisdiction=federal adds tier filter to ES query."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response(
            [],
            total=0,
            aggregations={
                "by_tier": {"buckets": []},
                "by_category": {"buckets": []},
                "by_status": {"buckets": []},
                "by_law_type": {"buckets": []},
                "by_state": {"buckets": []},
            },
        )

        url = reverse("search")
        self.client.get(url, {"q": "test", "jurisdiction": "federal"})

        body = _extract_es_kwargs(mock_es.search)
        query_str = str(body)
        assert "federal" in query_str

    @patch("apps.api.search_views.es_client")
    def test_filter_by_state(self, mock_es):
        """Passing state=colima adds prefix filter on law_id."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response(
            [],
            total=0,
            aggregations={
                "by_tier": {"buckets": []},
                "by_category": {"buckets": []},
                "by_status": {"buckets": []},
                "by_law_type": {"buckets": []},
                "by_state": {"buckets": []},
            },
        )

        url = reverse("search")
        self.client.get(url, {"q": "civil", "state": "Colima"})

        body = _extract_es_kwargs(mock_es.search)
        query_str = str(body)
        assert "colima_" in query_str

    @patch("apps.api.search_views.es_client")
    def test_filter_by_category(self, mock_es):
        """Passing category=ley adds term filter."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response(
            [],
            total=0,
            aggregations={
                "by_tier": {"buckets": []},
                "by_category": {"buckets": []},
                "by_status": {"buckets": []},
                "by_law_type": {"buckets": []},
                "by_state": {"buckets": []},
            },
        )

        url = reverse("search")
        self.client.get(url, {"q": "prueba", "category": "ley"})

        body = _extract_es_kwargs(mock_es.search)
        filters = body["query"]["bool"].get("filter", [])
        assert any(f.get("term", {}).get("category") == "ley" for f in filters)

    @patch("apps.api.search_views.es_client")
    def test_filter_by_law_type(self, mock_es):
        """Passing law_type=legislative adds term filter."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response(
            [],
            total=0,
            aggregations={
                "by_tier": {"buckets": []},
                "by_category": {"buckets": []},
                "by_status": {"buckets": []},
                "by_law_type": {"buckets": []},
                "by_state": {"buckets": []},
            },
        )

        url = reverse("search")
        self.client.get(url, {"q": "prueba", "law_type": "legislative"})

        body = _extract_es_kwargs(mock_es.search)
        filters = body["query"]["bool"].get("filter", [])
        assert any(f.get("term", {}).get("law_type") == "legislative" for f in filters)

    @patch("apps.api.search_views.es_client")
    def test_filter_by_status(self, mock_es):
        """Passing status=vigente adds term filter."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response(
            [],
            total=0,
            aggregations={
                "by_tier": {"buckets": []},
                "by_category": {"buckets": []},
                "by_status": {"buckets": []},
                "by_law_type": {"buckets": []},
                "by_state": {"buckets": []},
            },
        )

        url = reverse("search")
        self.client.get(url, {"q": "prueba", "status": "vigente"})

        body = _extract_es_kwargs(mock_es.search)
        filters = body["query"]["bool"].get("filter", [])
        assert any(f.get("term", {}).get("status") == "vigente" for f in filters)


@pytest.mark.django_db
class TestSearchViewFacets:
    """Faceted search returns aggregation buckets."""

    def setup_method(self):
        self.client = APIClient()

    @patch("apps.api.search_views.es_client")
    def test_facets_returned_in_response(self, mock_es):
        """Search response includes facets from ES aggregations."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response(
            hits=[
                _make_hit("doc-1", "cpeum", "1", "Articulo uno.", score=5.0),
            ],
            total=1,
            aggregations={
                "by_tier": {
                    "buckets": [
                        {"key": "federal", "doc_count": 100},
                        {"key": "state", "doc_count": 50},
                    ]
                },
                "by_category": {
                    "buckets": [
                        {"key": "ley", "doc_count": 80},
                        {"key": "codigo", "doc_count": 70},
                    ]
                },
                "by_status": {
                    "buckets": [
                        {"key": "vigente", "doc_count": 120},
                        {"key": "abrogada", "doc_count": 30},
                    ]
                },
                "by_law_type": {
                    "buckets": [
                        {"key": "legislative", "doc_count": 110},
                    ]
                },
                "by_state": {
                    "buckets": [
                        {"key": "Jalisco", "doc_count": 25},
                        {"key": "Colima", "doc_count": 15},
                    ]
                },
            },
        )

        url = reverse("search")
        response = self.client.get(url, {"q": "articulo"})

        assert response.status_code == 200
        data = response.json()

        assert "facets" in data
        facets = data["facets"]

        # Verify by_tier facet
        assert "by_tier" in facets
        tier_keys = [b["key"] for b in facets["by_tier"]]
        assert "federal" in tier_keys
        assert "state" in tier_keys

        # Verify by_category facet
        assert "by_category" in facets
        cat_keys = [b["key"] for b in facets["by_category"]]
        assert "ley" in cat_keys

        # Verify by_status facet
        assert "by_status" in facets

        # Verify by_state facet
        assert "by_state" in facets
        state_keys = [b["key"] for b in facets["by_state"]]
        assert "Jalisco" in state_keys


@pytest.mark.django_db
class TestSearchViewPagination:
    """Pagination via page and page_size parameters."""

    def setup_method(self):
        self.client = APIClient()

    @patch("apps.api.search_views.es_client")
    def test_default_pagination(self, mock_es):
        """Default page=1, page_size=10 are applied."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response(
            hits=[
                _make_hit(f"doc-{i}", "cpeum", str(i), f"Art {i}.") for i in range(10)
            ],
            total=25,
            aggregations={
                "by_tier": {"buckets": []},
                "by_category": {"buckets": []},
                "by_status": {"buckets": []},
                "by_law_type": {"buckets": []},
                "by_state": {"buckets": []},
            },
        )

        url = reverse("search")
        response = self.client.get(url, {"q": "articulo"})

        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total"] == 25
        assert data["total_pages"] == 3  # ceil(25/10)

    @patch("apps.api.search_views.es_client")
    def test_custom_page_and_size(self, mock_es):
        """Custom page and page_size are respected."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response(
            hits=[_make_hit("doc-1", "cpeum", "21", "Art 21.")],
            total=50,
            aggregations={
                "by_tier": {"buckets": []},
                "by_category": {"buckets": []},
                "by_status": {"buckets": []},
                "by_law_type": {"buckets": []},
                "by_state": {"buckets": []},
            },
        )

        url = reverse("search")
        response = self.client.get(
            url, {"q": "articulo", "page": "3", "page_size": "20"}
        )

        data = response.json()
        assert data["page"] == 3
        assert data["page_size"] == 20
        assert data["total_pages"] == 3  # ceil(50/20)

        # Verify ES was called with correct offset
        body = _extract_es_kwargs(mock_es.search)
        assert body["from"] == 40  # (3-1) * 20
        assert body["size"] == 20

    @patch("apps.api.search_views.es_client")
    def test_page_size_capped_at_100(self, mock_es):
        """page_size > 100 is capped at 100."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response(
            hits=[],
            total=0,
            aggregations={
                "by_tier": {"buckets": []},
                "by_category": {"buckets": []},
                "by_status": {"buckets": []},
                "by_law_type": {"buckets": []},
                "by_state": {"buckets": []},
            },
        )

        url = reverse("search")
        response = self.client.get(url, {"q": "test", "page_size": "500"})

        data = response.json()
        assert data["page_size"] == 100

    @patch("apps.api.search_views.es_client")
    def test_negative_page_defaults_to_1(self, mock_es):
        """Negative page number defaults to page 1."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response(
            hits=[],
            total=0,
            aggregations={
                "by_tier": {"buckets": []},
                "by_category": {"buckets": []},
                "by_status": {"buckets": []},
                "by_law_type": {"buckets": []},
                "by_state": {"buckets": []},
            },
        )

        url = reverse("search")
        response = self.client.get(url, {"q": "test", "page": "-1"})

        data = response.json()
        assert data["page"] == 1
