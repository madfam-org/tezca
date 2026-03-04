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
    TIER_RANK,
    has_tier_access,
    normalize_export_tier,
)


class TestNormalizeExportTier:
    @pytest.mark.parametrize(
        "input_tier,expected",
        [
            ("internal", "premium"),
            ("pro", "premium"),
            ("enterprise", "premium"),
            ("madfam", "premium"),
            ("essentials", "free"),
            # Pass-through for already-normalized tiers
            ("anon", "anon"),
            ("free", "free"),
            ("premium", "premium"),
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
            ("free", "free", True),
            ("premium", "premium", True),
            ("internal", "internal", True),
            # Higher tier has access to lower
            ("free", "anon", True),
            ("premium", "anon", True),
            ("internal", "anon", True),
            ("pro", "free", True),
            ("enterprise", "premium", True),
            # Lower tier denied access to higher
            ("anon", "free", False),
            ("anon", "premium", False),
            ("free", "premium", False),
            # Unknown tier defaults to rank 0
            ("unknown", "free", False),
        ],
    )
    def test_access(self, user_tier, required_tier, expected):
        assert has_tier_access(user_tier, required_tier) == expected


class TestConstants:
    def test_all_export_formats_present(self):
        expected_formats = {"txt", "pdf", "latex", "docx", "epub", "json"}
        assert set(FORMAT_TIERS.keys()) == expected_formats

    def test_all_rate_limit_tiers_present(self):
        expected = {
            "anon",
            "free",
            "essentials",
            "community",
            "pro",
            "enterprise",
            "madfam",
            "internal",
        }
        assert set(RATE_LIMITS.keys()) == expected

    def test_rate_limits_are_tuples(self):
        for tier, limits in RATE_LIMITS.items():
            assert isinstance(limits, tuple), f"{tier} limits should be a tuple"
            assert len(limits) == 2, f"{tier} should have (per_minute, per_hour)"

    def test_export_hourly_limits_cover_export_tiers(self):
        export_tiers = {"anon", "free", "premium"}
        assert set(EXPORT_HOURLY_LIMITS.keys()) == export_tiers

    def test_tier_rank_ordering(self):
        assert TIER_RANK["anon"] < TIER_RANK["free"]
        assert TIER_RANK["free"] < TIER_RANK["premium"]
        assert TIER_RANK["premium"] < TIER_RANK["internal"]
