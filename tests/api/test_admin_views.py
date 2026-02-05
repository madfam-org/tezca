from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import Law


@pytest.mark.django_db
class TestAdminViews:
    def setup_method(self):
        self.client = APIClient()

        # Create some test data for metrics
        Law.objects.create(
            official_id="law-1", name="Federal Law", tier="0", category="ley"
        )
        Law.objects.create(
            official_id="law-2", name="State Law", tier="1", category="codigo"
        )
        Law.objects.create(
            official_id="law-3", name="Muni Law", tier="2", category="reglamento"
        )

    def test_health_check(self):
        """Test health check endpoint returns 200 and healthy status."""
        url = reverse("admin-health")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert "timestamp" in data

    def test_system_metrics(self):
        """Test metrics aggregation."""
        url = reverse("admin-metrics")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert data["total_laws"] == 3
        # Check tier counts (tier 0=federal, 1=state, 2=municipal)
        assert data["counts"]["federal"] == 1
        assert data["counts"]["state"] == 1
        assert data["counts"]["municipal"] == 1

        assert "top_categories" in data
        assert "quality_distribution" in data

    @patch("apps.api.ingestion_manager.IngestionManager.get_status")
    def test_job_status(self, mock_get_status):
        """Test job status endpoint."""
        # Mock running status
        mock_get_status.return_value = {
            "status": "running",
            "message": "Ingesting...",
            "progress": 50,
            "timestamp": "2024-01-01T12:00:00",
        }

        url = reverse("admin-job-status")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["progress"] == 50

    @patch("apps.api.ingestion_manager.IngestionManager.get_status")
    def test_list_jobs(self, mock_get_status):
        """Test job list endpoint."""
        mock_get_status.return_value = {"status": "idle"}

        url = reverse("admin-jobs-list")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["status"] == "idle"

    @patch("elasticsearch.Elasticsearch")
    @patch("apps.api.admin_views.connection")
    def test_system_config(self, mock_connection, mock_es_class):
        """Test GET /admin/config/ returns all config sections."""
        # Mock database connection check
        mock_connection.ensure_connection.return_value = None

        # Mock Elasticsearch ping success (imported locally inside system_config)
        mock_es = mock_es_class.return_value
        mock_es.ping.return_value = True

        url = reverse("admin-config")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()

        # Verify all four top-level sections exist
        assert "environment" in data
        assert "database" in data
        assert "elasticsearch" in data
        assert "data" in data

        # Verify environment section structure
        assert "debug" in data["environment"]
        assert "allowed_hosts" in data["environment"]
        assert "language" in data["environment"]
        assert "timezone" in data["environment"]

        # Verify database section
        assert "engine" in data["database"]
        assert data["database"]["status"] == "connected"
        assert "name" in data["database"]

        # Verify elasticsearch section
        assert data["elasticsearch"]["status"] == "connected"
        assert "host" in data["elasticsearch"]

        # Verify data section
        assert data["data"]["total_laws"] == 3
        assert data["data"]["total_versions"] == 0
        assert data["data"]["latest_publication"] is None

        # Verify mocks were called
        mock_connection.ensure_connection.assert_called_once()
        mock_es_class.assert_called_once()
        mock_es.ping.assert_called_once()

    @patch("elasticsearch.Elasticsearch")
    @patch("apps.api.admin_views.connection")
    def test_system_config_es_unavailable(self, mock_connection, mock_es_class):
        """Test /admin/config/ when Elasticsearch raises an exception."""
        # Mock database connection check (succeeds)
        mock_connection.ensure_connection.return_value = None

        # Mock Elasticsearch to raise an exception on instantiation (imported locally)
        mock_es_class.side_effect = Exception("Connection refused")

        url = reverse("admin-config")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()

        # ES should report unavailable when an exception is raised
        assert data["elasticsearch"]["status"] == "unavailable"

        # Other sections should still be present and correct
        assert data["database"]["status"] == "connected"
        assert "environment" in data
        assert "data" in data
