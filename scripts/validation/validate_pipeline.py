#!/usr/bin/env python
"""
End-to-end pipeline health validation script.

Checks every stage of the data pipeline and reports overall health.

Usage:
    python scripts/validation/validate_pipeline.py
    python scripts/validation/validate_pipeline.py --verbose
    python scripts/validation/validate_pipeline.py --tier state
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.indigo.settings")

import django

django.setup()


def check_metadata_files():
    """Check that metadata JSON files exist and are valid."""
    results = []

    files = {
        "state_laws_metadata.json": "state",
        "municipal_laws_metadata.json": "municipal",
    }

    for filename, tier in files.items():
        path = PROJECT_ROOT / "data" / filename
        if not path.exists():
            results.append(
                {
                    "check": f"{tier} metadata",
                    "status": "FAIL",
                    "detail": "File not found",
                }
            )
            continue

        try:
            data = json.loads(path.read_text())
            laws = data.get("laws", [])
            with_text = sum(1 for l in laws if l.get("text_file"))
            with_akn = sum(1 for l in laws if l.get("akn_file_path"))

            results.append(
                {
                    "check": f"{tier} metadata",
                    "status": "OK",
                    "detail": (
                        f"{len(laws)} laws, {with_text} with text, "
                        f"{with_akn} with AKN XML"
                    ),
                }
            )
        except Exception as e:
            results.append(
                {"check": f"{tier} metadata", "status": "FAIL", "detail": str(e)}
            )

    return results


def check_database():
    """Check database has laws and versions."""
    from apps.api.models import Law, LawVersion

    results = []

    total_laws = Law.objects.count()
    federal = Law.objects.filter(tier="federal").count()
    state = Law.objects.filter(tier="state").count()
    municipal = Law.objects.filter(tier="municipal").count()

    results.append(
        {
            "check": "Database laws",
            "status": "OK" if total_laws > 0 else "FAIL",
            "detail": (
                f"{total_laws} total: {federal} federal, "
                f"{state} state, {municipal} municipal"
            ),
        }
    )

    # Check versions with xml_file_path
    total_versions = LawVersion.objects.count()
    with_xml = (
        LawVersion.objects.exclude(xml_file_path="")
        .exclude(xml_file_path__isnull=True)
        .count()
    )

    results.append(
        {
            "check": "Law versions with file paths",
            "status": "OK" if with_xml > 0 else "WARN",
            "detail": f"{with_xml}/{total_versions} have xml_file_path",
        }
    )

    # Check how many files actually exist
    from apps.api.utils.paths import resolve_data_path_or_none

    sample_versions = LawVersion.objects.exclude(xml_file_path="").exclude(
        xml_file_path__isnull=True
    )[:100]

    found = 0
    akn_count = 0
    raw_count = 0
    for v in sample_versions:
        path = resolve_data_path_or_none(v.xml_file_path)
        if path:
            found += 1
            text = path.read_text(encoding="utf-8", errors="ignore")[:500]
            if "<?xml" in text or "<akomaNtoso" in text:
                akn_count += 1
            else:
                raw_count += 1

    sample_size = len(sample_versions)
    results.append(
        {
            "check": "File existence (sample)",
            "status": "OK" if found > 0 else "WARN",
            "detail": (
                f"{found}/{sample_size} files found "
                f"({akn_count} AKN XML, {raw_count} raw text)"
            ),
        }
    )

    return results


def check_elasticsearch():
    """Check Elasticsearch connectivity and indices."""
    from apps.api.utils.paths import ES_HOST

    results = []

    try:
        from elasticsearch import Elasticsearch

        es = Elasticsearch([ES_HOST])
        if not es.ping():
            results.append(
                {
                    "check": "Elasticsearch",
                    "status": "FAIL",
                    "detail": f"Cannot connect to {ES_HOST}",
                }
            )
            return results

        results.append(
            {"check": "Elasticsearch connection", "status": "OK", "detail": ES_HOST}
        )

        # Check indices
        for index_name in ["laws", "articles"]:
            if es.indices.exists(index=index_name):
                count = es.count(index=index_name)["count"]
                results.append(
                    {
                        "check": f"ES index '{index_name}'",
                        "status": "OK",
                        "detail": f"{count:,} documents",
                    }
                )
            else:
                results.append(
                    {
                        "check": f"ES index '{index_name}'",
                        "status": "WARN",
                        "detail": "Index does not exist",
                    }
                )

    except ImportError:
        results.append(
            {
                "check": "Elasticsearch",
                "status": "SKIP",
                "detail": "elasticsearch-py not installed",
            }
        )
    except Exception as e:
        results.append({"check": "Elasticsearch", "status": "FAIL", "detail": str(e)})

    return results


def check_parsers():
    """Check that parser components are importable and functional."""
    results = []

    try:
        from apps.parsers.akn_generator_v2 import AkomaNtosoGeneratorV2

        gen = AkomaNtosoGeneratorV2()
        results.append(
            {"check": "AKN Generator V2", "status": "OK", "detail": "Importable"}
        )
    except Exception as e:
        results.append(
            {"check": "AKN Generator V2", "status": "FAIL", "detail": str(e)}
        )

    try:
        from apps.parsers.state_parser import StateLawParser

        parser = StateLawParser(base_dir=PROJECT_ROOT)
        results.append(
            {"check": "State Law Parser", "status": "OK", "detail": "Importable"}
        )
    except Exception as e:
        results.append(
            {"check": "State Law Parser", "status": "FAIL", "detail": str(e)}
        )

    try:
        from apps.parsers.quality import QualityCalculator

        calc = QualityCalculator()
        results.append(
            {"check": "Quality Calculator", "status": "OK", "detail": "Importable"}
        )
    except Exception as e:
        results.append(
            {"check": "Quality Calculator", "status": "FAIL", "detail": str(e)}
        )

    return results


def check_path_resolution():
    """Verify path resolution works correctly."""
    from apps.api.utils.paths import BASE_DIR, ES_HOST, resolve_data_path

    results = []

    results.append(
        {
            "check": "BASE_DIR",
            "status": "OK" if BASE_DIR.exists() else "FAIL",
            "detail": str(BASE_DIR),
        }
    )

    results.append({"check": "ES_HOST", "status": "OK", "detail": ES_HOST})

    # Test resolving the data directory
    data_dir = resolve_data_path("data")
    results.append(
        {
            "check": "data/ directory",
            "status": "OK" if data_dir.exists() else "WARN",
            "detail": str(data_dir),
        }
    )

    return results


def check_dataops():
    """Check DataOps models and data."""
    results = []

    try:
        from apps.scraper.dataops.models import AcquisitionLog, DataSource, GapRecord

        sources = DataSource.objects.count()
        gaps_open = GapRecord.objects.filter(status="open").count()
        gaps_total = GapRecord.objects.count()
        logs = AcquisitionLog.objects.count()

        results.append(
            {
                "check": "DataOps sources",
                "status": "OK" if sources > 0 else "WARN",
                "detail": f"{sources} data sources registered",
            }
        )
        results.append(
            {
                "check": "DataOps gaps",
                "status": "OK",
                "detail": f"{gaps_open} open / {gaps_total} total",
            }
        )
        results.append(
            {
                "check": "DataOps logs",
                "status": "OK",
                "detail": f"{logs} acquisition logs",
            }
        )
    except Exception as e:
        results.append({"check": "DataOps", "status": "SKIP", "detail": str(e)})

    return results


def main():
    parser = argparse.ArgumentParser(description="Validate pipeline health")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--tier", choices=["federal", "state", "municipal", "all"], default="all"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("PIPELINE HEALTH VALIDATION")
    print("=" * 70)
    print()

    all_results = []

    checks = [
        ("Path Resolution", check_path_resolution),
        ("Parser Components", check_parsers),
        ("Metadata Files", check_metadata_files),
        ("Database", check_database),
        ("Elasticsearch", check_elasticsearch),
        ("DataOps", check_dataops),
    ]

    for section_name, check_fn in checks:
        print(f"--- {section_name} ---")
        try:
            results = check_fn()
        except Exception as e:
            results = [{"check": section_name, "status": "ERROR", "detail": str(e)}]

        for r in results:
            status_icon = {
                "OK": "  OK ",
                "WARN": " WARN",
                "FAIL": " FAIL",
                "SKIP": " SKIP",
                "ERROR": "ERROR",
            }.get(r["status"], "  ?  ")

            print(f"  [{status_icon}] {r['check']}: {r['detail']}")

        all_results.extend(results)
        print()

    # Summary
    ok_count = sum(1 for r in all_results if r["status"] == "OK")
    warn_count = sum(1 for r in all_results if r["status"] == "WARN")
    fail_count = sum(1 for r in all_results if r["status"] == "FAIL")
    total = len(all_results)

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total checks: {total}")
    print(f"  Passed:       {ok_count}")
    print(f"  Warnings:     {warn_count}")
    print(f"  Failed:       {fail_count}")

    if total > 0:
        health_pct = (ok_count / total) * 100
        print(f"\n  Pipeline Health: {health_pct:.0f}%")

        if fail_count == 0:
            print("  Status: HEALTHY")
        elif fail_count <= 2:
            print("  Status: DEGRADED")
        else:
            print("  Status: CRITICAL")

    print("=" * 70)

    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
