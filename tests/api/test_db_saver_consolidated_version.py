"""DatabaseSaver: clean names and the consolidated text's version date.

The registry's ``publication_date`` is the law's original DOF date; the text
ingested is the consolidated one, current to the «Última Reforma DOF» its PDF
header states. Production labelled the LFPDPPP text of 14-11-2025 as the
version of 2025-03-20.
"""

from datetime import date

import pytest

from apps.api.models import Law, LawVersion
from apps.ingestion.db_saver import DatabaseSaver

RAW_NAME = (
    "LEY Federal de Protección de Datos Personales en Posesión de los Particulares"
    " \t\t\t\t \t\t\t\tDOF 20/03/2025 \t\t\t\t \t\t\t\tNueva reforma"
)
CLEAN_NAME = (
    "LEY Federal de Protección de Datos Personales en Posesión de los Particulares"
)


def _metadata(**overrides):
    metadata = {
        "id": "lfpdppp",
        "name": RAW_NAME,
        "short_name": RAW_NAME[:50] + "...",
        "category": "uncategorized",
        "publication_date": "2025-03-20",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf",
        "status": "discovered",
    }
    metadata.update(overrides)
    return metadata


class TestParseLastReform:
    def test_accepts_iso_strings_and_dates(self):
        assert DatabaseSaver._parse_last_reform("2025-11-14") == date(2025, 11, 14)
        assert DatabaseSaver._parse_last_reform(date(2025, 11, 14)) == date(
            2025, 11, 14
        )

    def test_rejects_missing_or_malformed_values(self):
        assert DatabaseSaver._parse_last_reform(None) is None
        assert DatabaseSaver._parse_last_reform("") is None
        assert DatabaseSaver._parse_last_reform("14-11-2025") is None


@pytest.mark.django_db
class TestSaveLawVersion:
    def test_new_law_name_has_no_catalog_debris(self):
        DatabaseSaver().save_law_version(_metadata(), "data/x.xml", "x.pdf")

        law = Law.objects.get(official_id="lfpdppp")
        assert law.name == CLEAN_NAME
        assert "\t" not in law.short_name
        assert law.short_name == CLEAN_NAME[:50] + "..."

    def test_existing_dirty_name_is_cleaned_on_reingest(self):
        Law.objects.create(official_id="lfpdppp", name=RAW_NAME, tier="federal")

        DatabaseSaver().save_law_version(_metadata(), "data/x.xml", "x.pdf")

        assert Law.objects.get(official_id="lfpdppp").name == CLEAN_NAME

    def test_without_a_reform_date_the_version_is_the_publication(self):
        version = DatabaseSaver().save_law_version(_metadata(), "data/x.xml", "x.pdf")

        assert version.publication_date == date(2025, 3, 20)
        assert version.change_summary is None

    def test_consolidated_text_is_dated_by_its_last_reform(self):
        version = DatabaseSaver().save_law_version(
            _metadata(last_reform_date="2025-11-14"), "data/x.xml", "x.pdf"
        )

        assert version.publication_date == date(2025, 11, 14)
        assert version.valid_from == date(2025, 11, 14)
        assert "14-11-2025" in version.change_summary

    def test_existing_publication_version_is_kept_and_closed(self):
        saver = DatabaseSaver()
        original = saver.save_law_version(_metadata(), "data/x.xml", "x.pdf")

        saver.save_law_version(
            _metadata(last_reform_date="2025-11-14"), "data/x.xml", "x.pdf"
        )

        law = Law.objects.get(official_id="lfpdppp")
        assert LawVersion.objects.filter(law=law).count() == 2
        assert law.versions.first().publication_date == date(2025, 11, 14)
        original.refresh_from_db()
        assert original.publication_date == date(2025, 3, 20)
        assert original.valid_to == date(2025, 11, 14)

    def test_reingest_with_the_same_reform_date_adds_no_version(self):
        saver = DatabaseSaver()
        for _ in range(2):
            saver.save_law_version(
                _metadata(last_reform_date="2025-11-14"), "data/x.xml", "x.pdf"
            )

        assert LawVersion.objects.filter(law__official_id="lfpdppp").count() == 1

    def test_reform_date_before_publication_is_ignored(self):
        version = DatabaseSaver().save_law_version(
            _metadata(last_reform_date="2024-01-01"), "data/x.xml", "x.pdf"
        )

        assert version.publication_date == date(2025, 3, 20)
