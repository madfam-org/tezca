# Tezca A+ Remediation — Progress & Forward Plan

**Date:** 2026-04-28 (live snapshot)
**Companion:** [`A_PLUS_REMEDIATION_PLAN_2026-04-27.md`](./A_PLUS_REMEDIATION_PLAN_2026-04-27.md) (original rubric, sequencing, open questions)
**Status:** Active — this doc tracks the *delta* against the plan and re-sequences the remaining work.

---

## 1. Where we are vs. the A+ rubric

| Dimension | Then (2026-04-27 baseline) | Now (post-PR-#83) | A+ threshold | Status |
|---|---|---|---|:-:|
| Test discipline (pass rate) | A — 1527/1542 = 99.0%, 15 skipped | A — 2164 passed / 17 skipped / 0 failures | A+ (≥99.5%, all skipped tracked) | 🟡 |
| Backend coverage | C+ (44%, gate 44%) | **A (64% actual, 60% gate)** | A (≥60%, gate ≥55%) | ✅ |
| Frontend coverage (`all: true`) | unknown — gate disabled | **A (gates 61/54/58/62, floor 63/57/60/64)** | A (≥50% statements w/ `all: true`) | ✅ |
| Architectural integrity | A | A — 0 policy regressions in 90 days | A+ (90 days) | 🟢 |
| Code-debt hygiene | A− (64 bare `except`, 7 files >900 LOC) | **A (0 silent excepts, 0 files >800 LOC)** | A+ (0 bare, ≤1 over 800 LOC) | 🟢 |
| Infra resilience | C− | C− — RFC 0012 in flight, ES + Redis HA pending | A (multi-AZ PG/ES/Redis) | 🔴 |
| Production-path validation | B− | B — per-scraper checklist landed; synthetic monitoring pending | A (live ≤7d, monitored) | 🟡 |
| Security posture | A− | **A (TLS pinning architecture + CVE SLO)** — capture sweep pending | A (ISO 27001 prep started) | 🟡 |
| Observability | B (Sentry + PostHog) | B (no change) | A (Grafana + SLO board) | 🔴 |

**Composite right now: A** (up from B+/B at the start of the session). All four application-side dimensions (test discipline, backend coverage, frontend coverage, code-debt hygiene + architecture + security architecture) are now at **A or A+**. The remaining gaps to A+ are **platform-side (HA + observability)** and **operator-side (TLS fingerprint capture sweep + ISO 27001 prep)** — none addressable by application code alone.

---

## 2. What shipped — PRs #55 → #80

15 PRs landed (#55, #56, #75–#83), ratcheting backend coverage 44% → 64% and frontend gates from disabled → 61/54/58/62 with floor at 63/57/60/64.

| PR | Workstream | Coverage move | Notes |
|---|---|---|---|
| #55 | WS1 Phase 1A | `scheduling/tasks.py` 0% → 73% | Celery beat tasks |
| #56 | WS3 + WS4 + WS5 + WS6 | bare-except cleanup, vitest `all:true` flip, CVE SLO + Dependabot, scraper checklist | Bundled Items 2–5 |
| #75 | WS3 enforcement + WS7 H7 | Silent-except CI gate; TLS fingerprint pinning architecture | `audit_silent_excepts.py` + `_FingerprintPinnedAdapter` + capture script |
| #76 | WS1 Phase 1B | `parsers/pipeline.py` 0% → 76% | 35 tests, fixture-based |
| #77 | WS1 Phase 1C/1D | `playwright_base` 0→96, `scjn_scraper` 22→71, `treaty_scraper` 14→59 | Gate 44 → 48 |
| #78 | WS1 1C + WS2 2B | `law_registry` 0→71, `sinec_scraper` 0→69, `pnt_scraper` 0→66 | Backend gate 48 → 51, frontend gates ratcheted to 51/44/47/52 |
| #79 | WS1 1C/1D | 5 state scrapers 0% → 60-70% | Gate 51 → 54 |
| #80 | WS1 1C/1D | `state_congress_municipal` 0→55, `scjn_playwright` 0→36 | Gate 54 → 56 |
| #81 | docs | A+ progress doc + 6-workstream forward plan | Synced INDEX + CLAUDE + README |
| #82 | **WS-R1 ✅** | nom_scraper, conamer, dof_daily, dof_api_client, catalog_spider, billing_stream, helpers | Backend 61% → 64%; gate 56 → 60 |
| #83 | **WS-R2 ✅** | api.ts facade + 11 component test files (graph, skeletons, MetricCard, AnnotationBadge, JsonLd, LawArticles, theme-provider, StatesGrid, feature-labels, sentry) | Frontend 56% → 63%; gates locked at 61/54/58/62 (floor−2pp) |

**Test count (this session, ending 2026-04-28):** Backend 1527 → **2164** (+637). Frontend 761 → **930** (+169). Admin 78. api-client 48. MCP 23. **Total monorepo: ~3243 passing tests.** Files >900 LOC: 7 → 0. Silent bare-except: 64 → 0. CI quality gates added: 2 (silent-except audit + frontend `all: true` coverage).

---

## 3. What remains — six concrete workstreams

The eight workstreams in the original plan collapse to six now that WS1 Phase 1A/1B/1C/1D, WS2 2A, WS3, WS4 (file-size threshold), WS5 partial, WS6 Phase 1, and WS7 H7-architecture are done.

### WS-R1 — Backend coverage to 60%+ (push) ✅ DONE (2026-04-27)
**Outcome:** Backend coverage 61% → **64%**. Gate ratcheted **56 → 60** with 4pp headroom. Met the A-grade threshold (≥60% actual, ≥55% gate).

**Modules covered in this round (PR after #81):**
- `apps/scraper/federal/nom_scraper.py`: 14% → **71%** (41 new tests)
- `apps/scraper/federal/conamer_scraper.py`: 25% → **67%** (38 new tests)
- `apps/scraper/federal/conamer_playwright.py`: 0% → **partial** (11 new tests via shim)
- `apps/scraper/federal/dof_daily.py`: 20% → **52%** (22 new tests)
- `apps/scraper/federal/dof_api_client.py`: 0% → **76%** (10 new tests)
- `apps/scraper/federal/catalog_spider.py`: 0% → **74%** (6 new tests)
- `apps/api/billing_stream_consumer.py`: 0% → **53%** (23 new tests)
- `apps/api/management/commands/classify_law_domains.py`: 0% → **28%** (16 tests on pure helper)
- `apps/api/management/commands/ingest_rmf.py`: 0% → **28%** (6 tests on pure helper)

**Why the gate is at 60% (not 65%):** the remaining 36% of uncovered code is dominated by Django-DB-coupled `Command.handle()` methods, browser-driven Playwright orchestration, and Selva/madfam_bridge integration paths that yield brittle low-value coverage when mocked. Pushing to 65% would require infrastructure (DB fixtures, Playwright recordings) that's better deferred to integration testing in WS-R4.

### WS-R2 — Frontend coverage ratchet to lock target ✅ DONE (2026-04-27)
**Outcome:** Floor pushed from 56.44 / 49.68 / 52.09 / 57.66 to **63.36 / 56.85 / 60.28 / 64.21** (+~7pp on every metric). Gates locked at floor−2pp = **61 / 54 / 58 / 62**. Frontend coverage dimension is now at A.

**Modules covered in WS-R2:**
- `apps/web/lib/api.ts` (168 stmts → covered): full mocked-fetch suite, 46 tests for URL composition, error matrix, auth + body wiring, graceful-degradation paths.
- `apps/web/components/graph/`: 7 of 9 components now tested — GraphFilters, GraphLegend, GraphSearch, GraphStats, GraphTooltip, useGraphExport, graphConstants. (LawGraph + LawGraphContainer are sigma-coupled and excluded.)
- `apps/web/components/skeletons/`: all 3 skeletons covered.
- `apps/web/components/admin/MetricCard.tsx` covered.
- `apps/web/components/laws/AnnotationBadge.tsx` covered.
- `apps/web/components/{JsonLd, LawArticles, theme-provider, mode-toggle}` covered.
- `apps/web/lib/{feature-labels, sentry}` covered.
- `apps/web/app/estados/StatesGrid.tsx` covered.

Test count: 761 → **930** (+169). 12 new test files.

**Why we stopped at the current floor (not pushed to 75%+):** the remaining gaps are LawGraph (sigma.js renderer, hard to mock), busqueda/page.tsx (full search-page integration), and per-page Next.js Server Components. Each yields shallow coverage when unit-tested; better tested via Playwright E2E in WS-R4.

### WS-R3 — Operator security sweep (TLS fingerprint capture + ISO 27001 prep)
**Effort:** ~1 day operator + 2 weeks ISO doc work. **Owner:** operator + security-track lead.

The TLS pinning **architecture** landed in PR #75. The capture sweep is operator work:

1. **Capture sweep (~1 day):** run `scripts/utils/capture_tls_fingerprint.py <host>` for each of the 10 hosts in `INSECURE_HOSTS`. For each successful capture, paste into `HOST_FINGERPRINTS` and remove from `INSECURE_HOSTS`. The current 10 hosts are listed in `apps/scraper/http.py:INSECURE_HOSTS`.

2. **ISO 27001 audit RFC (~2 weeks):** file `internal-devops/audits/2026-Q3-iso27001-prep.md` per the original plan. Document encryption-at-rest (CNPG once cutover lands), access logs (already in `dataops.AcquisitionLog`), pen-test cadence (annual, operator-procured).

**Done criterion:** ≥7 of 10 `INSECURE_HOSTS` hosts pinned; CLAUDE.md "Known Issues" promotes H7 to Resolved; ISO 27001 RFC filed.

### WS-R4 — Synthetic monitoring + Karafiel-test integration runtime
**Effort:** ~1–2 weeks. **Owner:** engineering + ops + Karafiel team.

Per the original WS6 Phase 2/3:

1. **Synthetic probes (~1 week):** new `tests/synthetic/` directory with health-checks against `api.tezca.mx/api/v1/admin/health/`, `/api/v1/stats/`, `/api/v1/laws/cpeum/`. Run on a 5-minute Grafana cadence; PagerDuty alert on probe failure.

2. **Karafiel-test integration (~1 week):** per `KARAFIEL_INTEGRATION_AUDIT_2026-04-27.md` §7. Provision API key, register webhook with `domain_filter: ["fiscal"]`, fire test event, verify end-to-end.

**Done criterion:** every Wave 1A scraper has at least one production AcquisitionLog row; synthetic probes deployed + alerting; Karafiel-test integration runtime passes.

### WS-R5 — Infra HA (PG + ES + Redis)
**Effort:** ~6–8 weeks. **Owner:** platform team. **Leverage:** highest on resilience axis.

Tezca-side prep is **already done** (PR #52 added CNPG-friendly DB connection settings). Remaining is platform-side:

1. **Postgres HA (CNPG)** — RFC 0012, in flight per `CNPG_MIGRATION_PREP_2026-04-27.md`. Tezca cutover is a one-line env var swap.
2. **ES HA via ECK** — file new RFC `0015-elasticsearch-ha-via-eck.md`. Tezca-side: `apps/api/config.py` already supports comma-split ES_HOST.
3. **Redis HA via Sentinel** — staged manifests in `enclii/infra/k8s/redis-sentinel/`. Tezca-side: env-var swap `REDIS_URL` → `redis-sentinel://...`.

**Done criterion:** all three failover drills pass quarterly; status page publishes 99.9% SLO with 30-day proof.

### WS-R6 — Observability (Grafana + SLO board)
**Effort:** ~2–3 weeks. **Owner:** platform + engineering.

Per the original WS8:

1. **Per-service Grafana dashboards (~1 week):** tezca-api (request rate, p50/95/99 latency, error rate, deps health), tezca-worker (task rate by name, retry rate, DLQ depth), tezca-beat (drift from schedule).

2. **SLO board (~1 week):** 99.9% availability for `api.tezca.mx`, p95 <500ms search / <200ms law detail. Publish to status.tezca.mx.

3. **Error budget tracking:** burn-rate alerts at 2x and 14x; monthly SLO review.

**Done criterion:** ≥4 Grafana dashboards deployed; SLO board live; first monthly review held.

---

## 4. Sequencing — what to ship next, in priority order

Application-side work (WS-R1 through WS-R3) can ship next week without blockers. Platform-side work (WS-R4 through WS-R6) is gated on the platform team.

| Order | Workstream | Effort | Blocker? |
|---|---|---|:-:|
| 1 | **WS-R1** — push backend to 65% | 3–5 days | none |
| 2 | **WS-R2** — frontend to ≥65% / lock at 60-50-55-60 | 1–2 weeks | none |
| 3 | **WS-R3a** — operator runs TLS capture sweep | ~1 day | needs operator session |
| 4 | **WS-R4** — synthetic monitoring + Karafiel-test integration | 1–2 weeks | Karafiel team coord |
| 5 | **WS-R3b** — ISO 27001 RFC | 2 weeks (operator) | none |
| 6 | **WS-R5** — PG HA cutover (then ES, then Redis) | 6–8 weeks platform | RFC 0012 progress |
| 7 | **WS-R6** — Grafana + SLO board | 2–3 weeks | partly gated on WS-R5 |

**Realistic A+ achievement date** (if platform team executes RFC 0012 within 8 weeks): **2026-06-22** for code-side dimensions, **2026-07-15** for full A+ including infra.

---

## 5. Definition of done — A+ verification commands

Same checklist as the original plan, updated thresholds:

```bash
# Backend
poetry run pytest tests/ --cov=apps --cov-fail-under=60         # ≥60% gate
poetry run pytest tests/ --no-cov -q | grep skipped              # ≤2 (each documented)
poetry run python scripts/utils/audit_silent_excepts.py          # 0 findings
poetry run python scripts/utils/audit_file_sizes.py | grep "0$"  # 0 files >800 LOC

# Frontend
cd apps/web && npx vitest run --coverage --coverage.reporter=text-summary
# Statements ≥60, Branches ≥50, Functions ≥55, Lines ≥60

# Infra
kubectl get cluster postgres-ha -n data -o jsonpath='{.status.phase}'
kubectl get elasticsearch tezca-articles -n data -o jsonpath='{.status.health}'
kubectl get redissentinel -n data ...

# Observability
curl -s status.tezca.mx | grep "99.9"
curl -s grafana.enclii.dev/api/dashboards | jq '.[] | select(.title | startswith("tezca"))' | wc -l  # ≥4

# Security
grep -rn "verify=False" apps/scraper/ | grep -v "# pragma: pinned"  # 0
gh api repos/madfam-org/tezca/dependabot/alerts --jq '.[] | select(.state=="open" and .severity=="high")' | wc -l  # ≤3
```

---

## 6. Risks & open questions

The original plan's §5 questions are mostly resolved. What's left:

1. **Engineer-weeks allocation** — the code-side workstreams (WS-R1, WS-R2, WS-R3, WS-R4) are ~3–4 weeks at 1 FTE. Can fit in a single sprint cycle.
2. **Platform team RFC 0012 ETA** — still the gating dependency for the A+ infra dimension. If it slips past June, ship the code-side dimensions and accept a B on resilience until cutover.
3. **TLS capture sweep risk** — some `INSECURE_HOSTS` may have rotating leaf certs (load balancers); pin only the stable ones. Acceptable per the SECURITY.md two-layer model.

---

## 7. Related

- [`A_PLUS_REMEDIATION_PLAN_2026-04-27.md`](./A_PLUS_REMEDIATION_PLAN_2026-04-27.md) — original rubric (still authoritative for the dimensions)
- [`COMPETITIVE_BENCHMARK_2026-04-27.md`](./COMPETITIVE_BENCHMARK_2026-04-27.md) — feature gap analysis (separate quality axis)
- [`FEATURE_PARITY_PLAN_2026-04-27.md`](./FEATURE_PARITY_PLAN_2026-04-27.md) — product roadmap (this doc complements it)
- [`KARAFIEL_INTEGRATION_AUDIT_2026-04-27.md`](./KARAFIEL_INTEGRATION_AUDIT_2026-04-27.md) — first-customer-readiness
- [`CNPG_MIGRATION_PREP_2026-04-27.md`](./CNPG_MIGRATION_PREP_2026-04-27.md) — Postgres HA cutover (WS-R5 dep)
