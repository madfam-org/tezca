#!/usr/bin/env python3
"""
Bulk State Law Scraper

Scrapes all legislative laws from all 32 Mexican states via OJN.

This script can run for hours without AI/computational credits.
Outputs progress to both console and log file.
"""

import json
from pathlib import Path
from ojn_scraper import OJNScraper
from datetime import datetime
import sys

def main():
    # Load state registry
    registry_path = Path("data/state_registry.json")
    with open(registry_path, 'r', encoding='utf-8') as f:
        registry = json.load(f)
    
    states = registry['states']
    
    # Setup logging
    log_file = Path("data/state_laws/scraping_log.txt")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log(message):
        """Log to both console and file"""
        print(message)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - {message}\n")
    
    # Initialize scraper
    scraper = OJNScraper(output_dir="data/state_laws")
    
    # Overall statistics
    total_stats = {
        'states_completed': 0,
        'states_failed': 0,
        'total_laws_found': 0,
        'total_laws_downloaded': 0,
        'total_laws_failed': 0,
        'start_time': datetime.now().isoformat(),
        'state_results': []
    }
    
    log("="*80)
    log("🚀 BULK STATE LAW SCRAPING - STARTING")
    log(f"Total states to scrape: {len(states)}")
    log(f"Start time: {total_stats['start_time']}")
    log("="*80)
    
    # Scrape each state
    for i, state in enumerate(states, 1):
        state_id = state['id']
        state_name = state['name']
        
        log(f"\n[{i}/{len(states)}] Starting state: {state_name} (ID: {state_id})")
        
        try:
            # Scrape state (no limit = all laws)
            results = scraper.scrape_state(state_id, state_name, limit=None)
            
            # Update statistics
            total_stats['states_completed'] += 1
            total_stats['total_laws_found'] += results['total_found']
            total_stats['total_laws_downloaded'] += results['successful']
            total_stats['total_laws_failed'] += results['failed']
            
            # Store state result
            total_stats['state_results'].append({
                'state_id': state_id,
                'state_name': state_name,
                'found': results['total_found'],
                'downloaded': results['successful'],
                'failed': results['failed'],
                'success_rate': f"{results['successful']/results['total_found']*100:.1f}%" if results['total_found'] > 0 else "0%"
            })
            
            log(f"✅ {state_name} complete: {results['successful']}/{results['total_found']} laws")
            
        except Exception as e:
            log(f"❌ {state_name} FAILED with error: {e}")
            total_stats['states_failed'] += 1
            total_stats['state_results'].append({
                'state_id': state_id,
                'state_name': state_name,
                'error': str(e)
            })
        
        # Save progress after each state
        progress_file = Path("data/state_laws/scraping_progress.json")
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(total_stats, f, indent=2, ensure_ascii=False)
    
    # Final summary
    total_stats['end_time'] = datetime.now().isoformat()
    
    log("\n" + "="*80)
    log("🎉 BULK SCRAPING COMPLETE!")
    log("="*80)
    log(f"States completed: {total_stats['states_completed']}/{len(states)}")
    log(f"States failed: {total_stats['states_failed']}")
    log(f"Total laws found: {total_stats['total_laws_found']}")
    log(f"Total laws downloaded: {total_stats['total_laws_downloaded']}")
    log(f"Total laws failed: {total_stats['total_laws_failed']}")
    log(f"Overall success rate: {total_stats['total_laws_downloaded']/total_stats['total_laws_found']*100:.1f}%")
    log(f"End time: {total_stats['end_time']}")
    log("="*80)
    
    # Save final summary
    summary_file = Path("data/state_laws/scraping_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(total_stats, f, indent=2, ensure_ascii=False)
    
    log(f"\n📊 Full summary saved to: {summary_file}")
    log(f"📝 Log saved to: {log_file}")

if __name__ == "__main__":
    main()
