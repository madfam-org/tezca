"""Tests for user-scoped API key endpoints.

Covers:
  - List own API keys (GET /user/apikeys/)
  - Create API key (POST /user/apikeys/)
  - Update API key (PATCH /user/apikeys/<prefix>/)
  - Revoke API key (DELETE /user/apikeys/<prefix>/revoke/)
"""

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.middleware.janua_auth import JanuaUser
from apps.api.models import APIKey

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"


def _make_user(user_id="test-user-1", tier="academic"):
    user = JanuaUser({"sub": user_id, "email": f"{user_id}@test.com", "tier": tier})
    user.tier = tier
    user.scopes = ["read", "search"]
    user.allowed_domains = []
    user.api_key_prefix = ""
    return user


@pytest.mark.django_db
class TestUserApiKeyList:
    """Tests for GET /user/apikeys/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("user-apikey-list-create")
        self.user = _make_user()

    @patch(AUTH_PATCH)
    def test_list_empty(self, mock_auth):
        """GET returns empty list when user has no API keys."""
        mock_auth.return_value = (self.user, "fake-token")
        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["keys"] == []

    @patch(AUTH_PATCH)
    def test_list_own_keys_only(self, mock_auth):
        """GET returns only keys belonging to the authenticated user."""
        mock_auth.return_value = (self.user, "fake-token")

        # Keys for our user
        APIKey.objects.create(
            prefix="ownkey01",
            hashed_key="fakehash1",
            name="My Key 1",
            owner_email="test-user-1@test.com",
            janua_user_id="test-user-1",
            tier="academic",
            scopes=["read", "search"],
            is_active=True,
        )
        APIKey.objects.create(
            prefix="ownkey02",
            hashed_key="fakehash2",
            name="My Key 2",
            owner_email="test-user-1@test.com",
            janua_user_id="test-user-1",
            tier="academic",
            scopes=["read", "search"],
            is_active=True,
        )

        # Key for another user (should NOT appear)
        APIKey.objects.create(
            prefix="otherk01",
            hashed_key="fakehash3",
            name="Other Key",
            owner_email="other-user@test.com",
            janua_user_id="other-user",
            tier="essentials",
            scopes=["read"],
            is_active=True,
        )

        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert len(data["keys"]) == 2
        prefixes = {k["prefix"] for k in data["keys"]}
        assert prefixes == {"ownkey01", "ownkey02"}

    @patch(AUTH_PATCH)
    def test_list_includes_inactive(self, mock_auth):
        """GET returns both active and inactive keys for the user."""
        mock_auth.return_value = (self.user, "fake-token")

        APIKey.objects.create(
            prefix="actkey01",
            hashed_key="fakehash1",
            name="Active Key",
            owner_email="test-user-1@test.com",
            janua_user_id="test-user-1",
            tier="academic",
            scopes=["read", "search"],
            is_active=True,
        )
        APIKey.objects.create(
            prefix="inactk01",
            hashed_key="fakehash2",
            name="Inactive Key",
            owner_email="test-user-1@test.com",
            janua_user_id="test-user-1",
            tier="academic",
            scopes=["read", "search"],
            is_active=False,
        )

        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert len(data["keys"]) == 2

    def test_list_unauthenticated(self):
        """GET without auth returns 401."""
        response = self.client.get(self.url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestUserApiKeyCreate:
    """Tests for POST /user/apikeys/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("user-apikey-list-create")
        self.user = _make_user()

    @patch(AUTH_PATCH)
    def test_create_success(self, mock_auth):
        """POST with valid name returns 201 with key starting with tzk_."""
        mock_auth.return_value = (self.user, "fake-token")

        response = self.client.post(self.url, {"name": "My key"}, format="json")

        assert response.status_code == 201
        data = response.json()
        assert data["key"].startswith("tzk_")
        assert "prefix" in data
        assert len(data["prefix"]) == 8
        assert data["tier"] == "academic"

    @patch(AUTH_PATCH)
    def test_create_inherits_tier(self, mock_auth):
        """Created key inherits the authenticated user's tier."""
        mock_auth.return_value = (self.user, "fake-token")

        response = self.client.post(self.url, {"name": "Tier check"}, format="json")

        assert response.status_code == 201
        data = response.json()
        assert data["tier"] == "academic"
        # Verify in DB
        api_key = APIKey.objects.get(prefix=data["prefix"])
        assert api_key.tier == "academic"

    @patch(AUTH_PATCH)
    def test_create_default_scopes(self, mock_auth):
        """Created key gets appropriate default scopes for the user's tier."""
        mock_auth.return_value = (self.user, "fake-token")

        response = self.client.post(self.url, {"name": "Scopes check"}, format="json")

        assert response.status_code == 201
        data = response.json()
        scopes = data["scopes"]
        assert "read" in scopes
        assert "search" in scopes
        # Academic tier also gets export and bulk
        assert "export" in scopes
        assert "bulk" in scopes

    @patch(AUTH_PATCH)
    def test_create_missing_name(self, mock_auth):
        """POST without name returns 400."""
        mock_auth.return_value = (self.user, "fake-token")

        response = self.client.post(self.url, {}, format="json")

        assert response.status_code == 400

    @patch(AUTH_PATCH)
    def test_create_max_limit(self, mock_auth):
        """POST when user already has 5 active keys returns 409."""
        mock_auth.return_value = (self.user, "fake-token")

        for i in range(5):
            APIKey.objects.create(
                prefix=f"maxkey0{i}",
                hashed_key=f"fakehash{i}",
                name=f"Key {i}",
                owner_email="test-user-1@test.com",
                janua_user_id="test-user-1",
                tier="academic",
                scopes=["read", "search"],
                is_active=True,
            )

        response = self.client.post(self.url, {"name": "One too many"}, format="json")

        assert response.status_code == 409
        data = response.json()
        assert "maximum" in data["error"].lower()

    @patch(AUTH_PATCH)
    def test_create_anon_forbidden(self, mock_auth):
        """POST from an anon-tier user returns 403."""
        anon_user = _make_user(tier="anon")
        mock_auth.return_value = (anon_user, "fake-token")

        response = self.client.post(self.url, {"name": "Anon key"}, format="json")

        assert response.status_code == 403


@pytest.mark.django_db
class TestUserApiKeyUpdate:
    """Tests for PATCH /user/apikeys/<prefix>/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = _make_user()

    @patch(AUTH_PATCH)
    def test_update_name(self, mock_auth):
        """PATCH with new name returns 200 and updates the name."""
        mock_auth.return_value = (self.user, "fake-token")

        api_key = APIKey.objects.create(
            prefix="updkey01",
            hashed_key="fakehash",
            name="Old Name",
            owner_email="test-user-1@test.com",
            janua_user_id="test-user-1",
            tier="academic",
            scopes=["read", "search"],
            is_active=True,
        )
        url = reverse("user-apikey-update", args=[api_key.prefix])

        response = self.client.patch(url, {"name": "New Name"}, format="json")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        api_key.refresh_from_db()
        assert api_key.name == "New Name"

    @patch(AUTH_PATCH)
    def test_update_other_user_key(self, mock_auth):
        """PATCH on another user's key returns 404."""
        mock_auth.return_value = (self.user, "fake-token")

        other_key = APIKey.objects.create(
            prefix="othrupd1",
            hashed_key="fakehash",
            name="Other Key",
            owner_email="other-user@test.com",
            janua_user_id="other-user",
            tier="essentials",
            scopes=["read"],
            is_active=True,
        )
        url = reverse("user-apikey-update", args=[other_key.prefix])

        response = self.client.patch(url, {"name": "Hacked Name"}, format="json")

        assert response.status_code == 404
        other_key.refresh_from_db()
        assert other_key.name == "Other Key"

    @patch(AUTH_PATCH)
    def test_update_tier_ignored(self, mock_auth):
        """PATCH with tier field does not change the tier."""
        mock_auth.return_value = (self.user, "fake-token")

        api_key = APIKey.objects.create(
            prefix="tiernch1",
            hashed_key="fakehash",
            name="Tier Lock",
            owner_email="test-user-1@test.com",
            janua_user_id="test-user-1",
            tier="academic",
            scopes=["read", "search"],
            is_active=True,
        )
        url = reverse("user-apikey-update", args=[api_key.prefix])

        response = self.client.patch(
            url, {"name": "Still Tier Lock", "tier": "madfam"}, format="json"
        )

        assert response.status_code == 200
        api_key.refresh_from_db()
        assert api_key.tier == "academic"


@pytest.mark.django_db
class TestUserApiKeyRevoke:
    """Tests for DELETE /user/apikeys/<prefix>/revoke/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = _make_user()

    @patch(AUTH_PATCH)
    def test_revoke_success(self, mock_auth):
        """DELETE sets is_active=False and returns 204."""
        mock_auth.return_value = (self.user, "fake-token")

        api_key = APIKey.objects.create(
            prefix="revkey01",
            hashed_key="fakehash",
            name="Revoke Me",
            owner_email="test-user-1@test.com",
            janua_user_id="test-user-1",
            tier="academic",
            scopes=["read", "search"],
            is_active=True,
        )
        url = reverse("user-apikey-revoke", args=[api_key.prefix])

        response = self.client.delete(url)

        assert response.status_code == 204
        api_key.refresh_from_db()
        assert api_key.is_active is False

    @patch(AUTH_PATCH)
    def test_revoke_other_user(self, mock_auth):
        """DELETE on another user's key returns 404."""
        mock_auth.return_value = (self.user, "fake-token")

        other_key = APIKey.objects.create(
            prefix="othrrev1",
            hashed_key="fakehash",
            name="Other Revoke",
            owner_email="other-user@test.com",
            janua_user_id="other-user",
            tier="essentials",
            scopes=["read"],
            is_active=True,
        )
        url = reverse("user-apikey-revoke", args=[other_key.prefix])

        response = self.client.delete(url)

        assert response.status_code == 404
        other_key.refresh_from_db()
        assert other_key.is_active is True

    @patch(AUTH_PATCH)
    def test_revoke_nonexistent(self, mock_auth):
        """DELETE on a prefix that does not exist returns 404."""
        mock_auth.return_value = (self.user, "fake-token")

        url = reverse("user-apikey-revoke", args=["ZZZZZZZZ"])

        response = self.client.delete(url)

        assert response.status_code == 404
