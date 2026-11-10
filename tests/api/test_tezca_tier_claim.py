"""Tezca gates Janua users ONLY on its own entitlement claims.

The generic `tier`/`plan` claims summarize whatever product an org pays for,
so a buyer of another product must never read as a paying Tezca user.
"""

from unittest.mock import patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.api.middleware.combined_auth import CombinedAuthentication
from apps.api.middleware.janua_auth import JanuaUser
from apps.api.middleware.tier_permissions import JANUA_FREE_TIER, resolve_janua_tier


class TestResolveJanuaTier:
    @pytest.mark.parametrize(
        "claims",
        [
            {"tier": "pro"},
            {"tier": "essentials"},
            {"tier": "premium", "plan": "enterprise"},
            {"plan": "pro"},
            {"tier": "community"},
            {"tier": "madfam"},
            {"tier": "pro", "karafiel_tier": "pro", "dhanam_tier": "premium"},
            {"tier": "pro", "madfam_entitled_products": ["karafiel:pro"]},
        ],
    )
    def test_other_product_tier_without_tezca_claim_is_free(self, claims):
        assert resolve_janua_tier(claims) == JANUA_FREE_TIER

    def test_no_claims_is_free(self):
        assert resolve_janua_tier({}) == JANUA_FREE_TIER
        assert resolve_janua_tier(None) == JANUA_FREE_TIER

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("free", "free_member"),
            ("essentials", "essentials"),
            ("academic", "academic"),
            ("institutional", "institutional"),
            ("community", "community"),
            ("pro", "academic"),
            ("pro_plus", "academic"),
            ("enterprise", "academic"),
            ("ACADEMIC", "academic"),
        ],
    )
    def test_tezca_tier_maps_catalog_tiers(self, value, expected):
        assert (
            resolve_janua_tier({"tezca_tier": value, "tier": "community"}) == expected
        )

    def test_tezca_tier_wins_over_generic_tier(self):
        assert resolve_janua_tier({"tezca_tier": "essentials", "tier": "premium"}) == (
            "essentials"
        )

    def test_madfam_operator_keeps_operator_tier(self):
        assert resolve_janua_tier({"tezca_tier": "madfam"}) == "madfam"
        assert resolve_janua_tier({"tezca_tier": "internal"}) == "madfam"

    @pytest.mark.parametrize(
        "value", ["", "admin", "platinum", "tezca:academic", 3, ["academic"], {"a": 1}]
    )
    def test_malformed_or_unknown_tezca_tier_fails_closed(self, value):
        # Even with a generous generic tier and a tezca entitlement, a present
        # but unusable tezca_tier is the free tier.
        claims = {
            "tezca_tier": value,
            "tier": "premium",
            "madfam_entitled_products": ["tezca:institutional"],
        }
        assert resolve_janua_tier(claims) == JANUA_FREE_TIER

    def test_entitled_products_used_when_tezca_tier_absent(self):
        claims = {
            "tier": "community",
            "madfam_entitled_products": ["dhanam:pro", "tezca:academic"],
        }
        assert resolve_janua_tier(claims) == "academic"

    @pytest.mark.parametrize(
        "entitled",
        [
            ["tezca:admin"],
            ["tezca:"],
            ["tezcaacademic"],
            "tezca:academic",
            [None, 7],
        ],
    )
    def test_unusable_entitled_products_fail_closed(self, entitled):
        claims = {"tier": "pro", "madfam_entitled_products": entitled}
        assert resolve_janua_tier(claims) == JANUA_FREE_TIER


class TestCombinedAuthenticationJanuaTier:
    @pytest.fixture(autouse=True)
    def _managed(self, settings):
        settings.TEZCA_DEPLOYMENT = "managed"

    def _authenticate(self, claims):
        request = APIRequestFactory().get(
            "/api/v1/laws/", HTTP_AUTHORIZATION="Bearer fake.jwt.token"
        )
        user = JanuaUser({"sub": "user-1", **claims})
        with patch(
            "apps.api.middleware.combined_auth.JanuaJWTAuthentication.authenticate",
            return_value=(user, "fake.jwt.token"),
        ):
            result = CombinedAuthentication().authenticate(request)
        assert result is not None
        return result[0]

    def test_other_product_pro_buyer_is_free(self):
        assert self._authenticate({"tier": "pro"}).tier == "free_member"

    def test_janua_default_community_tier_is_not_tezca_community(self):
        assert self._authenticate({"tier": "community"}).tier == "free_member"

    def test_no_claims_is_free(self):
        assert self._authenticate({}).tier == "free_member"

    def test_tezca_academic(self):
        assert self._authenticate(
            {"tezca_tier": "academic", "tier": "community"}
        ).tier == ("academic")

    def test_madfam_service_account_keeps_operator_access(self):
        user = self._authenticate({"tezca_tier": "madfam", "tier": "community"})
        assert user.tier == "madfam"

    def test_unknown_tezca_tier_is_free(self):
        assert self._authenticate(
            {"tezca_tier": "platinum", "tier": "premium"}
        ).tier == ("free_member")


def test_self_hosted_cap_still_applies_to_madfam(settings):
    settings.TEZCA_DEPLOYMENT = "self-hosted"
    request = APIRequestFactory().get(
        "/api/v1/laws/", HTTP_AUTHORIZATION="Bearer x.y.z"
    )
    user = JanuaUser({"sub": "svc", "tezca_tier": "madfam"})
    with patch(
        "apps.api.middleware.combined_auth.JanuaJWTAuthentication.authenticate",
        return_value=(user, "x.y.z"),
    ):
        authed, _ = CombinedAuthentication().authenticate(request)
    assert authed.tier == "academic"
