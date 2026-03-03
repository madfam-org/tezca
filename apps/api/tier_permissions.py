"""
Single source of truth for tier naming, ranking, and format access.

All tier-dependent logic should import from this module.
"""

# Canonical tier names
TIER_ANON = "anon"
TIER_FREE = "free"
TIER_ESSENTIALS = "essentials"
TIER_PRO = "pro"
TIER_ENTERPRISE = "enterprise"
TIER_MADFAM = "madfam"
TIER_INTERNAL = "internal"

# Aliases that map to canonical export tiers
EXPORT_TIER_MAP = {
    "internal": "premium",
    "pro": "premium",
    "enterprise": "premium",
    "madfam": "premium",
    "essentials": "free",
}

# Tier ranking for access control (higher = more access)
TIER_RANK = {
    "anon": 0,
    "free": 1,
    "essentials": 1,
    "pro": 2,
    "premium": 2,
    "enterprise": 2,
    "madfam": 2,
    "internal": 3,
}

# Export format access by tier
FORMAT_TIERS = {
    "txt": "anon",
    "pdf": "free",
    "latex": "premium",
    "docx": "premium",
    "epub": "premium",
    "json": "premium",
}

# Export hourly limits
EXPORT_HOURLY_LIMITS = {
    "anon": 10,
    "free": 30,
    "premium": 100,
}

# Rate limiting (per minute, per hour)
RATE_LIMITS = {
    "anon": (10, 100),
    "free": (30, 500),
    "essentials": (30, 500),
    "pro": (60, 2_000),
    "enterprise": (120, 10_000),
    "madfam": (120, 10_000),
    "internal": (200, 50_000),
}


def normalize_export_tier(tier: str) -> str:
    """Normalize a tier name to an export-level tier (anon/free/premium)."""
    return EXPORT_TIER_MAP.get(tier, tier)


def has_tier_access(user_tier: str, required_tier: str) -> bool:
    """Check if a user's tier meets or exceeds the required tier."""
    return TIER_RANK.get(user_tier, 0) >= TIER_RANK.get(required_tier, 0)
