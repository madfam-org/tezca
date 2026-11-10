"""
Tier-based DRF permission classes for feature gating.

Reads tiers.json and provides RequireTier (rank-based) and RequireFeature
(feature-flag-based) permission factories.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)

TIERS_FILE = Path(__file__).parent.parent / "tiers.json"
TIER_HIERARCHY = {
    "anon": 0,
    "free_member": 1,
    "community": 1,
    "free": 2,
    "essentials": 2,
    "academic": 3,
    "pro": 3,
    "premium": 3,
    "enterprise": 3,
    "institutional": 4,
    "madfam": 5,
    "internal": 5,
}

# Normalize legacy/internal tier names to canonical form
TIER_NORMALIZE = {
    "anon": "anon",
    "free_member": "free_member",
    "free": "essentials",
    "internal": "madfam",
    "enterprise": "academic",
    "premium": "academic",
    "pro": "academic",
}


# Tezca's own per-product claim. Janua mints `{product}_tier` from the
# product's catalog purchase (org `product_tiers` or a per-user grant) and
# `madfam` for MADFAM operator clients.
TEZCA_TIER_CLAIM = "tezca_tier"
TEZCA_ENTITLEMENT_PREFIX = "tezca:"

# A signed-in Janua user with no Tezca entitlement.
JANUA_FREE_TIER = "free_member"

# Values a Tezca entitlement claim may carry, mapped to the tier Tezca gates
# on. Anything else (another product's tier name, a typo, a non-string) is
# read as the free tier: the claim fails closed.
#
# - free/essentials/academic/institutional: the Tezca catalog ladder. The
#   catalog's `free` is the $0 signed-in tier, i.e. `free_member` here.
# - community: Tezca's own community plan (tezca_community).
# - pro/pro_plus/enterprise: unsellable or legacy catalog tiers, kept at the
#   `academic` level they already resolved to.
# - madfam/internal: MADFAM operators and service accounts.
JANUA_CLAIM_TIERS = {
    "free": JANUA_FREE_TIER,
    "free_member": JANUA_FREE_TIER,
    "community": "community",
    "essentials": "essentials",
    "academic": "academic",
    "institutional": "institutional",
    "pro": "academic",
    "pro_plus": "academic",
    "premium": "academic",
    "enterprise": "academic",
    "madfam": "madfam",
    "internal": "madfam",
}


def _map_claim_tier(value) -> str:
    if not isinstance(value, str):
        return JANUA_FREE_TIER
    return JANUA_CLAIM_TIERS.get(value.strip().lower(), JANUA_FREE_TIER)


def resolve_janua_tier(claims) -> str:
    """Resolve a Janua user's Tezca tier from Tezca's OWN entitlement claims.

    Order: the `tezca_tier` claim; else a `tezca:<tier>` entry in
    `madfam_entitled_products`; else the free tier. The generic `tier`/`plan`
    claims are never read: they summarize whatever product the org pays for,
    so reading them would hand Tezca access to buyers of other products.
    """
    if not isinstance(claims, dict):
        return JANUA_FREE_TIER

    own = claims.get(TEZCA_TIER_CLAIM)
    if own is not None:
        return _map_claim_tier(own)

    entitled = claims.get("madfam_entitled_products")
    if isinstance(entitled, list):
        for entry in entitled:
            if isinstance(entry, str) and entry.startswith(TEZCA_ENTITLEMENT_PREFIX):
                return _map_claim_tier(entry[len(TEZCA_ENTITLEMENT_PREFIX) :])

    return JANUA_FREE_TIER


@lru_cache(maxsize=1)
def load_tiers() -> dict:
    """Load tier definitions from tiers.json (cached)."""
    try:
        return json.loads(TIERS_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.error("Failed to load tiers.json: %s", exc)
        return {}


def normalize_tier(tier: str) -> str:
    """Normalize tier name to canonical form."""
    return TIER_NORMALIZE.get(tier, tier)


def has_tier(user_tier: str, required_tier: str) -> bool:
    """Check if user_tier meets or exceeds required_tier."""
    user_rank = TIER_HIERARCHY.get(normalize_tier(user_tier), 0)
    required_rank = TIER_HIERARCHY.get(normalize_tier(required_tier), 0)
    return user_rank >= required_rank


def check_feature(tier: str, feature: str) -> bool:
    """Check if a specific boolean feature is enabled for the tier."""
    tiers = load_tiers()
    tier_config = tiers.get(normalize_tier(tier), tiers.get("essentials", {}))
    return bool(tier_config.get(feature, False))


def get_tier_limits(tier: str) -> dict:
    """Get the full limits dict for a tier."""
    tiers = load_tiers()
    return tiers.get(normalize_tier(tier), tiers.get("essentials", {}))


def get_effective_tier(tier: str) -> str:
    """
    Apply deployment-mode caps to the resolved tier.

    In self-hosted mode (TEZCA_DEPLOYMENT=self-hosted), the effective tier
    is capped at 'academic' (rank 3). This means institutional features
    like webhooks, graph API, DOCX/EPUB export are only available on
    the managed platform.
    """
    deployment = getattr(settings, "TEZCA_DEPLOYMENT", "self-hosted")
    if deployment == "self-hosted":
        max_rank = TIER_HIERARCHY.get("academic", 3)
        tier_rank = TIER_HIERARCHY.get(normalize_tier(tier), 0)
        if tier_rank > max_rank:
            return "academic"
    return tier


class RequireTier(BasePermission):
    """
    DRF permission class that gates access based on user tier rank.

    Usage:
        @permission_classes([RequireTier.of("academic")])
        def premium_endpoint(request): ...
    """

    min_tier = "academic"

    @classmethod
    def of(cls, min_tier: str):
        """Factory method to create a permission class for a specific tier."""
        return type(
            f"RequireTier_{min_tier}",
            (cls,),
            {"min_tier": min_tier},
        )

    def has_permission(self, request, view):
        user_tier = getattr(request.user, "tier", "anon")
        if has_tier(user_tier, self.min_tier):
            return True

        # Set detail message for the 403 response
        checkout = settings.DHANAM_CHECKOUT_URL
        self.message = (
            f"This feature requires {self.min_tier} tier or above. "
            f"Upgrade at {checkout}?plan=tezca_{self.min_tier}&product=tezca"
        )
        return False


class RequireFeature(BasePermission):
    """
    DRF permission class that gates access based on a feature flag in tiers.json.

    Unlike RequireTier, this supports non-monotonic features (e.g. bulk_download
    available to community but not essentials).

    Usage:
        @permission_classes([RequireFeature.of("bulk_download")])
        def bulk_endpoint(request): ...
    """

    feature = ""

    @classmethod
    def of(cls, feature: str):
        """Factory method to create a permission class for a specific feature."""
        return type(
            f"RequireFeature_{feature}",
            (cls,),
            {"feature": feature},
        )

    def has_permission(self, request, view):
        tier = getattr(request.user, "tier", "anon")
        if check_feature(tier, self.feature):
            return True

        checkout = settings.DHANAM_CHECKOUT_URL
        self.message = (
            f"This feature requires a tier with {self.feature} access. "
            f"Upgrade at {checkout}?product=tezca"
        )
        return False
