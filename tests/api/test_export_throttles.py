"""Tests for export throttle functions: quota tracking via ExportLog."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.api.export_throttles import check_export_quota, get_export_count, log_export
from apps.api.models import ExportLog


def _create_export(
    user_id="", ip_address="127.0.0.1", law_id="cpeum", fmt="pdf", tier="anon"
):
    """Helper to create an ExportLog record and return it."""
    return ExportLog.objects.create(
        user_id=user_id,
        ip_address=ip_address,
        law_id=law_id,
        format=fmt,
        tier=tier,
    )


@pytest.mark.django_db
class TestGetExportCount:
    def test_counts_by_user_id(self):
        """Create 3 records for user 'u1', 1 for 'u2' -- count for u1 == 3."""
        for _ in range(3):
            _create_export(user_id="u1", ip_address="10.0.0.1")
        _create_export(user_id="u2", ip_address="10.0.0.2")

        assert get_export_count(user_id="u1") == 3
        assert get_export_count(user_id="u2") == 1

    def test_counts_by_ip_address(self):
        """Records without user_id are counted by IP address."""
        for _ in range(2):
            _create_export(user_id="", ip_address="192.168.1.10")
        _create_export(user_id="", ip_address="192.168.1.20")

        assert get_export_count(ip_address="192.168.1.10") == 2
        assert get_export_count(ip_address="192.168.1.20") == 1

    def test_excludes_old_records(self):
        """Records older than 1 hour are not counted."""
        record = _create_export(user_id="", ip_address="10.0.0.5")
        # Move created_at to 2 hours ago
        two_hours_ago = timezone.now() - timedelta(hours=2)
        ExportLog.objects.filter(pk=record.pk).update(created_at=two_hours_ago)

        assert get_export_count(ip_address="10.0.0.5") == 0

    def test_returns_zero_when_no_records(self):
        """Fresh DB returns 0 for any user or IP."""
        assert get_export_count(user_id="nonexistent") == 0
        assert get_export_count(ip_address="10.99.99.99") == 0

    def test_user_id_takes_priority_over_ip(self):
        """Records with user_id are filtered by user_id; records without are filtered by IP."""
        # Authenticated export (has user_id)
        _create_export(user_id="auth-user", ip_address="10.0.0.1")
        # Anonymous export from same IP (no user_id)
        _create_export(user_id="", ip_address="10.0.0.1")

        # Counting by user_id should find only the authenticated record
        assert get_export_count(user_id="auth-user") == 1

        # Counting by IP (anonymous path) should find only the record with empty user_id
        assert get_export_count(ip_address="10.0.0.1") == 1


@pytest.mark.django_db
class TestCheckExportQuota:
    def test_within_quota_returns_allowed(self):
        """Zero exports against anon limit of 10 returns (True, 0)."""
        allowed, retry_after = check_export_quota("anon", "", "172.16.0.1")

        assert allowed is True
        assert retry_after == 0

    def test_quota_exceeded_returns_not_allowed(self):
        """Create 10 anon exports for an IP, then check returns (False, retry_after>0)."""
        ip = "172.16.0.2"
        for _ in range(10):
            _create_export(user_id="", ip_address=ip, tier="anon")

        allowed, retry_after = check_export_quota("anon", "", ip)

        assert allowed is False
        assert retry_after > 0

    def test_retry_after_calculation(self):
        """Retry-after is based on the oldest export in the window."""
        ip = "172.16.0.3"
        # Create 10 exports (anon limit)
        for _ in range(10):
            _create_export(user_id="", ip_address=ip, tier="anon")

        # Move the oldest record to 50 minutes ago so it expires in ~10 minutes
        oldest = (
            ExportLog.objects.filter(ip_address=ip, user_id="")
            .order_by("created_at")
            .first()
        )
        fifty_min_ago = timezone.now() - timedelta(minutes=50)
        ExportLog.objects.filter(pk=oldest.pk).update(created_at=fifty_min_ago)

        allowed, retry_after = check_export_quota("anon", "", ip)

        assert allowed is False
        # Oldest was 50 min ago, expires in ~10 min = ~600 seconds
        # Allow generous range to account for test execution time
        assert 500 <= retry_after <= 700

    def test_unknown_tier_defaults_to_anon(self):
        """An unrecognized tier falls back to the anon limit (10)."""
        ip = "172.16.0.4"
        # Create 10 exports (anon limit)
        for _ in range(10):
            _create_export(user_id="", ip_address=ip)

        allowed, _ = check_export_quota("nonexistent_tier", "", ip)
        assert allowed is False

        # 9 exports should still be within anon limit of 10
        ip2 = "172.16.0.5"
        for _ in range(9):
            _create_export(user_id="", ip_address=ip2)

        allowed2, retry2 = check_export_quota("nonexistent_tier", "", ip2)
        assert allowed2 is True
        assert retry2 == 0

    def test_per_tier_limits(self):
        """Verify distinct limits: anon=10, essentials=30, academic=60."""
        ip_anon = "172.16.1.1"
        ip_ess = "172.16.1.2"
        ip_acad = "172.16.1.3"

        # 10 exports: anon blocked, essentials and academic allowed
        for _ in range(10):
            _create_export(user_id="", ip_address=ip_anon)
            _create_export(user_id="", ip_address=ip_ess)
            _create_export(user_id="", ip_address=ip_acad)

        anon_allowed, _ = check_export_quota("anon", "", ip_anon)
        ess_allowed, _ = check_export_quota("essentials", "", ip_ess)
        acad_allowed, _ = check_export_quota("academic", "", ip_acad)

        assert anon_allowed is False
        assert ess_allowed is True
        assert acad_allowed is True

        # Add 20 more (total 30): essentials blocked, academic still allowed
        for _ in range(20):
            _create_export(user_id="", ip_address=ip_ess)
            _create_export(user_id="", ip_address=ip_acad)

        ess_allowed2, _ = check_export_quota("essentials", "", ip_ess)
        acad_allowed2, _ = check_export_quota("academic", "", ip_acad)

        assert ess_allowed2 is False
        assert acad_allowed2 is True

    def test_user_id_path(self):
        """Authenticated user is checked by user_id, not IP."""
        user_id = "auth-user-quota"
        ip = "172.16.2.1"

        # Create 10 exports for the user (anon limit)
        for _ in range(10):
            _create_export(user_id=user_id, ip_address=ip, tier="anon")

        # Also create anonymous exports from the same IP
        for _ in range(5):
            _create_export(user_id="", ip_address=ip, tier="anon")

        # Checking with user_id should see 10 (blocked for anon tier)
        allowed, retry_after = check_export_quota("anon", user_id, ip)
        assert allowed is False
        assert retry_after > 0

        # Checking anonymously by IP should see only 5 (allowed for anon tier)
        allowed_ip, retry_ip = check_export_quota("anon", "", ip)
        assert allowed_ip is True
        assert retry_ip == 0


@pytest.mark.django_db
class TestLogExport:
    def test_creates_export_log_record(self):
        """log_export creates a single ExportLog record."""
        assert ExportLog.objects.count() == 0

        log_export("user-1", "10.0.0.1", "cpeum", "pdf", "academic")

        assert ExportLog.objects.count() == 1

    def test_multiple_logs(self):
        """Three calls create three records."""
        log_export("user-1", "10.0.0.1", "cpeum", "pdf", "academic")
        log_export("user-1", "10.0.0.1", "lgeepa", "txt", "academic")
        log_export("user-2", "10.0.0.2", "cpeum", "json", "essentials")

        assert ExportLog.objects.count() == 3

    def test_stores_all_fields(self):
        """Verify all fields are stored correctly on the created record."""
        log_export("user-abc", "192.168.5.5", "lfmn", "latex", "institutional")

        record = ExportLog.objects.get(user_id="user-abc")
        assert record.ip_address == "192.168.5.5"
        assert record.law_id == "lfmn"
        assert record.format == "latex"
        assert record.tier == "institutional"
        assert record.created_at is not None
