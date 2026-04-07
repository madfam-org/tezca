"""
Tests for the resolve endpoint — combined article + judicial search.

Covers:
  - Missing q param returns 400
  - Valid query returns articles + judicial data
  - Domain filtering via DOMAIN_MAP
  - max_articles and max_judicial limit clamping
  - Invalid max_articles/max_judicial defaults gracefully
  - ES unavailable returns degraded response (judicial still works)
  - Empty results return empty arrays with 200
  - Cache-Control header is set
"""

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from elasticsearch.exceptions import ConnectionError as ESConnectionError
from elasticsearch.exceptions import ConnectionTimeout
from rest_framework.test import APIClient

from apps.api.models import JudicialRecord


# ── Helpers ───────────────────────────────────────────────────────────


def _build_es_article_hit(
    law_id,
    article_num,
    text="Texto de prueba.",
    score=5.0,
    tier="federal",
    domains=None,
    highlight_text=None,
):
    """Build a single ES hit matching the shape expected by resolve_views."""
    source = {
        "law_id": law_id,
        "law_name": f"Ley {law_id}",
        "article": str(article_num),
        "article_id": str(article_num),
        "text": text,
        "tier": tier,
        "status": "vigente",
        "domains": domains or [],
    }
    hit = {
        "_id": f"{law_id}-art-{article_num}",
        "_score": score,
        "_source": source,
    }
    if highlight_text:
        hit["highlight"] = {"text": [highlight_text]}
    else:
        hit["highlight"] = {"text": [f"<em>{text[:100]}</em>"]}
    return hit


def _build_es_response(hits):
    """Build a minimal ES search response envelope."""
    return {
        "hits": {
            "total": {"value": len(hits)},
            "hits": hits,
        },
    }


def _create_judicial_record(
    query_term="amparo",
    materia="civil",
    uid_suffix=None,
):
    """Create a single JudicialRecord whose rubro contains *query_term*."""
    uid = uid_suffix or uuid.uuid4().hex[:8]
    return JudicialRecord.objects.create(
        registro=f"REG-{uid}",
        epoca="11a",
        instancia="Primera Sala",
        materia=materia,
        tipo="jurisprudencia",
        rubro=f"DERECHO AL {query_term.upper()}. INTERPRETACION",
        texto=f"El {query_term} es un derecho fundamental...",
        ponente="Min. Prueba",
        fuente="Semanario Judicial de la Federacion",
        fecha_publicacion=date(2025, 1, 15),
    )


# ── Test classes ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestResolveMissingQuery:
    """Missing or blank q parameter must return 400."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("resolve")

    def test_no_q_param_returns_400(self):
        """GET /resolve/ with no q param returns 400 with error message."""
        response = self.client.get(self.url)

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "'q'" in data["error"]

    def test_empty_q_param_returns_400(self):
        """GET /resolve/?q= (empty string) returns 400."""
        response = self.client.get(self.url, {"q": ""})

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_whitespace_only_q_returns_400(self):
        """GET /resolve/?q=   (whitespace) returns 400 after .strip()."""
        response = self.client.get(self.url, {"q": "   "})

        assert response.status_code == 400


@pytest.mark.django_db
class TestResolveValidQuery:
    """Valid query returns articles from ES + judicial records from ORM."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("resolve")

    @patch("apps.api.resolve_views.es_client")
    def test_valid_query_returns_articles_and_judicial(self, mock_es):
        """Combined response includes both articles and judicial arrays."""
        mock_es.ping.return_value = True
        hits = [
            _build_es_article_hit("cpeum", 1, "Derechos humanos.", score=9.0),
            _build_es_article_hit("cpeum", 2, "Garantias individuales.", score=7.0),
        ]
        mock_es.search.return_value = _build_es_response(hits)

        rec = _create_judicial_record(query_term="derechos")

        response = self.client.get(self.url, {"q": "derechos"})

        assert response.status_code == 200
        data = response.json()

        # Articles from ES
        assert len(data["articles"]) == 2
        first = data["articles"][0]
        assert first["law_id"] == "cpeum"
        assert first["score"] == 9.0
        assert "snippet" in first
        assert "Art." in first["article"]
        assert "tier" in first
        assert "domains" in first

        # Judicial from ORM
        assert len(data["judicial"]) >= 1
        jud = data["judicial"][0]
        assert jud["registro"] == rec.registro
        assert jud["tipo"] == "jurisprudencia"
        assert jud["materia"] == "civil"
        assert "rubro" in jud
        assert "epoca" in jud
        assert "instancia" in jud

        # Metadata
        assert data["query"] == "derechos"
        assert "response_time_ms" in data
        assert "degraded" not in data  # no degradation

    @patch("apps.api.resolve_views.es_client")
    def test_response_shape_article_fields(self, mock_es):
        """Each article in the response has the expected field set."""
        mock_es.ping.return_value = True
        hits = [
            _build_es_article_hit(
                "lft", 10, "Articulo sobre trabajo.", score=6.5, domains=["labor"]
            ),
        ]
        mock_es.search.return_value = _build_es_response(hits)

        response = self.client.get(self.url, {"q": "trabajo"})

        data = response.json()
        art = data["articles"][0]
        expected_fields = {"law_id", "law_name", "article", "snippet", "score", "tier", "domains"}
        assert expected_fields.issubset(set(art.keys()))

    @patch("apps.api.resolve_views.es_client")
    def test_cache_control_header_present(self, mock_es):
        """Response includes Cache-Control header."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        response = self.client.get(self.url, {"q": "test"})

        assert response.status_code == 200
        assert "Cache-Control" in response
        assert "public" in response["Cache-Control"]
        assert "max-age=60" in response["Cache-Control"]


@pytest.mark.django_db
class TestResolveDomainFiltering:
    """Domain parameter filters both ES and judicial results."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("resolve")

    @patch("apps.api.resolve_views.es_client")
    def test_domain_adds_es_filter_clause(self, mock_es):
        """Passing domain=labor adds terms filter to the ES bool query."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        self.client.get(self.url, {"q": "despido", "domain": "labor"})

        assert mock_es.search.called
        call_kwargs = mock_es.search.call_args[1]
        query = call_kwargs["query"]
        bool_query = query["bool"]
        filter_clauses = bool_query.get("filter", [])
        # DOMAIN_MAP["labor"] == ["labor"], so terms filter should contain ["labor"]
        assert len(filter_clauses) == 1
        terms_filter = filter_clauses[0]
        assert "terms" in terms_filter
        assert terms_filter["terms"]["domains"] == ["labor"]

    @patch("apps.api.resolve_views.es_client")
    def test_composite_domain_expands_via_domain_map(self, mock_es):
        """Composite domain (e.g. 'manufacturing') maps to multiple base domains."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        self.client.get(self.url, {"q": "produccion", "domain": "manufacturing"})

        call_kwargs = mock_es.search.call_args[1]
        filter_clauses = call_kwargs["query"]["bool"].get("filter", [])
        assert len(filter_clauses) == 1
        domain_values = filter_clauses[0]["terms"]["domains"]
        # DOMAIN_MAP["manufacturing"] == ["labor", "administrative", "commercial"]
        assert set(domain_values) == {"labor", "administrative", "commercial"}

    @patch("apps.api.resolve_views.es_client")
    def test_unknown_domain_passes_through_as_single_item_list(self, mock_es):
        """Domain not in DOMAIN_MAP is passed through as [domain]."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        self.client.get(self.url, {"q": "test", "domain": "exotic"})

        call_kwargs = mock_es.search.call_args[1]
        filter_clauses = call_kwargs["query"]["bool"].get("filter", [])
        assert len(filter_clauses) == 1
        assert filter_clauses[0]["terms"]["domains"] == ["exotic"]

    @patch("apps.api.resolve_views.es_client")
    def test_domain_filters_judicial_by_materia(self, mock_es):
        """Domain parameter also filters JudicialRecord via materia__icontains."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        # Create records with different materias
        _create_judicial_record(query_term="despido", materia="laboral", uid_suffix="lab1")
        _create_judicial_record(query_term="despido", materia="civil", uid_suffix="civ1")

        response = self.client.get(
            self.url, {"q": "despido", "domain": "laboral"}
        )

        data = response.json()
        # Only the laboral record should appear
        assert len(data["judicial"]) == 1
        assert data["judicial"][0]["materia"] == "laboral"

    @patch("apps.api.resolve_views.es_client")
    def test_no_domain_returns_all_judicial(self, mock_es):
        """Without domain param, all matching judicial records are returned."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        _create_judicial_record(query_term="constitucion", materia="civil", uid_suffix="nd1")
        _create_judicial_record(
            query_term="constitucion", materia="constitucional", uid_suffix="nd2"
        )

        response = self.client.get(self.url, {"q": "constitucion"})

        data = response.json()
        assert len(data["judicial"]) == 2

    @patch("apps.api.resolve_views.es_client")
    def test_no_domain_omits_filter_from_es_query(self, mock_es):
        """Without domain param, no filter clause is added to ES query."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        self.client.get(self.url, {"q": "test"})

        call_kwargs = mock_es.search.call_args[1]
        bool_query = call_kwargs["query"]["bool"]
        assert "filter" not in bool_query

    @patch("apps.api.resolve_views.es_client")
    def test_domain_null_in_response_when_not_provided(self, mock_es):
        """Response domain field is null when no domain param is given."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        response = self.client.get(self.url, {"q": "test"})

        data = response.json()
        assert data["domain"] is None

    @patch("apps.api.resolve_views.es_client")
    def test_domain_echoed_in_response(self, mock_es):
        """Response domain field reflects the provided domain parameter."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        response = self.client.get(self.url, {"q": "test", "domain": "labor"})

        data = response.json()
        assert data["domain"] == "labor"


@pytest.mark.django_db
class TestResolveMaxLimits:
    """max_articles and max_judicial are respected and clamped to 1-10."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("resolve")

    @patch("apps.api.resolve_views.es_client")
    def test_max_articles_default_is_3(self, mock_es):
        """Without max_articles, ES search uses size=3."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        self.client.get(self.url, {"q": "test"})

        call_kwargs = mock_es.search.call_args[1]
        assert call_kwargs["size"] == 3

    @patch("apps.api.resolve_views.es_client")
    def test_max_articles_custom_value(self, mock_es):
        """max_articles=5 passes size=5 to ES."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        self.client.get(self.url, {"q": "test", "max_articles": "5"})

        call_kwargs = mock_es.search.call_args[1]
        assert call_kwargs["size"] == 5

    @patch("apps.api.resolve_views.es_client")
    def test_max_articles_clamped_to_10(self, mock_es):
        """max_articles=50 is clamped to 10."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        self.client.get(self.url, {"q": "test", "max_articles": "50"})

        call_kwargs = mock_es.search.call_args[1]
        assert call_kwargs["size"] == 10

    @patch("apps.api.resolve_views.es_client")
    def test_max_articles_clamped_to_1_minimum(self, mock_es):
        """max_articles=0 is clamped to 1."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        self.client.get(self.url, {"q": "test", "max_articles": "0"})

        call_kwargs = mock_es.search.call_args[1]
        assert call_kwargs["size"] == 1

    @patch("apps.api.resolve_views.es_client")
    def test_max_articles_negative_clamped_to_1(self, mock_es):
        """max_articles=-5 is clamped to 1."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        self.client.get(self.url, {"q": "test", "max_articles": "-5"})

        call_kwargs = mock_es.search.call_args[1]
        assert call_kwargs["size"] == 1

    @patch("apps.api.resolve_views.es_client")
    def test_max_judicial_default_is_2(self, mock_es):
        """Without max_judicial, at most 2 judicial records are returned."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        # Create 5 records, all matching query
        for i in range(5):
            _create_judicial_record(
                query_term="amparo", materia="civil", uid_suffix=f"mj-{i}"
            )

        response = self.client.get(self.url, {"q": "amparo"})

        data = response.json()
        assert len(data["judicial"]) == 2

    @patch("apps.api.resolve_views.es_client")
    def test_max_judicial_custom_value(self, mock_es):
        """max_judicial=4 returns at most 4 judicial records."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        for i in range(5):
            _create_judicial_record(
                query_term="amparo", materia="civil", uid_suffix=f"mjc-{i}"
            )

        response = self.client.get(self.url, {"q": "amparo", "max_judicial": "4"})

        data = response.json()
        assert len(data["judicial"]) == 4

    @patch("apps.api.resolve_views.es_client")
    def test_max_judicial_clamped_to_10(self, mock_es):
        """max_judicial=99 is clamped to 10."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        for i in range(12):
            _create_judicial_record(
                query_term="amparo", materia="civil", uid_suffix=f"mjx-{i}"
            )

        response = self.client.get(self.url, {"q": "amparo", "max_judicial": "99"})

        data = response.json()
        assert len(data["judicial"]) == 10

    @patch("apps.api.resolve_views.es_client")
    def test_max_judicial_clamped_to_1_minimum(self, mock_es):
        """max_judicial=0 is clamped to 1."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        for i in range(3):
            _create_judicial_record(
                query_term="amparo", materia="civil", uid_suffix=f"mjm-{i}"
            )

        response = self.client.get(self.url, {"q": "amparo", "max_judicial": "0"})

        data = response.json()
        assert len(data["judicial"]) == 1


@pytest.mark.django_db
class TestResolveInvalidLimitParams:
    """Invalid (non-integer) max_articles/max_judicial fall back to defaults."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("resolve")

    @patch("apps.api.resolve_views.es_client")
    def test_invalid_max_articles_defaults_to_3(self, mock_es):
        """Non-integer max_articles falls back to default 3."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        self.client.get(self.url, {"q": "test", "max_articles": "abc"})

        call_kwargs = mock_es.search.call_args[1]
        assert call_kwargs["size"] == 3

    @patch("apps.api.resolve_views.es_client")
    def test_invalid_max_judicial_defaults_to_2(self, mock_es):
        """Non-integer max_judicial falls back to default 2."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        for i in range(5):
            _create_judicial_record(
                query_term="amparo", materia="civil", uid_suffix=f"inv-{i}"
            )

        response = self.client.get(self.url, {"q": "amparo", "max_judicial": "xyz"})

        data = response.json()
        assert len(data["judicial"]) == 2

    @patch("apps.api.resolve_views.es_client")
    def test_float_max_articles_defaults_to_3(self, mock_es):
        """Float value for max_articles falls back to default 3."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        self.client.get(self.url, {"q": "test", "max_articles": "3.5"})

        call_kwargs = mock_es.search.call_args[1]
        assert call_kwargs["size"] == 3

    @patch("apps.api.resolve_views.es_client")
    def test_empty_string_max_articles_defaults_to_3(self, mock_es):
        """Empty string max_articles falls back to default 3."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        self.client.get(self.url, {"q": "test", "max_articles": ""})

        call_kwargs = mock_es.search.call_args[1]
        assert call_kwargs["size"] == 3


@pytest.mark.django_db
class TestResolveESDegradation:
    """ES unavailability triggers degraded mode: articles empty, judicial still works."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("resolve")

    @patch("apps.api.resolve_views.es_client")
    def test_es_ping_fails_returns_degraded(self, mock_es):
        """When ES ping returns False, articles_degraded=True and articles=[]."""
        mock_es.ping.return_value = False

        rec = _create_judicial_record(query_term="amparo", uid_suffix="deg1")

        response = self.client.get(self.url, {"q": "amparo"})

        assert response.status_code == 200
        data = response.json()
        assert data["degraded"] is True
        assert data["articles"] == []
        # Judicial still works
        assert len(data["judicial"]) >= 1
        assert data["judicial"][0]["registro"] == rec.registro

    @patch("apps.api.resolve_views.es_client")
    def test_es_connection_error_returns_degraded(self, mock_es):
        """ESConnectionError triggers degraded mode."""
        mock_es.ping.side_effect = ESConnectionError("Connection refused")

        rec = _create_judicial_record(query_term="amparo", uid_suffix="deg2")

        response = self.client.get(self.url, {"q": "amparo"})

        assert response.status_code == 200
        data = response.json()
        assert data["degraded"] is True
        assert data["articles"] == []
        assert len(data["judicial"]) >= 1

    @patch("apps.api.resolve_views.es_client")
    def test_es_connection_timeout_returns_degraded(self, mock_es):
        """ConnectionTimeout triggers degraded mode."""
        mock_es.ping.side_effect = ConnectionTimeout("Timeout")

        rec = _create_judicial_record(query_term="amparo", uid_suffix="deg3")

        response = self.client.get(self.url, {"q": "amparo"})

        assert response.status_code == 200
        data = response.json()
        assert data["degraded"] is True
        assert data["articles"] == []
        assert len(data["judicial"]) >= 1

    @patch("apps.api.resolve_views.es_client")
    def test_degraded_flag_absent_when_es_healthy(self, mock_es):
        """When ES is healthy, 'degraded' key is not in response."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        response = self.client.get(self.url, {"q": "test"})

        data = response.json()
        assert "degraded" not in data

    @patch("apps.api.resolve_views.es_client")
    def test_es_search_raises_connection_error_mid_query(self, mock_es):
        """ESConnectionError during search (not ping) also triggers degraded."""
        mock_es.ping.return_value = True
        mock_es.search.side_effect = ESConnectionError("lost connection")

        response = self.client.get(self.url, {"q": "test"})

        assert response.status_code == 200
        data = response.json()
        assert data["degraded"] is True
        assert data["articles"] == []


@pytest.mark.django_db
class TestResolveEmptyResults:
    """Empty results from both sources return empty arrays and 200 status."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("resolve")

    @patch("apps.api.resolve_views.es_client")
    def test_no_matches_returns_empty_arrays(self, mock_es):
        """Query matching nothing returns empty articles and judicial arrays."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        response = self.client.get(self.url, {"q": "xyznonexistent123"})

        assert response.status_code == 200
        data = response.json()
        assert data["articles"] == []
        assert data["judicial"] == []
        assert data["query"] == "xyznonexistent123"
        assert "response_time_ms" in data

    @patch("apps.api.resolve_views.es_client")
    def test_es_empty_judicial_has_data(self, mock_es):
        """ES returns nothing but judicial has matching records."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = _build_es_response([])

        _create_judicial_record(query_term="propiedad", uid_suffix="emp1")

        response = self.client.get(self.url, {"q": "propiedad"})

        data = response.json()
        assert data["articles"] == []
        assert len(data["judicial"]) == 1

    @patch("apps.api.resolve_views.es_client")
    def test_es_has_data_judicial_empty(self, mock_es):
        """ES returns hits but no judicial records match."""
        mock_es.ping.return_value = True
        hits = [_build_es_article_hit("cpeum", 1, "Articulo unico.", score=4.0)]
        mock_es.search.return_value = _build_es_response(hits)

        response = self.client.get(self.url, {"q": "xyzunmatchable999"})

        data = response.json()
        assert len(data["articles"]) == 1
        assert data["judicial"] == []
