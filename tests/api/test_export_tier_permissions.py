"""
Tests for apps.api.tier_permissions — single source of truth for tier config.

Covers:
  - normalize_export_tier maps known tiers correctly and passes through unknowns
  - has_tier_access respects the TIER_RANK hierarchy
  - Constant completeness (all expected tiers and formats present)
"""

import pytest

from apps.api.tier_permissions import (
    EXPORT_HOURLY_LIMITS,
    EXPORT_TIER_MAP,
    FORMAT_TIERS,
    RATE_LIMITS,
    SEARCH_PAGE_SIZE_LIMITS,
    TIER_RANK,
    has_tier_access,
    normalize_export_tier,
)


class TestNormalizeExportTier:
    @pytest.mark.parametrize(
        "input_tier,expected",
        [
            # Each canonical tier maps to itself
            ("anon", "anon"),
            ("community", "community"),
            ("essentials", "essentials"),
            ("academic", "academic"),
            ("institutional", "institutional"),
            ("madfam", "madfam"),
            # Legacy names
            ("pro", "academic"),
            ("premium", "academic"),
            ("enterprise", "academic"),
            ("free", "essentials"),
            ("internal", "madfam"),
            # Unknown tiers pass through unchanged
            ("unknown", "unknown"),
        ],
    )
    def test_mapping(self, input_tier, expected):
        assert normalize_export_tier(input_tier) == expected


class TestHasTierAccess:
    @pytest.mark.parametrize(
        "user_tier,required_tier,expected",
        [
            # Same tier always has access
            ("anon", "anon", True),
            ("community", "community", True),
            ("essentials", "essentials", True),
            ("academic", "academic", True),
            ("institutional", "institutional", True),
            ("madfam", "madfam", True),
            # Higher tier has access to lower
            ("community", "anon", True),
            ("essentials", "anon", True),
            ("essentials", "community", True),
            ("academic", "anon", True),
            ("academic", "community", True),
            ("academic", "essentials", True),
            ("institutional", "academic", True),
            ("madfam", "anon", True),
            ("madfam", "institutional", True),
            # Legacy aliases
            ("pro", "essentials", True),
            ("enterprise", "academic", True),
            ("internal", "madfam", True),
            # Lower tier denied access to higher
            ("anon", "community", False),
            ("anon", "essentials", False),
            ("anon", "academic", False),
            ("community", "essentials", False),
            ("essentials", "academic", False),
            ("academic", "institutional", False),
            # Unknown tier defaults to rank 0
            ("unknown", "community", False),
        ],
    )
    def test_access(self, user_tier, required_tier, expected):
        assert has_tier_access(user_tier, required_tier) == expected


class TestConstants:
    def test_all_export_formats_present(self):
        expected_formats = {"txt", "pdf", "latex", "docx", "epub", "json"}
        assert set(FORMAT_TIERS.keys()) == expected_formats

    def test_format_tier_values(self):
        assert FORMAT_TIERS["pdf"] == "community"
        assert FORMAT_TIERS["json"] == "community"
        assert FORMAT_TIERS["latex"] == "academic"
        assert FORMAT_TIERS["docx"] == "institutional"
        assert FORMAT_TIERS["epub"] == "institutional"

    def test_all_rate_limit_tiers_present(self):
        # Canonical tiers + legacy aliases
        expected = {
            "anon",
            "free",
            "essentials",
            "community",
            "academic",
            "pro",
            "premium",
            "enterprise",
            "institutional",
            "madfam",
            "internal",
        }
        assert set(RATE_LIMITS.keys()) == expected

    def test_rate_limits_are_tuples(self):
        for tier, limits in RATE_LIMITS.items():
            assert isinstance(limits, tuple), f"{tier} limits should be a tuple"
            assert len(limits) == 2, f"{tier} should have (per_minute, per_hour)"

    def test_export_hourly_limits_cover_export_tiers(self):
        # Canonical tiers + legacy aliases
        expected = {
            "anon",
            "community",
            "essentials",
            "academic",
            "institutional",
            "madfam",
            "free",
            "pro",
            "premium",
            "enterprise",
            "internal",
        }
        assert set(EXPORT_HOURLY_LIMITS.keys()) == expected

    def test_export_hourly_limit_values(self):
        assert EXPORT_HOURLY_LIMITS["community"] == 1000
        assert EXPORT_HOURLY_LIMITS["essentials"] == 30
        assert EXPORT_HOURLY_LIMITS["academic"] == 60
        assert EXPORT_HOURLY_LIMITS["institutional"] == 200
        assert EXPORT_HOURLY_LIMITS["madfam"] == 200

    def test_tier_rank_ordering(self):
        assert TIER_RANK["anon"] < TIER_RANK["community"]
        assert TIER_RANK["community"] < TIER_RANK["essentials"]
        assert TIER_RANK["essentials"] < TIER_RANK["academic"]
        assert TIER_RANK["academic"] < TIER_RANK["institutional"]
        assert TIER_RANK["institutional"] < TIER_RANK["madfam"]

    def test_search_page_size_limits(self):
        assert SEARCH_PAGE_SIZE_LIMITS["anon"] == 25
        assert SEARCH_PAGE_SIZE_LIMITS["community"] == 1000
        assert SEARCH_PAGE_SIZE_LIMITS["essentials"] == 50
        assert SEARCH_PAGE_SIZE_LIMITS["academic"] == 100
        assert SEARCH_PAGE_SIZE_LIMITS["institutional"] == 1000
        assert SEARCH_PAGE_SIZE_LIMITS["madfam"] == 1000
