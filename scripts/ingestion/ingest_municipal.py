#!/usr/bin/env python3
"""
Municipal Law Ingestion Script

Bulk ingest laws from municipal scrapers.
Bridge between MunicipalScraper framework and IngestionPipeline.

Usage:
    python scripts/ingestion/ingest_municipal.py --all
    python scripts/ingestion/ingest_municipal.py --muni guadalajara
    python scripts/ingestion/ingest_municipal.py --all --dry-run
    python scripts/ingestion/ingest_municipal.py --all --limit 5
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.scraper.municipal import get_scraper, list_available_scrapers
from apps.parsers.pipeline import IngestionPipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_municipality(muni_id: str, dry_run: bool = False, limit: int = 0):
    """
    Run ingestion for a single municipality.
    """
    print(f"\n🏙️  Processing: {muni_id.upper()}")
    
    try:
        scraper = get_scraper(muni_id)
    except Exception as e:
        print(f"❌ Failed to load scraper: {e}")
        return

    # 1. Scrape Catalog
    print("   🔍 Scraping catalog...")
    try:
        results = scraper.scrape_catalog()
        # run() typically returns a list of law metadata dicts
        # Expected keys: name, url, date, category, tags
    except Exception as e:
        print(f"   ❌ Scraper failed: {e}")
        return

    if not results:
        print("   ⚠️  No laws found in catalog.")
        return

    print(f"   ✅ Found {len(results)} items.")

    if limit > 0:
        results = results[:limit]
        print(f"   Note: Limiting to top {limit} items.")

    if dry_run:
        print("   [Dry Run] Listing first 3 items:")
        for law in results[:3]:
            print(f"    - {law.get('name')} ({law.get('date')}) -> {law.get('url')}")
        return

    # 2. Ingest Laws
    pipeline = IngestionPipeline()
    success_count = 0
    
    for law in results:
        law_name = law.get('name', 'Unknown')
        print(f"   📥 Ingesting: {law_name[:50]}...")
        
        try:
            # Generate ID if missing
            if 'id' not in law:
                # Generate a temporary ID slug
                slug = law_name.lower().replace(' ', '-').replace('.', '')[:50]
                law['id'] = f"mun-{muni_id}-{slug}"
            
            # Prepare metadata for pipeline
            law_metadata = {
                'id': law['id'],
                'name': law_name,
                'short_name': law_name,
                'url': law.get('url'),
                'publication_date': law.get('date', '2024-01-01'), # Default fallback
                'slug': law['id'],
                'type': 'reglamento', # Default for municipal
                'municipality': muni_id,
                'expected_articles': 0 # not known upfront
            }
            
            # Run Pipeline
            result = pipeline.ingest_law(law_metadata)
            
            # Output result
            print(f"     {result.summary()}")
            
            if result.success:
                success_count += 1
            
        except Exception as e:
            print(f"     ❌ Critical Failure: {e}")

    print(f"   🏁 Completed {muni_id}: {success_count}/{len(results)} ingested.")

def main():
    parser = argparse.ArgumentParser(description='Municipal Ingestion')
    parser.add_argument('--all', action='store_true', help='Process all implemented municipalities')
    parser.add_argument('--muni', type=str, help='Specific municipality ID')
    parser.add_argument('--dry-run', action='store_true', help='Scrape catalog only, do not download files')
    parser.add_argument('--limit', type=int, default=0, help='Limit items per municipality')
    
    args = parser.parse_args()

    if args.all:
        # Get list of implemented scrapers
        implemented = [
            m for m, status in list_available_scrapers().items() 
            if status in ['implemented', 'partial']
        ]
        for muni in implemented:
            ingest_municipality(muni, args.dry_run, args.limit)

    elif args.muni:
        ingest_municipality(args.muni, args.dry_run, args.limit)
    else:
        print("Please specify --all or --muni <id>")
        sys.exit(1)

if __name__ == "__main__":
    main()
