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


# ── ingest_state_catalogs ─────────────────────────────────────────────


class TestIngestStateCatalogs:
    def test_no_catalogs_short_circuits(self, tmp_path, monkeypatch):
        """No data/state_laws/*/catalog.json → clean no-op."""
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_state_catalogs()
        assert result["status"] == "no_files"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_ingest_when_catalog_present(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        state_dir = tmp_path / "data" / "state_laws" / "guerrero"
        state_dir.mkdir(parents=True)
        (state_dir / "catalog.json").write_text("[]")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_state_catalogs()
        assert result["status"] == "completed"
        mock_call_command.assert_called_once_with("ingest_state_catalogs", all=True)

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_error_is_reported_not_raised(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        state_dir = tmp_path / "data" / "state_laws" / "guerrero"
        state_dir.mkdir(parents=True)
        (state_dir / "catalog.json").write_text("[]")
        mock_call_command.side_effect = RuntimeError("state boom")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_state_catalogs()
        assert result["status"] == "error"
        assert "state boom" in result["error"]


# ── reindex_law ───────────────────────────────────────────────────────


class TestReindexLaw:
    def test_missing_law_id_is_rejected(self):
        """No law_id → error before any command runs."""
        from apps.scraper.scheduling import tasks

        assert tasks.reindex_law("")["status"] == "error"
        assert tasks.reindex_law("   ")["status"] == "error"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_index_laws_in_place_for_the_law(
        self, mock_call_command, mock_log_cls
    ):
        """Happy path calls index_laws with law_id and NO --reindex/--all."""
        from apps.scraper.scheduling import tasks

        result = tasks.reindex_law("lfpdppp")
        assert result["status"] == "completed"
        assert result["law_id"] == "lfpdppp"
        assert result["dry_run"] is False
        mock_call_command.assert_called_once()
        args, kwargs = mock_call_command.call_args
        assert args[0] == "index_laws"
        assert kwargs["law_id"] == "lfpdppp"
        assert kwargs["dry_run"] is False
        # Must NOT drop the corpus: never a full-reindex / all-laws run.
        assert "reindex" not in kwargs and "all" not in kwargs

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_dry_run_passes_through_and_writes_nothing(
        self, mock_call_command, mock_log_cls
    ):
        from apps.scraper.scheduling import tasks

        result = tasks.reindex_law("reg_reg_lfpdppp", dry_run=True)
        assert result["status"] == "completed"
        assert result["dry_run"] is True
        assert mock_call_command.call_args.kwargs["dry_run"] is True

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_command_failure_surfaces_as_error(self, mock_call_command, mock_log_cls):
        from apps.scraper.scheduling import tasks

        mock_call_command.side_effect = RuntimeError("index boom")
        result = tasks.reindex_law("lfpdppp")
        assert result["status"] == "error"
        assert "index boom" in result["error"]
        assert result["law_id"] == "lfpdppp"


# ── ingest_law ────────────────────────────────────────────────────────


class _FakeResult:
    """Minimal stand-in for IngestionResult (success/error/grade)."""

    def __init__(self, success=True, error="", grade="A"):
        self.success = success
        self.error = error
        self.grade = grade


class TestIngestLaw:
    def test_missing_law_id_is_rejected(self):
        from apps.scraper.scheduling import tasks

        assert tasks.ingest_law("")["status"] == "error"
        assert tasks.ingest_law("   ")["status"] == "error"

    @patch("apps.scraper.utils.law_registry.LawRegistry")
    def test_law_not_in_registry_is_a_clean_error(self, mock_registry_cls):
        from apps.scraper.scheduling import tasks

        mock_registry_cls.return_value.get_by_id.return_value = None
        result = tasks.ingest_law("does_not_exist")
        assert result["status"] == "error"
        assert "not in data/law_registry.json" in result["error"]

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.scraper.scheduling.tasks.reindex_law")
    @patch("apps.parsers.pipeline.IngestionPipeline")
    @patch("apps.scraper.utils.law_registry.LawRegistry")
    def test_happy_path_ingests_then_indexes(
        self, mock_registry_cls, mock_pipeline_cls, mock_reindex, mock_log_cls
    ):
        from apps.scraper.scheduling import tasks

        mock_registry_cls.return_value.get_by_id.return_value = {
            "id": "reg_reg_lfpdppp"
        }
        mock_pipeline_cls.return_value.ingest_law.return_value = _FakeResult(
            success=True, grade="B"
        )
        mock_reindex.return_value = {"status": "completed"}

        result = tasks.ingest_law("reg_reg_lfpdppp")
        assert result["status"] == "completed"
        assert result["grade"] == "B"
        assert result["quarantined"] is False
        assert result["indexed"] is True
        mock_pipeline_cls.return_value.ingest_law.assert_called_once()
        mock_reindex.assert_called_once_with("reg_reg_lfpdppp")

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.scraper.scheduling.tasks.reindex_law")
    @patch("apps.parsers.pipeline.IngestionPipeline")
    @patch("apps.scraper.utils.law_registry.LawRegistry")
    def test_quarantined_parse_is_saved_not_indexed(
        self, mock_registry_cls, mock_pipeline_cls, mock_reindex, mock_log_cls
    ):
        from apps.scraper.scheduling import tasks

        mock_registry_cls.return_value.get_by_id.return_value = {"id": "somelaw"}
        # Quarantine: success=False with a "Quarantined:" error, DB version saved.
        mock_pipeline_cls.return_value.ingest_law.return_value = _FakeResult(
            success=False, error="Quarantined: Grade D (55.0%)", grade="D"
        )

        result = tasks.ingest_law("somelaw")
        # Reported as a completed (quality) outcome, NOT an error, and NOT indexed.
        assert result["status"] == "completed"
        assert result["quarantined"] is True
        assert result["indexed"] is False
        assert "note" in result
        mock_reindex.assert_not_called()

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.scraper.scheduling.tasks.reindex_law")
    @patch("apps.parsers.pipeline.IngestionPipeline")
    @patch("apps.scraper.utils.law_registry.LawRegistry")
    def test_index_false_persists_only(
        self, mock_registry_cls, mock_pipeline_cls, mock_reindex, mock_log_cls
    ):
        from apps.scraper.scheduling import tasks

        mock_registry_cls.return_value.get_by_id.return_value = {"id": "somelaw"}
        mock_pipeline_cls.return_value.ingest_law.return_value = _FakeResult(
            success=True, grade="A"
        )

        result = tasks.ingest_law("somelaw", index=False)
        assert result["status"] == "completed"
        assert result["indexed"] is False
        mock_reindex.assert_not_called()

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.parsers.pipeline.IngestionPipeline")
    @patch("apps.scraper.utils.law_registry.LawRegistry")
    def test_ingest_failure_surfaces_as_error(
        self, mock_registry_cls, mock_pipeline_cls, mock_log_cls
    ):
        from apps.scraper.scheduling import tasks

        mock_registry_cls.return_value.get_by_id.return_value = {"id": "somelaw"}
        mock_pipeline_cls.return_value.ingest_law.return_value = _FakeResult(
            success=False, error="download failed", grade=None
        )

        result = tasks.ingest_law("somelaw")
        assert result["status"] == "error"
        assert result["stage"] == "ingest"
        assert "download failed" in result["error"]
