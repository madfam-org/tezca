"""RMF publication tracking: DOF corpus watch, all DOF editions, loud SAT
scraper failures, health-check alerting, and the off-cluster SAT check.

Fixtures are verbatim pages fetched 2026-11-10:

* ``tests/fixtures/dof/dof_index_2026-10-01_VES.html`` — DOF vespertina of
  2026-10-01 (Segunda RMRMF 2026, codigo 5800157);
* ``tests/fixtures/dof/dof_index_2026-10-30_MAT.html`` — DOF matutina of
  2026-10-30 (Cuarta RMRMF 2026, codigo 5802597), which check_dof_daily saw
  that day and flagged nothing;
* ``tests/fixtures/sat/sat_rmf_rgce2026_links.html`` — every RMF link anchor
  of SAT's 2026 RMF/RGCE page plus a few anexo/RGCE anchors.
"""

import datetime
import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from lxml import html

from apps.scraper.federal.dof_daily import DofScraper
from apps.scraper.scheduling.corpus_watch import (
    CORPUS_WATCHES_BY_KEY,
    RMF_WATCH,
    scan_entries,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"
DOF_VES_2026_10_01 = FIXTURES / "dof" / "dof_index_2026-10-01_VES.html"
DOF_MAT_2026_10_30 = FIXTURES / "dof" / "dof_index_2026-10-30_MAT.html"
SAT_PAGE = FIXTURES / "sat" / "sat_rmf_rgce2026_links.html"
REPO = Path(__file__).resolve().parents[2]


def _parse(path):
    return DofScraper()._parse_index_page(html.fromstring(path.read_bytes()))


# ── DOF index parsing: issuer and section are filled ──────────────────


class TestDofIndexContext:
    def test_issuer_and_section_come_from_the_dof_markup(self):
        entries = _parse(DOF_MAT_2026_10_30)
        assert len(entries) == 15
        assert all(e["category"] for e in entries)
        assert {e["section"] for e in entries} == {"UNICA SECCION"}
        rmf = next(e for e in entries if "5802597" in e["url"])
        assert rmf["category"] == "SECRETARIA DE HACIENDA Y CREDITO PUBLICO"
        assert rmf["title"].startswith(
            "Cuarta Resolución de Modificaciones a la Resolución Miscelánea Fiscal"
        )


# ── RMF corpus watch ───────────────────────────────────────────────────


class TestRmfWatch:
    def test_registered(self):
        assert CORPUS_WATCHES_BY_KEY["rmf_resolucion_miscelanea_fiscal"] is RMF_WATCH
        assert "ingest_rmf_rules" in RMF_WATCH.action
        assert "rmf-rule-ingestion.md" in RMF_WATCH.action

    def test_fires_on_the_4a_rmrmf_morning_edition(self):
        hits = scan_entries(_parse(DOF_MAT_2026_10_30))
        assert [(h.watch_key, h.corpus) for h in hits] == [
            ("rmf_resolucion_miscelanea_fiscal", "rmf")
        ]
        assert "codigo=5802597" in hits[0].url

    def test_fires_on_the_2a_rmrmf_evening_edition(self):
        hits = scan_entries(_parse(DOF_VES_2026_10_01))
        assert len(hits) == 1
        assert hits[0].title.startswith("Segunda Resolución de Modificaciones")
        assert "codigo=5800157" in hits[0].url

    @pytest.mark.parametrize(
        "title",
        [
            "RESOLUCIÓN Miscelánea Fiscal para 2027.",
            "Anexo 1 de la Resolución Miscelánea Fiscal para 2026.",
            "Primera Resolución de Modificaciones a la Resolucion Miscelanea "
            "Fiscal para 2027",
        ],
    )
    def test_matches_annual_modifications_and_anexos(self, title):
        assert RMF_WATCH.matches(title, "SECRETARIA DE HACIENDA Y CREDITO PUBLICO")

    def test_needs_the_federal_issuer(self):
        # A state gazette's "Resolución Miscelánea Fiscal" is not the SAT's.
        assert not RMF_WATCH.matches(
            "Resolución Miscelánea Fiscal para el Estado de Guanajuato",
            "GOBIERNO DEL ESTADO DE GUANAJUATO",
        )
        assert not RMF_WATCH.matches(
            "Tasas para el cálculo del impuesto especial sobre producción y servicios",
            "SECRETARIA DE HACIENDA Y CREDITO PUBLICO",
        )


# ── DOF editions: MAT + VES + EXT, and yesterday's late editions ──────


class TestDofEditions:
    def test_reads_every_edition_and_tags_entries(self):
        scraper = DofScraper(date=datetime.date(2026, 10, 1))
        pages = {"VES": DOF_VES_2026_10_01.read_bytes()}
        requested = []

        def fake_get(url, timeout):
            requested.append(url)
            response = MagicMock()
            response.raise_for_status.return_value = None
            edition = url.rsplit("edicion=", 1)[1]
            response.content = pages.get(edition, b"<html><body></body></html>")
            return response

        scraper.session.get = fake_get
        entries = scraper.fetch_daily_edition()
        assert [u.rsplit("edicion=", 1)[1] for u in requested] == ["MAT", "VES", "EXT"]
        assert all("year=2026&month=10&day=01" in u for u in requested)
        assert len(entries) == 2
        assert {e["edition"] for e in entries} == {"VES"}
        assert {e["date"] for e in entries} == {"2026-10-01"}

    def test_morning_run_also_reads_yesterdays_late_editions_without_duplicates(self):
        scraper = DofScraper(
            date=datetime.date(2026, 10, 2), include_previous_late_editions=True
        )
        calls = []
        shared = {
            "title": "Aviso",
            "url": "https://dof.gob.mx/nota_detalle.php?codigo=1",
        }

        def fake_fetch(date, edition):
            calls.append((date.isoformat(), edition))
            if (date.isoformat(), edition) == ("2026-10-01", "VES"):
                return [
                    {**shared, "date": date.isoformat(), "edition": edition},
                    {
                        "title": "Segunda Resolución de Modificaciones",
                        "url": "https://dof.gob.mx/nota_detalle.php?codigo=5800157",
                        "date": date.isoformat(),
                        "edition": edition,
                    },
                ]
            if edition == "MAT":
                return [{**shared, "date": date.isoformat(), "edition": edition}]
            return []

        scraper._fetch_edition = fake_fetch
        entries = scraper.fetch_daily_edition()
        assert calls == [
            ("2026-10-01", "VES"),
            ("2026-10-01", "EXT"),
            ("2026-10-02", "MAT"),
            ("2026-10-02", "VES"),
            ("2026-10-02", "EXT"),
        ]
        assert [e["url"].rsplit("=", 1)[1] for e in entries] == ["1", "5800157"]

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.api.models.Law")
    @patch("apps.scraper.federal.dof_daily.DofScraper")
    def test_daily_task_asks_for_yesterdays_late_editions(
        self, mock_scraper_cls, mock_law, mock_log_cls
    ):
        from apps.scraper.scheduling.tasks import check_dof_daily

        mock_law.objects.values_list.return_value = []
        mock_scraper_cls.return_value.run.return_value = {"entries": [], "changes": []}
        check_dof_daily()
        assert (
            mock_scraper_cls.call_args.kwargs["include_previous_late_editions"] is True
        )


# ── SAT scraper: zero documents is a failure ───────────────────────────


class TestRmfScraperFailsLoudly:
    @pytest.mark.parametrize("total,expect_error", [(0, True), (7, False)])
    def test_zero_documents_records_an_error(self, total, expect_error):
        from apps.scraper.scheduling import tasks

        scraper = MagicMock()
        scraper.run.return_value = {"total": total, "by_type": {}, "downloaded": 0}
        with patch(
            "apps.scraper.federal.rmf_scraper.RmfScraper", return_value=scraper
        ), patch.object(tasks, "_start_log", return_value=MagicMock()), patch.object(
            tasks, "_finish_log"
        ) as finish:
            tasks.run_rmf_scraper(year=2026)
        error = finish.call_args.kwargs["error"]
        assert bool(error) is expect_error
        if expect_error:
            assert "0 documents" in error and "504" in error

    def test_http_status_is_logged_for_error_responses(self, caplog):
        """Response.__bool__ is False for 4xx/5xx; the status must not be lost."""
        import requests

        from apps.scraper.federal import rmf_scraper

        response = requests.Response()
        response.status_code = 504
        error = requests.HTTPError(response=response)
        scraper = rmf_scraper.RmfScraper.__new__(rmf_scraper.RmfScraper)
        scraper._session = MagicMock()
        scraper._session.get.return_value.raise_for_status.side_effect = error
        scraper._last_request_at = 0.0
        with patch.object(rmf_scraper, "_MAX_RETRIES", 1), patch.object(
            rmf_scraper.time, "sleep"
        ), patch.object(scraper, "_rate_limit"):
            assert scraper._get("https://www.sat.gob.mx/x") is None
        assert "HTTP 504" in caplog.text


# ── Health check: quarterly RMF failures and staleness alert ──────────


@pytest.mark.django_db
class TestScraperHealthAlerts:
    def _log(self, operation, days_ago, error=""):
        from django.utils import timezone

        from apps.scraper.dataops.models import AcquisitionLog

        row = AcquisitionLog.objects.create(operation=operation, error_summary=error)
        AcquisitionLog.objects.filter(pk=row.pk).update(
            started_at=timezone.now() - datetime.timedelta(days=days_ago)
        )

    def test_failed_quarterly_rmf_run_alerts(self, monkeypatch, tmp_path):
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(tasks, "check_row_growth", lambda now: [])
        self._log("rmf_scrape", 33, error="RMF scraper discovered 0 documents")
        # dof_daily_check writes its change summary into error_summary on a
        # healthy run: that must not count as a failure.
        self._log("dof_daily_check", 0, error="2 law changes detected")
        with patch("apps.api.tasks.deliver_operator_alert") as alert:
            result = tasks.check_scraper_health()
        assert result["rmf_scrape"]["last_run_failed"] is True
        assert result["rmf_scrape"]["is_stale"] is False
        assert result["dof_daily_check"]["last_run_failed"] is False
        alert.delay.assert_called_once()
        event, payload = alert.delay.call_args.args
        assert event == "scraper_health.problems"
        assert set(payload["problems"]) == {"rmf_scrape"}

    def test_stale_quarterly_run_alerts(self, monkeypatch, tmp_path):
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(tasks, "check_row_growth", lambda now: [])
        self._log("rmf_scrape", 200)
        with patch("apps.api.tasks.deliver_operator_alert") as alert:
            result = tasks.check_scraper_health()
        assert result["rmf_scrape"]["is_stale"] is True
        alert.delay.assert_called_once()

    def test_healthy_runs_send_no_alert(self, monkeypatch, tmp_path):
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(tasks, "check_row_growth", lambda now: [])
        self._log("rmf_scrape", 10)
        self._log("dof_daily_check", 0)
        with patch("apps.api.tasks.deliver_operator_alert") as alert:
            tasks.check_scraper_health()
        alert.delay.assert_not_called()


# ── Off-cluster SAT check (scripts/check_sat_rmf_compilations.py) ────


def _sat_script():
    spec = importlib.util.spec_from_file_location(
        "check_sat_rmf_compilations", REPO / "scripts" / "check_sat_rmf_compilations.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestSatRmfCheck:
    def test_extracts_resolutions_and_compilations_only(self):
        module = _sat_script()
        links = module.rmf_links(SAT_PAGE.read_text(encoding="utf-8"), 2026)
        names = [link["filename"] for link in links]
        assert "RMF_2026-DOF-28122025.pdf" in names
        assert (
            "Compilado_Tercera_Modificacion_a_la-Resolucion_Miscelanea_Fiscal_para_2026.pdf"
            in names
        )
        assert not any("anexo" in n.lower() or "anticipada" in n.lower() for n in names)
        assert {link["kind"] for link in links} == {"resolucion", "compilada"}

    def test_shipped_manifest_already_knows_every_listed_document(self):
        module = _sat_script()
        manifest = json.loads(
            (REPO / "apps/parsers/rmf/manifests/rmf_2026.json").read_text(
                encoding="utf-8"
            )
        )
        links = module.rmf_links(SAT_PAGE.read_text(encoding="utf-8"), 2026)
        new, report = module.build_report(2026, links, manifest)
        assert new == []
        assert "0 publication(s) not in the manifest" in report

    def test_reports_a_compilation_the_manifest_lacks(self):
        module = _sat_script()
        manifest = json.loads(
            (REPO / "apps/parsers/rmf/manifests/rmf_2026.json").read_text(
                encoding="utf-8"
            )
        )
        manifest["versions"] = manifest["versions"][:-1]  # drop compilada-3a-rm
        links = module.rmf_links(SAT_PAGE.read_text(encoding="utf-8"), 2026)
        new, report = module.build_report(2026, links, manifest)
        assert [n["filename"] for n in new] == [
            "Compilado_Tercera_Modificacion_a_la-Resolucion_Miscelanea_Fiscal_para_2026.pdf"
        ]
        assert "1 publication(s) not in the manifest" in report
        assert "rmf-rule-ingestion.md" in report

    def test_main_writes_github_output_and_fails_without_links(
        self, tmp_path, monkeypatch
    ):
        module = _sat_script()
        output = tmp_path / "out.txt"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output))
        assert module.main(["--year", "2026", "--html", str(SAT_PAGE)]) == 0
        assert output.read_text() == "new_count=0\n"
        empty = tmp_path / "empty.html"
        empty.write_text("<html></html>")
        assert module.main(["--year", "2026", "--html", str(empty)]) == 2
