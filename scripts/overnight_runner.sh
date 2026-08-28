#!/bin/bash
# =============================================================================
# Overnight Data Acquisition Runner
# =============================================================================
# Runs the full data motor sequentially:
#   Phase A: Smart retry on existing state legislative failures (~1-2h)
#   Phase B: Bulk non-legislative scrape (OJN Poderes 1/3/4) (~12-24h)
#   Phase C: Consolidate non-legislative metadata (~30s)
#   Phase D: Ingest into database (~10 min)
#   Phase E: Index in Elasticsearch (~30 min)
#
# Usage:
#   ./scripts/overnight_runner.sh              # Full run
#   ./scripts/overnight_runner.sh --skip-retry  # Skip smart retry
#   ./scripts/overnight_runner.sh --post-only   # Only post-processing (C/D/E)
#
# Monitor:
#   tail -f data/logs/overnight_YYYYMMDD.log
# =============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

DATE=$(date +%Y%m%d)
LOG_DIR="$PROJECT_ROOT/data/logs"
LOG_FILE="$LOG_DIR/overnight_${DATE}.log"

mkdir -p "$LOG_DIR"

SKIP_RETRY=false
POST_ONLY=false

for arg in "$@"; do
    case $arg in
        --skip-retry) SKIP_RETRY=true ;;
        --post-only) POST_ONLY=true ;;
    esac
done

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a "$LOG_FILE"
}

log_section() {
    log "================================================================"
    log "$1"
    log "================================================================"
}

# Track timing
START_TIME=$(date +%s)

log_section "OVERNIGHT DATA ACQUISITION - START"
log "Project root: $PROJECT_ROOT"
log "Log file: $LOG_FILE"
log "Skip retry: $SKIP_RETRY"
log "Post-only: $POST_ONLY"

if [ "$POST_ONLY" = false ]; then

    # =========================================================================
    # Phase A: Smart Retry (existing legislative failures)
    # =========================================================================
    if [ "$SKIP_RETRY" = false ]; then
        log_section "PHASE A: Smart Retry (legislative failures)"

        if [ -f "$PROJECT_ROOT/scripts/scraping/smart_retry.py" ]; then
            cd "$PROJECT_ROOT/scripts/scraping"
            log "Starting smart_retry.py..."
            python smart_retry.py >> "$LOG_FILE" 2>&1 || {
                log "WARNING: Smart retry exited with error (continuing anyway)"
            }
            cd "$PROJECT_ROOT"
            log "Phase A complete."
        else
            log "WARNING: smart_retry.py not found, skipping Phase A"
        fi
    else
        log "Phase A skipped (--skip-retry)"
    fi

    # =========================================================================
    # Phase B: Bulk Non-Legislative Scrape (OJN Poderes 1/3/4)
    # =========================================================================
    log_section "PHASE B: Bulk Non-Legislative Scrape"

    cd "$PROJECT_ROOT/scripts/scraping"
    log "Starting bulk_non_legislative_scraper.py --resume..."
    log "Expected: ~23,660 laws across 32 states (12-24h)"

    python bulk_non_legislative_scraper.py --resume >> "$LOG_FILE" 2>&1 || {
        log "WARNING: Bulk scraper exited with error (attempting post-processing anyway)"
    }
    cd "$PROJECT_ROOT"

    SCRAPE_END=$(date +%s)
    SCRAPE_DURATION=$(( (SCRAPE_END - START_TIME) / 60 ))
    log "Phase B complete. Scraping took ${SCRAPE_DURATION} minutes."

fi  # end of POST_ONLY check

# =========================================================================
# Phase C: Consolidate Non-Legislative Metadata
# =========================================================================
log_section "PHASE C: Consolidate Metadata"

NL_DIR="$PROJECT_ROOT/data/state_laws_non_legislative"
if [ -d "$NL_DIR" ] && [ "$(ls -A "$NL_DIR" 2>/dev/null)" ]; then
    cd "$PROJECT_ROOT/scripts/scraping"
    log "Running consolidate_non_legislative_metadata.py..."
    python consolidate_non_legislative_metadata.py >> "$LOG_FILE" 2>&1 || {
        log "ERROR: Consolidation failed"
        exit 1
    }
    cd "$PROJECT_ROOT"
    log "Phase C complete."
else
    log "ERROR: No data in $NL_DIR - nothing to consolidate"
    exit 1
fi

# =========================================================================
# Phase D: Ingest into Database
# =========================================================================
log_section "PHASE D: Database Ingestion"

METADATA_FILE="$PROJECT_ROOT/data/state_laws_non_legislative_metadata.json"
if [ -f "$METADATA_FILE" ]; then
    log "Running ingest_non_legislative_laws --all..."
    python manage.py ingest_non_legislative_laws --all >> "$LOG_FILE" 2>&1 || {
        log "ERROR: Ingestion failed"
        exit 1
    }
    log "Phase D complete."
else
    log "ERROR: Metadata file not found: $METADATA_FILE"
    exit 1
fi

# =========================================================================
# Phase E: Elasticsearch Indexing
# =========================================================================
log_section "PHASE E: Elasticsearch Indexing"

log "Running index_laws --all --tier state..."
python manage.py index_laws --all --tier state --create-indices >> "$LOG_FILE" 2>&1 || {
    log "WARNING: ES indexing failed (DB ingestion still succeeded)"
}
log "Phase E complete."

# =========================================================================
# Final Summary
# =========================================================================
END_TIME=$(date +%s)
TOTAL_DURATION=$(( (END_TIME - START_TIME) / 60 ))

log_section "OVERNIGHT RUN COMPLETE"
log "Total duration: ${TOTAL_DURATION} minutes ($(( TOTAL_DURATION / 60 ))h $(( TOTAL_DURATION % 60 ))m)"

# Print law count if Django is available
python manage.py shell -c "
from apps.api.models import Law
total = Law.objects.count()
state = Law.objects.filter(tier='state').count()
print(f'DB law count: {total} total, {state} state')
" >> "$LOG_FILE" 2>&1 || true

log "Check progress:"
log "  cat $NL_DIR/scraping_progress.json | python -m json.tool"
log "  tail -50 $LOG_FILE"
log "Done."
