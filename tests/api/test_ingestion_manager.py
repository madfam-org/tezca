"""Tests for IngestionManager — status tracking, command building, concurrency.

Covers:
  - get_status() — idle, running, error, file missing, corrupt JSON
  - start_ingestion() — Celery first, thread fallback, conflict prevention
  - _build_command() — various parameter combinations
  - _update_status_message() — partial status file updates
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.api.ingestion_manager import IngestionManager


class TestGetStatus:
    """Tests for IngestionManager.get_status()."""

    @patch("apps.api.ingestion_manager.STATUS_FILE")
    @patch("apps.api.ingestion_manager.IngestionManager._ensure_paths")
    def test_idle_when_no_status_file(self, mock_ensure, mock_file):
        mock_file.exists.return_value = False

        result = IngestionManager.get_status()

        assert result["status"] == "idle"
        assert result["message"] == "No ingestion active"
        assert "timestamp" in result

    def test_reads_existing_status_file(self, tmp_path):
        status_file = tmp_path / "ingestion_status.json"
        status_data = {
            "status": "running",
            "message": "Indexing laws...",
            "progress": 50,
            "timestamp": "2026-03-01T12:00:00",
        }
        status_file.write_text(json.dumps(status_data))

        with patch("apps.api.ingestion_manager.STATUS_FILE", status_file):
            with patch("apps.api.ingestion_manager.IngestionManager._ensure_paths"):
                result = IngestionManager.get_status()

        assert result["status"] == "running"
        assert result["progress"] == 50

    def test_handles_corrupt_json(self, tmp_path):
        status_file = tmp_path / "ingestion_status.json"
        status_file.write_text("not valid json {{{")

        with patch("apps.api.ingestion_manager.STATUS_FILE", status_file):
            with patch("apps.api.ingestion_manager.IngestionManager._ensure_paths"):
                result = IngestionManager.get_status()

        assert result["status"] == "error"
        assert "Failed to read ingestion status" in result["message"]

    def test_handles_permission_error(self, tmp_path):
        status_file = tmp_path / "ingestion_status.json"
        status_file.write_text('{"status": "running"}')

        with patch("apps.api.ingestion_manager.STATUS_FILE", status_file):
            with patch("apps.api.ingestion_manager.IngestionManager._ensure_paths"):
                with patch("builtins.open", side_effect=PermissionError("denied")):
                    result = IngestionManager.get_status()

        assert result["status"] == "error"

    def test_returns_completed_status(self, tmp_path):
        status_file = tmp_path / "ingestion_status.json"
        status_data = {
            "status": "completed",
            "message": "Ingestion finished successfully",
            "timestamp": "2026-03-01T14:00:00",
        }
        status_file.write_text(json.dumps(status_data))

        with patch("apps.api.ingestion_manager.STATUS_FILE", status_file):
            with patch("apps.api.ingestion_manager.IngestionManager._ensure_paths"):
                result = IngestionManager.get_status()

        assert result["status"] == "completed"

    def test_returns_failed_status(self, tmp_path):
        status_file = tmp_path / "ingestion_status.json"
        status_data = {
            "status": "failed",
            "message": "Ingestion failed with code 1",
            "timestamp": "2026-03-01T13:00:00",
        }
        status_file.write_text(json.dumps(status_data))

        with patch("apps.api.ingestion_manager.STATUS_FILE", status_file):
            with patch("apps.api.ingestion_manager.IngestionManager._ensure_paths"):
                result = IngestionManager.get_status()

        assert result["status"] == "failed"
        assert "failed with code" in result["message"]


class TestStartIngestion:
    """Tests for IngestionManager.start_ingestion()."""

    @patch("apps.api.ingestion_manager.IngestionManager.get_status")
    def test_prevents_concurrent_ingestion(self, mock_status):
        """Cannot start when already running."""
        mock_status.return_value = {"status": "running", "message": "Active"}

        success, message = IngestionManager.start_ingestion()

        assert success is False
        assert "already running" in message.lower()

    @patch("apps.api.ingestion_manager.IngestionManager._ensure_paths")
    @patch("apps.api.ingestion_manager.IngestionManager.get_status")
    def test_tries_celery_first(self, mock_status, mock_paths):
        """Attempts Celery dispatch before thread fallback."""
        mock_status.return_value = {"status": "idle"}

        mock_task = MagicMock()
        mock_task.delay.return_value = MagicMock(id="task-123")

        with patch("apps.api.tasks.run_ingestion", mock_task):
            success, message = IngestionManager.start_ingestion({"mode": "all"})

        assert success is True
        assert "task-123" in message

    @patch("apps.api.ingestion_manager.IngestionManager._ensure_paths")
    @patch("apps.api.ingestion_manager.IngestionManager.get_status")
    def test_falls_back_to_thread(self, mock_status, mock_paths, tmp_path):
        """Falls back to thread when Celery broker is unavailable."""
        mock_status.return_value = {"status": "idle"}

        # Make run_ingestion.delay() raise (simulating broker unavailable)
        mock_task = MagicMock()
        mock_task.delay.side_effect = Exception("Redis connection refused")

        status_file = tmp_path / "ingestion_status.json"
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        with patch("apps.api.tasks.run_ingestion", mock_task):
            with patch("apps.api.ingestion_manager.STATUS_FILE", status_file):
                with patch("apps.api.ingestion_manager.DATA_DIR", data_dir):
                    with patch("threading.Thread") as mock_thread:
                        mock_thread_instance = MagicMock()
                        mock_thread.return_value = mock_thread_instance

                        success, message = IngestionManager.start_ingestion()

        assert success is True
        assert "thread fallback" in message.lower()
        mock_thread_instance.start.assert_called_once()


class TestBuildCommand:
    """Tests for IngestionManager._build_command()."""

    def test_default_command(self):
        cmd = IngestionManager._build_command(None)
        assert cmd == ["python", "scripts/ingestion/bulk_ingest.py"]

    def test_mode_all(self):
        cmd = IngestionManager._build_command({"mode": "all"})
        assert "--all" in cmd

    def test_mode_priority(self):
        cmd = IngestionManager._build_command({"mode": "priority", "priority_level": 2})
        assert "--priority" in cmd
        idx = cmd.index("--priority")
        assert cmd[idx + 1] == "2"

    def test_mode_priority_default_level(self):
        """Priority mode defaults to level 1 if not specified."""
        cmd = IngestionManager._build_command({"mode": "priority"})
        assert "--priority" in cmd
        idx = cmd.index("--priority")
        assert cmd[idx + 1] == "1"

    def test_mode_specific_laws(self):
        cmd = IngestionManager._build_command({"mode": "specific", "laws": "cpeum,cff"})
        assert "--laws" in cmd
        idx = cmd.index("--laws")
        assert cmd[idx + 1] == "cpeum,cff"

    def test_mode_specific_without_laws_skips(self):
        """Specific mode without laws param does not add --laws flag."""
        cmd = IngestionManager._build_command({"mode": "specific"})
        assert "--laws" not in cmd

    def test_mode_tier(self):
        cmd = IngestionManager._build_command({"mode": "tier", "tier": "federal"})
        assert "--tier" in cmd
        idx = cmd.index("--tier")
        assert cmd[idx + 1] == "federal"

    def test_mode_tier_without_tier_param(self):
        """Tier mode without tier param does not add --tier flag."""
        cmd = IngestionManager._build_command({"mode": "tier"})
        assert "--tier" not in cmd

    def test_skip_download_flag(self):
        cmd = IngestionManager._build_command({"skip_download": True})
        assert "--skip-download" in cmd

    def test_no_skip_download(self):
        cmd = IngestionManager._build_command({"skip_download": False})
        assert "--skip-download" not in cmd

    def test_workers_param(self):
        cmd = IngestionManager._build_command({"workers": 8})
        assert "--workers" in cmd
        idx = cmd.index("--workers")
        assert cmd[idx + 1] == "8"

    def test_combined_params(self):
        cmd = IngestionManager._build_command(
            {"mode": "all", "skip_download": True, "workers": 2}
        )
        assert "--all" in cmd
        assert "--skip-download" in cmd
        assert "--workers" in cmd
        idx = cmd.index("--workers")
        assert cmd[idx + 1] == "2"

    def test_empty_params(self):
        """Empty params dict produces base command only."""
        cmd = IngestionManager._build_command({})
        assert cmd == ["python", "scripts/ingestion/bulk_ingest.py"]


class TestUpdateStatusMessage:
    """Tests for IngestionManager._update_status_message()."""

    def test_updates_message_in_existing_file(self, tmp_path):
        status_file = tmp_path / "ingestion_status.json"
        status_file.write_text(json.dumps({"status": "running", "message": "old"}))

        with patch("apps.api.ingestion_manager.STATUS_FILE", status_file):
            IngestionManager._update_status_message("Indexing law 5/100")

        result = json.loads(status_file.read_text())
        assert result["status"] == "running"
        assert result["message"] == "Indexing law 5/100"
        assert "timestamp" in result

    def test_creates_default_when_file_missing(self, tmp_path):
        status_file = tmp_path / "nonexistent_status.json"

        with patch("apps.api.ingestion_manager.STATUS_FILE", status_file):
            # Should not crash even if file doesn't exist
            IngestionManager._update_status_message("Starting...")

    def test_handles_corrupt_file_gracefully(self, tmp_path):
        status_file = tmp_path / "ingestion_status.json"
        status_file.write_text("corrupt json")

        with patch("apps.api.ingestion_manager.STATUS_FILE", status_file):
            # Should not raise — method catches exceptions internally
            IngestionManager._update_status_message("Update")


class TestEnsurePaths:
    """Tests for IngestionManager._ensure_paths()."""

    def test_creates_directories(self, tmp_path):
        data_dir = tmp_path / "testdata"

        with patch("apps.api.ingestion_manager.DATA_DIR", data_dir):
            IngestionManager._ensure_paths()

        assert data_dir.exists()
        assert (data_dir / "logs").exists()

    def test_idempotent(self, tmp_path):
        """Calling _ensure_paths twice does not raise."""
        data_dir = tmp_path / "testdata"

        with patch("apps.api.ingestion_manager.DATA_DIR", data_dir):
            IngestionManager._ensure_paths()
            IngestionManager._ensure_paths()  # Should not raise

        assert data_dir.exists()
