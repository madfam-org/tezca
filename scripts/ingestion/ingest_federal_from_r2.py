#!/usr/bin/env python3
"""
Ingest federal laws from R2 storage into PostgreSQL.

Reads law_registry.json and discovered_reglamentos.json from R2,
creates Law + LawVersion records using existing XML files in R2.

Usage (on production pod):
    PYTHONPATH=/tmp/pylibs:$PYTHONPATH python scripts/ingestion/ingest_federal_from_r2.py
    PYTHONPATH=/tmp/pylibs:$PYTHONPATH python scripts/ingestion/ingest_federal_from_r2.py --reglamentos
    PYTHONPATH=/tmp/pylibs:$PYTHONPATH python scripts/ingestion/ingest_federal_from_r2.py --all
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.indigo.settings")

import django

django.setup()

import boto3
from django.utils.dateparse import parse_date

from apps.api.models import Law, LawVersion
from apps.api.storage import get_storage_backend


def list_r2_keys(prefix="federal/"):
    """List all keys in R2 with given prefix (single API call per 1000)."""
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    keys = set()
    token = None
    while True:
        kwargs = {"Bucket": os.environ["R2_BUCKET_NAME"], "Prefix": prefix, "MaxKeys": 1000}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            keys.add(obj["Key"])
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return keys


def ingest_laws(metadata_list, r2_keys, dry_run=False, label="federal"):
    """Ingest a list of law metadata dicts into the DB."""
    created = 0
    updated = 0
    errors = 0

    for i, meta in enumerate(metadata_list, 1):
        law_id = meta.get("id", meta.get("official_id", "unknown"))
        name = meta.get("name", meta.get("law_name", "Unknown"))

        try:
            # Determine XML path in R2 (use pre-fetched key set)
            xml_key = None
            for candidate in [
                f"federal/mx-fed-{law_id}-v2.xml",
                f"federal/{law_id}-v2.xml",
                f"federal/{law_id}.xml",
            ]:
                if candidate in r2_keys:
                    xml_key = candidate
                    break

            if dry_run:
                print(f"  [{i}] {law_id}: {name[:60]} (xml={'YES' if xml_key else 'NONE'})")
                continue

            # Get or create Law — always "federal" tier for this script
            tier = "federal"
            category = meta.get("category", "")
            short_name = meta.get("short_name", name)[:200]
            law_type = meta.get("law_type", "")
            source_url = meta.get("url", "") or meta.get("source_url", "") or ""

            defaults = {
                "name": name,
                "short_name": short_name,
                "category": category,
                "tier": tier,
                "source_url": source_url,
            }
            if law_type:
                defaults["law_type"] = law_type

            law, law_created = Law.objects.get_or_create(
                official_id=law_id,
                defaults=defaults,
            )

            if not law_created:
                law.name = name
                law.short_name = short_name
                law.category = category
                law.tier = tier
                law.save()
                updated += 1
            else:
                created += 1

            # Create LawVersion
            pub_date_str = meta.get("publication_date", "")
            if pub_date_str and pub_date_str != "1900-01-01":
                pub_date = parse_date(pub_date_str)
            else:
                pub_date = None

            if pub_date and xml_key:
                LawVersion.objects.get_or_create(
                    law=law,
                    publication_date=pub_date,
                    defaults={
                        "xml_file_path": xml_key,
                        "dof_url": meta.get("url", "") or "",
                    },
                )

        except Exception as e:
            errors += 1
            print(f"  ERROR [{i}] {law_id}: {e}")

        if i % 50 == 0:
            print(f"  [{i}/{len(metadata_list)}] created={created} updated={updated} errors={errors}")

    print(f"\n{label} ingestion complete:")
    print(f"  Created: {created}")
    print(f"  Updated: {updated}")
    print(f"  Errors: {errors}")
    return created + updated


def main():
    parser = argparse.ArgumentParser(description="Ingest federal laws from R2")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--laws", action="store_true", default=True, help="Ingest federal laws (default)")
    group.add_argument("--reglamentos", action="store_true", help="Ingest reglamentos only")
    group.add_argument("--all", action="store_true", help="Ingest both laws and reglamentos")
    parser.add_argument("--dry-run", action="store_true", help="List what would be ingested")
    args = parser.parse_args()

    storage = get_storage_backend()

    # Pre-fetch all federal/ keys from R2 (avoids per-law HEAD requests)
    print("Listing federal/ keys in R2...")
    r2_keys = list_r2_keys("federal/")
    print(f"Found {len(r2_keys)} files in federal/")

    total = 0

    if args.all or (not args.reglamentos):
        # Federal laws from law_registry.json
        print("\nLoading law_registry.json from R2...")
        content = storage.get("law_registry.json")
        if not content:
            print("ERROR: law_registry.json not found in R2")
            sys.exit(1)
        registry = json.loads(content)
        if isinstance(registry, list):
            laws = registry
        elif isinstance(registry, dict):
            laws = registry.get("federal_laws", registry.get("laws", []))
        else:
            laws = []
        print(f"Found {len(laws)} federal laws")
        total += ingest_laws(laws, r2_keys, args.dry_run, label="Federal laws")

    if args.all or args.reglamentos:
        # Reglamentos from discovered_reglamentos.json
        print("\nLoading discovered_reglamentos.json from R2...")
        content = storage.get("discovered_reglamentos.json")
        if not content:
            print("ERROR: discovered_reglamentos.json not found in R2")
            sys.exit(1)
        reglamentos = json.loads(content)
        if isinstance(reglamentos, dict):
            reglamentos = reglamentos.get("reglamentos", reglamentos.get("laws", []))
        print(f"Found {len(reglamentos)} reglamentos")

        # Normalize reglamento metadata
        normalized = []
        for r in reglamentos:
            normalized.append({
                "id": r.get("id", r.get("official_id", "")),
                "name": r.get("name", r.get("law_name", "")),
                "short_name": r.get("short_name", r.get("name", "")),
                "category": r.get("category", "Reglamento"),
                "tier": "federal",
                "law_type": "reglamento",
                "publication_date": r.get("publication_date", ""),
                "url": r.get("url", r.get("source_url", "")),
            })
        total += ingest_laws(normalized, r2_keys, args.dry_run, label="Reglamentos")

    print(f"\nTotal laws ingested: {total}")


if __name__ == "__main__":
    main()
