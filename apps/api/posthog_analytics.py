"""PostHog analytics for Tezca -- graceful no-op when API key is empty."""

import os
from typing import Optional

_client: Optional[object] = None


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
