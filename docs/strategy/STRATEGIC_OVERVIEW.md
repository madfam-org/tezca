# Leyes Como Código - Strategic Overview & Vision

**Date**: 2026-02-05
**Current Coverage**: 93.9% of Legislative Laws (11,696 of 12,456)
**Total Laws in DB**: ~11,904 (333 federal + 11,363 state + 208 municipal)
**Coverage Source**: `data/universe_registry.json`

---

## 🎯 Mission Statement

**Create the definitive digital platform for Mexican legal research** - a comprehensive, machine-readable database of all Mexican laws (federal, state, municipal) with gorgeous, intuitive interfaces for legal professionals, researchers, and citizens.

---

## 📊 Current Status Dashboard

### Data Coverage

All numbers sourced from `data/universe_registry.json`.

| Level | Laws | Universe | Coverage | Source |
|-------|------|----------|----------|--------|
| **Federal** | 333 | 336 | 99.1% | Cámara de Diputados |
| **State (Legislativo)** | 11,363 | 12,120 | 93.7% | OJN Poder Legislativo |
| **State (Other Powers)** | 0 | 23,660 | 0% | OJN Poderes 1/3/4 |
| **Municipal** | 208 | Unknown | N/A | 5 city portals |
| **Leyes Vigentes** | **11,696** | **12,456** | **93.9%** | Federal + State Legislativo |

### Quality Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Federal Coverage** | 99.1% (333/336) | Cámara de Diputados catalog |
| **State Legislative Coverage** | 93.7% (11,363/12,120) | OJN Poder Legislativo |
| **Schema Compliance** | 100% | Akoma Ntoso validation |
| **Permanent OJN Gaps** | 782 dead links | Michoacán 504, EDOMEX 141, SLP 47 |

### Platform Health

```
Backend (Django):  ✅ Stable (production-hardened: HSTS, secure cookies, structured logging)
Database:          ✅ PostgreSQL production-ready (shared MADFAM cluster)
Search:            ✅ Elasticsearch operational (860K+ articles)
Scraping:          ✅ OJN pipeline functional
Frontend (Next):   ✅ Phase 3 UI/UX complete (comparison tool, mobile, dark mode, visual QA, search autocomplete)
Admin Panel:       ✅ Functional (Janua auth integrated, 4 dashboard pages)
DataOps:           ✅ Gap tracking, health monitoring, coverage dashboard operational
Deployment:        🔄 Infrastructure ready, pending manual provisioning (see below)
```

### Deployment Status (Tezca)

**Brand**: Tezca | **Domain**: tezca.mx | **Full details**: [Production Deployment Guide](../deployment/PRODUCTION_DEPLOYMENT.md)

| Component | Status |
|-----------|--------|
| Dockerfiles (3 services, multi-stage) | ✅ Done |
| Janua JWT auth (admin API + admin console) | ✅ Done |
| K8s manifests (16 files, HPA, PVCs) | ✅ Done |
| Enclii specs (7 services) | ✅ Done |
| CI/CD workflows (3 deploy pipelines) | ✅ Done |
| Python deps (PyJWT, cryptography) | ✅ Done |
| Private npm package (@janua/nextjs) | ⏳ Needs registry config |
| GitHub secrets (GHCR token, enclii callback) | ⏳ Needs repo admin |
| K8s secrets (DB, Janua keys) | ⏳ Needs enclii CLI |
| Janua OAuth client registration | ⏳ Needs Janua admin |
| Cloudflare DNS + ArgoCD config | ⏳ Needs DevOps |
| Initial migration + ES indexing | ⏳ Needs cluster access |

---

## 🏗️ Architecture Overview

### Full Stack Topology

```
┌─────────────────────────────────────────────────────────────┐
│                       PUBLIC USERS                           │
│                  (Legal Research Platform)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────▼────────────┐
           │   Next.js Frontend     │  Port 3000
           │   (apps/web)           │  React/TypeScript
           │   - Law browsing       │  TailwindCSS
           │   - Search UI          │
           │   - Comparison tool    │
           └───────────┬────────────┘
                       │
                       │ REST API
                       │
           ┌───────────▼────────────┐
           │   Django Backend       │  Port 8000
           │   (apps/api)           │  Python
           │   - Law endpoints      │  Django REST
           │   - Search proxy       │
           │   - Metadata API       │
           └─────┬─────────────┬────┘
                 │             │
        ┌────────▼──┐    ┌────▼────────┐
        │PostgreSQL │    │Elasticsearch│  Port 9200
        │   DB      │    │   Search    │  Full-text
        │ 11,904    │    │ 860,000+    │  index
        │  laws     │    │  articles   │
        └───────────┘    └─────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       ADMIN USERS                            │
│                  (Backend Management)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────▼────────────┐
           │   Admin Panel          │  Port 3001
           │   (apps/admin)         │  Next.js
           │   - Ingestion status   │  Real-time
           │   - Quality dashboard  │  monitoring
           │   - DataOps dashboard  │  coverage/gaps
           │   - Trigger jobs       │
           └───────────┬────────────┘
                       │
                       │ WebSocket + REST
                       │
           ┌───────────▼────────────┐
           │ Background Workers     │
           │ (apps/ingestion)       │
           │ - Scraping jobs        │
           │ - XML processing       │
           │ - Indexing tasks       │
           └───────────┬────────────┘
                       │
              ┌────────▼─────────┐
              │   Data Lake      │
              │ - 4.7GB raw docs │
              │ - 1.5GB archived │
              │ - XML outputs    │
              └──────────────────┘
```

### Data Flow Pipeline

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│   DOF    │───▶│ Scraper  │───▶│  Parser  │───▶│   DB     │
│  Source  │    │(Python)  │    │(AkomaXML)│    │(Storage) │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                      │
                                      ▼
                                ┌──────────┐
                                │Validator │
                                │(Quality) │
                                └──────────┘
                                      │
                                      ▼
                                ┌──────────┐
                                │  Index   │
                                │(Search)  │
                                └──────────┘
```

---

## 📁 Codebase Structure

### Module Breakdown (~262k lines)

```
tezca/
├── apps/                          # Main application modules
│   ├── api/                       # Django REST API (17 files)
│   │   ├── models.py              # Law, LawVersion, Article models
│   │   ├── views.py               # API endpoints
│   │   ├── search_views.py        # Elasticsearch integration
│   │   └── law_views.py           # Law detail/list endpoints
│   │
│   ├── parsers/                   # XML processing (25 files)
│   │   ├── pipeline.py            # Main ingestion orchestrator
│   │   ├── akn_generator_v2.py    # Akoma Ntoso XML generator
│   │   ├── validators/            # Schema + completeness validation
│   │   └── quality.py             # A-F grading system
│   │
│   ├── scraper/                   # DOF scraping (10 files)
│   │   ├── dof_api_client.py      # Official DOF API client
│   │   └── catalog_spider.py      # Law discovery
│   │
│   ├── ingestion/                 # Database persistence (2 files)
│   │   └── db_saver.py            # ORM interactions
│   │
│   ├── web/                       # Next.js Public UI (46 files)
│   │   ├── app/
│   │   │   ├── page.tsx           # Homepage
│   │   │   ├── laws/              # Law browsing
│   │   │   └── search/            # Search interface
│   │   ├── components/            # React components
│   │   └── lib/                   # API clients
│   │
│   └── admin/                     # Next.js Admin Panel (20 files)
│       ├── app/
│       │   ├── dashboard/         # Status dashboard
│       │   ├── ingestion/         # Job management
│       │   └── dataops/           # DataOps coverage, health, gaps
│       └── components/            # Admin UI components
│
├── scripts/                       # Automation (32 files)
│   ├── ingestion/
│   │   ├── bulk_ingest.py         # Batch processor (federal laws)
│   │   ├── index_laws.py          # Elasticsearch indexing
│   │   └── ingest_state_laws.py   # State law processor (planned)
│   │
│   ├── scraping/
│   │   ├── ojn_scraper.py         # State law scraper
│   │   ├── bulk_state_scraper.py  # Batch state scraping
│   │   └── retry_failed.py        # Failure recovery
│   │
│   └── conversion/
│       └── word_to_pdf.py         # Word→PDF converter (planned)
│
├── data/                          # Data storage
│   ├── law_registry.json          # Federal law catalog (336 laws)
│   ├── state_registry.json        # State catalog (32 states)
│   ├── xml/                       # Akoma Ntoso output (330 files)
│   └── state_laws/                # State downloads (11,337 files, 4.7GB)
│
├── archives/                      # Compressed backups
│   └── state_laws/
│       ├── originals_2026-02-03.tar.gz (1.5GB)
│       └── archive_metadata.json
│
├── docs/                          # Documentation (15 files)
│   ├── INGESTION_FIXES.md
│   ├── CATALA_STATUS.md
│   └── OJN_SCRAPING_STRATEGY.md
│
├── engines/                       # Computational engines
│   └── openfisca/                 # Tax calculation (disabled)
│
└── tests/                         # Test suite (24 files)
    ├── test_parser.py
    ├── test_validation.py
    └── test_api.py
```

---

## 🛣️ Path to Long-Term Stability

### Phase 1: Foundation ✅ COMPLETE

**Status**: Production-ready for federal laws

✅ Quality validation framework
✅ Batch processing
✅ Elasticsearch integration
✅ REST API
✅ 333 federal laws ingested (99.1% of 336)
✅ Test suite

### Phase 2: State Expansion ✅ COMPLETE

**Status**: Complete — 11,363 state laws in database, indexed in Elasticsearch

✅ OJN scraper built
✅ 11,363 state laws downloaded (93.7% of 12,120 OJN Legislativo)
✅ Database schema migration complete
✅ State ingestion pipeline operational
✅ Elasticsearch re-indexing complete (860K+ articles)
✅ Frontend state filters deployed

### Phase 3: Municipal Coverage 🔄 IN PROGRESS

**Status**: Design phase (Q2 2026)

**Challenges**:
- 2,465 municipalities
- Mostly non-digitized
- Requires partnerships

**Strategy**:
- Tier 1: 10 largest cities (CDMX, Guadalajara, Monterrey, etc.)
- Tier 2: State capitals (32 cities)
- Tier 3: Top 100 municipalities
- Tier 4: Long-tail (2+ years)

**ETA**: Tier  1 in 6 months, full coverage 2-3 years

### Phase 4: Advanced Features 🎨 VISION

**Computational Law**:
- ✅ Akoma Ntoso XML (machine-readable)
- ⏳ Tax calculation engine (Catala/OpenFisca - needs fixing)
- 📋 Contract compliance checking
- 📋 Legal reasoning AI

**Platform Intelligence**:
- Citation network analysis
- Legal precedent matching
- Automatic updates from DOF
- Version diffing visualization

---

## Data Completeness Trajectory

### Current State (Feb 2026)

All figures sourced from `data/universe_registry.json` with official citations.

```
Legislative Laws (Federal + State Legislativo):
  Universe:   12,456 (336 federal + 12,120 state)
  We have:    11,696 (333 federal + 11,363 state)
  Coverage:   93.9%
  Gaps:       782 permanent OJN dead links

Full Legal Framework (including non-legislative state laws):
  Universe:   36,116 (adds 23,660 from OJN poderes 1/3/4)
  We have:    11,696
  Coverage:   32.4%

Municipal:
  Universe:   Unknown (2,468 municipalities, no census of laws)
  We have:    208 from 5 city portals
```

#### Breakdown by Jurisdiction

**Federal Level**: 333/336 (99.1%) — Source: Cámara de Diputados
**State Legislativo**: 11,363/12,120 (93.7%) — Source: OJN Poder Legislativo
**State Other Powers**: 0/23,660 (0%) — Source: OJN Poderes 1/3/4 (Ejecutivo/Judicial/Autónomos)
**Municipal**: 208 laws from 5 cities — No known universe

### 6-Month Projection (Aug 2026)

```
Federal:         333 laws     (99.1% of 336)     ✅
State Legis:     11,800 laws  (97%+ of 12,120)   ✅
Municipal:       500 laws     (5-10 cities)       ⏳
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Leyes Vigentes:  12,133 laws  (97.4% of 12,456)
```

---

## 🎨 UI/UX Vision

### Dual Interface Strategy

####  Public Interface (apps/web) - **For Everyone**

**Target Users**: Legal professionals, researchers, students, citizens

**Current State**:
- ⚠️ **Basic**: Simple law list and search
- ⚠️ **Functional**: API-driven but minimal UX
- ❌ **Not Premium**: Lacks polish and engagement

**Vision**: **World-Class Legal Research Platform**

##### Homepage (Reimagined)

```
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║     🏛️  LEYES COMO CÓDIGO                            ║
║     El Sistema Legal Mexicano, Digitalizado          ║
║                                                       ║
║   ┌─────────────────────────────────────────┐       ║
║   │  🔍  Buscar en 11,900+ leyes...          │       ║
║   └─────────────────────────────────────────┘       ║
║                                                       ║
║    ✨ Cobertura: 93.9% de leyes legislativas vigentes ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝

┌──────────────────┬──────────────────┬──────────────────┐
│  🏛️ Federal      │  🏢 Estatal      │  🏘️ Municipal    │
│  333 leyes       │  11,363 leyes    │  208 leyes       │
│  99.1% of 336    │  93.7% of 12,120 │  5 cities        │
└──────────────────┴──────────────────┴──────────────────┘

📚 Leyes Populares
┌──────────────────────────────────────────────────────┐
│  [Constitución]  [Código Civil]  [Código Penal]     │
│  [ISR]  [IVA]  [Trabajo]  [Seguro Social]           │
└──────────────────────────────────────────────────────┘

📊 Estadísticas en Vivo
• ~11,900 leyes procesadas
• Artículos indexados en Elasticsearch
• 93.9% cobertura de leyes legislativas
• Actualizado: 2026-02-03
```

**Design Principles**:
1. **Gorgeous First Impression**
   - Modern glassmorphism effects
   - Vibrant color palette (not generic red/blue)
   - Smooth animations and micro-interactions
   - Google Fonts (Inter, Outfit, etc.)
   - Dark mode toggle

2. **Intuitive Navigation**
   - Clear jurisdiction tabs (Federal/State/Municipal)
   - Smart search with autocomplete
   - Faceted filters (category, tier, date, state)
   - Recent searches & popular laws

3. **Engaging Content Presentation**
   - Law cards with visual hierarchy
   - Grade badges (A/B/C) with tooltips
   - Interactive timelines for versions
   - Citation network graphs
   - "Read More" expandable sections

##### Search Page (Enhanced)

```
🔍 Búsqueda Avanzada

┌─────────────────────────────────────────────────────┐
│  código civil matrimonio                           │
└─────────────────────────────────────────────────────┘

Filtros:
☑️ Federal    ☑️ Estatal    ☐ Municipal
☑️ Leyes      ☑️ Códigos    ☐ Reglamentos

Estado: [Todos ▾]    Categoría: [Civil  ▾]    Vigencia: [Vigente ▾]

Resultados: 47 leyes encontradas
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[A] Código Civil Federal
    📄 1,234 artículos  •  🏛️ Federal  •  📅 1928 (Última reforma: 2025)
    ...coincidencia en Art. 267: "El matrimonio es la unión libre de..."
    
[A] Código Civil para el Estado de Jalisco  
    📄 1,456 artículos  •  🏢 Jalisco  •  📅 1967 (Última reforma: 2024)
    ...coincidencia en Art. 258: "Requisitos del matrimonio civil..."
    
[B] Código Familiar del Estado de Michoacán
    📄 892 artículos  •  🏢 Michoacán  •  📅 2015
    ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pág. 1 of 5    [<]  1  2  3  4  5  [>]
```

**Features**:
- Real-time search with highlights
- Snippet previews with context
- Relevance sorting + filters
- Save searches & alerts
- Export results (PDF/CSV)

##### Law Detail Page (Rich)

```
┌─────────────────────────────────────────────────────┐
│  [A] Código Civil Federal                           │
│  📄 1,234 artículos  •  🏛️ Federal  •  Vigente        │
└─────────────────────────────────────────────────────┘

📊 Estadísticas
• Artículos: 1,234
• Capítulos: 45
• Libros: 4
• Transitorios: 8
• Última reforma: 2025-01-15

📜 Historial de Versiones
┌──────────────────────────────────────────────┐
│  🟢 2025-01-15 (actual)                      │
│  🟡 2024-06-30                               │
│  🟡 2023-12-01                               │
│  [Ver todas las 287 versiones]              │
└──────────────────────────────────────────────┘

📚 Tabla de Contenido
├─ Libro Primero: De las Personas
│  ├─ Título Primero: De las personas físicas
│  ├─ Título Segundo: De las personas morales
│  └─ ...
├─ Libro Segundo: De los Bienes
├─ Libro Tercero: De las Sucesiones  
└─ Libro Cuarto: De las Obligaciones

🔗 Leyes Relacionadas (12)
[Código de Procedimientos Civiles]  [LGTAIP]  [...]

📥 Descargar
[XML]  [PDF]  [JSON]  [Markdown]
```

**Advanced Features**:
- Side-by-side version comparison
- Citation network visualization
- Annotate & bookmark
- Share specific articles (deep links)
- AI-powered summaries
- Translation (EN/ES toggle — implemented for legal pages and footer; law content remains Spanish-only)

##### Comparison Tool (Killer Feature)

```
🔬 Comparar Leyes

┌────────────────────────┬─────────────────────────┐
│  Código Civil Federal  │  Código Civil Jalisco   │
├────────────────────────┼─────────────────────────┤
│  Art. 267              │  Art. 258               │
│                        │                         │
│  "El matrimonio es la  │  "El matrimonio civil   │
│   unión libre de dos   │   es un contrato       │
│   personas para        │   solemne entre dos    │
│   realizar la          │   personas que desean  │
│   comunidad de vida."  │   unir su vida."       │
│                        │                         │
│  Última reforma:       │  Última reforma:        │
│  2019-06-28           │  2016-01-07            │
└────────────────────────┴─────────────────────────┘

📊 Análisis de Diferencias
• Redacción: 85% similar
• Estructura: Idéntica
• Requisitos: 2 diferencias encontradas
```

####  Admin Interface (apps/admin) - **For Operations**

**Target Users**: Platform administrators, data teams

**Vision**: **Mission Control Dashboard**

##### Admin Dashboard

```
╔══════════════════════════════════════════════════════╗
║  🎛️ PANEL DE ADMINISTRACIÓN                         ║
║  Leyes Como Código - Control Central                ║
╚══════════════════════════════════════════════════════╝

⚡ Estado del  Sistema
┌────────────────┬────────────────┬────────────────────┐
│  🟢 API        │  🟢 Database   │  🟢 Elasticsearch  │
│  Healthy       │  Healthy       │  Healthy           │
│  Operational   │  ~11,904 laws  │  Indexed           │
└────────────────┴────────────────┴────────────────────┘

📊 Cobertura de Datos
Federal:    ████████████████████░  99.1%  (333/336)
Estatal:    ██████████████████░░░  93.7%  (11,363/12,120)
Municipal:  █░░░░░░░░░░░░░░░░░░░░  208    (5 cities, no universe)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Vigentes:   ██████████████████░░░  93.9%  (11,696/12,456)

🔄 Trabajos en Curso
┌────────────────────────────────────────────────────┐
│  ⏳ Retry Failed State Laws                        │
│     Progress: [████████░░░░] 65%                   │
│     Recovered: 512/783 laws                        │
│     ETA: 45 minutes                                 │
│                                                     │
│  [Ver logs]  [Cancelar]                            │
└────────────────────────────────────────────────────┘

🚨 Alertas Recientes
• ⚠️  Michoacán: 504 scraping failures (investigate)
• ⚠️  CDMX: 0 laws found (structural issue)
• ℹ️  13 laws pending quality review

📋 Acciones Rápidas
[🔄 Reintentar Fallos]  [📥 Ingestar Nueva Ley]  [🔍 Reindexar Todo]
```

**Features** (5-card dashboard: Ingestion, Metrics, DataOps, Roadmap, Settings):
- Real-time job monitoring (Ingestion)
- System metrics and jurisdiction breakdown (Metrics)
- Coverage dashboard with tier progress, state table, gap summary, health grid (DataOps)
- Expansion roadmap with phase tracking and status updates (Roadmap)
- Manual trigger controls
- Error log viewing
- System health metrics and configuration (Settings)

---

## 🚀 Strategic Priorities (Next 6 Months)

### Priority 1: Production Go-Live (Tezca) ⭐⭐⭐

**Impact**: Platform available to the public at tezca.mx
**Timeline**: 1-2 weeks (manual provisioning steps)
**Effort**: Low (infrastructure code is done)

**Completed**:
1. ✅ Dockerfiles hardened (multi-stage, non-root, HEALTHCHECK)
2. ✅ Django production security (HSTS, secure cookies, SSL redirect, logging)
3. ✅ Janua JWT authentication (admin API + admin console)
4. ✅ K8s manifests (16 files: deployments, services, PVCs, HPA)
5. ✅ Enclii service specs (7 services)
6. ✅ CI/CD deploy workflows (3 GitHub Actions for GHCR + ArgoCD)
7. ✅ Health endpoints on all services
8. ✅ Python deps locked (PyJWT + cryptography)

**Remaining (manual, requires credentials)**:
1. ⏳ Configure `@janua/nextjs` private npm registry
2. ⏳ Set GitHub secrets (`MADFAM_BOT_PAT`, `ENCLII_CALLBACK_TOKEN`)
3. ⏳ Create K8s `tezca-secrets` via enclii CLI
4. ⏳ Register Janua OAuth client for admin console
5. ⏳ Configure Cloudflare DNS for tezca.mx zone
6. ⏳ Add tezca to ArgoCD root application
7. ⏳ Run initial migration, collectstatic, and ES indexing
8. ⏳ Smoke test all domains (see [Verification Checklist](../deployment/PRODUCTION_DEPLOYMENT.md#verification-checklist))

**Full deployment guide**: [docs/deployment/PRODUCTION_DEPLOYMENT.md](../deployment/PRODUCTION_DEPLOYMENT.md)

### Priority 2: Complete State Law Processing ⭐⭐⭐

**Impact**: 11,363 → 11,800 laws (93.7% → 97%+ of OJN Legislativo)
**Timeline**: 4 weeks
**Effort**: High

**Tasks**:
1. Retry failed downloads (783 laws)
2. Word→PDF conversion pipeline
3. Database schema migration
4. State ingestion pipeline
5. Elasticsearch re-indexing
6. Frontend state filters

### Priority 3: Public UI/UX Overhaul ⭐⭐⭐ ✅ COMPLETE

**Status**: All tasks delivered

1. ✅ Complete design system (colors, typography, components)
2. ✅ Homepage redesign (gorgeous first impression)
3. ✅ Enhanced search page (filters, previews, highlights)
4. ✅ Rich law detail pages (versions, citations, downloads)
5. ✅ Legal pages (Terms, Disclaimer, Privacy) — bilingual ES/EN
6. ✅ Site footer + disclaimer banner
7. ✅ Comparison tool (side-by-side, sync scroll, metadata panel, mobile tabs)
8. ✅ Mobile optimization (responsive design, 44px touch targets)
9. ✅ Dark mode + Visual QA (sticky footer, Suspense spinners, tab tooltips)
10. ✅ Search autocomplete with typeahead

### Priority 4: Admin Panel Completion ⭐⭐

**Impact**: Operational efficiency
**Timeline**: 3-4 weeks
**Effort**: Medium

**Tasks**:
1. Real-time job monitoring
2. Manual ingestion triggers
3. Quality dashboard
4. Error log viewer
5. System health metrics

### Priority 5: Data Quality & Stability ⭐⭐

**Impact**: Long-term maintainability
**Timeline**: Ongoing
**Effort**: Medium

**Tasks**:
1. Automated testing expansion
2. Continuous DOF monitoring
3. Quality assurance (QA) framework
4. Error handling improvements
5. Documentation updates

### Priority 6: Municipal Law Pilot (Tier 1) ⭐

**Impact**: +500 laws (CDMX, Guadalajara, Monterrey, etc.)
**Timeline**: 3-4 months (Q2 2026)
**Effort**: High

**Tasks**:
1. Municipal data source research
2. Partnership outreach
3. Custom scrapers for 10 cities
4. Ingestion pipeline adaptation
5. Pilot launch

---

## 💎 Unique Value Propositions

### For Legal Professionals
- ✅ **Comprehensive Coverage**: 93.9% of legislative laws, growing toward 97%+
- ✅ **Version History**: Track legal evolution over time
- ✅ **Comparison Tool**: Side-by-side analysis (federal vs state)
- ✅ **Machine-Readable**: API access for legal tech startups
- ✅ **Always Updated**: Automated DOF monitoring

### For Researchers & Academics
- ✅ **Citation Networks**: Visualize legal interconnections
- ✅ **Bulk Downloads**: Export entire datasets (XML/JSON)
- ✅ **Historical Analysis**: 300+ years of legal history
- ✅ **Quality Metrics**: Transparency in data processing
- ✅ **Open Source**: Contribute and collaborate

### For Citizens
- ✅ **Free Access**: No paywalls or subscriptions
- ✅ **Simple Search**: Find relevant laws in seconds
- ✅ **Plain Language**: AI-powered summaries (planned)
- ✅ **Mobile-Friendly**: Responsive design
- ✅ **Trustworthy**: Official government sources only

### For Developers
- ✅ **REST API**: Integrate into legal tech apps
- ✅ **Akoma Ntoso XML**: Standard legal format
- ✅ **Elasticsearch**: Advanced search capabilities
- ✅ **WebHooks**: Real-time updates (planned)
- ✅ **Documentation**: Comprehensive API docs

---

## 🎯 Success Metrics (6-Month Goals)

### Data Metrics
- ✅ **Legislative Coverage**: 93.9% → **97%+**
- ✅ **State Laws**: 11,363 → **11,800+** (of 12,120 OJN Legislativo)
- ✅ **Municipal**: 208 → **500** (Tier 1 cities)

### Platform Metrics
- ✅ **API Uptime**: **99.5%+**
- ✅ **Search Latency**: **<500ms**
- ✅ **Page Load**: **<2 seconds**
- ✅ **Mobile Score**: **90+** (Lighthouse)

### User Metrics
- ✅ **Monthly Users**: 0 → **10,000+** (post-launch)
- ✅ **Search Queries**: **50,000+/month**
- ✅ **API Calls**: **100,000+/month**
- ✅ **User Satisfaction**: **4.5+/5** stars

---

## 🛡️ Risk Mitigation

### Technical Risks

**Risk**: Elasticsearch performance degradation with 860K+ articles  
**Mitigation**: Cluster scaling, index optimization, caching layer

**Risk**: Database schema migration breaks existing data  
**Mitigation**: Staging environment testing, rollback plan, backups

**Risk**: Word→PDF conversion failures  
**Mitigation**: Fallback to manual conversion, quality checks

### Operational Risks

**Risk**: Municipal data not digitized  
**Mitigation**: Partnerships, OCR processing, crowdsourcing

**Risk**: DOF changes API structure  
**Mitigation**: Automated monitoring, rapid adapter updates

**Risk**: Single person dependency (bus factor)  
**Mitigation**: Comprehensive documentation, code reviews, team expansion

### Legal Risks

**Risk**: Copyright issues with law publication  
**Mitigation**: Public domain, official sources only, legal counsel

**Risk**: Data accuracy complaints
**Mitigation**: Quality metrics, error reporting, version control

**Risk**: Legal liability from user reliance
**Mitigation**: Terms & Conditions (`/terminos`), Legal Disclaimer (`/aviso-legal`), dismissable homepage banner, footer disclaimer bar — all bilingual

---

## 🌟 Conclusion

**Leyes Como Código is positioned to become the definitive platform for Mexican legal research.**

**Current Status**: Strong foundation (93.9% legislative coverage, production-ready backend)

**Next Steps**: UI/UX polish + state law completion = world-class platform

**Timeline**: 6 months to 95%+ coverage with gorgeous interfaces

**Impact**: Democratize access to Mexican law for millions of users

---

**Let's build something extraordinary.** 🚀

---

**Document Version**: 1.1
**Last Updated**: 2026-02-06
**Next Review**: 2026-03-06
