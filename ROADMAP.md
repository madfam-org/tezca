# Leyes Como Código - Product Roadmap

**Last Updated**: 2026-02-06
**Current Status**: 93.9% Legislative Coverage (11,904 laws)
**Data Motor**: Pipeline fix complete (state/municipal AKN parsing + unified indexer)
**DataOps**: Protocol implemented (gap tracking, health monitoring, coverage dashboard)

---

## Vision

**Build the definitive platform for Mexican legal research** - complete coverage of federal, state, and municipal laws with gorgeous, intuitive interfaces for everyone from legal professionals to curious citizens.

---

## Current Status (Feb 2026)

### ✅ Achievements
- **11,904 laws** in database (333 federal + 11,363 state + 208 municipal)
- **93.9% legislative coverage** (11,696 of 12,456 leyes vigentes)
- **98.9% parser accuracy** (world-class quality)
- **860,000+ articles** indexed and searchable
- **Production-ready** backend infrastructure
- **Full-stack Testing** (82 Vitest + 203 Pytest)

### 🔄 In Progress
- UI/UX Transformation (Phase 3)
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
- ✅ **Bilingual Toggle**: ES/EN language switch for legal pages and footer
- ✅ **Comparison Tool**: Side-by-side law comparison with sync scroll, metadata panel, mobile tabs
- ✅ **Mobile**: Fully responsive design (44px touch targets, responsive tabs, stacked layouts)
- ✅ **Dark Mode**: Complete theme support
- ✅ **Visual QA**: Sticky footer, Suspense fallback spinners, tab tooltips, WCAG 2.1 AA touch targets

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

## Next Sprint: Data Expansion + Search Quality

**Sprint Goal**: Expand data coverage and improve search quality once the pipeline is running.

| # | Task | Priority | Notes |
|---|------|----------|-------|
| 1 | Municipal scraper: Guadalajara + Monterrey content download | High | Content download now implemented |
| 2 | Federal Reglamentos scraper (diputados.gob.mx/LeyesBiblio/regla.htm) | High | ~800 instruments, similar portal to Tier 1 |
| 3 | ES search quality: spanish_legal analyzer tuning, synonym list | Medium | -- |
| 4 | DOF daily monitoring scraper (replace stub) | Medium | -- |
| 5 | CONAMER CNARTyS integration exploration | Medium | 113,373 regulations — assess API/bulk access |
| 6 | Embeddings/vector search integration | Low | -- |
| 7 | Coverage dashboard: admin UI integration | Low | -- |

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

## Success Metrics

### 6-Month Goals (Aug 2026)
- ✅ **Coverage**: 87% → 95%+ (add 1,000+ laws)
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
1. ⭐⭐⭐ Complete state law processing (4 weeks)
2. ⭐⭐⭐ Public UI/UX overhaul (6-8 weeks)
3. ⭐⭐ Admin panel completion (3-4 weeks)

### Medium Priority (3-6 Months)
4. ⭐⭐ Municipal pilot (Tier 1 cities)
5. ⭐⭐ Auto-update system (DOF monitoring)
6. ✅ ~~Comparison tool implementation~~ (completed Feb 2026)

### Low Priority (6-12 Months)
7. ⭐ Tax calculator (Catala fix)
8. ⭐ Citation network visualization
9. ⭐ Translation feature

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
https://github.com/madfam-org/leyes-como-codigo-mx/issues

**Let's democratize access to Mexican law.** 🚀
