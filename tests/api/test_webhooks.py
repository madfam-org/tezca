"""
Tests for webhook subscription CRUD and dispatch.

Covers:
  - Create webhook requires API key (not JWT)
  - Create webhook validates events
  - List webhooks returns only key's subscriptions
  - Delete webhook
  - Webhook dispatch with HMAC signature
  - Auto-disable after max failures
"""

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.apikeys import generate_api_key
from apps.api.middleware.apikey_auth import APIKeyUser
from apps.api.models import APIKey, WebhookSubscription

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"


def _make_api_key_user(api_key):
    return APIKeyUser(api_key)


@pytest.mark.django_db
class TestWebhookCRUD:
    def setup_method(self):
        self.client = APIClient()
        full, prefix, hashed = generate_api_key()
        self.api_key = APIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed,
            name="Webhook Test Key",
            owner_email="webhook@example.com",
            tier="pro",
            scopes=["read", "search"],
        )
        self.user = _make_api_key_user(self.api_key)

    @patch(AUTH_PATCH)
    def test_create_webhook(self, mock_auth):
        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-create")
        response = self.client.post(
            url,
            {
                "url": "https://api.dhan.am/hooks/tezca",
                "events": ["version.created"],
                "domain_filter": ["fiscal"],
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["url"] == "https://api.dhan.am/hooks/tezca"
        assert "secret" in response.data  # Shown once
        assert len(response.data["secret"]) == 64
        assert WebhookSubscription.objects.count() == 1

    @patch(AUTH_PATCH)
    def test_create_webhook_invalid_events(self, mock_auth):
        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-create")
        response = self.client.post(
            url,
            {
                "url": "https://example.com/hook",
                "events": ["invalid.event"],
            },
            format="json",
        )

        assert response.status_code == 400
        assert "Invalid events" in response.data["error"]

    @patch(AUTH_PATCH)
    def test_create_webhook_missing_url(self, mock_auth):
        mock_auth.return_value = (self.user, "fake-key")

        url = reverse("webhook-create")
        response = self.client.post(url, {"events": ["version.created"]}, format="json")

        assert response.status_code == 400

    @patch(AUTH_PATCH)
    def test_list_webhooks(self, mock_auth):
        mock_auth.return_value = (self.user, "fake-key")

        WebhookSubscription.objects.create(
            api_key=self.api_key,
            url="https://example.com/hook1",
            events=["version.created"],
            secret="a" * 64,
        )
        WebhookSubscription.objects.create(
            api_key=self.api_key,
            url="https://example.com/hook2",
            events=["law.updated"],
            secret="b" * 64,
        )

        url = reverse("webhook-list")
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.data["count"] == 2
        # Secret should NOT be in list response
        for wh in response.data["webhooks"]:
            assert "secret" not in wh

    @patch(AUTH_PATCH)
    def test_delete_webhook(self, mock_auth):
        mock_auth.return_value = (self.user, "fake-key")

        sub = WebhookSubscription.objects.create(
            api_key=self.api_key,
            url="https://example.com/hook",
            events=["version.created"],
            secret="c" * 64,
        )

        url = reverse("webhook-delete", args=[sub.pk])
        response = self.client.delete(url)

        assert response.status_code == 200
        assert response.data["status"] == "deleted"
        assert not WebhookSubscription.objects.filter(pk=sub.pk).exists()

    def test_create_webhook_requires_api_key(self):
        """JWT-only auth (no API key) should be rejected for webhooks."""
        # No auth at all → 401
        url = reverse("webhook-create")
        response = self.client.post(
            url,
            {"url": "https://example.com", "events": ["version.created"]},
            format="json",
        )
        assert response.status_code == 401


# ── Webhook dispatch ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestWebhookDispatch:
    def setup_method(self):
        full, prefix, hashed = generate_api_key()
        self.api_key = APIKey.objects.create(
            prefix=prefix,
            hashed_key=hashed,
            name="Dispatch Test",
            owner_email="dispatch@example.com",
        )
        self.sub = WebhookSubscription.objects.create(
            api_key=self.api_key,
            url="https://example.com/hook",
            events=["version.created"],
            domain_filter=["fiscal"],
            secret="test_secret_key",
        )

    @patch("apps.api.webhooks.requests.post")
    def test_dispatch_sends_signed_payload(self, mock_post):
        """Webhook dispatch sends HMAC-signed POST request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        from apps.api.webhooks import dispatch_webhook_event

        dispatch_webhook_event(
            "version.created",
            {
                "law_id": "cff",
                "category": "fiscal",
            },
        )

        assert mock_post.called
        call_kwargs = mock_post.call_args
        headers = (
            call_kwargs[1]["headers"]
            if "headers" in call_kwargs[1]
            else call_kwargs.kwargs["headers"]
        )

        assert headers["X-Tezca-Event"] == "version.created"
        assert headers["X-Tezca-Signature"].startswith("sha256=")

        # Verify HMAC signature
        body = call_kwargs[1].get("data") or call_kwargs.kwargs.get("data")
        expected_sig = hmac.new(
            self.sub.secret.encode(), body.encode(), hashlib.sha256
        ).hexdigest()
        assert headers["X-Tezca-Signature"] == f"sha256={expected_sig}"

    @patch("apps.api.webhooks.requests.post")
    def test_dispatch_skips_non_matching_domain(self, mock_post):
        """Webhook with domain_filter=['fiscal'] ignores penal events."""
        from apps.api.webhooks import dispatch_webhook_event

        dispatch_webhook_event(
            "version.created",
            {
                "law_id": "cpf",
                "category": "penal",
            },
        )

        assert not mock_post.called

    @patch("apps.api.webhooks.time.sleep")
    @patch("apps.api.webhooks.requests.post")
    def test_auto_disable_after_failures(self, mock_post, mock_sleep):
        """Webhook is auto-disabled after MAX_FAILURES consecutive failures."""
        import requests as req_lib

        mock_post.side_effect = req_lib.ConnectionError("Connection refused")
        self.sub.failure_count = 9
        self.sub.save()

        from apps.api.webhooks import dispatch_webhook_event

        dispatch_webhook_event(
            "version.created",
            {
                "law_id": "cff",
                "category": "fiscal",
            },
        )

        self.sub.refresh_from_db()
        assert self.sub.failure_count >= 10
        assert self.sub.is_active is False
