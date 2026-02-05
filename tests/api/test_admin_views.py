from unittest.mock import patch

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
