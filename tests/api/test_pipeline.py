"""Tests for the data collection pipeline status API and task structure."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestPipelineStatusAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("admin-pipeline-status")

    def test_pipeline_status_idle(self):
        """GET returns idle when no status file exists."""
        with patch("apps.api.admin_views.PIPELINE_STATUS_FILE") as mock_path:
            mock_path.exists.return_value = False
            response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"
        assert "timestamp" in data

    def test_pipeline_status_running(self, tmp_path):
        """GET returns running status from file."""
        status_file = tmp_path / "pipeline_status.json"
        status_data = {
            "status": "running",
            "message": "Phase 2/7: Scrape state laws",
            "phase": "Scrape state laws",
            "phase_number": 2,
            "total_phases": 7,
            "progress": 28,
            "started_at": "2026-02-05T10:00:00+00:00",
            "timestamp": "2026-02-05T10:05:00+00:00",
            "task_id": "abc-123",
            "phase_results": [
                {
                    "phase": "Scrape federal catalog",
                    "phase_number": 1,
                    "returncode": 0,
                    "status": "success",
                    "duration": "1.5m",
                }
            ],
        }
        status_file.write_text(json.dumps(status_data))

        with patch("apps.api.admin_views.PIPELINE_STATUS_FILE", status_file):
            response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["phase"] == "Scrape state laws"
        assert data["phase_number"] == 2
        assert data["progress"] == 28
        assert len(data["phase_results"]) == 1

    def test_pipeline_status_completed(self, tmp_path):
        """GET returns completed status with phase results and summary."""
        status_file = tmp_path / "pipeline_status.json"
        status_data = {
            "status": "completed",
            "message": "Pipeline finished: 7/7 phases succeeded",
            "phase": "done",
            "phase_number": 7,
            "total_phases": 7,
            "progress": 100,
            "started_at": "2026-02-05T10:00:00+00:00",
            "completed_at": "2026-02-05T22:00:00+00:00",
            "duration_human": "12.0h",
            "timestamp": "2026-02-05T22:00:00+00:00",
            "task_id": "abc-123",
            "phase_results": [
                {
                    "phase": f"Phase {i}",
                    "phase_number": i,
                    "returncode": 0,
                    "status": "success",
                    "duration": "1.0m",
                }
                for i in range(1, 8)
            ],
            "summary": {
                "total_phases": 7,
                "succeeded": 7,
                "failed": 0,
            },
        }
        status_file.write_text(json.dumps(status_data))

        with patch("apps.api.admin_views.PIPELINE_STATUS_FILE", status_file):
            response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert data["summary"]["succeeded"] == 7
        assert data["summary"]["failed"] == 0
        assert len(data["phase_results"]) == 7

    def test_pipeline_status_completed_with_errors(self, tmp_path):
        """GET returns completed_with_errors when some phases failed."""
        status_file = tmp_path / "pipeline_status.json"
        status_data = {
            "status": "completed_with_errors",
            "message": "Pipeline finished: 5/7 phases succeeded",
            "phase": "done",
            "phase_number": 7,
            "total_phases": 7,
            "progress": 100,
            "started_at": "2026-02-05T10:00:00+00:00",
            "completed_at": "2026-02-05T22:00:00+00:00",
            "duration_human": "12.0h",
            "timestamp": "2026-02-05T22:00:00+00:00",
            "task_id": "abc-123",
            "phase_results": [],
            "summary": {
                "total_phases": 7,
                "succeeded": 5,
                "failed": 2,
            },
        }
        status_file.write_text(json.dumps(status_data))

        with patch("apps.api.admin_views.PIPELINE_STATUS_FILE", status_file):
            response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed_with_errors"
        assert data["summary"]["failed"] == 2


class TestPipelineTaskStructure:
    """Test that pipeline phases are built correctly from params."""

    def test_default_phases(self):
        """All phases present with no skip flags."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases(None)
        names = [p["name"] for p in phases]

        assert "Scrape federal catalog" in names
        assert "Scrape state laws" in names
        assert "Scrape municipal laws" in names
        assert "Scrape municipal laws (OJN)" in names
        assert "Consolidate state metadata" in names
        assert "Consolidate municipal metadata" in names
        assert "Parse state laws to AKN XML" in names
        assert "Parse municipal laws to AKN XML" in names
        assert "Ingest federal laws" in names
        assert "Ingest state laws" in names
        assert "Ingest municipal laws" in names
        assert "Index to Elasticsearch" in names
        assert len(phases) == 12

    def test_skip_scrape(self):
        """--skip-scrape removes all scraping phases."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases({"skip_scrape": True})
        names = [p["name"] for p in phases]

        assert "Scrape federal catalog" not in names
        assert "Scrape state laws" not in names
        assert "Scrape municipal laws" not in names
        # Consolidate x2 + parse x2 + ingest x3 + index = 8
        assert len(phases) == 8

    def test_skip_states(self):
        """--skip-states removes only state scraping."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases({"skip_states": True})
        names = [p["name"] for p in phases]

        assert "Scrape federal catalog" in names
        assert "Scrape state laws" not in names
        assert "Scrape municipal laws" in names
        assert "Parse state laws to AKN XML" not in names
        assert "Parse municipal laws to AKN XML" in names
        assert len(phases) == 10

    def test_skip_municipal(self):
        """--skip-municipal removes municipal scraping, consolidation, ingestion."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases({"skip_municipal": True})
        names = [p["name"] for p in phases]

        assert "Scrape municipal laws" not in names
        assert "Scrape municipal laws (OJN)" not in names
        assert "Consolidate municipal metadata" not in names
        assert "Parse municipal laws to AKN XML" not in names
        assert "Ingest municipal laws" not in names
        assert "Scrape state laws" in names
        assert "Parse state laws to AKN XML" in names
        assert len(phases) == 7

    def test_skip_index(self):
        """--skip-index removes ES indexing phase."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases({"skip_index": True})
        names = [p["name"] for p in phases]

        assert "Index to Elasticsearch" not in names
        assert len(phases) == 11

    def test_skip_all(self):
        """Skip scrape + index leaves consolidate + ingest only."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases(
            {
                "skip_scrape": True,
                "skip_index": True,
            }
        )
        names = [p["name"] for p in phases]

        assert names == [
            "Consolidate state metadata",
            "Consolidate municipal metadata",
            "Parse state laws to AKN XML",
            "Parse municipal laws to AKN XML",
            "Ingest federal laws",
            "Ingest state laws",
            "Ingest municipal laws",
        ]

    def test_skip_municipal_ojn(self):
        """--skip-municipal-ojn removes only OJN municipal scraping."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases({"skip_municipal_ojn": True})
        names = [p["name"] for p in phases]

        assert "Scrape municipal laws" in names
        assert "Scrape municipal laws (OJN)" not in names
        assert len(phases) == 11

    def test_workers_param(self):
        """Workers param flows through to ingest federal command."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases({"workers": 8})
        ingest_phase = next(p for p in phases if p["name"] == "Ingest federal laws")
        assert "--workers" in ingest_phase["cmd"]
        idx = ingest_phase["cmd"].index("--workers")
        assert ingest_phase["cmd"][idx + 1] == "8"

    def test_force_flag_in_ingest(self):
        """Ingest federal always has --force flag."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases(None)
        ingest_phase = next(p for p in phases if p["name"] == "Ingest federal laws")
        assert "--force" in ingest_phase["cmd"]

    def test_state_scraper_cwd(self):
        """State scraper runs with cwd=scripts/scraping/."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases(None)
        state_phase = next(p for p in phases if p["name"] == "Scrape state laws")
        assert state_phase["cwd"].endswith("scripts/scraping")
