"""Tests for notification and alert endpoints."""

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.middleware.janua_auth import JanuaUser
from apps.api.models import Notification, UserAlert

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"


def _make_user(user_id="test-user-1", tier="academic"):
    user = JanuaUser({"sub": user_id, "email": f"{user_id}@test.com", "tier": tier})
    user.tier = tier
    user.scopes = ["read", "search"]
    user.allowed_domains = []
    user.api_key_prefix = ""
    return user


@pytest.mark.django_db
class TestNotificationList:
    """Tests for GET /user/notifications/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("notification-list")
        self.user = _make_user()

    @patch(AUTH_PATCH)
    def test_list_empty(self, mock_auth):
        """GET returns empty list when user has no notifications."""
        mock_auth.return_value = (self.user, "fake-token")
        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["unread"] == 0
        assert data["notifications"] == []

    @patch(AUTH_PATCH)
    def test_list_with_data(self, mock_auth):
        """GET returns notifications for the authenticated user."""
        mock_auth.return_value = (self.user, "fake-token")
        Notification.objects.create(
            janua_user_id="test-user-1",
            title="Law Updated",
            body="CPEUM was updated",
            link="/leyes/cpeum",
        )
        Notification.objects.create(
            janua_user_id="test-user-1",
            title="New Version",
            body="LFT has a new version",
            is_read=True,
        )
        # Another user's notification (should not appear)
        Notification.objects.create(
            janua_user_id="other-user",
            title="Other",
            body="Not mine",
        )

        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["unread"] == 1

    @patch(AUTH_PATCH)
    def test_list_unread_first_ordering(self, mock_auth):
        """GET orders unread notifications before read ones."""
        mock_auth.return_value = (self.user, "fake-token")
        Notification.objects.create(
            janua_user_id="test-user-1",
            title="Read notification",
            body="Already read",
            is_read=True,
        )
        Notification.objects.create(
            janua_user_id="test-user-1",
            title="Unread notification",
            body="Not yet read",
            is_read=False,
        )

        response = self.client.get(self.url)

        data = response.json()
        # Unread (is_read=False=0) sorts before read (is_read=True=1)
        assert data["notifications"][0]["title"] == "Unread notification"
        assert data["notifications"][0]["is_read"] is False

    @patch(AUTH_PATCH)
    def test_list_pagination(self, mock_auth):
        """GET respects page and page_size parameters."""
        mock_auth.return_value = (self.user, "fake-token")
        for i in range(5):
            Notification.objects.create(
                janua_user_id="test-user-1",
                title=f"Notification {i}",
                body=f"Body {i}",
            )

        response = self.client.get(self.url, {"page": 1, "page_size": 2})

        data = response.json()
        assert data["total"] == 5
        assert len(data["notifications"]) == 2

    def test_list_unauthenticated(self):
        """GET without auth returns 401."""
        response = self.client.get(self.url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestNotificationMarkRead:
    """Tests for POST /user/notifications/mark-read/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("notification-mark-read")
        self.user = _make_user()

    @patch(AUTH_PATCH)
    def test_mark_read_by_ids(self, mock_auth):
        """POST with ids marks specific notifications as read."""
        mock_auth.return_value = (self.user, "fake-token")
        n1 = Notification.objects.create(
            janua_user_id="test-user-1", title="N1", body="B1"
        )
        n2 = Notification.objects.create(
            janua_user_id="test-user-1", title="N2", body="B2"
        )
        n3 = Notification.objects.create(
            janua_user_id="test-user-1", title="N3", body="B3"
        )

        response = self.client.post(self.url, {"ids": [n1.id, n2.id]}, format="json")

        assert response.status_code == 200
        assert response.json()["marked_read"] == 2
        n1.refresh_from_db()
        n2.refresh_from_db()
        n3.refresh_from_db()
        assert n1.is_read is True
        assert n2.is_read is True
        assert n3.is_read is False

    @patch(AUTH_PATCH)
    def test_mark_all_read(self, mock_auth):
        """POST with all=true marks all notifications as read."""
        mock_auth.return_value = (self.user, "fake-token")
        for i in range(3):
            Notification.objects.create(
                janua_user_id="test-user-1",
                title=f"N{i}",
                body=f"B{i}",
            )

        response = self.client.post(self.url, {"all": True}, format="json")

        assert response.status_code == 200
        assert response.json()["marked_read"] == 3
        assert (
            Notification.objects.filter(
                janua_user_id="test-user-1", is_read=False
            ).count()
            == 0
        )

    @patch(AUTH_PATCH)
    def test_mark_read_invalid_ids_format(self, mock_auth):
        """POST with ids as non-list returns 400."""
        mock_auth.return_value = (self.user, "fake-token")

        response = self.client.post(self.url, {"ids": "not-a-list"}, format="json")

        assert response.status_code == 400
        assert "list" in response.json()["error"].lower()

    def test_mark_read_unauthenticated(self):
        """POST without auth returns 401."""
        response = self.client.post(self.url, {"all": True}, format="json")
        assert response.status_code == 401


@pytest.mark.django_db
class TestAlertList:
    """Tests for GET/POST /user/alerts/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("alert-list")
        self.user = _make_user()

    @patch(AUTH_PATCH)
    def test_list_alerts(self, mock_auth):
        """GET returns active alerts for the authenticated user."""
        mock_auth.return_value = (self.user, "fake-token")
        UserAlert.objects.create(
            janua_user_id="test-user-1",
            law_id="cpeum",
            alert_type="law_updated",
        )
        UserAlert.objects.create(
            janua_user_id="test-user-1",
            category="fiscal",
            alert_type="new_law",
            is_active=False,  # inactive, should not appear
        )

        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["law_id"] == "cpeum"

    @patch(AUTH_PATCH)
    def test_create_alert_valid(self, mock_auth):
        """POST creates a new alert with valid alert_type."""
        mock_auth.return_value = (self.user, "fake-token")
        payload = {
            "law_id": "cpeum",
            "alert_type": "new_version",
            "delivery": "email",
        }

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == 201
        data = response.json()
        assert data["alert_type"] == "new_version"
        assert data["law_id"] == "cpeum"
        assert UserAlert.objects.count() == 1

    @patch(AUTH_PATCH)
    def test_create_alert_all_valid_types(self, mock_auth):
        """POST accepts all three valid alert_type values."""
        mock_auth.return_value = (self.user, "fake-token")
        for alert_type in ("law_updated", "new_version", "new_law"):
            response = self.client.post(
                self.url,
                {"alert_type": alert_type, "law_id": "test"},
                format="json",
            )
            assert response.status_code == 201

    @patch(AUTH_PATCH)
    def test_create_alert_invalid_type(self, mock_auth):
        """POST with invalid alert_type returns 400."""
        mock_auth.return_value = (self.user, "fake-token")
        payload = {"alert_type": "invalid_type", "law_id": "cpeum"}

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == 400
        assert "invalid" in response.json()["error"].lower()

    def test_list_alerts_unauthenticated(self):
        """GET without auth returns 401."""
        response = self.client.get(self.url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestAlertDelete:
    """Tests for DELETE /user/alerts/<id>/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = _make_user()

    @patch(AUTH_PATCH)
    def test_delete_success(self, mock_auth):
        """DELETE deactivates the alert and returns 204."""
        mock_auth.return_value = (self.user, "fake-token")
        alert = UserAlert.objects.create(
            janua_user_id="test-user-1",
            law_id="cpeum",
            alert_type="law_updated",
        )
        url = reverse("alert-delete", args=[alert.id])

        response = self.client.delete(url)

        assert response.status_code == 204
        alert.refresh_from_db()
        assert alert.is_active is False

    @patch(AUTH_PATCH)
    def test_delete_not_found(self, mock_auth):
        """DELETE on non-existent alert returns 404."""
        mock_auth.return_value = (self.user, "fake-token")
        url = reverse("alert-delete", args=[99999])

        response = self.client.delete(url)

        assert response.status_code == 404

    def test_delete_unauthenticated(self):
        """DELETE without auth returns 401."""
        url = reverse("alert-delete", args=[1])
        response = self.client.delete(url)
        assert response.status_code == 401
