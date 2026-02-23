#!/usr/bin/env python3
"""
Lean law ingestion from R2 metadata JSONs — no text file validation.

Creates Law + LawVersion records directly from metadata, using akn_file_path
as xml_file_path. Skips the text content check that the management commands do.

Usage (on production pod):
    PYTHONPATH=/tmp/pylibs:$PYTHONPATH python scripts/ingestion/ingest_from_metadata.py --state
    PYTHONPATH=/tmp/pylibs:$PYTHONPATH python scripts/ingestion/ingest_from_metadata.py --non-legislative
    PYTHONPATH=/tmp/pylibs:$PYTHONPATH python scripts/ingestion/ingest_from_metadata.py --all
"""

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.indigo.settings")

import django

django.setup()

from django.utils.dateparse import parse_date

from apps.api.models import Law, LawVersion
from apps.api.storage import get_storage_backend


def _strip_host_prefix(path_str):
    """Strip absolute host project root from paths."""
    for marker in ("tezca/", "leyes-como-codigo-mx/"):
        idx = path_str.find(marker)
        if idx != -1:
            return path_str[idx + len(marker) :]
    return path_str


def _normalize_r2_key(path_str):
    """Convert a metadata path to an R2 key."""
    key = _strip_host_prefix(path_str)
    key = key.lstrip("/")
    if key.startswith("data/"):
        key = key[5:]
    return key


def ingest_batch(laws_meta, law_type="", batch_label=""):
    """Ingest a batch of law metadata into the DB."""
    created = 0
    updated = 0
    errors = 0
    no_akn = 0

    for i, meta in enumerate(laws_meta, 1):
        official_id = meta.get("official_id", "")
        law_name = meta.get("law_name", "")
        if not official_id or not law_name:
            errors += 1
            continue

        try:
            tier = meta.get("tier", "state")
            category = meta.get("category", "Otros")
            state = meta.get("state", "")
            municipality = meta.get("municipality", "")
            source_url = (meta.get("url", "") or "")[:500]

            # Truncate fields to fit DB constraints
            short_name = law_name[:200]
            official_id = official_id[:200]

            defaults = {
                "name": law_name[:500],
                "short_name": short_name,
                "category": category[:100] if category else "",
                "tier": tier[:50] if tier else "state",
                "state": state[:100] if state else "",
                "source_url": source_url,
            }
            if municipality:
                defaults["municipality"] = municipality[:100]
            if law_type:
                defaults["law_type"] = law_type[:20]

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

            # Create LawVersion with akn_file_path
            pub_date_str = meta.get("publication_date", "")
            pub_date = parse_date(pub_date_str) if pub_date_str else None
            if not pub_date:
                pub_date = parse_date("2023-01-01")

            akn_file = meta.get("akn_file_path", "")
            if akn_file:
                xml_key = _normalize_r2_key(akn_file)
            else:
                text_file = meta.get("text_file", "")
                xml_key = _normalize_r2_key(text_file) if text_file else ""
                no_akn += 1

            LawVersion.objects.get_or_create(
                law=law,
                publication_date=pub_date,
                defaults={
                    "dof_url": (meta.get("url", "") or "")[:500],
                    "xml_file_path": xml_key[:500],
                },
            )

        except Exception as e:
            errors += 1
            if errors <= 10:
                print(f"  ERROR [{i}] {official_id[:40]}: {e}")

        if i % 500 == 0:
            print(
                f"  [{i}/{len(laws_meta)}] created={created} updated={updated} errors={errors}"
            )

    print(f"\n{batch_label} ingestion complete:")
    print(
        f"  Created: {created}, Updated: {updated}, Errors: {errors}, No AKN: {no_akn}"
    )
    return created + updated


def main():
    parser = argparse.ArgumentParser(description="Lean law ingestion from metadata")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--state", action="store_true", help="Ingest state legislative laws"
    )
    group.add_argument(
        "--non-legislative", action="store_true", help="Ingest state non-legislative"
    )
    group.add_argument(
        "--all", action="store_true", help="Ingest both state + non-legislative"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    storage = get_storage_backend()
    total = 0

    if args.state or args.all:
        print("Loading state_laws_metadata.json from R2...")
        content = storage.get("state_laws_metadata.json")
        if not content:
            print("ERROR: state_laws_metadata.json not found")
            sys.exit(1)
        meta = json.loads(content)
        laws = meta.get("laws", [])
        print(f"Found {len(laws)} state legislative laws")
        if not args.dry_run:
            total += ingest_batch(laws, batch_label="State legislative")
        else:
            print("Dry run — skipping")

    if args.non_legislative or args.all:
        print("\nLoading state_laws_non_legislative_metadata.json from R2...")
        content = storage.get("state_laws_non_legislative_metadata.json")
        if not content:
            print("ERROR: state_laws_non_legislative_metadata.json not found")
            sys.exit(1)
        meta = json.loads(content)
        laws = meta.get("laws", [])
        print(f"Found {len(laws)} non-legislative laws")
        if not args.dry_run:
            total += ingest_batch(
                laws, law_type="non_legislative", batch_label="Non-legislative"
            )
        else:
            print("Dry run — skipping")

    print(f"\nTotal laws ingested: {total}")


if __name__ == "__main__":
    main()
