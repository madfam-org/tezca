from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from elasticsearch.exceptions import ConnectionError as ESConnectionError
from rest_framework.test import APIClient

from apps.api.middleware.janua_auth import JanuaUser
from apps.api.models import Law

# Shared admin user for test auth bypass
_ADMIN_CLAIMS = {"sub": "test-admin", "email": "admin@test.com", "role": "admin"}


def _start_admin_patches(test_instance):
    """Bypass JanuaJWT auth + IsTezcaAdmin for admin view tests."""
    admin_user = JanuaUser(_ADMIN_CLAIMS)
    admin_user.tier = "madfam"
    admin_user.scopes = ["read", "search"]
    admin_user.allowed_domains = []
    admin_user.api_key_prefix = ""

    test_instance._auth_patcher = patch(
        "apps.api.middleware.janua_auth.JanuaJWTAuthentication.authenticate",
        return_value=(admin_user, "fake-token"),
    )
    test_instance._admin_patcher = patch(
        "apps.api.middleware.admin_permission.IsTezcaAdmin.has_permission",
        return_value=True,
    )
    test_instance._auth_patcher.start()
    test_instance._admin_patcher.start()


def _stop_admin_patches(test_instance):
    test_instance._admin_patcher.stop()
    test_instance._auth_patcher.stop()


@pytest.mark.django_db
class TestAdminViews:
    def setup_method(self):
        self.client = APIClient()
        _start_admin_patches(self)

        # Create some test data for metrics
        Law.objects.create(
            official_id="law-1", name="Federal Law", tier="federal", category="ley"
        )
        Law.objects.create(
            official_id="law-2", name="State Law", tier="state", category="codigo"
        )
        Law.objects.create(
            official_id="law-3",
            name="Muni Law",
            tier="municipal",
            category="reglamento",
        )

    def teardown_method(self):
        _stop_admin_patches(self)

    def test_health_check(self):
        """Test health check endpoint returns 200 and healthy status."""
        url = reverse("admin-health")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["services"]["database"] == "connected"
        assert "timestamp" in data

    def test_system_metrics(self):
        """Test metrics aggregation."""
        url = reverse("admin-metrics")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert data["total_laws"] == 3
        # Check tier counts (tier 0=federal, 1=state, 2=municipal)
        assert data["counts"]["federal"] == 1
        assert data["counts"]["state"] == 1
        assert data["counts"]["municipal"] == 1

        assert "top_categories" in data
        assert "quality_distribution" in data

    @patch("apps.api.ingestion_manager.IngestionManager.get_status")
    def test_job_status(self, mock_get_status):
        """Test job status endpoint."""
        # Mock running status
        mock_get_status.return_value = {
            "status": "running",
            "message": "Ingesting...",
            "progress": 50,
            "timestamp": "2024-01-01T12:00:00",
        }

        url = reverse("admin-job-status")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["progress"] == 50

    @patch("apps.api.ingestion_manager.IngestionManager.get_status")
    def test_list_jobs(self, mock_get_status):
        """Test job list endpoint."""
        mock_get_status.return_value = {"status": "idle"}

        url = reverse("admin-jobs-list")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["status"] == "idle"

    @patch("apps.api.admin_views.es_client")
    @patch("apps.api.admin_views.connection")
    def test_system_config(self, mock_connection, mock_es):
        """Test GET /admin/config/ returns all config sections."""
        # Mock database connection check
        mock_connection.ensure_connection.return_value = None

        # Mock Elasticsearch ping success
        mock_es.ping.return_value = True

        url = reverse("admin-config")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()

        # Verify all four top-level sections exist
        assert "environment" in data
        assert "database" in data
        assert "elasticsearch" in data
        assert "data" in data

        # Verify environment section structure
        assert "debug" in data["environment"]
        assert "allowed_hosts" in data["environment"]
        assert "language" in data["environment"]
        assert "timezone" in data["environment"]

        # Verify database section
        assert "engine" in data["database"]
        assert data["database"]["status"] == "connected"
        assert "name" in data["database"]

        # Verify elasticsearch section
        assert data["elasticsearch"]["status"] == "connected"
        assert "host" in data["elasticsearch"]

        # Verify data section
        assert data["data"]["total_laws"] == 3
        assert data["data"]["total_versions"] == 0
        assert data["data"]["latest_publication"] is None

        # Verify mocks were called
        mock_connection.ensure_connection.assert_called_once()
        mock_es.ping.assert_called_once()

    @patch("apps.api.admin_views.es_client")
    @patch("apps.api.admin_views.connection")
    def test_system_config_es_unavailable(self, mock_connection, mock_es):
        """Test /admin/config/ when Elasticsearch raises an exception."""
        # Mock database connection check (succeeds)
        mock_connection.ensure_connection.return_value = None

        # Mock Elasticsearch ping to raise a connection error
        mock_es.ping.side_effect = ESConnectionError("Connection refused")

        url = reverse("admin-config")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()

        # ES should report unavailable when an exception is raised
        assert data["elasticsearch"]["status"] == "unavailable"

        # Other sections should still be present and correct
        assert data["database"]["status"] == "connected"
        assert "environment" in data
        assert "data" in data

    @patch("apps.scraper.dataops.coverage_dashboard.CoverageDashboard")
    def test_coverage_summary_returns_200(self, mock_class):
        """Test GET /admin/coverage/ returns 200."""
        mock_instance = mock_class.return_value
        mock_instance.full_report.return_value = {
            "summary": {
                "total_in_db": 10,
                "total_scraped": 20,
                "total_gaps": 5,
                "actionable_gaps": 2,
            },
            "federal": {"laws_in_db": 5, "laws_scraped": 10},
            "state": {"total_in_db": 3, "total_scraped": 8, "total_permanent_gaps": 1},
            "municipal": {"total_in_db": 2, "total_scraped": 2, "cities_covered": 1},
            "gaps": {
                "total": 5,
                "open": 2,
                "in_progress": 1,
                "resolved": 1,
                "permanent": 1,
            },
        }

        url = reverse("admin-coverage")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert data["summary"]["total_in_db"] == 10

    @patch("apps.scraper.dataops.health_monitor.HealthMonitor")
    def test_health_sources_returns_200(self, mock_class):
        """Test GET /admin/health-sources/ returns 200."""
        mock_instance = mock_class.return_value
        mock_instance.get_summary.return_value = {
            "total_sources": 10,
            "healthy": 7,
            "degraded": 2,
            "down": 1,
            "unknown": 0,
            "never_checked": 0,
        }

        url = reverse("admin-health-sources")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["total_sources"] == 10
        assert data["healthy"] == 7

    @patch("apps.scraper.dataops.gap_registry.GapRegistry")
    def test_gap_records_returns_200(self, mock_class):
        """Test GET /admin/gaps/ returns 200."""
        mock_instance = mock_class.return_value
        mock_instance.get_dashboard_stats.return_value = {
            "total": 53,
            "by_status": {"open": 40, "resolved": 10, "permanent": 3},
            "by_tier": {},
            "by_level": {},
            "by_type": {},
            "actionable": 30,
            "overdue": 5,
        }

        url = reverse("admin-gaps")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 53
        assert data["actionable"] == 30

    @patch("apps.scraper.dataops.coverage_dashboard.CoverageDashboard")
    def test_coverage_dashboard_returns_200(self, mock_class):
        """Test GET /admin/coverage/dashboard/ returns full dashboard report."""
        mock_instance = mock_class.return_value
        mock_instance.dashboard_report.return_value = {
            "generated_at": "2026-02-06T00:00:00Z",
            "tier_progress": [
                {
                    "key": "federal",
                    "label": "Federal",
                    "known_universe": 336,
                    "scraped": 333,
                    "in_db": 333,
                    "permanent_gaps": 0,
                    "coverage_pct": 99.1,
                    "confidence": "high",
                    "source_name": "Diputados",
                    "source_url": "https://example.com",
                }
            ],
            "coverage_views": {
                "leyes_vigentes": {
                    "label": "Leyes Vigentes",
                    "universe": 12456,
                    "captured": 11699,
                    "pct": 93.9,
                }
            },
            "state_coverage": [],
            "gap_summary": {"total": 53, "actionable": 30, "overdue": 5},
            "expansion_priorities": [],
            "health_status": {"summary": {}, "sources": []},
        }

        url = reverse("admin-coverage-dashboard")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "tier_progress" in data
        assert "coverage_views" in data
        assert "state_coverage" in data
        assert "gap_summary" in data
        assert "expansion_priorities" in data
        assert "health_status" in data
        assert data["tier_progress"][0]["key"] == "federal"


@pytest.mark.django_db
class TestRoadmapEndpoint:
    def setup_method(self):
        self.client = APIClient()
        _start_admin_patches(self)

    def teardown_method(self):
        _stop_admin_patches(self)

    def test_roadmap_get_empty(self):
        """Test GET /admin/roadmap/ with no items."""
        from apps.scraper.dataops.models import RoadmapItem

        RoadmapItem.objects.all().delete()

        url = reverse("admin-roadmap")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "phases" in data
        assert data["summary"]["total_items"] == 0
        assert data["phases"] == []

    def test_roadmap_get_with_items(self):
        """Test GET /admin/roadmap/ returns seeded roadmap items."""
        from apps.scraper.dataops.models import RoadmapItem

        RoadmapItem.objects.all().delete()
        RoadmapItem.objects.create(
            phase=1,
            title="Test item 1",
            category="fix",
            estimated_laws=100,
            sort_order=1,
        )
        RoadmapItem.objects.create(
            phase=2,
            title="Test item 2",
            category="scraper",
            estimated_laws=500,
            sort_order=1,
        )

        url = reverse("admin-roadmap")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_items"] == 2
        assert data["summary"]["total_estimated_laws"] == 600
        assert len(data["phases"]) == 2
        assert data["phases"][0]["phase"] == 1
        assert data["phases"][0]["items"][0]["title"] == "Test item 1"

    def test_roadmap_patch_status(self):
        """Test PATCH /admin/roadmap/ updates item status."""
        from apps.scraper.dataops.models import RoadmapItem

        RoadmapItem.objects.all().delete()
        item = RoadmapItem.objects.create(
            phase=1,
            title="Patchable item",
            category="fix",
            sort_order=1,
        )

        url = reverse("admin-roadmap")
        response = self.client.patch(
            url,
            {"id": item.id, "status": "in_progress"},
            format="json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["status"] == "in_progress"

        item.refresh_from_db()
        assert item.status == "in_progress"
        assert item.started_at is not None

    def test_roadmap_patch_completed(self):
        """Test PATCH completed sets progress to 100 and completed_at."""
        from apps.scraper.dataops.models import RoadmapItem

        RoadmapItem.objects.all().delete()
        item = RoadmapItem.objects.create(
            phase=1,
            title="Completable",
            category="fix",
            sort_order=1,
        )

        url = reverse("admin-roadmap")
        response = self.client.patch(
            url,
            {"id": item.id, "status": "completed"},
            format="json",
        )

        assert response.status_code == 200
        item.refresh_from_db()
        assert item.status == "completed"
        assert item.progress_pct == 100
        assert item.completed_at is not None

    def test_roadmap_patch_invalid_id(self):
        """Test PATCH with non-existent id returns 404."""
        url = reverse("admin-roadmap")
        response = self.client.patch(
            url, {"id": 99999, "status": "blocked"}, format="json"
        )
        assert response.status_code == 404

    def test_roadmap_patch_missing_id(self):
        """Test PATCH without id returns 400."""
        url = reverse("admin-roadmap")
        response = self.client.patch(url, {"status": "blocked"}, format="json")
        assert response.status_code == 400

    def test_roadmap_patch_invalid_status(self):
        """Test PATCH with invalid status returns 400."""
        from apps.scraper.dataops.models import RoadmapItem

        RoadmapItem.objects.all().delete()
        item = RoadmapItem.objects.create(
            phase=1, title="Invalid status test", category="fix", sort_order=1
        )

        url = reverse("admin-roadmap")
        response = self.client.patch(
            url, {"id": item.id, "status": "nonexistent"}, format="json"
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestTaskHealthEndpoint:
    def setup_method(self):
        self.client = APIClient()
        _start_admin_patches(self)

    def teardown_method(self):
        _stop_admin_patches(self)

    def test_task_health_returns_200(self):
        """Test GET /admin/task-health/ returns 200 with task list."""
        url = reverse("admin-task-health")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "never_run" in data
        assert "checked_at" in data

    def test_task_health_stale_detection(self):
        """Test tasks with old AcquisitionLog entries are flagged as stale."""
        from datetime import timedelta

        from django.utils import timezone

        from apps.scraper.dataops.models import AcquisitionLog

        # Create a log entry, then backdate it (started_at is auto_now_add)
        old_time = timezone.now() - timedelta(days=30)
        log = AcquisitionLog.objects.create(
            operation="dof_daily_check",
            finished_at=old_time + timedelta(minutes=5),
            found=10,
            downloaded=0,
            failed=0,
            ingested=0,
        )
        AcquisitionLog.objects.filter(pk=log.pk).update(started_at=old_time)

        url = reverse("admin-task-health")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        dof_tasks = [t for t in data["tasks"] if t["operation"] == "dof_daily_check"]
        assert len(dof_tasks) == 1
        assert dof_tasks[0]["is_stale"] is True

    def test_task_health_never_run(self):
        """Tasks with no AcquisitionLog entries appear in never_run list."""
        url = reverse("admin-task-health")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        # Known tasks in _TASK_EXPECTED_INTERVALS with no logs should appear
        never_run_ops = [t["operation"] for t in data["never_run"]]
        assert "dof_daily_check" in never_run_ops
        for item in data["never_run"]:
            assert item["run_count"] == 0
            assert item["is_stale"] is True

    def test_list_jobs_field_names(self):
        """Verify list_jobs uses correct AcquisitionLog field names."""
        from django.utils import timezone

        from apps.scraper.dataops.models import AcquisitionLog

        now = timezone.now()
        AcquisitionLog.objects.create(
            operation="test_op",
            started_at=now,
            finished_at=now,
            found=5,
            downloaded=3,
            failed=2,
            ingested=0,
        )

        url = reverse("admin-jobs-list")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        jobs = data["jobs"]
        assert len(jobs) >= 1
        job = next(j for j in jobs if j["operation"] == "test_op")
        assert job["found"] == 5
        assert job["downloaded"] == 3
        assert job["failed"] == 2


class TestSafeErrorSummary:
    """Coverage for the stack-trace sanitizer fronting `dof_summary`.

    See CodeQL alert py/stack-trace-exposure on `admin/dof/`. The endpoint is
    admin-only but admin payloads should still not carry tracebacks (avoids
    accidental leak of file paths or credentials echoed in exceptions).
    """

    def test_none_returns_default(self):
        from apps.api.admin_views import _safe_error_summary

        assert _safe_error_summary(None) == "No changes detected"

    def test_empty_string_returns_default(self):
        from apps.api.admin_views import _safe_error_summary

        assert _safe_error_summary("") == "No changes detected"

    def test_single_line_passes_through(self):
        from apps.api.admin_views import _safe_error_summary

        assert _safe_error_summary("3 law changes detected") == "3 law changes detected"

    def test_traceback_redacts_after_first_line(self):
        from apps.api.admin_views import _safe_error_summary

        raw = (
            "DOF download failed for 2026-04-26\n"
            "Traceback (most recent call last):\n"
            '  File "/app/scraper/dof.py", line 42, in fetch\n'
            "    response.raise_for_status()\n"
            "ConnectionError: api-key=secret123 leaked into stack"
        )
        result = _safe_error_summary(raw)
        assert result.startswith("DOF download failed for 2026-04-26")
        assert "(details redacted)" in result
        assert "secret123" not in result
        assert "/app/scraper/dof.py" not in result

    def test_long_single_line_truncates(self):
        from apps.api.admin_views import _safe_error_summary

        raw = "x" * 1000
        result = _safe_error_summary(raw)
        assert len(result) == 500


@pytest.mark.django_db
class TestHealthCheckRedisReporting:
    """A real Redis outage must be reported, not raised.

    redis-py raises redis.exceptions.RedisError, which is neither an OSError
    nor the builtin ConnectionError. The previous
    `except (ConnectionError, OSError)` could not catch it, so a Redis outage
    escaped health_check as an unhandled 500 and the documented
    services["redis"] == "error" was unreachable.
    """

    def setup_method(self):
        self.client = APIClient()
        _start_admin_patches(self)

    def teardown_method(self):
        _stop_admin_patches(self)

    def _get_health_with_cache_error(self, exc):
        """Fail only the health probe's own cache write.

        Patching cache.set wholesale also breaks the tier throttle, which
        shares the cache — so raise for the "_health" key and pass everything
        else through to the real backend.
        """
        from django.core.cache import cache

        real_set = cache.set

        def _selective_set(key, *args, **kwargs):
            if key == "_health":
                raise exc
            return real_set(key, *args, **kwargs)

        with patch("django.core.cache.cache.set", side_effect=_selective_set):
            return self.client.get(reverse("admin-health"))

    def test_redis_connection_error_is_reported_not_raised(self):
        from redis.exceptions import ConnectionError as RedisConnectionError

        response = self._get_health_with_cache_error(
            RedisConnectionError("Error connecting to redis:6379")
        )

        assert response.status_code == 200, (
            "Redis outage escaped health_check as an unhandled error instead of "
            "being reported in services['redis']"
        )
        assert response.json()["services"]["redis"] == "error"

    def test_redis_timeout_is_reported_not_raised(self):
        from redis.exceptions import TimeoutError as RedisTimeoutError

        response = self._get_health_with_cache_error(RedisTimeoutError("timeout"))

        assert response.status_code == 200
        assert response.json()["services"]["redis"] == "error"

    def test_os_level_socket_error_is_still_reported(self):
        """The original OSError path must keep working."""
        response = self._get_health_with_cache_error(OSError("socket closed"))

        assert response.status_code == 200
        assert response.json()["services"]["redis"] == "error"
