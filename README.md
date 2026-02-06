# Leyes Como Código - Mexico

**The definitive digital platform for Mexican legal research** - comprehensive, machine-readable database of Mexican laws (federal, state, municipal) with intuitive interfaces for professionals and citizens.

**Coverage**: 93.9% of Legislative Laws (11,904 of 12,456) — [sourced from `data/universe_registry.json`]
**Status**: Production Ready

## Quick Start

### Prerequisites
- Node.js 20+
- Python 3.10+
- Docker & Docker Compose

### Development Setup

1. **Install Dependencies**
   ```bash
   npm install          # Frontend (all workspaces)
   poetry install       # Backend (Python)
   cp .env.example .env # Configure environment
   ```

2. **Start Development Servers**
   ```bash
   npm run dev:web          # Public portal → http://localhost:3000
   npm run dev:admin        # Admin console → http://localhost:3001
   poetry run python manage.py runserver  # API → http://localhost:8000
   ```

3. **Docker (all services)**
   ```bash
   docker compose up -d   # API, Celery, Web, Admin, PostgreSQL, Redis, Elasticsearch
   ```


## Coverage

All numbers sourced from `data/universe_registry.json` with links to official sources.

| Level | Laws | Universe | Coverage | Source |
|-------|------|----------|----------|--------|
| **Federal** | 333/336 | 336 | 99.1% | [Cámara de Diputados](https://www.diputados.gob.mx/LeyesBiblio/) |
| **State (Legislativo)** | 11,363/12,120 | 12,120 | 93.7% | [OJN - Poder Legislativo](https://compilacion.ordenjuridico.gob.mx/) |
| **State (Other Powers)** | 0/23,660 | 23,660 | 0% | OJN - Poderes 1/3/4 (not yet scraped) |
| **Municipal** | 208 | Unknown | N/A | 5 city portals (no census exists) |
| **Leyes Vigentes** | **11,696/12,456** | **12,456** | **93.9%** | Federal + State Legislativo |

**Note**: 782 OJN links are permanently dead (Michoacán 504, EDOMEX 141, SLP 47). Municipal universe is unknown — INEGI reports 2,468 municipalities but no authoritative count of municipal laws exists.

## Features

- ✅ **93.9% Legislative Coverage** - 11,696 of 12,456 legislative laws (federal + state)
- ✅ **Structured Parsing** - Akoma Ntoso XML output with automated validation
- ✅ **Dynamic Dashboard** - Real-time statistics and recent legislation feed
- ✅ **Advanced Search** - Date range filtering, state filters, and auto-complete
- ✅ **Law Detail 2.0** - Enhanced typography, improved ease-of-reading, and citations
- ✅ **Quality Validation** - 5 automated checks, A-F grading
- ✅ **Full-Text Search** - 550,000+ articles indexed in Elasticsearch
- ✅ **Version History** - Track legal evolution over time
- ✅ **REST API** - Machine-readable access for legal tech
- ✅ **Batch Processing** - Parallel ingestion with 4-8 workers
- ✅ **Production Ready** - Full-stack testing (Backend + Frontend w/ Vitest)
- ✅ **OpenAPI Documentation** - Swagger UI, ReDoc at `/api/docs/`
- ✅ **Background Processing** - Celery + Redis for ingestion jobs
- ✅ **Cross-References** - Automatic detection and linking between laws

## Architecture

### Monorepo Structure
This project uses a monorepo architecture managed by NPM Workspaces.

```text
/
├── packages/
│   ├── ui/          # Shared UI Library (@leyesmx/ui) - React 19 / Shadcn
│   ├── lib/         # Shared Utilities & Types (@leyesmx/lib)
│   └── tsconfig/    # Shared TypeScript configurations
├── apps/
│   ├── web/         # Public Portal (Next.js 15)
│   ├── admin/       # Management Console (Next.js 16)
│   └── api/         # Backend API (Django / Python)
└── package.json     # Workspace Root
```

### Components
  - **Ingestion Pipeline**: PDF Download → Text Extraction → Parsing → Validation
  - **Public Portal**: Citizen-facing search and traversal of laws
  - **Admin Console**: Operator dashboard for monitoring ingestion jobs

## Documentation

- [Setup Guide](docs/guides/SETUP.md) - Installation and configuration
- [Tech Stack](docs/architecture/TECH_STACK.md) - Approved technologies
- [Architecture](docs/architecture/ARCHITECTURE.md) - System design
- [Testing](tests/) - Test suite (backend + frontend)

## Performance

| Metric | Result |
|--------|--------|
| Processing Speed | 23s per law |
| Parallel Speedup | 3-4x |
| Schema Compliance | 100% |

## Project Roadmap

**Phase 1: Federal Laws** - ✅ COMPLETE
- ✅ 333 federal laws ingested (99.1% of 336)
- ✅ Quality validation framework
- ✅ Elasticsearch full-text search

**Phase 2: State Laws** - ✅ COMPLETE
- ✅ 11,363 state laws downloaded (93.7% of 12,120 OJN Legislativo)
- ✅ Database schema update
- ✅ State law processing pipeline
- ✅ Frontend state filters

**Phase 3: UI/UX Transformation** - 🔄 IN PROGRESS
- ✅ Dynamic Homepage Dashboard
- ✅ Law Detail Page 2.0
- ✅ Advanced Search Filters (Date Range)
- 🔄 Comparison Tool

**Phase 3: Municipal Laws** - 📋 PLANNED (Q2 2026)
- 📋 Tier 1: 10 largest cities
- 📋 Tier 2: 32 state capitals
- 📋 Long-term: Full municipal coverage

**See**: [ROADMAP.md](ROADMAP.md) for detailed timeline and [docs/strategic_overview.md](docs/strategic_overview.md) for comprehensive vision

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

##License

MIT License - see LICENSE file for details.

## Contact

Issues: https://github.com/madfam-org/leyes-como-codigo-mx/issues
