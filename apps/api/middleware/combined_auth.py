"""
Combined authentication middleware.

Tries API key first, then Janua JWT, then returns None (anonymous).
Sets request.user.tier and request.user.scopes uniformly.
"""

import logging

from rest_framework.authentication import BaseAuthentication

from .apikey_auth import APIKeyAuthentication
from .janua_auth import JanuaJWTAuthentication

logger = logging.getLogger(__name__)


class AnonymousAPIUser:
    """Represents an unauthenticated request with tier defaults."""

    id = ""
    email = ""
    name = ""
    tier = "anon"
    scopes = []
    allowed_domains = []
    api_key_prefix = ""
    is_authenticated = False
    claims = {"tier": "anon"}

    def __str__(self):
        return "anonymous"


class CombinedAuthentication(BaseAuthentication):
    """
    Tries authentication methods in order:
    1. API key (X-API-Key or Authorization: ApiKey)
    2. Janua JWT (Authorization: Bearer)
    3. Returns None — anonymous access (DRF will set AnonymousUser)

    After authentication, request.user will always have .tier and .scopes.
    """

    def authenticate(self, request):
        # 1. Try API key auth
        try:
            result = APIKeyAuthentication().authenticate(request)
            if result is not None:
                return result
        except Exception:
            # If API key was provided but invalid, let it raise
            # Check if there was actually an API key header
            has_api_key = (
                request.META.get("HTTP_X_API_KEY")
                or request.META.get("HTTP_AUTHORIZATION", "").startswith("ApiKey ")
            )
            if has_api_key:
                raise
            # No API key header — fall through to JWT

        # 2. Try Janua JWT
        try:
            result = JanuaJWTAuthentication().authenticate(request)
            if result is not None:
                user, token = result
                # Enrich JanuaUser with tier/scopes for uniform access
                if not hasattr(user, "tier"):
                    user.tier = user.claims.get(
                        "tier", user.claims.get("plan", "free")
                    )
                if not hasattr(user, "scopes"):
                    user.scopes = user.claims.get("scopes", ["read", "search"])
                if not hasattr(user, "allowed_domains"):
                    user.allowed_domains = []
                if not hasattr(user, "api_key_prefix"):
                    user.api_key_prefix = ""
                return (user, token)
        except Exception:
            # If JWT was provided but invalid, let it raise
            has_bearer = request.META.get("HTTP_AUTHORIZATION", "").startswith(
                "Bearer "
            )
            if has_bearer:
                raise

        # 3. No auth — return None (DRF sets AnonymousUser)
        return None

    def authenticate_header(self, request):
        return 'ApiKey realm="api", Bearer realm="api"'
