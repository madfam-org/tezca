"""
Janua JWT Authentication backend for Django REST Framework.

Validates RS256 JWTs issued by a Janua identity provider.
Applied only to admin API endpoints — public endpoints remain open.
"""

import logging
import threading
import time

import jwt
import requests
from django.conf import settings
from jwt.algorithms import RSAAlgorithm
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)

# JWKS cache with thread-safe access
_jwks_cache = {"keys": None, "fetched_at": 0, "lock": threading.Lock()}
JWKS_CACHE_TTL = 3600  # 1 hour


def _get_jwks():
    """Fetch and cache JWKS from Janua's well-known endpoint."""
    now = time.time()
    with _jwks_cache["lock"]:
        if _jwks_cache["keys"] and (now - _jwks_cache["fetched_at"]) < JWKS_CACHE_TTL:
            return _jwks_cache["keys"]

    base_url = getattr(settings, "JANUA_BASE_URL", "")
    if not base_url:
        raise AuthenticationFailed(
            "Janua auth is not configured (JANUA_BASE_URL missing)"
        )

    jwks_url = f"{base_url.rstrip('/')}/.well-known/jwks.json"
    try:
        resp = requests.get(jwks_url, timeout=10)
        resp.raise_for_status()
        jwks = resp.json()
    except requests.RequestException as exc:
        logger.error("Failed to fetch JWKS from %s: %s", jwks_url, exc)
        # Return stale cache if available
        if _jwks_cache["keys"]:
            return _jwks_cache["keys"]
        raise AuthenticationFailed("Unable to validate token: JWKS unavailable")

    with _jwks_cache["lock"]:
        _jwks_cache["keys"] = jwks.get("keys", [])
        _jwks_cache["fetched_at"] = time.time()

    return _jwks_cache["keys"]


def _get_public_key(token):
    """Extract the correct public key from JWKS based on the token's kid."""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.DecodeError:
        raise AuthenticationFailed("Invalid token format")

    kid = unverified_header.get("kid")
    if not kid:
        raise AuthenticationFailed("Token missing 'kid' header")

    jwks = _get_jwks()
    for key_data in jwks:
        if key_data.get("kid") == kid:
            return RSAAlgorithm.from_jwk(key_data)

    # kid not found — force refresh and retry once
    _jwks_cache["keys"] = None
    jwks = _get_jwks()
    for key_data in jwks:
        if key_data.get("kid") == kid:
            return RSAAlgorithm.from_jwk(key_data)

    raise AuthenticationFailed("Unable to find matching key for token")


class JanuaUser:
    """Lightweight user object from JWT claims (no Django User model needed)."""

    def __init__(self, claims):
        self.id = claims.get("sub", "")
        self.email = claims.get("email", "")
        self.name = claims.get("name", "")
        self.claims = claims
        self.is_authenticated = True

    def __str__(self):
        return self.email or self.id


class JanuaJWTAuthentication(BaseAuthentication):
    """
    DRF authentication class that validates Janua-issued RS256 JWTs.

    Usage in views:
        @api_view(["GET"])
        @authentication_classes([JanuaJWTAuthentication])
        @permission_classes([IsAuthenticated])
        def admin_endpoint(request): ...
    """

    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith(f"{self.keyword} "):
            return None  # No auth header — let permission classes decide

        token = auth_header[len(self.keyword) + 1 :]
        if not token:
            return None

        public_key = _get_public_key(token)
        audience = getattr(settings, "JANUA_AUDIENCE", "tezca-api")
        issuer = getattr(settings, "JANUA_BASE_URL", "")

        try:
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=audience,
                issuer=issuer,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token has expired")
        except jwt.InvalidAudienceError:
            raise AuthenticationFailed("Invalid token audience")
        except jwt.InvalidIssuerError:
            raise AuthenticationFailed("Invalid token issuer")
        except jwt.PyJWTError:
            raise AuthenticationFailed("Token validation failed")

        return (JanuaUser(claims), token)

    def authenticate_header(self, request):
        return self.keyword
