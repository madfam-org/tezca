"""Tests for law_views.py — comprehensive coverage of all law-related endpoints.

Targets: LawListView filtering, categories_list, law_search, law_articles edge cases,
law_structure ES errors, states_list, municipalities_list, suggest with ES,
RelatedLawsView, law_stats, and _natural_sort_key / _safe_pct helpers.
"""

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from elasticsearch.exceptions import ConnectionError as ESConnectionError
from elasticsearch.exceptions import ConnectionTimeout
from rest_framework.test import APIClient

from apps.api.models import CrossReference, Law, LawVersion

# ---------------------------------------------------------------------------
# Helper factory
# ---------------------------------------------------------------------------


def _uid():
    return uuid.uuid4().hex[:8]


def _create_law(
    official_id=None,
    name="Test Law",
    tier="federal",
    category="ley",
    status="vigente",
    law_type="legislative",
    state=None,
    municipality=None,
    short_name=None,
):
    return Law.objects.create(
        official_id=official_id or f"law_{_uid()}",
        name=name,
        tier=tier,
        category=category,
        status=status,
        law_type=law_type,
        state=state,
        municipality=municipality,
        short_name=short_name,
    )


# ---------------------------------------------------------------------------
# _natural_sort_key and _safe_pct
# ---------------------------------------------------------------------------


class TestHelpers:
    """Unit tests for module-level helper functions."""

    def test_natural_sort_key_numbers(self):
        from apps.api.law_views import _natural_sort_key

        items = ["Art. 10", "Art. 2", "Art. 1"]
        sorted_items = sorted(items, key=_natural_sort_key)
        assert sorted_items == ["Art. 1", "Art. 2", "Art. 10"]

    def test_natural_sort_key_empty(self):
        from apps.api.law_views import _natural_sort_key

        assert _natural_sort_key("") == [""]
        assert _natural_sort_key(None) == [""]

    def test_safe_pct_normal(self):
        from apps.api.law_views import _safe_pct

        assert _safe_pct(50, 100) == 50.0

    def test_safe_pct_capped_at_100(self):
        from apps.api.law_views import _safe_pct

        assert _safe_pct(200, 100) == 100.0

    def test_safe_pct_zero_universe(self):
        from apps.api.law_views import _safe_pct

        assert _safe_pct(50, 0) is None

    def test_safe_pct_none_universe(self):
        from apps.api.law_views import _safe_pct

        assert _safe_pct(50, None) is None


# ---------------------------------------------------------------------------
# LawListView — filtering, sorting, pagination
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLawListFiltering:
    """Tests for GET /laws/ with various filter parameters."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("law-list")

        # Create diverse laws
        self.fed_law = _create_law(
            official_id=f"fed_{_uid()}",
            name="Ley Federal de X",
            tier="federal",
            category="ley",
            status="vigente",
            law_type="legislative",
        )
        self.state_law = _create_law(
            official_id=f"jal_{_uid()}",
            name="Codigo Civil de Jalisco",
            tier="state",
            category="codigo",
            status="vigente",
            law_type="legislative",
            state="Jalisco",
        )
        self.muni_law = _create_law(
            official_id=f"muni_{_uid()}",
            name="Reglamento de Guadalajara",
            tier="municipal",
            category="reglamento",
            status="vigente",
            law_type="non_legislative",
            state="Jalisco",
            municipality="Guadalajara",
        )
        self.abrogada = _create_law(
            official_id=f"abrog_{_uid()}",
            name="Ley Abrogada",
            tier="federal",
            category="ley",
            status="abrogada",
        )

        # Add versions for sort-by-date tests
        LawVersion.objects.create(law=self.fed_law, publication_date=date(2025, 1, 1))
        LawVersion.objects.create(
            law=self.state_law, publication_date=date(2024, 6, 15)
        )

    def test_list_all_laws(self):
        response = self.client.get(self.url)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 4

    def test_filter_by_tier(self):
        response = self.client.get(self.url, {"tier": "federal"})
        assert response.status_code == 200
        for item in response.json()["results"]:
            assert item["tier"] == "federal"

    def test_filter_by_state(self):
        response = self.client.get(self.url, {"state": "Jalisco"})
        assert response.status_code == 200
        # Both state and municipal laws have state=Jalisco
        assert response.json()["count"] >= 1

    def test_filter_by_category(self):
        response = self.client.get(self.url, {"category": "codigo"})
        assert response.status_code == 200
        for item in response.json()["results"]:
            assert item["category"] == "codigo"

    def test_filter_by_comma_separated_categories(self):
        response = self.client.get(self.url, {"category": "ley,codigo"})
        assert response.status_code == 200
        for item in response.json()["results"]:
            assert item["category"] in ("ley", "codigo")

    def test_filter_by_status(self):
        response = self.client.get(self.url, {"status": "abrogada"})
        assert response.status_code == 200
        for item in response.json()["results"]:
            assert item["status"] == "abrogada"

    def test_filter_by_law_type(self):
        response = self.client.get(self.url, {"law_type": "non_legislative"})
        assert response.status_code == 200
        for item in response.json()["results"]:
            assert item["law_type"] == "non_legislative"

    def test_filter_law_type_all_returns_everything(self):
        """law_type=all should not filter at all."""
        response = self.client.get(self.url, {"law_type": "all"})
        assert response.status_code == 200
        assert response.json()["count"] >= 4

    def test_filter_by_q_search(self):
        response = self.client.get(self.url, {"q": "Guadalajara"})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        for item in data["results"]:
            assert "guadalajara" in item["name"].lower()

    def test_sort_name_desc(self):
        response = self.client.get(self.url, {"sort": "name_desc"})
        assert response.status_code == 200
        ids = [r["id"] for r in response.json()["results"]]
        assert ids == sorted(ids, reverse=True)

    def test_sort_date_desc(self):
        response = self.client.get(self.url, {"sort": "date_desc"})
        assert response.status_code == 200

    def test_pagination_page_size(self):
        response = self.client.get(self.url, {"page_size": 2})
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 2

    def test_domain_filter(self):
        """Test filtering by domain (maps to categories via DOMAIN_MAP)."""
        # Create a law with a category that is in a domain
        law = _create_law(
            official_id=f"fiscal_{_uid()}",
            name="Codigo Fiscal",
            category="fiscal",
        )
        response = self.client.get(self.url, {"domain": "fiscal"})
        assert response.status_code == 200
        # Should include the fiscal law
        ids = [r["id"] for r in response.json()["results"]]
        assert law.official_id in ids

    def test_result_item_structure(self):
        response = self.client.get(self.url)
        item = response.json()["results"][0]
        assert "id" in item
        assert "name" in item
        assert "tier" in item
        assert "category" in item
        assert "status" in item
        assert "versions" in item
        assert "law_type" in item


# ---------------------------------------------------------------------------
# LawDetailView — edge cases
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLawDetailEdgeCases:
    """Edge case tests for GET /laws/{id}/."""

    def setup_method(self):
        self.client = APIClient()

    @patch("apps.api.law_views.es_client")
    def test_law_detail_es_unavailable(self, mock_es):
        """Law detail returns data with degraded=True when ES is down."""
        law = _create_law(official_id=f"det_{_uid()}", name="Detail Test Law")
        mock_es.ping.return_value = False

        url = reverse("law-detail", args=[law.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["articles"] == 0
        assert data.get("degraded") is True

    @patch("apps.api.law_views.es_client")
    def test_law_detail_es_connection_error(self, mock_es):
        """Law detail handles ES connection error gracefully."""
        law = _create_law(official_id=f"esc_{_uid()}", name="ES Error Law")
        mock_es.ping.side_effect = ESConnectionError("connection refused")

        url = reverse("law-detail", args=[law.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data.get("degraded") is True

    @patch("apps.api.law_views.es_client")
    def test_law_detail_has_cross_refs(self, mock_es):
        """Law detail shows has_cross_refs when cross-references exist."""
        law = _create_law(official_id=f"xref_{_uid()}", name="CrossRef Law")
        CrossReference.objects.create(
            source_law_slug=law.official_id,
            source_article_id="1",
            target_law_slug="other",
            reference_text="ref",
            confidence=0.9,
            start_position=0,
            end_position=3,
        )
        mock_es.ping.return_value = True
        mock_es.count.return_value = {"count": 10}

        url = reverse("law-detail", args=[law.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.json()["has_cross_refs"] is True

    @patch("apps.api.law_views.es_client")
    def test_law_detail_versions_sorted_desc(self, mock_es):
        """Versions are returned in descending publication_date order."""
        law = _create_law(official_id=f"ver_{_uid()}", name="Versioned Law")
        LawVersion.objects.create(law=law, publication_date=date(2023, 1, 1))
        LawVersion.objects.create(law=law, publication_date=date(2025, 6, 1))
        LawVersion.objects.create(law=law, publication_date=date(2024, 3, 15))

        mock_es.ping.return_value = True
        mock_es.count.return_value = {"count": 0}

        url = reverse("law-detail", args=[law.official_id])
        response = self.client.get(url)

        dates = [v["publication_date"] for v in response.json()["versions"]]
        assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# law_search — intra-law search
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLawSearch:
    """Tests for GET /laws/{id}/search/."""

    def setup_method(self):
        self.client = APIClient()
        self.law = _create_law(official_id=f"srch_{_uid()}", name="Search Law")

    def test_missing_query_returns_400(self):
        url = reverse("law-search", args=[self.law.official_id])
        response = self.client.get(url)
        assert response.status_code == 400
        assert "q" in response.json()["error"].lower()

    def test_empty_query_returns_400(self):
        url = reverse("law-search", args=[self.law.official_id])
        response = self.client.get(url, {"q": "  "})
        assert response.status_code == 400

    def test_nonexistent_law_returns_404(self):
        url = reverse("law-search", args=["nonexistent"])
        response = self.client.get(url, {"q": "test"})
        assert response.status_code == 404

    @patch("apps.api.law_views.es_client")
    def test_search_success(self, mock_es):
        mock_es.search.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {"article": "5", "text": "Art 5 text..."},
                        "_score": 3.5,
                        "highlight": {"text": ["<em>Art</em> 5 text..."]},
                    }
                ],
            }
        }

        url = reverse("law-search", args=[self.law.official_id])
        response = self.client.get(url, {"q": "texto"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["query"] == "texto"
        assert data["results"][0]["article_id"] == "5"
        assert data["results"][0]["score"] == 3.5

    @patch("apps.api.law_views.es_client")
    def test_search_without_highlight(self, mock_es):
        """When no highlight, snippet falls back to text[:200]."""
        mock_es.search.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {"article": "1", "text": "Full text here"},
                        "_score": 1.0,
                    }
                ],
            }
        }

        url = reverse("law-search", args=[self.law.official_id])
        response = self.client.get(url, {"q": "test"})

        assert response.status_code == 200
        assert response.json()["results"][0]["snippet"] == "Full text here"

    @patch("apps.api.law_views.es_client")
    def test_search_es_error_returns_500(self, mock_es):
        mock_es.search.side_effect = ESConnectionError("connection refused")

        url = reverse("law-search", args=[self.law.official_id])
        response = self.client.get(url, {"q": "test"})

        assert response.status_code == 500
        assert "error" in response.json()


# ---------------------------------------------------------------------------
# law_articles — pagination, dedup, ES errors
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLawArticlesEdgeCases:
    """Edge case tests for GET /laws/{id}/articles/."""

    def setup_method(self):
        self.client = APIClient()
        self.law = _create_law(official_id=f"arts_{_uid()}", name="Articles Law")

    def test_nonexistent_law_returns_404(self):
        url = reverse("law-articles", args=["nonexistent"])
        response = self.client.get(url)
        assert response.status_code == 404

    @patch("apps.api.law_views.es_client")
    def test_pagination_params(self, mock_es):
        mock_es.count.return_value = {"count": 100}
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"article": f"{i}", "text": f"Art {i}"}}
                    for i in range(1, 6)
                ]
            }
        }

        url = reverse("law-articles", args=[self.law.official_id])
        response = self.client.get(url, {"page": 2, "page_size": 5})

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 5

    @patch("apps.api.law_views.es_client")
    def test_deduplicates_articles(self, mock_es):
        """Duplicate article IDs from ES are deduplicated."""
        mock_es.count.return_value = {"count": 2}
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"article": "1", "text": "First"}},
                    {"_source": {"article": "1", "text": "Duplicate"}},
                    {"_source": {"article": "2", "text": "Second"}},
                ]
            }
        }

        url = reverse("law-articles", args=[self.law.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        articles = response.json()["articles"]
        article_ids = [a["article_id"] for a in articles]
        assert len(article_ids) == 2
        assert article_ids == sorted(article_ids)

    @patch("apps.api.law_views.es_client")
    def test_es_connection_error_returns_degraded(self, mock_es):
        """law_articles returns 200 with degraded=True when ES is down."""
        mock_es.count.side_effect = ConnectionTimeout("timeout")

        url = reverse("law-articles", args=[self.law.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["degraded"] is True
        assert data["articles"] == []
        assert data["total"] == 0
        assert data["law_id"] == self.law.official_id


# ---------------------------------------------------------------------------
# law_structure — ES errors
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLawStructureErrors:
    """Error handling for GET /laws/{id}/structure/."""

    def setup_method(self):
        self.client = APIClient()
        self.law = _create_law(official_id=f"struct_{_uid()}", name="Structure Law")

    def test_nonexistent_law_returns_404(self):
        url = reverse("law-structure", args=["nonexistent"])
        response = self.client.get(url)
        assert response.status_code == 404

    @patch("apps.api.law_views.es_client")
    def test_es_error_returns_500(self, mock_es):
        mock_es.search.side_effect = ESConnectionError("down")

        url = reverse("law-structure", args=[self.law.official_id])
        response = self.client.get(url)

        assert response.status_code == 500
        assert "error" in response.json()

    @patch("apps.api.law_views.es_client")
    def test_empty_hierarchy(self, mock_es):
        """Laws with no hierarchy data return empty structure."""
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"article": "1", "hierarchy": []}},
                ]
            }
        }

        url = reverse("law-structure", args=[self.law.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.json()["structure"] == []


# ---------------------------------------------------------------------------
# categories_list
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCategoriesList:
    """Tests for GET /categories/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("categories-list")

    def test_categories_with_counts(self):
        _create_law(category="fiscal")
        _create_law(category="fiscal")
        _create_law(category="laboral")

        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        cats = {c["category"]: c["count"] for c in data}
        assert cats.get("fiscal", 0) >= 2
        assert cats.get("laboral", 0) >= 1

    def test_categories_have_labels(self):
        _create_law(category="civil")

        response = self.client.get(self.url)
        data = response.json()
        civil = next((c for c in data if c["category"] == "civil"), None)
        assert civil is not None
        assert civil["label"] == "Derecho Civil"

    def test_excludes_empty_categories(self):
        _create_law(category="")
        _create_law(category=None)
        _create_law(category="fiscal")

        response = self.client.get(self.url)
        data = response.json()
        cats = [c["category"] for c in data]
        assert "" not in cats
        assert None not in cats


# ---------------------------------------------------------------------------
# RelatedLawsView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRelatedLaws:
    """Tests for GET /laws/{id}/related/."""

    def setup_method(self):
        self.client = APIClient()
        self.law = _create_law(
            official_id=f"rel_{_uid()}", name="Related Test Law", category="fiscal"
        )

    def test_nonexistent_law_returns_404(self):
        url = reverse("law-related", args=["nonexistent"])
        response = self.client.get(url)
        assert response.status_code == 404

    @patch("apps.api.law_views.es_client")
    def test_es_error_falls_back_to_db(self, mock_es):
        """When ES fails, related laws come from same-category DB fallback."""
        mock_es.ping.side_effect = ESConnectionError("down")

        # Create a same-category law for fallback
        other = _create_law(
            official_id=f"relother_{_uid()}", name="Other Fiscal Law", category="fiscal"
        )

        url = reverse("law-related", args=[self.law.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["law_id"] == self.law.official_id
        related_ids = [r["law_id"] for r in data["related"]]
        assert other.official_id in related_ids

    @patch("apps.api.law_views.es_client")
    def test_es_returns_empty_falls_back(self, mock_es):
        """When ES returns empty results, fallback to DB."""
        mock_es.ping.return_value = True
        mock_es.search.side_effect = [
            # First call: articles for MLT context
            {"hits": {"hits": []}},
            # Second call: MLT results
            {"hits": {"hits": []}, "aggregations": {"by_law": {"buckets": []}}},
        ]

        other = _create_law(
            official_id=f"relf_{_uid()}", name="Fallback Law", category="fiscal"
        )

        url = reverse("law-related", args=[self.law.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert len(response.json()["related"]) >= 1

    @patch("apps.api.law_views.es_client")
    def test_es_returns_related(self, mock_es):
        """When ES returns results, they are used directly."""
        mock_es.ping.return_value = True
        mock_es.search.side_effect = [
            # First call: articles for MLT context
            {"hits": {"hits": [{"_source": {"text": "Fiscal obligations apply..."}}]}},
            # Second call: MLT results
            {
                "hits": {"hits": []},
                "aggregations": {
                    "by_law": {
                        "buckets": [
                            {
                                "key": "cff",
                                "doc_count": 5,
                                "top_hit": {
                                    "hits": {
                                        "hits": [
                                            {
                                                "_source": {
                                                    "law_name": "Codigo Fiscal",
                                                    "tier": "federal",
                                                    "category": "fiscal",
                                                    "state": None,
                                                }
                                            }
                                        ]
                                    }
                                },
                            }
                        ]
                    }
                },
            },
        ]

        url = reverse("law-related", args=[self.law.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        related = response.json()["related"]
        assert len(related) == 1
        assert related[0]["law_id"] == "cff"
        assert related[0]["name"] == "Codigo Fiscal"


# ---------------------------------------------------------------------------
# suggest — with ES and DB fallback
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSuggestWithES:
    """Tests for GET /suggest/ covering ES path and fallback."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("law-suggest")

    @patch("apps.api.law_views.es_client")
    def test_suggest_es_success(self, mock_es):
        """When ES completion suggester returns results, those are used."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = {
            "suggest": {
                "law-suggest": [
                    {
                        "options": [
                            {
                                "_source": {
                                    "id": "cpeum",
                                    "name": "Constitucion",
                                    "tier": "federal",
                                }
                            }
                        ]
                    }
                ]
            }
        }

        response = self.client.get(self.url, {"q": "const"})

        assert response.status_code == 200
        suggestions = response.json()["suggestions"]
        assert len(suggestions) == 1
        assert suggestions[0]["id"] == "cpeum"


# ---------------------------------------------------------------------------
# laws_exist — batch existence check
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLawsExist:
    """Tests for GET /laws/exists/?ids=..."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("laws-exist")

    def test_returns_existing_ids(self):
        law1 = _create_law(official_id="cpeum", name="Constitucion")
        law2 = _create_law(official_id="ccf", name="Codigo Civil Federal")

        response = self.client.get(self.url, {"ids": "cpeum,ccf,nonexistent"})
        assert response.status_code == 200
        data = response.json()
        existing = set(data["existing"])
        assert "cpeum" in existing
        assert "ccf" in existing
        assert "nonexistent" not in existing

    def test_empty_ids_returns_empty(self):
        response = self.client.get(self.url, {"ids": ""})
        assert response.status_code == 200
        assert response.json()["existing"] == []

    def test_no_ids_param_returns_empty(self):
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert response.json()["existing"] == []

    def test_limits_to_20_ids(self):
        """Only the first 20 IDs are checked."""
        ids = [f"law_{i}" for i in range(25)]
        for lid in ids[:21]:
            _create_law(official_id=lid)

        response = self.client.get(self.url, {"ids": ",".join(ids)})
        assert response.status_code == 200
        assert len(response.json()["existing"]) <= 20

    def test_whitespace_in_ids_handled(self):
        _create_law(official_id="cpeum")
        response = self.client.get(self.url, {"ids": " cpeum , , ccf "})
        assert response.status_code == 200
        assert "cpeum" in response.json()["existing"]

    def test_cache_header_set(self):
        response = self.client.get(self.url, {"ids": "cpeum"})
        assert "max-age=3600" in response.get("Cache-Control", "")


@pytest.mark.django_db
class TestSuggestESFailure:
    """Suggest endpoint fallback when ES is unavailable."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("law-suggest")

    @patch("apps.api.law_views.es_client")
    def test_suggest_es_failure_falls_back_to_db(self, mock_es):
        """When ES fails, fallback to DB icontains search."""
        mock_es.ping.side_effect = ESConnectionError("down")

        _create_law(official_id=f"fb_{_uid()}", name="Ley de Fallback")

        response = self.client.get(self.url, {"q": "Fallback"})

        assert response.status_code == 200
        suggestions = response.json()["suggestions"]
        assert len(suggestions) >= 1
        assert "Fallback" in suggestions[0]["name"]
