"""Tests for tier-aware search page_size limits."""

from unittest.mock import MagicMock, patch

import pytest

from apps.api.tier_permissions import SEARCH_PAGE_SIZE_LIMITS


class TestSearchPageSizeLimits:
    """Test SEARCH_PAGE_SIZE_LIMITS constants."""

    def test_anon_capped_at_25(self):
        assert SEARCH_PAGE_SIZE_LIMITS["anon"] == 25

    def test_community_gets_1000(self):
        assert SEARCH_PAGE_SIZE_LIMITS["community"] == 1000

    def test_essentials_capped_at_50(self):
        assert SEARCH_PAGE_SIZE_LIMITS["essentials"] == 50

    def test_free_capped_at_50(self):
        assert SEARCH_PAGE_SIZE_LIMITS["free"] == 50

    def test_academic_gets_100(self):
        assert SEARCH_PAGE_SIZE_LIMITS["academic"] == 100

    def test_institutional_gets_1000(self):
        assert SEARCH_PAGE_SIZE_LIMITS["institutional"] == 1000

    def test_madfam_gets_1000(self):
        assert SEARCH_PAGE_SIZE_LIMITS["madfam"] == 1_000

    def test_unknown_tier_defaults_to_25(self):
        # dict.get with default
        assert SEARCH_PAGE_SIZE_LIMITS.get("nonexistent", 25) == 25
