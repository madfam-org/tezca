"""Tests for the posthog_analytics wrapper.

The wrapper must speak both posthog-python majors: 3.x
(``capture(distinct_id, event)``, module-level ``identify()``) and 6+/7.x
(``capture(event, *, distinct_id=...)``, ``identify()`` removed in favour
of ``set()``). A silent regression here no-ops all product telemetry —
the calls are wrapped in broad excepts by design, so nothing else would
surface it.
"""

from unittest.mock import MagicMock, patch

from apps.api import posthog_analytics


class _V7StyleClient:
    """Mimics posthog 6+/7.x: keyword-only capture, no identify()."""

    def __init__(self):
        self.capture_calls = []
        self.set_calls = []

    def capture(self, event=None, *, distinct_id=None, properties=None, **kw):
        if not isinstance(event, str):
            raise TypeError("capture() event must be the first argument")
        self.capture_calls.append((event, distinct_id, properties))

    def set(self, *, distinct_id=None, properties=None, **kw):
        self.set_calls.append((distinct_id, properties))

    # NOTE: no identify() attribute, matching 6+.


class _V3StyleClient:
    """Mimics posthog 3.x: capture(distinct_id, event), identify()."""

    def __init__(self):
        self.capture_calls = []
        self.identify_calls = []

    def capture(self, distinct_id=None, event=None, properties=None, **kw):
        self.capture_calls.append((distinct_id, event, properties))

    def identify(self, distinct_id, properties=None, **kw):
        self.identify_calls.append((distinct_id, properties))


class TestTrack:
    def test_noop_when_client_unset(self):
        with patch.object(posthog_analytics, "_client", None):
            posthog_analytics.track("user-1", "law_viewed")  # must not raise

    def test_v7_client_receives_keyword_call(self):
        client = _V7StyleClient()
        with patch.object(posthog_analytics, "_client", client):
            posthog_analytics.track("user-1", "law_viewed", {"law": "cpeum"})
        assert client.capture_calls == [("law_viewed", "user-1", {"law": "cpeum"})]

    def test_v3_client_receives_keyword_call(self):
        client = _V3StyleClient()
        with patch.object(posthog_analytics, "_client", client):
            posthog_analytics.track("user-1", "law_viewed")
        assert client.capture_calls == [("user-1", "law_viewed", {})]

    def test_capture_exception_is_swallowed(self):
        client = MagicMock()
        client.capture.side_effect = RuntimeError("network blip")
        with patch.object(posthog_analytics, "_client", client):
            posthog_analytics.track("user-1", "law_viewed")  # must not raise


class TestIdentify:
    def test_noop_when_client_unset(self):
        with patch.object(posthog_analytics, "_client", None):
            posthog_analytics.identify("user-1")  # must not raise

    def test_v3_client_uses_identify(self):
        client = _V3StyleClient()
        with patch.object(posthog_analytics, "_client", client):
            posthog_analytics.identify("user-1", {"tier": "academic"})
        assert client.identify_calls == [("user-1", {"tier": "academic"})]

    def test_v7_client_falls_back_to_set(self):
        client = _V7StyleClient()
        with patch.object(posthog_analytics, "_client", client):
            posthog_analytics.identify("user-1", {"tier": "academic"})
        assert client.set_calls == [("user-1", {"tier": "academic"})]

    def test_identify_exception_is_swallowed(self):
        client = _V3StyleClient()
        client.identify = MagicMock(side_effect=RuntimeError("boom"))
        with patch.object(posthog_analytics, "_client", client):
            posthog_analytics.identify("user-1")  # must not raise
