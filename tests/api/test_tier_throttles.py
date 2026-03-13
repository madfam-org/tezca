"""Tests for TieredRateThrottle — identity resolution, tier detection, rate limiting.

Covers:
  - _get_tier: authenticated vs anonymous users
  - _get_identity: API key, JWT user, anonymous IP
  - _get_limits: tier defaults, custom overrides, cap enforcement
  - _check_and_increment: counter creation, limit checking (mocked cache)
  - _get_client_ip: X-Forwarded-For handling
  - allow_request: integration test of the full throttle flow
  - wait(): returns wait time
"""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.api.tier_throttles import TieredRateThrottle, _get_client_ip


class TestGetClientIP:
    """Tests for _get_client_ip helper."""

    def test_uses_x_forwarded_for_first_ip(self):
        factory = APIRequestFactory()
        request = factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.5, 10.0.0.1"
        assert _get_client_ip(request) == "203.0.113.5"

    def test_uses_remote_addr_when_no_xff(self):
        factory = APIRequestFactory()
        request = factory.get("/")
        request.META.pop("HTTP_X_FORWARDED_FOR", None)
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        assert _get_client_ip(request) == "192.168.1.1"

    def test_defaults_to_localhost(self):
        factory = APIRequestFactory()
        request = factory.get("/")
        request.META.pop("HTTP_X_FORWARDED_FOR", None)
        request.META.pop("REMOTE_ADDR", None)
        ip = _get_client_ip(request)
        assert ip == "127.0.0.1"

    def test_strips_whitespace_from_xff(self):
        factory = APIRequestFactory()
        request = factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "  203.0.113.5 , 10.0.0.1"
        assert _get_client_ip(request) == "203.0.113.5"


class TestGetTier:
    """Tests for TieredRateThrottle._get_tier()."""

    def setup_method(self):
        self.factory = APIRequestFactory()
        self.throttle = TieredRateThrottle()

    def test_authenticated_user_returns_user_tier(self):
        request = self.factory.get("/")
        user = MagicMock()
        user.is_authenticated = True
        user.tier = "community"
        request.user = user

        assert self.throttle._get_tier(request) == "community"

    def test_unauthenticated_returns_anon(self):
        request = self.factory.get("/")
        request.user = MagicMock(is_authenticated=False)

        assert self.throttle._get_tier(request) == "anon"

    def test_no_user_returns_anon(self):
        request = self.factory.get("/")
        request.user = None

        assert self.throttle._get_tier(request) == "anon"

    def test_authenticated_with_pro_tier(self):
        request = self.factory.get("/")
        user = MagicMock()
        user.is_authenticated = True
        user.tier = "pro"
        request.user = user

        assert self.throttle._get_tier(request) == "pro"

    def test_authenticated_with_madfam_tier(self):
        request = self.factory.get("/")
        user = MagicMock()
        user.is_authenticated = True
        user.tier = "madfam"
        request.user = user

        assert self.throttle._get_tier(request) == "madfam"


class TestGetIdentity:
    """Tests for TieredRateThrottle._get_identity()."""

    def setup_method(self):
        self.factory = APIRequestFactory()
        self.throttle = TieredRateThrottle()

    def test_api_key_user_identity(self):
        request = self.factory.get("/")
        user = MagicMock()
        user.is_authenticated = True
        user.api_key_prefix = "abc12345"
        request.user = user

        identity = self.throttle._get_identity(request)
        assert identity == "key:abc12345"

    def test_jwt_user_identity(self):
        request = self.factory.get("/")
        user = MagicMock()
        user.is_authenticated = True
        user.api_key_prefix = ""
        user.id = "user-uuid-123"
        request.user = user

        identity = self.throttle._get_identity(request)
        assert identity == "user:user-uuid-123"

    def test_anonymous_identity_uses_ip(self):
        request = self.factory.get("/")
        request.user = MagicMock(is_authenticated=False)
        request.META["REMOTE_ADDR"] = "10.0.0.42"

        identity = self.throttle._get_identity(request)
        assert identity == "ip:10.0.0.42"

    def test_anonymous_with_xff(self):
        request = self.factory.get("/")
        request.user = MagicMock(is_authenticated=False)
        request.META["HTTP_X_FORWARDED_FOR"] = "198.51.100.1"

        identity = self.throttle._get_identity(request)
        assert identity == "ip:198.51.100.1"


class TestGetLimits:
    """Tests for TieredRateThrottle._get_limits()."""

    def setup_method(self):
        self.factory = APIRequestFactory()
        self.throttle = TieredRateThrottle()

    def _make_request(self, tier="pro", rate_limit_per_hour=None):
        request = self.factory.get("/")
        user = MagicMock()
        user.is_authenticated = True
        user.tier = tier
        user.api_key_prefix = "testkey1"
        user.rate_limit_per_hour = rate_limit_per_hour
        request.user = user
        return request

    def test_anon_limits(self):
        request = self.factory.get("/")
        request.user = MagicMock(spec=[])
        limits = self.throttle._get_limits(request, "anon")
        assert limits == (10, 100)

    def test_essentials_limits(self):
        request = self._make_request(tier="essentials")
        limits = self.throttle._get_limits(request, "essentials")
        assert limits == (30, 500)

    def test_community_limits(self):
        request = self._make_request(tier="community")
        limits = self.throttle._get_limits(request, "community")
        assert limits == (60, 2_000)

    def test_pro_limits(self):
        request = self._make_request(tier="pro")
        limits = self.throttle._get_limits(request, "pro")
        assert limits == (60, 2_000)

    def test_madfam_limits(self):
        request = self._make_request(tier="madfam")
        limits = self.throttle._get_limits(request, "madfam")
        assert isinstance(limits, tuple)
        assert len(limits) == 2

    def test_custom_hourly_override(self):
        request = self._make_request(tier="pro", rate_limit_per_hour=5000)
        limits = self.throttle._get_limits(request, "pro")
        assert limits == (60, 5000)

    def test_custom_override_capped_at_max(self):
        request = self._make_request(tier="pro", rate_limit_per_hour=999_999)
        limits = self.throttle._get_limits(request, "pro")
        assert limits == (60, 100_000)

    def test_none_override_uses_default(self):
        request = self._make_request(tier="pro", rate_limit_per_hour=None)
        limits = self.throttle._get_limits(request, "pro")
        assert limits == (60, 2_000)

    def test_zero_override_uses_default(self):
        request = self._make_request(tier="pro", rate_limit_per_hour=0)
        limits = self.throttle._get_limits(request, "pro")
        assert limits == (60, 2_000)

    def test_unknown_tier_falls_back_to_anon(self):
        request = self._make_request(tier="unknown_tier")
        limits = self.throttle._get_limits(request, "unknown_tier")
        assert limits == (10, 100)

    def test_negative_override_uses_default(self):
        request = self._make_request(tier="pro", rate_limit_per_hour=-5)
        limits = self.throttle._get_limits(request, "pro")
        assert limits == (60, 2_000)

    def test_override_at_max_boundary(self):
        request = self._make_request(tier="pro", rate_limit_per_hour=100_000)
        limits = self.throttle._get_limits(request, "pro")
        assert limits == (60, 100_000)


class TestCheckAndIncrement:
    """Tests for TieredRateThrottle._check_and_increment() with mocked cache.

    Redis is not available in test, so we mock django.core.cache.cache.
    """

    def setup_method(self):
        self.throttle = TieredRateThrottle()

    @patch("apps.api.tier_throttles.cache")
    def test_first_request_creates_key(self, mock_cache):
        """When key doesn't exist, incr raises ValueError, key is set to 1."""
        mock_cache.incr.side_effect = ValueError("key not found")

        result = self.throttle._check_and_increment("test:key", 10, 60)

        assert result is True
        mock_cache.set.assert_called_once_with("test:key", 1, 60)

    @patch("apps.api.tier_throttles.cache")
    def test_within_limit_allowed(self, mock_cache):
        """When count is within limit, returns True."""
        mock_cache.incr.return_value = 5

        result = self.throttle._check_and_increment("test:key", 10, 60)

        assert result is True

    @patch("apps.api.tier_throttles.cache")
    def test_at_limit_allowed(self, mock_cache):
        """When count equals limit, returns True."""
        mock_cache.incr.return_value = 10

        result = self.throttle._check_and_increment("test:key", 10, 60)

        assert result is True

    @patch("apps.api.tier_throttles.cache")
    def test_over_limit_denied(self, mock_cache):
        """When count exceeds limit, returns False."""
        mock_cache.incr.return_value = 11

        result = self.throttle._check_and_increment("test:key", 10, 60)

        assert result is False

    @patch("apps.api.tier_throttles.cache")
    def test_high_volume_denied(self, mock_cache):
        """Much over limit is denied."""
        mock_cache.incr.return_value = 1000

        result = self.throttle._check_and_increment("test:key", 10, 60)

        assert result is False


class TestWait:
    """Tests for TieredRateThrottle.wait()."""

    def test_returns_default_wait(self):
        throttle = TieredRateThrottle()
        assert throttle.wait() == 60

    def test_returns_custom_wait(self):
        throttle = TieredRateThrottle()
        throttle.wait_seconds = 30
        assert throttle.wait() == 30

    def test_returns_zero_wait_not_negative(self):
        throttle = TieredRateThrottle()
        throttle.wait_seconds = 0
        assert throttle.wait() == 0


class TestAllowRequestIntegration:
    """Integration tests for the full allow_request flow with mocked cache."""

    def setup_method(self):
        self.factory = APIRequestFactory()
        self.throttle = TieredRateThrottle()

    @patch("apps.api.tier_throttles.cache")
    def test_anonymous_request_allowed(self, mock_cache):
        """First anonymous request is allowed."""
        mock_cache.incr.side_effect = ValueError("new key")

        request = self.factory.get("/")
        request.user = MagicMock(is_authenticated=False)
        request.META["REMOTE_ADDR"] = "192.0.2.100"

        result = self.throttle.allow_request(request, None)
        assert result is True

    @patch("apps.api.tier_throttles.cache")
    def test_authenticated_request_allowed(self, mock_cache):
        """First authenticated request is allowed."""
        mock_cache.incr.side_effect = ValueError("new key")

        request = self.factory.get("/")
        user = MagicMock()
        user.is_authenticated = True
        user.tier = "pro"
        user.api_key_prefix = "inttest1"
        user.rate_limit_per_hour = None
        request.user = user

        result = self.throttle.allow_request(request, None)
        assert result is True

    @patch("apps.api.tier_throttles.cache")
    def test_rate_limited_returns_false(self, mock_cache):
        """Request over per-minute limit returns False."""
        # First incr (minute check) returns over-limit
        mock_cache.incr.return_value = 11
        mock_cache.ttl.return_value = 30  # mock TTL for _get_wait

        request = self.factory.get("/")
        request.user = MagicMock(is_authenticated=False)
        request.META["REMOTE_ADDR"] = "192.0.2.200"

        result = self.throttle.allow_request(request, None)
        # anon limit is 10/min, count=11 > 10
        assert result is False

    @patch("apps.api.tier_throttles.cache")
    def test_hourly_limit_exceeded(self, mock_cache):
        """Request under per-minute but over per-hour limit returns False."""
        # First call (minute check): under limit
        # Second call (hour check): over limit
        mock_cache.incr.side_effect = [
            5,
            101,
        ]  # 5 < 10 (minute ok), 101 > 100 (hour denied)

        mock_cache.ttl.return_value = 30  # mock TTL for _get_wait
        request = self.factory.get("/")
        request.user = MagicMock(is_authenticated=False)
        request.META["REMOTE_ADDR"] = "192.0.2.201"

        result = self.throttle.allow_request(request, None)
        assert result is False
