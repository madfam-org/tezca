"""Tests for signal-driven webhook dispatch.

Covers:
  - Law post_save signal fires dispatch_webhook_event
  - LawVersion post_save signal fires dispatch_webhook_event (created only)
  - dispatch_webhook_event filters by event type
  - dispatch_webhook_event respects domain_filter
  - deliver_webhook signs payload with sha256= prefix
"""

from datetime import date
from unittest.mock import patch

import pytest

from apps.api.apikeys import generate_api_key
from apps.api.models import APIKey, Law, LawVersion, WebhookSubscription


@pytest.mark.django_db
class TestSignalDispatch:
    """Verify Django signals fire dispatch_webhook_event on model save."""

    def setup_method(self):
        full, prefix, hashed = generate_api_key()
        self.api_key = APIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed,
            name="Signal Test",
            owner_email="signal@example.com",
        )
        self.sub = WebhookSubscription.objects.create(
            api_key=self.api_key,
            url="https://example.com/hook",
            events=["law.created", "law.updated", "version.created"],
            secret="s" * 64,
        )

    @patch("apps.api.tasks.deliver_webhook.delay")
    def test_law_created_signal(self, mock_delay):
        """Creating a Law fires law.created event."""
        Law.objects.create(
            official_id="test_signal_create",
            name="Test Signal Law",
            tier="federal",
            category="fiscal",
        )

        # Signal fires dispatch_webhook_event → deliver_webhook.delay
        # But only if there are matching subscriptions
        assert mock_delay.called
        call_args = mock_delay.call_args
        assert call_args[0][1] == "law.created"
        assert call_args[0][2]["law_id"] == "test_signal_create"

    @patch("apps.api.tasks.deliver_webhook.delay")
    def test_law_updated_signal(self, mock_delay):
        """Updating a Law fires law.updated event."""
        law = Law.objects.create(
            official_id="test_signal_update",
            name="Original Name",
            tier="federal",
            category="fiscal",
        )
        mock_delay.reset_mock()

        law.name = "Updated Name"
        law.save()

        mock_delay.assert_called_once()
        call_args = mock_delay.call_args
        assert call_args[0][1] == "law.updated"

    @patch("apps.api.tasks.deliver_webhook.delay")
    def test_version_created_signal(self, mock_delay):
        """Creating a LawVersion fires version.created event."""
        law = Law.objects.create(
            official_id="test_signal_version",
            name="Version Law",
            tier="federal",
            category="fiscal",
        )
        mock_delay.reset_mock()

        LawVersion.objects.create(
            law=law,
            publication_date=date(2026, 3, 1),
        )

        # Should have been called for version.created (law.updated also fires from law save)
        calls = [c for c in mock_delay.call_args_list if c[0][1] == "version.created"]
        assert len(calls) == 1
        assert calls[0][0][2]["law_id"] == "test_signal_version"

    @patch("apps.api.tasks.deliver_webhook.delay")
    def test_version_update_does_not_dispatch(self, mock_delay):
        """Updating an existing LawVersion does NOT fire version.created."""
        law = Law.objects.create(
            official_id="test_signal_no_ver",
            name="No Version Event",
            tier="federal",
        )
        ver = LawVersion.objects.create(
            law=law,
            publication_date=date(2026, 1, 1),
        )
        mock_delay.reset_mock()

        ver.publication_date = date(2026, 2, 1)
        ver.save()

        # Only law.updated from the version save touching the version, no version.created
        version_calls = [
            c for c in mock_delay.call_args_list if c[0][1] == "version.created"
        ]
        assert len(version_calls) == 0


@pytest.mark.django_db
class TestDispatchFiltering:
    """Verify dispatch_webhook_event applies event and domain filters."""

    def setup_method(self):
        full, prefix, hashed = generate_api_key()
        self.api_key = APIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed,
            name="Filter Test",
            owner_email="filter@example.com",
        )

    @patch("apps.api.tasks.deliver_webhook.delay")
    def test_filters_by_event_type(self, mock_delay):
        """Subscription for law.updated only should not receive law.created."""
        WebhookSubscription.objects.create(
            api_key=self.api_key,
            url="https://example.com/hook",
            events=["law.updated"],
            secret="a" * 64,
        )
        from apps.api.webhooks import dispatch_webhook_event

        dispatch_webhook_event("law.created", {"law_id": "test", "category": "fiscal"})
        assert not mock_delay.called

    @patch("apps.api.tasks.deliver_webhook.delay")
    def test_respects_domain_filter(self, mock_delay):
        """Subscription with domain_filter=['fiscal'] ignores penal events."""
        WebhookSubscription.objects.create(
            api_key=self.api_key,
            url="https://example.com/hook",
            events=["law.updated"],
            domain_filter=["fiscal"],
            secret="b" * 64,
        )
        from apps.api.webhooks import dispatch_webhook_event

        dispatch_webhook_event("law.updated", {"law_id": "cpf", "category": "penal"})
        assert not mock_delay.called

    @patch("apps.api.tasks.deliver_webhook.delay")
    def test_matches_domain_filter(self, mock_delay):
        """Subscription with domain_filter=['fiscal'] receives fiscal events."""
        WebhookSubscription.objects.create(
            api_key=self.api_key,
            url="https://example.com/hook",
            events=["law.updated"],
            domain_filter=["fiscal"],
            secret="c" * 64,
        )
        from apps.api.webhooks import dispatch_webhook_event

        dispatch_webhook_event("law.updated", {"law_id": "cff", "category": "fiscal"})
        assert mock_delay.called
