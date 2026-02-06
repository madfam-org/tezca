#!/usr/bin/env python
"""
Coverage Report CLI: Generates a comprehensive data coverage report.

Usage:
    python scripts/dataops/coverage_report.py [--format text|json|markdown]
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

from apps.scraper.dataops.coverage_dashboard import CoverageDashboard  # noqa: E402


def format_text(report):
    """Format report as human-readable text."""
    lines = []
    s = report["summary"]
    lines.append("=" * 70)
    lines.append("Leyes Como Código MX - Coverage Status Report")
    lines.append("=" * 70)
    lines.append(f"  Total in DB: {s['total_in_db']}")
    lines.append(f"  Total scraped: {s['total_scraped']}")
    lines.append(f"  Total gaps: {s['total_gaps']}")
    lines.append(f"  Actionable gaps: {s['actionable_gaps']}")
    lines.append("")

    # Federal
    f = report["federal"]
    lines.append("--- FEDERAL ---")
    lines.append(f"  Laws in DB: {f['laws_in_db']}")
    lines.append(f"  Laws scraped: {f['laws_scraped']}")
    for k, v in f.get("gaps", {}).items():
        lines.append(f"  Gap: {k} - {v}")
    lines.append("")

    # State
    st = report["state"]
    lines.append("--- STATE ---")
    lines.append(f"  Total in DB: {st['total_in_db']}")
    lines.append(f"  Total scraped: {st['total_scraped']}")
    lines.append(f"  Permanent gaps: {st['total_permanent_gaps']}")
    if st["states_with_anomalies"]:
        lines.append(f"  Anomalies: {', '.join(st['states_with_anomalies'])}")
    lines.append("")

    # Municipal
    m = report["municipal"]
    lines.append("--- MUNICIPAL ---")
    lines.append(f"  Total in DB: {m['total_in_db']}")
    lines.append(f"  Total scraped: {m['total_scraped']}")
    lines.append(f"  Cities covered: {m['cities_covered']}")
    lines.append(f"  Est. total municipalities: {m['estimated_total_municipalities']}")
    for city in m["per_city"][:10]:
        lines.append(
            f"    {city['city']}: {city['scraped']} scraped, {city['in_db']} in DB"
        )
    lines.append("")

    # Gaps
    g = report["gaps"]
    lines.append("--- GAPS ---")
    for status, count in g.items():
        lines.append(f"  {status}: {count}")

    lines.append("=" * 70)
    return "\n".join(lines)


def format_markdown(report):
    """Format report as Markdown table."""
    lines = []
    s = report["summary"]
    lines.append("# Coverage Status Report")
    lines.append("")
    lines.append(
        f"**Grand Total**: {s['total_scraped']} laws scraped "
        f"({s['total_in_db']} in DB)"
    )
    lines.append("")

    lines.append("| Level | Scraped | In DB | Gaps |")
    lines.append("|-------|---------|-------|------|")

    f = report["federal"]
    lines.append(
        f"| Federal | {f['laws_scraped']} | {f['laws_in_db']} | "
        f"Reglamentos, DOF, NOMs |"
    )

    st = report["state"]
    lines.append(
        f"| State | {st['total_scraped']} | {st['total_in_db']} | "
        f"{st['total_permanent_gaps']} permanent |"
    )

    m = report["municipal"]
    lines.append(
        f"| Municipal | {m['total_scraped']} | {m['total_in_db']} | "
        f"{m['estimated_total_municipalities'] - m['cities_covered']} cities uncovered |"
    )

    lines.append("")

    if st["states_with_anomalies"]:
        lines.append("## Anomalies")
        for state in st["states_with_anomalies"]:
            lines.append(f"- **{state}**: Suspiciously low count")
        lines.append("")

    g = report["gaps"]
    lines.append("## Gap Summary")
    lines.append(f"- Open: {g.get('open', 0)}")
    lines.append(f"- In progress: {g.get('in_progress', 0)}")
    lines.append(f"- Resolved: {g.get('resolved', 0)}")
    lines.append(f"- Permanent: {g.get('permanent', 0)}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate coverage report")
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        dest="output_format",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    dashboard = CoverageDashboard()
    report = dashboard.full_report()

    if args.output_format == "json":
        print(json.dumps(report, indent=2, default=str))
    elif args.output_format == "markdown":
        print(format_markdown(report))
    else:
        print(format_text(report))


if __name__ == "__main__":
    main()
