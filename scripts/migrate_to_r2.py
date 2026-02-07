#!/usr/bin/env python
"""
Bulk upload existing local data/ directory to Cloudflare R2.

Usage:
    STORAGE_BACKEND=r2 python scripts/migrate_to_r2.py [--dry-run]

Uploads ~30GB of legal documents from local /data/ to the R2 bucket
configured via R2_* environment variables. Supports resumption —
skips keys that already exist in R2.
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Must set before importing Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.indigo.settings")


def main():
    parser = argparse.ArgumentParser(description="Migrate local data/ to Cloudflare R2")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be uploaded without actually uploading",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(PROJECT_ROOT / "data"),
        help="Local data directory to upload (default: <project>/data)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="",
        help="Only upload files under this subdirectory (e.g., 'federal/')",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        sys.exit(1)

    # Force R2 backend
    os.environ["STORAGE_BACKEND"] = "r2"

    from apps.api.storage import get_storage_backend

    storage = get_storage_backend()

    # Collect files
    search_dir = data_dir / args.prefix if args.prefix else data_dir
    if not search_dir.exists():
        print(f"Search directory not found: {search_dir}")
        sys.exit(1)

    files = sorted(p for p in search_dir.rglob("*") if p.is_file())
    total_size = sum(f.stat().st_size for f in files)
    print(f"Found {len(files)} files ({total_size / (1024**3):.2f} GB)")

    if args.dry_run:
        for f in files[:20]:
            key = str(f.relative_to(data_dir))
            size_mb = f.stat().st_size / (1024**2)
            print(f"  {key} ({size_mb:.1f} MB)")
        if len(files) > 20:
            print(f"  ... and {len(files) - 20} more files")
        print("\nDry run complete. Use without --dry-run to upload.")
        return

    # Upload with progress
    uploaded = 0
    skipped = 0
    failed = 0
    bytes_uploaded = 0
    start_time = time.time()

    for i, filepath in enumerate(files, 1):
        key = str(filepath.relative_to(data_dir))
        file_size = filepath.stat().st_size

        # Skip if already exists in R2
        if storage.exists(key):
            skipped += 1
            continue

        try:
            storage.put_file(key, filepath)
            uploaded += 1
            bytes_uploaded += file_size
        except Exception as e:
            failed += 1
            print(f"  FAILED: {key} — {e}")

        # Progress every 50 files
        if i % 50 == 0:
            elapsed = time.time() - start_time
            rate = bytes_uploaded / elapsed / (1024**2) if elapsed > 0 else 0
            print(
                f"  [{i}/{len(files)}] "
                f"uploaded={uploaded} skipped={skipped} failed={failed} "
                f"({rate:.1f} MB/s)"
            )

    elapsed = time.time() - start_time
    print(f"\nMigration complete in {elapsed:.0f}s:")
    print(f"  Uploaded: {uploaded}")
    print(f"  Skipped (already in R2): {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Total data uploaded: {bytes_uploaded / (1024**3):.2f} GB")


if __name__ == "__main__":
    main()
