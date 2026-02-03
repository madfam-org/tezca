#!/usr/bin/env python3
"""
Ingestion status dashboard - View recent runs and quality trends.

Usage:
    python scripts/ingestion_status.py
    python scripts/ingestion_status.py --last 10
    python scripts/ingestion_status.py --law amparo
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import sys

# Add apps to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'apps'))


def load_quality_history(history_file: Path) -> List[Dict]:
    """Load quality history from JSON file."""
    if not history_file.exists():
        return []
    
    try:
        with open(history_file, 'r') as f:
            data = json.load(f)
        return data.get('records', [])
    except Exception:
        return []


def load_error_log(error_file: Path) -> List[Dict]:
    """Load error log from JSON lines file."""
    if not error_file.exists():
        return []
    
    errors = []
    try:
        with open(error_file, 'r') as f:
            for line in f:
                if line.strip():
                    errors.append(json.loads(line))
    except Exception:
        pass
    
    return errors


def filter_by_timeframe(records: List[Dict], hours: int = 24) -> List[Dict]:
    """Filter records within timeframe."""
    cutoff = datetime.now() - timedelta(hours=hours)
    
    filtered = []
    for record in records:
        try:
            record_time = datetime.fromisoformat(record['timestamp'])
            if record_time >= cutoff:
                filtered.append(record)
        except Exception:
            continue
    
    return filtered


def get_grade_distribution(records: List[Dict]) -> Dict[str, int]:
    """Get distribution of grades."""
    distribution = {}
    for record in records:
        grade = record.get('grade', 'N/A')
        distribution[grade] = distribution.get(grade, 0) + 1
    return distribution


def get_average_metrics(records: List[Dict]) -> Dict[str, float]:
    """Calculate average scores."""
    if not records:
        return {}
    
    total_accuracy = sum(r.get('accuracy', 0) for r in records)
    total_completeness = sum(r.get('completeness', 0) for r in records)
    total_overall = sum(r.get('overall', 0) for r in records)
    
    count = len(records)
    
    return {
        'accuracy': total_accuracy / count,
        'completeness': total_completeness / count,
        'overall': total_overall / count
    }


def print_dashboard(records: List[Dict], errors: List[Dict], timeframe: int = 24):
    """Print formatted dashboard."""
    
    print("=" * 70)
    print("INGESTION DASHBOARD")
    print("=" * 70)
    
    print(f"\nLast {timeframe} hours:")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not records:
        print("\n⚠️  No ingestion records found")
        print("=" * 70)
        return
    
    # Overall stats
    total_laws = len(set(r['law_id'] for r in records))
    success_rate = sum(1 for r in records if r.get('grade') not in ['F', 'N/A']) / len(records) * 100
    
    print(f"\nTotal runs: {len(records)}")
    print(f"Unique laws: {total_laws}")
    print(f"Success rate: {success_rate:.1f}%")
    
    # Average metrics
    avg_metrics = get_average_metrics(records)
    if avg_metrics:
        print(f"\nAverage quality:")
        print(f"  Accuracy:     {avg_metrics['accuracy']:.1f}%")
        print(f"  Completeness: {avg_metrics['completeness']:.1f}%")
        print(f"  Overall:      {avg_metrics['overall']:.1f}%")
    
    # Grade distribution
    grades = get_grade_distribution(records)
    print(f"\nGrade distribution:")
    for grade in ['A', 'B', 'C', 'D', 'F']:
        count = grades.get(grade, 0)
        if count > 0:
            pct = count / len(records) * 100
            print(f"  {grade}: {count} ({pct:.1f}%)")
    
    # Recent runs (last 5)
    print(f"\nRecent runs:")
    for record in sorted(records, key=lambda r: r['timestamp'], reverse=True)[:5]:
        timestamp = datetime.fromisoformat(record['timestamp']).strftime('%m-%d %H:%M')
        law_id = record['law_id']
        grade = record.get('grade', 'N/A')
        overall = record.get('overall', 0)
        print(f"  {timestamp} - {law_id:10} - Grade {grade} ({overall:.1f}%)")
    
    # Errors
    if errors:
        print(f"\nRecent errors ({len(errors)}):")
        error_by_category = {}
        for error in errors:
            cat = error.get('category', 'UNKNOWN')
            error_by_category[cat] = error_by_category.get(cat, 0) + 1
        
        for category, count in sorted(error_by_category.items()):
            print(f"  {category}: {count}")
    
    print("\n" + "=" * 70)


def print_law_detail(law_id: str, records: List[Dict]):
    """Print detailed history for a specific law."""
    
    law_records = [r for r in records if r['law_id'] == law_id]
    
    if not law_records:
        print(f"No records found for law: {law_id}")
        return
    
    print("=" * 70)
    print(f"LAW DETAIL: {law_id}")
    print("=" * 70)
    
    print(f"\nTotal runs: {len(law_records)}")
    
    # Sort by timestamp
    law_records.sort(key=lambda r: r['timestamp'])
    
    print(f"\nHistory:")
    for i, record in enumerate(law_records, 1):
        timestamp = datetime.fromisoformat(record['timestamp']).strftime('%Y-%m-%d %H:%M')
        grade = record.get('grade', 'N/A')
        overall = record.get('overall', 0)
        accuracy = record.get('accuracy', 0)
        completeness = record.get('completeness', 0)
        
        print(f"\n  Run {i} - {timestamp}")
        print(f"    Grade: {grade} ({overall:.1f}%)")
        print(f"    Accuracy: {accuracy:.1f}%")
        print(f"    Completeness: {completeness:.1f}%")
    
    # Trend
    if len(law_records) >= 2:
        first = law_records[0]['overall']
        last = law_records[-1]['overall']
        diff = last - first
        
        if diff > 0:
            print(f"\n  📈 Quality improved: +{diff:.1f}%")
        elif diff < 0:
            print(f"\n  📉 Quality degraded: {diff:.1f}%")
        else:
            print(f"\n  ➡️  Quality stable")
    
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='View ingestion status and quality trends'
    )
    
    parser.add_argument('--last', type=int, default=24,
                       help='Hours to look back (default: 24)')
    parser.add_argument('--law', type=str,
                       help='Show detail for specific law ID')
    
    args = parser.parse_args()
    
    # Load data
    data_dir = Path('data')
    quality_file = data_dir / 'quality_history.json'
    error_file = data_dir / 'logs' / 'errors.log'
    
    records = load_quality_history(quality_file)
    errors = load_error_log(error_file)
    
    # Filter by timeframe
    records = filter_by_timeframe(records, args.last)
    errors = filter_by_timeframe(errors, args.last)
    
    # Show dashboard or law detail
    if args.law:
        print_law_detail(args.law, records)
    else:
        print_dashboard(records, errors, args.last)


if __name__ == "__main__":
    main()
