"""Tests for the ingest_treaties management command."""

import json
import uuid

import pytest
from django.core.management import call_command

from apps.api.management.commands.ingest_treaties import _slugify
from apps.api.models import Law, LawVersion


def _treaty_entry(
    treaty_id="treaty_001",
    name="Tratado de Prueba",
    treaty_type="bilateral",
    url="https://example.com/treaty",
    date_signed="2023-06-15",
    date_ratified="2024-01-10",
):
    return {
        "id": treaty_id,
        "name": name,
        "treaty_type": treaty_type,
        "url": url,
        "date_signed": date_signed,
        "date_ratified": date_ratified,
    }


# ---------------------------------------------------------------------------
# Management command tests (call_command)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestIngestTreaties:
    """Tests for ingest_treaties management command via call_command."""

    def test_dry_run_no_writes(self, tmp_path, capsys):
        """--dry-run counts treaties without DB writes."""
        catalog = tmp_path / "treaties.json"
        treaties = [_treaty_entry(treaty_id=f"dry_{i}") for i in range(3)]
        catalog.write_text(json.dumps(treaties), encoding="utf-8")

        before_laws = Law.objects.count()
        before_versions = LawVersion.objects.count()

        call_command("ingest_treaties", "--all", "--dry-run", "--catalog", str(catalog))
        captured = capsys.readouterr()

        assert Law.objects.count() == before_laws
        assert LawVersion.objects.count() == before_versions
        assert "TREATY INGESTION SUMMARY" in captured.out

    def test_ingests_treaties(self, tmp_path):
        """Creates Law + LawVersion from treaty metadata."""
        catalog = tmp_path / "treaties.json"
        treaties = [
            _treaty_entry(treaty_id="ing_001", name="Convenio Internacional"),
        ]
        catalog.write_text(json.dumps(treaties), encoding="utf-8")

        call_command("ingest_treaties", "--all", "--catalog", str(catalog))

        law = Law.objects.get(official_id="treaty_ing_001")
        assert law.name == "Convenio Internacional"
        assert law.tier == "federal"
        assert law.law_type == "non_legislative"
        assert law.category == "bilateral"
        assert law.versions.count() == 1
        assert str(law.versions.first().publication_date) == "2024-01-10"

    def test_skips_existing(self, tmp_path):
        """Re-run doesn't duplicate treaties."""
        catalog = tmp_path / "treaties.json"
        treaties = [_treaty_entry(treaty_id="dup_001")]
        catalog.write_text(json.dumps(treaties), encoding="utf-8")

        call_command("ingest_treaties", "--all", "--catalog", str(catalog))
        call_command("ingest_treaties", "--all", "--catalog", str(catalog))

        assert Law.objects.filter(official_id="treaty_dup_001").count() == 1

    def test_limit_flag(self, tmp_path, capsys):
        """--limit 1 stops early."""
        catalog = tmp_path / "treaties.json"
        treaties = [_treaty_entry(treaty_id=f"lim_{i}") for i in range(5)]
        catalog.write_text(json.dumps(treaties), encoding="utf-8")

        call_command(
            "ingest_treaties", "--all", "--limit", "1", "--catalog", str(catalog)
        )
        captured = capsys.readouterr()

        assert "Treaties to ingest: 1" in captured.out
        assert Law.objects.filter(official_id__startswith="treaty_lim_").count() == 1

    def test_missing_file_error(self, tmp_path, capsys):
        """Graceful error when catalog JSON not found."""
        missing = tmp_path / "nonexistent.json"

        call_command("ingest_treaties", "--all", "--catalog", str(missing))
        captured = capsys.readouterr()

        assert "Catalog not found" in captured.out

    def test_empty_name_fails(self, tmp_path, capsys):
        """Treaty with empty name is reported as failure."""
        catalog = tmp_path / "treaties.json"
        treaties = [_treaty_entry(treaty_id="noname", name="")]
        catalog.write_text(json.dumps(treaties), encoding="utf-8")

        call_command("ingest_treaties", "--all", "--catalog", str(catalog))
        captured = capsys.readouterr()

        assert "Failed:" in captured.out


# ---------------------------------------------------------------------------
# Direct unit tests (create_law_and_version)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestIngestTreatyIdempotency:
    """Test that ingest_treaties is idempotent at the record level."""

    def _make_treaty(self, treaty_id, **overrides):
        defaults = {
            "id": treaty_id,
            "name": "Tratado de Libre Comercio entre México y Chile",
            "treaty_type": "bilateral",
            "parties": "México, Chile",
            "date_signed": "2010-05-15",
            "date_ratified": "2011-01-01",
            "place_adopted": "Santiago",
            "url": "https://example.com/treaty/123",
            "pdf_url": "",
            "source": "sre_tratados",
            "full_text": "",
        }
        defaults.update(overrides)
        return defaults

    def test_double_ingest_no_duplicate_versions(self):
        from apps.api.management.commands.ingest_treaties import Command

        tid = f"test_treaty_{uuid.uuid4().hex[:8]}"
        treaty = self._make_treaty(tid)

        cmd = Command()
        r1 = cmd.create_law_and_version(treaty)
        assert r1["success"] is True
        assert r1["version_created"] is True

        r2 = cmd.create_law_and_version(treaty)
        assert r2["success"] is True
        assert r2["version_created"] is False

        law = Law.objects.get(official_id=f"treaty_{tid}")
        assert LawVersion.objects.filter(law=law).count() == 1

    def test_date_fallback_to_signed(self):
        from apps.api.management.commands.ingest_treaties import Command

        tid = f"test_treaty_{uuid.uuid4().hex[:8]}"
        treaty = self._make_treaty(tid, date_ratified="", date_signed="2015-06-20")

        cmd = Command()
        cmd.create_law_and_version(treaty)

        law = Law.objects.get(official_id=f"treaty_{tid}")
        version = LawVersion.objects.get(law=law)
        assert str(version.publication_date) == "2015-06-20"

    def test_dry_run_no_db_writes(self):
        from apps.api.management.commands.ingest_treaties import Command

        tid = f"test_treaty_{uuid.uuid4().hex[:8]}"
        treaty = self._make_treaty(tid)

        cmd = Command()
        r = cmd.create_law_and_version(treaty, dry_run=True)
        assert r["success"] is True
        assert r["action"] == "dry_run"
        assert not Law.objects.filter(official_id=f"treaty_{tid}").exists()


# ---------------------------------------------------------------------------
# _slugify helper
# ---------------------------------------------------------------------------
class TestSlugify:
    """Unit tests for the _slugify helper."""

    def test_basic_slugify(self):
        assert _slugify("Tratado de Libre Comercio") == "tratado_de_libre_comercio"

    def test_special_characters_removed(self):
        result = _slugify("Convenio (México-USA) #123")
        assert "(" not in result
        assert "#" not in result

    def test_truncates_at_150(self):
        long_name = "a" * 200
        assert len(_slugify(long_name)) == 150
