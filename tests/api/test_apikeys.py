"""
Tests for API key generation, hashing, and the APIKey model.

Covers:
  - Key generation format and uniqueness
  - Key hashing consistency
  - APIKey model creation and validation
  - APIKeyAuthentication backend
  - CombinedAuthentication fallback chain
"""

import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from apps.api.apikeys import generate_api_key, hash_key
from apps.api.middleware.apikey_auth import APIKeyAuthentication, APIKeyUser
from apps.api.middleware.combined_auth import CombinedAuthentication
from apps.api.models import APIKey

# ── Key generation ─────────────────────────────────────────────────────


class TestKeyGeneration:
    def test_key_format(self):
        """Generated key starts with tzk_ prefix."""
        full_key, prefix, hashed = generate_api_key()
        assert full_key.startswith("tzk_")
        assert len(prefix) == 8

    def test_key_uniqueness(self):
        """Two generated keys are different."""
        k1 = generate_api_key()
        k2 = generate_api_key()
        assert k1[0] != k2[0]
        assert k1[1] != k2[1]

    def test_hash_consistency(self):
        """Hashing the same key twice gives the same result."""
        full_key, _, hashed = generate_api_key()
        assert hash_key(full_key) == hashed
        assert hash_key(full_key) == hash_key(full_key)

    def test_hash_differs_for_different_keys(self):
        """Different keys produce different hashes."""
        k1 = generate_api_key()
        k2 = generate_api_key()
        assert k1[2] != k2[2]


# ── APIKey model ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAPIKeyModel:
    def test_create_api_key(self):
        """APIKey can be created with all fields."""
        full_key, prefix, hashed = generate_api_key()
        key = APIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed,
            name="Test Key",
            owner_email="test@example.com",
            tier="pro",
            scopes=["read", "search", "bulk"],
            allowed_domains=["fiscal", "mercantil"],
        )
        assert key.prefix == prefix
        assert key.tier == "pro"
        assert key.is_active is True
        assert "read" in key.scopes

    def test_prefix_unique(self):
        """Duplicate prefix raises IntegrityError."""
        full_key, prefix, hashed = generate_api_key()
        APIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed,
            name="Key 1",
            owner_email="a@example.com",
        )
        with pytest.raises(Exception):  # IntegrityError
            APIKey.objects.create(
                prefix=prefix,
                hashed_key="different_hash",
                name="Key 2",
                owner_email="b@example.com",
            )

    def test_str_representation(self):
        full_key, prefix, hashed = generate_api_key()
        key = APIKey(prefix=prefix, name="My Key", tier="enterprise")
        assert prefix in str(key)
        assert "enterprise" in str(key)


# ── APIKeyAuthentication backend ──────────────────────────────────────


@pytest.mark.django_db
class TestAPIKeyAuthentication:
    def setup_method(self):
        self.factory = APIRequestFactory()
        self.auth = APIKeyAuthentication()

        self.full_key, self.prefix, self.hashed = generate_api_key()
        self.api_key = APIKey.objects.create(
            prefix=self.prefix,
            hashed_key=self.hashed,
            name="Auth Test Key",
            owner_email="auth@example.com",
            tier="pro",
            scopes=["read", "search"],
        )

    def test_authenticate_via_x_api_key_header(self):
        """X-API-Key header authenticates correctly."""
        request = self.factory.get("/", HTTP_X_API_KEY=self.full_key)
        user, token = self.auth.authenticate(request)
        assert isinstance(user, APIKeyUser)
        assert user.tier == "pro"
        assert user.api_key_prefix == self.prefix
        assert user.is_authenticated is True

    def test_authenticate_via_authorization_header(self):
        """Authorization: ApiKey header authenticates correctly."""
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"ApiKey {self.full_key}")
        user, token = self.auth.authenticate(request)
        assert user.tier == "pro"

    def test_no_header_returns_none(self):
        """Request without API key header returns None (pass-through)."""
        request = self.factory.get("/")
        result = self.auth.authenticate(request)
        assert result is None

    def test_invalid_key_raises(self):
        """Invalid API key raises AuthenticationFailed."""
        request = self.factory.get(
            "/", HTTP_X_API_KEY="tzk_invalid_key_12345678901234567890"
        )
        with pytest.raises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_inactive_key_raises(self):
        """Inactive API key raises AuthenticationFailed."""
        self.api_key.is_active = False
        self.api_key.save()
        request = self.factory.get("/", HTTP_X_API_KEY=self.full_key)
        with pytest.raises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_expired_key_raises(self):
        """Expired API key raises AuthenticationFailed."""
        self.api_key.expires_at = timezone.now() - timedelta(hours=1)
        self.api_key.save()
        request = self.factory.get("/", HTTP_X_API_KEY=self.full_key)
        with pytest.raises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_non_tzk_prefix_returns_none(self):
        """Non-tzk_ prefixed key is ignored (returns None)."""
        request = self.factory.get("/", HTTP_X_API_KEY="sk_some_other_key")
        result = self.auth.authenticate(request)
        assert result is None


# ── CombinedAuthentication ────────────────────────────────────────────


@pytest.mark.django_db
class TestCombinedAuthentication:
    def setup_method(self):
        self.factory = APIRequestFactory()
        self.auth = CombinedAuthentication()

    def test_no_auth_returns_none(self):
        """No auth headers → returns None (anonymous)."""
        request = self.factory.get("/")
        result = self.auth.authenticate(request)
        assert result is None

    def test_api_key_takes_precedence(self):
        """API key is tried before JWT."""
        full_key, prefix, hashed = generate_api_key()
        APIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed,
            name="Combined Test",
            owner_email="combined@example.com",
            tier="enterprise",
            scopes=["read", "bulk"],
        )
        request = self.factory.get("/", HTTP_X_API_KEY=full_key)
        user, token = self.auth.authenticate(request)
        assert user.tier == "enterprise"
        assert user.api_key_prefix == prefix

    def test_invalid_api_key_raises_even_with_no_jwt(self):
        """If X-API-Key is present but invalid, raises (doesn't fall through to JWT)."""
        request = self.factory.get(
            "/", HTTP_X_API_KEY="tzk_bad_key_1234567890123456789012"
        )
        with pytest.raises(AuthenticationFailed):
            self.auth.authenticate(request)
