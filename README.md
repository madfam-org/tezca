# Leyes Como Código - Mexico

**The definitive digital platform for Mexican legal research** - comprehensive, machine-readable database of Mexican laws (federal, state, municipal) with intuitive interfaces for professionals and citizens.

**Coverage**: 93.9% of Legislative Laws (11,696 of 12,456) + 18,439 non-legislative (30,343 total) — [sourced from `data/universe_registry.json`]
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
| **State (Other Powers)** | 18,439/23,660 | 23,660 | 77.9% | OJN - Poderes 1/3/4 |
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
- ✅ **Full-Text Search** - 3,480,000+ articles indexed in Elasticsearch
- ✅ **Version History** - Track legal evolution over time
- ✅ **REST API** - Machine-readable access for legal tech (paginated, filtered, rate-limited)
- ✅ **Batch Processing** - Parallel ingestion with 4-8 workers
- ✅ **Production Ready** - Full-stack testing (229 web Vitest + 51 admin Vitest + ~201 Pytest + 8 E2E specs)
- ✅ **OpenAPI Documentation** - Swagger UI, ReDoc at `/api/docs/`
- ✅ **Background Processing** - Celery + Redis for ingestion jobs
- ✅ **Cross-References** - Automatic detection and linking between laws
- ✅ **Legal Pages** - Terms & Conditions, Legal Disclaimer, Privacy Policy (trilingual ES/EN/NAH)
- ✅ **Site Footer** - Persistent navigation, official source links, disclaimer bar
- ✅ **Disclaimer Banner** - Dismissable one-time homepage notice (localStorage persistence)
- ✅ **Trilingual UI** - ES/EN/NAH (Classical Nahuatl) language toggle across all components (law content remains Spanish)
- ✅ **Tezca Manifesto** - `/acerca-de` brand page with mission statement
- ✅ **Persistent Navbar** - Sticky navigation with mobile hamburger menu, transparent-on-homepage
- ✅ **Bookmarks** - Heart toggle, localStorage persistence, `/favoritos` page
- ✅ **Reading UX** - Progress bar, font size control, back-to-top, breadcrumbs
- ✅ **Share & Export** - Social sharing (Twitter, LinkedIn, WhatsApp), copy link, PDF print export
- ✅ **Loading Skeletons** - Shaped placeholders for law detail, search results, dashboard
- ✅ **API Hardening** - Rate limiting (100/hr), pagination (50/page), law status field, search-within-law
- ✅ **Accessibility** - WCAG 2.1 AA (skip-to-content, aria-labels, keyboard nav, 44px touch targets)
- ✅ **Search-Within-Law** - Elasticsearch-powered article search with highlighted snippets
- ✅ **Keyboard Shortcuts** - j/k article navigation, / search, b bookmark, ? help panel
- ✅ **Recently Viewed** - Homepage section showing last 10 visited laws (localStorage)
- ✅ **SEO Foundation** - Dynamic sitemap, robots.txt, OG metadata, trilingual 404 page
- ✅ **URL-Synced Search** - Pagination, filters, and query persisted in URL (shareable/bookmarkable)
- ✅ **Faceted Search** - ES aggregations (by tier, category, status, law_type, state) with live filter counts
- ✅ **Browse Pages** - Browse by Category (/categorias/) and State (/estados/) with API-backed counts
- ✅ **Related Laws** - Elasticsearch more_like_this recommendations on law detail
- ✅ **6-Format Export** - TXT/PDF/LaTeX/DOCX/EPUB/JSON with tier-based rate limits (anon/free/premium)
- ✅ **Word-Level Compare Diff** - Side-by-side comparison with green (added) / red (removed) inline highlights
- ✅ **Cross-Reference Panel** - Outgoing + incoming law references with confidence threshold filter
- ✅ **Version Timeline** - Collapsible history with change_summary and valid_to dates
- ✅ **Cmd+K Global Search** - Overlay with debounced suggestions and keyboard navigation
- ✅ **Citation Export** - Legal citation + BibTeX copy from article viewer
- ✅ **Dynamic OG Images** - Per-law opengraph images via Next.js ImageResponse
- ✅ **Homepage Refresh** - FeaturedLaws grid, QuickLinks, trilingual headings
- ✅ **JSON-LD Structured Data** - schema.org Legislation + WebSite + Organization
- ✅ **Canonical URLs** - alternates for es/en/x-default, expanded sitemap with categories + states
- ✅ **Spanish URL Paths** - /leyes, /busqueda, /comparar with 301 redirects from English
- ✅ **Dual Storage** - Local dev / Cloudflare R2 production backend
- ✅ **Sentry Integration** - Django API + Next.js web (optional)

## Architecture

### Monorepo Structure
This project uses a monorepo architecture managed by NPM Workspaces.

```text
/
├── packages/
│   ├── ui/          # Shared UI Library (@tezca/ui) - React 19 / Shadcn
│   ├── lib/         # Shared Utilities & Types (@tezca/lib)
│   └── tsconfig/    # Shared TypeScript configurations
├── apps/
│   ├── web/         # Public Portal (Next.js 16)
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
- [llms.txt](llms.txt) - Agent-consumable project summary ([llms-full.txt](llms-full.txt) for expanded version)

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

**Phase 3: UI/UX Transformation** - ✅ COMPLETE
- ✅ Dynamic Homepage Dashboard
- ✅ Law Detail Page 2.0 (breadcrumbs, font control, progress bar)
- ✅ Advanced Search with Autocomplete Typeahead
- ✅ Legal Pages (Terms, Disclaimer, Privacy) — trilingual ES/EN/NAH
- ✅ Persistent Navbar + Site Footer + Disclaimer Banner
- ✅ Comparison Tool (side-by-side, sync scroll, mobile tabs)
- ✅ Bookmarks, Share Buttons, PDF Export, Loading Skeletons
- ✅ API Hardening (pagination, filtering, rate limiting, search-within-law)
- ✅ CI/CD (coverage, E2E in CI, Dockerfile verification)

**Phase 4-7: Data Depth & Infrastructure** - ✅ COMPLETE
- ✅ 150 federal reglamentos ingested
- ✅ 18,439 non-legislative state laws (77.9% of OJN Poderes 1/3/4)
- ✅ Parser V2 (TRANSITORIOS boundary, dedup, Bis patterns)
- ✅ DOF daily scraper wired to Celery Beat (7 AM)
- ✅ Dual storage backend (local / Cloudflare R2)
- ✅ Sentry integration, ES resilience (retry/timeout/pooling)
- ✅ JSON-LD structured data on law detail pages
- ✅ Trilingual UI (ES/EN/NAH — Classical Nahuatl)

**Phase 8-9: Surface & Search Intelligence** - ✅ COMPLETE
- ✅ law_type field + non-legislative badges
- ✅ Faceted search (ES aggregations), browse by category/state
- ✅ Related laws (more_like_this), sort on catalog
- ✅ Spanish URL paths (/leyes, /busqueda, /comparar) with 301 redirects
- ✅ Hierarchical TOC, citation copy, enhanced accessibility

**Phase 10-11: Professional Polish & User Magnet** - ✅ COMPLETE
- ✅ SEO hardening (canonical URLs, alternates, expanded sitemap, OG images)
- ✅ Cross-reference panel, version timeline
- ✅ 6-format export (TXT/PDF/LaTeX/DOCX/EPUB/JSON) with tier-based rate limits
- ✅ Word-level compare diff
- ✅ Cmd+K global search overlay, citation + BibTeX export
- ✅ Homepage refresh (FeaturedLaws, QuickLinks, trilingual headings)

**Phase 12: Production & Municipal** - 📋 PLANNED (Q2 2026)
- 📋 Production go-live at tezca.mx
- 📋 Municipal Tier 1: 10 largest cities
- 📋 Embeddings / vector search integration

**See**: [ROADMAP.md](ROADMAP.md) for detailed timeline and [Strategic Overview](docs/strategy/STRATEGIC_OVERVIEW.md) for comprehensive vision

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## License

AGPL-3.0 — see [pyproject.toml](pyproject.toml) for details.

## Contact

Issues: https://github.com/madfam-org/tezca/issues
