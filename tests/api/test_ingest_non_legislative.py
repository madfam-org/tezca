"""Tests for the ingest_non_legislative_laws management command."""

import uuid
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.api.models import Law, LawVersion

MODULE = "apps.api.management.commands.ingest_non_legislative_laws"


def _make_metadata(laws):
    return {"laws": laws}


def _law_entry(
    official_id=None,
    law_name="Ley de prueba",
    state="Colima",
    category="Otros",
    tier="state",
    url="https://example.com/law.pdf",
    text_file="state/colima/law.txt",
    publication_date="2024-01-01",
):
    return {
        "official_id": official_id or f"nonleg_{uuid.uuid4().hex[:8]}",
        "law_name": law_name,
        "state": state,
        "category": category,
        "tier": tier,
        "url": url,
        "text_file": text_file,
        "publication_date": publication_date,
    }


@pytest.mark.django_db
class TestIngestNonLegislativeLaws:
    """Tests for ingest_non_legislative_laws management command."""

    @patch(f"{MODULE}.data_exists", return_value=False)
    @patch(f"{MODULE}.read_data_content", return_value="Some law text content")
    @patch(f"{MODULE}.read_metadata_json")
    def test_dry_run_no_writes(self, mock_meta, mock_content, mock_exists, capsys):
        """--dry-run should count items without creating records."""
        laws = [_law_entry() for _ in range(3)]
        mock_meta.return_value = _make_metadata(laws)

        before_laws = Law.objects.count()
        before_versions = LawVersion.objects.count()

        call_command("ingest_non_legislative_laws", "--all", "--dry-run")
        captured = capsys.readouterr()

        assert Law.objects.count() == before_laws
        assert LawVersion.objects.count() == before_versions
        assert "INGESTION SUMMARY" in captured.out

    @patch(f"{MODULE}.data_exists", return_value=True)
    @patch(f"{MODULE}.read_data_content", return_value="Contenido de ley de prueba")
    @patch(f"{MODULE}.read_metadata_json")
    def test_ingests_all_states(self, mock_meta, mock_content, mock_exists):
        """--all creates Law + LawVersion for each metadata entry."""
        laws = [_law_entry(state=s) for s in ["Colima", "Sonora", "Jalisco"]]
        mock_meta.return_value = _make_metadata(laws)

        call_command("ingest_non_legislative_laws", "--all")

        for entry in laws:
            law = Law.objects.get(official_id=entry["official_id"])
            assert law.name == entry["law_name"]
            assert law.law_type == "non_legislative"
            assert law.tier == "state"
            assert law.versions.count() == 1

    @patch(f"{MODULE}.data_exists", return_value=True)
    @patch(f"{MODULE}.read_data_content", return_value="Contenido")
    @patch(f"{MODULE}.read_metadata_json")
    def test_ingests_single_state(self, mock_meta, mock_content, mock_exists):
        """--state colima filters correctly to only that state."""
        colima = _law_entry(state="Colima", official_id="colima_1")
        sonora = _law_entry(state="Sonora", official_id="sonora_1")
        mock_meta.return_value = _make_metadata([colima, sonora])

        call_command("ingest_non_legislative_laws", "--state", "colima")

        assert Law.objects.filter(official_id="colima_1").exists()
        assert not Law.objects.filter(official_id="sonora_1").exists()

    @patch(f"{MODULE}.data_exists", return_value=True)
    @patch(f"{MODULE}.read_data_content", return_value="Contenido")
    @patch(f"{MODULE}.read_metadata_json")
    def test_skips_existing_laws(self, mock_meta, mock_content, mock_exists):
        """Re-ingestion updates existing laws instead of duplicating."""
        entry = _law_entry(official_id="existing_law_1")
        mock_meta.return_value = _make_metadata([entry])

        # First ingestion
        call_command("ingest_non_legislative_laws", "--all")
        assert Law.objects.filter(official_id="existing_law_1").count() == 1

        # Second ingestion — should update, not duplicate
        call_command("ingest_non_legislative_laws", "--all")
        assert Law.objects.filter(official_id="existing_law_1").count() == 1

    @patch(f"{MODULE}.read_metadata_json")
    def test_handles_missing_metadata(self, mock_meta, capsys):
        """Graceful error when metadata JSON not found."""
        mock_meta.return_value = None

        call_command("ingest_non_legislative_laws", "--all")
        captured = capsys.readouterr()

        assert "Metadata file not found" in captured.out

    @patch(f"{MODULE}.data_exists", return_value=True)
    @patch(f"{MODULE}.read_data_content", return_value="Contenido")
    @patch(f"{MODULE}.read_metadata_json")
    def test_limit_flag(self, mock_meta, mock_content, mock_exists):
        """--limit 2 stops after 2 laws."""
        laws = [_law_entry() for _ in range(5)]
        mock_meta.return_value = _make_metadata(laws)

        call_command("ingest_non_legislative_laws", "--all", "--limit", "2")

        assert Law.objects.count() == 2

    @patch(f"{MODULE}.data_exists", return_value=True)
    @patch(f"{MODULE}.read_data_content", return_value="Contenido")
    @patch(f"{MODULE}.read_metadata_json")
    def test_batch_size_respected(self, mock_meta, mock_content, mock_exists, capsys):
        """Batch size controls transaction grouping."""
        laws = [_law_entry() for _ in range(5)]
        mock_meta.return_value = _make_metadata(laws)

        call_command("ingest_non_legislative_laws", "--all", "--batch-size", "2")
        captured = capsys.readouterr()

        # 5 laws with batch_size=2 → 3 batches
        assert "Batch 3:" in captured.out
        assert Law.objects.count() == 5

    @patch(f"{MODULE}.data_exists", return_value=True)
    @patch(f"{MODULE}.read_data_content", return_value="Contenido de ley")
    @patch(f"{MODULE}.read_metadata_json")
    def test_creates_correct_tier_and_type(self, mock_meta, mock_content, mock_exists):
        """Verifies tier='state' and law_type='non_legislative'."""
        entry = _law_entry(
            official_id="tier_check",
            tier="state",
            category="Reglamento",
            state="Jalisco",
        )
        mock_meta.return_value = _make_metadata([entry])

        call_command("ingest_non_legislative_laws", "--all")

        law = Law.objects.get(official_id="tier_check")
        assert law.tier == "state"
        assert law.law_type == "non_legislative"
        assert law.category == "Reglamento"
        assert law.state == "Jalisco"
