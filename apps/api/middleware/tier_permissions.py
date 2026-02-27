"""
Tier-based DRF permission classes for feature gating.

Reads tiers.json and provides a @require_tier() permission factory.
Only gates features at "pro" and above — essentials-level features are
identical to the open-source self-hosted build (no gating).
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)

TIERS_FILE = Path(__file__).parent.parent / "tiers.json"
TIER_HIERARCHY = {"anon": 0, "free": 1, "essentials": 1, "pro": 2, "madfam": 3}

# Normalize legacy/internal tier names
TIER_NORMALIZE = {
    "anon": "anon",
    "free": "essentials",
    "internal": "madfam",
    "enterprise": "madfam",
    "premium": "pro",
}


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


class RequireTier(BasePermission):
    """
    DRF permission class that gates access based on user tier.

    Usage:
        @permission_classes([RequireTier.of("pro")])
        def premium_endpoint(request): ...
    """

    min_tier = "pro"

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
        self.message = (
            f"This feature requires {self.min_tier} tier or above. "
            f"Upgrade at https://dhanam.madfam.io/checkout?plan=tezca_{self.min_tier}&product=tezca"
        )
        return False
