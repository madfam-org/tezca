"""
Tests for the catalog-ingest Celery tasks in apps/scraper/scheduling/tasks.py.

Split out of test_scheduling_tasks.py when the wiring-gap fix series
(#140/#141/#146/#156/#159/#162) pushed that file past the 800-line audit
gate — these classes all follow the same 3-test pattern (no-op / happy /
error) against the dataops.ingest_*_catalog task family.
"""

from unittest.mock import patch

# ── ingest_judicial_batches ───────────────────────────────────────────


class TestIngestJudicialBatches:
    def test_no_batch_files_short_circuits(self, tmp_path, monkeypatch):
        """When there are no batch files the task no-ops cleanly."""
        from apps.scraper.scheduling import tasks

        # Use cwd manipulation: easier than mocking Path globally
        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_judicial_batches()
        assert result["status"] == "no_files"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_ingest_when_files_present(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        # The Playwright scraper writes into per-type subdirectories, not a
        # flat data/judicial/batches — the task must recurse to find them.
        batch_dir = tmp_path / "data" / "judicial" / "jurisprudencia"
        batch_dir.mkdir(parents=True)
        (batch_dir / "batch_0000.json").write_text("[]")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_judicial_batches()
        assert result["status"] == "completed"
        mock_call_command.assert_called_once()
        # reads from the judicial root, not the nonexistent .../batches
        assert mock_call_command.call_args.kwargs["dir"] == "data/judicial"


# ── ingest_conamer_catalog ────────────────────────────────────────────


class TestIngestConamerCatalog:
    def test_no_catalog_short_circuits(self, tmp_path, monkeypatch):
        """No discovered_conamer.json and no batch files → clean no-op."""
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_conamer_catalog()
        assert result["status"] == "no_files"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_ingest_when_catalog_present(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        conamer_dir = tmp_path / "data" / "conamer"
        conamer_dir.mkdir(parents=True)
        (conamer_dir / "discovered_conamer.json").write_text("[]")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_conamer_catalog()
        assert result["status"] == "completed"
        mock_call_command.assert_called_once_with("ingest_conamer", all=True)

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_ingest_from_batch_files(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        conamer_dir = tmp_path / "data" / "conamer"
        conamer_dir.mkdir(parents=True)
        (conamer_dir / "batch_0000.json").write_text("[]")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_conamer_catalog()
        assert result["status"] == "completed"
        mock_call_command.assert_called_once_with("ingest_conamer", all=True)


# ── ingest_rmf_catalog ────────────────────────────────────────────────


class TestIngestRmfCatalog:
    def test_no_catalog_short_circuits(self, tmp_path, monkeypatch):
        """No data/rmf/catalog.json → clean no-op."""
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_rmf_catalog()
        assert result["status"] == "no_files"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_ingest_when_catalog_present(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        rmf_dir = tmp_path / "data" / "rmf"
        rmf_dir.mkdir(parents=True)
        (rmf_dir / "catalog.json").write_text("{}")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_rmf_catalog()
        assert result["status"] == "completed"
        mock_call_command.assert_called_once_with(
            "ingest_rmf", catalog="data/rmf/catalog.json"
        )

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_error_is_reported_not_raised(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        rmf_dir = tmp_path / "data" / "rmf"
        rmf_dir.mkdir(parents=True)
        (rmf_dir / "catalog.json").write_text("{}")
        mock_call_command.side_effect = RuntimeError("ingest boom")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_rmf_catalog()
        assert result["status"] == "error"
        assert "ingest boom" in result["error"]


# ── ingest_nom_catalog ────────────────────────────────────────────────


class TestIngestNomCatalog:
    def test_no_catalog_short_circuits(self, tmp_path, monkeypatch):
        """No data/noms/discovered_noms.json → clean no-op."""
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_nom_catalog()
        assert result["status"] == "no_files"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_ingest_when_catalog_present(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        noms_dir = tmp_path / "data" / "noms"
        noms_dir.mkdir(parents=True)
        (noms_dir / "discovered_noms.json").write_text("[]")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_nom_catalog()
        assert result["status"] == "completed"
        mock_call_command.assert_called_once_with(
            "ingest_noms", catalog="data/noms/discovered_noms.json"
        )

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_error_is_reported_not_raised(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        noms_dir = tmp_path / "data" / "noms"
        noms_dir.mkdir(parents=True)
        (noms_dir / "discovered_noms.json").write_text("[]")
        mock_call_command.side_effect = RuntimeError("nom boom")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_nom_catalog()
        assert result["status"] == "error"
        assert "nom boom" in result["error"]


# ── ingest_treaty_catalog ─────────────────────────────────────────────


class TestIngestTreatyCatalog:
    def test_no_catalog_short_circuits(self, tmp_path, monkeypatch):
        """No discovered_treaties.json → clean no-op."""
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_treaty_catalog()
        assert result["status"] == "no_files"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_ingest_when_catalog_present(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        treaties_dir = tmp_path / "data" / "treaties"
        treaties_dir.mkdir(parents=True)
        (treaties_dir / "discovered_treaties.json").write_text("[]")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_treaty_catalog()
        assert result["status"] == "completed"
        mock_call_command.assert_called_once_with("ingest_treaties", all=True)

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_error_is_reported_not_raised(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        treaties_dir = tmp_path / "data" / "treaties"
        treaties_dir.mkdir(parents=True)
        (treaties_dir / "discovered_treaties.json").write_text("[]")
        mock_call_command.side_effect = RuntimeError("treaty boom")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_treaty_catalog()
        assert result["status"] == "error"
        assert "treaty boom" in result["error"]
