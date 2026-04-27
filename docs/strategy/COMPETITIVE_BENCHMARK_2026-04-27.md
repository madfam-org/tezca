# Tezca Competitive Benchmark — 2026-04-27

**Author:** Audit session, 2026-04-27. Tezca branch: `main` at commit `121a47a` (post-audit-remediation).
**Triggering question:** "Benchmark our platform against Buho Legal and other platforms in similar and adjacent problem spaces."
**Confidence:** Medium. Web research only; no first-hand product trials of competitors. Prices and feature matrices reflect public marketing pages on the date listed; revisit before any pricing decision.
**Status:** Findings + recommendations. No code or pricing changes made in this session. Action items live in the "Execution checklist" at the bottom.

---

## 1. The space we're actually in

Tezca is **not** competing with Buho Legal. They solve different problems and could plausibly partner.

| Dimension | Tezca | Buho Legal |
|---|---|---|
| Primary unit | Laws, articles, jurisprudence | Court case files (expedientes), name-on-docket alerts |
| Data source | DOF, gazettes, SCJN, CONAMER, scrapers | Court agreement lists ("listas de acuerdos") |
| User question answered | "What does article N of law X say?" | "Did anything happen in case file 123/2026 today?" |
| AI involvement | None first-party today; MCP exposes data to others | None ("does not use AI or predictive analysis") |
| Buyer | Researchers, developers, in-house counsel, AI builders | Litigators tracking active cases |

Lumping these together would mislead positioning. Buho's free tier (5 case-file watches) and Premium ($749–$15,000 MXN/yr) compete with **MiDespacho** and similar docket trackers, not Tezca.

The actual competitive set, in four clusters:

1. **Premium incumbent corpora:** vLex, Tirant Prime
2. **AI-native legal copilots:** Lexius, Help-AI, Maite.ai, Sof-IA (Tirant), Amparo IA, Lexfania
3. **Open data infrastructure:** Tezca, government portals (dof.gob.mx, scjn.gob.mx, ordenjuridico.gob.mx)
4. **Adjacent (not competitors, possible partners/integrations):** Buho Legal, MiDespacho, lawyer-directory products

Tezca currently sits alone in cluster 3, with cluster 1 as the substitution risk for paying users and cluster 2 as the loudest UX-pressure source.

---

## 2. Competitor profiles (what each one actually offers)

### 2.1 Buho Legal — judicial monitoring (NOT a Tezca competitor)
- **What it does:** Monitor up to 5 case files free; premium expands volume. Name-alerts (be notified if you're sued). Search lawyer professional credentials, SAT blacklists, CURP/RFC. Lists of agreements from Federal and State courts.
- **What it does NOT do:** No corpus of laws/articles, no jurisprudence database, no AI, no API as a product.
- **Pricing:** Free for 5 cases. Premium $749–$15,000 MXN/year (volume-banded).
- **Strategic posture toward Tezca:** Could become a customer (if their alerts engine wanted law-text references) or a partner (cross-link case files to relevant laws).

### 2.2 vLex México — incumbent corpus + AI assistant ("Vincent")
- **Coverage:** Federal + state + municipal legislation, jurisprudence (SCJN, Circuit, Electoral, Administrative), gazettes, books/journals, contracts, news. International coverage in 17+ countries.
- **AI:** Vincent — chat over corpus, drafting, citations.
- **Pricing (public approximation):** ~€30–50/mo individual (~$600–1,000 MXN/mo); €200+/mo small-firm; enterprise quote-based.
- **Strengths:** Editorial commentary depth, brand trust with senior firms, multi-country, oldest/largest jurisprudence archive.
- **Weaknesses:** No public API as a product (gated behind enterprise sales), expensive per-seat, slow innovation, content lock-in.

### 2.3 Tirant Prime México — incumbent corpus + Sof-IA assistant
- **Coverage:** Federal/state/municipal legislation (current + consolidated), all gazettes, jurisprudence and "tesis ejecutorias" from federal and circuit tribunals plus other judicial/administrative bodies.
- **AI:** Sof-IA — reads docs while user writes, surfaces relevant laws/forms/jurisprudence/doctrine.
- **Pricing:** Opaque/quote-based. Empirically tends $3–10k MXN/mo for firms.
- **Strengths:** Editorial doctrine library (Tirant lo Blanch publishing), strong with mid-large firms.
- **Weaknesses:** UI dated, pricing opacity is a sales-cycle drag, no developer API.

### 2.4 Lexius — AI-first MX legal copilot
- **Coverage claim:** 2,902 legal texts, 124,850 court decisions updated daily, federal focus.
- **AI:** Voice-enabled "virtual lawyer" with visible reasoning; doc analysis; PowerPoint, podcast, mind-map, song generation.
- **Pricing:** Undisclosed; trial available.
- **Strengths:** Modern UX, demoable AI gimmicks, multi-format export (PDF/Word/Excel).
- **Weaknesses:** Corpus much smaller than vLex/Tirant; data provenance not disclosed; no API.

### 2.5 Help-AI MX — AI agents over MX legal/fiscal corpus
- **Coverage claim:** Federal + 32 states, "30+ specialized agents."
- **Pricing (public):** Estándar $499/mo (2M tokens), Plus $999/mo (10M tokens), Premium $1,999/mo (30M tokens). 5-day free trial; annual = 2 free months.
- **Differentiators:** ISO 42001 (AI management) + ISO 27001 (security) certifications. Access to ChatGPT/Grok/Gemini bundled (Claude on Plus+).
- **Weaknesses:** Pure SaaS chatbot wrapper; no developer surface; corpus quality opaque.

### 2.6 Maite.ai, Sof-IA, Amparo IA, Lexfania
- All variations on "chat over MX legal corpus." Differentiation among them is minor (UI polish, vertical specialization). None ship an API or open infrastructure.

### 2.7 Government portals (DOF, SCJN, ordenjuridico.gob.mx)
- Authoritative source of truth for everything.
- **UI/UX:** circa 1998. No relevance ranking, broken search, no machine-readable bulk export.
- **API:** Effectively none (DOF has a partial JSON endpoint Tezca already uses).
- **Strategic role:** Not a competitor, but our upstream. If a competitor invests in scraping these well, they catch up to us on raw corpus — only Tezca's *quality grading + parsing pipeline + MCP* matter as moats.

---

## 3. Feature matrix

Legend: ✅ has it · 🟡 partial · ❌ missing · "?" undisclosed

| Capability | Tezca | Buho | vLex MX | Tirant | Lexius | Help-AI |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Federal laws | ✅ 30k+ | ❌ | ✅ | ✅ | ✅ ~2,900 | ✅ |
| Full 32-state coverage | 🟡 ~12/32 | n/a | ✅ | ✅ | 🟡 | ✅ claim |
| Municipal regs | ✅ (CDMX +) | ❌ | 🟡 | ✅ | ❌ | 🟡 |
| NOMs | ✅ | ❌ | 🟡 | ✅ | ❌ | 🟡 |
| Treaties | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| CONAMER (regulatory pipeline) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| SCJN jurisprudence | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Cross-references (article-level) | ✅ batch | ❌ | 🟡 | 🟡 | ❌ | ❌ |
| Multi-version timeline (DOF history) | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Quality grading on parsed laws | ✅ A–F + quarantine | ❌ | ❌ | ❌ | ❌ | ❌ |
| Public REST API | ✅ tier-throttled | ❌ | 🟡 enterprise | 🟡 enterprise | ❌ | ❌ |
| **MCP server for AI agents** | ✅ on PyPI | ❌ | ❌ | ❌ | ❌ | ❌ |
| Webhook subscriptions | ✅ HMAC | ❌ | ❌ | ❌ | ❌ | ❌ |
| Bulk export (PDF/JSON/DOCX/EPUB/LaTeX) | ✅ 6 formats | ❌ | 🟡 | 🟡 | ✅ 3 | ✅ |
| Case-file/docket monitoring | ❌ | ✅ core | ❌ | ❌ | ❌ | ❌ |
| Name alerts (SAT/CURP/RFC) | ❌ | ✅ | ❌ | ❌ | ❌ | 🟡 |
| AI assistant / chat-with-corpus | ❌ first-party | ❌ | ✅ Vincent | ✅ Sof-IA | ✅ voice | ✅ 30+ agents |
| Document drafting / templates | ❌ | ❌ | 🟡 | ✅ | ✅ | ✅ |
| OCR ingest of scanned PDFs | ✅ optional | ❌ | ❌ | ❌ | ❌ | 🟡 |
| Trilingual UI (es/en/Nahuatl) | ✅ | ❌ | 🟡 es/en | ❌ es | ❌ es | ❌ es |
| **Open source (AGPL)** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Self-hosting** | ✅ (capped at academic) | ❌ | ❌ | ❌ | ❌ | ❌ |
| Pricing transparency | ✅ public | 🟡 | ✅ | ❌ quote | ❌ | ✅ |
| ISO certs (security/AI) | 🟡 in progress | ❌ | ? | ? | ? | ✅ 27001 + 42001 |

---

## 4. Pricing landscape

| Platform | Entry | Mid | Top |
|---|---|---|---|
| Buho Legal | free (5 cases) | ~$62/mo equiv | $15,000 MXN/yr |
| **Tezca** | **free anon + free_member** | **Essentials $599/mo** | **Institutional $1,999/mo** |
| Help-AI | Estándar $499/mo | Plus $999/mo | Premium $1,999/mo |
| vLex | ~€30/mo (~$700 MXN) individual | ~€200/mo (~$4,500 MXN) firm | enterprise |
| Tirant Prime | undisclosed | undisclosed | enterprise (~$3–10k/mo) |
| Lexius | undisclosed | — | — |

**Read on Tezca's positioning:**
- Essentials at $599 sits between Help-AI Estándar ($499) and Plus ($999). Right band.
- Institutional at $1,999 matches Help-AI Premium and undercuts vLex small-firm by 50%+ and Tirant by ~70%. Aggressive but justified by API surface.
- Community at $199 has no commercial peer — pure differentiator. The only thing close is Buho's free tier, but for a totally different product.

**Confidence on pricing fit: low** (per CLAUDE.md the Tulana v0.2 WTP automation is pending). Don't ratchet prices until PMF score crosses the activation threshold.

---

## 5. Tezca's moats (ranked by defensibility)

### 5.1 Strong moats — invest in these
1. **MCP server on PyPI.** No competitor ships one. As Claude Code, Cursor, Copilot, and in-house agent builders proliferate in MX legal-tech, every AI lawyer product can plug Tezca directly into its agent loop without scraping. Compounds with each new agent framework. **This is the quietest and strongest advantage.**
2. **Public API + webhooks at low tiers.** vLex/Tirant gate API behind enterprise sales. Tezca lets community-tier users self-serve `tzk_*` keys. AI builders on a budget have one place to go.
3. **Quality grading + quarantine pipeline.** A–F grades and D/F auto-quarantine on indexing. Nobody else publishes data quality. AI products desperately need this signal but can't generate it themselves.
4. **AGPL + self-hosting.** Universities, government bodies, and journalism outlets that can't or won't pay vLex have a way to deploy their own.

### 5.2 Medium moats — protect these
5. **Cross-reference graph + Sigma viz.** vLex has citations as text; Tezca has navigable graphs with public showcase access. Hard for competitors to replicate without a parsing pipeline.
6. **CONAMER scraper.** Regulatory pipeline visibility. Niche but no one else has it.
7. **Trilingual including Nahuatl.** Cultural/political signal. No commercial competitor will ever invest here. Cheap to maintain, big optics.

### 5.3 Weak/contested moats — don't bet the company on these
8. Federal corpus completeness — vLex/Tirant match or exceed.
9. UI polish — Lexius wins on demos.
10. Editorial commentary — vLex's moat, not ours.

---

## 6. Tezca's gaps relative to the field

### 6.1 Critical (close in 6 months)
- **State scraper coverage 12/32 → 32/32.** vLex/Tirant/Help-AI all claim full coverage. Until Tezca closes this, "complete Mexican legal corpus" claim has an asterisk that competitors can hammer in sales conversations. **20 missing state scrapers = single biggest credibility gap.**
- **First-party AI assistant ("/preguntar" or similar).** Every paid competitor has one. Tezca's MCP enables external products to use Tezca, but a built-in chat is what 60-second-demo evaluators expect. Plumbing-only project: ES + cross-refs + RAG over a Claude/GPT call. No new infra.

### 6.2 Important (close in 12 months)
- **Case-file/docket monitoring (PJF API + name alerts).** Buho owns this. If Tezca added a thin layer it consolidates the "I want one platform" buyer. Likely highest-ROI feature for paid conversions.
- **Document drafting / templates.** Lexius, Help-AI, Tirant all have these. Tezca has the references + cross-refs + structured articles to power good ones — the data layer is already there.
- **HA infrastructure.** CLAUDE.md flags single-node ES/PG/Redis. Selling Institutional ($1,999/mo) without HA is a credibility gap. vLex/Tirant have multi-region. Multi-AZ Postgres + ES is the minimum bar.
- **Public corpus completeness dashboard.** Make the moat visible: live counts, last-updated timestamps, A-F grade distribution per category. Competitors can't replicate this without our pipeline.

### 6.3 Nice-to-have / parking lot
- ISO 27001 + 42001 certifications. Help-AI markets these heavily; for Institutional buyers it's procurement table-stakes. Likely a 2027 push.
- Editorial annotations / commentary. vLex's moat — don't chase.
- Lawyer directory. Buho/MiDespacho own this — skip.
- Voice AI / podcast generators (à la Lexius). Demo-ware, low ROI. Skip.

---

## 7. Strategic recommendation

### 7.1 Position
> "The open infrastructure for Mexican law — the data layer everyone else builds on top of."

This is the only positioning where:
- Tezca's quiet moats (MCP, API, AGPL, quality grading) are the headline.
- Competitors can't easily copy without restructuring their business.
- Buyers self-select correctly (AI builders, researchers, price-sensitive firms).

### 7.2 Targets, in priority order
1. **AI tooling builders** — Cursor agents, in-house legal RAG teams, AI copilot startups. They need clean machine-readable MX law + an MCP. Tezca is the only option. Sell `Institutional` for API volume + webhook fan-out.
2. **Universities, journalists, NGOs** that find vLex prohibitive. Sell `Academic` (LaTeX, bulk download) or recommend self-hosting under AGPL.
3. **In-house counsel at mid-market firms** that find vLex overkill but want more than free DOF browsing. Sell `Essentials` with cross-refs and law alerts.

### 7.3 What NOT to chase
- AI chat polish — you'll be third-best to vLex/Lexius on UX.
- Drafting workflows — late entrant, narrow buyer.
- Lawyer directory features — not a corpus play.

### 7.4 Win on (in order of leverage)
1. Corpus completeness — close 32/32 states.
2. Data quality transparency — publicize A–F grades publicly, per law.
3. API / MCP excellence — the quiet moat. Document, demo, and brand it.
4. Price-to-API-call ratio — undercut vLex enterprise on volume math.

---

## 8. Three-quarter execution priorities (suggested)

### Q3-2026 (Jul–Sep)
- **State coverage push.** Finish 20 missing state scrapers. Set a public scoreboard at `/cobertura/estados` showing 12 → 32 progression weekly.
- **First-party `/preguntar` chat.** RAG over existing ES, Claude/GPT call, citations link back to articles via cross-ref graph. Gate behind `essentials+` tier.
- **Docket monitoring MVP.** PJF API + name alerts + email notifications. Compete with Buho's free tier as a community-tier feature.

### Q4-2026 (Oct–Dec)
- **HA infra.** Multi-AZ Postgres (failover) + ES cluster (3 nodes minimum). Required to honestly sell Institutional.
- **Document export templates.** Tier 2 features: contract clause references, statute summaries auto-generated from articles + cross-refs.
- **Public quality dashboard.** A–F grade distribution per law category, last-update timestamps, indexing latency. Make the data quality moat visible.

### Q1-2027 (Jan–Mar)
- **ISO 27001 audit start.** Procurement table-stakes for Institutional buyers.
- **Public competitive scoreboard.** Live page comparing Tezca vs vLex vs Tirant on (a) corpus completeness (b) data freshness (c) parse quality (d) API/MCP availability. Update weekly.
- **Partnership exploration:** Buho Legal cross-link, MiDespacho integration, Tulana ecosystem rollout. The "data layer everyone builds on" pitch goes from messaging to a measurable network effect.

---

## 9. Open questions for the team

These need decisions before the above execution plan can be costed/sequenced:

1. **State coverage:** Is the bottleneck engineering capacity or per-state legal/access constraints? Some state portals are aggressively WAF'd.
2. **First-party AI:** Build vs. partner? A Help-AI-style RAG can be MVP'd in <2 weeks but introduces an LLM-cost line item. Alternative: rely on MCP and let third parties build the UX.
3. **HA timing:** Tezca's tier system claims `Institutional` already. Is shipping Institutional buyers without HA acceptable for 6 more months, or is HA a P0?
4. **Docket monitoring:** Buho-as-partner vs. Buho-as-competitor. A partnership avoids us scraping court dockets directly (high-effort, fragile) but cedes the "one platform" message.
5. **Pricing review:** CLAUDE.md flags "Confidence: low" on the current band. Schedule a pricing review after the Tulana v0.2 WTP signal arrives, before any tier moves.

---

## 10. Sources (researched 2026-04-27)

- [Buho Legal homepage](https://www.buholegal.com/)
- [Buho Legal Premium tiers](https://www.buholegal.com/premium/)
- [Buho Legal — free services](https://en.buholegal.com/servicios_gratuitos/)
- [MiDespacho vs Buho Legal comparison](https://blog.midespacho.cloud/midespacho-vs-buholegal/)
- [vLex Mexico coverage](https://vlex.com/coverage/mexico)
- [vLex pricing breakdown (Expertos en Leyes)](https://expertosenleyes.com/conoce-el-costo-de-la-suscripcion-a-vlex-para-abogados/)
- [vLex about](https://vlex.com/about-us)
- [Tirant Prime México pricing](https://www.tirantonline.com.mx/tolmex/informacion/tarifas)
- [Sof-IA — Tirant Prime](https://prime.tirant.com/mx/sofia/)
- [Lexius México](https://lexius.io/mx/)
- [Help-AI México](https://www.help-ai.mx/)
- [Maite.ai](https://www.maite.ai/)
- [Globalex: Researching Mexican Law](https://www.nyulawglobal.org/globalex/mexico1.html)
- [LLRX: Best Mexican Law Websites](https://www.llrx.com/2004/01/features-electronic-guide-to-the-best-mexican-law-websites/)
- [Free Law Project — open source legal tools](https://free.law/open-source-tools/)
- [Sourceforge: Best Legal Research Software in Mexico 2025](https://sourceforge.net/software/legal-research/mexico/)
- [Elephas: Legal AI Tools Pricing Comparison 2026](https://elephas.app/resources/legal-ai-tools-pricing-comparison)

---

## 11. Execution checklist (action items)

Track these as separate tickets/PRs. None depend on this doc continuing to exist — this is the briefing, not the work.

### Engineering
- [ ] Finish 20 missing state scrapers (currently 12/32 per CLAUDE.md known gaps).
- [ ] Build `/preguntar` chat over ES + cross-refs (RAG via Claude/GPT). Gate behind `essentials+`.
- [ ] PJF docket-monitoring MVP + name alerts (compete with Buho free tier).
- [ ] HA Postgres (multi-AZ failover) + ES cluster (≥3 nodes).
- [ ] Public coverage dashboard at `/cobertura/estados` (weekly auto-update).
- [ ] Public quality dashboard: A–F grade distribution per category + last-update timestamps.

### Brand / GTM
- [ ] Reposition homepage tagline around "open infrastructure for MX law" theme.
- [ ] Document the MCP server prominently — it's the quiet moat. Add a `/mcp` landing page.
- [ ] Public competitive scoreboard page (Tezca vs vLex vs Tirant on completeness, freshness, API access).

### Process / strategy
- [ ] Decide build-vs-partner on docket monitoring (Buho as partner vs as competitor).
- [ ] Decide build-vs-rely-on-MCP for first-party AI assistant.
- [ ] Re-run pricing review after Tulana v0.2 PMF signal.
- [ ] Investigate ISO 27001 + 42001 audit cost/timeline (procurement table-stakes for Institutional).

### Documentation followups (this session left undone)
- [ ] When this benchmark is acted on, update `ROADMAP.md` (last touched 2026-03-20) with the Q3-2026 → Q1-2027 priorities chosen above.
- [ ] Cross-link this doc from `docs/strategy/STRATEGIC_OVERVIEW.md` and `docs/strategy/PRD.md` once decisions land.
