"""Tests for the ingest_noms management command (apps/api/management/commands/ingest_noms.py).

Distinct from tests/api/test_ingest_noms.py, which covers the standalone
scripts/ingestion/ingest_noms.py PDF-download helper.
"""

import json

import pytest
from django.core.management import call_command

from apps.api.management.commands.ingest_noms import NOM_CATEGORY, build_official_id
from apps.api.models import Law, LawVersion


def _nom_entry(
    nom_id="nom_001_ssa1_2010",
    nom_number="NOM-001-SSA1-2010",
    name="Salud ambiental. Agua para uso y consumo humano",
    secretaria="Secretaría de Salud",
    url="https://dof.gob.mx/nota_detalle.php?codigo=1",
    date_published="2010-06-15",
    status="vigente",
):
    return {
        "id": nom_id,
        "nom_number": nom_number,
        "name": name,
        "secretaria": secretaria,
        "url": url,
        "date_published": date_published,
        "status": status,
    }


@pytest.mark.django_db
class TestIngestNomsCommand:
    """Tests for ingest_noms management command via call_command."""

    def test_dry_run_no_writes(self, tmp_path, capsys):
        """--dry-run counts NOMs without DB writes."""
        catalog = tmp_path / "discovered_noms.json"
        noms = [
            _nom_entry(nom_id=f"dry_{i}", nom_number=f"NOM-{i:03d}-SSA1-2020")
            for i in range(3)
        ]
        catalog.write_text(json.dumps(noms), encoding="utf-8")

        before_laws = Law.objects.count()
        before_versions = LawVersion.objects.count()

        call_command("ingest_noms", "--dry-run", "--catalog", str(catalog))
        captured = capsys.readouterr()

        assert Law.objects.count() == before_laws
        assert LawVersion.objects.count() == before_versions
        assert "DRY-RUN" in captured.out
        assert "NOM ingest complete" in captured.out

    def test_ingests_noms(self, tmp_path):
        """Creates Law + LawVersion from NOM catalog entries."""
        catalog = tmp_path / "discovered_noms.json"
        noms = [_nom_entry(nom_number="NOM-001-SSA1-2010")]
        catalog.write_text(json.dumps(noms), encoding="utf-8")

        call_command("ingest_noms", "--catalog", str(catalog))

        law = Law.objects.get(official_id="nom_NOM-001-SSA1-2010")
        assert law.name == "Salud ambiental. Agua para uso y consumo humano"
        assert law.tier == "federal"
        assert law.law_type == "non_legislative"
        assert law.category == NOM_CATEGORY
        assert law.status == Law.Status.VIGENTE
        assert law.versions.count() == 1
        assert str(law.versions.first().publication_date) == "2010-06-15"

    def test_skips_existing(self, tmp_path):
        """Re-run doesn't duplicate NOMs."""
        catalog = tmp_path / "discovered_noms.json"
        noms = [_nom_entry(nom_number="NOM-002-SSA1-2011")]
        catalog.write_text(json.dumps(noms), encoding="utf-8")

        call_command("ingest_noms", "--catalog", str(catalog))
        call_command("ingest_noms", "--catalog", str(catalog))

        assert Law.objects.filter(official_id="nom_NOM-002-SSA1-2011").count() == 1
        assert (
            LawVersion.objects.filter(law__official_id="nom_NOM-002-SSA1-2011").count()
            == 1
        )

    def test_dir_flag_resolves_catalog_path(self, tmp_path):
        """--dir points at a directory containing discovered_noms.json."""
        catalog = tmp_path / "discovered_noms.json"
        noms = [_nom_entry(nom_number="NOM-003-STPS-2012")]
        catalog.write_text(json.dumps(noms), encoding="utf-8")

        call_command("ingest_noms", "--dir", str(tmp_path))

        assert Law.objects.filter(official_id="nom_NOM-003-STPS-2012").exists()

    def test_missing_file_error(self, tmp_path, capsys):
        """Graceful error when catalog JSON not found."""
        missing = tmp_path / "nonexistent.json"

        call_command("ingest_noms", "--catalog", str(missing))
        captured = capsys.readouterr()

        assert "Catalog not found" in captured.err

    def test_empty_catalog_no_op(self, tmp_path, capsys):
        """Empty catalog list is a clean no-op."""
        catalog = tmp_path / "discovered_noms.json"
        catalog.write_text("[]", encoding="utf-8")

        call_command("ingest_noms", "--catalog", str(catalog))
        captured = capsys.readouterr()

        assert "nothing to ingest" in captured.out

    def test_status_mapping(self, tmp_path):
        """abrogada/derogada/unknown statuses map to the right Law.Status."""
        catalog = tmp_path / "discovered_noms.json"
        noms = [
            _nom_entry(nom_number="NOM-004-SSA1-2013", status="abrogada"),
            _nom_entry(nom_number="NOM-005-SSA1-2014", status="derogada"),
            _nom_entry(nom_number="NOM-006-SSA1-2015", status="something-else"),
        ]
        catalog.write_text(json.dumps(noms), encoding="utf-8")

        call_command("ingest_noms", "--catalog", str(catalog))

        assert (
            Law.objects.get(official_id="nom_NOM-004-SSA1-2013").status
            == Law.Status.ABROGADA
        )
        assert (
            Law.objects.get(official_id="nom_NOM-005-SSA1-2014").status
            == Law.Status.DEROGADA
        )
        assert (
            Law.objects.get(official_id="nom_NOM-006-SSA1-2015").status
            == Law.Status.UNKNOWN
        )

    def test_date_fallback_when_missing(self, tmp_path):
        """Missing date_published falls back to the 2020-01-01 default."""
        catalog = tmp_path / "discovered_noms.json"
        noms = [_nom_entry(nom_number="NOM-007-SSA1-2016", date_published="")]
        catalog.write_text(json.dumps(noms), encoding="utf-8")

        call_command("ingest_noms", "--catalog", str(catalog))

        law = Law.objects.get(official_id="nom_NOM-007-SSA1-2016")
        assert str(law.versions.first().publication_date) == "2020-01-01"


# ---------------------------------------------------------------------------
# build_official_id helper
# ---------------------------------------------------------------------------
class TestBuildOfficialId:
    def test_uses_nom_number_when_present(self):
        assert (
            build_official_id({"id": "x", "nom_number": "NOM-001-SSA1-2010"})
            == "nom_NOM-001-SSA1-2010"
        )

    def test_falls_back_to_id(self):
        assert build_official_id({"id": "abc123"}) == "nom_abc123"

    def test_falls_back_to_unknown(self):
        assert build_official_id({}) == "nom_unknown"
