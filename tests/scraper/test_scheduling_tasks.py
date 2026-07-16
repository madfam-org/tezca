"""
Tests for apps/scraper/scheduling/tasks.py — every Celery beat task.

A+ Item 1 (per docs/strategy/A_PLUS_REMEDIATION_PLAN_2026-04-27.md
Workstream 1 Phase 1A): the 942-LOC tasks module had **0% coverage**
despite running every nightly job. Each task gets at minimum:

* happy path — confirms the scraper/command is wired correctly and the
  AcquisitionLog row is written
* error path — confirms `_finish_log(error=...)` records the failure

Plus dedicated suites for the two helper functions (`_start_log`,
`_finish_log`) and for the subprocess-injection-resistant
``replicate_batch`` that landed in the audit-remediation PR (#43).

**Patching strategy:** the task module uses *lazy imports* — `import
subprocess`, `import requests`, etc. happen inside the `@shared_task`
function body. So we patch at the source module path (`subprocess.run`,
`requests.head`) rather than at `apps.scraper.scheduling.tasks.<name>`.
Same for the scraper classes that are imported lazily — patch at their
source module (`apps.scraper.federal.foo.FooScraper`), which works
because Python re-imports from sys.modules.

All tests use mocked models + mocked subprocess + mocked scrapers — no
network, no DB, no real Celery worker needed.
"""

from unittest.mock import MagicMock, patch

import pytest

# ── Helpers (_start_log / _finish_log) ────────────────────────────────


class TestStartLog:
    @patch("apps.scraper.dataops.models.AcquisitionLog")
    def test_creates_acquisition_log_row(self, mock_log_cls):
        from apps.scraper.scheduling.tasks import _start_log

        mock_log_cls.objects.create.return_value = MagicMock()
        _start_log("test_op", parameters={"foo": "bar"})
        mock_log_cls.objects.create.assert_called_once()
        kwargs = mock_log_cls.objects.create.call_args[1]
        assert kwargs["operation"] == "test_op"
        assert kwargs["parameters"] == {"foo": "bar"}

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    def test_returns_none_on_db_failure(self, mock_log_cls):
        """Must NOT crash a Celery task when AcquisitionLog write fails."""
        from apps.scraper.scheduling.tasks import _start_log

        mock_log_cls.objects.create.side_effect = Exception("db down")
        result = _start_log("test_op")
        assert result is None

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    def test_handles_no_parameters(self, mock_log_cls):
        from apps.scraper.scheduling.tasks import _start_log

        mock_log_cls.objects.create.return_value = MagicMock()
        _start_log("test_op")
        kwargs = mock_log_cls.objects.create.call_args[1]
        assert kwargs["parameters"] == {}


class TestFinishLog:
    def test_no_op_when_log_entry_is_none(self):
        from apps.scraper.scheduling.tasks import _finish_log

        # Should not raise
        _finish_log(None, found=5, downloaded=3)

    def test_writes_counts_to_log_entry(self):
        from apps.scraper.scheduling.tasks import _finish_log

        log = MagicMock()
        _finish_log(log, found=10, downloaded=8, failed=2, ingested=8)
        assert log.found == 10
        assert log.downloaded == 8
        assert log.failed == 2
        assert log.ingested == 8
        log.save.assert_called_once()

    def test_truncates_long_error_to_max_length(self):
        from apps.scraper.scheduling.tasks import MAX_ERROR_LENGTH, _finish_log

        log = MagicMock()
        long_error = "x" * 5000
        _finish_log(log, error=long_error)
        assert len(log.error_summary) == MAX_ERROR_LENGTH

    def test_swallows_save_failure_without_raising(self):
        """Failed log persistence must not break the actual task."""
        from apps.scraper.scheduling.tasks import _finish_log

        log = MagicMock()
        log.save.side_effect = Exception("write conflict")
        _finish_log(log, found=1)  # must not raise


# ── run_health_checks ─────────────────────────────────────────────────


class TestRunHealthChecks:
    @patch("apps.scraper.dataops.health_monitor.HealthMonitor")
    def test_critical_only_passes_flag(self, mock_monitor_cls):
        from apps.scraper.scheduling.tasks import run_health_checks

        monitor = MagicMock()
        monitor.check_all.return_value = []
        monitor.get_summary.return_value = {
            "healthy": 5,
            "degraded": 0,
            "down": 0,
        }
        mock_monitor_cls.return_value = monitor

        run_health_checks(sources="critical")
        monitor.check_all.assert_called_once_with(critical_only=True)

    @patch("apps.scraper.dataops.health_monitor.HealthMonitor")
    def test_all_sources_disables_critical_filter(self, mock_monitor_cls):
        from apps.scraper.scheduling.tasks import run_health_checks

        monitor = MagicMock()
        monitor.check_all.return_value = []
        monitor.get_summary.return_value = {
            "healthy": 0,
            "degraded": 0,
            "down": 0,
        }
        mock_monitor_cls.return_value = monitor

        run_health_checks(sources="all")
        monitor.check_all.assert_called_once_with(critical_only=False)

    @patch("apps.scraper.dataops.health_monitor.HealthMonitor")
    def test_returns_summary(self, mock_monitor_cls):
        from apps.scraper.scheduling.tasks import run_health_checks

        monitor = MagicMock()
        monitor.check_all.return_value = []
        expected = {"healthy": 7, "degraded": 1, "down": 2}
        monitor.get_summary.return_value = expected
        mock_monitor_cls.return_value = monitor

        result = run_health_checks()
        assert result == expected


# ── detect_staleness ──────────────────────────────────────────────────


class TestDetectStaleness:
    @patch("apps.scraper.dataops.health_monitor.HealthMonitor")
    def test_passes_max_age_to_monitor(self, mock_monitor_cls):
        from apps.scraper.scheduling.tasks import detect_staleness

        monitor = MagicMock()
        stale_qs = MagicMock()
        stale_qs.count.return_value = 3
        monitor.detect_staleness.return_value = stale_qs
        mock_monitor_cls.return_value = monitor

        result = detect_staleness(max_age_days=180)
        monitor.detect_staleness.assert_called_once_with(max_age_days=180)
        assert result == {"stale_count": 3, "max_age_days": 180}


# ── generate_coverage_report ──────────────────────────────────────────


class TestGenerateCoverageReport:
    @patch("apps.scraper.dataops.coverage_dashboard.CoverageDashboard")
    def test_returns_summary(self, mock_dashboard_cls):
        from apps.scraper.scheduling.tasks import generate_coverage_report

        dashboard = MagicMock()
        summary = {
            "total_in_db": 100,
            "total_scraped": 80,
            "total_gaps": 20,
            "actionable_gaps": 5,
        }
        dashboard.full_report.return_value = {"summary": summary}
        mock_dashboard_cls.return_value = dashboard

        result = generate_coverage_report()
        assert result == summary


# ── retry_transient_failures ──────────────────────────────────────────


class TestRetryTransientFailures:
    """retry_transient_failures imports `requests` and `GapRecord` lazily,
    so we patch at their canonical module paths."""

    @patch("requests.head")
    @patch("apps.scraper.dataops.models.GapRecord")
    def test_resolves_when_url_responds_ok(self, mock_gap_cls, mock_head):
        from apps.scraper.scheduling.tasks import retry_transient_failures

        gap = MagicMock()
        gap.source_url = "https://example.com"
        gap.attempts = []
        mock_gap_cls.objects.filter.return_value = [gap]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        # bind=True Celery task: invoke via .run() so Celery does the
        # binding, not us
        result = retry_transient_failures.run()
        assert result["resolved"] == 1
        assert result["escalated"] == 0
        assert gap.status == "resolved"

    @patch("requests.head")
    @patch("apps.scraper.dataops.models.GapRecord")
    def test_escalates_when_url_still_dead(self, mock_gap_cls, mock_head):
        from apps.scraper.scheduling.tasks import retry_transient_failures

        gap = MagicMock()
        gap.source_url = "https://example.com"
        gap.attempts = []
        mock_gap_cls.objects.filter.return_value = [gap]

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_head.return_value = mock_response

        result = retry_transient_failures.run()
        assert result["escalated"] == 1
        assert result["resolved"] == 0
        assert gap.current_tier == 1

    @patch("requests.head")
    @patch("apps.scraper.dataops.models.GapRecord")
    def test_per_gap_exception_does_not_break_loop(self, mock_gap_cls, mock_head):
        from apps.scraper.scheduling.tasks import retry_transient_failures

        good_gap = MagicMock()
        good_gap.source_url = "https://good.example.com"
        good_gap.attempts = []
        bad_gap = MagicMock()
        bad_gap.source_url = "https://bad.example.com"
        bad_gap.attempts = []
        mock_gap_cls.objects.filter.return_value = [good_gap, bad_gap]

        # First call OK, second raises
        good_response = MagicMock(status_code=200)
        mock_head.side_effect = [good_response, Exception("timeout")]

        result = retry_transient_failures.run()
        # 1 resolved + 1 errored, neither blocks the other
        assert result["resolved"] == 1
        assert result["errors"] == 1


# ── run_state_scraper ─────────────────────────────────────────────────


class TestRunStateScraper:
    def test_unknown_state_returns_error(self):
        from apps.scraper.scheduling.tasks import run_state_scraper

        result = run_state_scraper("not_a_state")
        assert "error" in result


# ── run_conamer_scraper ───────────────────────────────────────────────


class TestRunConamerScraper:
    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.scraper.federal.conamer_scraper.ConamerScraper")
    def test_invokes_scraper_with_pagination_args(self, mock_scraper_cls, mock_log_cls):
        from apps.scraper.scheduling.tasks import run_conamer_scraper

        scraper = MagicMock()
        scraper.run.return_value = {
            "total_scraped": 50,
            "unique_after_dedup": 45,
        }
        mock_scraper_cls.return_value = scraper

        run_conamer_scraper(max_pages=5, resume_from_page=2)
        scraper.run.assert_called_once_with(
            output_dir="data/conamer", max_pages=5, resume_from_page=2
        )


# ── run_nom_scraper ───────────────────────────────────────────────────


class TestRunNomScraper:
    @patch("apps.scraper.federal.nom_scraper.NomScraper")
    def test_passes_priority_and_max_results(self, mock_scraper_cls):
        from apps.scraper.scheduling.tasks import run_nom_scraper

        scraper = MagicMock()
        scraper.run.return_value = {"total": 100}
        mock_scraper_cls.return_value = scraper

        result = run_nom_scraper(priority_only=False, max_results=200)
        scraper.run.assert_called_once_with(
            output_dir="data/noms", priority_only=False, max_results=200
        )
        assert result["total"] == 100


# ── run_treaty_scraper ────────────────────────────────────────────────


class TestRunTreatyScraper:
    @patch("apps.scraper.federal.treaty_scraper.TreatyScraper")
    def test_passes_fetch_details_flag(self, mock_scraper_cls):
        from apps.scraper.scheduling.tasks import run_treaty_scraper

        scraper = MagicMock()
        scraper.run.return_value = {"total": 1500}
        mock_scraper_cls.return_value = scraper

        run_treaty_scraper(fetch_details=True, max_details=100)
        scraper.run.assert_called_once_with(
            output_dir="data/treaties", fetch_details=True, max_details=100
        )


# ── run_rmf_scraper ───────────────────────────────────────────────────


class TestRunRmfScraper:
    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.scraper.federal.rmf_scraper.RmfScraper")
    def test_uses_current_year_when_year_is_none(self, mock_scraper_cls, mock_log_cls):
        import datetime

        from apps.scraper.scheduling.tasks import run_rmf_scraper

        scraper = MagicMock()
        scraper.run.return_value = {
            "total": 5,
            "by_type": {"rmf": 1, "annex": 4},
            "downloaded": 5,
            "errors": 0,
        }
        mock_scraper_cls.return_value = scraper

        run_rmf_scraper(year=None, include_annexes=True, download_documents=True)
        call_kwargs = scraper.run.call_args[1]
        assert call_kwargs["year"] == datetime.date.today().year

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.scraper.federal.rmf_scraper.RmfScraper")
    def test_passes_year_through(self, mock_scraper_cls, mock_log_cls):
        from apps.scraper.scheduling.tasks import run_rmf_scraper

        scraper = MagicMock()
        scraper.run.return_value = {
            "total": 0,
            "by_type": {},
            "downloaded": 0,
            "errors": 0,
        }
        mock_scraper_cls.return_value = scraper

        run_rmf_scraper(year=2025)
        assert scraper.run.call_args[1]["year"] == 2025

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.scraper.federal.rmf_scraper.RmfScraper")
    def test_records_failure_in_acquisition_log(self, mock_scraper_cls, mock_log_cls):
        from apps.scraper.scheduling.tasks import run_rmf_scraper

        scraper = MagicMock()
        scraper.run.side_effect = Exception("SAT portal blocked us")
        mock_scraper_cls.return_value = scraper

        result = run_rmf_scraper(year=2026)
        assert "error" in result
        assert "SAT" in result["error"]


# ── replicate_batch (subprocess-injection-resistant) ──────────────────


class TestReplicateBatch:
    """The subprocess module is imported lazily inside replicate_batch,
    so we patch at its canonical path."""

    @patch("subprocess.run")
    def test_r2_sync_failure_short_circuits(self, mock_run):
        from apps.scraper.scheduling.tasks import replicate_batch

        mock_run.return_value = MagicMock(returncode=1, stderr="r2 down")
        result = replicate_batch(prefix="state_laws/x/")
        assert result["success"] is False
        assert result["stage"] == "r2_sync"

    @patch("subprocess.run")
    def test_invalid_ingest_command_returns_error(self, mock_run):
        """Track 1 hardening: shlex.split rejects malformed shell input."""
        from apps.scraper.scheduling.tasks import replicate_batch

        # First call (r2 sync) succeeds
        mock_run.return_value = MagicMock(returncode=0)

        # Unclosed quote → shlex.split raises ValueError
        result = replicate_batch(
            prefix="x/", ingest_command='index_laws --tier "federal'
        )
        assert result["success"] is False
        assert result["stage"] == "ingestion"
        assert "Invalid" in result["error"]

    @patch("subprocess.run")
    def test_full_success_path(self, mock_run):
        from apps.scraper.scheduling.tasks import replicate_batch

        mock_run.return_value = MagicMock(returncode=0, stdout="ok")
        result = replicate_batch(
            prefix="state_laws/y/", ingest_command="index_laws --tier state"
        )
        assert result["success"] is True
        # Two subprocess calls: r2 sync + ingest command
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_no_ingest_command_skips_second_subprocess(self, mock_run):
        from apps.scraper.scheduling.tasks import replicate_batch

        mock_run.return_value = MagicMock(returncode=0)
        result = replicate_batch(prefix="x/")
        assert result["success"] is True
        # Only r2 sync was called
        assert mock_run.call_count == 1


# ── run_parser_pipeline ───────────────────────────────────────────────


class TestRunParserPipeline:
    @patch("subprocess.run")
    def test_new_only_appends_flag(self, mock_run):
        from apps.scraper.scheduling.tasks import run_parser_pipeline

        mock_run.return_value = MagicMock(returncode=0, stdout="done")
        run_parser_pipeline(new_only=True)
        cmd = mock_run.call_args[0][0]
        assert "--new-only" in cmd

    @patch("subprocess.run")
    def test_full_corpus_omits_new_only(self, mock_run):
        from apps.scraper.scheduling.tasks import run_parser_pipeline

        mock_run.return_value = MagicMock(returncode=0, stdout="done")
        run_parser_pipeline(new_only=False)
        cmd = mock_run.call_args[0][0]
        assert "--new-only" not in cmd

    @patch("subprocess.run")
    def test_pipeline_failure_returns_error(self, mock_run):
        from apps.scraper.scheduling.tasks import run_parser_pipeline

        mock_run.return_value = MagicMock(returncode=1, stderr="pipeline crashed")
        result = run_parser_pipeline()
        assert result["success"] is False


# ── run_conamer_playwright / scrape_scjn_playwright ───────────────────


try:
    import playwright  # noqa: F401
    import playwright.sync_api as _pw_sync_check

    # If sync_playwright is a MagicMock (shimmed by another test file), treat
    # playwright as not installed for the purposes of these tests.
    _real = callable(getattr(_pw_sync_check, "sync_playwright", None)) and (
        type(_pw_sync_check.sync_playwright).__name__ != "MagicMock"
    )
    HAS_PLAYWRIGHT = _real
except ImportError:
    HAS_PLAYWRIGHT = False


@pytest.mark.skipif(
    not HAS_PLAYWRIGHT,
    reason="playwright package not installed (poetry install -E production)",
)
class TestPlaywrightTasks:
    """Playwright-backed scrapers live in modules that aren't auto-imported
    by their package, so we import them ourselves before patching."""

    def test_conamer_playwright_logs_finished(self):
        # Import first to register the submodule
        import apps.scraper.federal.conamer_playwright  # noqa: F401
        from apps.scraper.scheduling.tasks import run_conamer_playwright

        with patch(
            "apps.scraper.federal.conamer_playwright.ConamerPlaywrightScraper"
        ) as mock_scraper_cls, patch("apps.scraper.dataops.models.AcquisitionLog"):
            scraper = MagicMock()
            scraper.run.return_value = {
                "total_items": 100,
                "total_after_dedup": 90,
            }
            mock_scraper_cls.return_value = scraper

            result = run_conamer_playwright(max_pages=10)
            assert result["total_items"] == 100

    def test_conamer_playwright_records_error(self):
        import apps.scraper.federal.conamer_playwright  # noqa: F401
        from apps.scraper.scheduling.tasks import run_conamer_playwright

        with patch(
            "apps.scraper.federal.conamer_playwright.ConamerPlaywrightScraper"
        ) as mock_scraper_cls, patch("apps.scraper.dataops.models.AcquisitionLog"):
            scraper = MagicMock()
            scraper.run.side_effect = Exception("WAF blocked us")
            mock_scraper_cls.return_value = scraper

            result = run_conamer_playwright()
            assert "error" in result

    def test_scjn_playwright_passes_epoca_and_tipo(self):
        import apps.scraper.judicial.scjn_playwright  # noqa: F401
        from apps.scraper.scheduling.tasks import scrape_scjn_playwright

        with patch(
            "apps.scraper.judicial.scjn_playwright.ScjnPlaywrightScraper"
        ) as mock_scraper_cls, patch("apps.scraper.dataops.models.AcquisitionLog"):
            scraper = MagicMock()
            scraper.run.return_value = {"total_items": 200}
            mock_scraper_cls.return_value = scraper

            scrape_scjn_playwright(max_items=200, epoca=11, tipo="tesis_aislada")
            kwargs = scraper.run.call_args[1]
            assert kwargs["epoca"] == 11
            assert kwargs["tipo"] == "tesis_aislada"
            assert kwargs["max_items"] == 200


# ── run_ojn_recovery / run_wayback_recovery ───────────────────────────


class TestRecoveryTasks:
    @patch("subprocess.run")
    def test_ojn_recovery_passes_args(self, mock_run):
        from apps.scraper.scheduling.tasks import run_ojn_recovery

        mock_run.return_value = MagicMock(returncode=0, stdout="done")
        run_ojn_recovery(paths="abc", scope="non_leg", limit=300)
        cmd = mock_run.call_args[0][0]
        assert "--path" in cmd and "abc" in cmd
        assert "--scope" in cmd and "non_leg" in cmd

    @patch("subprocess.run")
    def test_ojn_recovery_failure_returns_error(self, mock_run):
        from apps.scraper.scheduling.tasks import run_ojn_recovery

        mock_run.return_value = MagicMock(returncode=2, stderr="failed")
        result = run_ojn_recovery()
        assert result["success"] is False

    @patch("subprocess.run")
    def test_wayback_with_no_domains_uses_all(self, mock_run):
        from apps.scraper.scheduling.tasks import run_wayback_recovery

        mock_run.return_value = MagicMock(returncode=0, stdout="ok")
        run_wayback_recovery(domains=None, limit=100)
        cmd = mock_run.call_args[0][0]
        assert "--all" in cmd

    @patch("subprocess.run")
    def test_wayback_with_specific_domains(self, mock_run):
        from apps.scraper.scheduling.tasks import run_wayback_recovery

        mock_run.return_value = MagicMock(returncode=0, stdout="ok")
        run_wayback_recovery(domains=["example.com", "test.gob.mx"])
        cmd = mock_run.call_args[0][0]
        # Use explicit element-equality (not substring-of-the-whole-list)
        # to avoid CodeQL's URL-substring-sanitization false-positive class.
        assert any(arg == "example.com" for arg in cmd)
        assert any(arg == "test.gob.mx" for arg in cmd)


# ── run_dof_historical ────────────────────────────────────────────────


class TestRunDofHistorical:
    @patch("subprocess.run")
    def test_year_takes_precedence_over_range(self, mock_run):
        from apps.scraper.scheduling.tasks import run_dof_historical

        mock_run.return_value = MagicMock(returncode=0, stdout="ok")
        run_dof_historical(mode="noms", year=2024, date_range=None)
        cmd = mock_run.call_args[0][0]
        assert "--year" in cmd and "2024" in cmd

    @patch("subprocess.run")
    def test_range_used_when_year_is_none(self, mock_run):
        from apps.scraper.scheduling.tasks import run_dof_historical

        mock_run.return_value = MagicMock(returncode=0, stdout="ok")
        run_dof_historical(mode="all", year=None, date_range="2020-2023")
        cmd = mock_run.call_args[0][0]
        assert "--range" in cmd and "2020-2023" in cmd


# ── scrape_scjn ───────────────────────────────────────────────────────


class TestScrapeScjn:
    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.scraper.judicial.scjn_scraper.ScjnScraper")
    def test_passes_epoca_and_mode(self, mock_scraper_cls, mock_log_cls):
        from apps.scraper.scheduling.tasks import scrape_scjn

        scraper = MagicMock()
        scraper.run.return_value = {"total_scraped": 1000, "failed": 5}
        mock_scraper_cls.return_value = scraper

        scrape_scjn(max_items=1000, epoca=10, mode="tesis")
        kwargs = scraper.run.call_args[1]
        assert kwargs["epoca"] == 10
        assert kwargs["mode"] == "tesis"
        assert kwargs["max_items"] == 1000

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.scraper.judicial.scjn_scraper.ScjnScraper")
    def test_records_failure(self, mock_scraper_cls, mock_log_cls):
        from apps.scraper.scheduling.tasks import scrape_scjn

        scraper = MagicMock()
        scraper.run.side_effect = Exception("SCJN portal down")
        mock_scraper_cls.return_value = scraper

        result = scrape_scjn()
        assert "error" in result


# ── ingest_judicial_batches ───────────────────────────────────────────


class TestIngestJudicialBatches:
    def test_no_batch_files_short_circuits(self, tmp_path, monkeypatch):
        """When there are no batch files the task no-ops cleanly."""
        from apps.scraper.scheduling import tasks

        # Use cwd manipulation: easier than mocking Path globally
        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_judicial_batches()
        assert result["status"] == "no_files"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_ingest_when_files_present(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        # The Playwright scraper writes into per-type subdirectories, not a
        # flat data/judicial/batches — the task must recurse to find them.
        batch_dir = tmp_path / "data" / "judicial" / "jurisprudencia"
        batch_dir.mkdir(parents=True)
        (batch_dir / "batch_0000.json").write_text("[]")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_judicial_batches()
        assert result["status"] == "completed"
        mock_call_command.assert_called_once()
        # reads from the judicial root, not the nonexistent .../batches
        assert mock_call_command.call_args.kwargs["dir"] == "data/judicial"


# ── ingest_conamer_catalog ────────────────────────────────────────────


class TestIngestConamerCatalog:
    def test_no_catalog_short_circuits(self, tmp_path, monkeypatch):
        """No discovered_conamer.json and no batch files → clean no-op."""
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_conamer_catalog()
        assert result["status"] == "no_files"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_ingest_when_catalog_present(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        conamer_dir = tmp_path / "data" / "conamer"
        conamer_dir.mkdir(parents=True)
        (conamer_dir / "discovered_conamer.json").write_text("[]")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_conamer_catalog()
        assert result["status"] == "completed"
        mock_call_command.assert_called_once_with("ingest_conamer", all=True)

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_ingest_from_batch_files(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        conamer_dir = tmp_path / "data" / "conamer"
        conamer_dir.mkdir(parents=True)
        (conamer_dir / "batch_0000.json").write_text("[]")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_conamer_catalog()
        assert result["status"] == "completed"
        mock_call_command.assert_called_once_with("ingest_conamer", all=True)


# ── ingest_rmf_catalog ────────────────────────────────────────────────


class TestIngestRmfCatalog:
    def test_no_catalog_short_circuits(self, tmp_path, monkeypatch):
        """No data/rmf/catalog.json → clean no-op."""
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_rmf_catalog()
        assert result["status"] == "no_files"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_ingest_when_catalog_present(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        rmf_dir = tmp_path / "data" / "rmf"
        rmf_dir.mkdir(parents=True)
        (rmf_dir / "catalog.json").write_text("{}")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_rmf_catalog()
        assert result["status"] == "completed"
        mock_call_command.assert_called_once_with(
            "ingest_rmf", catalog="data/rmf/catalog.json"
        )

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_error_is_reported_not_raised(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        rmf_dir = tmp_path / "data" / "rmf"
        rmf_dir.mkdir(parents=True)
        (rmf_dir / "catalog.json").write_text("{}")
        mock_call_command.side_effect = RuntimeError("ingest boom")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_rmf_catalog()
        assert result["status"] == "error"
        assert "ingest boom" in result["error"]


# ── ingest_nom_catalog ────────────────────────────────────────────────


class TestIngestNomCatalog:
    def test_no_catalog_short_circuits(self, tmp_path, monkeypatch):
        """No data/noms/discovered_noms.json → clean no-op."""
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_nom_catalog()
        assert result["status"] == "no_files"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_ingest_when_catalog_present(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        noms_dir = tmp_path / "data" / "noms"
        noms_dir.mkdir(parents=True)
        (noms_dir / "discovered_noms.json").write_text("[]")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_nom_catalog()
        assert result["status"] == "completed"
        mock_call_command.assert_called_once_with(
            "ingest_noms", catalog="data/noms/discovered_noms.json"
        )

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_error_is_reported_not_raised(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        noms_dir = tmp_path / "data" / "noms"
        noms_dir.mkdir(parents=True)
        (noms_dir / "discovered_noms.json").write_text("[]")
        mock_call_command.side_effect = RuntimeError("nom boom")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_nom_catalog()
        assert result["status"] == "error"
        assert "nom boom" in result["error"]


# ── ingest_treaty_catalog ─────────────────────────────────────────────


class TestIngestTreatyCatalog:
    def test_no_catalog_short_circuits(self, tmp_path, monkeypatch):
        """No discovered_treaties.json → clean no-op."""
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_treaty_catalog()
        assert result["status"] == "no_files"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_runs_ingest_when_catalog_present(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        treaties_dir = tmp_path / "data" / "treaties"
        treaties_dir.mkdir(parents=True)
        (treaties_dir / "discovered_treaties.json").write_text("[]")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_treaty_catalog()
        assert result["status"] == "completed"
        mock_call_command.assert_called_once_with("ingest_treaties", all=True)

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("django.core.management.call_command")
    def test_error_is_reported_not_raised(
        self, mock_call_command, mock_log_cls, tmp_path, monkeypatch
    ):
        from apps.scraper.scheduling import tasks

        treaties_dir = tmp_path / "data" / "treaties"
        treaties_dir.mkdir(parents=True)
        (treaties_dir / "discovered_treaties.json").write_text("[]")
        mock_call_command.side_effect = RuntimeError("treaty boom")

        monkeypatch.chdir(tmp_path)
        result = tasks.ingest_treaty_catalog()
        assert result["status"] == "error"
        assert "treaty boom" in result["error"]


# ── classify_law_domains_task ─────────────────────────────────────────


class TestClassifyLawDomainsTask:
    @patch("django.core.management.call_command")
    def test_invokes_classify_command_with_all_flag(self, mock_call_command):
        from apps.scraper.scheduling.tasks import classify_law_domains_task

        result = classify_law_domains_task()
        mock_call_command.assert_called_once_with(
            "classify_law_domains", all=True, batch_size=500
        )
        assert result["status"] == "completed"


# ── check_scraper_health ──────────────────────────────────────────────


class TestCheckScraperHealth:
    @patch("apps.scraper.dataops.models.AcquisitionLog")
    def test_handles_no_operations(self, mock_log_cls):
        """No prior runs → empty results dict, no crash."""
        from apps.scraper.scheduling.tasks import check_scraper_health

        # Chained queryset: .values_list().distinct().order_by() → []
        mock_log_cls.objects.values_list.return_value.distinct.return_value.order_by.return_value = (
            []
        )

        result = check_scraper_health()
        assert isinstance(result, dict)

    def test_row_growth_warnings_surface_in_report(self, monkeypatch, tmp_path):
        """The health task's returned report includes row-growth warnings
        under `_row_growth_warnings`, so operators see them without
        digging into logs. Guard internals are covered in
        test_row_growth_guard.py; this just confirms the wiring."""
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)

        with patch("apps.scraper.dataops.models.AcquisitionLog") as mock_log_cls:
            mock_log_cls.objects.values_list.return_value.distinct.return_value.order_by.return_value = (
                []
            )
            monkeypatch.setattr(
                tasks, "check_row_growth", lambda now: ["pipeline fake: flat rows"]
            )
            result = tasks.check_scraper_health()

        assert result["_row_growth_warnings"] == ["pipeline fake: flat rows"]

    def test_report_intact_when_row_growth_guard_yields_no_warnings(
        self, monkeypatch, tmp_path
    ):
        """The row-growth guard is fail-open internally (see
        test_row_growth_guard.py::test_guard_exception_does_not_raise_and_returns_empty).
        This confirms the primary per-operation results are unaffected by
        the guard call — with no DB access allowed here, the guard's real
        implementation naturally hits an exception internally and returns
        [], but `check_scraper_health`'s own report must stay intact."""
        from apps.scraper.scheduling import tasks

        monkeypatch.chdir(tmp_path)

        with patch("apps.scraper.dataops.models.AcquisitionLog") as mock_log_cls:
            mock_log_cls.objects.values_list.return_value.distinct.return_value.order_by.return_value = [
                "some_op"
            ]
            mock_log_cls.objects.filter.return_value.order_by.return_value.first.return_value = (
                None
            )
            mock_log_cls.objects.filter.return_value.filter.return_value.count.return_value = (
                0
            )
            result = tasks.check_scraper_health()

        assert "some_op" in result
        assert result["some_op"]["recent_failures"] == 0
        assert result["_row_growth_warnings"] == []


# ── DOF daily materialization (flag-gated) ────────────────────────────


class TestDofMaterialization:
    def test_metadata_from_change(self):
        from apps.scraper.scheduling.dof_ingest import _dof_change_to_law_metadata

        md = _dof_change_to_law_metadata(
            {
                "title": "LEY de Prueba de Economía",
                "url": "https://dof.gob.mx/nota_detalle.php?codigo=1",
                "change_type": "new_law",
            }
        )
        assert md["id"] == "ley_de_prueba_de_economia"
        assert md["name"] == "LEY de Prueba de Economía"
        assert md["url"] == "https://dof.gob.mx/nota_detalle.php?codigo=1"
        assert md["source"] == "dof_daily"

    def test_materialize_disabled_by_default(self, settings):
        settings.DOF_AUTO_INGEST_ENABLED = False
        from apps.scraper.scheduling.dof_ingest import _materialize_dof_changes

        with patch("apps.parsers.pipeline.IngestionPipeline") as mock_pipeline:
            result = _materialize_dof_changes(
                [{"title": "LEY X", "url": "http://x", "change_type": "new_law"}]
            )
        assert result == (0, 0)
        mock_pipeline.assert_not_called()

    def test_materialize_enabled_ingests_new_and_reform_only(self, settings):
        settings.DOF_AUTO_INGEST_ENABLED = True
        from apps.scraper.scheduling.dof_ingest import _materialize_dof_changes

        changes = [
            {"title": "LEY Nueva", "url": "http://a", "change_type": "new_law"},
            {"title": "Reforma a la LEY Y", "url": "http://b", "change_type": "reform"},
            {
                "title": "Se abroga la LEY Z",
                "url": "http://c",
                "change_type": "abrogation",
            },
            {"title": "Otro aviso", "url": "http://d", "change_type": "other"},
        ]
        with patch("apps.parsers.pipeline.IngestionPipeline") as mock_pipeline_cls:
            instance = mock_pipeline_cls.return_value
            instance.ingest_law.return_value = MagicMock(success=True)
            materialized, failed = _materialize_dof_changes(changes)

        assert materialized == 2  # new_law + reform only
        assert failed == 0
        assert instance.ingest_law.call_count == 2

    def test_materialize_counts_failures(self, settings):
        settings.DOF_AUTO_INGEST_ENABLED = True
        from apps.scraper.scheduling.dof_ingest import _materialize_dof_changes

        changes = [
            {"title": "LEY A", "url": "http://a", "change_type": "new_law"},
            {"title": "LEY B", "url": "http://b", "change_type": "new_law"},
        ]
        with patch("apps.parsers.pipeline.IngestionPipeline") as mock_pipeline_cls:
            instance = mock_pipeline_cls.return_value
            instance.ingest_law.side_effect = [
                MagicMock(success=True),
                Exception("parse boom"),
            ]
            materialized, failed = _materialize_dof_changes(changes)

        assert materialized == 1
        assert failed == 1

    def test_materialize_skips_changes_without_url(self, settings):
        settings.DOF_AUTO_INGEST_ENABLED = True
        from apps.scraper.scheduling.dof_ingest import _materialize_dof_changes

        changes = [{"title": "LEY no URL", "url": "", "change_type": "new_law"}]
        with patch("apps.parsers.pipeline.IngestionPipeline") as mock_pipeline_cls:
            instance = mock_pipeline_cls.return_value
            materialized, failed = _materialize_dof_changes(changes)

        assert (materialized, failed) == (0, 0)
        instance.ingest_law.assert_not_called()
