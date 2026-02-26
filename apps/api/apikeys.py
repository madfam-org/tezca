"""
API key generation and hashing utilities.

Key format: tzk_<36-char-urlsafe-random> (40 chars total)
"""

import hashlib
import secrets


KEY_PREFIX_TAG = "tzk_"
KEY_RANDOM_LENGTH = 36


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns (full_key, prefix, hashed_key).
    The full_key is shown once to the user and never stored.
    """
    random_part = secrets.token_urlsafe(KEY_RANDOM_LENGTH)
    full_key = f"{KEY_PREFIX_TAG}{random_part}"
    prefix = random_part[:8]
    hashed = hash_key(full_key)
    return full_key, prefix, hashed


def hash_key(full_key: str) -> str:
    """SHA-256 hash of the full API key."""
    return hashlib.sha256(full_key.encode()).hexdigest()
