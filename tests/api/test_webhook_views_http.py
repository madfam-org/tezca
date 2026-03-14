"""Tests for webhook_views.py — HTTP endpoint tests for webhook CRUD + test ping.

Covers gaps not in test_webhooks.py:
  - test_webhook endpoint (sends test event)
  - delete_webhook for non-owned webhooks
  - list_webhooks with no webhooks
  - create_webhook with missing events
  - _get_api_key helper edge cases
  - JWT-only user (no api_key_prefix) gets 403
"""

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.apikeys import generate_api_key
from apps.api.middleware.apikey_auth import APIKeyUser
from apps.api.middleware.janua_auth import JanuaUser
from apps.api.models import APIKey, WebhookSubscription
from apps.api.utils.url_validation import UnsafeURLError

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"


def _make_api_key_user(api_key):
    return APIKeyUser(api_key)


@pytest.mark.django_db
class TestWebhookTestEndpoint:
    """Tests for POST /webhooks/{id}/test/ — sends test ping."""

    def setup_method(self):
        self.client = APIClient()
        full, prefix, hashed = generate_api_key()
        self.api_key = APIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed,
            name="Test Ping Key",
            owner_email="ping@example.com",
            tier="institutional",
            scopes=["read", "search"],
        )
        self.user = _make_api_key_user(self.api_key)
        self.sub = WebhookSubscription.objects.create(
            api_key=self.api_key,
            url="https://example.com/hook",
            events=["version.created"],
            secret="s" * 64,
        )

    @patch("apps.api.webhook_views.deliver_webhook")
    @patch(AUTH_PATCH)
    def test_test_webhook_success(self, mock_auth, mock_deliver):
        """POST /webhooks/{id}/test/ sends test ping and returns 200."""
        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-test", args=[self.sub.pk])
        response = self.client.post(url)

        assert response.status_code == 200
        assert response.json()["status"] == "sent"
        mock_deliver.assert_called_once()
        # Verify test payload
        call_args = mock_deliver.call_args[0]
        assert call_args[0] == self.sub.pk
        assert call_args[1] == "test.ping"
        assert call_args[2]["test"] is True

    @patch(AUTH_PATCH)
    def test_test_webhook_not_found(self, mock_auth):
        """POST /webhooks/9999/test/ returns 404 for non-existent webhook."""
        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-test", args=[99999])
        response = self.client.post(url)

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    @patch("apps.api.webhook_views.deliver_webhook")
    @patch(AUTH_PATCH)
    def test_test_webhook_delivery_failure(self, mock_auth, mock_deliver):
        """POST /webhooks/{id}/test/ returns 502 when delivery fails."""
        mock_auth.return_value = (self.user, "fake-key")
        mock_deliver.side_effect = Exception("Connection refused")

        url = reverse("webhook-test", args=[self.sub.pk])
        response = self.client.post(url)

        assert response.status_code == 502
        assert response.json()["status"] == "failed"

    @patch(AUTH_PATCH)
    def test_test_other_users_webhook_returns_404(self, mock_auth):
        """Cannot test another user's webhook — returns 404."""
        # Create a different API key
        full2, prefix2, hashed2 = generate_api_key()
        other_key = APIKey.objects.create(
            prefix=prefix2,
            hashed_key=hashed2,
            name="Other Key",
            owner_email="other@example.com",
            tier="institutional",
        )
        other_user = _make_api_key_user(other_key)
        mock_auth.return_value = (other_user, "fake-key")

        url = reverse("webhook-test", args=[self.sub.pk])
        response = self.client.post(url)

        assert response.status_code == 404


@pytest.mark.django_db
class TestWebhookDeleteEdgeCases:
    """Edge cases for DELETE /webhooks/{id}/."""

    def setup_method(self):
        self.client = APIClient()
        full, prefix, hashed = generate_api_key()
        self.api_key = APIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed,
            name="Delete Test Key",
            owner_email="delete@example.com",
            tier="institutional",
        )
        self.user = _make_api_key_user(self.api_key)

    @patch(AUTH_PATCH)
    def test_delete_other_users_webhook_returns_404(self, mock_auth):
        """Cannot delete another user's webhook — returns 404."""
        # Create another key's webhook
        full2, prefix2, hashed2 = generate_api_key()
        other_key = APIKey.objects.create(
            prefix=prefix2,
            hashed_key=hashed2,
            name="Other Delete Key",
            owner_email="other@example.com",
        )
        sub = WebhookSubscription.objects.create(
            api_key=other_key,
            url="https://example.com/other",
            events=["law.updated"],
            secret="x" * 64,
        )

        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-delete", args=[sub.pk])
        response = self.client.delete(url)

        assert response.status_code == 404
        # Webhook should still exist
        assert WebhookSubscription.objects.filter(pk=sub.pk).exists()

    @patch(AUTH_PATCH)
    def test_delete_nonexistent_returns_404(self, mock_auth):
        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-delete", args=[99999])
        response = self.client.delete(url)

        assert response.status_code == 404


@pytest.mark.django_db
class TestWebhookListEdgeCases:
    """Edge cases for GET /webhooks/list/."""

    def setup_method(self):
        self.client = APIClient()
        full, prefix, hashed = generate_api_key()
        self.api_key = APIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed,
            name="List Test Key",
            owner_email="list@example.com",
            tier="institutional",
        )
        self.user = _make_api_key_user(self.api_key)

    @patch(AUTH_PATCH)
    def test_list_empty_webhooks(self, mock_auth):
        """Returns empty list when user has no webhooks."""
        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-list")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["webhooks"] == []

    @patch(AUTH_PATCH)
    def test_list_only_own_webhooks(self, mock_auth):
        """Only returns webhooks belonging to the authenticated API key."""
        # Create own webhook
        WebhookSubscription.objects.create(
            api_key=self.api_key,
            url="https://example.com/mine",
            events=["law.updated"],
            secret="m" * 64,
        )

        # Create another key's webhook
        full2, prefix2, hashed2 = generate_api_key()
        other_key = APIKey.objects.create(
            prefix=prefix2,
            hashed_key=hashed2,
            name="Other List Key",
            owner_email="other@example.com",
        )
        WebhookSubscription.objects.create(
            api_key=other_key,
            url="https://example.com/theirs",
            events=["law.created"],
            secret="t" * 64,
        )

        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-list")
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["webhooks"][0]["url"] == "https://example.com/mine"


@pytest.mark.django_db
class TestWebhookAuthRequirements:
    """Tests for webhook endpoint authentication requirements."""

    def setup_method(self):
        self.client = APIClient()

    def test_create_webhook_unauthenticated_returns_401(self):
        """POST /webhooks/ without auth returns 401."""
        url = reverse("webhook-create")
        response = self.client.post(
            url,
            {"url": "https://example.com", "events": ["version.created"]},
            format="json",
        )
        assert response.status_code == 401

    @patch(AUTH_PATCH)
    def test_create_webhook_jwt_only_returns_403(self, mock_auth):
        """JWT user without api_key_prefix gets 403 (webhooks require API key)."""
        jwt_user = JanuaUser(
            {"sub": "user-123", "email": "user@test.com", "tier": "institutional"}
        )
        jwt_user.tier = "institutional"
        jwt_user.scopes = ["read", "search"]
        jwt_user.allowed_domains = []
        jwt_user.api_key_prefix = ""  # No API key
        mock_auth.return_value = (jwt_user, "fake-token")

        url = reverse("webhook-create")
        response = self.client.post(
            url,
            {"url": "https://example.com", "events": ["version.created"]},
            format="json",
        )

        assert response.status_code == 403
        assert "api key" in response.json()["error"].lower()

    def test_list_webhooks_unauthenticated_returns_401(self):
        url = reverse("webhook-list")
        response = self.client.get(url)
        assert response.status_code == 401

    def test_delete_webhook_unauthenticated_returns_401(self):
        url = reverse("webhook-delete", args=[1])
        response = self.client.delete(url)
        assert response.status_code == 401

    def test_test_webhook_unauthenticated_returns_401(self):
        url = reverse("webhook-test", args=[1])
        response = self.client.post(url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestCreateWebhookValidation:
    """Tests for create_webhook input validation."""

    def setup_method(self):
        self.client = APIClient()
        full, prefix, hashed = generate_api_key()
        self.api_key = APIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed,
            name="Validation Key",
            owner_email="val@example.com",
            tier="institutional",
        )
        self.user = _make_api_key_user(self.api_key)

    @patch(AUTH_PATCH)
    def test_create_missing_events_returns_400(self, mock_auth):
        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-create")
        response = self.client.post(
            url, {"url": "https://example.com/hook"}, format="json"
        )

        assert response.status_code == 400
        assert "events" in response.json()["error"].lower()

    @patch(AUTH_PATCH)
    def test_create_empty_events_list_returns_400(self, mock_auth):
        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-create")
        response = self.client.post(
            url,
            {"url": "https://example.com/hook", "events": []},
            format="json",
        )

        assert response.status_code == 400

    @patch(AUTH_PATCH)
    def test_create_with_domain_filter(self, mock_auth):
        """Can create webhook with domain filter."""
        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-create")
        response = self.client.post(
            url,
            {
                "url": "https://example.com/hook",
                "events": ["law.updated"],
                "domain_filter": ["fiscal", "laboral"],
            },
            format="json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["domain_filter"] == ["fiscal", "laboral"]
        assert data["is_active"] is True

    @patch(
        "apps.api.webhook_views.validate_webhook_url",
        side_effect=UnsafeURLError(
            "Webhook URL resolves to private/reserved IP: 127.0.0.1"
        ),
    )
    @patch(AUTH_PATCH)
    def test_create_webhook_rejects_private_url(self, mock_auth, mock_validate):
        """Creating a webhook with a private IP URL returns 400."""
        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-create")
        response = self.client.post(
            url,
            {"url": "https://internal.corp/hook", "events": ["law.updated"]},
            format="json",
        )

        assert response.status_code == 400
        assert "private" in response.json()["error"].lower()

    @patch(
        "apps.api.webhook_views.validate_webhook_url",
        side_effect=UnsafeURLError(
            "Webhook URL resolves to private/reserved IP: 127.0.0.1"
        ),
    )
    @patch(AUTH_PATCH)
    def test_create_webhook_rejects_localhost(self, mock_auth, mock_validate):
        """Creating a webhook targeting localhost returns 400."""
        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-create")
        response = self.client.post(
            url,
            {"url": "https://localhost/hook", "events": ["law.updated"]},
            format="json",
        )

        assert response.status_code == 400

    @patch(AUTH_PATCH)
    def test_create_generates_64char_secret(self, mock_auth):
        """Created webhook has a 64-character hex secret."""
        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-create")
        response = self.client.post(
            url,
            {"url": "https://example.com/hook", "events": ["version.created"]},
            format="json",
        )

        assert response.status_code == 201
        assert len(response.json()["secret"]) == 64
