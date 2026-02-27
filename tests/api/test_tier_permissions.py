"""Tests for tier-based permission middleware."""

import json
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.api.middleware.tier_permissions import (
    TIER_HIERARCHY,
    TIER_NORMALIZE,
    RequireTier,
    check_feature,
    get_tier_limits,
    has_tier,
    load_tiers,
    normalize_tier,
)


class TestLoadTiers:
    """Tests for load_tiers() — reads and caches tiers.json."""

    def setup_method(self):
        # Clear lru_cache between tests
        load_tiers.cache_clear()

    def test_loads_tiers_from_json(self):
        tiers = load_tiers()
        assert isinstance(tiers, dict)
        assert "essentials" in tiers
        assert "pro" in tiers
        assert "madfam" in tiers

    def test_essentials_tier_has_expected_keys(self):
        tiers = load_tiers()
        essentials = tiers["essentials"]
        assert "search_results_per_query" in essentials
        assert "api_requests_per_day" in essentials
        assert "export_formats" in essentials
        assert "search_analytics" in essentials

    def test_pro_tier_has_unlimited_api_requests(self):
        tiers = load_tiers()
        assert tiers["pro"]["api_requests_per_day"] == -1

    def test_returns_empty_dict_on_missing_file(self):
        load_tiers.cache_clear()
        with patch(
            "apps.api.middleware.tier_permissions.TIERS_FILE"
        ) as mock_path:
            mock_path.read_text.side_effect = FileNotFoundError("missing")
            result = load_tiers()
            assert result == {}

    def test_returns_empty_dict_on_invalid_json(self):
        load_tiers.cache_clear()
        with patch(
            "apps.api.middleware.tier_permissions.TIERS_FILE"
        ) as mock_path:
            mock_path.read_text.return_value = "not json {"
            result = load_tiers()
            assert result == {}

    def test_result_is_cached(self):
        load_tiers.cache_clear()
        first = load_tiers()
        second = load_tiers()
        assert first is second  # same object reference (cached)


class TestNormalizeTier:
    """Tests for normalize_tier() — maps legacy names to canonical tiers."""

    def test_free_maps_to_essentials(self):
        assert normalize_tier("free") == "essentials"

    def test_premium_maps_to_pro(self):
        assert normalize_tier("premium") == "pro"

    def test_internal_maps_to_madfam(self):
        assert normalize_tier("internal") == "madfam"

    def test_enterprise_maps_to_madfam(self):
        assert normalize_tier("enterprise") == "madfam"

    def test_anon_maps_to_anon(self):
        assert normalize_tier("anon") == "anon"

    def test_canonical_names_pass_through(self):
        assert normalize_tier("essentials") == "essentials"
        assert normalize_tier("pro") == "pro"
        assert normalize_tier("madfam") == "madfam"

    def test_unknown_tier_passes_through(self):
        assert normalize_tier("unknown_tier") == "unknown_tier"


class TestHasTier:
    """Tests for has_tier() — checks if user tier meets required tier."""

    def test_anon_below_essentials(self):
        assert has_tier("anon", "essentials") is False

    def test_essentials_meets_essentials(self):
        assert has_tier("essentials", "essentials") is True

    def test_pro_meets_essentials(self):
        assert has_tier("pro", "essentials") is True

    def test_essentials_below_pro(self):
        assert has_tier("essentials", "pro") is False

    def test_madfam_meets_all(self):
        assert has_tier("madfam", "anon") is True
        assert has_tier("madfam", "essentials") is True
        assert has_tier("madfam", "pro") is True
        assert has_tier("madfam", "madfam") is True

    def test_anon_only_meets_anon(self):
        assert has_tier("anon", "anon") is True
        assert has_tier("anon", "essentials") is False
        assert has_tier("anon", "pro") is False
        assert has_tier("anon", "madfam") is False

    def test_legacy_tier_names_normalized(self):
        # "free" normalizes to "essentials" (rank 1)
        assert has_tier("free", "essentials") is True
        # "premium" normalizes to "pro" (rank 2)
        assert has_tier("premium", "pro") is True
        # "internal" normalizes to "madfam" (rank 3)
        assert has_tier("internal", "madfam") is True

    def test_free_and_essentials_equivalent(self):
        # Both map to rank 1
        assert has_tier("free", "essentials") is True
        assert has_tier("essentials", "free") is True

    def test_unknown_tier_defaults_to_rank_zero(self):
        assert has_tier("nonexistent", "essentials") is False
        assert has_tier("nonexistent", "anon") is True  # 0 >= 0


class TestCheckFeature:
    """Tests for check_feature() — checks boolean feature flags per tier."""

    def setup_method(self):
        load_tiers.cache_clear()

    def test_essentials_has_newsletter_access(self):
        assert check_feature("essentials", "newsletter_access") is True

    def test_essentials_no_search_analytics(self):
        assert check_feature("essentials", "search_analytics") is False

    def test_pro_has_search_analytics(self):
        assert check_feature("pro", "search_analytics") is True

    def test_pro_has_api_key_access(self):
        assert check_feature("pro", "api_key_access") is True

    def test_essentials_no_api_key_access(self):
        assert check_feature("essentials", "api_key_access") is False

    def test_madfam_has_premium_export(self):
        assert check_feature("madfam", "premium_export") is True

    def test_legacy_tier_name_normalizes(self):
        # "free" -> "essentials"
        assert check_feature("free", "newsletter_access") is True
        assert check_feature("free", "search_analytics") is False

    def test_unknown_feature_returns_false(self):
        assert check_feature("pro", "nonexistent_feature") is False

    def test_unknown_tier_falls_back_to_essentials(self):
        assert check_feature("nonexistent", "newsletter_access") is True
        assert check_feature("nonexistent", "search_analytics") is False


class TestGetTierLimits:
    """Tests for get_tier_limits() — returns the full limits dict for a tier."""

    def setup_method(self):
        load_tiers.cache_clear()

    def test_essentials_limits(self):
        limits = get_tier_limits("essentials")
        assert limits["search_results_per_query"] == 25
        assert limits["api_requests_per_day"] == 500
        assert limits["export_formats"] == ["json"]

    def test_pro_limits_unlimited(self):
        limits = get_tier_limits("pro")
        assert limits["search_results_per_query"] == -1
        assert limits["api_requests_per_day"] == -1
        assert "csv" in limits["export_formats"]

    def test_madfam_has_xml_export(self):
        limits = get_tier_limits("madfam")
        assert "xml" in limits["export_formats"]

    def test_legacy_name_returns_canonical_limits(self):
        free_limits = get_tier_limits("free")
        essentials_limits = get_tier_limits("essentials")
        assert free_limits == essentials_limits

    def test_unknown_tier_falls_back_to_essentials(self):
        unknown = get_tier_limits("nonexistent")
        essentials = get_tier_limits("essentials")
        assert unknown == essentials


class TestRequireTier:
    """Tests for RequireTier DRF permission class."""

    def setup_method(self):
        self.factory = APIRequestFactory()

    def _make_request_with_tier(self, tier):
        request = self.factory.get("/api/v1/test/")
        user = MagicMock()
        user.tier = tier
        request.user = user
        return request

    def test_of_factory_creates_permission_class(self):
        perm_class = RequireTier.of("pro")
        assert perm_class.min_tier == "pro"
        assert perm_class.__name__ == "RequireTier_pro"
        assert issubclass(perm_class, RequireTier)

    def test_of_factory_different_tiers(self):
        essentials_perm = RequireTier.of("essentials")
        madfam_perm = RequireTier.of("madfam")
        assert essentials_perm.min_tier == "essentials"
        assert madfam_perm.min_tier == "madfam"
        assert essentials_perm is not madfam_perm

    def test_pro_user_passes_pro_gate(self):
        perm = RequireTier.of("pro")()
        request = self._make_request_with_tier("pro")
        assert perm.has_permission(request, None) is True

    def test_madfam_user_passes_pro_gate(self):
        perm = RequireTier.of("pro")()
        request = self._make_request_with_tier("madfam")
        assert perm.has_permission(request, None) is True

    def test_essentials_user_fails_pro_gate(self):
        perm = RequireTier.of("pro")()
        request = self._make_request_with_tier("essentials")
        assert perm.has_permission(request, None) is False

    def test_anon_user_fails_pro_gate(self):
        perm = RequireTier.of("pro")()
        request = self._make_request_with_tier("anon")
        assert perm.has_permission(request, None) is False

    def test_essentials_user_passes_essentials_gate(self):
        perm = RequireTier.of("essentials")()
        request = self._make_request_with_tier("essentials")
        assert perm.has_permission(request, None) is True

    def test_denial_sets_upgrade_message(self):
        perm = RequireTier.of("pro")()
        request = self._make_request_with_tier("essentials")
        perm.has_permission(request, None)
        assert "pro tier or above" in perm.message
        assert "dhanam.madfam.io/checkout" in perm.message

    def test_default_min_tier_is_pro(self):
        perm = RequireTier()
        assert perm.min_tier == "pro"

    def test_missing_tier_attribute_defaults_to_anon(self):
        perm = RequireTier.of("essentials")()
        request = self.factory.get("/api/v1/test/")
        request.user = MagicMock(spec=[])  # no .tier attribute
        assert perm.has_permission(request, None) is False
