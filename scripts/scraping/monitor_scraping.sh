#!/bin/bash
# Monitor overnight scraping progress

echo "=== Bulk State Scraping Monitor ==="
echo ""

# Check if process is running
if ps aux | grep -q "[b]ulk_state_scraper"; then
    echo "✅ Scraper is RUNNING"
    PID=$(ps aux | grep "[b]ulk_state_scraper" | awk '{print $2}')
    echo "   PID: $PID"
else
    echo "❌ Scraper is NOT running"
fi

echo ""
echo "=== Progress Summary ==="

# Check progress file
if [ -f "../../data/state_laws/scraping_progress.json" ]; then
    python3 -c "
import json
with open('../../data/state_laws/scraping_progress.json') as f:
    data = json.load(f)
    print(f\"States completed: {data.get('states_completed', 0)}/32\")
    print(f\"Laws found: {data.get('total_laws_found', 0)}\")
    print(f\"Laws downloaded: {data.get('total_laws_downloaded', 0)}\")
    print(f\"Success rate: {data['total_laws_downloaded']/data['total_laws_found']*100:.1f}%\" if data.get('total_laws_found', 0) > 0 else '')
    
    if 'state_results' in data and len(data['state_results']) > 0:
        print(f\"\nLast completed: {data['state_results'][-1]['state_name']}\")
"
else
    echo "No progress file yet - scraping just started"
fi

echo ""
echo "=== Recent Log Entries ==="
if [ -f "../../data/state_laws/scraping_log.txt" ]; then
    tail -20 ../../data/state_laws/scraping_log.txt
else
    echo "No log file yet"
fi
