"""PostHog analytics for Tezca -- graceful no-op when API key is empty."""

import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

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
        # Keyword form binds on both posthog majors: 3.x is
        # capture(distinct_id, event, ...), 6+/7.x is
        # capture(event, *, distinct_id=..., ...) — positional args would
        # TypeError on 6+ and silently kill all telemetry via the
        # except below.
        _client.capture(
            event=event, distinct_id=distinct_id, properties=properties or {}
        )
    except Exception:
        # Telemetry must never break a request. Log at debug for visibility
        # without polluting production logs with PostHog network blips.
        logger.debug("PostHog track() failed for event=%s", event, exc_info=True)


def identify(distinct_id: str, properties: Optional[dict] = None) -> None:
    if _client is None:
        return
    try:
        # posthog 6+ removed module-level identify(); set() is its
        # replacement for attaching person properties.
        if hasattr(_client, "identify"):
            _client.identify(distinct_id, properties=properties or {})
        else:
            _client.set(distinct_id=distinct_id, properties=properties or {})
    except Exception:
        logger.debug("PostHog identify() failed", exc_info=True)


def shutdown() -> None:
    if _client is None:
        return
    try:
        _client.shutdown()
    except Exception:
        logger.debug("PostHog shutdown() failed", exc_info=True)
