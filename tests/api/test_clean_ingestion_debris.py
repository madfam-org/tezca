"""Tests for the clean_ingestion_debris management command."""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.api.management.commands.clean_ingestion_debris import (
    DUP_ID_CLAUSE,
    PAGE_HEADER_CLAUSE,
    laws_with_symptom_query,
)
from apps.api.models import Law

TABS = " \t\t\t\t \t\t\t\t"
DIRTY = (
    "LEY Federal de Protección de Datos Personales en Posesión de los "
    f"Particulares{TABS}DOF 20/03/2025{TABS}Nueva reforma"
)
CLEAN = "LEY Federal de Protección de Datos Personales en Posesión de los Particulares"


def _law(official_id, name, **extra):
    return Law.objects.create(
        official_id=official_id, name=name, tier="federal", **extra
    )


def test_symptom_queries_only_read_and_count_distinct_laws():
    body = laws_with_symptom_query(DUP_ID_CLAUSE)
    assert body["size"] == 0
    assert body["aggs"]["laws"]["cardinality"]["field"] == "law_id"
    assert DUP_ID_CLAUSE == {"regexp": {"article": {"value": ".*-dup[0-9]+"}}}
    assert PAGE_HEADER_CLAUSE == {
        "match_phrase": {"text": "Secretaría de Servicios Parlamentarios"}
    }


@pytest.mark.django_db
class TestCleanIngestionDebris:
    def test_default_run_writes_nothing(self, capsys):
        _law("lfpdppp", DIRTY, short_name=DIRTY[:50] + "...")

        call_command("clean_ingestion_debris", "--law-id", "lfpdppp", "--skip-es")

        out = capsys.readouterr().out
        assert "Would rename lfpdppp" in out
        assert "Dry run" in out
        assert Law.objects.get(official_id="lfpdppp").name == DIRTY

    def test_apply_repairs_only_the_selected_law(self, capsys):
        _law("lfpdppp", DIRTY, short_name=DIRTY[:50] + "...")
        _law("ladua", f"LEY Aduanera{TABS}DOF 15/12/1995")

        call_command(
            "clean_ingestion_debris", "--law-id", "lfpdppp", "--apply", "--skip-es"
        )

        law = Law.objects.get(official_id="lfpdppp")
        assert law.name == CLEAN
        assert law.short_name == CLEAN[:50] + "..."
        assert "\t" in Law.objects.get(official_id="ladua").name
        assert "repairable: 2" in capsys.readouterr().out

    def test_all_names_repairs_every_dirty_name_and_is_idempotent(self):
        _law("lfpdppp", DIRTY)
        _law("ladua", f"LEY Aduanera{TABS}DOF 15/12/1995")
        _law("amparo", "Ley de Amparo", short_name="Amparo")

        for _ in range(2):
            call_command(
                "clean_ingestion_debris", "--all-names", "--apply", "--skip-es"
            )

        assert Law.objects.get(official_id="lfpdppp").name == CLEAN
        assert Law.objects.get(official_id="ladua").name == "LEY Aduanera"
        amparo = Law.objects.get(official_id="amparo")
        assert (amparo.name, amparo.short_name) == ("Ley de Amparo", "Amparo")

    def test_apply_without_a_selection_is_refused(self):
        with pytest.raises(CommandError):
            call_command("clean_ingestion_debris", "--apply", "--skip-es")

    def test_unknown_law_id_is_refused(self):
        with pytest.raises(CommandError):
            call_command("clean_ingestion_debris", "--law-id", "nope", "--skip-es")

    def test_report_counts_other_laws_from_elasticsearch(self, tmp_path):
        _law("lfpdppp", DIRTY)
        es = MagicMock()
        es.ping.return_value = True
        es.search.return_value = {
            "hits": {"total": {"value": 31}},
            "aggregations": {
                "laws": {"value": 2},
                "sample": {
                    "buckets": [
                        {"key": "lfpdppp", "doc_count": 28},
                        {"key": "cff", "doc_count": 3},
                    ]
                },
            },
        }
        output = tmp_path / "report.json"

        with patch("apps.api.config.es_client", es):
            call_command("clean_ingestion_debris", "--output", str(output))

        report = json.loads(output.read_text(encoding="utf-8"))
        assert report["dry_run"] is True
        assert report["elasticsearch"]["page_furniture"]["laws"] == 2
        assert report["elasticsearch"]["dup_article_ids"]["articles"] == 31
        assert es.search.call_count == 2
        # Reads only: no write API was touched.
        assert not es.delete_by_query.called and not es.index.called

    def test_unreachable_elasticsearch_does_not_abort_the_report(self, capsys):
        es = MagicMock()
        es.ping.return_value = False

        with patch("apps.api.config.es_client", es):
            call_command("clean_ingestion_debris")

        assert "not measured" in capsys.readouterr().out
