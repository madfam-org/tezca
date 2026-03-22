"""Tests for feature interest capture endpoints."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import FeatureInterest


@pytest.mark.django_db
class TestRegisterInterest:
    """Tests for POST /interest/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("register-interest")

    def test_register_new(self):
        """POST with valid data creates interest and returns 201."""
        response = self.client.post(
            self.url,
            {
                "email": "user@example.com",
                "feature_key": "latex_export",
                "use_case": "research",
                "source_page": "export_dropdown",
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["status"] == "registered"
        interest = FeatureInterest.objects.get(email="user@example.com")
        assert interest.feature_key == "latex_export"
        assert interest.use_case == "research"
        assert interest.source_page == "export_dropdown"

    def test_register_duplicate(self):
        """POST with same email+feature returns 200 already_registered."""
        FeatureInterest.objects.create(
            email="user@example.com", feature_key="latex_export"
        )

        response = self.client.post(
            self.url,
            {"email": "user@example.com", "feature_key": "latex_export"},
            format="json",
        )

        assert response.status_code == 200
        assert response.json()["status"] == "already_registered"

    def test_register_same_email_different_feature(self):
        """Same email with different feature_key creates new record."""
        FeatureInterest.objects.create(
            email="user@example.com", feature_key="latex_export"
        )

        response = self.client.post(
            self.url,
            {"email": "user@example.com", "feature_key": "docx_export"},
            format="json",
        )

        assert response.status_code == 201
        assert FeatureInterest.objects.filter(email="user@example.com").count() == 2

    def test_invalid_email(self):
        """POST with invalid email returns 400."""
        response = self.client.post(
            self.url,
            {"email": "not-an-email", "feature_key": "latex_export"},
            format="json",
        )

        assert response.status_code == 400
        assert "email" in response.json()["error"].lower()

    def test_empty_email(self):
        """POST with empty email returns 400."""
        response = self.client.post(
            self.url,
            {"email": "", "feature_key": "latex_export"},
            format="json",
        )

        assert response.status_code == 400

    def test_missing_email(self):
        """POST without email field returns 400."""
        response = self.client.post(
            self.url,
            {"feature_key": "latex_export"},
            format="json",
        )

        assert response.status_code == 400

    def test_invalid_feature_key(self):
        """POST with unknown feature_key returns 400."""
        response = self.client.post(
            self.url,
            {"email": "user@example.com", "feature_key": "nonexistent_feature"},
            format="json",
        )

        assert response.status_code == 400
        assert "feature_key" in response.json()["error"].lower()

    def test_missing_feature_key(self):
        """POST without feature_key returns 400."""
        response = self.client.post(
            self.url,
            {"email": "user@example.com"},
            format="json",
        )

        assert response.status_code == 400

    def test_normalizes_email(self):
        """POST normalizes email to lowercase and strips whitespace."""
        response = self.client.post(
            self.url,
            {"email": "  User@Example.COM  ", "feature_key": "webhooks"},
            format="json",
        )

        assert response.status_code == 201
        assert FeatureInterest.objects.filter(email="user@example.com").exists()

    def test_supplementary_field_update_on_duplicate(self):
        """Re-registration fills in empty supplementary fields."""
        FeatureInterest.objects.create(
            email="user@example.com",
            feature_key="latex_export",
            use_case="",
            janua_user_id="",
            source_page="",
        )

        response = self.client.post(
            self.url,
            {
                "email": "user@example.com",
                "feature_key": "latex_export",
                "use_case": "research",
                "janua_user_id": "uid_123",
                "source_page": "pricing",
            },
            format="json",
        )

        assert response.status_code == 200
        interest = FeatureInterest.objects.get(
            email="user@example.com", feature_key="latex_export"
        )
        assert interest.use_case == "research"
        assert interest.janua_user_id == "uid_123"
        assert interest.source_page == "pricing"

    def test_supplementary_fields_not_overwritten(self):
        """Re-registration does not overwrite existing supplementary fields."""
        FeatureInterest.objects.create(
            email="user@example.com",
            feature_key="latex_export",
            use_case="work",
            janua_user_id="uid_original",
            source_page="search",
        )

        response = self.client.post(
            self.url,
            {
                "email": "user@example.com",
                "feature_key": "latex_export",
                "use_case": "research",
                "janua_user_id": "uid_new",
                "source_page": "pricing",
            },
            format="json",
        )

        assert response.status_code == 200
        interest = FeatureInterest.objects.get(
            email="user@example.com", feature_key="latex_export"
        )
        assert interest.use_case == "work"
        assert interest.janua_user_id == "uid_original"
        assert interest.source_page == "search"

    def test_all_allowed_features(self):
        """All allowed feature_key values are accepted."""
        for i, feature in enumerate(FeatureInterest.ALLOWED_FEATURES):
            response = self.client.post(
                self.url,
                {"email": f"user{i}@example.com", "feature_key": feature},
                format="json",
            )
            assert response.status_code == 201, f"Failed for feature: {feature}"

    def test_optional_fields_default_empty(self):
        """Optional fields default to empty strings."""
        self.client.post(
            self.url,
            {"email": "user@example.com", "feature_key": "graph_api"},
            format="json",
        )

        interest = FeatureInterest.objects.get(email="user@example.com")
        assert interest.use_case == ""
        assert interest.janua_user_id == ""
        assert interest.source_page == ""
        assert interest.wishlist == ""

    def test_wishlist_field_accepted(self):
        """POST with wishlist field stores it correctly."""
        response = self.client.post(
            self.url,
            {
                "email": "user@example.com",
                "feature_key": "webhooks",
                "wishlist": "I need real-time notifications for legislative changes",
            },
            format="json",
        )

        assert response.status_code == 201
        interest = FeatureInterest.objects.get(email="user@example.com")
        assert (
            interest.wishlist
            == "I need real-time notifications for legislative changes"
        )

    def test_wishlist_capped_at_2000_chars(self):
        """Wishlist text is truncated to 2000 characters."""
        long_text = "x" * 3000
        response = self.client.post(
            self.url,
            {
                "email": "user@example.com",
                "feature_key": "webhooks",
                "wishlist": long_text,
            },
            format="json",
        )

        assert response.status_code == 201
        interest = FeatureInterest.objects.get(email="user@example.com")
        assert len(interest.wishlist) == 2000

    def test_wishlist_filled_on_reregistration(self):
        """Re-registration fills in wishlist when previously empty."""
        FeatureInterest.objects.create(
            email="user@example.com",
            feature_key="webhooks",
            wishlist="",
        )

        response = self.client.post(
            self.url,
            {
                "email": "user@example.com",
                "feature_key": "webhooks",
                "wishlist": "Need webhook filtering by domain",
            },
            format="json",
        )

        assert response.status_code == 200
        interest = FeatureInterest.objects.get(
            email="user@example.com", feature_key="webhooks"
        )
        assert interest.wishlist == "Need webhook filtering by domain"

    def test_wishlist_not_overwritten_on_reregistration(self):
        """Re-registration does not overwrite existing wishlist."""
        FeatureInterest.objects.create(
            email="user@example.com",
            feature_key="webhooks",
            wishlist="Original wishlist text",
        )

        response = self.client.post(
            self.url,
            {
                "email": "user@example.com",
                "feature_key": "webhooks",
                "wishlist": "New text",
            },
            format="json",
        )

        assert response.status_code == 200
        interest = FeatureInterest.objects.get(
            email="user@example.com", feature_key="webhooks"
        )
        assert interest.wishlist == "Original wishlist text"
