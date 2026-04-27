# `madfam-org/docket-watcher` — Bootstrap Kit

**Last Updated:** 2026-04-27
**Track:** Track 7 of [FEATURE_PARITY_PLAN_2026-04-27](./FEATURE_PARITY_PLAN_2026-04-27.md) §3.7 (Path B).
**Status:** Specification ready. Repo creation is operator-only (cannot spin up a sibling repo from inside Tezca). Scheduled Q1-2027 per the plan.

---

## 1. Why a sibling repo, not part of Tezca

Per the plan §3.7, Path B was chosen over Path A (build inside Tezca):

> Cleaner separation: Tezca = laws, docket-watcher = case files. Reuses Tezca's auth (Janua) + billing (Dhanam) + webhooks pattern. Could be onboarded via RFC 0014 zero-touch.

Buho Legal owns the docket-monitoring market today (free tier monitors 5 cases, premium $749–$15,000 MXN/yr). MADFAM's parity offering is an ecosystem-aligned competitor: same cleaning + auth + billing patterns as the rest of the stack, plus tight integration with Tezca for "this docket activity references these laws."

Building this **inside** `tezca-api` would contaminate the corpus product (different ToS, different scrape patterns, different fear-driven user workflow). Sibling repo is right.

---

## 2. Repo bootstrap checklist

When the operator is ready to spin this up (per plan Q1-2027 sequencing):

### 2.1 Create the repo

```bash
gh repo create madfam-org/docket-watcher --private --description "Mexican judicial docket monitoring (PJF + state TSJ). Sibling to madfam-org/tezca."
```

Initially **private** — same posture as Tezca was at PR #0. Flip to public when launch-ready.

### 2.2 Onboard via RFC 0014 zero-touch flow

Per `internal-devops/rfcs/0014-zero-touch-onboarding.md`, the operator runs:

```bash
enclii onboard --repo madfam-org/docket-watcher \
  --db-name docket_watcher \
  --secrets-file .env
```

This one-shot creates: namespace `docket-watcher`, ArgoCD app, Cloudflare tunnel routes, Janua client (`docket-watcher-web`), and NetworkPolicies.

### 2.3 Domain provisioning

Reserve via Porkbun + add to the canonical domain inventory in
`internal-devops/ecosystem/domain-map.md`:

| Subdomain | Backed by | Container port |
|---|---|---|
| `dockets.madfam.io` (or new TLD `dockets.lat`) | docket-watcher-web | 3000 |
| `api.dockets.madfam.io` | docket-watcher-api | 8000 |
| `admin.dockets.madfam.io` | docket-watcher-admin | 3001 |

(Per ECOSYSTEM convention, new product domains get their own brand. `dockets.lat` matches the `tezca.mx` / `karafiel.mx` brand-per-product pattern.)

---

## 3. Architecture (target shape)

```
                  ┌──────────────────────────────────────┐
                  │  docket-watcher-web (Next.js)        │
                  │  - List my watched dockets            │
                  │  - Add docket watch (case # / name)   │
                  │  - Receive notifications              │
                  │  - Cross-link to Tezca laws cited     │
                  └──────────────────────────────────────┘
                              │
                              │ Janua JWT
                              ▼
                  ┌──────────────────────────────────────┐
                  │  docket-watcher-api (Django, mirrors │
                  │  tezca-api's Combined-Auth pattern)  │
                  │                                      │
                  │   Models:                            │
                  │   - DocketWatch(case_number, name,   │
                  │     court, user_id, alerts_enabled)  │
                  │   - DocketEvent(watch_id, kind,      │
                  │     occurred_at, raw_excerpt, ref_   │
                  │     law_ids[])                       │
                  │                                      │
                  │   API:                               │
                  │   POST /api/v1/watches/              │
                  │   GET  /api/v1/watches/              │
                  │   POST /api/v1/watches/test/         │
                  │   POST /api/v1/webhooks/             │
                  │     (HMAC-signed dispatch on event)  │
                  └──────────────────────────────────────┘
                              │
                              │ Celery (poll daily/hourly)
                              ▼
            ┌──────────────────────────────────────────────┐
            │  Scrapers (mirror apps/scraper/judicial/)    │
            │   - PJF (Poder Judicial Federal)             │
            │   - SCJN docket portal                       │
            │   - Per-state TSJ (gradual rollout, mirrors  │
            │     the state-laws scraper backlog)          │
            └──────────────────────────────────────────────┘
                              │
                              │ enrichment: cross-link
                              │ event excerpts to law_ids
                              ▼
            ┌──────────────────────────────────────────────┐
            │  Tezca API consumer                          │
            │   GET https://api.tezca.mx/api/v1/laws/?     │
            │     name=<extracted_law_name>                │
            │   (regular Institutional API key)            │
            └──────────────────────────────────────────────┘
```

**Key constraints carried over from Tezca's architecture:**
- Auth via Janua JWT + API keys (`dwk_*` prefix to disambiguate from `tzk_*`)
- Billing via Dhanam (separate `docket_watcher_*` plan slugs)
- Webhooks HMAC-signed, SSRF-protected (port `apps/api/utils/url_validation.py`)
- Tier-throttled rate limits (port `apps/api/tier_throttles.py` minus the legal-corpus specifics)
- Trilingual UI (es/en/nah) — same `LanguageContext` pattern

**What's NEW for docket-watcher:**
- Court-portal scrapers (PJF, SCJN dockets, state TSJs) — different from Tezca's gazette scrapers
- Watch + event data model (transactional, vs Tezca's reference-data model)
- Cross-linking to Tezca law references via `apps/api-client` SDK

---

## 4. Pricing recommendation

Per the parity plan §3.7 and `internal-devops/decisions/2026-04-25-tulana-ecosystem-pricing.md` methodology, anchored on Buho Legal's bands:

| Tier | MXN/mo | Includes | Notes |
|---|---|---|---|
| Free | $0 | 3 case watches, email alerts | Matches Buho free (5 cases) but drops to 3 to push paid conversion |
| Personal | $199 | 25 case watches, email + push | Matches Tezca Community ($199) — same anchor for cross-product bundle |
| Despacho | $599 | 200 case watches, name alerts, daily digest | Matches Tezca Essentials |
| Firma | $1,999 | Unlimited watches, webhook fanout for Karafiel pattern, API access | Matches Tezca Institutional |

Confidence: low. Run through Tulana v0.2 once the first 5 paying customers reveal price elasticity (mirrors Tezca's pricing-review trigger per plan §6.7).

**Cross-product bundle opportunity:** Tezca + docket-watcher + Karafiel = "MADFAM Compliance Stack" — sell as a unified Institutional offering at $4,999 MXN/mo (vs $1,999 × 3 = $5,997 standalone).

---

## 5. Initial files for the repo (suggested)

When the operator runs `gh repo create`, the first commit should establish the structure. Here's a starter layout that mirrors Tezca's conventions:

```
docket-watcher/
├── apps/
│   ├── api/                  # Django REST API (mirrors tezca/apps/api)
│   ├── web/                  # Next.js public site
│   ├── admin/                # Internal admin console
│   ├── scraper/
│   │   ├── pjf/              # Poder Judicial Federal scrapers
│   │   ├── scjn_dockets/     # SCJN-specific docket portal
│   │   └── state_tsj/        # Per-state TSJ scrapers (gradual)
│   └── indigo/               # Django settings + WSGI (rename to project)
├── packages/
│   ├── lib/                  # @docket-watcher/lib
│   ├── ui/                   # @docket-watcher/ui (or reuse @tezca/ui)
│   └── api-client/           # @docket-watcher/api-client (published SDK)
├── tests/
├── enclii.yaml               # Onboarding spec (per RFC 0014)
├── CLAUDE.md                 # Service-specific instructions
├── docker-compose.yml
└── pyproject.toml
```

Suggested initial CLAUDE.md skeleton (paste as the first file):

```markdown
# CLAUDE.md — docket-watcher Developer Guide

## Project Overview

Mexican judicial docket monitoring. Sibling to `madfam-org/tezca`.

**Why separate from tezca**: Tezca tracks laws; docket-watcher tracks
case files. Different scrape sources (court portals vs gazettes),
different user workflows (litigators tracking active cases vs
researchers reading laws), different ToS posture.

**Cross-product integration**: docket-watcher consumes the public Tezca
API to link event excerpts to law references.

## Stack
... (mirror tezca CLAUDE.md structure)
```

---

## 6. Done criterion (Q1-2027 target)

- [ ] Repo created (`madfam-org/docket-watcher`, private)
- [ ] Onboarded via `enclii onboard` (per RFC 0014)
- [ ] Domain provisioned (`dockets.madfam.io` or `dockets.lat`)
- [ ] First scraper green (PJF federal, mirrors `tezca/apps/scraper/judicial/scjn_playwright.py`)
- [ ] User can register a `DocketWatch`, receive an alert within 1 hour of court-portal update
- [ ] Cross-linking: at least one event correctly links to a Tezca law via the public API
- [ ] Pricing tiers in Dhanam catalog (`docket_watcher_free`, `docket_watcher_personal`, `docket_watcher_despacho`, `docket_watcher_firma`)
- [ ] Public landing page at `dockets.madfam.io`

---

## 7. Risks (carried from the plan §9)

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Court portals aggressively rate-limit | High | Material | Polite scraping (1 req/min like Tezca's pattern); fallback to Wayback for backfill |
| Buho Legal incumbent advantage | Medium | Material | Cross-product bundle pitch: docket-watcher + Tezca + Karafiel as one stack, undercut Buho's standalone pricing |
| ToS prohibits scraping | Medium | Severe | Read each portal's ToS before scraper rollout. Some may require operator-mediated access (e.g., direct API agreement) |
| Compliance with Mexican judiciary data-protection rules | High | Severe | Anonymize PII in cached event excerpts; consult legal before launch |

---

## 8. Why this doc lives in tezca

The `tezca` repo is the natural home for the **specification** because:
1. The competitive benchmark + parity plan + Karafiel-as-anchor-customer thesis live here
2. Operators reading the FEATURE_PARITY_PLAN need a co-located bootstrap
3. The doc itself doesn't ship code — pure spec until repo creation

When the repo exists, this doc gets a "moved-to" pointer and the canonical source becomes `madfam-org/docket-watcher/docs/strategy/BOOTSTRAP.md`.

---

## 9. Related

- [FEATURE_PARITY_PLAN_2026-04-27.md §3.7](./FEATURE_PARITY_PLAN_2026-04-27.md)
- [COMPETITIVE_BENCHMARK_2026-04-27.md §2.1](./COMPETITIVE_BENCHMARK_2026-04-27.md) — Buho Legal profile
- `internal-devops/rfcs/0014-zero-touch-onboarding.md`
- `internal-devops/ecosystem/domain-map.md` — domain reservation pattern
- `internal-devops/decisions/2026-04-25-tulana-ecosystem-pricing.md` — pricing methodology
