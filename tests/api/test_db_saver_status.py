"""
Tests for DatabaseSaver status population (Defect 3).

The registry historically carries non-canonical status strings ("active",
"discovered") that are NOT valid Law.Status choices, and db_saver previously
dropped the field entirely — so every freshly ingested law was created with the
model default (UNKNOWN) and the API served status="unknown". These tests pin
the fix: a law saved with a current version becomes "vigente" and registry
aliases are normalised to valid model choices.
"""

import pytest

from apps.api.models import Law
from apps.ingestion.db_saver import DatabaseSaver


class TestResolveStatus:
    """Pure normalisation logic — no DB required."""

    def test_missing_status_defaults_to_vigente(self):
        assert DatabaseSaver._resolve_status(None) == Law.Status.VIGENTE
        assert DatabaseSaver._resolve_status("") == Law.Status.VIGENTE

    def test_registry_aliases_normalised(self):
        # Non-canonical registry markers → valid model choices.
        assert DatabaseSaver._resolve_status("active") == Law.Status.VIGENTE
        assert DatabaseSaver._resolve_status("discovered") == Law.Status.VIGENTE
        assert DatabaseSaver._resolve_status("ACTIVE") == Law.Status.VIGENTE

    def test_canonical_values_pass_through(self):
        assert DatabaseSaver._resolve_status("vigente") == "vigente"
        assert DatabaseSaver._resolve_status("abrogada") == "abrogada"
        assert DatabaseSaver._resolve_status("derogada") == "derogada"
        assert DatabaseSaver._resolve_status("Vigente") == "vigente"

    def test_resolved_value_is_a_valid_choice(self):
        valid = {choice.value for choice in Law.Status}
        for raw in [None, "active", "discovered", "vigente", "weird-unknown-marker"]:
            assert DatabaseSaver._resolve_status(raw) in valid


@pytest.mark.django_db
class TestSaveLawVersionStatus:
    """End-to-end: save_law_version must populate Law.status."""

    def _metadata(self, **overrides):
        md = {
            "id": "lfpdppp",
            "name": "Ley Federal de Protección de Datos Personales",
            "short_name": "LFPDPPP",
            "category": "general",
            "publication_date": "2025-03-20",
            "url": "https://example.com/lfpdppp.pdf",
            "status": "discovered",  # non-canonical registry value
        }
        md.update(overrides)
        return md

    def test_new_law_gets_vigente_status(self):
        saver = DatabaseSaver()
        saver.save_law_version(
            self._metadata(), xml_path="data/x.xml", pdf_path="x.pdf"
        )

        law = Law.objects.get(official_id="lfpdppp")
        # NOT the model default "unknown".
        assert law.status == Law.Status.VIGENTE
        assert law.status != Law.Status.UNKNOWN

    def test_explicit_vigente_status_honoured(self):
        saver = DatabaseSaver()
        saver.save_law_version(
            self._metadata(id="iva", status="vigente"),
            xml_path="data/iva.xml",
            pdf_path="iva.pdf",
        )
        assert Law.objects.get(official_id="iva").status == Law.Status.VIGENTE

    def test_existing_unknown_law_is_promoted(self):
        # A law previously created without status (the pre-fix state).
        Law.objects.create(official_id="cff", name="CFF", tier="federal")
        assert Law.objects.get(official_id="cff").status == Law.Status.UNKNOWN

        saver = DatabaseSaver()
        saver.save_law_version(
            self._metadata(id="cff", name="Código Fiscal", status="active"),
            xml_path="data/cff.xml",
            pdf_path="cff.pdf",
        )
        assert Law.objects.get(official_id="cff").status == Law.Status.VIGENTE

    def test_curated_status_not_downgraded_to_unknown(self):
        # An already-abrogada law must not be reset to unknown by a later save
        # that omits status.
        Law.objects.create(
            official_id="old_law",
            name="Ley Abrogada",
            tier="federal",
            status=Law.Status.ABROGADA,
        )
        saver = DatabaseSaver()
        saver.save_law_version(
            self._metadata(id="old_law", name="Ley Abrogada", status="unknown"),
            xml_path="data/old.xml",
            pdf_path="old.pdf",
        )
        assert Law.objects.get(official_id="old_law").status == Law.Status.ABROGADA
