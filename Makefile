.PHONY: help up down restart status logs clean test dev build lint format test-all test-pytest test-vitest test-e2e

# Default target
help:
	@echo "🇲🇽 Leyes Como Código - Management Toolkit"
	@echo ""
	@echo "Available commands:"
	@echo "  make up           - Start all services (Docker + Next.js)"
	@echo "  make down         - Stop all services"
	@echo "  make restart      - Restart all services"
	@echo "  make status       - Show status of all services"
	@echo "  make logs         - Show logs from all services"
	@echo "  make clean        - Clean up containers, volumes, and build artifacts"
	@echo "  make dev          - Start development environment"
	@echo "  make build        - Build Docker images"
	@echo "  make test         - Run pytest suite"
	@echo "  make test-all     - Run all tests (vitest + pytest + e2e)"
	@echo "  make test-pytest  - Run Python tests only"
	@echo "  make test-vitest  - Run Vitest frontend tests only"
	@echo "  make test-e2e     - Run Playwright E2E tests only"
	@echo "  make lint         - Run all linters"
	@echo "  make format       - Auto-format code"
	@echo "  make ingest       - Run law ingestion pipeline"
	@echo "  make viewer       - Open law viewer in browser"
	@echo ""

# Start all services
up:
	@echo "🚀 Starting all services..."
	@docker-compose up -d
	@echo "✅ Docker services started"
	@echo "🌐 Starting Next.js development server..."
	@cd apps/web && npm install && npm run dev &
	@echo "✅ All services running!"
	@echo ""
	@echo "📍 Access points:"
	@echo "   - Law Viewer: http://localhost:3000"
	@echo "   - API: http://localhost:8000"
	@echo ""

# Stop all services
down:
	@echo "🛑 Stopping all services..."
	@docker-compose down
	@pkill -f "next dev" || true
	@echo "✅ All services stopped"

# Restart all services
restart: down up

# Show status of all services
status:
	@echo "📊 Service Status"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Docker Containers:"
	@docker-compose ps || echo "No containers running"
	@echo ""
	@echo "Next.js Process:"
	@pgrep -f "next dev" > /dev/null && echo "✅ Running (PID: $$(pgrep -f 'next dev'))" || echo "❌ Not running"
	@echo ""
	@echo "Port Usage:"
	@lsof -i :3000 -i :8000 | grep LISTEN || echo "No ports in use"

# Show logs from all services
logs:
	@echo "📜 Service Logs (Ctrl+C to exit)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@docker-compose logs -f

# Clean up everything
clean:
	@echo "🧹 Cleaning up..."
	@docker-compose down -v
	@rm -rf apps/web/.next
	@rm -rf apps/admin/.next
	@rm -rf apps/web/node_modules/.cache
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf .coverage
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

# Development mode (Docker + Next.js with hot reload)
dev:
	@echo "🔧 Starting development environment..."
	@docker-compose up -d
	@cd apps/web && npm install
	@echo "✅ Backend started"
	@echo "🌐 Starting Next.js dev server..."
	@cd apps/web && npm run dev

# Build Docker images
build:
	@echo "🏗️  Building Docker images..."
	@docker-compose build
	@echo "✅ Build complete"

# ── Testing ────────────────────────────────────────────────────────────

# Run Python tests (default test target)
test: test-pytest

# Run all tests sequentially: vitest → pytest → e2e
test-all:
	@echo "🧪 Running full test suite..."
	@echo ""
	@echo "── Vitest (frontend) ──"
	@npx vitest run || echo "⚠️  Vitest tests failed"
	@echo ""
	@echo "── Pytest (backend) ──"
	@python -m pytest tests/ -v --cov=apps --cov-report=term || echo "⚠️  Pytest tests failed"
	@echo ""
	@echo "── Playwright (E2E) ──"
	@npx playwright test || echo "⚠️  E2E tests failed"
	@echo ""
	@echo "✅ Full test suite complete"

# Python tests only
test-pytest:
	@echo "🧪 Running Python tests..."
	@python -m pytest tests/ -v --cov=apps --cov-report=html --cov-report=term
	@echo "✅ Tests complete"
	@echo "📊 Coverage report: htmlcov/index.html"

# Vitest frontend tests only
test-vitest:
	@echo "🧪 Running Vitest tests..."
	@npx vitest run
	@echo "✅ Vitest complete"

# Playwright E2E tests only
test-e2e:
	@echo "🧪 Running E2E tests..."
	@npx playwright test
	@echo "✅ E2E tests complete"

# ── Linting & Formatting ──────────────────────────────────────────────

# Run all linters
# Aligned with CI: pyproject.toml + .github/workflows/ci.yml use black + isort
# (not ruff). Keep this make target consistent so local pre-PR checks match
# what the pipeline will enforce.
lint:
	@echo "🔍 Running linters..."
	@echo ""
	@echo "── Python (black --check) ──"
	@poetry run black --check apps/ tests/ scripts/ || echo "⚠️  black found issues"
	@echo ""
	@echo "── Python (isort --check-only) ──"
	@poetry run isort --check-only apps/ tests/ scripts/ || echo "⚠️  isort found issues"
	@echo ""
	@echo "── TypeScript (eslint) ──"
	@npm run lint:web || echo "⚠️  Web lint failed"
	@npm run lint:admin || echo "⚠️  Admin lint failed"
	@echo ""
	@echo "✅ Lint complete"

# Auto-format code
format:
	@echo "🎨 Formatting code..."
	@echo ""
	@echo "── Python (black + isort) ──"
	@poetry run black apps/ tests/ scripts/
	@poetry run isort apps/ tests/ scripts/
	@echo ""
	@echo "✅ Format complete"

# ── Data Operations ───────────────────────────────────────────────────

# Run law ingestion
ingest:
	@echo "📚 Running law ingestion pipeline..."
	@python scripts/ingestion/bulk_ingest.py --all --workers 8
	@echo "✅ Ingestion complete"

# Open law viewer in browser
viewer:
	@echo "🌐 Opening law viewer..."
	@open http://localhost:3000/laws || xdg-open http://localhost:3000/laws || echo "Please open http://localhost:3000/laws in your browser"

# Quick start (install dependencies + start everything)
quickstart:
	@echo "⚡ Quick start..."
	@echo "📦 Installing Python dependencies..."
	@pip install -r requirements.txt || poetry install
	@echo "📦 Installing Next.js dependencies..."
	@cd apps/web && npm install
	@echo "🚀 Starting services..."
	@make up
	@echo ""
	@echo "✅ System ready!"
	@echo "📍 Law Viewer: http://localhost:3000/laws"

# Health check
health:
	@echo "🏥 System Health Check"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Docker:"
	@docker --version
	@docker-compose --version || echo "⚠️  docker-compose not found"
	@echo ""
	@echo "Python:"
	@python --version
	@echo ""
	@echo "Node.js:"
	@node --version
	@echo ""
	@echo "NPM:"
	@npm --version
	@echo ""
	@echo "Services:"
	@make status

# Database operations
db-shell:
	@docker-compose exec db psql -U postgres leyes_db || echo "Database not running"

# API shell
api-shell:
	@docker-compose exec api /bin/bash || echo "API container not running"
