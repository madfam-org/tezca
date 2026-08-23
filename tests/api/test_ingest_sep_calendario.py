"""Tests for the ingest_sep_calendario command and the SEP calendario API surface.

Two concerns:

1. **Ingestion** — the pinned SEP calendario corpus lands as Law +
   LawVersion rows modeled as administrative rules (``non_legislative`` /
   ``calendario_escolar``), never as leyes.
2. **API surface** — the acuerdo resolves through the same endpoints other
   corpora use, in particular ``GET /api/v1/laws/{official_id}/``, plus the
   ``law_type`` / ``category`` filters.
"""

import json

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.api.models import Law, LawVersion
from apps.scraper.federal.sep_calendario_scraper import (
    SEP_CALENDAR_DOCUMENTS,
    SEP_CATEGORY,
    SepCalendarFetcher,
)

CID = "sep-calendario-escolar-2026-2027"


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIngestSepCalendarioCommand:
    def test_ingests_the_pinned_corpus_without_a_catalog_file(self):
        """The SEP calendario is an enumerated corpus (one acuerdo per
        ciclo), so the registry is the source of truth — ingestion must not
        require a scraper run first."""
        call_command("ingest_sep_calendario")

        assert Law.objects.filter(
            official_id__startswith="sep-calendario-"
        ).count() == (len(SEP_CALENDAR_DOCUMENTS))
        for doc in SEP_CALENDAR_DOCUMENTS:
            assert Law.objects.filter(official_id=doc.official_id).exists()

    def test_models_the_acuerdo_as_administrative_rules_not_a_ley(self):
        call_command("ingest_sep_calendario")

        law = Law.objects.get(official_id=CID)
        assert law.law_type == Law.LawType.NON_LEGISLATIVE
        assert law.category == SEP_CATEGORY == "calendario_escolar"
        assert law.domains == ["education"]
        assert law.tier == "federal"

    def test_records_dof_url_publication_and_vigor_dates(self):
        call_command("ingest_sep_calendario")

        law = Law.objects.get(official_id=CID)
        assert "5793645" in law.source_url
        assert law.status == Law.Status.VIGENTE

        version = law.versions.get()
        assert version.publication_date.isoformat() == "2026-07-15"
        # Transitorio Primero: in force the day after publication.
        assert version.valid_from.isoformat() == "2026-07-16"

    def test_vigencia_note_records_the_abrogation_of_the_prior_acuerdo(self):
        call_command("ingest_sep_calendario")

        note = LawVersion.objects.get(law__official_id=CID).change_summary
        assert note
        assert "18/06/25" in note  # the acuerdo it abrogates
        assert "185" in note  # the day count

    def test_is_idempotent(self):
        call_command("ingest_sep_calendario")
        call_command("ingest_sep_calendario")

        assert Law.objects.filter(official_id=CID).count() == 1
        assert LawVersion.objects.filter(law__official_id=CID).count() == 1

    def test_dry_run_writes_nothing(self, capsys):
        call_command("ingest_sep_calendario", "--dry-run")

        assert not Law.objects.filter(
            official_id__startswith="sep-calendario-"
        ).exists()
        assert "[DRY-RUN]" in capsys.readouterr().out

    def test_reports_missing_text_plainly(self, capsys, tmp_path):
        """Metadata-only ingestion is a legitimate state; the command must
        say the text is not searchable rather than imply success."""
        call_command("ingest_sep_calendario", "--text-dir", str(tmp_path))

        out = capsys.readouterr().out
        assert "text is NOT" in out
        assert "sep_calendario_scraper --download" in out

    def test_links_materialized_akn_onto_the_version(self, tmp_path, capsys):
        akn = tmp_path / f"{CID}.xml"
        akn.write_text("<?xml version='1.0'?><akomaNtoso/>", encoding="utf-8")

        call_command("ingest_sep_calendario", "--text-dir", str(tmp_path))

        version = LawVersion.objects.get(law__official_id=CID)
        assert version.xml_file_path == str(akn)
        assert "index_laws" in capsys.readouterr().out

    def test_ingests_from_a_catalog_file(self, tmp_path):
        catalog_dir = tmp_path / "sep"
        SepCalendarFetcher(output_dir=str(catalog_dir)).run(download_documents=False)

        call_command(
            "ingest_sep_calendario", "--catalog", str(catalog_dir / "catalog.json")
        )

        assert Law.objects.filter(official_id=CID).exists()

    def test_missing_catalog_is_an_error_not_a_silent_noop(self, tmp_path, capsys):
        call_command("ingest_sep_calendario", "--catalog", str(tmp_path / "nope.json"))

        assert not Law.objects.filter(
            official_id__startswith="sep-calendario-"
        ).exists()
        assert "Catalog not found" in capsys.readouterr().err

    def test_empty_catalog_ingests_nothing(self, tmp_path, capsys):
        catalog = tmp_path / "catalog.json"
        catalog.write_text(json.dumps([]), encoding="utf-8")

        call_command("ingest_sep_calendario", "--catalog", str(catalog))

        assert not Law.objects.filter(
            official_id__startswith="sep-calendario-"
        ).exists()
        assert "empty" in capsys.readouterr().out.lower()


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSepCalendarApiSurface:
    @pytest.fixture(autouse=True)
    def _ingest(self):
        call_command("ingest_sep_calendario")

    def test_law_detail_resolves_by_official_id(self, client):
        url = reverse("law-detail", kwargs={"law_id": CID})
        resp = client.get(url)

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == CID
        assert data["law_type"] == "non_legislative"
        assert data["category"] == SEP_CATEGORY
        assert data["status"] == "vigente"
        assert "education" in data["domains"]
        assert "5793645" in data["source_url"]

    def test_law_detail_exposes_the_vigencia_note_on_the_version(self, client):
        data = client.get(reverse("law-detail", kwargs={"law_id": CID})).json()
        assert data["versions"][0]["change_summary"]
        assert "5793645" in data["versions"][0]["dof_url"]

    def test_law_list_filters_by_the_new_category(self, client):
        resp = client.get(
            reverse("law-list"), {"category": SEP_CATEGORY, "page_size": 100}
        )
        assert resp.status_code == 200
        ids = {row["id"] for row in resp.json()["results"]}
        assert ids == {doc.official_id for doc in SEP_CALENDAR_DOCUMENTS}

    def test_law_list_filters_by_law_type(self, client):
        resp = client.get(
            reverse("law-list"), {"law_type": "non_legislative", "page_size": 100}
        )
        ids = {row["id"] for row in resp.json()["results"]}
        assert CID in ids

    def test_laws_exist_reports_the_acuerdo(self, client):
        resp = client.get(reverse("laws-exist"), {"ids": CID})
        assert resp.status_code == 200
        assert CID in resp.json()["existing"]

    def test_unknown_ciclo_id_404s(self, client):
        url = reverse(
            "law-detail", kwargs={"law_id": "sep-calendario-escolar-1999-2000"}
        )
        assert client.get(url).status_code == 404
