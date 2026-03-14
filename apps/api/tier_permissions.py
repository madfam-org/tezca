"""
Single source of truth for tier naming, ranking, and format access.

All tier-dependent logic should import from this module.
Feature-gating functions are re-exported from middleware.tier_permissions
so callers can import everything from one place.
"""

# Canonical tier names
TIER_ANON = "anon"
TIER_COMMUNITY = "community"
TIER_ESSENTIALS = "essentials"
TIER_ACADEMIC = "academic"
TIER_INSTITUTIONAL = "institutional"
TIER_MADFAM = "madfam"

# Tier ranking for access control (higher = more access)
# Legacy aliases map to their canonical equivalents
TIER_RANK = {
    "anon": 0,
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

# Export format access by minimum tier
FORMAT_TIERS = {
    "txt": "anon",
    "pdf": "community",
    "json": "community",
    "latex": "academic",
    "docx": "institutional",
    "epub": "institutional",
}

# Export tier normalization — each tier maps to itself (no more 3-level collapsing)
# Legacy aliases redirect to new canonical names
EXPORT_TIER_MAP = {
    "anon": "anon",
    "community": "community",
    "essentials": "essentials",
    "academic": "academic",
    "institutional": "institutional",
    "madfam": "madfam",
    # Legacy aliases
    "free": "essentials",
    "internal": "madfam",
    "pro": "academic",
    "premium": "academic",
    "enterprise": "academic",
}

# Export hourly limits
EXPORT_HOURLY_LIMITS = {
    "anon": 10,
    "community": 1_000,
    "essentials": 30,
    "academic": 60,
    "institutional": 200,
    "madfam": 200,
    # Legacy aliases
    "free": 30,
    "pro": 60,
    "premium": 60,
    "enterprise": 200,
    "internal": 200,
}

# Rate limiting (per minute, per hour)
RATE_LIMITS = {
    "anon": (10, 100),
    "community": (1_000, 100_000),
    "essentials": (30, 500),
    "free": (30, 500),
    "academic": (60, 2_000),
    "pro": (60, 2_000),
    "premium": (60, 2_000),
    "enterprise": (200, 50_000),
    "institutional": (200, 50_000),
    "madfam": (200, 50_000),
    "internal": (200, 50_000),
}

# Search page_size limits by tier
SEARCH_PAGE_SIZE_LIMITS = {
    "anon": 25,
    "community": 1_000,
    "essentials": 50,
    "free": 50,
    "academic": 100,
    "pro": 100,
    "premium": 100,
    "enterprise": 1_000,
    "institutional": 1_000,
    "madfam": 1_000,
    "internal": 1_000,
}


def normalize_export_tier(tier: str) -> str:
    """Normalize a tier name to its canonical export tier."""
    return EXPORT_TIER_MAP.get(tier, tier)


def has_tier_access(user_tier: str, required_tier: str) -> bool:
    """Check if a user's tier meets or exceeds the required tier."""
    return TIER_RANK.get(user_tier, 0) >= TIER_RANK.get(required_tier, 0)


# Re-export feature-gating functions from middleware so callers can import
# everything from apps.api.tier_permissions
from .middleware.tier_permissions import (  # noqa: E402, F401
    RequireFeature,
    RequireTier,
    check_feature,
    get_effective_tier,
    get_tier_limits,
    normalize_tier,
)
