"""
Custom throttle classes for export endpoints.

Uses ExportLog for persistent, auditable quota tracking instead of cache.
Limits per tier defined in tier_permissions.EXPORT_HOURLY_LIMITS.
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework.throttling import BaseThrottle

from .models import ExportLog
from .tier_permissions import EXPORT_HOURLY_LIMITS as TIER_LIMITS


def get_export_count(*, user_id: str = "", ip_address: str = "") -> int:
    """Count exports in the last hour for a user or IP."""
    one_hour_ago = timezone.now() - timedelta(hours=1)
    qs = ExportLog.objects.filter(created_at__gte=one_hour_ago)
    if user_id:
        qs = qs.filter(user_id=user_id)
    else:
        qs = qs.filter(ip_address=ip_address, user_id="")
    return qs.count()


def check_export_quota(tier: str, user_id: str, ip_address: str) -> tuple[bool, int]:
    """
    Check if an export is allowed under the tier quota.

    Returns (allowed, seconds_until_retry).
    """
    limit = TIER_LIMITS.get(tier, TIER_LIMITS["anon"])

    if user_id:
        count = get_export_count(user_id=user_id)
    else:
        count = get_export_count(ip_address=ip_address)

    if count >= limit:
        # Find oldest export in window to calculate retry-after
        one_hour_ago = timezone.now() - timedelta(hours=1)
        qs = ExportLog.objects.filter(created_at__gte=one_hour_ago)
        if user_id:
            qs = qs.filter(user_id=user_id)
        else:
            qs = qs.filter(ip_address=ip_address, user_id="")
        oldest = qs.order_by("created_at").first()
        if oldest:
            retry_after = int(
                (
                    oldest.created_at + timedelta(hours=1) - timezone.now()
                ).total_seconds()
            )
            return False, max(retry_after, 1)
        return False, 3600

    return True, 0


def log_export(user_id: str, ip_address: str, law_id: str, fmt: str, tier: str) -> None:
    """Record an export for quota tracking."""
    ExportLog.objects.create(
        user_id=user_id,
        ip_address=ip_address,
        law_id=law_id,
        format=fmt,
        tier=tier,
    )
