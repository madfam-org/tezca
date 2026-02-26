"""
Tests for API key admin CRUD endpoints.

Covers:
  - Create API key (POST /admin/apikeys/)
  - List API keys (GET /admin/apikeys/list/)
  - Update API key (PATCH /admin/apikeys/<prefix>/)
  - Revoke API key (DELETE /admin/apikeys/<prefix>/revoke/)
"""

import uuid
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.middleware.janua_auth import JanuaUser
from apps.api.models import APIKey

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"


def _admin_user():
    """Create a mock admin JanuaUser."""
    user = JanuaUser(
        {"sub": "admin-user-1", "email": "admin@madfam.io", "tier": "premium"}
    )
    user.tier = "premium"
    user.scopes = ["read", "search"]
    user.allowed_domains = []
    user.api_key_prefix = ""
    return user


@pytest.mark.django_db
class TestCreateAPIKey:
    def setup_method(self):
        self.client = APIClient()

    @patch(AUTH_PATCH)
    def test_create_key_success(self, mock_auth):
        mock_auth.return_value = (_admin_user(), "fake-token")

        url = reverse("admin-apikey-create")
        response = self.client.post(
            url,
            {
                "name": "Dhanam Compliance Prod",
                "owner_email": "dev@dhanam.mx",
                "tier": "internal",
                "scopes": ["read", "search", "bulk"],
                "allowed_domains": ["fiscal", "mercantil"],
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["key"].startswith("tzk_")
        assert response.data["tier"] == "internal"
        assert "bulk" in response.data["scopes"]
        assert APIKey.objects.filter(prefix=response.data["prefix"]).exists()

    @patch(AUTH_PATCH)
    def test_create_key_missing_fields(self, mock_auth):
        mock_auth.return_value = (_admin_user(), "fake-token")

        url = reverse("admin-apikey-create")
        response = self.client.post(url, {}, format="json")

        assert response.status_code == 400
        assert "required" in response.data["error"]

    @patch(AUTH_PATCH)
    def test_create_key_invalid_tier(self, mock_auth):
        mock_auth.return_value = (_admin_user(), "fake-token")

        url = reverse("admin-apikey-create")
        response = self.client.post(
            url,
            {"name": "Bad Tier", "owner_email": "x@x.com", "tier": "platinum"},
            format="json",
        )

        assert response.status_code == 400
        assert "Invalid tier" in response.data["error"]


@pytest.mark.django_db
class TestListAPIKeys:
    def setup_method(self):
        self.client = APIClient()

    @patch(AUTH_PATCH)
    def test_list_keys(self, mock_auth):
        mock_auth.return_value = (_admin_user(), "fake-token")

        from apps.api.apikeys import generate_api_key

        for i in range(3):
            full, prefix, hashed = generate_api_key()
            APIKey.objects.create(
                prefix=prefix,
                hashed_key=hashed,
                name=f"Key {i}",
                owner_email=f"user{i}@example.com",
            )

        url = reverse("admin-apikey-list")
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.data["count"] == 3
        # Full key should never be returned
        for key_data in response.data["keys"]:
            assert "key" not in key_data or not key_data.get("key", "").startswith(
                "tzk_"
            )


@pytest.mark.django_db
class TestUpdateAPIKey:
    def setup_method(self):
        self.client = APIClient()
        from apps.api.apikeys import generate_api_key

        full, self.prefix, hashed = generate_api_key()
        self.api_key = APIKey.objects.create(
            prefix=self.prefix,
            hashed_key=hashed,
            name="Update Me",
            owner_email="update@example.com",
            tier="free",
        )

    @patch(AUTH_PATCH)
    def test_update_tier(self, mock_auth):
        mock_auth.return_value = (_admin_user(), "fake-token")

        url = reverse("admin-apikey-update", args=[self.prefix])
        response = self.client.patch(url, {"tier": "pro"}, format="json")

        assert response.status_code == 200
        assert response.data["tier"] == "pro"
        self.api_key.refresh_from_db()
        assert self.api_key.tier == "pro"

    @patch(AUTH_PATCH)
    def test_update_nonexistent_key(self, mock_auth):
        mock_auth.return_value = (_admin_user(), "fake-token")

        url = reverse("admin-apikey-update", args=["ZZZZZZZZ"])
        response = self.client.patch(url, {"tier": "pro"}, format="json")

        assert response.status_code == 404


@pytest.mark.django_db
class TestRevokeAPIKey:
    def setup_method(self):
        self.client = APIClient()
        from apps.api.apikeys import generate_api_key

        full, self.prefix, hashed = generate_api_key()
        self.api_key = APIKey.objects.create(
            prefix=self.prefix,
            hashed_key=hashed,
            name="Revoke Me",
            owner_email="revoke@example.com",
        )

    @patch(AUTH_PATCH)
    def test_revoke_key(self, mock_auth):
        mock_auth.return_value = (_admin_user(), "fake-token")

        url = reverse("admin-apikey-revoke", args=[self.prefix])
        response = self.client.delete(url)

        assert response.status_code == 200
        assert response.data["status"] == "revoked"
        self.api_key.refresh_from_db()
        assert self.api_key.is_active is False
