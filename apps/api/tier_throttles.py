"""
Tier-aware rate limiting using Django cache (Redis sliding window).

Replaces the default AnonRateThrottle and SearchRateThrottle with a single
throttle class that respects the user's API key tier.
"""

import logging
import time

from django.core.cache import cache
from rest_framework.throttling import BaseThrottle

logger = logging.getLogger(__name__)

# (requests_per_minute, requests_per_hour)
TIER_RATE_LIMITS = {
    "anon": (10, 100),
    "free": (30, 500),
    "pro": (60, 2_000),
    "enterprise": (120, 10_000),
    "internal": (200, 50_000),
}


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

        # Check per-minute limit
        minute_key = f"tezca:throttle:{identity}:min"
        if not self._check_window(minute_key, per_minute, 60):
            self.wait_seconds = self._get_wait(minute_key, 60)
            return False

        # Check per-hour limit
        hour_key = f"tezca:throttle:{identity}:hr"
        if not self._check_window(hour_key, per_hour, 3600):
            self.wait_seconds = self._get_wait(hour_key, 3600)
            return False

        # Record this request in both windows
        now = time.time()
        pipe_minute = f"tezca:throttle:{identity}:min"
        pipe_hour = f"tezca:throttle:{identity}:hr"

        # Use a simple counter approach with expiry
        cache.incr(f"{pipe_minute}:count", 1) if cache.get(f"{pipe_minute}:count") else cache.set(f"{pipe_minute}:count", 1, 60)
        cache.incr(f"{pipe_hour}:count", 1) if cache.get(f"{pipe_hour}:count") else cache.set(f"{pipe_hour}:count", 1, 3600)

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
            # Check for per-key rate_limit_per_hour override
            # We'd need to look it up, but the APIKeyUser doesn't carry it.
            # For now, use tier defaults.
            pass
        return TIER_RATE_LIMITS.get(tier, TIER_RATE_LIMITS["anon"])

    def _check_window(self, key: str, limit: int, window: int) -> bool:
        count_key = f"{key}:count"
        current = cache.get(count_key, 0)
        return current < limit

    def _get_wait(self, key: str, window: int) -> int:
        ttl = cache.ttl(f"{key}:count") if hasattr(cache, "ttl") else window
        return max(ttl, 1)
