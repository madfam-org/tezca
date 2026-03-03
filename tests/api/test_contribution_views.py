"""Tests for contribution API endpoints."""

import uuid

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import Contribution


@pytest.mark.django_db
class TestSubmitContribution:
    """Tests for POST /contributions/"""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("contribution-submit")
        self.valid_payload = {
            "submitter_name": "Ana Garcia",
            "submitter_email": "ana@example.com",
            "submitter_institution": "UNAM",
            "data_type": "federal",
            "jurisdiction": "federal",
            "description": "Ley General de Salud actualizada 2025",
            "file_url": "https://example.com/salud.pdf",
            "file_format": "pdf",
        }

    def test_submit_contribution_success(self):
        response = self.client.post(self.url, self.valid_payload, format="json")

        assert response.status_code == 201
        data = response.json()
        assert data["submitter_name"] == "Ana Garcia"
        assert data["submitter_email"] == "ana@example.com"
        assert data["status"] == "pending"
        assert data["data_type"] == "federal"
        assert Contribution.objects.count() == 1

        record = Contribution.objects.first()
        assert record.status == "pending"
        assert record.submitter_institution == "UNAM"

    def test_submit_contribution_missing_fields(self):
        # Missing required fields: submitter_name, submitter_email, data_type, description
        response = self.client.post(
            self.url,
            {"submitter_name": "Ana Garcia"},
            format="json",
        )

        assert response.status_code == 400
        errors = response.json()
        assert "submitter_email" in errors
        assert "data_type" in errors
        assert "description" in errors
        assert Contribution.objects.count() == 0

    def test_submit_contribution_invalid_email(self):
        payload = {**self.valid_payload, "submitter_email": "not-an-email"}
        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == 400
        errors = response.json()
        assert "submitter_email" in errors

    def test_submit_contribution_invalid_data_type(self):
        payload = {**self.valid_payload, "data_type": "invalid_type"}
        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == 400
        errors = response.json()
        assert "data_type" in errors

    def test_submit_contribution_optional_fields_default(self):
        """Optional fields default to empty strings when omitted."""
        payload = {
            "submitter_name": "Test User",
            "submitter_email": "test@example.com",
            "data_type": "state",
            "description": "Missing optional fields test",
        }
        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == 201
        record = Contribution.objects.first()
        assert record.submitter_institution == ""
        assert record.file_url == ""
        assert record.file_format == ""
        assert record.jurisdiction == ""


@pytest.mark.django_db
class TestSubmitExpertContact:
    """Tests for POST /contributions/expert/"""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("expert-contact")
        self.valid_payload = {
            "name": "Dr. Roberto Hernandez",
            "email": "roberto@itam.mx",
            "institution": "ITAM",
            "expertise_area": "Derecho fiscal mexicano",
            "how_can_help": "Puedo verificar leyes fiscales y NOMs",
            "contact_preference": "email",
        }

    def test_submit_expert_contact_success(self):
        response = self.client.post(self.url, self.valid_payload, format="json")

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert "id" in data
        assert data["message"] == "Thank you!"

        assert Contribution.objects.count() == 1
        record = Contribution.objects.first()
        assert record.submitter_name == "Dr. Roberto Hernandez"
        assert record.submitter_email == "roberto@itam.mx"
        assert record.data_type == "other"
        assert "Derecho fiscal mexicano" in record.description
        assert "verificar leyes fiscales" in record.description

    def test_submit_expert_contact_missing_fields(self):
        # Missing required fields: name, email, expertise_area, how_can_help
        response = self.client.post(
            self.url,
            {"name": "Test"},
            format="json",
        )

        assert response.status_code == 400
        errors = response.json()
        assert "email" in errors
        assert "expertise_area" in errors
        assert "how_can_help" in errors

    def test_submit_expert_contact_invalid_email(self):
        payload = {**self.valid_payload, "email": "bad-email"}
        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == 400
        assert "email" in response.json()


@pytest.mark.django_db
class TestListContributions:
    """Tests for GET /admin/contributions/"""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("admin-contributions")
        uid = uuid.uuid4().hex[:8]

        # Create contributions with different statuses
        Contribution.objects.create(
            submitter_name=f"User A {uid}",
            submitter_email="a@example.com",
            data_type="federal",
            description="Federal law contribution",
            status="pending",
        )
        Contribution.objects.create(
            submitter_name=f"User B {uid}",
            submitter_email="b@example.com",
            data_type="state",
            description="State law contribution",
            status="approved",
        )
        Contribution.objects.create(
            submitter_name=f"User C {uid}",
            submitter_email="c@example.com",
            data_type="municipal",
            description="Municipal regs contribution",
            status="pending",
        )

    def _auth_get(self, url, **kwargs):
        """
        GET request bypassing Janua auth.

        The admin-contributions endpoint is protected by _protected() which
        applies JanuaJWTAuthentication + IsAuthenticated. We patch the
        authentication to bypass it in tests.
        """
        from unittest.mock import patch

        from django.contrib.auth.models import AnonymousUser

        class FakeUser:
            is_authenticated = True

        with patch(
            "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate",
            return_value=(FakeUser(), "fake-token"),
        ):
            return self.client.get(url, **kwargs)

    def test_list_contributions(self):
        response = self._auth_get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_list_contributions_filter_status(self):
        response = self._auth_get(f"{self.url}?status=pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for item in data:
            assert item["status"] == "pending"

    def test_list_contributions_filter_approved(self):
        response = self._auth_get(f"{self.url}?status=approved")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "approved"

    def test_list_contributions_filter_empty_result(self):
        response = self._auth_get(f"{self.url}?status=rejected")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
