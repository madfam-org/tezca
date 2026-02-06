"""
Integration tests for the full data pipeline.

Tests the flow: text → parse → AKN XML → DB ingest → ES index
using sample data and mocked ES.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase

from apps.api.models import Law, LawVersion
from apps.api.utils.paths import BASE_DIR, resolve_data_path, resolve_data_path_or_none


class TestPathResolution(TestCase):
    """Test unified path resolution works in local dev."""

    def test_base_dir_is_project_root(self):
        """BASE_DIR should point to the project root."""
        assert BASE_DIR.exists()
        assert (BASE_DIR / "manage.py").exists() or (BASE_DIR / "apps").is_dir()

    def test_resolve_existing_file(self):
        """resolve_data_path should find files that exist."""
        # manage.py exists at project root
        path = resolve_data_path("manage.py")
        assert path.exists()

    def test_resolve_nonexistent_returns_basedir_relative(self):
        """resolve_data_path returns BASE_DIR-relative for missing files."""
        path = resolve_data_path("data/nonexistent_file_xyz.json")
        assert str(path).startswith(str(BASE_DIR))

    def test_resolve_or_none_missing_file(self):
        """resolve_data_path_or_none returns None for missing files."""
        result = resolve_data_path_or_none("totally_fake_file_abc123.txt")
        assert result is None

    def test_resolve_or_none_empty_string(self):
        """resolve_data_path_or_none handles empty input."""
        assert resolve_data_path_or_none("") is None
        assert resolve_data_path_or_none(None) is None

    def test_resolve_strips_app_prefix(self):
        """Path resolver should strip /app/ prefix from Docker paths."""
        path = resolve_data_path("/app/manage.py")
        assert "app/app" not in str(path)


class TestStateLawParser(TestCase):
    """Test state law parser with sample text."""

    def test_parser_importable(self):
        """StateLawParser should import without errors."""
        from apps.parsers.state_parser import StateLawParser

        parser = StateLawParser(base_dir=BASE_DIR)
        assert parser is not None

    def test_parse_sample_law(self):
        """Parser should generate AKN XML from sample text."""
        from apps.parsers.state_parser import StateLawParser

        parser = StateLawParser(base_dir=BASE_DIR)

        # Create a temporary text file with sample law content
        with tempfile.TemporaryDirectory() as tmpdir:
            text_file = Path(tmpdir) / "sample_law.txt"
            text_file.write_text(
                "LEY DE PROTECCIÓN AL MEDIO AMBIENTE DEL ESTADO DE COLIMA\n\n"
                "TÍTULO PRIMERO\n"
                "DISPOSICIONES GENERALES\n\n"
                "CAPÍTULO ÚNICO\n\n"
                "Artículo 1.- La presente Ley es de orden público e interés social "
                "y tiene por objeto establecer las bases para la protección del "
                "medio ambiente en el Estado de Colima.\n\n"
                "Artículo 2.- Para los efectos de esta Ley se entiende por:\n"
                "I.- Ambiente: El conjunto de elementos naturales.\n"
                "II.- Contaminación: La presencia de sustancias.\n\n"
                "Artículo 3.- Son instrumentos de la política ambiental:\n"
                "I.- La planeación ambiental.\n"
                "II.- La evaluación del impacto ambiental.\n\n"
                "TRANSITORIOS\n\n"
                "Primero.- La presente Ley entrará en vigor al día siguiente.\n",
                encoding="utf-8",
            )

            metadata = {
                "official_id": "test-colima-ley-ambiental",
                "law_name": "Ley de Protección al Medio Ambiente del Estado de Colima",
                "state": "Colima",
                "tier": "state",
                "publication_date": "2023-01-01",
                "text_file": str(text_file),
            }

            # Patch at the source module so the dynamic import finds it
            with patch(
                "apps.api.utils.paths.resolve_data_path_or_none",
                return_value=text_file,
            ):
                # Override output path to use temp dir
                parser._determine_akn_output_path = (
                    lambda m: Path(tmpdir) / "output.xml"
                )
                result = parser.parse_law(metadata)

            assert result.success, f"Parser failed: {result.error}"
            assert result.akn_path is not None
            assert result.akn_path.exists()
            assert result.article_count >= 2  # At least 2 articles detected

            # Verify the output is valid XML
            xml_content = result.akn_path.read_text(encoding="utf-8")
            assert "<?xml" in xml_content
            assert "akomaNtoso" in xml_content

    def test_parse_missing_text_file(self):
        """Parser should handle missing text file gracefully."""
        from apps.parsers.state_parser import StateLawParser

        parser = StateLawParser(base_dir=BASE_DIR)

        metadata = {
            "official_id": "test-missing",
            "law_name": "Test Law",
            "state": "Test",
            "tier": "state",
            "text_file": "",
        }

        result = parser.parse_law(metadata)
        assert not result.success
        assert result.error is not None


class TestIngestStateCommand(TestCase):
    """Test the ingest_state_laws management command."""

    def test_command_handles_missing_metadata(self):
        """Command should fail gracefully when metadata file is missing."""
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        err = StringIO()

        # This will try to find the metadata file - it may or may not exist
        # The key test is that it doesn't crash
        try:
            call_command(
                "ingest_state_laws",
                "--all",
                "--dry-run",
                "--limit",
                "1",
                stdout=out,
                stderr=err,
            )
        except SystemExit:
            pass  # argparse exit is fine

        # Command should produce output without crashing
        output = out.getvalue()
        assert output is not None


class TestIndexLawsCommand(TestCase):
    """Test the unified index_laws management command."""

    def test_command_has_new_arguments(self):
        """Verify new CLI arguments are registered."""
        import argparse

        from apps.api.management.commands.index_laws import Command

        cmd = Command()
        parser = argparse.ArgumentParser()
        cmd.add_arguments(parser)

        # Test that --create-indices and --tier are recognized
        args = parser.parse_args(
            ["--all", "--dry-run", "--tier", "state", "--create-indices"]
        )
        assert args.tier == "state"
        assert args.create_indices is True

    def _make_command(self):
        """Create a properly initialized Command instance."""
        from django.core.management.color import no_style

        from apps.api.management.commands.index_laws import Command

        cmd = Command()
        cmd.style = no_style()
        cmd.stdout = MagicMock()
        cmd.stderr = MagicMock()
        return cmd

    def test_index_law_with_no_version(self):
        """index_law should return 0 for law without versions."""
        cmd = self._make_command()

        law = Law.objects.create(
            official_id="test-no-version",
            name="Test Law No Version",
            tier="state",
        )

        result = cmd.index_law(law, es=None, dry_run=True)
        assert result == 0

    def test_index_law_dry_run_with_version(self):
        """Dry run should count articles without ES writes."""
        cmd = self._make_command()

        law = Law.objects.create(
            official_id="test-dry-run",
            name="Test Law",
            tier="federal",
        )
        LawVersion.objects.create(
            law=law,
            publication_date="2023-01-01",
            xml_file_path="data/federal/mx-fed-test-v2.xml",
        )

        # No actual file exists, so should return 0
        result = cmd.index_law(law, es=None, dry_run=True)
        assert result == 0


class TestPipelinePhases(TestCase):
    """Test pipeline phase construction."""

    def test_default_phases_include_parse(self):
        """Pipeline should include parse phases by default."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases({})
        phase_names = [p["name"] for p in phases]

        assert "Parse state laws to AKN XML" in phase_names
        assert "Parse municipal laws to AKN XML" in phase_names

    def test_skip_parse_flag(self):
        """skip_parse should remove parse phases."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases({"skip_parse": True})
        phase_names = [p["name"] for p in phases]

        assert "Parse state laws to AKN XML" not in phase_names
        assert "Parse municipal laws to AKN XML" not in phase_names

    def test_index_phase_includes_create_indices(self):
        """Index phase should include --create-indices flag."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases({})
        index_phase = [p for p in phases if "Index" in p["name"]]

        assert len(index_phase) == 1
        assert "--create-indices" in index_phase[0]["cmd"]

    def test_phases_order(self):
        """Phases should follow: scrape → consolidate → parse → ingest → index."""
        from apps.api.tasks import _build_pipeline_phases

        phases = _build_pipeline_phases({})
        phase_names = [p["name"] for p in phases]

        # Find indices of key phases
        def find_idx(keyword):
            for i, name in enumerate(phase_names):
                if keyword.lower() in name.lower():
                    return i
            return -1

        consolidate_idx = find_idx("Consolidate state")
        parse_idx = find_idx("Parse state")
        ingest_state_idx = find_idx("Ingest state")
        index_idx = find_idx("Index to")

        # Verify ordering
        assert consolidate_idx < parse_idx, "Consolidate should come before Parse"
        assert parse_idx < ingest_state_idx, "Parse should come before Ingest"
        assert ingest_state_idx < index_idx, "Ingest should come before Index"
