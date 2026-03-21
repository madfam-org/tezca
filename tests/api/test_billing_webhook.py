"""Tests for the Dhanam billing webhook receiver."""

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from apps.api.billing_views import (
    DOWNGRADE_EVENTS,
    PLAN_TO_TIER,
    TRIAL_EVENTS,
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
            "plan": "tezca_academic",
            "user_id": "usr_123",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["tier"] == "academic"
        assert response.data["keys_updated"] == 2
        # Called twice: once for tier update, once for clearing trial fields
        assert mock_qs.filter.call_count == 2

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
        data = {
            "event": "subscription.activated",
            "plan": "tezca_academic",
            "user_id": "x",
        }
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
    def test_cancelled_downgrades_to_free_member(self, mock_qs):
        mock_qs.filter.return_value.update.return_value = 1
        data = {
            "event": "subscription.cancelled",
            "plan": "tezca_academic",
            "user_id": "usr_123",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["tier"] == "free_member"

    @override_settings(DHANAM_WEBHOOK_SECRET="")
    def test_missing_secret_rejects_all(self):
        data = {
            "event": "subscription.activated",
            "plan": "tezca_academic",
            "user_id": "x",
        }
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
    @patch("apps.api.billing_views.APIKey.objects")
    def test_essentials_plan_mapping(self, mock_qs):
        """tezca_essentials plan maps to essentials tier."""
        mock_qs.filter.return_value.update.return_value = 1
        data = {
            "event": "subscription.activated",
            "plan": "tezca_essentials",
            "user_id": "usr_ess",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["tier"] == "essentials"

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    def test_unknown_event_ignored(self):
        data = {
            "event": "invoice.paid",
            "plan": "tezca_academic",
            "user_id": "usr_123",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["status"] == "ignored"

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    @patch("apps.api.billing_views.APIKey.objects")
    def test_institutional_plan_mapping(self, mock_qs):
        """tezca_institutional plan maps to institutional tier."""
        mock_qs.filter.return_value.update.return_value = 1
        data = {
            "event": "subscription.activated",
            "plan": "tezca_institutional",
            "user_id": "usr_inst",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["tier"] == "institutional"

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    @patch("apps.api.billing_views.APIKey.objects")
    def test_legacy_pro_plan_maps_to_academic(self, mock_qs):
        """Legacy tezca_pro plan maps to academic tier."""
        mock_qs.filter.return_value.update.return_value = 1
        data = {
            "event": "subscription.activated",
            "plan": "tezca_pro",
            "user_id": "usr_legacy",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["tier"] == "academic"

    # ------------------------------------------------------------------
    # Promo plan mapping tests
    # ------------------------------------------------------------------

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    @patch("apps.api.billing_views.APIKey.objects")
    def test_essentials_promo_maps_to_essentials(self, mock_qs):
        """Promotional essentials plan maps to essentials tier."""
        mock_qs.filter.return_value.update.return_value = 1
        data = {
            "event": "subscription.activated",
            "plan": "tezca_essentials_promo",
            "user_id": "usr_promo_ess",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["tier"] == "essentials"
        assert response.data["keys_updated"] == 1

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    @patch("apps.api.billing_views.APIKey.objects")
    def test_academic_promo_maps_to_academic(self, mock_qs):
        """Promotional academic plan maps to academic tier."""
        mock_qs.filter.return_value.update.return_value = 3
        data = {
            "event": "subscription.upgraded",
            "plan": "tezca_academic_promo",
            "user_id": "usr_promo_acad",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["tier"] == "academic"
        assert response.data["keys_updated"] == 3

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    @patch("apps.api.billing_views.APIKey.objects")
    def test_institutional_promo_maps_to_institutional(self, mock_qs):
        """Promotional institutional plan maps to institutional tier."""
        mock_qs.filter.return_value.update.return_value = 1
        data = {
            "event": "subscription.activated",
            "plan": "tezca_institutional_promo",
            "user_id": "usr_promo_inst",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["tier"] == "institutional"

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    @patch("apps.api.billing_views.APIKey.objects")
    def test_madfam_plan_mapping(self, mock_qs):
        """tezca_madfam plan maps to madfam tier."""
        mock_qs.filter.return_value.update.return_value = 1
        data = {
            "event": "subscription.activated",
            "plan": "tezca_madfam",
            "user_id": "usr_madfam",
        }
        request = self._post(data)
        response = billing_webhook(request)
        assert response.status_code == 200
        assert response.data["tier"] == "madfam"

    # ------------------------------------------------------------------
    # Trial CC extension tests
    # ------------------------------------------------------------------

    @override_settings(
        DHANAM_WEBHOOK_SECRET=TEST_SECRET, TRIAL_DURATION_WITH_CC_DAYS=21
    )
    @patch("apps.api.billing_views.APIKey.objects")
    def test_cc_provided_extends_trial(self, mock_qs):
        """trial.cc_provided event extends trial_ends_at to trial_started_at + 21 days."""
        trial_start = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        mock_key = MagicMock()
        mock_key.trial_started_at = trial_start
        mock_key.trial_cc_provided = False
        mock_key.trial_ends_at = trial_start + timedelta(days=3)

        mock_qs.filter.return_value = [mock_key]

        data = {
            "event": "trial.cc_provided",
            "plan": "tezca_academic",
            "user_id": "usr_trial_cc",
        }
        request = self._post(data)
        response = billing_webhook(request)

        assert response.status_code == 200
        assert response.data["keys_updated"] == 1
        assert mock_key.trial_cc_provided is True
        assert mock_key.trial_ends_at == trial_start + timedelta(days=21)
        mock_key.save.assert_called_once_with(
            update_fields=["trial_cc_provided", "trial_ends_at"]
        )

    @override_settings(
        DHANAM_WEBHOOK_SECRET=TEST_SECRET, TRIAL_DURATION_WITH_CC_DAYS=21
    )
    @patch("apps.api.billing_views.APIKey.objects")
    def test_cc_provided_no_active_trial_ignored(self, mock_qs):
        """trial.cc_provided with no active trial keys returns ok with keys_updated=0."""
        mock_qs.filter.return_value = []

        data = {
            "event": "trial.cc_provided",
            "plan": "tezca_academic",
            "user_id": "usr_no_trial",
        }
        request = self._post(data)
        response = billing_webhook(request)

        assert response.status_code == 200
        assert response.data["keys_updated"] == 0

    @override_settings(
        DHANAM_WEBHOOK_SECRET=TEST_SECRET, TRIAL_DURATION_WITH_CC_DAYS=21
    )
    @patch("apps.api.billing_views.APIKey.objects")
    def test_cc_provided_without_trial_started_at_skipped(self, mock_qs):
        """Key with trial_tier but no trial_started_at is not extended."""
        mock_key = MagicMock()
        mock_key.trial_started_at = None
        mock_key.trial_tier = "academic"

        mock_qs.filter.return_value = [mock_key]

        data = {
            "event": "trial.cc_provided",
            "plan": "tezca_academic",
            "user_id": "usr_no_start",
        }
        request = self._post(data)
        response = billing_webhook(request)

        assert response.status_code == 200
        assert response.data["keys_updated"] == 0
        mock_key.save.assert_not_called()

    # ------------------------------------------------------------------
    # Edge case tests
    # ------------------------------------------------------------------

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    @patch("apps.api.billing_views.APIKey.objects")
    def test_upgrade_clears_trial_fields(self, mock_qs):
        """Upgrade event clears trial_tier, trial_ends_at, and trial_cc_provided."""
        mock_qs.filter.return_value.update.return_value = 1

        data = {
            "event": "subscription.activated",
            "plan": "tezca_academic",
            "user_id": "usr_trial_upgrade",
        }
        request = self._post(data)
        response = billing_webhook(request)

        assert response.status_code == 200
        assert response.data["tier"] == "academic"
        # First filter().update() sets tier, second clears trial fields
        assert mock_qs.filter.call_count == 2
        second_update_call = mock_qs.filter.return_value.update.call_args_list[1]
        assert second_update_call == (
            (),
            {
                "trial_tier": None,
                "trial_ends_at": None,
                "trial_cc_provided": False,
            },
        )

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    @patch("apps.api.billing_views.APIKey.objects")
    def test_downgrade_behavior(self, mock_qs):
        """subscription.downgraded event sets tier to free_member."""
        mock_qs.filter.return_value.update.return_value = 2
        data = {
            "event": "subscription.downgraded",
            "plan": "tezca_institutional",
            "user_id": "usr_downgrade",
        }
        request = self._post(data)
        response = billing_webhook(request)

        assert response.status_code == 200
        assert response.data["tier"] == "free_member"
        assert response.data["keys_updated"] == 2
        mock_qs.filter.assert_called_once_with(
            janua_user_id="usr_downgrade", is_active=True
        )
        mock_qs.filter.return_value.update.assert_called_once_with(tier="free_member")

    @override_settings(DHANAM_WEBHOOK_SECRET=TEST_SECRET)
    @patch("apps.api.billing_views.APIKey.objects")
    def test_no_matching_api_keys_returns_ok(self, mock_qs):
        """Upgrade with no matching API keys still returns 200 with keys_updated=0."""
        mock_qs.filter.return_value.update.return_value = 0

        data = {
            "event": "subscription.activated",
            "plan": "tezca_essentials",
            "user_id": "usr_no_keys",
        }
        request = self._post(data)
        response = billing_webhook(request)

        assert response.status_code == 200
        assert response.data["keys_updated"] == 0
        assert response.data["tier"] == "essentials"
