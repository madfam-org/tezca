"""Tests for the trial management endpoints."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.api.trial_views import trial_start, trial_status

factory = APIRequestFactory()


def _authed_request(method, path, data=None, user_id="usr_123"):
    """Create a DRF request with forced authentication."""
    fn = getattr(factory, method)
    request = fn(path, data=data, format="json")
    user = MagicMock(id=user_id, is_authenticated=True)
    force_authenticate(request, user=user)
    return request


def _make_api_key(**overrides):
    """Create a mock APIKey with sensible defaults."""
    defaults = {
        "tier": "free_member",
        "trial_started_at": None,
        "trial_ends_at": None,
        "trial_tier": None,
        "trial_cc_provided": False,
        "is_active": True,
        "janua_user_id": "usr_123",
    }
    defaults.update(overrides)
    key = MagicMock(**defaults)
    key.save = MagicMock()
    return key


class TestTrialStart:
    """Tests for POST /api/v1/trial/start/."""

    @patch("apps.api.trial_views.track")
    @patch("apps.api.trial_views.get_distinct_id", return_value="dist_123")
    @patch("apps.api.trial_views.APIKey.objects")
    def test_happy_path_essentials(self, mock_qs, _mock_did, _mock_track):
        key = _make_api_key()
        mock_qs.filter.return_value.first.return_value = key
        request = _authed_request(
            "post", "/api/v1/trial/start/", {"plan": "essentials"}
        )
        response = trial_start(request)
        assert response.status_code == 201
        assert response.data["trial_tier"] == "essentials"
        assert response.data["days_remaining"] == 3
        key.save.assert_called_once()

    @patch("apps.api.trial_views.track")
    @patch("apps.api.trial_views.get_distinct_id", return_value="dist_123")
    @patch("apps.api.trial_views.APIKey.objects")
    def test_happy_path_academic(self, mock_qs, _mock_did, _mock_track):
        key = _make_api_key()
        mock_qs.filter.return_value.first.return_value = key
        request = _authed_request("post", "/api/v1/trial/start/", {"plan": "academic"})
        response = trial_start(request)
        assert response.status_code == 201
        assert response.data["trial_tier"] == "academic"

    @patch("apps.api.trial_views.track")
    @patch("apps.api.trial_views.get_distinct_id", return_value="dist_123")
    @patch("apps.api.trial_views.APIKey.objects")
    def test_happy_path_institutional(self, mock_qs, _mock_did, _mock_track):
        key = _make_api_key()
        mock_qs.filter.return_value.first.return_value = key
        request = _authed_request(
            "post", "/api/v1/trial/start/", {"plan": "institutional"}
        )
        response = trial_start(request)
        assert response.status_code == 201
        assert response.data["trial_tier"] == "institutional"

    def test_reject_invalid_plan(self):
        request = _authed_request(
            "post", "/api/v1/trial/start/", {"plan": "nonexistent"}
        )
        response = trial_start(request)
        assert response.status_code == 400
        assert "Invalid plan" in response.data["error"]

    def test_reject_plan_not_in_valid_set(self):
        request = _authed_request("post", "/api/v1/trial/start/", {"plan": "community"})
        response = trial_start(request)
        assert response.status_code == 400

    @patch("apps.api.trial_views.APIKey.objects")
    def test_reject_no_api_key(self, mock_qs):
        mock_qs.filter.return_value.first.return_value = None
        request = _authed_request(
            "post", "/api/v1/trial/start/", {"plan": "essentials"}
        )
        response = trial_start(request)
        assert response.status_code == 404
        assert "No active API key" in response.data["error"]

    @patch("apps.api.trial_views.APIKey.objects")
    def test_reject_trial_already_used(self, mock_qs):
        key = _make_api_key(trial_started_at=timezone.now())
        mock_qs.filter.return_value.first.return_value = key
        request = _authed_request(
            "post", "/api/v1/trial/start/", {"plan": "essentials"}
        )
        response = trial_start(request)
        assert response.status_code == 409
        assert "already used" in response.data["error"]

    @patch("apps.api.trial_views.APIKey.objects")
    def test_reject_non_eligible_tier(self, mock_qs):
        """academic user should not be able to start a trial (Step 1 bug fix)."""
        key = _make_api_key(tier="academic")
        mock_qs.filter.return_value.first.return_value = key
        request = _authed_request(
            "post", "/api/v1/trial/start/", {"plan": "essentials"}
        )
        response = trial_start(request)
        assert response.status_code == 403
        assert "not eligible" in response.data["error"]

    @patch("apps.api.trial_views.track")
    @patch("apps.api.trial_views.get_distinct_id", return_value="dist_123")
    @patch("apps.api.trial_views.APIKey.objects")
    def test_trial_ends_at_is_3_days(self, mock_qs, _mock_did, _mock_track):
        key = _make_api_key()
        mock_qs.filter.return_value.first.return_value = key
        before = timezone.now()
        request = _authed_request(
            "post", "/api/v1/trial/start/", {"plan": "essentials"}
        )
        response = trial_start(request)
        after = timezone.now()
        assert response.status_code == 201
        # Verify trial_ends_at was set to ~3 days from now
        assert key.trial_ends_at >= before + timedelta(days=3)
        assert key.trial_ends_at <= after + timedelta(days=3)

    @patch("apps.api.trial_views.track")
    @patch("apps.api.trial_views.get_distinct_id", return_value="dist_123")
    @patch("apps.api.trial_views.APIKey.objects")
    def test_trial_cc_provided_false_initially(self, mock_qs, _mock_did, _mock_track):
        key = _make_api_key()
        mock_qs.filter.return_value.first.return_value = key
        request = _authed_request(
            "post", "/api/v1/trial/start/", {"plan": "essentials"}
        )
        trial_start(request)
        assert key.trial_cc_provided is False


class TestTrialStatus:
    """Tests for GET /api/v1/trial/status/."""

    @patch("apps.api.trial_views.APIKey.objects")
    def test_active_trial(self, mock_qs):
        ends_at = timezone.now() + timedelta(days=2)
        key = _make_api_key(
            trial_tier="essentials",
            trial_ends_at=ends_at,
            trial_started_at=timezone.now() - timedelta(days=1),
            trial_cc_provided=False,
        )
        mock_qs.filter.return_value.first.return_value = key
        request = _authed_request("get", "/api/v1/trial/status/")
        response = trial_status(request)
        assert response.data["active"] is True
        assert response.data["trial_tier"] == "essentials"

    @patch("apps.api.trial_views.APIKey.objects")
    def test_expired_trial(self, mock_qs):
        ends_at = timezone.now() - timedelta(hours=1)
        key = _make_api_key(
            trial_tier="academic",
            trial_ends_at=ends_at,
            trial_started_at=timezone.now() - timedelta(days=4),
        )
        mock_qs.filter.return_value.first.return_value = key
        request = _authed_request("get", "/api/v1/trial/status/")
        response = trial_status(request)
        assert response.data["active"] is False

    @patch("apps.api.trial_views.APIKey.objects")
    def test_no_api_key(self, mock_qs):
        mock_qs.filter.return_value.first.return_value = None
        request = _authed_request("get", "/api/v1/trial/status/")
        response = trial_status(request)
        assert response.data["active"] is False
        assert response.data["trial_tier"] is None

    @patch("apps.api.trial_views.APIKey.objects")
    def test_no_trial_started(self, mock_qs):
        key = _make_api_key()  # defaults: trial_tier=None, trial_ends_at=None
        mock_qs.filter.return_value.first.return_value = key
        request = _authed_request("get", "/api/v1/trial/status/")
        response = trial_status(request)
        assert response.data["active"] is False

    @patch("apps.api.trial_views.APIKey.objects")
    def test_days_remaining_calculation(self, mock_qs):
        ends_at = timezone.now() + timedelta(days=2, hours=12)
        key = _make_api_key(
            trial_tier="essentials",
            trial_ends_at=ends_at,
            trial_started_at=timezone.now() - timedelta(hours=12),
        )
        mock_qs.filter.return_value.first.return_value = key
        request = _authed_request("get", "/api/v1/trial/status/")
        response = trial_status(request)
        assert response.data["days_remaining"] == 2


class TestExpireTrials:
    """Tests for the expire_trials Celery task."""

    @pytest.mark.django_db
    def test_expired_trials_cleared(self):
        from apps.api.models import APIKey
        from apps.api.tasks import expire_trials

        now = timezone.now()
        # Create an expired trial key
        expired_key = APIKey.objects.create(
            prefix="tzk_exp",
            hashed_key="fakehash_expired",
            name="Expired Trial Key",
            owner_email="expired@test.com",
            janua_user_id="usr_expired",
            tier="free_member",
            trial_tier="academic",
            trial_started_at=now - timedelta(days=5),
            trial_ends_at=now - timedelta(days=2),
            trial_cc_provided=True,
        )
        # Create an active trial key
        active_key = APIKey.objects.create(
            prefix="tzk_act",
            hashed_key="fakehash_active",
            name="Active Trial Key",
            owner_email="active@test.com",
            janua_user_id="usr_active",
            tier="free_member",
            trial_tier="essentials",
            trial_started_at=now - timedelta(days=1),
            trial_ends_at=now + timedelta(days=2),
            trial_cc_provided=False,
        )

        count = expire_trials()
        assert count == 1

        expired_key.refresh_from_db()
        assert expired_key.trial_tier is None
        assert expired_key.trial_ends_at is None
        assert expired_key.trial_cc_provided is False

        active_key.refresh_from_db()
        assert active_key.trial_tier == "essentials"
        assert active_key.trial_ends_at is not None
