"""
Tests for the DataOps module: models, gap registry, health monitor,
coverage dashboard, and source discovery.
"""

import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.scraper.dataops.models import AcquisitionLog, DataSource, GapRecord

# ── DataSource Model Tests ────────────────────────────────────────────


@pytest.mark.django_db
class TestDataSourceModel:
    def test_create_source(self):
        source = DataSource.objects.create(
            name="Test Source",
            source_type="scraper",
            level="federal",
            base_url="https://example.com",
        )
        assert source.id is not None
        assert source.status == "unknown"
        assert source.last_check is None

    def test_mark_healthy(self):
        source = DataSource.objects.create(
            name="Healthy Source",
            source_type="scraper",
            level="state",
        )
        source.mark_healthy(response_time_ms=250)
        source.refresh_from_db()
        assert source.status == "healthy"
        assert source.response_time_ms == 250
        assert source.last_check is not None
        assert source.last_success is not None

    def test_mark_degraded(self):
        source = DataSource.objects.create(
            name="Slow Source",
            source_type="api",
            level="federal",
        )
        source.mark_degraded(response_time_ms=15000)
        source.refresh_from_db()
        assert source.status == "degraded"
        assert source.response_time_ms == 15000
        assert source.last_check is not None

    def test_mark_down(self):
        source = DataSource.objects.create(
            name="Dead Source",
            source_type="scraper",
            level="state",
        )
        source.mark_down()
        source.refresh_from_db()
        assert source.status == "down"
        assert source.last_check is not None

    def test_str_representation(self):
        source = DataSource(name="OJN", state="Jalisco")
        assert str(source) == "OJN (Jalisco)"
        source2 = DataSource(name="Diputados")
        assert str(source2) == "Diputados"


# ── GapRecord Model Tests ────────────────────────────────────────────


@pytest.mark.django_db
class TestGapRecordModel:
    def test_create_gap(self):
        gap = GapRecord.objects.create(
            level="state",
            state="Michoacán",
            gap_type="dead_link",
            description="504 dead links",
            priority=2,
        )
        assert gap.id is not None
        assert gap.status == "open"
        assert gap.current_tier == 0
        assert gap.attempts == []

    def test_escalate(self):
        gap = GapRecord.objects.create(
            level="state",
            state="Test",
            gap_type="dead_link",
        )
        gap.escalate("Tried alt source", "not found")
        gap.refresh_from_db()
        assert gap.current_tier == 1
        assert gap.status == "in_progress"
        assert len(gap.attempts) == 1
        assert gap.attempts[0]["action"] == "Tried alt source"

    def test_escalate_max_tier(self):
        gap = GapRecord.objects.create(
            level="state",
            state="Test",
            gap_type="dead_link",
            current_tier=4,
        )
        gap.escalate("Final attempt", "failed")
        gap.refresh_from_db()
        assert gap.current_tier == 4  # stays at 4
        assert gap.status == "blocked"

    def test_resolve(self):
        gap = GapRecord.objects.create(
            level="state",
            state="Test",
            gap_type="dead_link",
            current_tier=1,
        )
        gap.resolve(via="Wayback Machine", url="https://web.archive.org/example")
        gap.refresh_from_db()
        assert gap.status == "resolved"
        assert gap.resolved_via == "Wayback Machine"
        assert gap.resolved_url == "https://web.archive.org/example"
        assert gap.resolved_at is not None

    def test_mark_permanent(self):
        gap = GapRecord.objects.create(
            level="state",
            state="Test",
            gap_type="dead_link",
        )
        gap.mark_permanent("OJN confirmed removal")
        gap.refresh_from_db()
        assert gap.status == "permanent"
        assert len(gap.attempts) == 1

    def test_str_representation(self):
        gap = GapRecord(
            law_name="Ley de Amparo",
            status="open",
            current_tier=1,
        )
        assert "Ley de Amparo" in str(gap)
        assert "Tier 1" in str(gap)


# ── AcquisitionLog Model Tests ───────────────────────────────────────


@pytest.mark.django_db
class TestAcquisitionLogModel:
    def test_create_log(self):
        log = AcquisitionLog.objects.create(
            operation="scrape_state_laws",
            found=100,
            downloaded=95,
            failed=5,
        )
        assert log.id is not None
        assert log.started_at is not None
        assert log.finished_at is None

    def test_finish(self):
        log = AcquisitionLog.objects.create(
            operation="test_op",
            found=10,
            downloaded=8,
            failed=2,
        )
        log.finish(error_summary="2 timeout errors")
        log.refresh_from_db()
        assert log.finished_at is not None
        assert log.error_summary == "2 timeout errors"

    def test_success_rate(self):
        log = AcquisitionLog(found=100, downloaded=90, failed=10)
        assert log.success_rate == 80.0

    def test_success_rate_zero(self):
        log = AcquisitionLog(found=0, downloaded=0, failed=0)
        assert log.success_rate is None


# ── Gap Registry Tests ────────────────────────────────────────────────


@pytest.mark.django_db
class TestGapRegistryBootstrap:
    def _create_ojn_source(self):
        return DataSource.objects.create(
            name="OJN Compilacion (State Laws)",
            source_type="scraper",
            level="state",
        )

    def test_import_from_gap_report(self, tmp_path):
        from apps.scraper.dataops.gap_registry import GapRegistry

        self._create_ojn_source()

        gap_report = {
            "timestamp": "2026-02-05T18:30:51",
            "states": [
                {
                    "state_name": "Michoacán",
                    "recovered": 0,
                    "still_failed": 504,
                    "permanent": 504,
                    "transient": 0,
                },
                {
                    "state_name": "Querétaro",
                    "recovered": 0,
                    "still_failed": 10,
                    "permanent": 9,
                    "transient": 1,
                },
            ],
            "total_permanent": 513,
            "total_transient": 1,
        }
        path = tmp_path / "gap_report.json"
        path.write_text(json.dumps(gap_report))

        registry = GapRegistry()
        created = registry.import_from_gap_report(path)
        # Michoacán permanent + Querétaro permanent + Querétaro transient
        assert created == 3
        assert GapRecord.objects.filter(status="permanent").count() == 2
        assert GapRecord.objects.filter(status="open").count() == 1

    def test_import_from_gap_report_missing_file(self, tmp_path):
        from apps.scraper.dataops.gap_registry import GapRegistry

        registry = GapRegistry()
        result = registry.import_from_gap_report(tmp_path / "nonexistent.json")
        assert result == 0

    def test_import_from_ojn_probe(self, tmp_path):
        from apps.scraper.dataops.gap_registry import GapRegistry

        self._create_ojn_source()

        probe_data = {
            "probe_date": "2026-02-05T18:26:47",
            "states_probed": 2,
            "total_new_laws_found": 335,
            "per_state": [
                {
                    "state_id": 1,
                    "state_name": "Aguascalientes",
                    "existing_estatal": 127,
                    "total_across_powers": 394,
                    "per_power": {"1": 247, "2": 127, "3": 4, "4": 16},
                    "new_from_other_powers": 267,
                },
                {
                    "state_id": 2,
                    "state_name": "Baja California",
                    "existing_estatal": 1,
                    "total_across_powers": 69,
                    "per_power": {"1": 21, "2": 3, "3": 0, "4": 45},
                    "new_from_other_powers": 68,
                },
            ],
        }
        path = tmp_path / "ojn_probe.json"
        path.write_text(json.dumps(probe_data))

        registry = GapRegistry()
        created = registry.import_from_ojn_probe(path)
        assert created == 2
        assert GapRecord.objects.filter(gap_type="not_scraped").count() == 2

    def test_import_low_count_states(self):
        from apps.scraper.dataops.gap_registry import GapRegistry

        registry = GapRegistry()
        created = registry.import_low_count_states()
        assert created == 4  # Durango, QR, BC, Hidalgo
        assert GapRecord.objects.filter(gap_type="low_count").count() == 4

    def test_import_missing_sources(self):
        from apps.scraper.dataops.gap_registry import GapRegistry

        registry = GapRegistry()
        created = registry.import_missing_sources()
        assert created == 7
        assert GapRecord.objects.filter(gap_type="missing_source").count() >= 5

    def test_idempotent_imports(self, tmp_path):
        """Running import twice should not create duplicates."""
        from apps.scraper.dataops.gap_registry import GapRegistry

        self._create_ojn_source()

        gap_report = {
            "states": [
                {
                    "state_name": "Test",
                    "permanent": 10,
                    "transient": 0,
                },
            ],
        }
        path = tmp_path / "gap_report.json"
        path.write_text(json.dumps(gap_report))

        registry = GapRegistry()
        first = registry.import_from_gap_report(path)
        second = registry.import_from_gap_report(path)
        assert first == 1
        assert second == 0

    def test_register_gap(self):
        from apps.scraper.dataops.gap_registry import GapRegistry

        registry = GapRegistry()
        gap = registry.register_gap(
            level="federal",
            gap_type="missing_source",
            description="Test gap",
            priority=1,
        )
        assert gap.id is not None

    def test_get_actionable_gaps(self):
        from apps.scraper.dataops.gap_registry import GapRegistry

        GapRecord.objects.create(level="state", gap_type="dead_link", status="open")
        GapRecord.objects.create(level="state", gap_type="dead_link", status="resolved")
        GapRecord.objects.create(
            level="federal", gap_type="missing_source", status="in_progress"
        )

        registry = GapRegistry()
        actionable = registry.get_actionable_gaps()
        assert actionable.count() == 2

        state_only = registry.get_actionable_gaps(level="state")
        assert state_only.count() == 1

    def test_get_dashboard_stats(self):
        from apps.scraper.dataops.gap_registry import GapRegistry

        GapRecord.objects.create(
            level="state",
            gap_type="dead_link",
            status="open",
            current_tier=0,
        )
        GapRecord.objects.create(
            level="federal",
            gap_type="missing_source",
            status="permanent",
            current_tier=2,
        )

        registry = GapRegistry()
        stats = registry.get_dashboard_stats()
        assert stats["total"] == 2
        assert stats["actionable"] == 1
        assert "open" in stats["by_status"]
        assert "state" in stats["by_level"]


# ── Health Monitor Tests ──────────────────────────────────────────────


@pytest.mark.django_db
class TestHealthMonitor:
    def test_check_source_healthy(self):
        from apps.scraper.dataops.health_monitor import HealthMonitor

        source = DataSource.objects.create(
            name="Test Source",
            source_type="scraper",
            level="federal",
            base_url="https://example.com",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "some content"

        with patch("apps.scraper.dataops.health_monitor.requests.get") as mock_get:
            mock_get.return_value = mock_response
            monitor = HealthMonitor()
            result = monitor.check_source(source)

        assert result.status == "healthy"
        source.refresh_from_db()
        assert source.status == "healthy"

    def test_check_source_down(self):
        from apps.scraper.dataops.health_monitor import HealthMonitor

        source = DataSource.objects.create(
            name="Dead Source",
            source_type="scraper",
            level="federal",
            base_url="https://example.com",
        )

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = ""

        with patch("apps.scraper.dataops.health_monitor.requests.get") as mock_get:
            mock_get.return_value = mock_response
            monitor = HealthMonitor()
            result = monitor.check_source(source)

        assert result.status == "down"
        source.refresh_from_db()
        assert source.status == "down"

    def test_check_source_timeout(self):
        import requests as req

        from apps.scraper.dataops.health_monitor import HealthMonitor

        source = DataSource.objects.create(
            name="Timeout Source",
            source_type="scraper",
            level="state",
            base_url="https://example.com",
        )

        with patch("apps.scraper.dataops.health_monitor.requests.get") as mock_get:
            mock_get.side_effect = req.Timeout("timed out")
            monitor = HealthMonitor()
            result = monitor.check_source(source)

        assert result.status == "down"
        assert "Timeout" in result.message

    def test_check_source_degraded_missing_text(self):
        from apps.scraper.dataops.health_monitor import PROBE_CONFIGS, HealthMonitor

        source = DataSource.objects.create(
            name="OJN Compilacion",
            source_type="scraper",
            level="state",
            base_url="https://compilacion.ordenjuridico.gob.mx/",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>No relevant content</html>"

        with patch("apps.scraper.dataops.health_monitor.requests.get") as mock_get:
            mock_get.return_value = mock_response
            monitor = HealthMonitor()
            result = monitor.check_source(source)

        assert result.status == "degraded"

    def test_check_source_not_found(self):
        from apps.scraper.dataops.health_monitor import HealthMonitor

        monitor = HealthMonitor()
        result = monitor.check_source("Nonexistent Source")
        assert result.status == "down"
        assert "not found" in result.message

    def test_check_all(self):
        from apps.scraper.dataops.health_monitor import HealthMonitor

        DataSource.objects.create(
            name="Source A",
            source_type="scraper",
            level="federal",
            base_url="https://a.example.com",
        )
        DataSource.objects.create(
            name="Source B",
            source_type="scraper",
            level="state",
            base_url="https://b.example.com",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "content"

        with patch("apps.scraper.dataops.health_monitor.requests.get") as mock_get:
            mock_get.return_value = mock_response
            monitor = HealthMonitor()
            results = monitor.check_all()

        assert len(results) == 2

    def test_get_summary(self):
        from apps.scraper.dataops.health_monitor import HealthMonitor

        DataSource.objects.create(
            name="H", source_type="scraper", level="federal", status="healthy"
        )
        DataSource.objects.create(
            name="D", source_type="scraper", level="state", status="down"
        )

        monitor = HealthMonitor()
        summary = monitor.get_summary()
        assert summary["total_sources"] == 2
        assert summary["healthy"] == 1
        assert summary["down"] == 1


# ── Coverage Dashboard Tests ─────────────────────────────────────────


@pytest.mark.django_db
class TestCoverageDashboard:
    def test_federal_coverage(self):
        from apps.api.models import Law
        from apps.scraper.dataops.coverage_dashboard import CoverageDashboard

        Law.objects.create(
            official_id="cpeum",
            name="Constitución",
            tier="federal",
        )

        dashboard = CoverageDashboard()
        result = dashboard.federal_coverage()
        assert result["laws_in_db"] == 1
        assert "reglamentos" in result["gaps"]

    def test_state_coverage(self):
        from apps.api.models import Law
        from apps.scraper.dataops.coverage_dashboard import CoverageDashboard

        Law.objects.create(
            official_id="jal-001",
            name="Test Jalisco",
            tier="state",
            state="Jalisco",
        )
        Law.objects.create(
            official_id="jal-002",
            name="Test Jalisco 2",
            tier="state",
            state="Jalisco",
        )

        dashboard = CoverageDashboard()
        result = dashboard.state_coverage()
        assert result["total_in_db"] == 2

    def test_municipal_coverage(self):
        from apps.api.models import Law
        from apps.scraper.dataops.coverage_dashboard import CoverageDashboard

        Law.objects.create(
            official_id="gdl-001",
            name="Test Guadalajara",
            tier="municipal",
            municipality="Guadalajara",
        )

        dashboard = CoverageDashboard()
        result = dashboard.municipal_coverage()
        assert result["total_in_db"] == 1

    def test_full_report(self):
        from apps.scraper.dataops.coverage_dashboard import CoverageDashboard

        dashboard = CoverageDashboard()
        report = dashboard.full_report()
        assert "summary" in report
        assert "federal" in report
        assert "state" in report
        assert "municipal" in report
        assert "gaps" in report
        assert "total_in_db" in report["summary"]


# ── Source Discovery Tests ────────────────────────────────────────────


class TestSourceDiscovery:
    def test_slugify_state(self):
        from apps.scraper.dataops.source_discovery import _slugify_state

        assert _slugify_state("Jalisco") == "jalisco"
        assert _slugify_state("Nuevo León") == "nuevoleon"
        assert _slugify_state("Ciudad de México") == "ciudadmexico"
        assert _slugify_state("San Luis Potosí") == "sanluispotosi"

    def test_search_state_alternatives(self):
        from apps.scraper.dataops.source_discovery import SourceDiscoverer

        discoverer = SourceDiscoverer()

        with patch.object(discoverer, "_probe_url", return_value=True):
            results = discoverer.search_state_alternatives("Jalisco")

        assert len(results) > 0
        assert any(r["type"] == "congress_portal" for r in results)

    def test_check_wayback_found(self):
        from apps.scraper.dataops.source_discovery import SourceDiscoverer

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "archived_snapshots": {
                "closest": {
                    "available": True,
                    "url": "https://web.archive.org/web/20250101/https://example.com",
                    "timestamp": "20250101120000",
                    "status": "200",
                }
            }
        }

        with patch("apps.scraper.dataops.source_discovery.requests.get") as mock_get:
            mock_get.return_value = mock_response
            discoverer = SourceDiscoverer()
            result = discoverer.check_wayback("https://example.com")

        assert result is not None
        assert "archive_url" in result

    def test_check_wayback_not_found(self):
        from apps.scraper.dataops.source_discovery import SourceDiscoverer

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"archived_snapshots": {}}

        with patch("apps.scraper.dataops.source_discovery.requests.get") as mock_get:
            mock_get.return_value = mock_response
            discoverer = SourceDiscoverer()
            result = discoverer.check_wayback("https://example.com")

        assert result is None

    def test_validate_discovered_source(self):
        from apps.scraper.dataops.source_discovery import SourceDiscoverer

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_response.text = '<a href="ley.pdf">Ley de Test</a> legislación vigente'

        with patch("apps.scraper.dataops.source_discovery.requests.get") as mock_get:
            mock_get.return_value = mock_response
            discoverer = SourceDiscoverer()
            result = discoverer.validate_discovered_source("https://example.com")

        assert result["accessible"] is True
        assert result["has_pdf_links"] is True
        assert result["has_law_keywords"] is True

    def test_validate_discovered_source_inaccessible(self):
        import requests as req

        from apps.scraper.dataops.source_discovery import SourceDiscoverer

        with patch("apps.scraper.dataops.source_discovery.requests.get") as mock_get:
            mock_get.side_effect = req.ConnectionError("refused")
            discoverer = SourceDiscoverer()
            result = discoverer.validate_discovered_source("https://dead.example.com")

        assert result["accessible"] is False

    def test_probe_url(self):
        from apps.scraper.dataops.source_discovery import SourceDiscoverer

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("apps.scraper.dataops.source_discovery.requests.head") as mock_head:
            mock_head.return_value = mock_response
            discoverer = SourceDiscoverer()
            assert discoverer._probe_url("https://example.com") is True

    def test_probe_url_failure(self):
        import requests as req

        from apps.scraper.dataops.source_discovery import SourceDiscoverer

        with patch("apps.scraper.dataops.source_discovery.requests.head") as mock_head:
            mock_head.side_effect = req.ConnectionError("refused")
            discoverer = SourceDiscoverer()
            assert discoverer._probe_url("https://dead.example.com") is False
