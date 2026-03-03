"""
Tests for treaty ingestion — idempotency, error handling, and helper functions.
"""

import uuid

import pytest

from apps.api.models import Law, LawVersion


@pytest.mark.django_db
class TestIngestTreatyIdempotency:
    """Test that ingest_treaties management command is idempotent."""

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
        """Running treaty ingest twice produces exactly 1 LawVersion."""
        from apps.api.management.commands.ingest_treaties import Command

        tid = f"test_treaty_{uuid.uuid4().hex[:8]}"
        treaty = self._make_treaty(tid)

        cmd = Command()

        r1 = cmd.create_law_and_version(treaty)
        assert r1["success"] is True
        assert r1["action"] == "created"
        assert r1["version_created"] is True

        r2 = cmd.create_law_and_version(treaty)
        assert r2["success"] is True
        assert r2["action"] == "updated"
        assert r2["version_created"] is False

        law = Law.objects.get(official_id=f"treaty_{tid}")
        assert LawVersion.objects.filter(law=law).count() == 1

    def test_version_updated_on_rerun(self):
        """Re-running updates metadata on existing treaty LawVersion."""
        from apps.api.management.commands.ingest_treaties import Command

        tid = f"test_treaty_{uuid.uuid4().hex[:8]}"
        treaty = self._make_treaty(tid, url="https://old.example.com")

        cmd = Command()
        cmd.create_law_and_version(treaty)

        treaty["url"] = "https://new.example.com"
        cmd.create_law_and_version(treaty)

        law = Law.objects.get(official_id=f"treaty_{tid}")
        version = LawVersion.objects.get(law=law)
        assert version.dof_url == "https://new.example.com"

    def test_treaty_fields_correct(self):
        """Verify law fields are set correctly for treaties."""
        from apps.api.management.commands.ingest_treaties import Command

        tid = f"test_treaty_{uuid.uuid4().hex[:8]}"
        treaty = self._make_treaty(tid)

        cmd = Command()
        r = cmd.create_law_and_version(treaty)
        assert r["success"] is True

        law = Law.objects.get(official_id=f"treaty_{tid}")
        assert law.tier == "federal"
        assert law.law_type == "non_legislative"
        assert law.category == "bilateral"
        assert law.status == Law.Status.VIGENTE

    def test_treaty_missing_name_fails(self):
        """Treaty with no name returns failure."""
        from apps.api.management.commands.ingest_treaties import Command

        tid = f"test_treaty_{uuid.uuid4().hex[:8]}"
        treaty = self._make_treaty(tid, name="")

        cmd = Command()
        r = cmd.create_law_and_version(treaty)
        assert r["success"] is False

    def test_date_fallback_to_signed(self):
        """When date_ratified is empty, falls back to date_signed."""
        from apps.api.management.commands.ingest_treaties import Command

        tid = f"test_treaty_{uuid.uuid4().hex[:8]}"
        treaty = self._make_treaty(tid, date_ratified="", date_signed="2015-06-20")

        cmd = Command()
        cmd.create_law_and_version(treaty)

        law = Law.objects.get(official_id=f"treaty_{tid}")
        version = LawVersion.objects.get(law=law)
        assert str(version.publication_date) == "2015-06-20"

    def test_dry_run_no_db_writes(self):
        """Dry run returns success without creating DB records."""
        from apps.api.management.commands.ingest_treaties import Command

        tid = f"test_treaty_{uuid.uuid4().hex[:8]}"
        treaty = self._make_treaty(tid)

        cmd = Command()
        r = cmd.create_law_and_version(treaty, dry_run=True)
        assert r["success"] is True
        assert r["action"] == "dry_run"
        assert not Law.objects.filter(official_id=f"treaty_{tid}").exists()


class TestSlugify:
    """Test the _slugify helper function."""

    def test_basic_slugification(self):
        from apps.api.management.commands.ingest_treaties import _slugify

        assert _slugify("Tratado de Libre Comercio") == "tratado_de_libre_comercio"

    def test_special_chars_removed(self):
        from apps.api.management.commands.ingest_treaties import _slugify

        result = _slugify("Convenio (México-USA) #123")
        assert "(" not in result
        assert "#" not in result

    def test_truncation(self):
        from apps.api.management.commands.ingest_treaties import _slugify

        long_name = "A" * 200
        result = _slugify(long_name)
        assert len(result) <= 150
