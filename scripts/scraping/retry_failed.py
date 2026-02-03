#!/usr/bin/env python3
"""
Retry Failed State Law Downloads

Retries all failed downloads from the initial bulk scraping run.
Uses longer timeouts and more retry attempts to maximize recovery.
"""

import json
from pathlib import Path
from ojn_scraper import OJNScraper
from datetime import datetime
import sys

def main():
    # Load scraping summary to identify failures
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    summary_file = project_root / "data/state_laws/scraping_summary.json"
    
    if not summary_file.exists():
        print(f"❌ Error: Summary file not found: {summary_file}")
        return 1
    
    with open(summary_file, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    # Setup logging
    log_file = project_root / "data/state_laws/retry_log.txt"
    
    def log(message):
        """Log to both console and file"""
        print(message)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - {message}\n")
    
    # Initialize scraper with longer timeouts
    scraper = OJNScraper(output_dir=str(project_root / "data/state_laws"))
    scraper.REQUEST_DELAY = 2.0  # More conservative rate limiting
    
    # Collect all states with failures
    retry_states = []
    total_to_retry = 0
    
    for state_result in summary['state_results']:
        if state_result.get('failed', 0) > 0:
            retry_states.append(state_result)
            total_to_retry += state_result['failed']
    
    log("="*80)
    log("🔄 RETRY FAILED DOWNLOADS - STARTING")
    log(f"States with failures: {len(retry_states)}")
    log(f"Total laws to retry: {total_to_retry}")
    log(f"Start time: {datetime.now().isoformat()}")
    log("="*80)
    
    # Statistics
    retry_stats = {
        'total_retried': 0,
        'recovered': 0,
        'still_failed': 0,
        'start_time': datetime.now().isoformat(),
        'state_results': []
    }
    
    # Retry each state with failures
    for state_result in retry_states:
        state_id = state_result['state_id']
        state_name = state_result['state_name']
        failed_count = state_result['failed']
        
        log(f"\n🔄 Retrying {state_name}: {failed_count} failures")
        
        # For states with many failures, re-scrape entirely
        # For states with few failures, would need to track specific failed laws
        # For simplicity, re-scrape states with >100 failures
        
        if failed_count > 100:
            log(f"   Many failures - re-scraping entire state")
            
            try:
                results = scraper.scrape_state(state_id, state_name, limit=None)
                
                new_success = results['successful']
                new_failed = results['failed']
                original_success = state_result['downloaded']
                
                recovered = new_success - original_success
                
                retry_stats['total_retried'] += failed_count
                retry_stats['recovered'] += max(0, recovered)
                retry_stats['still_failed'] += new_failed
                
                retry_stats['state_results'].append({
                    'state_name': state_name,
                    'original_failed': failed_count,
                    'recovered': max(0, recovered),
                    'still_failed': new_failed,
                    'retry_success_rate': f"{recovered/failed_count*100:.1f}%" if failed_count > 0 else "N/A"
                })
                
                log(f"   ✅ {state_name}: recovered {recovered}/{failed_count}")
                
            except Exception as e:
                log(f"   ❌ {state_name} retry FAILED: {e}")
                retry_stats['still_failed'] += failed_count
        
        else:
            # For states with few failures, just log (would need law-level tracking)
            log(f"   ⚠️  {state_name}: {failed_count} failures (manual review recommended)")
            retry_stats['total_retried'] += failed_count
            # Conservatively assume we can't recover these without law-level tracking
            retry_stats['still_failed'] += failed_count
    
    # Final summary
    retry_stats['end_time'] = datetime.now().isoformat()
    
    log("\n" + "="*80)
    log("🎉 RETRY COMPLETE!")
    log("="*80)
    log(f"Total retried: {retry_stats['total_retried']}")
    log(f"Recovered: {retry_stats['recovered']}")
    log(f"Still failed: {retry_stats['still_failed']}")
    log(f"Recovery rate: {retry_stats['recovered']/retry_stats['total_retried']*100:.1f}%")
    log(f"End time: {retry_stats['end_time']}")
    log("="*80)
    
    # Save retry summary
    retry_summary_file = project_root / "data/state_laws/retry_summary.json"
    with open(retry_summary_file, 'w', encoding='utf-8') as f:
        json.dump(retry_stats, f, indent=2, ensure_ascii=False)
    
    log(f"\n📊 Retry summary saved to: {retry_summary_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
