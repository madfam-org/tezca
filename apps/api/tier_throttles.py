"""
Tier-aware rate limiting using Django cache (Redis sliding window).

Replaces the default AnonRateThrottle and SearchRateThrottle with a single
throttle class that respects the user's API key tier.
"""

import logging

from django.core.cache import cache
from rest_framework.throttling import BaseThrottle

from .tier_permissions import RATE_LIMITS as TIER_RATE_LIMITS

logger = logging.getLogger(__name__)


def _get_client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


class TieredRateThrottle(BaseThrottle):
    """
    Sliding-window rate limiter using Redis cache.

    Identifies requests by API key prefix (authenticated) or IP (anonymous).
    Checks both per-minute and per-hour limits based on user tier.
    """

    def allow_request(self, request, view):
        tier = self._get_tier(request)
        identity = self._get_identity(request)
        limits = self._get_limits(request, tier)

        per_minute, per_hour = limits

        # Atomic check-and-increment for both windows
        minute_key = f"tezca:throttle:{identity}:min"
        if not self._check_and_increment(minute_key, per_minute, 60):
            self.wait_seconds = self._get_wait(minute_key, 60)
            return False

        hour_key = f"tezca:throttle:{identity}:hr"
        if not self._check_and_increment(hour_key, per_hour, 3600):
            self.wait_seconds = self._get_wait(hour_key, 3600)
            return False

        return True

    def wait(self):
        return getattr(self, "wait_seconds", 60)

    def _get_tier(self, request) -> str:
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            return getattr(user, "tier", "free")
        return "anon"

    def _get_identity(self, request) -> str:
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            prefix = getattr(user, "api_key_prefix", "")
            if prefix:
                return f"key:{prefix}"
            return f"user:{getattr(user, 'id', '')}"
        return f"ip:{_get_client_ip(request)}"

    def _get_limits(self, request, tier: str) -> tuple[int, int]:
        """Get rate limits, respecting per-key overrides."""
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            custom_hourly = getattr(user, "rate_limit_per_hour", None)
            if custom_hourly:
                default_minute, _ = TIER_RATE_LIMITS.get(tier, TIER_RATE_LIMITS["anon"])
                return (default_minute, custom_hourly)
        return TIER_RATE_LIMITS.get(tier, TIER_RATE_LIMITS["anon"])

    def _check_and_increment(self, key: str, limit: int, window: int) -> bool:
        """Atomically increment the counter and check against the limit."""
        try:
            count = cache.incr(key)
        except ValueError:
            # Key doesn't exist yet — set it with expiry
            cache.set(key, 1, window)
            return True
        return count <= limit

    def _get_wait(self, key: str, window: int) -> int:
        ttl = cache.ttl(key) if hasattr(cache, "ttl") else window
        return max(ttl, 1)
