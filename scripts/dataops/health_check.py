#!/usr/bin/env python
"""
Health Check CLI: Probes data sources and reports their status.

Usage:
    python scripts/dataops/health_check.py [--sources critical|all] [--format text|json]
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.indigo.settings")

import django  # noqa: E402

django.setup()

from apps.scraper.dataops.health_monitor import HealthMonitor  # noqa: E402


def format_text(results, summary):
    """Format results as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("Data Source Health Check")
    lines.append("=" * 70)

    status_symbols = {"healthy": "[OK]", "degraded": "[!!]", "down": "[XX]"}

    for r in results:
        sym = status_symbols.get(r.status, "[??]")
        lines.append(
            f"  {sym} {r.source_name:<30} {r.response_time_ms:>6}ms  {r.message}"
        )

    lines.append("")
    lines.append(
        f"Summary: {summary['healthy']} healthy, "
        f"{summary['degraded']} degraded, "
        f"{summary['down']} down, "
        f"{summary['unknown']} unknown"
    )
    lines.append("=" * 70)
    return "\n".join(lines)


def format_json(results, summary):
    """Format results as JSON."""
    data = {
        "results": [
            {
                "source": r.source_name,
                "status": r.status,
                "response_time_ms": r.response_time_ms,
                "message": r.message,
            }
            for r in results
        ],
        "summary": summary,
    }
    return json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Check data source health")
    parser.add_argument(
        "--sources",
        choices=["critical", "all"],
        default="critical",
        help="Which sources to check (default: critical)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="output_format",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    monitor = HealthMonitor()
    critical_only = args.sources == "critical"
    results = monitor.check_all(critical_only=critical_only)
    summary = monitor.get_summary()

    if args.output_format == "json":
        print(format_json(results, summary))
    else:
        print(format_text(results, summary))

    # Exit code: 1 if any source is down
    if any(r.status == "down" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
