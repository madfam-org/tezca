# Leyes Como Código - Product Roadmap

**Last Updated**: 2026-04-27
**Current Status**: 35,277 laws, 3.5M+ ES articles, 33,380+ cross-references
**Data Motor**: Pipeline fix complete (state/municipal AKN parsing + unified indexer)
**DataOps**: Protocol implemented (gap tracking, health monitoring, coverage dashboard)
**Codebase Audit**: Full audit completed 2026-03-20 — see [Codebase Audit](#codebase-audit-2026-03-20) section
**Strategy Layer**: Feature-parity plan landed 2026-04-27 — see [`docs/strategy/INDEX.md`](docs/strategy/INDEX.md) for the canonical source of "what's in flight." Tracks 1–8 (PRs #46–52) shipped same day.

---

## Vision

**Build the definitive platform for Mexican legal research** - complete coverage of federal, state, and municipal laws with gorgeous, intuitive interfaces for everyone from legal professionals to curious citizens.

---

## Current Status (Apr 2026)

### ✅ Achievements
- **35,277 laws** in database (1,931 federal + 30,907 state + 2,439 municipal)
- **93.9% legislative coverage** (11,696 of 12,456 leyes vigentes)
- **98.9% parser accuracy** (world-class quality)
- **3.5M+ articles** indexed in Elasticsearch
- **Production-ready** backend infrastructure (K8s, HPA, cosign-signed images)
- **Full-stack Testing** (**1,527** backend + **761** web Vitest + 82 admin Vitest + 89 E2E + 18 MCP — as of 2026-04-27)
- **6-tier access control** with billing (Dhanam), trials, webhooks, API keys
- **16-tool MCP server** published to PyPI for AI agent consumption
- **24+ Celery Beat tasks** including new `rmf-quarterly-scrape` (Track 1)
- **Graph visualization** (Sigma.js, ego graph, global overview, public showcase)
- **Judicial corpus** (SCJN jurisprudencia + tesis aisladas via API + Playwright scrapers)
- **First-party AI assistant** scaffold (`/api/v1/chat/preguntar/`, Selva-routed, gated by `CHAT_ENABLED=false` until Selva onboarding lands)
- **SAT regulatory feed** (`apps/scraper/federal/rmf_scraper.py`) — annual RMF + quarterly modifications + annexes; Karafiel-ready
- **Customer billing UI** scaffold (`/cuenta/billing`) — Dhanam-delegated, gated by `MONETIZATION_ENABLED=false`
- **State coverage** at 16/32 (Wave 1A added Aguascalientes, Hidalgo, Morelos, Yucatán)

### 🔄 In Progress
- Operator unblockers: Stripe live keys, Selva onboarding, classify_law_domains backfill verification
- Wave 1B state scrapers (8 medium-complexity states → 16/32 to 24/32)
- `/preguntar` chat UI (frontend follow-up; backend ready)
- Municipal pilot planning (Tier 1: 6 major cities)
- Karafiel integration runtime test (joint with Karafiel team)

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

## Completed Sprint: Q3-2026 Feature Parity (Tracks 1–8, 2026-04-27) ✅

**Sprint Goal**: Close the parity gaps identified in the 2026-04-27 competitive benchmark by leveraging MADFAM ecosystem primitives (Selva, Dhanam, CNPG, Karafiel-as-customer) instead of building greenfield. Source-of-truth: [`docs/strategy/FEATURE_PARITY_PLAN_2026-04-27.md`](docs/strategy/FEATURE_PARITY_PLAN_2026-04-27.md).

### Shipped (8 PRs, single session — #46 through #52)

| Track | PR | Deliverable |
|---|---|---|
| 1 — RMF recovery | #46 | SAT scraper + ingest command + quarterly Celery beat + 20 tests. Karafiel's compliance feed unblocked. |
| 2 — `/preguntar` chat | #47 | Selva-routed RAG-over-corpus chat at `/api/v1/chat/preguntar/`. Four gating layers, mockable client, 19 tests. |
| 3 — State scrapers Wave 1A | #50 | Aguascalientes, Hidalgo, Morelos, Yucatán. Coverage 12/32 → 16/32. 45 parametrized tests. |
| 4 — Billing UI | #51 | `/cuenta/billing` with Dhanam-delegated portal + invoice history. 11 tests. Tezca holds zero Stripe keys. |
| 5 — Karafiel integration audit | #48 | Tezca-side readiness verified. P0: domain-classification ≥95% before Karafiel goes live (operator SQL queries provided). |
| 6 — CNPG migration prep | #52 | Postgres connection-pool knobs (connect_timeout, keepalives, CONN_MAX_AGE). Cutover runbook. Gated on RFC 0012. |
| 7 — docket-watcher bootstrap | #52 | Spec for `madfam-org/docket-watcher` sibling repo (Q1-2027 scheduled). Architecture, layout, pricing tiers. |
| 8 — Selva onboarding ticket | #49 | Operator-side spec for `tezca-selva-relay` Janua client. Unblocks `CHAT_BACKEND=selva` flip. |

### Strategic outcome

Tezca closes every "missing-vs-competitors" capability while preserving every "unique-to-Tezca" moat (MCP, public API at low tiers, A-F quality grading, AGPL self-hosting, cross-reference graph, trilingual UI). The remaining work is operator-only: Stripe credentialing, Selva provisioning, Karafiel timeline, RFC 0012 cluster shipping.

### Cross-references
- [`docs/strategy/INDEX.md`](docs/strategy/INDEX.md) — strategy doc index
- [`docs/strategy/COMPETITIVE_BENCHMARK_2026-04-27.md`](docs/strategy/COMPETITIVE_BENCHMARK_2026-04-27.md) — gap analysis
- [`docs/strategy/FEATURE_PARITY_PLAN_2026-04-27.md`](docs/strategy/FEATURE_PARITY_PLAN_2026-04-27.md) — track-by-track plan

---

## Next Sprint: Wave 1B — State Coverage 16/32 → 24/32

**Sprint Goal**: Continue closing the state-scraper gap. 8 medium-complexity states (HTML + JS-rendered, no WAFs).

### Targets (suggested)

| State | Portal | Complexity |
|---|---|---|
| Coahuila | congresocoahuila.gob.mx | Medium |
| Guanajuato | congresogto.gob.mx | Medium |
| Jalisco | congresojal.gob.mx | Medium |
| Puebla | congresopuebla.gob.mx | Medium |
| Sinaloa | congresosinaloa.gob.mx | Medium |
| Sonora | congresoson.gob.mx | Medium |
| Tamaulipas | congresotamaulipas.gob.mx | Medium |
| Veracruz | legisver.gob.mx | Medium |

Each state follows the existing `apps/scraper/state/baja_california.py` template + Wave 1A extension. Add to `run_state_scraper` dispatch table; flip Beat schedules per-state after first manual green run.

**Wave 1C** (Q1-2027 scheduled): 8 hostile states needing Playwright/madfam-crawler delegation.

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
- ~~SCJN Jurisprudencia scraper~~ (implemented: API + Playwright, weekly Beat task)
- SIL legislative tracking integration
- International Treaties — SRE (~1,500 treaties)
- ~~Comparison tool UI~~ (completed Feb 2026)
- ~~Auto-update system~~ (DOF daily wired to Celery Beat, 7 AM)
- Address codebase audit gaps (see [Codebase Audit](#codebase-audit-2026-03-20) below)

---

## Codebase Audit (2026-03-20)

**Scope**: Full codebase exploration — 371 Python files (~40.9K LOC), ~272 TSX files, 17 K8s manifests, 7 CI workflows.

### Platform Inventory

| Component | Files | LOC | Key Stats |
|-----------|-------|-----|-----------|
| API (Django + DRF) | 70 | 8,606 | 40+ endpoints, 6-tier auth, 14 management commands |
| Scrapers | 47 | 10,581 | Federal (11), State (12), Municipal (10), Judicial (2), Playwright (3) |
| Parsers | 19 | 3,708 | 5-stage pipeline, A-F quality grading, 6 cross-ref patterns |
| Web frontend | ~272 | — | 16 routes (Spanish), 78 components, 9 lib modules |
| Admin panel | ~30 | — | 5 pages, 17 components, Janua-protected |
| Shared packages | 4 | — | @tezca/lib (types), @tezca/ui (7 primitives), @tezca/api-client (stub), tezca-mcp (16 tools) |
| Tests | 86 (py) + 77 (ts) + 15 (e2e) | ~10K+ | 1,234 backend + 643 web + 72 admin + 89 E2E + 18 MCP |
| Scripts | 69 | ~8K | Ingestion (26), scraping (22), dataops (5), validation (6), utility (8) |
| K8s manifests | 17 | — | Deployments, HPAs, PDBs, PVCs, services, secrets |
| CI workflows | 7 | — | ci, deploy-api, deploy-web, deploy-admin, publish-mcp, publish-sdk, codeql |

### What's Complete (Beyond Roadmap Documentation)

Several features listed under "Phase 5: Vision" are already implemented:

| Feature | Status | Implementation |
|---------|--------|----------------|
| Auto-Updates (DOF monitoring) | ✅ Done | `dof_daily.py` + Celery Beat (7 AM daily) |
| Annotations & Bookmarks | ✅ Done | `Annotation` model, `AnnotationPanel.tsx`, `BookmarksContext.tsx` |
| Alerts (subscribe to law changes) | ✅ Done | `UserAlert` model, `AlertButton.tsx`, `notification_views.py` |
| Deep links to articles | ✅ Done | Hash navigation (`#article-*`) in `LawDetail.tsx` |
| WebHooks | ✅ Done | `WebhookSubscription` model, HMAC-SHA256 signing, SSRF protection |
| Bulk Download | ✅ Done | `bulk_views.py`, tier-gated (`RequireFeature.of("bulk_download")`) |
| SDK (JavaScript) | 🔄 Stub | `@tezca/api-client` published but incomplete; real client = `apps/web/lib/api.ts` |
| Citation Network | ✅ Done | `CrossReference` model, `cross_reference_views.py`, `CrossReferencePanel.tsx` |
| SCJN Jurisprudencia | ✅ Done | `JudicialRecord` model, API + Playwright scrapers, weekly Beat task |
| Graph visualization | ✅ Done | Sigma.js, ego graph + overview + showcase APIs, `/grafo/` route |
| MCP server for AI agents | ✅ Done | 16 tools, published to PyPI, 18 tests |
| Billing & trials | ✅ Done | Dhanam webhook, 3/21-day trials, `TierGate` (4 variants) |

### Identified Gaps & Technical Debt

#### 🔴 Critical (Infrastructure Resilience)

| # | Gap | Impact | Mitigation |
|---|-----|--------|------------|
| 1 | **Single-node ES in production** | K8s manifest: single-node, 512MB JVM for 3.5M articles. Node failure = full search outage (graceful degradation returns empty, not errors) | Add ES clustering or increase JVM heap; evaluate managed ES |
| 2 | **Single-node PostgreSQL & Redis** | No HA. PDBs protect app pods but not data stores | Evaluate managed PG (RDS/CloudSQL) or PostgreSQL HA operator |
| 3 | **No backup/restore strategy** | No pg_dump schedule, no ES snapshot policy, no disaster recovery runbook in codebase | Add scheduled backups + test restore procedure |
| 4 | **ES JVM mismatch** | Dev: 2GB heap; K8s: 512MB heap for same dataset. Likely causes OOM/GC pressure in production | Align K8s ES heap to at least 1GB, ideally 2GB |
| 5 | **Deploy workflow race conditions** | Digest commits can race with subsequent pushes. 3-retry loop is a workaround | Evaluate atomic kustomization update or GitOps controller |

#### 🟡 Important (Quality & Coverage)

| # | Gap | Impact | Mitigation |
|---|-----|--------|------------|
| 6 | **Test coverage floor at 44%** | `--cov-fail-under=44` is low for a legal data platform. Edge cases in tier gating, export, webhook delivery may be uncovered | Incrementally raise to 60%, prioritize tier_permissions and export coverage |
| 7 | **20/32 states without dedicated scrapers** | Only ~12 state-specific scrapers. Other states rely on generic OJN bulk or have no dedicated implementation | Prioritize by population: create scrapers for top-10 uncovered states |
| 8 | **No quality quarantine** | Grade D/F laws indexed identically to Grade A. Low-quality parses with broken article detection serve incorrect content | Add pipeline gate: Grade D/F → manual review queue, not auto-indexed |
| 9 | **Cross-reference false positives** | All confidence levels (0-1) stored and displayed. No filtering threshold | Add minimum confidence floor (0.3) for display; keep all in DB for analysis |
| 10 | **Data integrity E2E tests not in CI** | `DATA_INTEGRITY_E2E=1` and `UI_FIDELITY_E2E=1` tests gated behind env flags, never run in default CI | Run these in a nightly CI schedule against staging |
| 11 | **No migration check in CI** | CI runs pytest but never runs `makemigrations --check` to detect drift | Add `python manage.py makemigrations --check --dry-run` to ci.yml |
| 12 | **Admin endpoints in OpenAPI schema** | Admin routes in same `urls.py`, discoverable via `drf-spectacular` | Exclude admin URLs from schema generation |

#### 🟢 Recommended (Developer Experience & Polish)

| # | Gap | Impact | Mitigation |
|---|-----|--------|------------|
| 13 | **@tezca/api-client is a stub** | Published to npm but incomplete. Real API client = `apps/web/lib/api.ts` (350+ LOC). SDK consumers get empty package | Generate from OpenAPI spec or extract web client into api-client package |
| 14 | **No committed OpenAPI spec** | `drf-spectacular` generates dynamically but no `openapi.yaml` in repo | Add `spectacular` management command to CI, commit spec |
| 15 | **No load testing in CI** | k6 scripts exist in `tests/load/` but never run. No perf regression detection | Add periodic k6 runs against staging in nightly CI |
| 16 | **MCP server thin test coverage** | 18 tests for 16 tools + 3 resources + 3 prompts | Expand to cover error paths, pagination, rate limiting |
| 17 | **Webhook disable without notification** | Webhooks auto-disable after 10 failures, subscriber never notified | Send email/notification on disable, add re-enable API |
| 18 | **No offline/PWA support** | Legal reference tool without offline access to viewed laws | Evaluate service worker for caching viewed law detail pages |
| 19 | **Comparison hard-limited to 2 laws** | Multi-law comparison (e.g., same article across 5 state constitutions) not possible | Extend comparison to N laws with horizontal scroll or grid layout |
| 20 | **No API versioning strategy** | All endpoints under `/api/v1/`. No plan for breaking changes | Document versioning policy; consider header-based versioning for v2 |
| 21 | **Celery monitoring** | No Flower or equivalent. Admin `JobMonitor` polls `/admin/jobs/` but unclear depth | Add Flower or integrate Celery task state into admin metrics |
| 22 | **Frontend re-render cascading** | 5+ React contexts (Language, Auth, Bookmarks, Comparison, trial polling) with no memoization strategy | Profile with React DevTools; consider context splitting or Zustand for high-frequency state |

### Architecture Strengths (Preserve These)

These patterns are well-designed and should be maintained:

1. **Single source of truth for tiers** — `tier_permissions.py` centralizes all naming, ranking, features, rates, formats
2. **Zero-downtime ES reindexing** — Alias-based versioning with atomic swap (`es_index_manager.py`)
3. **Graceful ES degradation** — Returns 200 + `degraded: true` instead of 500s
4. **SSRF webhook protection** — URL validation against private/reserved IPs at creation and delivery
5. **Zero-touch integration policy** — No hardcoded client references, all via API keys + webhooks
6. **Pluggable storage** — Local/R2 with transparent fallback (`storage.py`)
7. **Pipeline error tracking** — `ErrorTracker` with per-stage categorization and structured logging
8. **Batch cross-reference loading** — `useBatchCrossRefs` hook eliminates N+1 (200 IDs per chunk)
9. **Tier-gating components** — `TierGate` with 4 variants (inline, overlay, card, toast), i18n, countdown
10. **Comprehensive Celery Beat automation** — 20 scheduled tasks covering scraping, pipeline, health, trials

### Codebase Metrics Snapshot

```
Python files:        371        Test files (py):     86
TypeScript files:    ~272       Test files (ts):     77
E2E spec files:      15         E2E tests:           89 (4 browsers)
K8s manifests:       17         CI workflows:        7
Management commands: 14         Celery Beat tasks:   20
API endpoints:       40+        Scraper modules:     47
MCP tools:           16         Export formats:      6
Django models:       14         React contexts:      5
```

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

## Phase 5: Advanced Features 🚀 PARTIALLY COMPLETE

**Timeline**: 2026-2027
**Goal**: Platform intelligence and computational law

### Computational Law Features
- **Tax Calculator**: Re-enable Catala/OpenFisca engine (blocked — experimental)
- **Compliance Checker**: Automated contract verification (future)
- **Legal Reasoning**: AI-powered legal research assistant (future — MCP server is foundation)
- ✅ **Citation Network**: 33K+ cross-references with graph visualization (Sigma.js)
- ✅ **Precedent Matching**: SCJN judicial corpus with search + related laws API

### Platform Intelligence
- ✅ **Auto-Updates**: DOF daily wired to Celery Beat (7 AM), 20 scheduled tasks
- ✅ **Version Diffing**: Word-level comparison tool with diff highlighting
- ✅ **Translation**: Trilingual (ES/EN/NAH — Classical Nahuatl) across all components
- ✅ **Annotations**: User bookmarking (`BookmarksContext`), notes (`AnnotationPanel`), color-coded highlights
- ✅ **Sharing**: Deep links to articles (`#article-*`), social sharing (Twitter, LinkedIn, WhatsApp, email)
- ✅ **Alerts**: `UserAlert` model with law/category/state subscriptions, in-app + email delivery

### Developer Tools
- ✅ **WebHooks**: `WebhookSubscription` model, HMAC-SHA256 signing, SSRF protection, auto-disable after 10 failures
- **GraphQL API**: Not implemented (REST-only, evaluate need vs OpenAPI spec commitment)
- ✅ **Bulk Download**: `bulk_views.py`, tier-gated via `RequireFeature.of("bulk_download")`
- **Embeddings**: Dormant `EmbeddingGenerator` (paraphrase-multilingual-mpnet-base-v2), needs activation
- 🔄 **SDK**: `@tezca/api-client` published to npm but stub; `tezca-mcp` (Python MCP) published to PyPI

---

## Phase 6: Legal Knowledge Graph

**Timeline**: 2026-2027
**Goal**: Transform 33K+ cross-references into an interactive legal knowledge graph
**Research**: See `docs/research/Open Source Legal Data Graph.md`

### Phase 6.1: Graph Visualization (Sigma.js + existing data) ✅ COMPLETE
- ✅ Interactive WebGL network graph of law cross-references
- ✅ Per-law ego graph API (`/api/v1/laws/{id}/graph/`)
- ✅ Global overview API (`/api/v1/graph/overview/`)
- ✅ Public showcase endpoint (`/api/v1/graph/showcase/`, unauthenticated, top 50 nodes)
- ✅ Sigma.js + Graphology frontend with ForceAtlas2 layout
- ✅ Node color by tier, size by reference count, edge width by weight
- ✅ Route: `/grafo/` (Spanish convention)
- ✅ Graph search with autocomplete + camera animation (`GraphSearch.tsx`)
- ✅ Category filter pills (`GraphFilters.tsx`)
- ✅ Collapsible stats panel (`GraphStats.tsx`)
- ✅ PNG export via canvas compositing (`useGraphExport.ts`)

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
- ✅ **Coverage**: 93.9% legislative + 77.9% non-legislative (35,277 total laws)
- ✅ **Quality**: 98.9% parser accuracy
- 🔄 **Municipal**: 208 → 500 laws (Tier 1 cities, in progress)
- 🎯 **Users**: 10,000+ monthly active users
- 🎯 **API**: 100,000+ monthly calls
- 🎯 **Search**: <500ms latency
- 🎯 **Uptime**: 99.5%+
- 🎯 **Test coverage**: 44% → 60% backend
- 🎯 **Infrastructure**: Backup/restore operational, ES heap aligned

### 2-Year Vision (2028)
- 🎯 **Coverage**: 95%+ of Mexican legal system
- 🎯 **Municipal**: 8,000+ ordinances (80% coverage)
- 🎯 **Users**: 100,000+ monthly active users
- 🎯 **International**: Expand to other Latin American countries
- 🎯 **Revenue**: Sustainable API monetization model
- 🎯 **Team**: 5-10 full-time contributors
- 🎯 **State scrapers**: 32/32 dedicated implementations
- 🎯 **SDK**: Fully functional @tezca/api-client + tezca-mcp

---

## Priority Matrix

### High Priority (Next 3 Months)
1. ⭐⭐⭐ Production go-live at tezca.mx (1-2 weeks)
2. ⭐⭐⭐ Backup/restore strategy for PostgreSQL + ES snapshots
3. ⭐⭐⭐ ES production hardening (JVM heap alignment, evaluate clustering)
4. ⭐⭐⭐ Municipal pilot — Tier 1 cities (3-4 months)
5. ⭐⭐ CONAMER CNARTyS integration (113K regulations)
6. ⭐⭐ Raise test coverage floor (44% → 60%, prioritize tiers + export)

### Medium Priority (3-6 Months)
7. ⭐⭐ Quality quarantine for Grade D/F parses (don't auto-index)
8. ⭐⭐ ES search quality tuning (spanish_legal analyzer)
9. ⭐⭐ Federal Reglamentos expansion (150 → 800)
10. ⭐⭐ Complete @tezca/api-client SDK (extract from web client or generate from OpenAPI)
11. ⭐⭐ Add migration check (`makemigrations --check`) + nightly data integrity E2E to CI
12. ⭐⭐ State scraper expansion (top 10 uncovered states by population)

### Low Priority (6-12 Months)
13. ⭐ Tax calculator (Catala — experimental/blocked)
14. ⭐ Legal Knowledge Graph — Phase 6.4 (embeddings + vector search)
15. ⭐ Offline/PWA support for viewed law pages
16. ⭐ Multi-law comparison (extend beyond 2-law limit)
17. ⭐ Celery monitoring (Flower or equivalent)
18. ⭐ API versioning strategy documentation
19. ⭐ Webhook disable notification + re-enable API

### Completed (Phases 1-11 + audit reconciliation) ✅
- ✅ State law processing (93.7%)
- ✅ Non-legislative state laws (77.9%)
- ✅ Public UI/UX (Phases 3-11: all features built)
- ✅ Admin panel (5 pages)
- ✅ Comparison tool, trilingual UI, faceted search, export, Cmd+K, citation, SEO
- ✅ Graph visualization (Phase 6.1: Sigma.js, search, filters, stats, PNG export)
- ✅ DOF auto-updates (Celery Beat, 7 AM daily)
- ✅ Annotations, bookmarks, alerts, notifications
- ✅ Webhooks (HMAC-SHA256, SSRF protection)
- ✅ Bulk download (tier-gated)
- ✅ SCJN judicial corpus (API + Playwright scrapers, weekly)
- ✅ MCP server (16 tools, published to PyPI)
- ✅ Billing + trials (Dhanam integration, 3/21-day trials)

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
- 🔴 **Single-node data stores**: ES, PostgreSQL, Redis all single-node in K8s. Node failure = data/search outage. Mitigation = managed services or HA operators, backup/restore strategy
- 🔴 **ES JVM undersized in production**: 512MB heap for 3.5M articles (dev uses 2GB). Mitigation = align heap to workload, monitor GC pressure
- 🔴 **No disaster recovery**: No pg_dump schedule, no ES snapshots, no restore runbook. Mitigation = scheduled backups + tested restore procedure
- ⚠️ **Deploy race conditions**: Digest commits can race. 3-retry workaround. Mitigation = GitOps controller (ArgoCD/Flux) or atomic kustomization updates
- ⚠️ **Low test coverage floor**: 44% minimum allows regressions in tier gating, export, webhook delivery. Mitigation = raise incrementally, prioritize critical paths
- ⚠️ **Quality quarantine gap**: Grade D/F parses auto-indexed, serving potentially broken article content. Mitigation = pipeline gate blocking low-grade laws from ES
- ⚠️ **Municipal data gaps**: Only 208 laws from 5 cities. Mitigation = partnerships, OCR, dedicated scrapers
- ⚠️ **20 states without dedicated scrapers**: Bulk OJN coverage exists but no portal-specific freshness tracking. Mitigation = prioritize by population

### Operational Risks
- ⚠️ **Bus factor**: 1 full-time engineer. Mitigation = documentation (CLAUDE.md, ROADMAP.md), community, team expansion
- ⚠️ **DOF API changes**: Mitigation = monitoring, adapters, DOF daily scraper validates response format
- ⚠️ **Data accuracy**: Mitigation = quality grading, spot-check validation, user reports
- ⚠️ **Celery visibility**: No Flower dashboard. Admin JobMonitor polls but may miss stuck tasks. Mitigation = add dedicated Celery monitoring

### Business Risks
- ⚠️ **Monetization**: Mitigation = 6-tier freemium, Dhanam billing, trial system (3/21 days)
- ⚠️ **Competition**: Mitigation = open source (AGPL-3.0), quality focus, AI-ready (MCP server)
- ⚠️ **Legal liability**: Mitigation = disclaimers, official source attribution, terms & conditions
- ⚠️ **SDK adoption**: Published @tezca/api-client is a stub, may disappoint early adopters. Mitigation = complete SDK or generate from OpenAPI

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
