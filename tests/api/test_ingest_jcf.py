"""Tests for the ingest_jcf management command and the JCF API surface.

Two concerns:

1. **Ingestion** — the pinned JCF corpus lands as Law + LawVersion rows
   modeled as administrative rules (``non_legislative`` /
   ``reglas_de_operacion``), never as leyes.
2. **API surface** — the documents resolve through the same endpoints
   symbiosis-hcm's ``tezca_client`` already consumes, in particular
   ``GET /api/v1/laws/{official_id}/``, plus the ``law_type`` /
   ``category`` / ``domain`` filters that let a labor consumer find them.
"""

import json

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.api.models import Law, LawVersion
from apps.scraper.federal.jcf_scraper import (
    JCF_CATEGORY,
    JCF_DOCUMENTS,
    JCF_DOCUMENTS_BY_ID,
    JcfFetcher,
)

CONTROLLING_ID = "jcf-reglas-2026"


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIngestJcfCommand:
    def test_ingests_the_pinned_corpus_without_a_catalog_file(self):
        """JCF is an enumerated corpus, so the registry is the source of
        truth — ingestion must not require a scraper run first."""
        call_command("ingest_jcf")

        assert Law.objects.filter(official_id__startswith="jcf-").count() == len(
            JCF_DOCUMENTS
        )
        for doc in JCF_DOCUMENTS:
            assert Law.objects.filter(official_id=doc.official_id).exists()

    def test_models_documents_as_administrative_rules_not_leyes(self):
        call_command("ingest_jcf")

        for law in Law.objects.filter(official_id__startswith="jcf-"):
            assert law.law_type == Law.LawType.NON_LEGISLATIVE
            assert law.category == JCF_CATEGORY
            assert law.domains == ["labor"]
            assert law.tier == "federal"

    def test_records_dof_url_and_publication_date(self):
        call_command("ingest_jcf")

        law = Law.objects.get(official_id=CONTROLLING_ID)
        assert "5777674" in law.source_url
        assert law.status == Law.Status.VIGENTE

        version = law.versions.get()
        assert version.publication_date.isoformat() == "2025-12-31"
        # Transitorio Primero: in force the day after publication.
        assert version.valid_from.isoformat() == "2026-01-01"

    def test_vigencia_note_is_persisted_for_the_residual_lineamientos(self):
        """The 2019 Lineamientos are the one document whose status a
        consumer cannot act on without the explanation."""
        call_command("ingest_jcf")

        law = Law.objects.get(official_id="jcf-lineamientos-2019")
        assert law.status == Law.Status.UNKNOWN
        assert law.status != Law.Status.ABROGADA

        note = law.versions.get().change_summary
        assert note
        assert "jcf-reglas-2026" in note

    def test_unverified_prior_rop_is_not_ingested(self):
        """The abrogated 2025 ROP has an unverified DOF codigo, so it is
        absent by design rather than registered with a wrong citation."""
        call_command("ingest_jcf")
        assert not Law.objects.filter(official_id="jcf-reglas-2025").exists()

    def test_is_idempotent(self):
        call_command("ingest_jcf")
        call_command("ingest_jcf")

        assert Law.objects.filter(official_id__startswith="jcf-").count() == len(
            JCF_DOCUMENTS
        )
        assert LawVersion.objects.filter(law__official_id=CONTROLLING_ID).count() == 1

    def test_dry_run_writes_nothing(self, capsys):
        call_command("ingest_jcf", "--dry-run")

        assert not Law.objects.filter(official_id__startswith="jcf-").exists()
        assert "[DRY-RUN]" in capsys.readouterr().out

    def test_reports_missing_text_plainly(self, capsys, tmp_path):
        """Metadata-only ingestion is a legitimate state; the command must
        say the text is not searchable rather than imply success."""
        call_command("ingest_jcf", "--text-dir", str(tmp_path))

        out = capsys.readouterr().out
        assert "text is NOT" in out
        assert "jcf_scraper --download" in out

    def test_links_materialized_text_onto_the_version(self, tmp_path, capsys):
        akn = tmp_path / f"{CONTROLLING_ID}.xml"
        akn.write_text("<?xml version='1.0'?><akomaNtoso/>", encoding="utf-8")

        call_command("ingest_jcf", "--text-dir", str(tmp_path))

        version = LawVersion.objects.get(law__official_id=CONTROLLING_ID)
        assert version.xml_file_path == str(akn)
        assert "index_laws" in capsys.readouterr().out

    def test_links_raw_text_fallback_for_prose_documents(self, tmp_path):
        raw = tmp_path / "jcf-acuerdo-simplificacion-2026.txt"
        raw.write_text("STPS-03-026", encoding="utf-8")

        call_command("ingest_jcf", "--text-dir", str(tmp_path))

        version = LawVersion.objects.get(
            law__official_id="jcf-acuerdo-simplificacion-2026"
        )
        assert version.xml_file_path == str(raw)

    def test_ingests_from_a_catalog_file(self, tmp_path):
        catalog_dir = tmp_path / "jcf"
        JcfFetcher(output_dir=str(catalog_dir)).run(download_documents=False)

        call_command("ingest_jcf", "--catalog", str(catalog_dir / "catalog.json"))

        assert Law.objects.filter(official_id__startswith="jcf-").count() == len(
            JCF_DOCUMENTS
        )

    def test_missing_catalog_is_an_error_not_a_silent_noop(self, tmp_path, capsys):
        call_command("ingest_jcf", "--catalog", str(tmp_path / "nope.json"))

        assert not Law.objects.filter(official_id__startswith="jcf-").exists()
        assert "Catalog not found" in capsys.readouterr().err

    def test_empty_catalog_ingests_nothing(self, tmp_path, capsys):
        catalog = tmp_path / "catalog.json"
        catalog.write_text(json.dumps([]), encoding="utf-8")

        call_command("ingest_jcf", "--catalog", str(catalog))

        assert not Law.objects.filter(official_id__startswith="jcf-").exists()
        assert "empty" in capsys.readouterr().out.lower()


# ---------------------------------------------------------------------------
# API surface — what symbiosis-hcm actually calls
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestJcfApiSurface:
    @pytest.fixture(autouse=True)
    def _ingest(self):
        call_command("ingest_jcf")

    def test_law_detail_resolves_by_official_id(self, client):
        """symbiosis-hcm's enrich_with_tezca calls exactly this route."""
        url = reverse("law-detail", kwargs={"law_id": CONTROLLING_ID})
        resp = client.get(url)

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == CONTROLLING_ID
        assert data["law_type"] == "non_legislative"
        assert data["category"] == JCF_CATEGORY
        assert data["status"] == "vigente"
        assert "labor" in data["domains"]
        assert "5777674" in data["source_url"]

    def test_law_detail_exposes_the_vigencia_note_on_the_version(self, client):
        url = reverse("law-detail", kwargs={"law_id": "jcf-lineamientos-2019"})
        data = client.get(url).json()

        assert data["status"] == "unknown"
        assert data["versions"][0]["change_summary"]
        assert "5547857" in data["versions"][0]["dof_url"]

    def test_every_pinned_document_resolves(self, client):
        for doc in JCF_DOCUMENTS:
            url = reverse("law-detail", kwargs={"law_id": doc.official_id})
            assert client.get(url).status_code == 200, doc.official_id

    def test_law_list_filters_by_the_new_category(self, client):
        resp = client.get(
            reverse("law-list"), {"category": JCF_CATEGORY, "page_size": 100}
        )

        assert resp.status_code == 200
        ids = {row["id"] for row in resp.json()["results"]}
        assert ids == {doc.official_id for doc in JCF_DOCUMENTS}

    def test_law_list_filters_by_law_type(self, client):
        resp = client.get(
            reverse("law-list"), {"law_type": "non_legislative", "page_size": 100}
        )

        ids = {row["id"] for row in resp.json()["results"]}
        assert CONTROLLING_ID in ids

    def test_law_list_filters_by_labor_domain(self, client):
        """A labor-domain consumer must find JCF without knowing its
        category name.

        The ``domain`` filter ORs ``Law.domains @> [...]`` onto a
        ``category__in`` fallback, but the JSONField branch only runs on
        PostgreSQL (see LawListView.get). JCF carries ``domains=["labor"]``
        with ``category="reglas_de_operacion"``, so it is discoverable on
        the production engine and not on SQLite. Asserting per-engine keeps
        this honest instead of encoding the SQLite gap as correct.
        """
        from django.db import connection

        resp = client.get(reverse("law-list"), {"domain": "labor", "page_size": 100})
        ids = {row["id"] for row in resp.json()["results"]}

        if connection.vendor == "postgresql":
            assert CONTROLLING_ID in ids
        else:
            pytest.skip(
                "domain filter's JSONField branch is PostgreSQL-only; "
                "category filter covers discovery on this engine"
            )

    def test_domains_field_is_the_routing_key_for_labor_consumers(self, client):
        """Engine-independent guarantee behind the domain filter: whatever
        the query path, the row itself carries the labor domain that
        webhook ``domain_filter`` and DOMAIN_MAP routing key on."""
        law = Law.objects.get(official_id=CONTROLLING_ID)
        assert law.domains == ["labor"]

        detail = client.get(
            reverse("law-detail", kwargs={"law_id": CONTROLLING_ID})
        ).json()
        assert "labor" in detail["domains"]

    def test_laws_exist_reports_the_controlling_rop(self, client):
        resp = client.get(reverse("laws-exist"), {"ids": CONTROLLING_ID})
        assert resp.status_code == 200
        assert CONTROLLING_ID in resp.json()["existing"]

    def test_unknown_jcf_id_still_404s(self, client):
        url = reverse("law-detail", kwargs={"law_id": "jcf-reglas-1999"})
        assert client.get(url).status_code == 404


# ---------------------------------------------------------------------------
# Registry file
# ---------------------------------------------------------------------------


class TestLawRegistryEntries:
    """data/law_registry.json is the catalog the coverage/universe views
    read; the JCF entries must agree with the pinned scraper corpus."""

    @pytest.fixture(scope="class")
    def registry(self):
        from apps.api.utils.paths import resolve_data_path

        path = resolve_data_path("data/law_registry.json")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_registry_has_an_entry_per_pinned_document(self, registry):
        entries = {
            e["id"]: e for e in registry["federal_laws"] if e["id"].startswith("jcf-")
        }
        assert set(entries) == set(JCF_DOCUMENTS_BY_ID)

    def test_registry_entries_agree_with_the_pinned_corpus(self, registry):
        entries = {e["id"]: e for e in registry["federal_laws"]}
        for official_id, doc in JCF_DOCUMENTS_BY_ID.items():
            entry = entries[official_id]
            assert entry["publication_date"] == doc.publication_date
            assert entry["category"] == JCF_CATEGORY
            assert entry["tier"] == "labor"
            assert doc.dof_codigo in entry["url"]
            assert entry["notes"].strip()

    def test_no_jcf_entry_is_typed_as_a_ley(self, registry):
        for entry in registry["federal_laws"]:
            if entry["id"].startswith("jcf-"):
                assert entry["type"] != "ley"
                assert entry["type"] in ("reglas_de_operacion", "acuerdo")

    def test_the_new_category_is_registered_with_a_label(self, registry):
        category = registry["categories"][JCF_CATEGORY]
        assert category["name"]
        assert category["description"]

    def test_registry_ids_are_unique(self, registry):
        ids = [e["id"] for e in registry["federal_laws"]]
        assert len(ids) == len(set(ids))
