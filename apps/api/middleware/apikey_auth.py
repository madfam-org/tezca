"""
API Key authentication backend for Django REST Framework.

Checks X-API-Key header, then falls back to Authorization: ApiKey <key>.
Returns an APIKeyUser carrying tier, scopes, and allowed_domains.
"""

import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from ..apikeys import hash_key

logger = logging.getLogger(__name__)

# Only update last_used_at if stale by this amount
LAST_USED_DEBOUNCE = timedelta(minutes=5)


class APIKeyUser:
    """Lightweight user object from an API key (no Django User model needed)."""

    def __init__(self, api_key):
        self.id = f"apikey:{api_key.prefix}"
        self.email = api_key.owner_email
        self.name = api_key.name
        self.tier = api_key.tier
        self.scopes = api_key.scopes or []
        self.allowed_domains = api_key.allowed_domains or []
        self.api_key_prefix = api_key.prefix
        self.is_authenticated = True
        self.claims = {
            "tier": api_key.tier,
            "scopes": api_key.scopes or [],
            "allowed_domains": api_key.allowed_domains or [],
        }

    def __str__(self):
        return f"{self.name} ({self.api_key_prefix})"


class APIKeyAuthentication(BaseAuthentication):
    """
    DRF authentication class that validates API keys.

    Checks:
    1. X-API-Key header
    2. Authorization: ApiKey <key>
    """

    def authenticate(self, request):
        raw_key = self._extract_key(request)
        if not raw_key:
            return None

        if not raw_key.startswith("tzk_"):
            return None

        # Extract prefix from the random part (after "tzk_")
        random_part = raw_key[4:]
        if len(random_part) < 8:
            raise AuthenticationFailed("Invalid API key format")
        prefix = random_part[:8]

        # Lazy import to avoid circular imports
        from ..models import APIKey

        try:
            api_key = APIKey.objects.get(prefix=prefix, is_active=True)
        except APIKey.DoesNotExist:
            raise AuthenticationFailed("Invalid API key")

        # Verify hash
        if api_key.hashed_key != hash_key(raw_key):
            raise AuthenticationFailed("Invalid API key")

        # Check expiry
        if api_key.expires_at and api_key.expires_at < timezone.now():
            raise AuthenticationFailed("API key has expired")

        # Debounced last_used_at update
        now = timezone.now()
        if (
            not api_key.last_used_at
            or (now - api_key.last_used_at) > LAST_USED_DEBOUNCE
        ):
            APIKey.objects.filter(pk=api_key.pk).update(last_used_at=now)

        return (APIKeyUser(api_key), raw_key)

    def authenticate_header(self, request):
        return "ApiKey"

    def _extract_key(self, request) -> str | None:
        """Extract API key from request headers."""
        # 1. X-API-Key header (preferred)
        key = request.META.get("HTTP_X_API_KEY")
        if key:
            return key.strip()

        # 2. Authorization: ApiKey <key>
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("ApiKey "):
            return auth_header[7:].strip()

        return None
