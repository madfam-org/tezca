#!/usr/bin/env python3
"""
Bulk law ingestion CLI - Process multiple laws in parallel.

Usage:
    # Ingest all laws
    python scripts/bulk_ingest.py --all
    
    # Ingest by priority
    python scripts/bulk_ingest.py --priority 1
    
    # Ingest specific laws
    python scripts/bulk_ingest.py --laws amparo,iva,lft
    
    # Control parallelism
    python scripts/bulk_ingest.py --all --workers 8
    
    # Skip re-downloading PDFs
    python scripts/bulk_ingest.py --all --skip-download
"""

import argparse
import sys
from pathlib import Path
from multiprocessing import Pool
from datetime import datetime
import json

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'apps'))

from scraper.utils.law_registry import LawRegistry
from parsers.pipeline import IngestionPipeline, IngestionResult


def process_single_law(args_tuple):
    """
    Process a single law (called by worker process).
    
    Args:
        args_tuple: (law_metadata, skip_download)
    
    Returns:
        IngestionResult
    """
    law_metadata, skip_download = args_tuple
    
    # Create pipeline in worker
    pipeline = IngestionPipeline(skip_download=skip_download)
    
    # Ingest law
    result = pipeline.ingest_law(law_metadata)
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Bulk law ingestion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Law selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true',
                      help='Ingest all laws')
    group.add_argument('--priority', type=int, choices=[1, 2],
                      help='Ingest laws by priority level')
    group.add_argument('--tier', type=str,
                      help='Ingest laws by tier (e.g., fiscal, constitutional)')
    group.add_argument('--laws', type=str,
                      help='Comma-separated law IDs (e.g., amparo,iva,lft)')
    
    # Options
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of parallel workers (default: 4)')
    parser.add_argument('--skip-download', action='store_true',
                       help='Use existing PDFs, skip downloading')
    parser.add_argument('--output', type=str,
                       help='Save results to JSON file')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    # Load registry
    print("📚 Loading law registry...")
    registry = LawRegistry()
    
    # Select laws
    if args.all:
        laws = registry.all()
        selection_desc = "all laws"
    elif args.priority:
        laws = registry.filter_by_priority(args.priority)
        selection_desc = f"priority {args.priority} laws"
    elif args.tier:
        laws = registry.filter_by_tier(args.tier)
        selection_desc = f"{args.tier} laws"
    elif args.laws:
        law_ids = [lid.strip() for lid in args.laws.split(',')]
        laws = []
        for law_id in law_ids:
            law = registry.get_by_id(law_id)
            if law:
                laws.append(law)
            else:
                print(f"⚠️  Warning: Law '{law_id}' not found in registry")
        selection_desc = "selected laws"
    else:
        print("Error: Must specify --all, --priority, --tier, or --laws")
        return 1
    
    if not laws:
        print("❌ No laws found matching criteria")
        return 1
    
    # Display plan
    print(f"\n{'='*70}")
    print(f"BULK INGESTION PLAN")
    print(f"{'='*70}")
    print(f"Selection: {selection_desc}")
    print(f"Laws to process: {len(laws)}")
    print(f"Workers: {args.workers}")
    print(f"Skip download: {args.skip_download}")
    print()
    
    for law in laws:
        print(f"  • {law['id']:10} - {law.get('short_name', law.get('name', 'Unknown'))}")
    
    print(f"\n{'='*70}")
    
    # Confirm
    if len(laws) > 3 and not args.force:
        response = input(f"\nProcess {len(laws)} laws? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            return 0
    
    # Process laws
    start_time = datetime.now()
    print(f"\n🚀 Starting batch ingestion with {args.workers} workers...")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Prepare arguments for workers
    worker_args = [(law, args.skip_download) for law in laws]
    
    # Use multiprocessing pool
    if args.workers > 1:
        with Pool(processes=args.workers) as pool:
            results = pool.map(process_single_law, worker_args)
    else:
        # Single-threaded for debugging
        results = [process_single_law(arg) for arg in worker_args]
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Analyze results
    success_count = sum(1 for r in results if r.success)
    failed = [r for r in results if not r.success]
    
    # Sort results by ID for consistent display
    results.sort(key=lambda r: r.law_id)
    
    # Print summary
    print(f"\n{'='*70}")
    print("BATCH INGESTION SUMMARY")
    print(f"{'='*70}")
    print(f"Start time:   {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End time:     {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration:     {duration:.1f}s ({duration/60:.1f} min)")
    print(f"Total laws:   {len(results)}")
    print(f"Success:      {success_count} ({success_count/len(results)*100:.1f}%)")
    print(f"Failed:       {len(failed)}")
    print(f"Avg time:     {duration/len(results):.1f}s per law")
    
    # Grade distribution
    if success_count > 0:
        grades = {}
        for r in results:
            if r.success:
                grade = r.grade
                grades[grade] = grades.get(grade, 0) + 1
        
        print(f"\nGrade distribution:")
        for grade in ['A', 'B', 'C', 'D', 'F']:
            count = grades.get(grade, 0)
            if count > 0:
                print(f"  {grade}: {count}")
    
    # Individual results
    print(f"\nIndividual results:")
    for result in results:
        print(f"  {result.summary()}")
    
    # Failed laws detail
    if failed:
        print(f"\n❌ Failed laws ({len(failed)}):")
        for result in failed:
            print(f"  • {result.law_id}: {result.error}")
    
    print(f"{'='*70}")
    
    # Save results to JSON if requested
    if args.output:
        output_data = {
            'timestamp': start_time.isoformat(),
            'duration_seconds': duration,
            'total_laws': len(results),
            'success_count': success_count,
            'failed_count': len(failed),
            'results': [
                {
                    'law_id': r.law_id,
                    'law_name': r.law_name,
                    'success': r.success,
                    'error': r.error,
                    'grade': r.grade if r.success else None,
                    'duration_seconds': r.duration_seconds,
                    'xml_path': str(r.xml_path) if r.xml_path else None,
                }
                for r in results
            ]
        }
        
        output_path = Path(args.output)
        output_path.write_text(json.dumps(output_data, indent=2))
        print(f"\n💾 Results saved to: {output_path}")
    
    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
