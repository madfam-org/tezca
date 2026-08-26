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


@pytest.mark.django_db
class TestSaveLawVersionValidTo:
    """Defect #7: creating a 2nd version must close the 1st version's validity.

    ``LawVersion.valid_to`` is READ by the API/UI (law_views.py,
    VersionTimeline.tsx) but was WRITTEN nowhere in the pipeline, so a
    superseded version's ``valid_to`` stayed null forever and an older/repealed
    text looked "current". These tests pin the supersession write on version
    creation (half-open interval: prior.valid_to = new.valid_from).
    """

    def _metadata(self, **overrides):
        md = {
            "id": "liva",
            "name": "Ley del Impuesto al Valor Agregado",
            "short_name": "LIVA",
            "category": "fiscal",
            "publication_date": "2020-01-01",
            "url": "https://example.com/liva.pdf",
            "status": "vigente",
        }
        md.update(overrides)
        return md

    def test_second_version_closes_first_version_valid_to(self):
        from datetime import date

        from apps.api.models import Law, LawVersion

        saver = DatabaseSaver()

        # First version (2020-01-01).
        saver.save_law_version(
            self._metadata(publication_date="2020-01-01"),
            xml_path="data/liva-2020.xml",
            pdf_path="liva-2020.pdf",
        )
        law = Law.objects.get(official_id="liva")
        v1 = law.versions.get(publication_date=date(2020, 1, 1))
        # A single version is current — valid_to stays null.
        assert v1.valid_to is None

        # Second version (2022-06-15) — a reform.
        saver.save_law_version(
            self._metadata(publication_date="2022-06-15"),
            xml_path="data/liva-2022.xml",
            pdf_path="liva-2022.pdf",
        )

        v1.refresh_from_db()
        v2 = law.versions.get(publication_date=date(2022, 6, 15))

        # The FIRST version is now superseded: its valid_to == the second
        # version's valid_from (half-open interval).
        assert v1.valid_to is not None, "prior version valid_to was never written"
        assert v1.valid_to == v2.valid_from == date(2022, 6, 15)
        # The newest version remains current.
        assert v2.valid_to is None

    def test_third_version_closes_second_only(self):
        from datetime import date

        from apps.api.models import Law

        saver = DatabaseSaver()
        for pub in ("2020-01-01", "2022-06-15", "2024-03-10"):
            saver.save_law_version(
                self._metadata(publication_date=pub),
                xml_path=f"data/liva-{pub}.xml",
                pdf_path=f"liva-{pub}.pdf",
            )

        law = Law.objects.get(official_id="liva")
        v1 = law.versions.get(publication_date=date(2020, 1, 1))
        v2 = law.versions.get(publication_date=date(2022, 6, 15))
        v3 = law.versions.get(publication_date=date(2024, 3, 10))

        # Each older version closed against its immediate successor.
        assert v1.valid_to == date(2022, 6, 15)
        assert v2.valid_to == date(2024, 3, 10)
        # Newest is current.
        assert v3.valid_to is None

    def test_single_version_stays_current(self):
        from apps.api.models import Law

        saver = DatabaseSaver()
        saver.save_law_version(
            self._metadata(),
            xml_path="data/liva.xml",
            pdf_path="liva.pdf",
        )
        law = Law.objects.get(official_id="liva")
        assert law.versions.count() == 1
        assert law.versions.first().valid_to is None

    def test_out_of_order_ingestion_closes_correct_intervals(self):
        # An earlier reform arriving AFTER a later one must still yield a
        # correctly ordered chain (the earlier version closes against the later).
        from datetime import date

        from apps.api.models import Law

        saver = DatabaseSaver()
        # Ingest the 2024 version first…
        saver.save_law_version(
            self._metadata(publication_date="2024-03-10"),
            xml_path="data/liva-2024.xml",
            pdf_path="liva-2024.pdf",
        )
        # …then the older 2020 version arrives.
        saver.save_law_version(
            self._metadata(publication_date="2020-01-01"),
            xml_path="data/liva-2020.xml",
            pdf_path="liva-2020.pdf",
        )

        law = Law.objects.get(official_id="liva")
        v_old = law.versions.get(publication_date=date(2020, 1, 1))
        v_new = law.versions.get(publication_date=date(2024, 3, 10))

        # The 2020 version (inserted second, but chronologically first) is
        # closed against the 2024 successor; the 2024 version stays current.
        assert v_old.valid_to == date(2024, 3, 10)
        assert v_new.valid_to is None

    def test_reingest_same_version_does_not_reset_valid_to(self):
        # Re-saving an existing version (not v_created) must not disturb an
        # already-closed prior interval.
        from datetime import date

        from apps.api.models import Law

        saver = DatabaseSaver()
        saver.save_law_version(
            self._metadata(publication_date="2020-01-01"),
            xml_path="data/liva-2020.xml",
            pdf_path="liva-2020.pdf",
        )
        saver.save_law_version(
            self._metadata(publication_date="2022-06-15"),
            xml_path="data/liva-2022.xml",
            pdf_path="liva-2022.pdf",
        )
        law = Law.objects.get(official_id="liva")
        v1 = law.versions.get(publication_date=date(2020, 1, 1))
        assert v1.valid_to == date(2022, 6, 15)

        # Re-ingest the 2020 version (metadata refresh) — valid_to unchanged.
        saver.save_law_version(
            self._metadata(publication_date="2020-01-01"),
            xml_path="data/liva-2020-v2.xml",
            pdf_path="liva-2020.pdf",
        )
        v1.refresh_from_db()
        assert v1.valid_to == date(2022, 6, 15)
