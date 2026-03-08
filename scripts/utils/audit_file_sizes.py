#!/usr/bin/env python3
"""
Codebase Refactoring Audit

Scans all Python files and reports:
- ERROR: Files over 800 lines
- WARNING: Files over 600 lines

Usage:
    python scripts/utils/audit_file_sizes.py
    python scripts/utils/audit_file_sizes.py --format json
"""

import argparse
import json
import sys
from pathlib import Path

# Thresholds
ERROR_THRESHOLD = 800
WARNING_THRESHOLD = 600

# Directories to exclude
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "htmlcov",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    "engines",  # External codebases
}

# Files allowed to exceed ERROR_THRESHOLD (complex scrapers with inherent verbosity)
ALLOWED_LARGE_FILES = {
    "apps/scraper/federal/nom_agency_scrapers.py",
    "apps/scraper/federal/treaty_scraper.py",
    "apps/scraper/judicial/scjn_scraper.py",
}


def count_lines(file_path: Path) -> int:
    """Count non-empty lines in a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def should_exclude(path: Path) -> bool:
    """Check if path should be excluded from audit."""
    parts = set(path.parts)
    return bool(EXCLUDE_DIRS & parts)


def audit_codebase(root_dir: Path) -> dict:
    """
    Audit all Python files in the codebase.

    Returns:
        dict with 'errors', 'warnings', and 'summary' keys
    """
    errors = []
    warnings = []
    total_files = 0
    total_lines = 0

    for py_file in root_dir.rglob("*.py"):
        if should_exclude(py_file):
            continue

        line_count = count_lines(py_file)
        total_files += 1
        total_lines += line_count

        relative_path = py_file.relative_to(root_dir)

        if (
            line_count > ERROR_THRESHOLD
            and str(relative_path) not in ALLOWED_LARGE_FILES
        ):
            errors.append(
                {"path": str(relative_path), "lines": line_count, "severity": "ERROR"}
            )
        elif line_count > WARNING_THRESHOLD:
            warnings.append(
                {"path": str(relative_path), "lines": line_count, "severity": "WARNING"}
            )

    # Sort by line count descending
    errors.sort(key=lambda x: x["lines"], reverse=True)
    warnings.sort(key=lambda x: x["lines"], reverse=True)

    return {
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total_files": total_files,
            "total_lines": total_lines,
            "avg_lines_per_file": total_lines // total_files if total_files > 0 else 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    }


def print_report(results: dict):
    """Print human-readable audit report."""
    summary = results["summary"]
    errors = results["errors"]
    warnings = results["warnings"]

    print("=" * 70)
    print("CODEBASE REFACTORING AUDIT")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"  Total files scanned:  {summary['total_files']}")
    print(f"  Total lines of code:  {summary['total_lines']:,}")
    print(f"  Average lines/file:   {summary['avg_lines_per_file']}")
    print(f"  Files needing refactor (>800 lines): {summary['error_count']}")
    print(f"  Files to watch (>600 lines):         {summary['warning_count']}")

    if errors:
        print(
            f"\n❌ ERRORS - Files over {ERROR_THRESHOLD} lines (require refactoring):"
        )
        for item in errors:
            print(f"  • {item['path']:60} {item['lines']:4} lines")

    if warnings:
        print(
            f"\n⚠️  WARNINGS - Files over {WARNING_THRESHOLD} lines (consider refactoring):"
        )
        for item in warnings:
            print(f"  • {item['path']:60} {item['lines']:4} lines")

    if not errors and not warnings:
        print("\n✅ All files are within acceptable size limits!")

    print("\n" + "=" * 70)

    # Exit with error code if there are errors
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description="Audit codebase for file size issues")
    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    parser.add_argument("--root", type=str, default=".", help="Root directory to scan")
    args = parser.parse_args()

    root_dir = Path(args.root).resolve()
    results = audit_codebase(root_dir)

    if args.format == "json":
        print(json.dumps(results, indent=2))
        return 1 if results["errors"] else 0
    else:
        return print_report(results)


if __name__ == "__main__":
    sys.exit(main())
