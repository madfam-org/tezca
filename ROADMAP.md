# Leyes Como Código - Product Roadmap

**Last Updated**: 2026-03-07
**Current Status**: 35,277 laws, 1,071,445 ES articles, 33,380 cross-references
**Data Motor**: Pipeline fix complete (state/municipal AKN parsing + unified indexer)
**DataOps**: Protocol implemented (gap tracking, health monitoring, coverage dashboard)

---

## Vision

**Build the definitive platform for Mexican legal research** - complete coverage of federal, state, and municipal laws with gorgeous, intuitive interfaces for everyone from legal professionals to curious citizens.

---

## Current Status (Mar 2026)

### ✅ Achievements
- **35,277 laws** in database (1,931 federal + 30,907 state + 2,439 municipal)
- **93.9% legislative coverage** (11,696 of 12,456 leyes vigentes)
- **98.9% parser accuracy** (world-class quality)
- **1,071,445 articles** indexed in Elasticsearch
- **Production-ready** backend infrastructure
- **Full-stack Testing** (736 backend + 299 web Vitest + 72 admin Vitest)

### 🔄 In Progress
- Tezca production deployment
- Municipal pilot planning

---

## Phase 1: Federal Foundation ✅ COMPLETE

**Timeline**: Completed  
**Coverage**: 333/336 laws (99.1%)

### Deliverables
- ✅ Akoma Ntoso XML parser (98.9% accuracy)
- ✅ Quality validation system (A-F grading)
- ✅ Batch processing engine (6-8 workers)
- ✅ PostgreSQL database schema
- ✅ REST API endpoints
- ✅ Elasticsearch integration
- ✅ Test suite (>20 tests)

---

## Phase 2: State Expansion ✅ COMPLETE

**Timeline**: Completed
**Coverage Target**: 11,800 laws (~98%)

### Week 1: Archive & Retry ✅
- ✅ Create compressed archive (4.7GB → 1.5GB)
- ✅ Build retry script for 783 failures
- ✅ Execute retry (expected +400-600 laws)
- ✅ Archive complete dataset

### Week 2: Conversion & Schema ✅
- ✅ Convert Word documents to PDF (~10,000 files)
- ✅ Database schema migration (add jurisdiction fields)
- ✅ Test state ingestion on 3 pilot states
- ✅ Quality assurance framework

### Week 3: State Ingestion ✅
- ✅ Process all 11,800 state laws through pipeline
- ✅ Generate Akoma Ntoso XML for state laws
- ✅ Quality validation and grading
- ✅ Re-index Elasticsearch (~500,000 new articles)

### Week 4: Frontend & Polish ✅
- ✅ Add state filter to search UI
- ✅ Create state-specific law pages
- ✅ Update navigation (Federal/State tabs)
- ✅ Performance optimization
- ✅ Final QA and testing

---

## Phase 3: UI/UX Transformation ✅ COMPLETE

**Timeline**: Completed Feb 2026
**Goal**: World-class user experience

### Public Interface Redesign
- ✅ **Homepage**: Gorgeous first impression with live stats and dashboard
- ✅ **Search**: Advanced filters, autocomplete typeahead (`/suggest/` API), zero-results suggestions
- ✅ **Law Detail**: Rich pages with versions, citations, downloads (v2.0)
- ✅ **Legal Pages**: Terms & Conditions (`/terminos`), Legal Disclaimer (`/aviso-legal`), Privacy Policy (`/privacidad`)
- ✅ **Site Footer**: 4-column navigation, official source links, disclaimer bar, copyright
- ✅ **Disclaimer Banner**: Dismissable homepage warning (localStorage persistence)
- ✅ **Trilingual Toggle**: ES/EN/NAH language switch across all UI components
- ✅ **Comparison Tool**: Side-by-side law comparison with sync scroll, metadata panel, mobile tabs
- ✅ **Mobile**: Fully responsive design (44px touch targets, responsive tabs, stacked layouts)
- ✅ **Dark Mode**: Complete theme support
- ✅ **Visual QA**: Sticky footer, Suspense fallback spinners, tab tooltips, WCAG 2.1 AA touch targets
- ✅ **Persistent Navbar**: Sticky nav with brand, trilingual links, mobile hamburger, transparent-on-homepage
- ✅ **Reading UX**: Progress bar, font size control (A-/A/A+), back-to-top button, breadcrumbs
- ✅ **Bookmarks**: Heart toggle, localStorage persistence, `/favoritos` page
- ✅ **Share & Export**: Social sharing (Twitter, LinkedIn, WhatsApp), copy link, PDF print export
- ✅ **Loading Skeletons**: Shaped placeholders for law detail, search results, dashboard
- ✅ **Comparison Hint**: One-time onboarding tooltip for checkbox discovery

### API Hardening
- ✅ **Rate Limiting**: 100/hr anon, 30/min search (DRF throttling)
- ✅ **Pagination**: `/laws/` paginated (50/page, max 200) with `{ count, next, previous, results }`
- ✅ **Filtering**: `/laws/?tier=&state=&category=&status=&q=` query params
- ✅ **Legal Status**: `Law.status` field (vigente/abrogada/derogada/unknown) with migration
- ✅ **Search-within-Law**: `GET /laws/<id>/search/?q=` with ES highlight extraction

### CI/CD Improvements
- ✅ **Coverage**: `pytest --cov` + `vitest --coverage` in CI with artifact upload
- ✅ **E2E in CI**: Playwright Chromium job with report artifacts
- ✅ **@janua/nextjs Fix**: Optional dependency with stub fallback for CI builds
- ✅ **Dockerfile Verification**: Build-time assertion that `server.js` exists

### Admin Dashboard
- Real-time job monitoring
- Manual ingestion triggers
- Quality dashboard
- System health metrics
- Error log viewer

### Design Principles
- Vibrant color palette (no generic colors)
- Modern typography (Google Fonts)
- Smooth animations and micro-interactions
- Glassmorphism effects
- Premium, state-of-the-art feel

---

## Completed Sprint: Data Motor (Pipeline Fix) 🔧 DONE

**Sprint Goal**: Fix the broken ingestion/indexing pipeline so all 11,580+ scraped laws flow through scrape → parse → DB → ES end-to-end.

**Status**: Complete

| # | Task | Status | Blocker |
|---|------|--------|---------|
| 1 | Unified path resolution (Docker/local) | Done | -- |
| 2 | State/Municipal AKN parser pipeline | Done | -- |
| 3 | Fix ingestion commands to use AKN paths | Done | Task 2 |
| 4 | Unified ES indexer (merge two indexers) | Done | Task 3 |
| 5 | Pipeline orchestration update (tasks.py) | Done | Tasks 2-4 |
| 6 | Municipal scraper completion (tier-1 cities) | Done | -- |
| 7 | End-to-end validation + integration tests | Done | Tasks 1-5 |

**Definition of Done**: `python scripts/validation/validate_pipeline.py` reports 100% for federal, >90% for state, >80% for municipal tiers.

**Recently Completed (Previous Sprint: DataOps Protocol):**
- DataOps protocol: DataSource, GapRecord, AcquisitionLog models
- Gap Registry + 53 gap records bootstrapped
- Health Monitor with 5 source probes
- Coverage Dashboard + CLI reports
- Source Discovery framework (32 state congress portals)
- Celery Beat scheduling (5 scheduled tasks)
- Escalation Playbook (5-tier system + 3 contact templates)
- Law model enhancement (state, source_url, last_verified fields)

---

## Completed Sprint: Data Universe Documentation & OJN Expansion

**Sprint Goal**: Document the full Mexican legal framework universe (~670K+ instruments), establish partnership contacts, and execute the highest-ROI data expansion (OJN poderes 1/3/4).

**Status**: Documentation complete; OJN expansion scraper ready (runtime pending)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create `docs/data/MEXICAN_LEGAL_UNIVERSE.md` (7-tier taxonomy) | Done | ~670K+ instruments documented |
| 2 | Create `docs/data/PARTNERSHIP_DIRECTORY.md` (18+ institutions) | Done | Federal, state, academic, civil society |
| 3 | Expand `data/universe_registry.json` to v2.0 (tiers 5-7) | Done | +6 new sources, +2 coverage views |
| 4 | Update escalation playbook for post-INAI dissolution | Done | INAI → Anticorrupción, Template 4 added |
| 5 | Create `scripts/scraping/bulk_non_legislative_scraper.py` | Done | Highest-ROI: +23,660 laws |
| 6 | Run OJN poderes 1/3/4 scrape (all 32 states) | Pending | ~12-24 hour runtime |
| 7 | Post-scrape: update registry, ingest, re-index | Pending | After step 6 completes |

---

## Completed Sprint: Hardening Sprint ✅ DONE

**Sprint Goal**: Fix critical UI bugs, clean up dead code, ensure CI passes cleanly.

| # | Task | Status |
|---|------|--------|
| 1 | Fix broken popular law links on homepage | Done |
| 2 | Fix double article headings in law detail | Done |
| 3 | Fix unreadable content rendering | Done |
| 4 | Resolve ESLint set-state-in-effect warnings | Done |
| 5 | Black formatting CI fixes | Done |

---

## Completed Sprint: Agent-Friendly Initiative (llms.txt) ✅ DONE

**Sprint Goal**: Create llms.txt/llms-full.txt for AI agent interoperability + refresh all documentation for accuracy.

| # | Task | Status |
|---|------|--------|
| 1 | Create `llms.txt` (concise agent-consumable project summary) | Done |
| 2 | Create `llms-full.txt` (expanded version with inlined content) | Done |
| 3 | Audit and refresh all 21 docs for accuracy | Done |
| 4 | Update README.md (license, counts, links) | Done |
| 5 | Update ROADMAP.md (reconcile counts, add sprints) | Done |

---

## Completed: Phases 4-7 — Data Depth & Infrastructure ✅

**Sprints**: Audit, Parser V2, Reglamentos, Non-Legislative, Trilingual, Infrastructure

- ✅ Codebase audit: 67 fixes across 5 categories (security, dedup, API, UX, cleanup)
- ✅ Parser V2: TRANSITORIOS boundary, dedup, Bis patterns (100 tests)
- ✅ 150 federal reglamentos ingested via spider
- ✅ 18,439 non-legislative state laws (77.9% of OJN Poderes 1/3/4)
- ✅ Trilingual UI (ES/EN/NAH — Classical Nahuatl) across all 45 web components
- ✅ DOF daily scraper wired to Celery Beat (7 AM)
- ✅ Dual storage backend (local dev / Cloudflare R2)
- ✅ ES resilience (retry/timeout/pooling), Sentry integration
- ✅ JSON-LD structured data (schema.org Legislation)
- ✅ Docker Compose healthchecks
- ✅ Vitest suite: 36 tests across 5 files (admin)

---

## Completed: Phases 8-9 — Surface & Search Intelligence ✅

- ✅ law_type field on Law model (migration 0006+0007), backfilled 18,439 non-legislative
- ✅ Faceted search: ES aggregations (by_tier, by_category, by_status, by_law_type, by_state)
- ✅ Browse by category (/categorias/) and state (/estados/) with API-backed counts
- ✅ Related laws (/laws/{id}/related/) using ES more_like_this + DB fallback
- ✅ Categories API (/categories/) with real DB counts
- ✅ Sort param on LawListView (name_asc/desc, date_desc/asc, article_count)
- ✅ Spanish URL paths (/leyes, /busqueda, /comparar) with 301 redirects
- ✅ Hierarchical TOC (tree/flat toggle), citation copy, search UX enhancements
- ✅ DashboardStats 6-card grid, tier/law_type badges on search results

---

## Completed: Phases 10-11 — Professional Polish & User Magnet ✅

- ✅ SEO hardening: canonical URLs, alternates (es/en/x-default), WebSite + Organization JSON-LD, expanded sitemap
- ✅ Cross-reference panel (outgoing + incoming refs, confidence threshold)
- ✅ Version timeline (collapsible, change_summary, valid_to)
- ✅ 6-format export (TXT/PDF/LaTeX/DOCX/EPUB/JSON) with tier-based rate limits (anon: 10/hr, free: 30/hr, premium: 100/hr)
- ✅ Word-level compare diff (green=added, red=removed, blue=unique)
- ✅ Cmd+K global search overlay with debounced suggestions
- ✅ Citation + BibTeX export from article viewer
- ✅ Dynamic OG images per law (Next.js ImageResponse)
- ✅ Homepage refresh: FeaturedLaws, QuickLinks, trilingual headings
- ✅ About page (/acerca-de) with data sources, methodology, contact

---

## Next Sprint: Phase 12 — Production & Expansion

**Sprint Goal**: Ship to production and begin municipal expansion.

| # | Task | Priority | Notes |
|---|------|----------|-------|
| 1 | Production go-live at tezca.mx | High | Infrastructure code done, manual provisioning remaining |
| 2 | Municipal scraper: Guadalajara + Monterrey content | High | Content download implemented, needs execution |
| 3 | CONAMER CNARTyS integration exploration | Medium | 113,373 regulations — assess API/bulk access |
| 4 | Embeddings/vector search integration | Medium | Semantic search for legal queries |
| 5 | ES search quality: spanish_legal analyzer tuning | Medium | Synonym list, stemmer tuning |
| 6 | Federal Reglamentos expansion (150 → 800) | Low | Spider works, need to discover remaining URLs |

**Backlog (Future Sprints):**
- Remaining 25+ municipal scraper implementations (Tier 2: state capitals)
- State Periodicos Oficiales scrapers
- SCJN Jurisprudencia scraper (~500K judicial instruments)
- SIL legislative tracking integration
- International Treaties — SRE (~1,500 treaties)
- ~~Comparison tool UI~~ (completed Feb 2026)
- Auto-update system (DOF monitoring → parse → ingest → index cycle)

---

## Phase 4: Municipal Coverage 🏘️ IN PROGRESS

**Timeline**: Q2-Q4 2026 (6-12 months)
**Coverage Target**: +500-2,000 laws
**Current**: 208 municipal laws scraped (5 tier-1 cities), CDMX fully operational

### Tier 1: Major Cities (Q2 2026)
- **Cities**: CDMX, Guadalajara, Monterrey, Puebla, Tijuana, León
- **Target**: 6 largest municipalities (~500 laws)
- **Approach**: Custom scrapers with content download (implemented), municipal partnerships
- **Progress**: CDMX complete (217 laws), other 5 cities have catalog scrapers + content download
- **Timeline**: 3-4 months

### Tier 2: State Capitals (Q3 2026)
- **Cities**: All 32 state capitals
- **Target**: ~1,000 laws
- **Approach**: Systematic scraping, standardized templates
- **Timeline**: 2-3 months

### Tier 3: Top 100 (Q4 2026)
- **Cities**: Next 90 most populous municipalities
- **Target**: ~2,000 laws
- **Approach**: Automated pipeline, bulk processing
- **Timeline**: 3-4 months

### Long-Term: Full Coverage (2027-2028)
- Remaining ~2,300 municipalities
- Crowdsourcing and community contributions
- OCR for non-digitized documents
- 2-3 year timeline to 100%

---

## Phase 5: Advanced Features 🚀 VISION

**Timeline**: 2026-2027  
**Goal**: Platform intelligence and computational law

### Computational Law Features
- **Tax Calculator**: Re-enable Catala/OpenFisca engine
- **Compliance Checker**: Automated contract verification
- **Legal Reasoning**: AI-powered legal research assistant
- **Citation Network**: Visualize legal interconnections
- **Precedent Matching**: Find related cases and rulings

### Platform Intelligence
- **Auto-Updates**: Monitor DOF daily, auto-ingest new laws
- **Version Diffing**: Visual comparison of law changes
- **Translation**: English/Spanish toggle for all laws
- **Annotations**: User bookmarking and notes
- **Sharing**: Deep links to specific articles
- **Alerts**: Subscribe to law changes in areas of interest

### Developer Tools
- **WebHooks**: Real-time law change notifications
- **GraphQL API**: Flexible query interface
- **Bulk Download**: Dataset exports (XML/JSON/CSV)
- **Embeddings**: Vector search for semantic legal research
- **SDK**: Client libraries (Python, JavaScript, etc.)

---

## Phase 6: Legal Knowledge Graph

**Timeline**: 2026-2027
**Goal**: Transform 33K+ cross-references into an interactive legal knowledge graph
**Research**: See `docs/research/Open Source Legal Data Graph.md`

### Phase 6.1: Graph Visualization (Sigma.js + existing data) 🔄 IN PROGRESS
- Interactive WebGL network graph of law cross-references
- Per-law ego graph API (`/api/v1/laws/{id}/graph/`)
- Global overview API (`/api/v1/graph/overview/`)
- Sigma.js + Graphology frontend with ForceAtlas2 layout
- Node color by tier, size by reference count, edge width by weight
- Route: `/grafo/` (Spanish convention)

### Phase 6.2: Enriched Edge Types + NLP
- Edge type taxonomy (cites, modifies, derogates, defines, supersedes, references)
- spaCy NER activation for legal entity detection
- Improved cross-reference resolution (62.8% → 80%+)
- Abbreviation index from Law.short_name

### Phase 6.3: Temporal Graph
- Amendment chain API from LawVersion records
- Point-in-time legal state queries
- Temporal slider for graph visualization

### Phase 6.4: Embeddings + Graph Analytics
- Activate dormant EmbeddingGenerator (paraphrase-multilingual-mpnet-base-v2)
- ES dense_vector field + semantic search endpoint
- NetworkX centrality + PageRank on cross-reference data
- Community detection (Louvain) visualization

### Phase 6.5: NebulaGraph (if justified by 6.4 evaluation)
- Only if PostgreSQL proves insufficient at scale
- Threshold: 500K+ edges or real-time path-finding requirement
- Current assessment: 33K edges well within PostgreSQL capacity

---

## Success Metrics

### 6-Month Goals (Aug 2026)
- ✅ **Coverage**: 93.9% legislative + 77.9% non-legislative (30,343 total)
- ✅ **Quality**: 97.9% → 98.5%+
- ✅ **Municipal**: 0 → 500 laws (Tier 1)
- ✅ **Users**: 10,000+ monthly active users
- ✅ **API**: 100,000+ monthly calls
- ✅ **Search**: <500ms latency
- ✅ **Uptime**: 99.5%+

### 2-Year Vision (2028)
- ✅ **Coverage**: 95%+ of Mexican legal system
- ✅ **Municipal**: 8,000+ ordinances (80% coverage)
- ✅ **Users**: 100,000+ monthly active users
- ✅ **International**: Expand to other Latin American countries
- ✅ **Revenue**: Sustainable API monetization model
- ✅ **Team**: 5-10 full-time contributors

---

## Priority Matrix

### High Priority (Next 3 Months)
1. ⭐⭐⭐ Production go-live at tezca.mx (1-2 weeks)
2. ⭐⭐⭐ Municipal pilot — Tier 1 cities (3-4 months)
3. ⭐⭐ CONAMER CNARTyS integration (113K regulations)

### Medium Priority (3-6 Months)
4. ⭐⭐ Legal Knowledge Graph — Phase 6.1 (graph visualization)
5. ⭐⭐ ES search quality tuning (spanish_legal analyzer)
6. ⭐⭐ Federal Reglamentos expansion (150 → 800)

### Low Priority (6-12 Months)
7. ⭐ Tax calculator (Catala — experimental/blocked)
8. ⭐ Legal Knowledge Graph — Phase 6.4 (embeddings + vector search)
9. ⭐ GraphQL API / SDK

### Completed (Phases 1-11) ✅
- ✅ State law processing (93.7%)
- ✅ Non-legislative state laws (77.9%)
- ✅ Public UI/UX (Phases 3-11: all features built)
- ✅ Admin panel (5 pages)
- ✅ Comparison tool, trilingual UI, faceted search, export, Cmd+K, citation, SEO

---

## Resource Requirements

### Current Team
- 1 full-time engineer/architect
- Community contributors (open source)

### Ideal Team (12 months)
- 2 backend engineers
- 2 frontend engineers  
- 1 data engineer
- 1 designer/UX
- 1 legal domain expert

### Budget Estimates
- **Infrastructure**: $500-1,000/month (AWS/GCP)
- **Tools**: $200/month (monitoring, analytics)
- **Legal**: $500/month (consultation, verification)
- **Total**: ~$15,000/year minimum

---

## Risk Assessment

### Technical Risks
- ⚠️ **Elasticsearch scale**: Mitigation = cluster optimization
- ⚠️ **Word conversion**: Mitigation = manual fallback
- ⚠️ **Municipal data gaps**: Mitigation = partnerships, OCR

### Operational Risks
- ⚠️ **Bus factor**: Mitigation = documentation, team expansion
- ⚠️ **DOF API changes**: Mitigation = monitoring, adapters
- ⚠️ **Data accuracy**: Mitigation = quality metrics, user reports

### Business Risks
- ⚠️ **Monetization**: Mitigation = freemium API, partnerships
- ⚠️ **Competition**: Mitigation = open source, quality focus
- ⚠️ **Legal liability**: Mitigation = disclaimers (implemented), official sources, terms & conditions

---

## How to Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Focus Areas**:
- Municipal law collection
- UI/UX improvements
- API client libraries
- Documentation
- Translation
- Bug reports

---

## Documentation

- **[Strategic Overview](docs/strategy/STRATEGIC_OVERVIEW.md)**: Comprehensive vision and architecture
- **[Mexican Legal Universe](docs/data/MEXICAN_LEGAL_UNIVERSE.md)**: Complete 7-tier taxonomy (~670K+ instruments)
- **[Partnership Directory](docs/data/PARTNERSHIP_DIRECTORY.md)**: Institutional contacts, legal obligations, FOIA reference
- **[Escalation Playbook](docs/dataops/ESCALATION_PLAYBOOK.md)**: 5-tier data acquisition escalation process
- **[State Laws Report](docs/research/STATE_LAW_SCRAPING_REPORT.md)**: 4-week state processing plan
- **[Ingestion Fixes](docs/research/INGESTION_FIXES.md)**: Pipeline improvements
- **[OJN Strategy](docs/research/OJN_SCRAPING_STRATEGY.md)**: State law scraping guide

---

**Questions? Issues?**  
https://github.com/madfam-org/tezca/issues

**Let's democratize access to Mexican law.** 🚀
