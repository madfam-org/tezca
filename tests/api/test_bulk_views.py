"""
Tests for bulk data access and changelog endpoints.

Covers:
  - Bulk articles requires authentication
  - Bulk articles requires 'bulk' scope
  - Bulk articles returns cursor-paginated results
  - Changelog requires authentication
  - Changelog requires 'since' parameter
  - Changelog returns changes
  - Domain filter on existing endpoints
"""

import uuid
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.api.apikeys import generate_api_key
from apps.api.middleware.apikey_auth import APIKeyUser
from apps.api.models import APIKey, Law, LawVersion

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"


def _make_api_key_user(tier="pro", scopes=None, allowed_domains=None):
    """Create a mock APIKeyUser."""
    if scopes is None:
        scopes = ["read", "search", "bulk"]
    mock_key = MagicMock()
    mock_key.prefix = "testpfx1"
    mock_key.owner_email = "test@example.com"
    mock_key.name = "Test Key"
    mock_key.tier = tier
    mock_key.scopes = scopes
    mock_key.allowed_domains = allowed_domains or []
    user = APIKeyUser(mock_key)
    return user


# ── Bulk articles ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestBulkArticles:
    def setup_method(self):
        self.client = APIClient()

    def test_unauthenticated_returns_401(self):
        """Anonymous requests get 401."""
        url = reverse("bulk-articles")
        response = self.client.get(url)
        assert response.status_code == 401

    @patch(AUTH_PATCH)
    def test_missing_scope_returns_403(self, mock_auth):
        """API key without 'bulk' scope gets 403."""
        user = _make_api_key_user(scopes=["read", "search"])
        mock_auth.return_value = (user, "fake-key")

        url = reverse("bulk-articles")
        response = self.client.get(url)
        assert response.status_code == 403
        assert "bulk" in response.data["error"]

    @patch("apps.api.bulk_views.es_client")
    @patch(AUTH_PATCH)
    def test_bulk_articles_success(self, mock_auth, mock_es):
        """Authenticated request with bulk scope returns articles."""
        user = _make_api_key_user()
        mock_auth.return_value = (user, "fake-key")

        mock_es.search.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_source": {
                            "law_id": "cff",
                            "law_name": "Código Fiscal de la Federación",
                            "category": "fiscal",
                            "tier": "federal",
                            "status": "vigente",
                            "law_type": "legislative",
                            "state": None,
                            "article": "Art. 1",
                            "text": "Texto del artículo 1.",
                            "publication_date": "2024-01-01",
                        },
                        "sort": ["cff", "Art. 1"],
                    },
                    {
                        "_source": {
                            "law_id": "cff",
                            "law_name": "Código Fiscal de la Federación",
                            "category": "fiscal",
                            "tier": "federal",
                            "status": "vigente",
                            "law_type": "legislative",
                            "state": None,
                            "article": "Art. 2",
                            "text": "Texto del artículo 2.",
                            "publication_date": "2024-01-01",
                        },
                        "sort": ["cff", "Art. 2"],
                    },
                ],
            }
        }

        url = reverse("bulk-articles")
        response = self.client.get(url, {"domain": "finance", "page_size": "10"})

        assert response.status_code == 200
        assert response.data["count"] == 2
        assert len(response.data["results"]) == 2
        assert response.data["results"][0]["law_id"] == "cff"

    @patch(AUTH_PATCH)
    def test_domain_restriction_enforcement(self, mock_auth):
        """API key with allowed_domains rejects requests for other domains."""
        user = _make_api_key_user(
            scopes=["read", "search", "bulk"],
            allowed_domains=["finance"],
        )
        mock_auth.return_value = (user, "fake-key")

        url = reverse("bulk-articles")
        response = self.client.get(url, {"category": "penal"})

        assert response.status_code == 403
        assert "Domain restriction" in response.data["error"]


# ── Changelog ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestChangelog:
    def setup_method(self):
        self.client = APIClient()

    def test_unauthenticated_returns_401(self):
        url = reverse("changelog")
        response = self.client.get(url, {"since": "2026-01-01"})
        assert response.status_code == 401

    @patch(AUTH_PATCH)
    def test_missing_since_returns_400(self, mock_auth):
        user = _make_api_key_user(scopes=["read"])
        mock_auth.return_value = (user, "fake-key")

        url = reverse("changelog")
        response = self.client.get(url)
        assert response.status_code == 400
        assert "since" in response.data["error"]

    @patch(AUTH_PATCH)
    def test_changelog_returns_changes(self, mock_auth):
        user = _make_api_key_user(scopes=["read"])
        mock_auth.return_value = (user, "fake-key")

        law_id = f"fed_cl_{uuid.uuid4().hex[:8]}"
        law = Law.objects.create(
            official_id=law_id,
            name="Ley de Cambios",
            tier="federal",
            category="fiscal",
        )
        LawVersion.objects.create(
            law=law,
            publication_date=date(2026, 2, 20),
            change_summary="Reforma DOF 20-02-2026",
        )

        url = reverse("changelog")
        response = self.client.get(url, {"since": "2026-01-01"})

        assert response.status_code == 200
        assert response.data["total"] >= 1
        found = [c for c in response.data["changes"] if c["law_id"] == law_id]
        assert len(found) == 1
        assert found[0]["change_summary"] == "Reforma DOF 20-02-2026"


# ── Domain filter on existing endpoints ───────────────────────────────


@pytest.mark.django_db
class TestDomainFilter:
    """Test ?domain= filter on LawListView and SearchView."""

    def setup_method(self):
        self.client = APIClient()
        self.fiscal_id = f"fed_fiscal_{uuid.uuid4().hex[:8]}"
        self.penal_id = f"fed_penal_{uuid.uuid4().hex[:8]}"

        Law.objects.create(
            official_id=self.fiscal_id,
            name="Ley Fiscal Test",
            tier="federal",
            category="fiscal",
        )
        Law.objects.create(
            official_id=self.penal_id,
            name="Ley Penal Test",
            tier="federal",
            category="penal",
        )

    def test_law_list_domain_finance(self):
        """?domain=finance filters to fiscal+mercantil only."""
        url = reverse("law-list")
        response = self.client.get(url, {"domain": "finance"})

        assert response.status_code == 200
        ids = [r["id"] for r in response.data["results"]]
        assert self.fiscal_id in ids
        assert self.penal_id not in ids

    def test_law_list_multi_category(self):
        """?category=fiscal,penal returns both."""
        url = reverse("law-list")
        response = self.client.get(url, {"category": "fiscal,penal"})

        assert response.status_code == 200
        ids = [r["id"] for r in response.data["results"]]
        assert self.fiscal_id in ids
        assert self.penal_id in ids

    @patch("apps.api.search_views.es_client")
    def test_search_domain_filter(self, mock_es):
        """SearchView passes domain filter to ES query."""
        mock_es.ping.return_value = True
        mock_es.search.return_value = {
            "hits": {
                "total": {"value": 0},
                "hits": [],
            },
            "aggregations": {},
        }

        url = reverse("search")
        self.client.get(url, {"q": "impuesto", "domain": "finance"})

        # Verify ES was called with terms filter for fiscal+mercantil
        call_args = mock_es.search.call_args
        body = call_args[1]["body"] if "body" in call_args[1] else call_args[0][0]
        filters = body["query"]["bool"].get("filter", [])

        domain_filter = [f for f in filters if "terms" in f and "category" in f["terms"]]
        assert len(domain_filter) == 1
        assert set(domain_filter[0]["terms"]["category"]) == {"fiscal", "mercantil"}
