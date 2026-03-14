"""Tests for changelog endpoint."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.middleware.janua_auth import JanuaUser
from apps.api.models import Law, LawVersion

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"


def _make_user(user_id="test-user-1", tier="academic"):
    user = JanuaUser({"sub": user_id, "email": f"{user_id}@test.com", "tier": tier})
    user.tier = tier
    user.scopes = ["read", "search"]
    user.allowed_domains = []
    user.api_key_prefix = ""
    return user


@pytest.mark.django_db
class TestChangelog:
    """Tests for GET /changelog/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("changelog")
        self.user = _make_user()

        # Create test law and versions
        self.law = Law.objects.create(
            official_id="cpeum",
            name="Constitucion Politica",
            tier="federal",
            category="ley",
            status="vigente",
        )
        self.law2 = Law.objects.create(
            official_id="lft",
            name="Ley Federal del Trabajo",
            tier="federal",
            category="laboral",
            status="vigente",
        )

    @patch(AUTH_PATCH)
    def test_changelog_success(self, mock_auth):
        """GET ?since=YYYY-MM-DD returns changes since date."""
        mock_auth.return_value = (self.user, "fake-token")
        today = date.today()
        LawVersion.objects.create(
            law=self.law,
            publication_date=today,
            change_summary="Updated article 1",
        )

        since = (today - timedelta(days=1)).isoformat()
        response = self.client.get(self.url, {"since": since})

        assert response.status_code == 200
        data = response.json()
        assert data["since"] == since
        assert data["total"] == 1
        assert data["changes"][0]["law_id"] == "cpeum"
        assert data["changes"][0]["change_type"] == "new_version"

    @patch(AUTH_PATCH)
    def test_changelog_missing_since(self, mock_auth):
        """GET without since parameter returns 400."""
        mock_auth.return_value = (self.user, "fake-token")

        response = self.client.get(self.url)

        assert response.status_code == 400
        assert "since" in response.json()["error"].lower()

    @patch(AUTH_PATCH)
    def test_changelog_invalid_date_format(self, mock_auth):
        """GET with invalid date format returns 400."""
        mock_auth.return_value = (self.user, "fake-token")

        response = self.client.get(self.url, {"since": "not-a-date"})

        assert response.status_code == 400
        assert "date" in response.json()["error"].lower()

    def test_changelog_unauthenticated(self):
        """GET without auth returns 401."""
        response = self.client.get(self.url, {"since": "2026-01-01"})
        assert response.status_code == 401

    @patch(AUTH_PATCH)
    def test_changelog_insufficient_scope(self, mock_auth):
        """GET without 'read' scope returns 403."""
        user = _make_user()
        user.scopes = ["search"]  # No 'read' scope
        mock_auth.return_value = (user, "fake-token")

        response = self.client.get(self.url, {"since": "2026-01-01"})

        assert response.status_code == 403
        assert "scope" in response.json()["error"].lower()

    @patch(AUTH_PATCH)
    def test_changelog_domain_filter(self, mock_auth):
        """GET ?domain=labor filters to matching categories."""
        mock_auth.return_value = (self.user, "fake-token")
        today = date.today()
        LawVersion.objects.create(
            law=self.law,
            publication_date=today,
            change_summary="Ley update",
        )
        LawVersion.objects.create(
            law=self.law2,
            publication_date=today,
            change_summary="Labor update",
        )

        since = (today - timedelta(days=1)).isoformat()
        response = self.client.get(self.url, {"since": since, "domain": "labor"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["changes"][0]["law_id"] == "lft"

    @patch(AUTH_PATCH)
    def test_changelog_category_filter(self, mock_auth):
        """GET ?category=ley filters to matching category."""
        mock_auth.return_value = (self.user, "fake-token")
        today = date.today()
        LawVersion.objects.create(
            law=self.law, publication_date=today, change_summary="Ley update"
        )
        LawVersion.objects.create(
            law=self.law2, publication_date=today, change_summary="Labor update"
        )

        since = (today - timedelta(days=1)).isoformat()
        response = self.client.get(self.url, {"since": since, "category": "ley"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["changes"][0]["law_id"] == "cpeum"

    @patch(AUTH_PATCH)
    def test_changelog_allowed_domains_restriction(self, mock_auth):
        """GET with user restricted to specific domains filters results."""
        user = _make_user()
        user.allowed_domains = ["labor"]
        mock_auth.return_value = (user, "fake-token")
        today = date.today()
        LawVersion.objects.create(
            law=self.law, publication_date=today, change_summary="Ley update"
        )
        LawVersion.objects.create(
            law=self.law2, publication_date=today, change_summary="Labor update"
        )

        since = (today - timedelta(days=1)).isoformat()
        response = self.client.get(self.url, {"since": since})

        assert response.status_code == 200
        data = response.json()
        # Only laboral category laws should appear
        assert data["total"] == 1
        assert data["changes"][0]["law_id"] == "lft"

    @patch(AUTH_PATCH)
    def test_changelog_deduplicates_by_law(self, mock_auth):
        """GET deduplicates versions keeping latest per law."""
        mock_auth.return_value = (self.user, "fake-token")
        today = date.today()
        LawVersion.objects.create(
            law=self.law,
            publication_date=today - timedelta(days=1),
            change_summary="Older version",
        )
        LawVersion.objects.create(
            law=self.law,
            publication_date=today,
            change_summary="Newer version",
        )

        since = (today - timedelta(days=5)).isoformat()
        response = self.client.get(self.url, {"since": since})

        assert response.status_code == 200
        data = response.json()
        # Should deduplicate to 1 entry for cpeum
        assert data["total"] == 1
        assert data["changes"][0]["law_id"] == "cpeum"
