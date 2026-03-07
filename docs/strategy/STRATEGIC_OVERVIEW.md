# Leyes Como Código - Strategic Overview & Vision

**Date**: 2026-03-07
**Current Coverage**: 93.9% of Legislative Laws (11,696 of 12,456)
**Total Laws Processed**: 35,277 (1,931 federal + 30,907 state + 2,439 municipal)
**Coverage Source**: `data/universe_registry.json`, pipeline run logs

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
| **Federal Reglamentos** | 150 | ~800 | ~19% | Cámara de Diputados (regla.htm) |
| **State (Legislativo)** | 11,363 | 12,120 | 93.7% | OJN Poder Legislativo |
| **State (Other Powers)** | 18,439 | 23,660 | 77.9% | OJN Poderes 1/3/4 |
| **Municipal** | 208 | Unknown | N/A | 5 city portals |
| **Leyes Vigentes** | **11,696** | **12,456** | **93.9%** | Federal + State Legislativo |
| **Total Processed** | **30,343** | | | All tiers combined |

### Quality Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Federal Coverage** | 99.1% (333/336) | Cámara de Diputados catalog |
| **State Legislative Coverage** | 93.7% (11,363/12,120) | OJN Poder Legislativo |
| **State Non-Legislative** | 77.9% (18,439/23,660) | OJN Poderes 1/3/4 |
| **Federal Reglamentos** | 150 processed | Cámara de Diputados |
| **Schema Compliance** | 100% | Akoma Ntoso validation |
| **Permanent OJN Gaps** | 782 dead links | Michoacán 504, EDOMEX 141, SLP 47 |

### Platform Health

```
Backend (Django):  ✅ Stable (production-hardened: HSTS, secure cookies, structured logging)
Database:          ✅ PostgreSQL production-ready (shared MADFAM cluster)
Search:            ✅ Elasticsearch operational (3.48M+ articles, resilient client: retry/timeout/pooling)
Scraping:          ✅ OJN pipeline functional, DOF daily wired to Celery Beat
Frontend (Next):   ✅ Phase 11 complete (all user-facing features: faceted search, export, Cmd+K, citation, OG images, compare diff)
Admin Panel:       ✅ Functional (Janua auth integrated, 5 dashboard pages: Ingestion, Metrics, DataOps, Roadmap, Settings)
DataOps:           ✅ Gap tracking, health monitoring, coverage dashboard operational
Storage:           ✅ Dual-backend abstraction (local dev / Cloudflare R2 production)
Observability:     ✅ Sentry integration (Django API + Next.js web, optional)
SEO:               ✅ JSON-LD (Legislation + WebSite + Organization), dynamic OG images, canonical URLs, expanded sitemap
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
        │ 30,343    │    │ 3,480,000+  │  index
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
✅ Elasticsearch re-indexing complete (3.48M+ articles)
✅ Frontend state filters deployed

### Municipal Coverage 🔄 IN PROGRESS

**Status**: Pilot phase (Q2 2026)

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

### Advanced Features 🎨 VISION

**Computational Law**:
- ✅ Akoma Ntoso XML (machine-readable)
- ⏳ Tax calculation engine (Catala/OpenFisca — experimental/blocked)
- 📋 Contract compliance checking
- 📋 Legal reasoning AI

**Platform Intelligence** (many already built):
- ✅ Cross-reference panel (outgoing + incoming refs)
- ✅ Version timeline with change_summary
- ✅ Word-level compare diff
- ✅ DOF daily monitoring (Celery Beat, 7 AM)
- 🔄 Legal Knowledge Graph (Phase 6 -- graph visualization, NLP, temporal, embeddings)
- 📋 Legal precedent matching

### Legal Knowledge Graph Initiative

**Research**: `docs/research/Open Source Legal Data Graph.md`
**Status**: Phase 6.1 (Graph Visualization) in progress

The Legal Knowledge Graph transforms Tezca's existing cross-reference data (33K+ records) into an interactive, explorable network. Rather than deploying a dedicated graph database immediately, the initiative builds incrementally on PostgreSQL and Elasticsearch.

**Technology decisions**:
- **Visualization**: Sigma.js + Graphology (WebGL, MIT licensed) over D3.js or Cytoscape -- better performance for 300+ node graphs
- **Graph storage**: PostgreSQL aggregate queries on CrossReference model -- sufficient for 33K edges, NebulaGraph deferred until 500K+ threshold
- **NLP pipeline**: spaCy 3.7 (already installed) + XLM-RoBERTa for legal entity recognition
- **Embeddings**: paraphrase-multilingual-mpnet-base-v2 (768-dim) -- EmbeddingGenerator code exists but is dormant

**Existing data assets**:
- 33,380 CrossReference records (62.8% resolved, confidence 0.075-0.9)
- ~50K LawVersion records with `valid_from`/`valid_to` (bitemporal foundation)
- spaCy 3.7 installed in Poetry dependencies
- Regex-based parser pipeline producing Akoma Ntoso XML

**5-phase roadmap**: Visualization -> Enriched edges + NLP -> Temporal graph -> Embeddings + analytics -> NebulaGraph (if justified). Each phase delivers standalone value.

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

Full Legal Framework (including non-legislative state laws + reglamentos):
  Universe:   36,916 (adds 23,660 from OJN poderes 1/3/4 + ~800 reglamentos)
  We have:    30,343
  Coverage:   82.2%

Municipal:
  Universe:   Unknown (2,468 municipalities, no census of laws)
  We have:    208 from 5 city portals
```

#### Breakdown by Jurisdiction

**Federal Level**: 333/336 (99.1%) — Source: Cámara de Diputados
**Federal Reglamentos**: 150 processed (of ~800) — Source: Cámara de Diputados
**State Legislativo**: 11,363/12,120 (93.7%) — Source: OJN Poder Legislativo
**State Other Powers**: 18,439/23,660 (77.9%) — Source: OJN Poderes 1/3/4 (Ejecutivo/Judicial/Autónomos)
**Municipal**: 208 laws from 5 cities — No known universe
**Articles**: 3,480,000+ indexed in Elasticsearch (1.26M parsed: 860K legislative + 398K non-legislative)

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

**Current State** (Phase 11 complete):
- ✅ **Feature-Rich**: Faceted search, export, comparison, citation, Cmd+K, OG images
- ✅ **Trilingual**: ES/EN/NAH across all UI components
- ✅ **Professional**: SEO-hardened, accessible (WCAG 2.1 AA), mobile-optimized

**Vision**: **World-Class Legal Research Platform** — largely achieved, ongoing polish

##### Homepage (Reimagined)

```
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║     🏛️  LEYES COMO CÓDIGO                            ║
║     El Sistema Legal Mexicano, Digitalizado          ║
║                                                       ║
║   ┌─────────────────────────────────────────┐       ║
║   │  🔍  Buscar en 30,000+ leyes...          │       ║
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
• ~30,500 leyes procesadas
• 3.48M+ artículos indexados en Elasticsearch
• 93.9% cobertura de leyes legislativas
• Actualizado: 2026-02-07
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
- ✅ Trilingual UI (ES/EN/NAH) — implemented across all components; law content remains Spanish-only

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
│  Operational   │  30,343 laws  │  Indexed           │
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

### Priority 3: Public UI/UX + Search Intelligence + Professional Polish ⭐⭐⭐ ✅ COMPLETE (Phases 3-11)

**Status**: All tasks delivered through Phase 11

- ✅ Design system, homepage, search, law detail, comparison, legal pages, footer, dark mode
- ✅ Trilingual UI (ES/EN/NAH), search autocomplete, bookmarks, reading UX, keyboard shortcuts
- ✅ Faceted search with ES aggregations, browse by category/state, related laws
- ✅ Spanish URL paths with 301 redirects, URL-synced search
- ✅ SEO hardening (JSON-LD, canonical URLs, alternates, OG images, expanded sitemap)
- ✅ Cross-reference panel, version timeline, 6-format export (TXT/PDF/LaTeX/DOCX/EPUB/JSON)
- ✅ Word-level compare diff, Cmd+K search, citation + BibTeX export
- ✅ Homepage refresh (FeaturedLaws, QuickLinks, trilingual headings)

### Priority 4: Admin Panel ⭐⭐ ✅ COMPLETE

**Status**: 5 dashboard pages delivered (Ingestion, Metrics, DataOps, Roadmap, Settings)

- ✅ Real-time job monitoring (from AcquisitionLog, last 20 runs)
- ✅ System metrics with law_type breakdown
- ✅ Coverage dashboard with tier progress and state table
- ✅ Quality indicators (Buena/Media/Baja) on state coverage
- ✅ Janua JWT auth for all admin endpoints

### Priority 5: Data Quality & Stability ⭐⭐ ✅ LARGELY COMPLETE

- ✅ 229 web + 51 admin + ~201 backend tests + 8 E2E specs
- ✅ DOF daily monitoring (Celery Beat, 7 AM)
- ✅ ES resilience (retry/timeout/pooling)
- ✅ Sentry integration (Django + Next.js)
- ✅ Dual storage backend (local / R2)
- 🔄 Ongoing: documentation updates, test expansion

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

**Risk**: Elasticsearch performance degradation with 3.48M+ articles
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
**Mitigation**: Terms & Conditions (`/terminos`), Legal Disclaimer (`/aviso-legal`), dismissable homepage banner, footer disclaimer bar — all trilingual

---

## 🌟 Conclusion

**Leyes Como Código is positioned to become the definitive platform for Mexican legal research.**

**Current Status**: Strong foundation (93.9% legislative coverage, 30,343 total laws processed, 3.48M+ articles, production-ready backend)

**Next Steps**: Production go-live at tezca.mx + municipal pilot + vector search

**Timeline**: 6 months to 95%+ coverage with gorgeous interfaces

**Impact**: Democratize access to Mexican law for millions of users

---

**Let's build something extraordinary.** 🚀

---

**Document Version**: 1.3
**Last Updated**: 2026-03-07
**Next Review**: 2026-04-07
