# Tezca Feature-Parity Plan — Leveraging the MADFAM Ecosystem

**Last Updated:** 2026-04-27
**Author:** Audit/strategy session, 2026-04-27. Tezca branch: `main` at `3039ac7`.
**Companion docs:** [`COMPETITIVE_BENCHMARK_2026-04-27.md`](./COMPETITIVE_BENCHMARK_2026-04-27.md) (gap analysis); ecosystem references in `internal-devops/`.
**Status:** Draft for team review. No code, no tickets created yet — this is the architectural plan.
**Confidence:** Medium-high on architecture (ecosystem primitives are real and shipping); low on sequencing (depends on operator decisions enumerated in §11).

---

## 1. The thesis

Tezca's competitive gaps from the 2026-04-27 benchmark are **not greenfield engineering problems**. Almost every gap maps to a MADFAM ecosystem primitive that already exists or is in flight:

| Competitive gap | Ecosystem primitive that closes it |
|---|---|
| No first-party AI assistant | **Selva** — OpenAI-compatible LLM router (`/v1`) at agents-api.madfam.io |
| No HA infrastructure | **CNPG** — RFC 0012 Postgres HA (Wave 3 Track 3.3 of Q2 stability remediation) |
| No docket monitoring | **Karafiel** — already SAT-adjacent; **panopticon-mx** — state-structure atlas slated for Tezca integration |
| No subscription / billing | **Dhanam** — sole holder of payment keys; tiers already defined; webhook fanout shipping (Wave C) |
| No PMF gating | **Coforma + Tulana** — RFC 0013 PMF Score, `@madfam/pmf-widget` already in `apps/web` (gated) |
| Pricing transparency | **Tulana** — already shipped Tezca's $199/$599/$1,999 band (tezca#28) |
| Compliance buyers | **Karafiel is Tezca's anchor customer** per `gtm-strategy.md` Wave 1 (Tezca = "Law data feed + webhook for compliance alerts") |
| FX (for USD-quoting Institutional buyers) | **Dhanam `/v1/fx/spot`** — RFC 0011 FX as platform service |
| Auth | **Janua** — RS256 JWKS, already wired |
| Deploy / SLO | **Enclii** — Switchyard control plane; `enclii.yaml` declares status entries (already merged for Tezca, #40) |
| Identity federation | **Janua RFC** claims propagated to Tezca's `subscriptionTier` JWT claim per Wave C |
| State-structure data | **panopticon-mx** — explicit "→ tezca integration path" in repo registry |
| Pricing-cost reconciliation (low-confidence band) | **Tulana v0.2** — Van Westendorp + cost-of-delivery automation, target 2026-05-09 |

**Implication:** Tezca achieves feature parity with vLex / Tirant / Lexius / Help-AI primarily by **integrating well with the rest of MADFAM**, not by rebuilding what those primitives already provide. The pure-Tezca work concentrates on (a) corpus completeness (state scrapers), (b) AI-assistant UI surface, and (c) docket monitoring; the rest is integration glue.

This document maps each competitive gap to the responsible ecosystem service, the integration contract, and the work that lands in `tezca` itself.

---

## 2. Tezca's ecosystem position (canonical view)

Per `internal-devops/ECOSYSTEM.md` and `monetization-architecture-2026-04-26.md`:

```
                        Janua (auth) ──► RS256 JWT with subscriptionTier claim
                            │
                            ▼
   Customer  ───►  Tezca (api.tezca.mx, web.tezca.mx, admin.tezca.mx)
                      │      │       │
                      │      │       └─► Selva (/v1) ◀── all LLM calls
                      │      │
                      │      └────────► Dhanam (subscription state)
                      │                      │
                      │                      ├─► Stripe / Stripe-MX / Conekta
                      │                      ├─► Karafiel (CFDI 4.0)
                      │                      └─► billing.* events (Redis Streams)
                      │
                      └────────────────► consumed by Karafiel (Wave 1 GTM)
                      └────────────────► consumed by external AI agents (MCP)
                      └────────────────► consumed by Tulana (price/PMF telemetry)
```

**Tezca is positioned as:** the law oracle. It does **not** own auth, billing, payments, CFDI, FX, LLMs, or status-page wiring. Each of those has a single canonical owner elsewhere in the ecosystem. Per the "Constraint contract" in monetization-architecture §1: "Tezca subscriptionTier is set by Janua/Dhanam, not by Tezca itself."

**This means Tezca's job for parity is corpus + UX + integration**, never re-implementing identity/billing/inference/payments.

---

## 3. Gap-by-gap implementation plan

For each competitive gap from `COMPETITIVE_BENCHMARK_2026-04-27.md` §6, this section specifies: the responsible service, the integration contract, the work that lands in `tezca`, and the pre-conditions.

### 3.1 First-party AI assistant ("/preguntar") — close vs Lexius/Help-AI/vLex Vincent/Tirant Sof-IA

**Competitive parity target:** every paid MX legal-tech competitor has chat-with-corpus. Tezca's MCP enables third parties to use Tezca, but a built-in chat is what 60-second demos require.

**Owning service:** Selva (`madfam-org/autoswarm-office`, post-cutover `madfam-org/selva-office`). Per ECOSYSTEM convention: "every LLM call should route through Selva (`selva-office`) at `/v1` (OpenAI-compatible). Do not talk directly to OpenAI / Anthropic from service code."

**Integration contract:**
- Tezca-API calls `POST https://agents-api.madfam.io/v1/chat/completions` (post-cutover: `https://api.selva.town/v1/chat/completions`) with OpenAI-compatible payload + Janua-relayed credentials.
- Tezca **never** holds an OpenAI/Anthropic API key. Costs accrue to Selva, billed per-tier via Dhanam metered agent-hours (Maker $85 / Studio $170 / Enterprise $255 per agent-hour).

**Work in `tezca`:**
- New endpoint `POST /api/v1/chat/preguntar` (auth required, gated behind `essentials+` tier via existing `RequireTier.of("essentials")`).
- RAG pipeline: query → ES BM25 + vector retrieval → top-k articles + cross-refs → Selva chat-completion with corpus snippets in system prompt → cited response with article links.
- Frontend: `apps/web/app/preguntar/page.tsx` — chat UI with citations linking back to `/leyes/{id}#article-{N}`. Use existing `LinkifiedArticle` for citation rendering.
- Tier gating: `community` / `anon` see InterestGate; `essentials+` see chat with monthly token cap from `tiers.json`.

**Pre-conditions:**
- Selva supports the `tezca` namespace as a credentialed caller (one-shot Janua client provisioning).
- Token-budget enforcement at Tezca-side throttle (mirrors `TieredRateThrottle`) so a hot loop in chat can't blow the agent-hour ceiling.

**Effort estimate:** ~3 weeks. Existing primitives: ES + cross-refs are ready; Selva already in production for Yantra4D and Coforma. New primitives: RAG pipeline, chat UI.

**Risk:** LLM-cost runaway if tier caps are wrong. Mitigation: lean on Selva's metered agent-hours as the natural budget envelope; expose monthly usage in `cuenta/billing/`.

### 3.2 HA infrastructure — close vs vLex/Tirant credibility gap

**Competitive parity target:** selling `Institutional` ($1,999 MXN/mo) without HA is a procurement objection. vLex/Tirant publish multi-region SLAs.

**Owning service:** Enclii / CNPG (RFC 0012). Tezca migrates from single-instance Postgres to the shared `data` namespace CNPG cluster.

**Integration contract:**
- Tezca's database becomes one of the 17+ databases co-tenant in the CNPG `Cluster` (`data` namespace, `postgres-ha-rw` Service for writes, `postgres-ha-ro` for reads).
- Connection strings flip from `postgres.data.svc:5432` to `postgres-ha-rw.data.svc:5432` (PgBouncer hides this; Tezca's `apps/indigo/settings.py` reads from `DB_HOST` env).
- Failover semantics: <60s for primary node failure (per RFC 0012 §3.2), no client code change.

**Work in `tezca`:**
- Update `enclii.yaml` `runtime.databases[]` to declare dependency on `postgres-ha` Cluster (post-RFC 0014 zero-touch onboarding).
- Update `apps/indigo/settings.py` `DATABASES['default']['CONN_MAX_AGE']` to survive the <60s failover window.
- Migration runbook: pre-cutover dry-run on staging; production cutover during a maintenance window per RFC 0012 §6.
- ES is **separately** a SPOF flagged in CLAUDE.md; deferred to its own RFC (sister pattern to Postgres HA — likely "ES HA via ECK" in Wave 4 of Q2 stability remediation).

**Pre-conditions:**
- RFC 0012 cluster shipped (Wave 3 Track 3.3, Days 26-32 of Q2 plan).
- 4th node landing per Decision #12 (ideal for full anti-affinity; not blocking).

**Effort estimate:** ~1 week of Tezca-side work, but downstream of RFC 0012 landing first. Bulk of the work is platform-side, not Tezca-side.

**Risk:** all 17+ databases share one CNPG cluster. A bad migration affects all. Mitigation: per RFC 0012 §6, cutover in maintenance window with documented rollback to existing single-instance Deployment.

### 3.3 Subscription billing — close the Wave C gap

**Competitive parity target:** every competitor has a paid upgrade path. Tezca currently shows InterestGate (email capture) instead of TierGate (checkout) because `MONETIZATION_ENABLED=false`.

**Owning service:** Dhanam (`madfam-org/dhanam`). Sole holder of Stripe / Stripe-MX / Conekta keys per architectural north star.

**Integration contract** (per `monetization-architecture-2026-04-26.md` Wave C):
1. Define Tezca tiers in Dhanam catalog: `tezca-community` ($199), `tezca-essentials` ($599), `tezca-institutional` ($1,999).
2. Customer initiates upgrade from Tezca `/cuenta/billing/`.
3. Tezca calls `POST https://api.dhan.am/v1/checkouts` with `productSlug=tezca`, `tierSlug=tezca-essentials`, `customer={janua_user_id}`.
4. Dhanam mints Stripe PaymentIntent → customer pays.
5. Stripe webhook → Dhanam → fan-out signed `subscription.activated|upgraded|cancelled` events on `madfam:billing-events` Redis Stream.
6. Tezca subscribes (already declared as consumer in `event-schemas.yaml`); event handler updates `APIKey.tier`.
7. Janua refreshes JWT claim `subscriptionTier`; Tezca's `SubscriptionThrottleGuard` reflects new rate limits on next request.

**Work in `tezca`:**
- Build `/cuenta/billing/` page (mirroring Dhanam upgrade UI). Already partially scaffolded per existing `apps/web/app/cuenta/`.
- Add `BillingModule` to tezca-api (mirrors `JanuaBillingService` pattern in dhanam). Calls Dhanam SDK rather than Stripe directly.
- Subscribe to `madfam:billing-events` stream. Existing webhook receiver `apps/api/billing_views.py` (Dhanam direct webhook) is the precursor — extend or parallel it for stream consumption.
- Build public `/precios` page (already exists per CLAUDE.md route conventions — needs MONETIZATION_ENABLED=true mode).
- Flip `NEXT_PUBLIC_MONETIZATION_ENABLED=true` in deployed env after Wave A is green.

**Pre-conditions** (per monetization-architecture §7, "Operator-only blockers"):
- Stripe live keys in Dhanam (Wave A1).
- Stripe-MX live keys (Wave A1).
- Stripe price IDs created for Tezca tiers.
- Wave A smoke test passes (real card → invoice → portal).
- PMF score crosses activation threshold per RFC 0013 (`recommended_action = enable_paywall`).

**Effort estimate:** ~2 weeks Tezca-side, mostly UI + event-handler. Most heavy lifting is Wave A operator credentialing.

**Risk:** PMF gate trips false-positive (low PMF flips paywall on, conversions tank). Mitigation: RFC 0013's `recommended_action` is operator-approved, not auto-applied.

### 3.4 First paid customer = Karafiel (Wave 1 GTM)

**Competitive parity target:** the benchmark recommended targeting "AI tooling builders" first; the GTM doc has already chosen a sharper target — **Karafiel as Tezca's first Institutional customer**.

**Why this matters:** Per `gtm-strategy.md`:
- Karafiel Enterprise tier ($12,000 MXN/mo) explicitly includes "+ Tezca law tracking, NOM-151 stamping, API access."
- Tezca is listed as a "Supporting Service Active in Wave 1" — "Law data feed + webhook for compliance alerts."
- Karafiel's "Compliance Wedge" goal is 5 paying clients × $20-50k MRR by Month 3.

**Translation for Tezca:** Karafiel buying `Institutional` API access for itself + reselling Tezca-powered alerts to its own customers via a multi-tenant API key model is the **shortest path to first-dollar revenue**. No PMF widget gate needed — Karafiel is the operator-approved buyer.

**Integration contract:**
- Karafiel provisions a Tezca `tzk_*` API key (Institutional tier, scoped to `compliance` domain + `webhook_subscribe` scope).
- Karafiel registers webhooks for `law.updated`, `law.published`, filtered by `domain_filter: ["fiscal", "labor", "administrative"]`.
- Karafiel's compliance worker fans out matching Tezca events to its own tenants (multi-tenant RFC scoping).
- Quarterly billing reconciliation: Karafiel's volume → Tezca Institutional + per-call overage → Dhanam invoice → Karafiel CFDI.

**Work in `tezca`:**
- **Domain-filter completeness:** `webhook_filter` already supports `domain_filter` per CLAUDE.md. Verify all tax/labor/regulatory laws in DB have non-empty `Law.domains` (gap analysis says `classify_law_domains` exists; run it to completion).
- **Per-tenant rate-limit overrides:** Karafiel's volume will likely exceed default Institutional limits. `APIKey.rate_limit_per_hour` field already exists (per CLAUDE.md gotcha #17, capped at 100k/hr). Confirm Karafiel's projected volume fits.
- **Webhook fanout reliability:** existing webhook dispatch is HMAC-signed; ensure DLQ (already in event-schemas.yaml: "DLQ: madfam:{stream}-dlq after 3 failed processing attempts") is wired for `tezca` outbound dispatch too.

**Pre-conditions:**
- Karafiel reaches its own Wave 1 Month 1 deliverables (own database live, e.firma uploaded).
- Tezca corpus has enough fiscal/labor coverage that compliance alerts are credible (RMF deletion in our recent commit means SAT tax-rule scraping is currently a gap — see §3.6).

**Effort estimate:** ~1 week Tezca-side, mostly verification + monitoring. Bulk of the work is Karafiel-side.

**Risk:** Karafiel's compliance use case demands SAT-rule freshness (RMF, NOMs). Tezca currently has NOMs but RMF was a stub (deleted in commit 90294b1). **This is now a P0 to recover before Karafiel goes live.** See §3.6.

### 3.5 State scraper coverage 12/32 → 32/32

**Competitive parity target:** vLex / Tirant / Help-AI all claim full state coverage. The "complete corpus" claim has an asterisk until Tezca closes it.

**Owning service:** Tezca itself (no ecosystem leverage). One ecosystem-side helper:

**Possible ecosystem leverage:**
- **panopticon-mx** is registered with explicit "→ tezca integration path." It's a **Mexican state-structure atlas** (state codes, judiciary structure, congresses, gazette formats). Use panopticon-mx to:
  - Auto-generate state-scraper scaffolds: per-state base URL, gazette publication pattern, expected document types.
  - Provide ground-truth metadata for `STATE_COORDINATES` and the `KNOWN_STATES` constant in `apps/api/constants.py`.
  - Catalog gazette PDF schemas to drive the OCR/parser pipeline.
- **madfam-crawler** (private repo, Crawl4AI + ScrapegraphAI) is "scraping-as-a-service." Possibly delegate the WAF-resilient scraping for hostile state portals (Estado de México, Jalisco) instead of building per-state Playwright in Tezca.

**Work in `tezca`:**
- Inventory the 20 missing states; cluster by complexity:
  - **Trivial (HTML lists):** ~8 states with public gazette portals.
  - **Medium (JS-rendered):** ~8 states needing Playwright (CONAMER pattern).
  - **Hostile (WAF/captcha):** ~4 states. Delegate to madfam-crawler.
- For each state: scraper module → catalog ingestion → parser pipeline → ES indexing → coverage dashboard tile flips green.

**Pre-conditions:**
- panopticon-mx integration path validated (one-time ingest of state-structure metadata).
- Decision: stand up madfam-crawler as a sub-dependency vs. continue per-state Playwright in `apps/scraper`.

**Effort estimate:** ~2-3 months. Single biggest engineering investment in the parity plan, but the credibility win is the largest.

**Risk:** state portal access is legally fragile. Some have ToS forbidding scraping. Mitigation: document each scraper's source terms in `apps/scraper/state/<name>.py` docstring; exclude states that explicitly prohibit it (likely zero, but check).

### 3.6 Resolución Miscelánea Fiscal (RMF) recovery

**Competitive parity target:** Help-AI markets "fiscal" expertise; Tirant carries SAT regs in its corpus. Tezca's RMF scraper was a stub and was deleted in commit `90294b1`.

**Why this is now urgent:** Karafiel's first paid customer Use Case (§3.4) requires SAT regulatory freshness. RMF + RMF annexes + quarterly modifications + Rule 2.9.21 (digital-platform API requirements) are exactly the corpus Karafiel needs.

**Work in `tezca`:**
- Re-implement `apps/scraper/federal/rmf_scraper.py` — Playwright-based (SAT portal is JS-rendered) per the deleted stub's TODO list.
- Pipeline integration: parse rules into individual articles (each rule = `Article` row, parent `Law` = `RMF-2026`).
- Index to ES with `domains: ["fiscal"]` for Karafiel webhook filtering.
- Quarterly modification scraper as a separate Celery beat task.
- Compare implementing in `tezca/apps/scraper` vs delegating to `madfam-crawler`.

**Pre-conditions:** SAT portal navigation strategy (likely Playwright). Treat as a sister of the existing `conamer_playwright.py`.

**Effort estimate:** ~3 weeks (Playwright + parser + indexing + quarterly cron). Block on Karafiel timeline.

**Risk:** SAT portal is anti-scraping. Mitigation: rate-limit aggressively, use `apps/scraper/http.py` allowlist (already established for gov scrapers), document the verify=False tradeoff per CLAUDE.md H7.

### 3.7 Docket monitoring (Buho Legal parity)

**Competitive parity target:** Buho's free-tier-monitoring-5-cases. Catching this consolidates the "I want one platform" buyer; not catching it cedes the market segment.

**Owning service:** Could be Tezca or could be a **separate new ecosystem service** ("docket-watcher" or similar). The benchmark doc deferred this decision to operator review (§9.4 in COMPETITIVE_BENCHMARK).

**Path A — build in Tezca:**
- New `apps/api/dockets/` Django app.
- PJF (Poder Judicial Federal) API integration via Playwright scraper (mirroring `scjn_playwright.py` pattern).
- Per-state TSJ docket APIs / scrapers (parallels state-laws scraper backlog).
- Subscriptions: user creates `DocketWatch(case_number, name, alerts_enabled=true)`; daily Celery task polls; emits `docket.updated` events to user via existing webhook system.

**Path B — partner with Buho or spin up `madfam-org/docket-watcher`:**
- Cleaner separation: Tezca = laws, docket-watcher = case files.
- Reuses Tezca's auth (Janua) + billing (Dhanam) + webhooks pattern.
- Could be onboarded via RFC 0014 zero-touch.
- Parity argument: "MADFAM ecosystem covers laws + dockets via Tezca + docket-watcher" reads cleaner than "Tezca does both."

**Recommendation:** Path B. Docket monitoring is operationally distinct (court-system access patterns, court-side ToS, different user fear-driven workflow). Building it inside Tezca contaminates the corpus product. Spin up `madfam-org/docket-watcher` per RFC 0014; ship Path A only as a post-MVP fallback if Path B slips.

**Effort estimate:** Path A: ~6 weeks in Tezca. Path B: ~8 weeks for a new repo (zero-touch onboarding, scraper + Postgres + Janua + Dhanam wiring). Path B is strictly more work but operationally cleaner.

**Risk:** if Path B never ships, Buho's "I monitor 5 cases free" remains a sticky competitor.

### 3.8 PMF measurement (RFC 0013)

**Competitive parity target:** not a customer-facing parity item, but **gates** the §3.3 paywall flip. Without PMF score, monetization stays disabled and Tezca can't accept Karafiel's payment in §3.4.

**Owning service:** Tulana + Coforma per RFC 0013. Tezca is a consumer.

**Integration contract** (per CLAUDE.md "PMF measurement (2026-04-26)" already wired):
- `@madfam/pmf-widget` already mounted in `apps/web/components/pmf/PmfWidgetMount.tsx`, gated by `NEXT_PUBLIC_PMF_WIDGET_ENABLED=false`.
- POSTs to `https://api.tulana.madfam.io/v1/pmf/{nps,ellis,smile}`.
- Triggers: NPS afterSession=5, Sean Ellis afterSession=3, smile after 3 `law_viewed` actions.

**Work in `tezca`:**
- Operator (not Claude): rotate `NPM_MADFAM_TOKEN` so `@madfam/pmf-widget@^0.1.0` can publish + install.
- Operator: delete the local stub at `apps/web/types/madfam-pmf-widget.d.ts` once published `.d.ts` ships.
- Operator: flip `NEXT_PUBLIC_PMF_WIDGET_ENABLED=true` in deployed env.
- Operator: provision Tezca CAB in Coforma — recruit 5-15 Tezca customers per quarter for qualitative PMF.
- Engineering: ensure `law_viewed` event is fired from `apps/web/components/laws/LawDetail.tsx` (already auto-tracked per CLAUDE.md PostHog events list).

**Pre-conditions:** Tulana endpoints `/v1/pmf/*` deployed (per RFC 0013 already shipped 2026-04-25 in tulana#6).

**Effort estimate:** Operator-bottlenecked, not engineering. Engineering work is <2 days; operator unblocks landing the widget.

**Risk:** PMF below activation threshold for >90 days → paywall stays disabled → no revenue. Mitigation: RFC 0013's 4-quadrant `recommended_action` includes `measure_more` (not just enable/sunset), so a slow PMF score doesn't kill the product.

### 3.9 FX (USD-priced Institutional / future international expansion)

**Competitive parity target:** vLex prices in EUR; international firms expect USD invoicing. If Tezca ever pursues a US-firm-with-MX-practice persona, FX is needed.

**Owning service:** Dhanam `/v1/fx/spot` per RFC 0011.

**Work in `tezca`:** none today (current pricing is MXN-only). When the time comes:
- Use `@madfam/fx-sdk` (per RFC 0011 §2 deliverables).
- Consume in tezca-api at invoice/quote rendering.

**Pre-conditions:** RFC 0011 Phase 1 ships (already shipped per monetization-architecture §8: "RFC 0011 Phase 1 shipped — FX is a platform service. Dhanam's `/v1/fx/spot` is the source of truth").

**Effort estimate:** ~1 day when needed. No work today.

### 3.10 Identity / Janua (already done)

Tezca already verifies Janua JWTs via JWKS (`auth.madfam.io/.well-known/jwks.json`) per CLAUDE.md `JANUA_ISSUER_URL`. The post-Wave-C addition is the `subscriptionTier` claim populated by Dhanam fanout.

**Work:** zero new. The claim populator sits in dhanam, the consumer (`SubscriptionThrottleGuard`) is already a Tezca pattern.

### 3.11 Status page / SLO (already done)

Per recent commit `1b9e20e feat(enclii): declare status entries via enclii.yaml (#40)`, Tezca already declares its status entries via `enclii.yaml` per RFC 0014. Status page evolution per RFC 0002 will surface them.

**Work:** zero new.

### 3.12 Image signing / supply chain (already done)

Per ECOSYSTEM convention: "Images: `@sha256:`-pinned in every manifest. Kyverno fail-closes on `:latest` or mutable tags." Tezca's deploy commits (`9600bf0`, `e68077d`, etc.) follow this — every digest update is a `deploy(api): update digest to <sha>` commit.

**Work:** zero new.

### 3.13 ISO 27001 / 42001 certification

**Competitive parity target:** Help-AI markets ISO 27001 + 42001 prominently. Procurement table-stakes for Institutional buyers.

**Owning service:** ecosystem-wide governance (likely a 2027 push per benchmark).

**Tezca's contribution to a future audit:**
- Audit trail (already exists for billing per Dhanam; needs extension for `tezca-api` admin actions).
- Encryption at rest: relies on CNPG (Wave 3 Track 3.3) + Longhorn (already on the cluster).
- Access logs: Janua-issued JWT + Switchyard audit log already cover most of this.
- Penetration test report (annual, operator-procured).

**Effort estimate:** Out of scope for 2026. Track in `internal-devops/audits/`.

---

## 4. Master sequencing

### Quarter map (12-month plan)

| Quarter | Theme | Tezca-internal work | Ecosystem dependencies (must land first) |
|---|---|---|---|
| **2026 Q3 (Jul–Sep)** | Corpus + AI surface | §3.1 `/preguntar` chat, §3.5 state scrapers wave 1 (8 trivial states), §3.6 RMF recovery | Selva onboarding for `tezca` namespace; panopticon-mx state metadata |
| **2026 Q4 (Oct–Dec)** | Monetization + HA | §3.3 Wave C (billing UI + Dhanam catalog + flip MONETIZATION_ENABLED), §3.2 CNPG cutover, §3.4 Karafiel integration | Wave A operator credentialing (Stripe live keys); RFC 0012 cluster shipped; PMF activation per RFC 0013 |
| **2027 Q1 (Jan–Mar)** | Coverage close + adjacent expansion | §3.5 state scrapers wave 2 (8 medium states), §3.7 Path B `madfam-org/docket-watcher` MVP | Decision on Path A vs B for §3.7 |
| **2027 Q2 (Apr–Jun)** | Soak + ISO prep | §3.5 state scrapers wave 3 (4 hostile via madfam-crawler), audit prep, public quality dashboard, public competitive scoreboard | None |

### Cross-cutting ordering constraints

1. §3.1 chat **does not** require §3.3 monetization — chat can ship as `essentials+` gated immediately (using existing tier system); revenue capture comes when monetization flips.
2. §3.4 Karafiel integration **does** require §3.6 RMF — don't market the "fiscal alerts" pitch with stale data.
3. §3.3 monetization **does** require §3.8 PMF activation — operator-gated, not engineering-gated.
4. §3.5 state coverage is **independent** of all other tracks — can run in parallel forever.
5. §3.7 docket monitoring should ship **after** §3.5 wave 1 completes — don't dilute focus while corpus credibility is the existential threat.

### Critical-path PR sequence (first 90 days, top to bottom)

1. `tezca` — re-implement `rmf_scraper.py` (§3.6) — 3 weeks engineering
2. `tezca` — `/preguntar` chat MVP behind feature flag (§3.1) — 3 weeks engineering, 1 week Selva onboarding overlap
3. `internal-devops` — operator: PMF widget activation (§3.8) — 2 days engineering, gated on operator
4. `tezca` — first 4 state scrapers + coverage dashboard tiles (§3.5) — 4 weeks engineering, parallelizable
5. `tezca` — Karafiel integration audit + per-tenant rate-limit verification (§3.4) — 1 week, can start at any point
6. `tezca` — `apps/web/app/cuenta/billing/` skeleton + Dhanam SDK wiring (§3.3) — 2 weeks, operator-blocked on Wave A1

Total engineering: ~13 weeks of sequential effort or ~9 weeks parallelized across 2 people.

---

## 5. What we are explicitly NOT building

To preserve focus and avoid collisions with ecosystem owners:

- **No first-party billing/payments code in `tezca`.** Dhanam owns it. Tezca calls Dhanam's API.
- **No first-party LLM inference, OpenAI/Anthropic API keys, or Selva-bypass code.** Selva owns it.
- **No first-party CFDI emission.** Karafiel owns it. (Tezca doesn't sell to consumers as a SAT-issuer; if it ever does, it'll route through Karafiel.)
- **No first-party FX conversion.** Dhanam owns it via RFC 0011.
- **No first-party docket monitoring inside `tezca-api`.** §3.7 Path B spins up a sibling repo per RFC 0014.
- **No drafting / templates UI.** Lexius/Tirant own that lane; we lose the API/MCP positioning if we chase it.
- **No editorial commentary / annotations.** vLex's moat — don't chase.
- **No multi-country expansion.** Tezca is the *Mexican* law oracle. International is a different repo, different positioning.

---

## 6. Capability matrix — Tezca after this plan vs. competitors

Re-running the §3 matrix from `COMPETITIVE_BENCHMARK_2026-04-27.md` after this plan executes:

| Capability | Tezca today | Tezca after this plan | vLex MX | Tirant | Lexius | Help-AI |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Federal laws | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Full 32-state coverage | 🟡 12/32 | ✅ 32/32 (post Q1-2027) | ✅ | ✅ | 🟡 | ✅ claim |
| RMF (SAT regs) | ❌ deleted | ✅ via §3.6 | 🟡 | ✅ | ❌ | 🟡 |
| First-party AI assistant | ❌ | ✅ via §3.1 (Selva-routed) | ✅ Vincent | ✅ Sof-IA | ✅ voice | ✅ 30+ agents |
| Subscription billing / paywall | ❌ disabled | ✅ via §3.3 (Dhanam) | ✅ | ✅ | ✅ | ✅ |
| HA infrastructure | ❌ single-node | ✅ via §3.2 (CNPG) | ✅ | ✅ | ? | ? |
| MCP for AI agents | ✅ unique | ✅ unique | ❌ | ❌ | ❌ | ❌ |
| Public REST API at low tiers | ✅ unique | ✅ unique | ❌ | ❌ | ❌ | ❌ |
| Quality grading + quarantine | ✅ unique | ✅ unique | ❌ | ❌ | ❌ | ❌ |
| AGPL + self-hosting | ✅ unique | ✅ unique | ❌ | ❌ | ❌ | ❌ |
| Cross-reference graph | ✅ unique | ✅ unique | 🟡 | 🟡 | ❌ | ❌ |
| Docket monitoring | ❌ | ✅ via §3.7 (sibling repo) | ❌ | ❌ | ❌ | ❌ |
| Trilingual incl. Nahuatl | ✅ unique | ✅ unique | 🟡 | ❌ | ❌ | ❌ |
| ISO 27001 / 42001 | ❌ | 🟡 in flight (2027) | ? | ? | ? | ✅ |

**Read:** Tezca closes every "missing-vs-competitors" capability while preserving every "unique-to-Tezca" moat. The only remaining gap after this plan is ISO certification, which is a 2027 push.

---

## 7. Pricing implications

Per `2026-04-25-tulana-ecosystem-pricing.md`, Tezca's tiers are LIVE at $199 / $599 / $1,999 with **low confidence**.

**Post-plan re-pricing review** (target: post-§3.4 Karafiel revenue + Tulana v0.2):

- Once Karafiel is paying $1,999+ for Institutional, that's the **first medium-confidence WTP signal** for the band.
- Tulana v0.2 path to high-confidence prices (target 2026-05-09 per pricing doc):
  1. Operator enters cost-of-delivery for top 5 products including Tezca.
  2. Run `tulana_recommend` → review dossier.
  3. Schedule PhyneCRM Van Westendorp campaigns (10 responses × 3 SKUs).
  4. Approve via admin UI; recommendation engine stamps confidence.

**Expected outcome:** Essentials may move to $499 or $799 (within the Help-AI / vLex band). Institutional likely stable at $1,999 anchored by Karafiel WTP. Community at $199 stays as differentiator.

**Confidence:** medium on direction, low on magnitude. Don't ratchet prices until v0.2 + first 5 paid customers.

---

## 8. Cross-product economics — the ecosystem flywheel

The non-obvious benefit of this plan: **Tezca's value compounds with every ecosystem product launch**.

| Ecosystem product | Tezca consumption pattern | Tezca economic impact |
|---|---|---|
| **Karafiel** | Institutional API + webhooks for compliance | Direct paying customer (§3.4) |
| **Cotiza** | Could query NOMs / regulatory pricing rules per quote | Future Institutional customer |
| **Selva** | LLM provider; not a customer of Tezca, but Tezca is Selva's content provider via MCP | Token volume → Tezca usage → tier upgrade pressure |
| **Forj** | Marketplace storefront agreements may need legal-template references | Future API consumer |
| **Avala** | Verifies CONOCER credentials → may need MX education law tracking | Future API consumer |
| **Pravara MES** | Manufacturing compliance (NOMs, environmental regs) | Future API consumer |
| **Fortuna** | Problem intelligence may include legal-trend signals | Future API consumer |
| **Dhanam** | KYC + AML compliance references | Future API consumer |

**Translation:** Tezca's path to >5 paying customers is **MADFAM-internal first**, then external. Every other product's growth pulls Tezca usage with it. This is the ecosystem flywheel that no standalone competitor (vLex, Tirant, Lexius) can replicate.

**Strategic recommendation:** treat the first 6 months of paid Tezca as **MADFAM-internal cross-product billing**, then graduate to external customers in 2027. Internal billing also dogfoods the Dhanam → Tezca subscription pipeline before exposing to external buyers.

---

## 9. Risks & mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Selva not ready for Tezca's workload | Medium | Blocks §3.1 | Selva already serving Yantra4D + Coforma; Tezca's load profile (chat + RAG) is similar. Stage in non-prod first. |
| RFC 0012 CNPG cutover bug affects all 17 DBs | Low | Catastrophic | Maintenance window + documented rollback + dry-run in staging per RFC 0012 §6. |
| Karafiel timeline slips → Tezca first-revenue delays | High | Material | Decouple §3.4 from §3.5 / §3.1 — Tezca can ship parity-features without Karafiel. |
| PMF score never crosses activation | Medium | Material | RFC 0013's `measure_more` gives a non-binary state. If 6 months of `measure_more`, revisit pricing or product-market hypothesis. |
| State scrapers blocked by ToS / WAF | Medium | Material | madfam-crawler delegation; document each scraper's source terms; skip ToS-prohibited states. |
| Operator Stripe credentialing slips Wave A | High | Blocks §3.3 | Tezca-internal work (UI + SDK wiring) lands in advance; flip is a one-line env change. |
| Dhanam catalog drift (tier names mismatch) | Low | Embarrassing | Single source of truth in Dhanam catalog; Tezca treats it as authoritative; CI lint checks plan slugs match. |
| Multi-tenant API key model insufficient for Karafiel | Medium | Slows §3.4 | Existing `APIKey.rate_limit_per_hour` per-key override + scoped permissions cover the model. Verify against Karafiel's projected volume early. |

---

## 10. Success metrics

### 90-day metrics (end Q3-2026)
- §3.1 chat ships: 1+ paying user uses it (Karafiel-internal counts).
- §3.6 RMF: live RMF + at least 1 quarterly modification ingested + indexed.
- §3.5 wave 1: 4 of 8 trivial state scrapers green; coverage page shows progression.
- §3.4 Karafiel: tezca-API key provisioned, webhook subscribed, first compliance event delivered to Karafiel-test.

### 180-day metrics (end Q4-2026)
- §3.3 monetization: MONETIZATION_ENABLED=true in production; first dollar received.
- §3.2 CNPG: tezca DB migrated; failover drill passes.
- §3.4 Karafiel: paying for Tezca Institutional; reconciled in Dhanam invoice ledger.
- §3.5 wave 1: 8 of 8 trivial states complete.
- PMF: composite score reported weekly; recommended_action at least `measure_more`.

### 12-month metrics (end Q1-2027)
- §3.5 wave 2: 16 of 32 states (8 trivial + 8 medium).
- §3.7: `madfam-org/docket-watcher` MVP shipped (or Path A implemented in tezca if Path B slipped).
- 5+ paying customers (Karafiel + 4 external).
- Public quality dashboard live; competitive scoreboard live.
- Pricing review post-Tulana-v0.2 complete; tiers re-anchored at medium-confidence.

---

## 11. Open questions for the team (decisions blocking sequencing)

These are the §9 questions from `COMPETITIVE_BENCHMARK_2026-04-27.md` updated with ecosystem context:

1. **State coverage path:** Build 20 state scrapers in `tezca/apps/scraper/state/` (current pattern) or delegate the hostile 4 to `madfam-crawler`? Trade-off: speed vs operational coupling.
2. **First-party AI vs MCP-only:** Build `/preguntar` (§3.1) or rely entirely on MCP and let third parties ship the UX? Recommendation in this doc: build it. But the operator may prefer "infrastructure-pure" positioning.
3. **HA timing:** Ship Institutional ($1,999) without HA for 6 more months (until §3.2 CNPG cutover Q4) or hold paid product until HA lands? Recommendation: ship with documented "current SLO 99.9% best-effort, HA Q4-2026" caveat.
4. **Docket monitoring path:** Path A (in tezca) or Path B (sibling repo `madfam-org/docket-watcher`)? Recommendation: Path B for clean separation.
5. **Karafiel timeline coupling:** Is Tezca's first-revenue tied to Karafiel's Month 3 GTM milestone, or independent? Recommendation: independent. Tezca should be capable of taking external Institutional payments before Karafiel completes Wave 1.
6. **PMF gating strictness:** Wait for `enable_paywall` from RFC 0013 strictly, or flip MONETIZATION_ENABLED=true at `measure_more` if there's a known buyer (Karafiel)? Recommendation: pragmatic — operator-approved override is acceptable for known-buyer scenarios.
7. **Pricing review trigger:** Run §7 Tulana v0.2 review at first paid customer or wait for 5? Recommendation: at first paid customer; the WTP signal is too valuable to defer.
8. **panopticon-mx integration depth:** Light-touch (one-time state metadata ingest) or deep (continuous structure-of-government feed)? Recommendation: light-touch for §3.5; revisit deep integration in 2027.

---

## 12. Action items (parking lot — convert to tickets when prioritized)

### Engineering
- [ ] §3.1: scaffold `apps/api/chat/` Django app + Selva client SDK
- [ ] §3.1: scaffold `apps/web/app/preguntar/page.tsx` chat UI
- [ ] §3.2: PR for `enclii.yaml` updating `runtime.databases[]` to declare `postgres-ha` Cluster dependency
- [ ] §3.3: scaffold `apps/web/app/cuenta/billing/` page tree mirroring Dhanam upgrade UI
- [ ] §3.3: add `BillingModule` to tezca-api (mirrors `JanuaBillingService` pattern)
- [ ] §3.3: subscribe to `madfam:billing-events` Redis stream (Tezca already declared as consumer per `event-schemas.yaml:22`)
- [ ] §3.4: audit Karafiel-projected webhook volume vs `APIKey.rate_limit_per_hour` cap (100k/hr); raise if needed
- [ ] §3.5: state scraper backlog issue per state with complexity classification
- [ ] §3.6: re-implement `apps/scraper/federal/rmf_scraper.py` (Playwright-based)
- [ ] §3.7: ADR on Path A vs Path B for docket monitoring; if Path B, draft `madfam-org/docket-watcher` `enclii.yaml`

### Operator (cannot be done by an agent)
- [ ] §3.3: provision Stripe live keys + Stripe-MX live keys in Dhanam (Wave A)
- [ ] §3.3: create Stripe price IDs for `tezca-community`, `tezca-essentials`, `tezca-institutional`
- [ ] §3.8: rotate `NPM_MADFAM_TOKEN` so `@madfam/pmf-widget` can publish + install
- [ ] §3.8: provision Tezca CAB in Coforma (5-15 customers per quarter)
- [ ] §3.8: flip `NEXT_PUBLIC_PMF_WIDGET_ENABLED=true` in deployed env once published
- [ ] §3.4: Karafiel team: confirm webhook event volume estimate

### Cross-repo coordination
- [ ] §3.1: file Selva onboarding ticket — provision `tezca` namespace as credentialed `/v1` caller
- [ ] §3.2: comment on RFC 0012 PR confirming Tezca will migrate; participate in cutover dry-run
- [ ] §3.4: jointly with Karafiel team: write the integration runbook (which Tezca events fire which Karafiel compliance alerts)
- [ ] §3.5: open issue against `panopticon-mx` for the state-structure metadata API contract
- [ ] §3.7: file ADR in `internal-devops/decisions/` proposing Path A vs Path B

---

## 13. Related ecosystem documents (for the next session to read)

When picking this plan up, read these in order:

1. [`internal-devops/ECOSYSTEM.md`](../../../internal-devops/ECOSYSTEM.md) — full ecosystem map.
2. [`internal-devops/ecosystem/monetization-architecture-2026-04-26.md`](../../../internal-devops/ecosystem/monetization-architecture-2026-04-26.md) — the constraint contract (Dhanam owns money; Janua owns identity; Selva owns inference; Karafiel owns CFDI).
3. [`internal-devops/ecosystem/gtm-strategy.md`](../../../internal-devops/ecosystem/gtm-strategy.md) — the Wave 0/1/2 plan; Tezca's Wave 1 role as Karafiel feed.
4. [`internal-devops/decisions/2026-04-25-tulana-ecosystem-pricing.md`](../../../internal-devops/decisions/2026-04-25-tulana-ecosystem-pricing.md) — pricing source-of-truth.
5. [`internal-devops/rfcs/0012-postgres-ha-via-cnpg.md`](../../../internal-devops/rfcs/0012-postgres-ha-via-cnpg.md) — HA migration plan.
6. [`internal-devops/rfcs/0013-pmf-via-coforma-and-tulana.md`](../../../internal-devops/rfcs/0013-pmf-via-coforma-and-tulana.md) — PMF gate.
7. [`internal-devops/rfcs/0011-fx-as-platform-service.md`](../../../internal-devops/rfcs/0011-fx-as-platform-service.md) — Dhanam owns FX (when Tezca needs it).
8. [`internal-devops/rfcs/0014-zero-touch-onboarding.md`](../../../internal-devops/rfcs/0014-zero-touch-onboarding.md) — how to spin up `madfam-org/docket-watcher` if §3.7 Path B.
9. [`internal-devops/ecosystem/event-schemas.yaml`](../../../internal-devops/ecosystem/event-schemas.yaml) — Tezca is a declared consumer of `madfam:billing-events`; the schema is canonical.
10. This document.
11. [`docs/strategy/COMPETITIVE_BENCHMARK_2026-04-27.md`](./COMPETITIVE_BENCHMARK_2026-04-27.md) — companion gap analysis.
