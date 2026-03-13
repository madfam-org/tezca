"""Smoke tests for management commands: run_pipeline, dedup_laws, ingest_conamer, ingest_judicial.

Note: dedup_laws already has comprehensive tests in test_dedup_laws.py.
The tests here cover the management command entry points, argument handling,
and error paths not exercised by the dedicated test modules.
"""

import json
import uuid
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from apps.api.models import JudicialRecord, Law, LawVersion


# ---------------------------------------------------------------------------
# run_pipeline command
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestRunPipelineCommand:
    """Smoke tests for the run_pipeline management command."""

    @patch("apps.api.management.commands.run_pipeline.PIPELINE_STATUS_FILE")
    @patch("apps.api.management.commands.run_pipeline._ensure_paths")
    @patch("apps.api.tasks.run_full_pipeline")
    @patch("apps.api.tasks._build_pipeline_phases")
    def test_shows_plan_local_mode(
        self, mock_phases, mock_run, mock_ensure, mock_status_file
    ):
        """--local prints the pipeline plan before execution."""
        mock_status_file.exists.return_value = False
        mock_phases.return_value = [
            {"name": "Scrape federal catalog", "cmd": ["echo", "hi"]},
            {"name": "Ingest federal laws", "cmd": ["echo", "hi"]},
        ]
        mock_run.return_value = {
            "status": "completed",
            "summary": {"succeeded": 2, "total_phases": 2},
            "duration_human": "1m",
            "phase_results": [],
        }

        out = StringIO()
        call_command("run_pipeline", "--local", stdout=out)

        output = out.getvalue()
        assert "DATA COLLECTION PIPELINE" in output
        assert "Phase 1:" in output
        assert "Phase 2:" in output
        assert "local (synchronous)" in output
        mock_ensure.assert_called_once()

    @patch("apps.api.management.commands.run_pipeline.PIPELINE_STATUS_FILE")
    @patch("apps.api.management.commands.run_pipeline._ensure_paths")
    def test_aborts_if_already_running(self, mock_ensure, mock_status_file):
        """Command should refuse to start when pipeline is already running."""
        mock_status_file.exists.return_value = True
        mock_status_file.__str__ = lambda s: "/tmp/fake_status.json"
        mock_status_file.open = MagicMock()

        # Simulate reading a running status from the file
        running_status = json.dumps(
            {"status": "running", "phase": "Scrape state laws", "progress": 45}
        )

        with patch(
            "builtins.open",
            create=True,
            return_value=StringIO(running_status),
        ):
            out = StringIO()
            err = StringIO()
            call_command("run_pipeline", "--local", stdout=out, stderr=err)

        error_output = err.getvalue()
        assert "already running" in error_output

    @patch("apps.api.management.commands.run_pipeline.PIPELINE_STATUS_FILE")
    @patch("apps.api.management.commands.run_pipeline._ensure_paths")
    @patch("apps.api.tasks.run_full_pipeline")
    @patch("apps.api.tasks._build_pipeline_phases")
    def test_reports_failed_phases(
        self, mock_phases, mock_run, mock_ensure, mock_status_file
    ):
        """Failed phases should be reported on stderr."""
        mock_status_file.exists.return_value = False
        mock_phases.return_value = [
            {"name": "Ingest federal laws", "cmd": ["echo"]},
        ]
        mock_run.return_value = {
            "status": "completed_with_errors",
            "summary": {"succeeded": 0, "total_phases": 1},
            "duration_human": "30s",
            "phase_results": [
                {
                    "phase": "Ingest federal laws",
                    "status": "failed",
                    "error": "Connection refused",
                    "returncode": 1,
                }
            ],
        }

        out = StringIO()
        err = StringIO()
        call_command("run_pipeline", "--local", stdout=out, stderr=err)

        assert "FAILED" in err.getvalue()
        assert "Connection refused" in err.getvalue()


# ---------------------------------------------------------------------------
# dedup_laws command -- supplementary edge-case tests
# (Comprehensive tests live in test_dedup_laws.py)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestDedupLawsCommandEdgeCases:
    """Additional edge-case tests for dedup_laws command."""

    def test_dry_run_federal_tiers_shows_sample(self, capsys):
        """--fix-federal-tiers --dry-run should show sample IDs."""
        Law.objects.create(
            official_id=f"dup_{uuid.uuid4().hex[:6]}",
            name="Dup fiscal law",
            tier="fiscal",
        )
        call_command("dedup_laws", "--fix-federal-tiers", "--dry-run")
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out
        assert "Would delete" in captured.out

    def test_no_state_dupes_is_noop(self, capsys):
        """When no state duplicates exist, step reports nothing to clean."""
        Law.objects.create(
            official_id=f"good_{uuid.uuid4().hex[:6]}",
            name="Good state law",
            tier="state",
            state="Sonora",
        )
        call_command("dedup_laws", "--fix-state-dupes")
        captured = capsys.readouterr()
        assert "Nothing to clean up" in captured.out


# ---------------------------------------------------------------------------
# ingest_conamer command
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestIngestConamerCommand:
    """Smoke tests for the ingest_conamer management command."""

    def test_no_catalog_file_shows_error(self, tmp_path, capsys):
        """Command reports error when catalog file does not exist."""
        missing_path = tmp_path / "nonexistent" / "catalog.json"
        call_command("ingest_conamer", "--all", "--catalog", str(missing_path))
        captured = capsys.readouterr()
        assert "No regulations found" in captured.out

    def test_dry_run_no_db_writes(self, tmp_path, capsys):
        """--dry-run should not create any Law or LawVersion records."""
        catalog = tmp_path / "catalog.json"
        regulations = [
            {
                "id": "reg001",
                "name": "Reglamento de Prueba",
                "regulation_type": "reglamento",
                "url": "https://example.com/reg001",
                "date": "2024-06-15",
            },
            {
                "id": "reg002",
                "name": "Acuerdo de Prueba",
                "regulation_type": "acuerdo",
                "url": "https://example.com/reg002",
                "date": "2024-07-01",
            },
        ]
        catalog.write_text(json.dumps(regulations), encoding="utf-8")

        before_laws = Law.objects.count()
        before_versions = LawVersion.objects.count()

        call_command("ingest_conamer", "--all", "--dry-run", "--catalog", str(catalog))
        captured = capsys.readouterr()

        assert Law.objects.count() == before_laws
        assert LawVersion.objects.count() == before_versions
        assert "CONAMER INGESTION SUMMARY" in captured.out

    def test_creates_law_and_version(self, tmp_path, capsys):
        """Ingesting one regulation should create a Law and LawVersion."""
        catalog = tmp_path / "catalog.json"
        regulations = [
            {
                "id": "test_reg_123",
                "name": "Reglamento de Control Sanitario",
                "regulation_type": "reglamento",
                "url": "https://example.com/test_reg",
                "date": "2024-01-15",
            },
        ]
        catalog.write_text(json.dumps(regulations), encoding="utf-8")

        call_command("ingest_conamer", "--all", "--catalog", str(catalog))

        law = Law.objects.get(official_id="conamer_test_reg_123")
        assert law.name == "Reglamento de Control Sanitario"
        assert law.tier == "federal"
        assert law.law_type == "non_legislative"
        assert law.category == "reglamento"
        assert law.source_url == "https://example.com/test_reg"

        version = law.versions.first()
        assert version is not None
        assert str(version.publication_date) == "2024-01-15"

    def test_limit_option(self, tmp_path, capsys):
        """--limit should cap the number of regulations processed."""
        catalog = tmp_path / "catalog.json"
        regulations = [
            {"id": f"lim_{i}", "name": f"Regulation {i}", "regulation_type": "acuerdo"}
            for i in range(10)
        ]
        catalog.write_text(json.dumps(regulations), encoding="utf-8")

        call_command(
            "ingest_conamer", "--all", "--limit", "3", "--catalog", str(catalog)
        )
        captured = capsys.readouterr()

        # Only 3 should be processed
        assert "Regulations to ingest: 3" in captured.out

    def test_empty_name_skipped(self, tmp_path, capsys):
        """Regulations with no name should be reported as failures."""
        catalog = tmp_path / "catalog.json"
        regulations = [{"id": "no_name", "name": "", "regulation_type": "reglamento"}]
        catalog.write_text(json.dumps(regulations), encoding="utf-8")

        call_command("ingest_conamer", "--all", "--catalog", str(catalog))
        captured = capsys.readouterr()

        assert "Failed:" in captured.out


# ---------------------------------------------------------------------------
# ingest_judicial command
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestIngestJudicialCommand:
    """Smoke tests for the ingest_judicial management command."""

    def test_file_not_found(self, tmp_path, capsys):
        """Command reports error when JSON file does not exist."""
        missing = tmp_path / "nonexistent.json"
        call_command("ingest_judicial", "--file", str(missing))
        captured = capsys.readouterr()
        assert "No records found" in captured.out

    def test_dry_run_no_db_writes(self, tmp_path, capsys):
        """--dry-run should not create any JudicialRecord entries."""
        records_file = tmp_path / "judicial.json"
        records = [
            {
                "registro": "2025001",
                "epoca": "11a",
                "instancia": "Primera Sala",
                "materia": "civil",
                "tipo": "jurisprudencia",
                "rubro": "Derecho a la vivienda",
                "texto": "Texto de prueba",
            },
        ]
        records_file.write_text(json.dumps(records), encoding="utf-8")

        before_count = JudicialRecord.objects.count()

        call_command("ingest_judicial", "--file", str(records_file), "--dry-run")

        assert JudicialRecord.objects.count() == before_count

    def test_creates_judicial_record(self, tmp_path, capsys):
        """Ingesting a record should create a JudicialRecord."""
        records_file = tmp_path / "judicial.json"
        records = [
            {
                "registro": "TEST-2025-001",
                "epoca": "11a",
                "instancia": "Segunda Sala",
                "materia": "administrativa",
                "tipo": "tesis aislada",
                "rubro": "Principio de legalidad",
                "texto": "El principio de legalidad exige...",
                "ponente": "Min. Garcia",
                "fuente": "Semanario Judicial",
                "precedentes": "",
                "votos": "",
                "fecha_publicacion": "2025-03-01",
            },
        ]
        records_file.write_text(json.dumps(records), encoding="utf-8")

        call_command("ingest_judicial", "--file", str(records_file))

        record = JudicialRecord.objects.get(registro="TEST-2025-001")
        assert record.epoca == "11a"
        assert record.instancia == "Segunda Sala"
        assert record.materia == "administrativa"
        assert record.tipo == "tesis_aislada"
        assert record.rubro == "Principio de legalidad"
        assert record.ponente == "Min. Garcia"

    def test_skips_records_without_registro(self, tmp_path, capsys):
        """Records missing registro should be skipped."""
        records_file = tmp_path / "judicial.json"
        records = [
            {"registro": "", "tipo": "jurisprudencia", "rubro": "No registro"},
            {
                "registro": "VALID-001",
                "tipo": "jurisprudencia",
                "materia": "penal",
                "rubro": "Valid record",
                "texto": "...",
                "epoca": "10a",
                "instancia": "Pleno",
            },
        ]
        records_file.write_text(json.dumps(records), encoding="utf-8")

        call_command("ingest_judicial", "--file", str(records_file))
        captured = capsys.readouterr()

        assert "Skipped:" in captured.out
        assert JudicialRecord.objects.filter(registro="VALID-001").exists()
        assert JudicialRecord.objects.count() == 1

    def test_tipo_filter(self, tmp_path, capsys):
        """--tipo should filter records by type."""
        records_file = tmp_path / "judicial.json"
        records = [
            {
                "registro": "FILT-001",
                "tipo": "jurisprudencia",
                "materia": "civil",
                "rubro": "Jurisprudencia record",
                "texto": "...",
                "epoca": "11a",
                "instancia": "Pleno",
            },
            {
                "registro": "FILT-002",
                "tipo": "tesis aislada",
                "materia": "penal",
                "rubro": "Tesis record",
                "texto": "...",
                "epoca": "11a",
                "instancia": "Primera Sala",
            },
        ]
        records_file.write_text(json.dumps(records), encoding="utf-8")

        call_command(
            "ingest_judicial",
            "--file",
            str(records_file),
            "--tipo",
            "jurisprudencia",
        )

        assert JudicialRecord.objects.filter(registro="FILT-001").exists()
        assert not JudicialRecord.objects.filter(registro="FILT-002").exists()

    def test_dir_mode_merges_batches(self, tmp_path, capsys):
        """--dir should merge multiple JSON batch files."""
        batch_dir = tmp_path / "batches"
        batch_dir.mkdir()

        batch1 = [
            {
                "registro": "DIR-001",
                "tipo": "jurisprudencia",
                "materia": "civil",
                "rubro": "Batch 1 record",
                "texto": "...",
                "epoca": "11a",
                "instancia": "Pleno",
            },
        ]
        batch2 = [
            {
                "registro": "DIR-002",
                "tipo": "tesis aislada",
                "materia": "laboral",
                "rubro": "Batch 2 record",
                "texto": "...",
                "epoca": "10a",
                "instancia": "Segunda Sala",
            },
        ]

        (batch_dir / "batch_001.json").write_text(json.dumps(batch1), encoding="utf-8")
        (batch_dir / "batch_002.json").write_text(json.dumps(batch2), encoding="utf-8")

        call_command("ingest_judicial", "--dir", str(batch_dir))

        assert JudicialRecord.objects.filter(registro="DIR-001").exists()
        assert JudicialRecord.objects.filter(registro="DIR-002").exists()
        assert JudicialRecord.objects.count() == 2
