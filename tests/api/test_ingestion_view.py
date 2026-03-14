"""Tests for IngestionView — GET status and POST start endpoints.

Covers:
  - GET /ingest/ — returns current ingestion status (admin-protected)
  - POST /ingest/ — starts ingestion, returns 202 or 409 (admin-protected)
  - Unauthorized access returns 401/403
  - Various ingestion parameter combinations
"""

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.middleware.janua_auth import JanuaUser


def _start_admin_patches(test_instance):
    """Bypass JanuaJWT auth + IsTezcaAdmin for admin view tests."""
    admin_user = JanuaUser(
        {"sub": "test-admin", "email": "admin@test.com", "role": "admin"}
    )
    admin_user.tier = "madfam"
    admin_user.scopes = ["read", "search"]
    admin_user.allowed_domains = []
    admin_user.api_key_prefix = ""

    test_instance._auth_patcher = patch(
        "apps.api.middleware.janua_auth.JanuaJWTAuthentication.authenticate",
        return_value=(admin_user, "fake-token"),
    )
    test_instance._admin_patcher = patch(
        "apps.api.middleware.admin_permission.IsTezcaAdmin.has_permission",
        return_value=True,
    )
    test_instance._auth_patcher.start()
    test_instance._admin_patcher.start()


def _stop_admin_patches(test_instance):
    test_instance._admin_patcher.stop()
    test_instance._auth_patcher.stop()


@pytest.mark.django_db
class TestIngestionViewGet:
    """Tests for GET /ingest/ — ingestion status retrieval."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("ingest")
        _start_admin_patches(self)

    def teardown_method(self):
        _stop_admin_patches(self)

    @patch("apps.api.ingestion_manager.IngestionManager.get_status")
    def test_get_idle_status(self, mock_status):
        mock_status.return_value = {
            "status": "idle",
            "message": "No ingestion active",
            "timestamp": "2026-03-01T12:00:00",
        }

        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"
        assert data["message"] == "No ingestion active"

    @patch("apps.api.ingestion_manager.IngestionManager.get_status")
    def test_get_running_status(self, mock_status):
        mock_status.return_value = {
            "status": "running",
            "message": "Indexing laws...",
            "progress": 75,
            "timestamp": "2026-03-01T12:30:00",
        }

        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["progress"] == 75

    @patch("apps.api.ingestion_manager.IngestionManager.get_status")
    def test_get_completed_status(self, mock_status):
        mock_status.return_value = {
            "status": "completed",
            "message": "Ingestion finished successfully",
            "timestamp": "2026-03-01T14:00:00",
        }

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    @patch("apps.api.ingestion_manager.IngestionManager.get_status")
    def test_get_error_status(self, mock_status):
        mock_status.return_value = {
            "status": "error",
            "message": "Execution error: FileNotFoundError",
            "timestamp": "2026-03-01T12:05:00",
        }

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert response.json()["status"] == "error"


@pytest.mark.django_db
class TestIngestionViewPost:
    """Tests for POST /ingest/ — start ingestion."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("ingest")
        _start_admin_patches(self)

    def teardown_method(self):
        _stop_admin_patches(self)

    @patch("apps.api.ingestion_manager.IngestionManager.start_ingestion")
    def test_start_success(self, mock_start):
        mock_start.return_value = (True, "Ingestion started (task abc-123)")

        response = self.client.post(self.url, {}, format="json")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "started"
        assert "abc-123" in data["message"]

    @patch("apps.api.ingestion_manager.IngestionManager.start_ingestion")
    def test_start_conflict(self, mock_start):
        mock_start.return_value = (False, "Ingestion already running")

        response = self.client.post(self.url, {}, format="json")

        assert response.status_code == 409
        data = response.json()
        assert data["status"] == "error"
        assert "already running" in data["message"].lower()

    @patch("apps.api.ingestion_manager.IngestionManager.start_ingestion")
    def test_start_with_params(self, mock_start):
        mock_start.return_value = (True, "Ingestion started")
        params = {"mode": "tier", "tier": "federal", "workers": 2}

        response = self.client.post(self.url, params, format="json")

        assert response.status_code == 202
        # Verify params were passed through
        mock_start.assert_called_once_with(params)

    @patch("apps.api.ingestion_manager.IngestionManager.start_ingestion")
    def test_start_with_all_mode(self, mock_start):
        mock_start.return_value = (True, "Ingestion started")

        response = self.client.post(self.url, {"mode": "all"}, format="json")

        assert response.status_code == 202

    @patch("apps.api.ingestion_manager.IngestionManager.start_ingestion")
    def test_start_with_specific_laws(self, mock_start):
        mock_start.return_value = (True, "Ingestion started")
        params = {"mode": "specific", "laws": "cpeum,cff"}

        response = self.client.post(self.url, params, format="json")

        assert response.status_code == 202
        mock_start.assert_called_once_with(params)


@pytest.mark.django_db
class TestIngestionViewAuth:
    """Tests for ingestion endpoint authentication requirements."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("ingest")

    def test_get_without_auth_returns_403(self):
        """GET /ingest/ without authentication returns 403."""
        response = self.client.get(self.url)
        assert response.status_code in (401, 403)

    def test_post_without_auth_returns_403(self):
        """POST /ingest/ without authentication returns 403."""
        response = self.client.post(self.url, {}, format="json")
        assert response.status_code in (401, 403)

    def test_non_admin_user_returns_403(self):
        """Non-admin user cannot access ingestion endpoint."""
        user = JanuaUser({"sub": "user-123", "email": "user@test.com"})
        user.tier = "essentials"
        user.scopes = ["read"]
        user.allowed_domains = []
        user.api_key_prefix = ""

        with patch(
            "apps.api.middleware.janua_auth.JanuaJWTAuthentication.authenticate",
            return_value=(user, "fake-token"),
        ):
            with patch(
                "apps.api.middleware.admin_permission.IsTezcaAdmin.has_permission",
                return_value=False,
            ):
                response = self.client.get(self.url)

        assert response.status_code == 403
