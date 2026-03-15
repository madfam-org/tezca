"""PostHog analytics for Tezca -- graceful no-op when API key is empty."""

import hashlib
import os
from typing import Optional

_client: Optional[object] = None


def get_distinct_id(request) -> str:
    """Extract a stable distinct ID from any auth method.

    Priority: API key prefix > JWT user ID > hashed IP.
    """
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        # API key user
        prefix = getattr(user, "api_key_prefix", "")
        if prefix:
            return f"apikey:{prefix}"
        # JWT user
        uid = getattr(user, "id", None) or getattr(user, "pk", None)
        if uid:
            return str(uid)
    # Anonymous — hash IP
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = (
        xff.split(",")[0].strip()
        if xff
        else request.META.get("REMOTE_ADDR", "127.0.0.1")
    )
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def init_posthog() -> None:
    global _client
    api_key = os.environ.get("POSTHOG_API_KEY", "")
    if not api_key:
        return
    try:
        import posthog

        posthog.api_key = api_key
        posthog.host = os.environ.get("POSTHOG_HOST", "https://analytics.madfam.io")
        _client = posthog
    except ImportError:
        pass


def track(distinct_id: str, event: str, properties: Optional[dict] = None) -> None:
    if _client is None:
        return
    try:
        _client.capture(distinct_id, event, properties=properties or {})
    except Exception:
        pass


def identify(distinct_id: str, properties: Optional[dict] = None) -> None:
    if _client is None:
        return
    try:
        _client.identify(distinct_id, properties=properties or {})
    except Exception:
        pass


def shutdown() -> None:
    if _client is None:
        return
    try:
        _client.shutdown()
    except Exception:
        pass
