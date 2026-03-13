"""Tests for newsletter subscription endpoints."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import NewsletterSubscription


@pytest.mark.django_db
class TestNewsletterSubscribe:
    """Tests for POST /newsletter/subscribe/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("newsletter-subscribe")

    def test_subscribe_new(self):
        """POST with valid email creates subscription and returns 201."""
        response = self.client.post(
            self.url,
            {"email": "user@example.com", "topics": ["federal", "fiscal"]},
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["status"] == "subscribed"
        sub = NewsletterSubscription.objects.get(email="user@example.com")
        assert sub.is_active is True
        assert sub.topics == ["federal", "fiscal"]

    def test_subscribe_already_active(self):
        """POST with already-subscribed email returns already_subscribed."""
        NewsletterSubscription.objects.create(
            email="user@example.com", is_active=True, topics=["federal"]
        )

        response = self.client.post(
            self.url, {"email": "user@example.com"}, format="json"
        )

        assert response.status_code == 200
        assert response.json()["status"] == "already_subscribed"

    def test_subscribe_reactivation(self):
        """POST with previously unsubscribed email reactivates."""
        NewsletterSubscription.objects.create(
            email="user@example.com", is_active=False, topics=["old"]
        )

        response = self.client.post(
            self.url,
            {"email": "user@example.com", "topics": ["new"]},
            format="json",
        )

        assert response.status_code == 200
        assert response.json()["status"] == "resubscribed"
        sub = NewsletterSubscription.objects.get(email="user@example.com")
        assert sub.is_active is True
        assert sub.topics == ["new"]
        assert sub.unsubscribed_at is None

    def test_subscribe_invalid_email(self):
        """POST with invalid email returns 400."""
        response = self.client.post(self.url, {"email": "not-an-email"}, format="json")

        assert response.status_code == 400
        assert "email" in response.json()["error"].lower()

    def test_subscribe_empty_email(self):
        """POST with empty email returns 400."""
        response = self.client.post(self.url, {"email": ""}, format="json")

        assert response.status_code == 400

    def test_subscribe_missing_email(self):
        """POST without email field returns 400."""
        response = self.client.post(self.url, {}, format="json")

        assert response.status_code == 400

    def test_subscribe_normalizes_email(self):
        """POST normalizes email to lowercase and strips whitespace."""
        response = self.client.post(
            self.url, {"email": "  User@Example.COM  "}, format="json"
        )

        assert response.status_code == 201
        assert NewsletterSubscription.objects.filter(email="user@example.com").exists()

    def test_subscribe_invalid_topics_ignored(self):
        """POST with non-list topics defaults to empty list."""
        response = self.client.post(
            self.url,
            {"email": "user@example.com", "topics": "not-a-list"},
            format="json",
        )

        assert response.status_code == 201
        sub = NewsletterSubscription.objects.get(email="user@example.com")
        assert sub.topics == []


@pytest.mark.django_db
class TestNewsletterUnsubscribe:
    """Tests for POST /newsletter/unsubscribe/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("newsletter-unsubscribe")

    def test_unsubscribe_success(self):
        """POST with existing email deactivates subscription."""
        NewsletterSubscription.objects.create(email="user@example.com", is_active=True)

        response = self.client.post(
            self.url, {"email": "user@example.com"}, format="json"
        )

        assert response.status_code == 200
        assert response.json()["status"] == "unsubscribed"
        sub = NewsletterSubscription.objects.get(email="user@example.com")
        assert sub.is_active is False
        assert sub.unsubscribed_at is not None

    def test_unsubscribe_not_found(self):
        """POST with non-existent email returns 404."""
        response = self.client.post(
            self.url, {"email": "nonexistent@example.com"}, format="json"
        )

        assert response.status_code == 404
        assert response.json()["status"] == "not_found"

    def test_unsubscribe_empty_email(self):
        """POST with empty email returns 400."""
        response = self.client.post(self.url, {"email": ""}, format="json")

        assert response.status_code == 400
