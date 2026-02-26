"""
DRF middleware that logs API usage to APIUsageLog.

Uses batched inserts to avoid per-request DB writes.
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)

# In-memory buffer for batched inserts
_buffer = []
_buffer_lock = threading.Lock()
_last_flush = time.time()

BUFFER_SIZE = 100
FLUSH_INTERVAL = 5  # seconds


def _flush_buffer():
    """Flush the usage log buffer to the database."""
    global _last_flush
    with _buffer_lock:
        if not _buffer:
            return
        entries = _buffer.copy()
        _buffer.clear()
        _last_flush = time.time()

    try:
        from ..models import APIUsageLog

        APIUsageLog.objects.bulk_create(
            [APIUsageLog(**entry) for entry in entries],
            ignore_conflicts=True,
        )
    except Exception:
        logger.warning(
            "Failed to flush usage log buffer (%d entries)", len(entries), exc_info=True
        )


def log_api_usage(
    *,
    api_key_prefix: str = "",
    ip_address: str,
    endpoint: str,
    method: str = "GET",
    status_code: int = 200,
    response_time_ms: int = 0,
):
    """Add a usage log entry to the buffer. Flushes when buffer is full or stale."""
    global _last_flush

    entry = {
        "api_key_prefix": api_key_prefix,
        "ip_address": ip_address,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
    }

    with _buffer_lock:
        _buffer.append(entry)
        should_flush = (
            len(_buffer) >= BUFFER_SIZE or (time.time() - _last_flush) >= FLUSH_INTERVAL
        )

    if should_flush:
        _flush_buffer()


class UsageLoggingMiddleware:
    """
    Django middleware that logs API usage for /api/ requests.

    Add to MIDDLEWARE list in settings.py to enable.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only log API requests
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        start_time = time.time()
        response = self.get_response(request)
        elapsed_ms = int((time.time() - start_time) * 1000)

        # Extract identity
        user = getattr(request, "user", None)
        api_key_prefix = ""
        if user and getattr(user, "is_authenticated", False):
            api_key_prefix = getattr(user, "api_key_prefix", "")

        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = (
            xff.split(",")[0].strip()
            if xff
            else request.META.get("REMOTE_ADDR", "127.0.0.1")
        )

        log_api_usage(
            api_key_prefix=api_key_prefix,
            ip_address=ip,
            endpoint=request.path[:200],
            method=request.method,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
        )

        return response
