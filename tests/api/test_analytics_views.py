"""Tests for search analytics endpoint."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.api.middleware.janua_auth import JanuaUser
from apps.api.models import SearchQuery

# Analytics is wrapped with _protected() in urls.py, so it uses
# JanuaJWTAuthentication + IsTezcaAdmin for auth, plus check_feature() for tier gating.
JANUA_AUTH_PATCH = "apps.api.middleware.janua_auth.JanuaJWTAuthentication.authenticate"
ADMIN_PERM_PATCH = "apps.api.middleware.admin_permission.IsTezcaAdmin.has_permission"


def _make_admin(user_id="admin-user", tier="community"):
    user = JanuaUser({"sub": user_id, "email": f"{user_id}@test.com", "role": "admin"})
    user.tier = tier
    user.scopes = ["read", "search"]
    user.allowed_domains = []
    user.api_key_prefix = ""
    return user


@pytest.mark.django_db
class TestSearchAnalytics:
    """Tests for GET /admin/analytics/search/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("admin-search-analytics")

    @patch(ADMIN_PERM_PATCH, return_value=True)
    @patch(JANUA_AUTH_PATCH)
    def test_analytics_with_data(self, mock_auth, _mock_admin):
        """GET returns analytics aggregations when data exists."""
        admin = _make_admin(tier="community")
        mock_auth.return_value = (admin, "fake-token")

        now = timezone.now()
        SearchQuery.objects.create(
            query="constitucion", result_count=150, response_time_ms=45
        )
        SearchQuery.objects.create(
            query="constitucion", result_count=120, response_time_ms=50
        )
        SearchQuery.objects.create(
            query="ley federal del trabajo", result_count=0, response_time_ms=30
        )

        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["total_searches"] == 3
        assert data["period_days"] == 30
        assert data["avg_response_time_ms"] is not None
        assert len(data["top_queries"]) > 0
        assert data["top_queries"][0]["query"] == "constitucion"
        assert data["top_queries"][0]["count"] == 2
        assert len(data["zero_result_queries"]) == 1
        assert data["zero_result_queries"][0]["query"] == "ley federal del trabajo"

    @patch(ADMIN_PERM_PATCH, return_value=True)
    @patch(JANUA_AUTH_PATCH)
    def test_analytics_empty(self, mock_auth, _mock_admin):
        """GET returns zero totals when no search data exists."""
        admin = _make_admin(tier="community")
        mock_auth.return_value = (admin, "fake-token")

        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["total_searches"] == 0
        assert data["top_queries"] == []
        assert data["zero_result_queries"] == []
        assert data["avg_response_time_ms"] is None

    @patch(ADMIN_PERM_PATCH, return_value=True)
    @patch(JANUA_AUTH_PATCH)
    def test_analytics_anon_tier_forbidden(self, mock_auth, _mock_admin):
        """GET with anon tier returns 403 (feature gate)."""
        admin = _make_admin(tier="anon")
        mock_auth.return_value = (admin, "fake-token")

        response = self.client.get(self.url)

        assert response.status_code == 403
        assert "community" in response.json()["error"].lower()

    @patch(ADMIN_PERM_PATCH, return_value=True)
    @patch(JANUA_AUTH_PATCH)
    def test_analytics_essentials_tier_forbidden(self, mock_auth, _mock_admin):
        """GET with essentials tier returns 403 (feature gate)."""
        admin = _make_admin(tier="essentials")
        mock_auth.return_value = (admin, "fake-token")

        response = self.client.get(self.url)

        assert response.status_code == 403

    @patch(ADMIN_PERM_PATCH, return_value=True)
    @patch(JANUA_AUTH_PATCH)
    def test_analytics_community_tier_allowed(self, mock_auth, _mock_admin):
        """GET with community tier returns 200 (feature gate passes)."""
        admin = _make_admin(tier="community")
        mock_auth.return_value = (admin, "fake-token")

        response = self.client.get(self.url)

        assert response.status_code == 200

    @patch(ADMIN_PERM_PATCH, return_value=True)
    @patch(JANUA_AUTH_PATCH)
    def test_analytics_days_param_capped(self, mock_auth, _mock_admin):
        """GET ?days=365 is capped at 90 days."""
        admin = _make_admin(tier="community")
        mock_auth.return_value = (admin, "fake-token")

        response = self.client.get(self.url, {"days": 365})

        assert response.status_code == 200
        assert response.json()["period_days"] == 90

    @patch(ADMIN_PERM_PATCH, return_value=True)
    @patch(JANUA_AUTH_PATCH)
    def test_analytics_custom_days(self, mock_auth, _mock_admin):
        """GET ?days=7 filters to last 7 days only."""
        admin = _make_admin(tier="community")
        mock_auth.return_value = (admin, "fake-token")

        # Create a query from 20 days ago (should be excluded with days=7)
        old_query = SearchQuery.objects.create(
            query="old search", result_count=10, response_time_ms=20
        )
        SearchQuery.objects.filter(id=old_query.id).update(
            created_at=timezone.now() - timedelta(days=20)
        )

        # Create a recent query
        SearchQuery.objects.create(
            query="recent search", result_count=5, response_time_ms=15
        )

        response = self.client.get(self.url, {"days": 7})

        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 7
        assert data["total_searches"] == 1
