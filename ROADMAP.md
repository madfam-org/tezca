# Leyes Como Código - Product Roadmap

**Last Updated**: 2026-02-03  
**Current Status**: 87% Coverage (11,667 laws)

---

## Vision

**Build the definitive platform for Mexican legal research** - complete coverage of federal, state, and municipal laws with gorgeous, intuitive interfaces for everyone from legal professionals to curious citizens.

---

## Current Status (Feb 2026)

### ✅ Achievements
- **11,667 laws** in database (330 federal + 11,337 state)
- **87% coverage** of Mexican legal system
- **98.9% parser accuracy** (world-class quality)
- **550,000+ articles** indexed and searchable
- **Production-ready** backend infrastructure
- **Full-stack Testing** (Vitest + Pytest)

### 🔄 In Progress
- UI/UX Transformation (Phase 3)
- Municipal pilot planning

---

## Phase 1: Federal Foundation ✅ COMPLETE

**Timeline**: Completed  
**Coverage**: 330/336 laws (99.1%)

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

## Phase 3: UI/UX Transformation 🔄 IN PROGRESS

**Timeline**: 6-8 weeks (Mar-Apr 2026)
**Goal**: World-class user experience

### Public Interface Redesign
- ✅ **Homepage**: Gorgeous first impression with live stats and dashboard
- ✅ **Search**: Advanced filters (Date Range), autocomplete, previews
- ✅ **Law Detail**: Rich pages with versions, citations, downloads (v2.0)
- 🔄 **Comparison Tool**: Side-by-side law comparison (killer feature)
- 🔄 **Mobile**: Fully responsive design
- 🔄 **Dark Mode**: Complete theme support

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

## Phase 4: Municipal Coverage 🏘️ PLANNED

**Timeline**: Q2-Q4 2026 (6-12 months)  
**Coverage Target**: +500-2,000 laws

### Tier 1: Major Cities (Q2 2026)
- **Cities**: CDMX, Guadalajara, Monterrey, Puebla, Tijuana, etc.
- **Target**: 10 largest municipalities (~500 laws)
- **Approach**: Custom scrapers, municipal partnerships
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
6. ⭐ Comparison tool implementation

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
- ⚠️ **Legal liability**: Mitigation = disclaimers, official sources

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
- **[State Laws Report](docs/research/STATE_LAW_SCRAPING_REPORT.md)**: 4-week state processing plan
- **[Ingestion Fixes](docs/research/INGESTION_FIXES.md)**: Pipeline improvements
- **[OJN Strategy](docs/research/OJN_SCRAPING_STRATEGY.md)**: State law scraping guide

---

**Questions? Issues?**  
https://github.com/madfam-org/leyes-como-codigo-mx/issues

**Let's democratize access to Mexican law.** 🚀
