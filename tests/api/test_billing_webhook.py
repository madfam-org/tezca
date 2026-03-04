"""Tests for the Dhanam billing webhook receiver."""

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from apps.api.billing_views import (
    DOWNGRADE_EVENTS,
    PLAN_TO_TIER,
    UPGRADE_EVENTS,
    _verify_signature,
    billing_webhook,
)

TEST_SECRET = "test-webhook-secret-for-tests"


def _sign(payload: bytes, secret: str = TEST_SECRET) -> str:
    """Generate HMAC-SHA256 signature for test payloads."""
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class TestVerifySignature:
    """Tests for HMAC signature verification."""

    def test_valid_signature(self):
        body = b'{"event":"test"}'
        sig = _sign(body)
        assert _verify_signature(body, sig, TEST_SECRET) is True

    def test_invalid_signature(self):
        body = b'{"event":"test"}'
        assert _verify_signature(body, "sha256=bad", TEST_SECRET) is False

    def test_missing_signature(self):
        assert _verify_signature(b"data", "", TEST_SECRET) is False

    def test_missing_secret(self):
        assert _verify_signature(b"data", "sha256=abc", "") is False

    def test_wrong_prefix(self):
        assert _verify_signature(b"data", "md5=abc", TEST_SECRET) is False


class TestBillingWebhook:
    """Integration tests for the billing_webhook view."""

    def setup_method(self):
        self.factory = APIRequestFactory()

    def _post(self, data: dict, secret: str = TEST_SECRET, sig: str | None = None):
        body = json.dumps(data).encode()
        if sig is None:
            sig = _sign(body, secret)
        request = self.factory.post(
            "/api/v1/billing/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_DHANAM_SIGNATURE=sig,
        )
        return request

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    @patch("apps.api.billing_views.APIKey.objects")
    def test_activated_upgrades_tier(self, mock_qs):
        mock_qs.filter.return_value.update.return_value = 2
        data = {
            "event": "subscription.activated",
            "plan": "tezca_pro",
            "user_id": "usr_123",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["tier"] == "pro"
        assert response.data["keys_updated"] == 2
        mock_qs.filter.assert_called_once_with(janua_user_id="usr_123", is_active=True)

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    @patch("apps.api.billing_views.APIKey.objects")
    def test_upgraded_event_works(self, mock_qs):
        mock_qs.filter.return_value.update.return_value = 1
        data = {
            "event": "subscription.upgraded",
            "plan": "tezca_community",
            "user_id": "usr_456",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["tier"] == "community"

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    def test_invalid_signature_returns_403(self):
        data = {"event": "subscription.activated", "plan": "tezca_pro", "user_id": "x"}
        request = self._post(data, sig="sha256=invalid")
        response = billing_webhook(request)
        assert response.status_code == 403

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    def test_unknown_plan_returns_400(self):
        data = {
            "event": "subscription.activated",
            "plan": "tezca_unknown",
            "user_id": "usr_789",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 400
        assert "Unknown plan" in response.data["error"]

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    @patch("apps.api.billing_views.APIKey.objects")
    def test_cancelled_downgrades_to_free(self, mock_qs):
        mock_qs.filter.return_value.update.return_value = 1
        data = {
            "event": "subscription.cancelled",
            "plan": "tezca_pro",
            "user_id": "usr_123",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["tier"] == "free"

    @override_settings(DHANAM_WEBHOOK_SECRET="")
    def test_missing_secret_rejects_all(self):
        data = {"event": "subscription.activated", "plan": "tezca_pro", "user_id": "x"}
        request = self._post(data, sig="sha256=anything")
        response = billing_webhook(request)
        assert response.status_code == 500
        assert "not configured" in response.data["error"]

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    def test_missing_fields_returns_400(self):
        data = {"event": "subscription.activated"}  # no user_id
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 400

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    def test_unknown_event_ignored(self):
        data = {
            "event": "invoice.paid",
            "plan": "tezca_pro",
            "user_id": "usr_123",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["status"] == "ignored"
