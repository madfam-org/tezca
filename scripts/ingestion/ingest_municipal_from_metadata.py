#!/usr/bin/env python3
"""
Municipal law ingestion from pre-downloaded metadata JSONs.

Scans data/municipal/{city}/{city}_metadata.json files, optionally parses
PDFs through StateLawParser for AKN XML generation, and creates Law +
LawVersion records in the database.

Usage:
    python scripts/ingestion/ingest_municipal_from_metadata.py
    python scripts/ingestion/ingest_municipal_from_metadata.py --city guadalajara
    python scripts/ingestion/ingest_municipal_from_metadata.py --skip-parse --dry-run
    python scripts/ingestion/ingest_municipal_from_metadata.py --workers 4 --limit 50
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.indigo.settings")

import django

django.setup()

from django.utils.dateparse import parse_date

from apps.api.models import Law, LawVersion

DATA_DIR = PROJECT_ROOT / "data" / "municipal"


def discover_metadata_files(city_filter=None):
    """Find all {city}/{city}_metadata.json files under data/municipal/."""
    found = []
    if not DATA_DIR.is_dir():
        print(f"ERROR: Municipal data directory not found: {DATA_DIR}")
        return found

    for city_dir in sorted(DATA_DIR.iterdir()):
        if not city_dir.is_dir():
            continue
        city_key = city_dir.name
        if city_filter and city_key != city_filter:
            continue
        meta_path = city_dir / f"{city_key}_metadata.json"
        if meta_path.is_file():
            found.append((city_key, meta_path))
        else:
            print(
                f"  WARN: No metadata file for {city_key} (expected {meta_path.name})"
            )

    return found


def parse_single_law(law_meta):
    """
    Parse a single municipal law PDF to AKN XML.

    Runs in a subprocess when using --workers > 1. Must re-import inside
    the function because ProcessPoolExecutor forks.
    """
    # Lazy import inside worker to avoid Django setup issues in subprocesses
    from apps.parsers.state_parser import StateLawParser

    parser = StateLawParser(base_dir=PROJECT_ROOT)

    official_id = law_meta.get("official_id", "")
    local_path = law_meta.get("local_path", "")

    # StateLawParser.parse_law expects "text_file" key for the source file
    parse_meta = {
        "official_id": official_id,
        "law_name": law_meta.get("law_name", "Unknown"),
        "state": law_meta.get("state", ""),
        "tier": "municipal",
        "municipality": law_meta.get("municipality", ""),
        "publication_date": law_meta.get("publication_date", "2023-01-01"),
        "text_file": local_path,
    }

    result = parser.parse_law(parse_meta)
    return {
        "official_id": official_id,
        "success": result.success,
        "error": result.error,
        "akn_path": str(result.akn_path) if result.akn_path else "",
        "article_count": result.article_count,
        "duration": result.duration_seconds,
    }


def ingest_batch(laws_meta, batch_label="", dry_run=False, skip_parse=False, workers=1):
    """Ingest a batch of municipal law metadata into the DB."""
    created = 0
    updated = 0
    errors = 0
    parsed_ok = 0
    parse_fail = 0
    total = len(laws_meta)

    if not total:
        print(f"  {batch_label}: No laws to ingest.")
        return 0

    # --- Phase 1: Parse PDFs (optional) ---
    akn_results = {}
    if not skip_parse:
        print(f"  Parsing {total} PDFs (workers={workers})...")
        parse_start = time.time()

        if workers > 1:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                future_map = {
                    executor.submit(parse_single_law, meta): meta.get("official_id", "")
                    for meta in laws_meta
                }
                for future in as_completed(future_map):
                    oid = future_map[future]
                    try:
                        res = future.result()
                        akn_results[res["official_id"]] = res
                        if res["success"]:
                            parsed_ok += 1
                        else:
                            parse_fail += 1
                    except Exception as e:
                        parse_fail += 1
                        if parse_fail <= 10:
                            print(f"    PARSE ERROR {oid}: {e}")
                    done = parsed_ok + parse_fail
                    if done % 100 == 0:
                        print(f"    Parsed {done}/{total}...")
        else:
            for i, meta in enumerate(laws_meta, 1):
                try:
                    res = parse_single_law(meta)
                    akn_results[res["official_id"]] = res
                    if res["success"]:
                        parsed_ok += 1
                    else:
                        parse_fail += 1
                        if parse_fail <= 10:
                            print(
                                f"    PARSE FAIL {res['official_id']}: {res['error']}"
                            )
                except Exception as e:
                    parse_fail += 1
                    if parse_fail <= 10:
                        print(f"    PARSE ERROR {meta.get('official_id', '?')}: {e}")
                if i % 100 == 0:
                    print(f"    Parsed {i}/{total}...")

        parse_elapsed = time.time() - parse_start
        print(
            f"  Parse complete: {parsed_ok} OK, {parse_fail} failed "
            f"({parse_elapsed:.1f}s)"
        )

    # --- Phase 2: DB ingestion ---
    print(f"  Ingesting {total} laws into DB...")
    if dry_run:
        print("  [DRY RUN] Skipping DB writes.")
        for meta in laws_meta[:5]:
            oid = meta.get("official_id", "?")
            name = meta.get("law_name", "?")[:60]
            print(f"    {oid}: {name}")
        if total > 5:
            print(f"    ... and {total - 5} more")
        return 0

    for i, meta in enumerate(laws_meta, 1):
        official_id = meta.get("official_id", "")
        law_name = meta.get("law_name", "")
        if not official_id or not law_name:
            errors += 1
            continue

        try:
            category = meta.get("category", "Otros")
            state = meta.get("state", "")
            municipality = meta.get("municipality", "")
            source_url = (meta.get("url", "") or "")[:500]
            law_type = meta.get("law_type", "legislative")

            # Normalize law_type: "non-legislative" -> "non_legislative"
            if law_type == "non-legislative":
                law_type = "non_legislative"

            short_name = law_name[:200]
            official_id = official_id[:200]

            defaults = {
                "name": law_name[:500],
                "short_name": short_name,
                "category": category[:100] if category else "",
                "tier": "municipal",
                "state": state[:100] if state else "",
                "municipality": municipality[:100] if municipality else "",
                "source_url": source_url,
                "law_type": law_type[:20] if law_type else "legislative",
            }

            law, law_created = Law.objects.get_or_create(
                official_id=official_id,
                defaults=defaults,
            )

            if not law_created:
                for k, v in defaults.items():
                    setattr(law, k, v)
                law.save()
                updated += 1
            else:
                created += 1

            # Create LawVersion
            pub_date_str = meta.get("publication_date", "")
            pub_date = parse_date(pub_date_str) if pub_date_str else None
            if not pub_date:
                pub_date = parse_date("2023-01-01")

            # Use AKN path from parse results if available
            xml_path = ""
            parse_res = akn_results.get(official_id)
            if parse_res and parse_res.get("akn_path"):
                xml_path = parse_res["akn_path"]
                # Strip project root prefix for relative storage
                xml_path_str = str(xml_path)
                proj_prefix = str(PROJECT_ROOT) + "/"
                if xml_path_str.startswith(proj_prefix):
                    xml_path = xml_path_str[len(proj_prefix) :]
                # Strip data/ prefix for R2-compatible keys
                if xml_path.startswith("data/"):
                    xml_path = xml_path[5:]

            LawVersion.objects.get_or_create(
                law=law,
                publication_date=pub_date,
                defaults={
                    "dof_url": source_url,
                    "xml_file_path": xml_path[:500],
                },
            )

        except Exception as e:
            errors += 1
            if errors <= 10:
                print(f"    DB ERROR [{i}] {official_id[:40]}: {e}")

        if i % 100 == 0:
            print(
                f"    [{i}/{total}] created={created} updated={updated} "
                f"errors={errors}"
            )

    print(f"\n  {batch_label} ingestion complete:")
    print(f"    Created: {created}, Updated: {updated}, Errors: {errors}")
    return created + updated


def load_city_metadata(meta_path):
    """Load and validate a city metadata JSON file."""
    with open(meta_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    laws = data.get("laws", [])
    city_key = data.get("city_key", meta_path.parent.name)
    state_name = data.get("state", "")
    municipality = data.get("municipality", "")

    # Enrich each law with official_id if missing
    enriched = []
    for law in laws:
        file_id = law.get("file_id", "")
        if not file_id:
            continue

        # Generate official_id: mun_{city}_{file_id}
        if not law.get("official_id"):
            law["official_id"] = f"mun_{city_key}_{file_id}"

        # Fill in state/municipality from top-level if missing
        if not law.get("state"):
            law["state"] = state_name
        if not law.get("municipality"):
            law["municipality"] = municipality

        enriched.append(law)

    return enriched, city_key


def main():
    parser = argparse.ArgumentParser(
        description="Ingest municipal laws from pre-downloaded metadata"
    )
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="Process a single city (directory name under data/municipal/)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers for PDF parsing (default: 1)",
    )
    parser.add_argument(
        "--skip-parse",
        action="store_true",
        help="Skip PDF parsing, ingest metadata only (no AKN XML)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be ingested without writing to DB",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of laws per city (0 = no limit)",
    )
    args = parser.parse_args()

    print("Municipal Law Ingestion from Metadata")
    print("=" * 50)
    print(f"  Data dir:   {DATA_DIR}")
    print(f"  City:       {args.city or 'all'}")
    print(f"  Workers:    {args.workers}")
    print(f"  Skip parse: {args.skip_parse}")
    print(f"  Dry run:    {args.dry_run}")
    print(f"  Limit:      {args.limit or 'none'}")
    print()

    metadata_files = discover_metadata_files(city_filter=args.city)
    if not metadata_files:
        print("ERROR: No metadata files found.")
        sys.exit(1)

    print(f"Found {len(metadata_files)} city metadata file(s).\n")

    grand_total = 0
    start_time = time.time()

    for city_key, meta_path in metadata_files:
        print(f"--- {city_key.upper()} ---")
        print(f"  Loading {meta_path.name}...")

        try:
            laws, _ = load_city_metadata(meta_path)
        except Exception as e:
            print(f"  ERROR loading metadata: {e}")
            continue

        print(f"  Found {len(laws)} laws.")

        if args.limit > 0:
            laws = laws[: args.limit]
            print(f"  Limited to {len(laws)} laws.")

        count = ingest_batch(
            laws,
            batch_label=city_key.capitalize(),
            dry_run=args.dry_run,
            skip_parse=args.skip_parse,
            workers=args.workers,
        )
        grand_total += count
        print()

    elapsed = time.time() - start_time
    print("=" * 50)
    print(f"Total laws ingested: {grand_total}")
    print(f"Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
