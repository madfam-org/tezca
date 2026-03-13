"""Tests for per-key rate limit override in TieredRateThrottle."""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.api.tier_throttles import TieredRateThrottle


class TestPerKeyRateOverride:
    """Test that APIKey.rate_limit_per_hour overrides tier default."""

    def setup_method(self):
        self.factory = APIRequestFactory()
        self.throttle = TieredRateThrottle()

    def _make_request(self, tier="pro", rate_limit_per_hour=None):
        request = self.factory.get("/api/v1/test/")
        user = MagicMock()
        user.is_authenticated = True
        user.tier = tier
        user.api_key_prefix = "testkey1"
        user.rate_limit_per_hour = rate_limit_per_hour
        request.user = user
        return request

    def test_override_applies_custom_hourly_limit(self):
        request = self._make_request(tier="pro", rate_limit_per_hour=5000)
        limits = self.throttle._get_limits(request, "pro")
        # per-minute stays at tier default (60), hourly overridden to 5000
        assert limits == (60, 5000)

    def test_none_falls_back_to_tier_default(self):
        request = self._make_request(tier="pro", rate_limit_per_hour=None)
        limits = self.throttle._get_limits(request, "pro")
        assert limits == (60, 2_000)

    def test_zero_falls_back_to_tier_default(self):
        # 0 is falsy, so it should fall back
        request = self._make_request(tier="pro", rate_limit_per_hour=0)
        limits = self.throttle._get_limits(request, "pro")
        assert limits == (60, 2_000)

    def test_anon_request_uses_anon_limits(self):
        request = self.factory.get("/api/v1/test/")
        request.user = MagicMock(spec=[])  # no is_authenticated
        limits = self.throttle._get_limits(request, "anon")
        assert limits == (10, 100)

    def test_override_with_community_tier(self):
        request = self._make_request(tier="community", rate_limit_per_hour=3000)
        limits = self.throttle._get_limits(request, "community")
        assert limits == (60, 3000)

    def test_override_capped_at_max(self):
        """Custom rate_limit_per_hour cannot exceed MAX_RATE_LIMIT_PER_HOUR."""
        request = self._make_request(tier="pro", rate_limit_per_hour=999_999)
        limits = self.throttle._get_limits(request, "pro")
        assert limits == (60, 100_000)

    def test_override_at_max_boundary(self):
        """Exactly MAX_RATE_LIMIT_PER_HOUR passes through unchanged."""
        request = self._make_request(tier="pro", rate_limit_per_hour=100_000)
        limits = self.throttle._get_limits(request, "pro")
        assert limits == (60, 100_000)

    def test_override_below_max_not_capped(self):
        """Values below the cap pass through unchanged."""
        request = self._make_request(tier="pro", rate_limit_per_hour=50_000)
        limits = self.throttle._get_limits(request, "pro")
        assert limits == (60, 50_000)
