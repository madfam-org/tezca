# Strategy Documentation Index

**Last Updated:** 2026-04-27

This directory holds Tezca's product/architectural strategy. If you're new to the project and need to know "why X" or "what should we build next," start here. The documents are listed in suggested reading order.

---

## Reading order for new contributors

1. **[STRATEGIC_OVERVIEW.md](./STRATEGIC_OVERVIEW.md)** — High-level product vision. Legacy doc; partial refresh pending in 2026-Q3.
2. **[PRD.md](./PRD.md)** — Product requirements. Legacy; partial refresh pending.
3. **[COMPETITIVE_BENCHMARK_2026-04-27.md](./COMPETITIVE_BENCHMARK_2026-04-27.md)** — Where Tezca sits against vLex, Tirant Prime, Lexius, Help-AI, Buho Legal. Resulting positioning: "the open infrastructure for Mexican law — the data layer everyone builds on top of."
4. **[FEATURE_PARITY_PLAN_2026-04-27.md](./FEATURE_PARITY_PLAN_2026-04-27.md)** — **Source-of-truth** for what's in flight. Maps each competitive gap to the responsible MADFAM ecosystem service (Selva, Dhanam, CNPG, Karafiel, Tulana, Coforma). 13 sections, 8 quarters of sequencing, 8 open operator decisions.

## Track-specific docs (FEATURE_PARITY_PLAN cross-references)

5. **[KARAFIEL_INTEGRATION_AUDIT_2026-04-27.md](./KARAFIEL_INTEGRATION_AUDIT_2026-04-27.md)** — Track 5. Tezca-side readiness for Karafiel as anchor paying customer. Includes operator-runnable SQL queries to verify domain-classification coverage (P0 before Karafiel goes live).
6. **[SELVA_ONBOARDING_TICKET_2026-04-27.md](./SELVA_ONBOARDING_TICKET_2026-04-27.md)** — Track 8. Operator-side spec for provisioning the `tezca-selva-relay` Janua client. Unblocks `CHAT_BACKEND=selva` flip in production.
7. **[CNPG_MIGRATION_PREP_2026-04-27.md](./CNPG_MIGRATION_PREP_2026-04-27.md)** — Track 6. Tezca-side connection-pool knobs (already shipped) plus the cutover runbook. Gated on RFC 0012 (`madfam-org/enclii`) shipping the cluster.
8. **[DOCKET_WATCHER_BOOTSTRAP_2026-04-27.md](./DOCKET_WATCHER_BOOTSTRAP_2026-04-27.md)** — Track 7. Bootstrap kit for the `madfam-org/docket-watcher` sibling repo (Q1-2027). Architecture, repo layout, RFC 0014 onboarding command, pricing tiers anchored on Buho Legal.

## Quality / stability

9. **[A_PLUS_REMEDIATION_PLAN_2026-04-27.md](./A_PLUS_REMEDIATION_PLAN_2026-04-27.md)** — Original 8-workstream plan with the rubric and rationale. Still authoritative on the dimension definitions.
10. **[A_PLUS_PROGRESS_2026-04-27.md](./A_PLUS_PROGRESS_2026-04-27.md)** — **Live progress doc.** What shipped in PRs #55–80 (44%→61% backend coverage, 0 silent excepts, 0 files >800 LOC, TLS pinning architecture, frontend `all:true` gates). Consolidates remaining work into 6 forward workstreams (WS-R1…WS-R6) with sequencing and DoD verification commands. Read this for the *current* state.

## Subdirectories

- **[partnerships/](./partnerships/)** — Partner-specific integration agreements (legal-ops, MADFAM ecosystem, etc.)

---

## Status snapshot (as of 2026-04-27)

### What landed in PRs #46–52 this session

| Track | PR | Type | Done? |
|---|---|---|---|
| Track 1: §3.6 RMF scraper | #46 | code+tests | ✅ |
| Track 2: §3.1 `/preguntar` chat scaffold | #47 | code+tests, gated | ✅ scaffold; awaits Track 8 |
| Track 5: §3.4 Karafiel audit | #48 | docs | ✅ Tezca-side; awaits operator + Karafiel team |
| Track 8: Selva onboarding ticket | #49 | docs | ✅ spec; awaits operator |
| Track 3: §3.5 State scrapers Wave 1A | #50 | code+tests | ✅ 4 states; coverage 12→16 |
| Track 4: §3.3 Billing UI scaffold | #51 | code+tests, gated | ✅ scaffold; awaits operator |
| Track 6: §3.2 CNPG migration prep | #52 | code+docs | ✅ Tezca-side; awaits RFC 0012 |
| Track 7: §3.7 docket-watcher bootstrap | #52 | docs | ✅ spec; Q1-2027 |

### Operator-only blockers

These cannot be done by an agent — listed in priority order for revenue impact:

1. Stripe live keys + Stripe-MX live keys provisioned in Dhanam → flips `MONETIZATION_ENABLED=true`
2. Stripe price IDs created (`tezca_community`, `tezca_essentials`, `tezca_institutional`)
3. Selva provisions `tezca-selva-relay` Janua client → flips `CHAT_BACKEND=selva`
4. Run `classify_law_domains --all --force` on production (verifies ≥95% Karafiel webhook readiness)
5. Karafiel team's Wave 1 Month 1 deliverables (their database live + e.firma uploaded)
6. PMF score crosses activation OR operator-override for known-buyer scenarios
7. CNPG cluster shipping in `madfam-org/enclii` (RFC 0012)
8. `gh repo create madfam-org/docket-watcher` + `enclii onboard` (Q1-2027)

### A+ remediation — PRs #55–80 (this session)

| PR | Workstream | Coverage move |
|---|---|---|
| #55 | WS1 1A | `scheduling/tasks.py` 0% → 73% |
| #56 | WS3 + WS4 + WS5 + WS6 bundle | bare-except cleanup; vitest `all:true`; CVE SLO; Dependabot; scraper checklist |
| #75 | WS3 + WS7 H7 | silent-except CI gate; TLS fingerprint pinning architecture |
| #76 | WS1 1B | `parsers/pipeline.py` 0% → 76% |
| #77 | WS1 1C/1D | playwright_base 0→96, scjn 22→71, treaty 14→59; gate 44→48 |
| #78 | WS1 1C + WS2 2B | law_registry 0→71, sinec 0→69, pnt 0→66; gate 48→51; FE 51/44/47/52 → 53/46/49/54 |
| #79 | WS1 1C/1D | 5 state scrapers 0→60-70%; gate 51→54 |
| #80 | WS1 1C/1D | state_congress_municipal 0→55, scjn_playwright 0→36; gate 54→56 |

Backend coverage: 44% → 61% (gate at 56% with 5pp headroom). 0 silent bare-except. 0 files >800 LOC. Frontend gates active at floor−3pp. Composite grade: B+/B → **B+/A−**.

### What's still pending an agent (i.e., Tezca-side engineering work)

**A+ remediation (see `A_PLUS_PROGRESS_2026-04-27.md`):**
- **WS-R1** — push backend coverage 61% → 65% (~3-5 days, no blockers)
- **WS-R2** — frontend tests to ≥65% statements; lock at floor−2pp (~1-2 weeks)
- **WS-R3a** — operator runs TLS fingerprint capture sweep (~1 day)
- **WS-R4** — synthetic monitoring + Karafiel-test integration (~1-2 weeks)
- **WS-R5** — PG/ES/Redis HA cutover (~6-8 weeks platform team)
- **WS-R6** — Grafana dashboards + SLO board (~2-3 weeks)

**Feature parity / state coverage:**
- **Wave 1B state scrapers** — 8 medium-complexity states (Coahuila, Guanajuato, Jalisco, Puebla, Sonora, Tamaulipas, Veracruz, Sinaloa). 16/32 → 24/32 progression.
- **Wave 1C state scrapers** — 8 hostile states needing Playwright/madfam-crawler delegation.
- **`/preguntar` chat UI** — backend ready in #47; frontend `apps/web/app/preguntar/page.tsx` is a follow-up PR.
- **Coverage dashboard tile flip per state** — manual per-state validation post-deploy.
- **Public quality dashboard** — A-F grade distribution + last-update-timestamps publicized for the moat.
- **ROADMAP.md refresh** — last touched 2026-03-20; Q3-2026 → Q1-2027 priorities now in the parity plan need to land in ROADMAP.md too.

---

## Naming convention

- **Strategy docs** with date suffix `_YYYY-MM-DD.md` are point-in-time briefings. They don't get edited in place — superseded versions are added with new dates.
- **Strategy docs without a date suffix** (`STRATEGIC_OVERVIEW.md`, `PRD.md`) are living documents that are revised in place.
- This index (`INDEX.md`) is updated whenever a new strategy doc lands.

When in doubt: write a new dated doc rather than edit an old one. Cheap to add, free to ignore.

---

## Related (outside `docs/strategy/`)

- `CLAUDE.md` (repo root) — developer guide. Cross-references this directory.
- `ROADMAP.md` (repo root) — engineering execution roadmap. Strategy docs feed into roadmap items.
- `internal-devops/ECOSYSTEM.md` — MADFAM-wide ecosystem map. Strategy docs lean on its constraint contracts (Selva owns inference, Dhanam owns money, etc.).
- `internal-devops/ecosystem/gtm-strategy.md` — GTM master plan; defines Karafiel as Tezca's anchor customer.
- `internal-devops/decisions/2026-04-25-tulana-ecosystem-pricing.md` — pricing source-of-truth.
