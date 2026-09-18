"""Tests for the ingest_feriados command — the CNBV días-inhábiles-bancarios
corpus lands as Law + LawVersion rows, modeled as administrative rules
(``non_legislative`` / ``dias_inhabiles_bancarios``), never as leyes. This is
what makes the bank dates the feriados artifact emits traceable to the ingested
legal source they were read from."""

import pytest
from django.core.management import call_command

from apps.api.models import Law, LawVersion
from apps.scraper.federal.feriados_legales import FERIADOS_DOCUMENTS

CID = "cnbv-dias-inhabiles-bancarios-2026"


@pytest.mark.django_db
class TestIngestFeriadosCommand:
    def test_ingests_the_pinned_corpus_without_a_catalog(self):
        call_command("ingest_feriados")
        assert Law.objects.filter(official_id__startswith="cnbv-dias-inhabiles-").count() == len(
            FERIADOS_DOCUMENTS
        )
        for doc in FERIADOS_DOCUMENTS:
            assert Law.objects.filter(official_id=doc.official_id).exists()

    def test_models_the_disposicion_as_administrative_rules_not_a_ley(self):
        call_command("ingest_feriados")
        law = Law.objects.get(official_id=CID)
        assert law.law_type == Law.LawType.NON_LEGISLATIVE
        assert law.category == "dias_inhabiles_bancarios"
        assert law.domains == ["banking"]
        assert law.tier == "federal"

    def test_records_the_dof_url_and_publication_date(self):
        call_command("ingest_feriados")
        law = Law.objects.get(official_id=CID)
        version = LawVersion.objects.get(law=law)
        assert "5775684" in version.dof_url
        assert str(version.publication_date) == "2025-12-10"

    def test_is_idempotent(self):
        call_command("ingest_feriados")
        call_command("ingest_feriados")
        assert Law.objects.filter(official_id=CID).count() == 1
        assert LawVersion.objects.filter(law__official_id=CID).count() == 1

    def test_dry_run_writes_nothing(self):
        call_command("ingest_feriados", "--dry-run")
        assert not Law.objects.filter(official_id=CID).exists()
