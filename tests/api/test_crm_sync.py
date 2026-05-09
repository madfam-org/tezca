"""Tests for CRM sync — interest.created dispatch to phynd-crm."""

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from apps.api.models import FeatureInterest


@pytest.mark.django_db
class TestDispatchCrmEvent:
    """Tests for dispatch_crm_event gating logic."""

    def test_noop_when_url_empty(self):
        """dispatch_crm_event does nothing when CRM_WEBHOOK_URL is empty."""
        with patch("apps.api.crm_sync.CRM_WEBHOOK_URL", ""), patch(
            "apps.api.crm_sync.CRM_WEBHOOK_SECRET", "secret"
        ):
            from apps.api.crm_sync import dispatch_crm_event

            with patch("apps.api.tasks.deliver_crm_webhook") as mock_task:
                dispatch_crm_event("interest.created", {"email": "a@b.com"})
                mock_task.delay.assert_not_called()

    def test_noop_when_secret_empty(self):
        """dispatch_crm_event does nothing when CRM_WEBHOOK_SECRET is empty."""
        with patch(
            "apps.api.crm_sync.CRM_WEBHOOK_URL",
            "https://crm.example.com/api/webhooks/tezca",
        ), patch("apps.api.crm_sync.CRM_WEBHOOK_SECRET", ""):
            from apps.api.crm_sync import dispatch_crm_event

            with patch("apps.api.tasks.deliver_crm_webhook") as mock_task:
                dispatch_crm_event("interest.created", {"email": "a@b.com"})
                mock_task.delay.assert_not_called()

    def test_dispatches_when_configured(self):
        """dispatch_crm_event queues Celery task when both URL and secret are set."""
        with patch(
            "apps.api.crm_sync.CRM_WEBHOOK_URL",
            "https://crm.example.com/api/webhooks/tezca",
        ), patch("apps.api.crm_sync.CRM_WEBHOOK_SECRET", "secret"):
            from apps.api.crm_sync import dispatch_crm_event

            with patch("apps.api.tasks.deliver_crm_webhook") as mock_task:
                payload = {"email": "a@b.com", "feature_key": "webhooks"}
                dispatch_crm_event("interest.created", payload)
                mock_task.delay.assert_called_once_with("interest.created", payload)


@pytest.mark.django_db
class TestDeliverCrmWebhook:
    """Tests for deliver_crm_webhook Celery task."""

    @override_settings(
        CRM_WEBHOOK_URL="https://crm.example.com/api/webhooks/tezca",
        CRM_WEBHOOK_SECRET="test-secret",
    )
    @patch("apps.api.tasks.http_requests.post")
    def test_builds_correct_hmac_signature(self, mock_post):
        """Task builds valid HMAC-SHA256 signature in header."""
        mock_post.return_value = MagicMock(status_code=200)

        from apps.api.tasks import deliver_crm_webhook

        deliver_crm_webhook("interest.created", {"email": "a@b.com"})

        call_args = mock_post.call_args
        body = call_args.kwargs.get("data") or call_args[1].get("data")
        headers = call_args.kwargs.get("headers") or call_args[1].get("headers")

        expected_sig = hmac.new(
            b"test-secret", body.encode(), hashlib.sha256
        ).hexdigest()
        assert headers["X-Webhook-Signature"] == f"sha256={expected_sig}"

    @override_settings(CRM_WEBHOOK_URL="", CRM_WEBHOOK_SECRET="")
    @patch("apps.api.tasks.http_requests.post")
    def test_noop_when_not_configured(self, mock_post):
        """Task does nothing when CRM settings are empty."""
        from apps.api.tasks import deliver_crm_webhook

        deliver_crm_webhook("interest.created", {"email": "a@b.com"})

        mock_post.assert_not_called()

    @override_settings(
        CRM_WEBHOOK_URL="https://crm.example.com/api/webhooks/tezca",
        CRM_WEBHOOK_SECRET="secret",
    )
    @patch("apps.api.tasks.http_requests.post")
    def test_retries_on_http_failure(self, mock_post):
        """Task retries when HTTP response indicates failure."""
        mock_post.return_value = MagicMock(status_code=500)

        from apps.api.tasks import deliver_crm_webhook

        # The task should raise Retry on failure
        with pytest.raises(Exception):
            deliver_crm_webhook("interest.created", {"email": "a@b.com"})


@pytest.mark.django_db
class TestFeatureInterestSignal:
    """Tests for post_save signal on FeatureInterest."""

    @patch("apps.api.crm_sync.dispatch_crm_event")
    def test_signal_fires_on_create(self, mock_dispatch):
        """Signal dispatches CRM event when FeatureInterest is created."""
        FeatureInterest.objects.create(
            email="user@example.com",
            feature_key="webhooks",
            use_case="research",
            wishlist="need webhook support",
        )

        mock_dispatch.assert_called_once()
        call_args = mock_dispatch.call_args
        assert call_args[0][0] == "interest.created"
        assert call_args[0][1]["email"] == "user@example.com"
        assert call_args[0][1]["feature_key"] == "webhooks"
        assert call_args[0][1]["wishlist"] == "need webhook support"

    @patch("apps.api.crm_sync.dispatch_crm_event")
    def test_signal_does_not_fire_on_update(self, mock_dispatch):
        """Signal does NOT dispatch CRM event on update (only created=True)."""
        interest = FeatureInterest.objects.create(
            email="user@example.com",
            feature_key="webhooks",
        )
        mock_dispatch.reset_mock()

        interest.use_case = "work"
        interest.save()

        mock_dispatch.assert_not_called()
