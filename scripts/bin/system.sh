#!/bin/bash
# System control script for Leyes Como Código
# Usage: ./scripts/system.sh [start|stop|restart|status]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

start_system() {
    log_info "Starting Leyes Como Código system..."
    
    # Start Docker services
    log_info "Starting Docker containers..."
    docker-compose up -d
    
    # Wait for services to be ready
    sleep 2
    
    # Start Next.js
    log_info "Starting Next.js development server..."
    cd apps/web
    npm install > /dev/null 2>&1 || log_warn "npm install had warnings"
    npm run dev > "$PROJECT_ROOT/logs/nextjs.log" 2>&1 &
    NEXTJS_PID=$!
    echo $NEXTJS_PID > "$PROJECT_ROOT/.nextjs.pid"
    cd "$PROJECT_ROOT"
    
    log_success "System started successfully!"
    echo ""
    echo "📍 Access Points:"
    echo "   🌐 Law Viewer: http://localhost:3000/laws"
    echo "   🔧 API: http://localhost:8000"
    echo "   📊 Tax Calculator: http://localhost:3000"
    echo ""
    echo "Logs:"
    echo "   Next.js: tail -f logs/nextjs.log"
    echo "   Docker: docker-compose logs -f"
}

stop_system() {
    log_info "Stopping Leyes Como Código system..."
    
    # Stop Next.js
    if [ -f .nextjs.pid ]; then
        NEXTJS_PID=$(cat .nextjs.pid)
        if ps -p $NEXTJS_PID > /dev/null 2>&1; then
            log_info "Stopping Next.js (PID: $NEXTJS_PID)..."
            kill $NEXTJS_PID
        fi
        rm .nextjs.pid
    fi
    
    # Stop all node processes (Next.js dev server)
    pkill -f "next dev" || true
    
    # Stop Docker services
    log_info "Stopping Docker containers..."
    docker-compose down
    
    log_success "System stopped successfully!"
}

restart_system() {
    log_info "Restarting system..."
    stop_system
    sleep 1
    start_system
}

status_system() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 Leyes Como Código - System Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    echo "Docker Containers:"
    docker-compose ps || log_warn "No Docker containers running"
    echo ""
    
    echo "Next.js Development Server:"
    if pgrep -f "next dev" > /dev/null; then
        NEXTJS_PID=$(pgrep -f "next dev")
        log_success "Running (PID: $NEXTJS_PID)"
    else
        log_error "Not running"
    fi
    echo ""
    
    echo "Port Usage:"
    echo "  Port 3000 (Next.js):"
    lsof -i :3000 | grep LISTEN || echo "    Not in use"
    echo "  Port 8000 (API):"
    lsof -i :8000 | grep LISTEN || echo "    Not in use"
    echo ""
    
    echo "System Resources:"
    echo "  Docker Disk Usage:"
    docker system df --format "table {{.Type}}\t{{.Size}}\t{{.Reclaimable}}" 2>/dev/null || echo "    Cannot determine"
    echo ""
}

# Create logs directory if it doesn't exist
mkdir -p logs

# Main command handler
case "${1:-}" in
    start)
        start_system
        ;;
    stop)
        stop_system
        ;;
    restart)
        restart_system
        ;;
    status)
        status_system
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        echo ""
        echo "System Control Script for Leyes Como Código"
        echo ""
        echo "Commands:"
        echo "  start   - Start all services (Docker + Next.js)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  status  - Show current system status"
        exit 1
        ;;
esac
