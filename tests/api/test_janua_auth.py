"""Tests for Janua JWT authentication middleware."""

import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
import requests
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from jwt.algorithms import RSAAlgorithm
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from apps.api.middleware.janua_auth import (
    JWKS_CACHE_TTL,
    JanuaJWTAuthentication,
    JanuaUser,
    _get_jwks,
    _jwks_cache,
)


def _generate_rsa_keypair():
    """Generate an RSA keypair and return (private_key, jwk_dict)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    public_jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    public_jwk["kid"] = "test-kid-1"
    public_jwk["use"] = "sig"
    public_jwk["alg"] = "RS256"
    return private_key, public_jwk


def _make_token(private_key, claims, headers=None):
    """Encode a JWT with RS256."""
    _headers = {"kid": "test-kid-1"}
    if headers:
        _headers.update(headers)
    return pyjwt.encode(claims, private_key, algorithm="RS256", headers=_headers)


# Shared keypair for all tests
_private_key, _public_jwk = _generate_rsa_keypair()

JANUA_BASE_URL = "https://auth.test.example.com"


def _valid_claims(**overrides):
    now = int(time.time())
    claims = {
        "sub": "user-123",
        "email": "test@example.com",
        "name": "Test User",
        "iss": JANUA_BASE_URL,
        "aud": "tezca-api",
        "exp": now + 3600,
        "iat": now,
    }
    claims.update(overrides)
    return claims


def _reset_jwks_cache():
    _jwks_cache["keys"] = None
    _jwks_cache["fetched_at"] = 0


class TestGetJwks:
    """Tests for JWKS fetching and caching."""

    def setup_method(self):
        _reset_jwks_cache()

    @patch("apps.api.middleware.janua_auth.requests.get")
    @patch("apps.api.middleware.janua_auth.settings")
    def test_fetches_and_caches_jwks(self, mock_settings, mock_get):
        mock_settings.JANUA_BASE_URL = JANUA_BASE_URL
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"keys": [_public_jwk]}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        keys = _get_jwks()
        assert len(keys) == 1
        assert keys[0]["kid"] == "test-kid-1"
        # Second call should use cache (no extra HTTP call)
        keys2 = _get_jwks()
        assert keys2 == keys
        assert mock_get.call_count == 1

    @patch("apps.api.middleware.janua_auth.requests.get")
    @patch("apps.api.middleware.janua_auth.settings")
    def test_stale_fallback_on_network_failure(self, mock_settings, mock_get):
        mock_settings.JANUA_BASE_URL = JANUA_BASE_URL
        # Populate cache
        _jwks_cache["keys"] = [_public_jwk]
        _jwks_cache["fetched_at"] = 0  # expired

        mock_get.side_effect = requests.RequestException("network error")
        keys = _get_jwks()
        assert keys == [_public_jwk]

    @patch("apps.api.middleware.janua_auth.requests.get")
    @patch("apps.api.middleware.janua_auth.settings")
    def test_raises_when_no_cache_and_network_fails(self, mock_settings, mock_get):
        mock_settings.JANUA_BASE_URL = JANUA_BASE_URL
        mock_get.side_effect = requests.RequestException("network error")

        with pytest.raises(AuthenticationFailed, match="JWKS unavailable"):
            _get_jwks()

    @patch("apps.api.middleware.janua_auth.requests.get")
    @patch("apps.api.middleware.janua_auth.settings")
    def test_ttl_refresh(self, mock_settings, mock_get):
        mock_settings.JANUA_BASE_URL = JANUA_BASE_URL
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"keys": [_public_jwk]}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        # Populate with expired timestamp
        _jwks_cache["keys"] = [_public_jwk]
        _jwks_cache["fetched_at"] = time.time() - JWKS_CACHE_TTL - 10

        keys = _get_jwks()
        assert mock_get.call_count == 1  # should have refetched
        assert len(keys) == 1


class TestJanuaAuthentication:
    """Tests for JanuaJWTAuthentication.authenticate()."""

    def setup_method(self):
        _reset_jwks_cache()
        self.auth = JanuaJWTAuthentication()
        self.factory = APIRequestFactory()

    def _request_with_token(self, token):
        request = self.factory.get("/api/v1/admin/health/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return request

    def test_no_header_returns_none(self):
        request = self.factory.get("/api/v1/admin/health/")
        result = self.auth.authenticate(request)
        assert result is None

    def test_empty_bearer_returns_none(self):
        request = self.factory.get("/api/v1/admin/health/")
        request.META["HTTP_AUTHORIZATION"] = "Bearer "
        result = self.auth.authenticate(request)
        assert result is None

    @patch("apps.api.middleware.janua_auth._get_jwks")
    @patch("apps.api.middleware.janua_auth.settings")
    def test_valid_token_returns_janua_user(self, mock_settings, mock_get_jwks):
        mock_settings.JANUA_BASE_URL = JANUA_BASE_URL
        mock_settings.JANUA_AUDIENCE = "tezca-api"
        mock_get_jwks.return_value = [_public_jwk]

        token = _make_token(_private_key, _valid_claims())
        request = self._request_with_token(token)
        user, returned_token = self.auth.authenticate(request)

        assert isinstance(user, JanuaUser)
        assert user.id == "user-123"
        assert user.email == "test@example.com"
        assert user.is_authenticated is True
        assert returned_token == token

    @patch("apps.api.middleware.janua_auth._get_jwks")
    @patch("apps.api.middleware.janua_auth.settings")
    def test_expired_token_raises(self, mock_settings, mock_get_jwks):
        mock_settings.JANUA_BASE_URL = JANUA_BASE_URL
        mock_settings.JANUA_AUDIENCE = "tezca-api"
        mock_get_jwks.return_value = [_public_jwk]

        token = _make_token(
            _private_key,
            _valid_claims(exp=int(time.time()) - 100),
        )
        request = self._request_with_token(token)
        with pytest.raises(AuthenticationFailed, match="expired"):
            self.auth.authenticate(request)

    @patch("apps.api.middleware.janua_auth._get_jwks")
    @patch("apps.api.middleware.janua_auth.settings")
    def test_invalid_audience_raises(self, mock_settings, mock_get_jwks):
        mock_settings.JANUA_BASE_URL = JANUA_BASE_URL
        mock_settings.JANUA_AUDIENCE = "tezca-api"
        mock_get_jwks.return_value = [_public_jwk]

        token = _make_token(_private_key, _valid_claims(aud="wrong-audience"))
        request = self._request_with_token(token)
        with pytest.raises(AuthenticationFailed, match="audience"):
            self.auth.authenticate(request)

    @patch("apps.api.middleware.janua_auth._get_jwks")
    @patch("apps.api.middleware.janua_auth.settings")
    def test_invalid_issuer_raises(self, mock_settings, mock_get_jwks):
        mock_settings.JANUA_BASE_URL = JANUA_BASE_URL
        mock_settings.JANUA_AUDIENCE = "tezca-api"
        mock_get_jwks.return_value = [_public_jwk]

        token = _make_token(
            _private_key,
            _valid_claims(iss="https://wrong-issuer.example.com"),
        )
        request = self._request_with_token(token)
        with pytest.raises(AuthenticationFailed, match="issuer"):
            self.auth.authenticate(request)

    @patch("apps.api.middleware.janua_auth._get_jwks")
    @patch("apps.api.middleware.janua_auth.settings")
    def test_unknown_kid_raises(self, mock_settings, mock_get_jwks):
        mock_settings.JANUA_BASE_URL = JANUA_BASE_URL
        mock_settings.JANUA_AUDIENCE = "tezca-api"
        mock_get_jwks.return_value = [_public_jwk]

        token = _make_token(
            _private_key,
            _valid_claims(),
            headers={"kid": "unknown-kid"},
        )
        request = self._request_with_token(token)
        with pytest.raises(AuthenticationFailed, match="matching key"):
            self.auth.authenticate(request)

    def test_janua_user_str(self):
        user = JanuaUser({"sub": "u1", "email": "a@b.com", "name": "A"})
        assert str(user) == "a@b.com"

    def test_janua_user_str_fallback(self):
        user = JanuaUser({"sub": "u1"})
        assert str(user) == "u1"

    def test_janua_user_attributes(self):
        claims = {"sub": "u1", "email": "a@b.com", "name": "Alice", "tier": "premium"}
        user = JanuaUser(claims)
        assert user.id == "u1"
        assert user.email == "a@b.com"
        assert user.name == "Alice"
        assert user.claims["tier"] == "premium"
        assert user.is_authenticated is True
