"""
Health Monitor: Probes data sources to track availability and detect degradation.
"""

import logging
import time
from dataclasses import dataclass
from datetime import timedelta

import requests
from django.db import models
from django.utils import timezone

from .models import DataSource

logger = logging.getLogger(__name__)

# Probe timeout in seconds
PROBE_TIMEOUT = 30

# Response time threshold for degraded status (ms)
DEGRADED_THRESHOLD_MS = 10000


@dataclass
class HealthResult:
    source_name: str
    status: str  # healthy, degraded, down
    response_time_ms: int
    message: str = ""


# Default probe configurations
PROBE_CONFIGS = {
    "OJN Compilacion": {
        "url": "https://compilacion.ordenjuridico.gob.mx/poderes2.php?edo=11",
        "expect_text": "fichaOrdenamiento",
    },
    "Diputados Catalog": {
        "url": "https://www.diputados.gob.mx/LeyesBiblio/index.htm",
        "expect_text": "pdf/",
    },
    "DOF API": {
        "url": "https://www.diariooficial.gob.mx/",
        "expect_text": "Diario Oficial",
    },
    "CDMX Portal": {
        "url": "https://data.consejeria.cdmx.gob.mx/index.php/leyes/leyes",
        "expect_text": ".pdf",
    },
    "Guadalajara Transparencia": {
        "url": "https://transparencia.guadalajara.gob.mx/",
        "expect_text": "",
    },
}

# Sources considered critical (checked daily)
CRITICAL_SOURCES = ["OJN Compilacion", "Diputados Catalog", "DOF API"]


class HealthMonitor:
    """Probes data sources to track availability and response times."""

    def check_source(self, source):
        """Probe a single DataSource and update its health status.

        Args:
            source: DataSource instance or source name string

        Returns:
            HealthResult with probe outcome
        """
        if isinstance(source, str):
            try:
                source = DataSource.objects.get(name=source)
            except DataSource.DoesNotExist:
                return HealthResult(
                    source_name=source,
                    status="down",
                    response_time_ms=0,
                    message=f"Source '{source}' not found in registry",
                )

        probe_config = PROBE_CONFIGS.get(source.name, {})
        url = probe_config.get("url", source.base_url)
        expect_text = probe_config.get("expect_text", "")

        if not url:
            source.mark_down()
            return HealthResult(
                source_name=source.name,
                status="down",
                response_time_ms=0,
                message="No URL configured for probe",
            )

        start = time.time()
        try:
            response = requests.get(
                url,
                timeout=PROBE_TIMEOUT,
                headers={"User-Agent": "Tezca-HealthMonitor/1.0"},
                allow_redirects=True,
            )
            elapsed_ms = int((time.time() - start) * 1000)

            if response.status_code != 200:
                source.mark_down()
                return HealthResult(
                    source_name=source.name,
                    status="down",
                    response_time_ms=elapsed_ms,
                    message=f"HTTP {response.status_code}",
                )

            if expect_text and expect_text not in response.text:
                source.mark_degraded(elapsed_ms)
                return HealthResult(
                    source_name=source.name,
                    status="degraded",
                    response_time_ms=elapsed_ms,
                    message=f"Expected text '{expect_text}' not found in response",
                )

            if elapsed_ms > DEGRADED_THRESHOLD_MS:
                source.mark_degraded(elapsed_ms)
                return HealthResult(
                    source_name=source.name,
                    status="degraded",
                    response_time_ms=elapsed_ms,
                    message=f"Slow response: {elapsed_ms}ms",
                )

            source.mark_healthy(elapsed_ms)
            return HealthResult(
                source_name=source.name,
                status="healthy",
                response_time_ms=elapsed_ms,
                message="OK",
            )

        except requests.Timeout:
            elapsed_ms = int((time.time() - start) * 1000)
            source.mark_down()
            return HealthResult(
                source_name=source.name,
                status="down",
                response_time_ms=elapsed_ms,
                message=f"Timeout after {PROBE_TIMEOUT}s",
            )
        except requests.RequestException as e:
            elapsed_ms = int((time.time() - start) * 1000)
            source.mark_down()
            return HealthResult(
                source_name=source.name,
                status="down",
                response_time_ms=elapsed_ms,
                message=str(e),
            )

    def check_all(self, level_filter=None, critical_only=False):
        """Probe all registered sources.

        Args:
            level_filter: Optional filter by level (federal/state/municipal)
            critical_only: Only check critical sources

        Returns:
            List of HealthResult
        """
        qs = DataSource.objects.all()

        if level_filter:
            qs = qs.filter(level=level_filter)

        if critical_only:
            qs = qs.filter(name__in=CRITICAL_SOURCES)

        results = []
        for source in qs:
            result = self.check_source(source)
            results.append(result)
            logger.info(
                "Health check: %s -> %s (%dms) %s",
                result.source_name,
                result.status,
                result.response_time_ms,
                result.message,
            )

        return results

    def detect_staleness(self, max_age_days=90):
        """Find laws whose sources haven't been verified recently.

        Args:
            max_age_days: Maximum acceptable age in days

        Returns:
            QuerySet of stale Law objects
        """
        from apps.api.models import Law

        cutoff = timezone.now() - timedelta(days=max_age_days)
        return (
            Law.objects.filter(
                models.Q(last_verified__isnull=True)
                | models.Q(last_verified__lt=cutoff)
            )
            .exclude(source_url="")
            .exclude(source_url__isnull=True)
        )

    def get_summary(self):
        """Get overall health summary."""
        sources = DataSource.objects.all()
        return {
            "total_sources": sources.count(),
            "healthy": sources.filter(status="healthy").count(),
            "degraded": sources.filter(status="degraded").count(),
            "down": sources.filter(status="down").count(),
            "unknown": sources.filter(status="unknown").count(),
            "never_checked": sources.filter(last_check__isnull=True).count(),
        }

    def get_detail(self):
        """Get detailed health info per source."""
        summary = self.get_summary()
        sources = list(
            DataSource.objects.all().values(
                "id",
                "name",
                "source_type",
                "level",
                "status",
                "last_check",
                "last_success",
                "response_time_ms",
                "base_url",
            )
        )
        return {"summary": summary, "sources": sources}
