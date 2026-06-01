# Tezca Agent Operating Guide

> [!IMPORTANT]
> MADFAM-ENCLII-FIRST-LEGACY-RAW v1: This document contains legacy raw infrastructure command examples.
> Routine production operations must use Enclii web, API, or CLI. Treat raw
> `kubectl`, `helm`, SSH, provider CLI/API, `docker exec`, and direct container
> access as platform bootstrap or documented break-glass only, and record any
> missing Enclii adapter gap.


<!-- MADFAM-AGENTS-CANONICAL v1 -->

This is the canonical instruction file for Claude, Codex, and any other LLM
agent working in this repository. `CLAUDE.md` is kept only as a compatibility
redirect and should not become the source of truth again.

## Required operating doctrine

- Read this file before making repo changes.
- Prefer existing repo conventions, scripts, and docs over introducing new
  patterns.
- Preserve user work and never revert unrelated changes.
- Treat production operations as Enclii-first: use Enclii web, API, or CLI for
  provisioning, deployment, observability, domains, secrets, provider
  operations, scaling, rollback, and remediation.
- Use direct `kubectl`, `helm`, SSH, provider CLIs/APIs, `docker exec`, or
  direct container access only for platform bootstrap or documented break-glass
  emergencies when Enclii is unavailable or lacks an implemented adapter.
- Record any missing Enclii adapter gap instead of normalizing raw production

Legal/compliance data and side-effect rules:
- Treat legal texts, legal analysis, annotations, search/index data, scraper/source catalogs, official-source URLs, API keys/scopes, admin user IDs, CRM webhook payloads, billing/checkout handoffs, Selva chat prompts, Elasticsearch indexes, MCP queries, and generated exports as sensitive legal/compliance data where applicable.
- Treat scrapers/downloaders/ingestion/RMF/DOF jobs, quality backfills, cross-reference/domain classification, index rebuilds, exports, API key admin, webhook delivery, chat/LLM calls, DB migrations/seeds/resets, local docker stacks, MCP/SDK publish, and GitOps deploys as side-effectful. Run them only after an explicit operator request and the matching local guard environment variable.
- Placeholder-only secrets belong in examples and docs: Janua, Dhanam, Selva, CRM webhook, Elasticsearch, database/Redis, npm/GitHub, Sentry/PostHog, R2/S3, and Tezca API keys/tokens.
- Local guard variables: `LOCAL_SERVICES=yes` for service stacks/dev servers, `LOCAL_DB=yes` for migrations/seeds, `LOCAL_DESTRUCTIVE=yes` for cleanup/reset flows, and `LOCAL_LEGAL_DATA_OPS=yes` for legal ingestion/indexing/export/webhook/chat/package-publish operations.
  access in docs or runbooks.

## Repo entrypoints

- `README.md`
- `ECOSYSTEM.md`
- `docs/`
- `infra/`
- `.github/workflows/`

## LLM context files

- `llms.txt` is the compact context index.
- `llms-full.txt` is the durable full-context map and operating contract.
- `AGENTS.md` is canonical for agent instructions.
- `CLAUDE.md` redirects here for Claude compatibility.

## Maintenance

Regenerate or repair these files with
`internal-devops/scripts/sync-agent-docs.py` from the labspace ecosystem.

---

## Legacy CLAUDE.md guidance imported on 2026-05-13

<!-- BEGIN LEGACY_CLAUDE_IMPORT -->

# CLAUDE.md -- Tezca Developer Guide

## Project Overview

Tezca (tezca.mx) is Mexico's open law platform. 30,000+ laws and 3.5M+ Elasticsearch articles covering federal, state, and municipal legislation.

**Monorepo layout:**

| Directory | Stack | Purpose |
|-----------|-------|---------|
| `apps/web` | Next.js 16, React 19, Tailwind 4 | Public site (tezca.mx) |
| `apps/admin` | Next.js, React 19 | Internal admin panel |
| `apps/api` | Django 5, DRF | REST API |
| `apps/indigo` | Django settings, WSGI, Celery | Django project root |
| `apps/parsers` | Python | Law text parsing pipeline |
| `apps/scraper` | Python | Federal/state/municipal scrapers |
| `packages/lib` | TypeScript | `@tezca/lib` -- shared types and utils |
| `packages/ui` | React, shadcn | `@tezca/ui` -- shared UI components |
| `packages/api-client` | TypeScript | `@tezca/api-client` -- published SDK |
| `packages/mcp-server` | Python, FastMCP | `tezca-mcp` -- MCP server for AI agents |

**License:** AGPL-3.0

---

## Dev Setup

### Prerequisites

- Python 3.11+, Poetry
- Node 20+, npm (workspaces)
- Docker and Docker Compose
- uv (for `packages/mcp-server` only)

### Infrastructure

```bash
docker compose up -d postgres redis elasticsearch
```

This starts PostgreSQL 16, Redis 7, and Elasticsearch 8.17.

### Backend

```bash
poetry install                      # core deps
poetry install -E export            # WeasyPrint, python-docx, ebooklib, jinja2
poetry install -E ocr               # pytesseract, pdf2image
poetry install -E production        # all optional deps
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
npm install                         # all workspaces
npm run dev:web                     # localhost:3000
npm run dev:admin                   # localhost:3001
npm run dev:all                     # both concurrently
```

### Required Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `ES_HOST` | `http://elasticsearch:9200` | Use `http://localhost:9200` outside Docker |
| `NPM_MADFAM_TOKEN` | -- | Needed in `.npmrc` for `@janua/*` and `@tezca/*` private packages |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | API base for frontend apps |
| `DB_ENGINE` | sqlite3 | Set to `django.db.backends.postgresql` for Postgres |
| `INTERNAL_API_URL` | falls back to `NEXT_PUBLIC_API_URL` | Server-side API URL for SSR inside Docker (e.g. `http://api:8000/api/v1`) |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis for Celery tasks |
| `TEZCA_ADMIN_USER_IDS` | `""` | Comma-separated Janua user IDs allowed admin access |
| `DHANAM_CHECKOUT_URL` | `https://dhanam.madfam.io/checkout` | Billing checkout URL (used by tier gates) |
| `TEZCA_DEPLOYMENT` | `self-hosted` | Deployment mode. `self-hosted` caps effective tier at academic |
| `QUALITY_QUARANTINE_GRADES` | `D,F` | Comma-separated quality grades to quarantine from indexing |
| `NEXT_PUBLIC_MONETIZATION_ENABLED` | `false` | When `true`, enables full tier checkout flows. When `false` (default), shows interest-capture forms instead of paywalls |
| `CRM_WEBHOOK_URL` | `""` | Phynd-CRM webhook URL (e.g. `https://crm.madfam.io/api/webhooks/tezca`). No-ops when empty |
| `CRM_WEBHOOK_SECRET` | `""` | HMAC-SHA256 secret for CRM webhook signing. No-ops when empty |
| `CHAT_ENABLED` | `false` | Master kill-switch for `/api/v1/chat/preguntar/`. Flip to `true` once Selva onboarding lands |
| `CHAT_BACKEND` | `mock` | `mock` (deterministic, dev/test) or `selva` (production OpenAI-compatible /v1) |
| `SELVA_API_URL` | `https://selva.town/v1` | Selva endpoint when `CHAT_BACKEND=selva` (canonical public domain) |
| `SELVA_API_TOKEN` | `""` | Janua-relayed bearer token for the `tezca-selva-relay` client |
| `SELVA_DEFAULT_MODEL` | `claude-haiku-4-5` | Default LLM model for chat completions |
| `ES_USERNAME` | `""` | Elasticsearch basic-auth user (required when `xpack.security.enabled=true`, default in compose) |
| `ES_PASSWORD` | `""` | Elasticsearch basic-auth password — override `changeme-dev-only` for any non-throwaway env |
| `DB_CONNECT_TIMEOUT` | `5` | Postgres connect timeout in seconds. Tighter than kernel default to fail-fast on dead primary during CNPG failover |
| `DB_KEEPALIVES_IDLE` | `30` | TCP keepalive idle (seconds). Detect dropped conns within ~60s vs Linux default ~2h |
| `DB_CONN_MAX_AGE` | `0` | Django `CONN_MAX_AGE`. 0 = open/close per request (PgBouncer fronts the cluster) |

---

## Key Commands

### Testing

```bash
# Backend (pytest + django, 2164 tests / 17 skipped as of 2026-04-28; 64% coverage)
poetry run pytest tests/ -v
poetry run pytest tests/parsers/test_parser_v2.py    # parser tests (100 tests)

# Spot-check tests (data integrity across pipeline layers)
poetry run pytest -m spotcheck -v
python manage.py spot_check --golden-set             # management command

# Web (vitest, 930 tests across 102 files; 63% coverage with all:true)
cd apps/web && npx vitest run

# Admin (vitest, 78 tests across 11 files)
cd apps/admin && npx vitest run

# MCP server (pytest + respx, 23 passed / 8 skipped)
cd packages/mcp-server && uv sync --all-extras && uv run pytest tests/ -v

# Data recovery
python manage.py retry_failed_non_leg --dry-run          # report retryable non-leg gaps
python manage.py retry_failed_non_leg --all --batch-size 50  # retry with enhanced timeout

# Quality backfill
python manage.py backfill_quality_scores --all --dry-run     # preview
python manage.py backfill_quality_scores --all               # backfill all
python manage.py backfill_quality_scores --law-id cpeum      # single law
python manage.py backfill_quality_scores --all --force        # rescore

# Domain classification
python manage.py classify_law_domains --all --dry-run        # preview
python manage.py classify_law_domains --all                  # classify all
python manage.py classify_law_domains --law-id cpeum         # single law

# Cross-reference backfill
python manage.py backfill_cross_references --all --dry-run   # preview
python manage.py backfill_cross_references --all --batch-size 50  # backfill

# RMF (Resolución Miscelánea Fiscal) — SAT regulatory feed for Karafiel
python -m apps.scraper.federal.rmf_scraper --year 2026                # discover only
python -m apps.scraper.federal.rmf_scraper --year 2026 --download      # discover + fetch PDFs
python manage.py ingest_rmf --catalog data/rmf/catalog.json            # upsert into Law table
python manage.py ingest_rmf --catalog data/rmf/catalog.json --dry-run  # preview

# State scrapers (manual run via Celery dispatch — useful before flipping a Beat schedule)
python manage.py shell -c "from apps.scraper.scheduling.tasks import run_state_scraper; print(run_state_scraper('hidalgo'))"
# State keys registered: baja_california, durango, quintana_roo, guerrero,
# nuevo_leon, cdmx, estado_de_mexico, michoacan, san_luis_potosi, zacatecas,
# aguascalientes, hidalgo, morelos, yucatan (14 of 32; coverage 14/32 → 16/32 with Wave 1A)

# DOF health verification
python manage.py verify_dof_health                           # 7-day report
python manage.py verify_dof_health --days 30 --json          # 30-day JSON report
python manage.py verify_dof_health --run-now                 # manual DOF check

# E2E (Playwright; 16 specs across 4 browser projects)
cd apps/web && npx playwright test
cd apps/web && DATA_INTEGRITY_E2E=1 npx playwright test data-integrity.spec.ts  # live API
cd apps/web && UI_FIDELITY_E2E=1 npx playwright test e2e/ui-data-fidelity.spec.ts e2e/search-data-completeness.spec.ts  # live API
cd apps/web && AUTH_E2E=1 npx playwright test e2e/annotation-alert-flow.spec.ts  # auth required
```

### Linting and Formatting

```bash
# Python
poetry run black --check apps/ tests/ scripts/
poetry run black apps/ tests/ scripts/
poetry run isort apps/ tests/ scripts/

# JavaScript/TypeScript
npm run lint:web
npm run lint:admin
npm run lint:all
```

### Quality audits (CI-enforced)

```bash
# Block silent bare-except blocks (`except Exception: pass` etc.)
poetry run python scripts/utils/audit_silent_excepts.py

# Block files >800 LOC (with explicit allowlist for known mega-scrapers)
poetry run python scripts/utils/audit_file_sizes.py

# Capture a TLS fingerprint for a host (for HOST_FINGERPRINTS pinning)
poetry run python scripts/utils/capture_tls_fingerprint.py <host>
```

### Build

```bash
npm run build:web
npm run build:admin
npm run build:all
```

---

## Architecture

### Authentication

`CombinedAuthentication` in `apps/api/middleware/combined_auth.py` checks in order:

1. **API key** -- `X-API-Key` header, `tzk_` prefix
2. **Janua JWT** -- `Authorization: Bearer <token>`
3. **Anonymous fallback**

Admin endpoints use `_protected()` in `apps/api/urls.py`, which sets `JanuaJWTAuthentication` + `IsAuthenticated` + `IsTezcaAdmin` directly on the view class. `IsTezcaAdmin` (in `apps/api/middleware/admin_permission.py`) checks JWT `role == "admin"` claim OR user ID in `TEZCA_ADMIN_USER_IDS` env var.

### Integration Policy (Zero Touch)

Tezca is a generic multi-tenant platform. The codebase must NEVER contain:
- Hardcoded references to specific consuming services (Karafiel, Forgesight, PravaraMES, etc.)
- Client-specific routing, middleware, or business logic
- Organization-specific webhook filters or API key handling

All integrations happen through standard, client-agnostic mechanisms:
- **API Keys** (`tzk_*`) — provisioned via `provision_api_key` command, scoped by tier/domains/scopes
- **Webhooks** — any subscriber can register via `/api/v1/webhooks/`, receives HMAC-signed events. Supports `domain_filter` (by category) and `law_id_filter` (by specific law official_id). SSRF-protected: URLs validated against private/reserved IPs at creation and delivery time. Payloads include `law_type` and `domains` for consumer-side routing
- **REST API** — standard endpoints, rate-limited by tier
- **Django signals** — `post_save` on `Law`/`LawVersion` triggers generic `dispatch_webhook_event()`

Consuming services configure themselves to connect to Tezca, not the other way around.

### Rate Limiting

`TieredRateThrottle` in `apps/api/tier_throttles.py`, sliding window via Redis cache:

| Tier | Aliases | Per Minute | Per Hour |
|------|---------|-----------|----------|
| anon | — | 10 | 100 |
| community | — | 1,000 | 100,000 |
| essentials | `free` | 30 | 500 |
| academic | `pro`, `premium` | 60 | 2,000 |
| institutional | `enterprise` | 200 | 50,000 |
| madfam | `internal` | 200 | 50,000 |

### Tier-Based Access Control

6-tier hierarchy defined in `apps/api/tier_permissions.py` (single source of truth):

| Tier | Rank | Audience | Search page_size | Key Features |
|------|------|----------|-----------------|--------------|
| anon | 0 | Unauthenticated | 25 | TXT export only |
| community | 1 | Self-hosters | 1,000 | PDF/JSON export, bulk download, API keys |
| essentials | 2 | Individual researchers | 50 | PDF/JSON export, API keys |
| academic | 3 | Academic institutions | 100 | LaTeX export, bulk download, search analytics |
| institutional | 4 | Government/enterprise | 1,000 | DOCX/EPUB export, webhooks, graph API |
| madfam | 5 | Internal MADFAM | 1,000 | All features |

- `RequireFeature.of("bulk_download")` gates `bulk_articles` (non-monotonic: community has it, essentials doesn't)
- `RequireFeature.of("webhooks")` gates `create_webhook` (institutional+ only)
- `RequireFeature.of("graph_api")` gates graph endpoints (institutional+ only). Public showcase endpoint (`/api/v1/graph/showcase/`) is unauthenticated (top 50 nodes, min_weight=5)
- `RequireTier.of("academic")` for rank-based gating (monotonic features)
- `check_feature(tier, "search_analytics")` gates analytics view
- Feature flags and limits defined in `apps/api/tiers.json`
- `normalize_tier()` handles legacy names: `free`→`essentials`, `premium`/`enterprise`/`pro`→`academic`, `internal`→`madfam`
- `get_effective_tier()` caps tier at academic in self-hosted mode (`TEZCA_DEPLOYMENT=self-hosted`)

### Monetization

- **Monetization is currently disabled** (`NEXT_PUBLIC_MONETIZATION_ENABLED` defaults to `false`). Gated features show `InterestGate` (email capture) instead of `TierGate` (checkout). Set `NEXT_PUBLIC_MONETIZATION_ENABLED=true` to enable full tier checkout flows.
- `FeatureInterest` model collects email + feature intent signals at `POST /api/v1/interest/`
- Admin stats: `GET /api/v1/admin/interests/` (protected) returns counts by feature_key
- **Pricing source-of-truth**: `internal-devops/decisions/2026-04-25-tulana-ecosystem-pricing.md`. Tezca tiers: Community 199 / Essentials 599 / Institutional 1,999 MXN/mo. Anchored on Tulana v0.1 competitor band (vLex, Doctrina AI, LegalTracker MX). **Confidence: low** — pending v0.2 WTP automation.
- **PMF measurement**: per RFC 0013, NPS + Sean Ellis + retention via `@madfam/pmf-widget` → Tulana `/v1/pmf/*` endpoints. Composite PMF Score gates the `MONETIZATION_ENABLED` flip from InterestGate → checkout.
  - **Integration status (2026-04-26):** Wired into `apps/web` via `components/pmf/PmfWidgetMount.tsx`, mounted in the root `app/layout.tsx` (renders nowhere visible until activated). Gates: feature flag `NEXT_PUBLIC_PMF_WIDGET_ENABLED` (default `false`) + `auth.isAuthenticated` + path-prefix exclusion list (`/login`, `/bienvenida`, `/admin`). `productSlug=tezca`, `apiUrl=$NEXT_PUBLIC_TULANA_API_URL` (default `https://tulana-api.madfam.io`), triggers: NPS afterSession=5 / dismissCooldown=30d, Sean Ellis afterSession=3 / dismissCooldown=45d, smile after 3 `law_viewed` actions. Activation is operator-gated: requires (1) `NPM_MADFAM_TOKEN` rotation so `@madfam/pmf-widget@^0.1.0` can publish + install, (2) deletion of `apps/web/types/madfam-pmf-widget.d.ts` once the published `.d.ts` ships, (3) flipping `NEXT_PUBLIC_PMF_WIDGET_ENABLED=true` in the deployed env. The dynamic import is fail-closed — a missing module never breaks the page.
- **Monetization architecture (full ecosystem)**: `internal-devops/ecosystem/monetization-architecture-2026-04-26.md`. Tezca enforces tiers via `SubscriptionThrottleGuard` but does not mint them — Dhanam owns subscription state and fans out `subscription.activated|upgraded|cancelled` events. Tezca tier names are defined in Dhanam catalog (`tezca-free`, `tezca-pro`, `tezca-enterprise`).

### Billing

- Checkout URL: `settings.DHANAM_CHECKOUT_URL` (env `DHANAM_CHECKOUT_URL`, default `https://dhanam.madfam.io/checkout`)
- Webhook: `POST /api/v1/billing/webhook/` — HMAC-SHA256 signed by Dhanam, upgrades/downgrades API key tiers
- Secret: `DHANAM_WEBHOOK_SECRET` env var
- Plan mappings: `tezca_community`, `tezca_essentials`, `tezca_academic`, `tezca_institutional`, `tezca_madfam` → corresponding tiers (legacy `tezca_pro`→`academic`)
- Downgrade fallback: `free_member` (free tier for authenticated users)

### Trials

- `POST /api/v1/trial/start/` — starts a trial (only `free_member` users eligible, per `trial_eligible` flag in `tiers.json`)
- `GET /api/v1/trial/status/` — returns active/expired status, days remaining
- Trial durations: `TRIAL_DURATION_NO_CC_DAYS` (default 3) and `TRIAL_DURATION_WITH_CC_DAYS` (default 21), configurable via env
- Valid trial plans: `essentials`, `academic`, `institutional` (set in `settings.TRIAL_VALID_PLANS`)
- `expire_trials` Celery task runs hourly, clears expired trial fields
- CC extension: `trial.cc_provided` Dhanam webhook event extends trial to 21 days from start
- Frontend: `TrialBadge` (countdown in Navbar), `ConversionBanner` (CTA for non-paid users), `/precios` pricing page

### AI Chat (`/preguntar`)

- `POST /api/v1/chat/preguntar/` — first-party RAG-over-corpus chat assistant (Track 2 of `docs/strategy/FEATURE_PARITY_PLAN_2026-04-27.md` §3.1).
- Four gating layers in `apps/api/chat/views.py:preguntar`: (1) `CHAT_ENABLED` env, (2) authenticated user, (3) `RequireFeature.of("chat")` (essentials+ tier), (4) daily-message budget per `chat_messages_per_day` in `tiers.json` (essentials=30, academic=100, institutional=1000, madfam=-1).
- Tezca holds **zero** OpenAI/Anthropic API keys. Every LLM call routes through Selva at `/v1` (OpenAI-compatible) per the MADFAM ECOSYSTEM convention. Configurable via `CHAT_BACKEND` (`mock` for dev/test, `selva` for production).
- RAG pipeline: ES BM25 retrieval (top-5, 800-char snippets) → system prompt with `[law_id#article_id]` citation format → Selva chat-completion → cited response with `/leyes/{id}#article-{N}` links rendered via the existing `LinkifiedArticle` component.
- Failure-tolerant: ES down → empty context, polite reply, no Selva call. Selva down → 502 to user, no budget burn.
- Usage logged to `APIUsageLog` rows tagged `endpoint='chat.preguntar'`. Budget reset is UTC 00:00.
- Operator unblocker (Track 8): Selva must provision the `tezca-selva-relay` Janua client. Spec at `docs/strategy/SELVA_ONBOARDING_TICKET_2026-04-27.md`.

### RMF (Resolución Miscelánea Fiscal)

- SAT-published annual fiscal resolution + quarterly modifications + ~31 annexes per year. Required by Karafiel's Wave-1 GTM compliance feed (Track 1 / `docs/strategy/FEATURE_PARITY_PLAN_2026-04-27.md` §3.6).
- Scraper: `apps/scraper/federal/rmf_scraper.py` (`RmfScraper` class). Requests-first against `www.sat.gob.mx`, polite 1 req/sec rate-limit, classifies anchors into annual / modification / annex documents.
- Celery task: `dataops.run_rmf_scraper` — scheduled `rmf-quarterly-scrape` (8th of Jan/Apr/Jul/Oct, 03:00). Offset from `dof-historical-quarterly` (1st of same months).
- Ingest: `python manage.py ingest_rmf --catalog data/rmf/catalog.json` upserts Law + LawVersion with `category="resolución_miscelánea_fiscal"` and `domains=["fiscal"]`.
- Karafiel's webhook subscription `domain_filter: ["fiscal"]` will receive `law.created` / `law.updated` events for these via the standard `apps/api/webhooks.py` dispatch — no Karafiel-specific code in tezca.

### Billing UI (`/cuenta/billing`)

- Customer-facing billing surface delegating to Dhanam (Track 4 / `docs/strategy/FEATURE_PARITY_PLAN_2026-04-27.md` §3.3).
- Tezca holds **zero** Stripe keys. Tezca calls `api.dhan.am/v1/portal` and `api.dhan.am/v1/invoices`; Dhanam owns subscription state.
- Two display modes: `MONETIZATION_ENABLED=false` → InterestGate fallback; `MONETIZATION_ENABLED=true` → current-plan card + customer-portal CTA + invoice history table (PDF + CFDI 4.0 XML download links).
- Webhook flow handled by `apps/api/billing_stream_consumer.py` (Redis stream `madfam:billing-events`, consumer group `tezca-consumers`). `subscription.activated|cancelled` events map to `APIKey.tier` updates.

### Route Conventions

- **API endpoints are English:** `/api/v1/laws/`, `/api/v1/search/`, `/api/v1/categories/`, `/api/v1/coverage/`, `/api/v1/contributions/`, `/api/v1/judicial/`, `/api/v1/trial/`, `/api/v1/billing/`, `/api/v1/chat/preguntar/`, `/api/v1/user/apikeys/`
- **Web routes are Spanish:** `/leyes/`, `/busqueda/`, `/comparar/`, `/categorias/`, `/estados/`, `/cobertura/`, `/contribuir/`, `/convocatoria/`, `/jurisprudencia/`, `/desarrolladores/`, `/grafo/`, `/preguntar/` (chat UI, follow-up PR), `/precios/`, `/bienvenida/`, `/login/`, `/cuenta/apikeys/`, `/cuenta/billing/`
- 301 redirects exist from old English web routes (`/laws/` -> `/leyes/`)

### Domain Taxonomy

- `Law.category` stores document type: `ley`, `acuerdo`, `reglamento`, `decreto`, `codigo`, `constitucion`, `resolución_miscelánea_fiscal` (RMF), etc.
- `Law.domains` (JSONField, list of strings) stores legal branch classification: `labor`, `fiscal`, `criminal`, `civil`, `commercial`, `administrative`, `constitutional`, `environmental`, `health`, `education`
- A law can belong to multiple domains (e.g. `["labor", "administrative"]`)
- `classify_law_domains` management command populates `domains` via keyword matching against `Law.name`
- `DOMAIN_MAP` in `constants.py` maps composite domains (e.g. `manufacturing`, `customs`) to lists of base domains for filtering
- Domain filtering (`?domain=labor`) checks both `Law.domains` (JSONField) and `Law.category` (fallback for unclassified laws)
- ES index includes `domains` keyword field on both `laws` and `articles` indices
- Webhook `domain_filter` matches against the `domains` array in event payloads

### Elasticsearch

- Singleton client in `apps/api/config.py` (`es_client`)
- Index name: `articles` (constant `INDEX_NAME`), also aliased via `INDEX_ALIAS`
- ES 8.17, timeout 30s, 3 retries, 10 connections per node
- Always use `es_client` from config, never instantiate a new client
- **Alias strategy**: `articles` is an alias pointing to a versioned concrete index (`articles_v{timestamp}`). Zero-downtime reindex via `index_laws --reindex` creates a new versioned index, indexes into it, then atomically swaps the alias. One-time migration from concrete to alias via `manage_es_alias --migrate` or `index_laws --migrate-alias`
- **Alias management**: `python manage.py manage_es_alias --status|--migrate|--rollback INDEX|--cleanup`
- **Graceful degradation**: When ES is unavailable, `law_articles` and `law_stats` return HTTP 200 with `degraded: true` and empty/partial data instead of 500. Frontend shows an "articles unavailable" banner via `articlesDegraded` state in `LawDetail.tsx`.
- **Search relevance**: `function_score` with Gaussian decay on `publication_date` (5-year half-life, 1-year offset) applied on relevance sort only. `match_phrase` should clauses boost exact phrase matches in `text` (3.0) and `law_name` (5.0). Zero-result rescue retries with `fuzziness: "2"` and `minimum_should_match: "50%"` when first query returns 0 hits.
- **Synonyms**: 52 synonym pairs in `spanish_legal_synonyms` filter covering legal terminology, procedural, constitutional, commercial, tax, and administrative domains. Changes require `--reindex`.

### Quality Quarantine

- `LawVersion.quality_grade` (A-F) and `quality_score` (0-100) populated by parser pipeline
- Pipeline gate (Stage 4.5): D/F grades are quarantined — `result.success = False`, XML preserved for review
- `QUALITY_QUARANTINE_GRADES` setting (env var, default `D,F`) controls which grades are blocked
- `index_laws` excludes quarantined laws by default; `--include-quarantined` overrides
- Law detail API exposes `grade`/`score` from latest version
- Admin endpoint `GET /api/v1/admin/quarantined/` lists quarantined laws (protected)
- Admin endpoint `GET /api/v1/admin/task-health/` returns per-operation scraper health: last_run, run_count, success_rate, staleness detection (protected)

### Celery

- Broker and result backend: Redis
- Beat scheduler: `django_celery_beat.schedulers:DatabaseScheduler`
- Scheduled tasks defined in `apps/indigo/settings.py` (`CELERY_BEAT_SCHEDULE`)
- Worker concurrency: 4
- 23 scheduled tasks: health checks (daily/weekly), staleness detection, DOF daily, treaty/NOM/CONAMER scraping, coverage reports, parser pipeline (weekly), `state-guerrero-monthly` and `state-nuevo-leon-monthly` (monthly state scraping), `scjn-weekly-scrape` (SCJN judicial corpus, Sunday midnight), `scjn-playwright-weekly` (Saturday 22:00), `conamer-playwright-weekly` (Friday 23:00), `ojn-recovery-monthly` (10th), `wayback-recovery-monthly` (20th), `dof-historical-quarterly` (Jan/Apr/Jul/Oct), `check-scraper-health-daily` (daily 08:00, logs stale/failing scrapers), `nom-monthly-full` (15th, full-agency NOM scan with `priority_only=False`), `judicial-ingest-weekly` (Sunday 02:00, auto-ingests SCJN batches), `classify-domains-weekly` (Monday 05:30, classifies new laws into legal domains)

### Storage

- `apps/api/storage.py` -- `StorageBackend` abstraction (local filesystem or Cloudflare R2)
- Controlled by `STORAGE_BACKEND` env var (`local` or `r2`)
- boto3 is an optional dependency (`poetry install -E r2`)
- `apps/api/utils/paths.py` -- `read_data_content()`, `data_exists()`, `read_metadata_json()` provide R2 fallback for all data reads
- R2 fallback pattern: try local filesystem first → fall back to R2 via `read_data_content()`. Used by:
  - `law_views.py::_load_universe_registry()` — coverage stats (TTL-cached 5 min)
  - All ingestion management commands (`index_laws`, `ingest_state_laws`, etc.)
  - `coverage_dashboard.py::_load_json()` — all 7 JSON reads in coverage dashboard

---

## Design Tokens and Conventions

### UI Components

All UI primitives come from `@tezca/ui` (Card, Badge, Button, etc.). Import from `@tezca/ui`, not from raw radix or shadcn directly.

### Tier-Gating Components

- **`TierGate`** — Conditional upgrade prompt based on user tier. 4 variants: `inline` (compact banner), `overlay` (blur backdrop), `card` (standalone with benefits), `toast` (slide-in for rate limits). Supports countdown timer, i18n, and dismiss. Replaces the deprecated `UpgradeBanner`.
- **`TierComparison`** — Feature comparison table across Community/Essentials/Academic/Institutional tiers. Desktop table + mobile stacked cards. Use `compact` prop for inline usage.
- **`ConversionBanner`** — CTA banner for non-paid users. Self-hides via `hasPaidAccess(tier)`. Placed on homepage and law detail (after RelatedLaws). Tracks `conversion_banner.viewed` on mount and `conversion_banner.cta_clicked` on CTA.
- **`GraphTierMessage`** — Institutional tier messaging for graph page. Shows `InterestGate` (pre-monetization) or `TierGate` (monetization enabled) for non-institutional users. Tracks `graph_tier_message.shown`.
- **`DevApiCta`** — API access CTA for developer docs page. Shows for unauthenticated or unpaid users. Tracks `dev_docs.cta_clicked`.
- **`LinkifiedArticle`** — Cross-references are loaded in batch by `ArticleViewer` via `useBatchCrossRefs` hook (eliminates N+1). Individual articles receive refs via `preloadedRefs` prop. The `crossRefsDisabled` prop defaults to `false` when batch refs are available. Use the batch endpoint (`POST /api/v1/laws/{law_id}/articles/references/batch/`) for custom integrations.
- **`JsonLd`** — Shared component for injecting `<script type="application/ld+json">` structured data. Used for BreadcrumbList (9 pages), FAQPage (`/precios`), Dataset (`/cobertura`), and CollectionPage (`/categorias/[category]`).

### Colors

Use semantic Tailwind classes, never raw color values:

```
bg-muted              text-muted-foreground
bg-destructive/10     text-destructive
bg-primary            text-primary-foreground
```

Do NOT use `bg-red-500`, `text-gray-600`, or any raw Tailwind color.

### Error Displays

```tsx
<div className="bg-destructive/10 text-destructive">Error message</div>
```

### Text Size

Minimum text size is `text-xs` (12px). Never use `text-[10px]` or smaller.

### Spanish Language

Spanish accents are required in all user-facing text:

- articulo -> articulo (wrong), use "articulo" only in code identifiers
- User-facing: articulo, pagina, busqueda, termino, publicacion

### Admin Components

Presentational components in `apps/admin` should NOT have `'use client'` unless they use React hooks or event handlers.

---

## Internationalization (i18n)

Trilingual support: Spanish (es), English (en), Classical Nahuatl (nah).

```typescript
type Lang = 'es' | 'en' | 'nah';
```

- `useLang()` hook provides current language
- Content objects use `Record<Lang, string>` pattern
- `LOCALE_MAP` in `LanguageContext.tsx` for lookups (replaces ternaries)
- `layout.tsx` includes `"latin-ext"` font subset for Nahuatl macrons

---

## Key Files

| File | Purpose |
|------|---------|
| `apps/api/config.py` | ES_HOST, INDEX_NAME, es_client singleton |
| `apps/api/constants.py` | KNOWN_STATES (32 states), DOMAIN_MAP (generic + SCIAN 2023-aligned + consumer-facing: training, customs, safety). Used for composite domain expansion (e.g. `manufacturing` → `["labor", "administrative", "commercial"]`). The `Law.domains` JSONField is the canonical source for legal branch classification; `Law.category` stores document type (`ley`, `acuerdo`, `reglamento`, etc.) |
| `apps/api/management/commands/provision_api_key.py` | CLI API key provisioning |
| `apps/api/middleware/admin_permission.py` | `IsTezcaAdmin` permission (JWT role or user ID allow-list) |
| `apps/api/tier_permissions.py` | Single source of truth for tier naming, ranking, format access, rate limits. Re-exports `RequireTier`, `RequireFeature`, `check_feature`, `get_effective_tier` from middleware |
| `apps/api/middleware/tier_permissions.py` | `RequireTier` (rank-based), `RequireFeature` (feature-flag-based), `get_effective_tier()` (self-hosted cap) |
| `apps/api/tiers.json` | Feature flags and limits per tier (loaded by tier_permissions) |
| `apps/api/tier_throttles.py` | Rate limiting by tier (imports from tier_permissions) |
| `apps/api/posthog_analytics.py` | PostHog telemetry — `init_posthog()`, `track()`, `identify()`, `get_distinct_id(request)`. No-op when `POSTHOG_API_KEY` is unset |
| `apps/web/lib/analytics/posthog.ts` | Frontend PostHog — `initPostHog()`, `trackEvent()`, `identifyUser()`, `resetUser()`. No-op when `NEXT_PUBLIC_POSTHOG_KEY` is unset |
| `apps/api/billing_views.py` | Dhanam billing webhook receiver (HMAC-verified tier upgrades) |
| `apps/api/trial_views.py` | Trial start/status endpoints, duration constants from settings |
| `apps/web/lib/billing.ts` | Checkout URL builders (`getCheckoutUrl`, `getTrialCheckoutUrl`, `hasPaidAccess`) |
| `apps/web/lib/pricing.ts` | Pricing constants (PRICING, PROMO) for frontend tier cards |
| `apps/api/utils/url_validation.py` | Webhook SSRF protection — validates URLs against private/reserved IPs |
| `apps/api/storage.py` | StorageBackend (local + R2) |
| `apps/api/export_views.py` | PDF/TXT/LaTeX/DOCX/EPUB/JSON export |
| `apps/api/graph_views.py` | Law graph API (ego graph + global overview + public showcase for Sigma.js) |
| `apps/api/export_throttles.py` | Export-specific rate limits by tier (imports from tier_permissions) |
| `apps/api/models.py` | Law, Article, ExportLog, AcquisitionLog, Contribution, JudicialRecord, FeatureInterest (with wishlist field) |
| `apps/api/interest_views.py` | Feature interest capture endpoint (`POST /api/v1/interest/`) — email + feature_key + wishlist collection before monetization. `ALLOWED_FEATURES` includes `early_access` for pre-monetization waitlist |
| `apps/api/user_apikey_views.py` | Self-serve API key CRUD (`GET/POST /api/v1/user/apikeys/`, `PATCH ./<prefix>/`, `DELETE ./<prefix>/revoke/`) — tier-inherited, max 5 keys |
| `apps/api/crm_sync.py` | CRM webhook dispatch — sends interest.created and newsletter.subscribed events to phynd-crm (no-ops when CRM_WEBHOOK_URL not set) |
| `apps/indigo/settings.py` | Django settings, Celery Beat schedule |
| `apps/web/lib/config.ts` | API_BASE_URL, INTERNAL_API_URL |
| `apps/web/lib/auth-token.ts` | Shared Janua auth token retrieval utility |
| `apps/web/components/providers/AuthContext.tsx` | Janua JWT auth state |
| `apps/web/components/TierGate.tsx` | Tier-gating upgrade prompts (4 variants, i18n, countdown) |
| `apps/web/components/InterestGate.tsx` | Pre-monetization interest-capture component (4 variants, email form, wishlist, i18n). Shown when `MONETIZATION_ENABLED=false`. Fires `funnel.premium_interest` for `early_access` feature |
| `apps/web/app/bienvenida/page.tsx` | UTM-aware landing page for social media traffic. Reads `utm_source/medium/campaign` params. Newsletter signup → CRM dispatch. Account CTA after subscription. PostHog `funnel.landing_viewed` + `funnel.newsletter_subscribed` |
| `apps/web/app/login/page.tsx` | Login/signup page — renders Janua SignIn/SignUp with redirect support |
| `apps/web/app/cuenta/page.tsx` | Account page — profile card, quick links (bookmarks, notes, alerts, API keys), tier comparison |
| `apps/web/app/cuenta/apikeys/page.tsx` | Self-serve API key management — list, create, copy secret, revoke. InterestGate for anon |
| `apps/web/lib/feature-labels.ts` | Feature key → i18n display labels for InterestGate |
| `apps/web/components/TierComparison.tsx` | Tier feature comparison table |
| `apps/web/contexts/LanguageContext.tsx` | i18n with LOCALE_MAP |
| `apps/web/lib/sentry.ts` | Sentry init + `captureError()` (conditional on `@sentry/nextjs`) |
| `apps/web/components/ErrorBoundary.tsx` | Class-based error boundary (wraps layout children), reports to Sentry |
| `apps/web/components/RouteError.tsx` | Shared i18n route error component (used by 20 route `error.tsx` files) |
| `apps/web/app/global-error.tsx` | Layout-level catch-all (raw styles, Sentry) |
| `apps/api/management/commands/spot_check.py` | Data integrity spot-check (samples laws, traces DB→file→ES→API) |
| `apps/parsers/error_tracker.py` | ErrorTracker + ErrorRecord for pipeline error logging |
| `apps/parsers/pipeline.py` | Ingestion pipeline (Download→Extract→Parse→Validate→Quality→Quarantine) with ErrorTracker |
| `apps/ingestion/db_saver.py` | DatabaseSaver — persists law versions with quality metrics to Django DB |
| `apps/api/management/commands/retry_failed_non_leg.py` | Retry failed non-leg state law downloads |
| `apps/api/management/commands/backfill_quality_scores.py` | Backfill quality_grade/quality_score for existing LawVersion records |
| `apps/api/management/commands/classify_law_domains.py` | Keyword-based domain classification for Law.domains JSONField |
| `apps/api/management/commands/backfill_cross_references.py` | Cross-reference detection backfill for existing laws |
| `apps/api/management/commands/verify_dof_health.py` | DOF daily task health report (last N days, optional `--run-now`) |
| `apps/scraper/state/guerrero.py` | Guerrero state congress scraper |
| `apps/scraper/state/nuevo_leon.py` | Nuevo Leon state congress scraper |
| `apps/scraper/state/aguascalientes.py` | Aguascalientes state congress scraper (Wave 1A — `congresoags.gob.mx`) |
| `apps/scraper/state/hidalgo.py` | Hidalgo state congress scraper (Wave 1A — `congreso-hidalgo.gob.mx`) |
| `apps/scraper/state/morelos.py` | Morelos state congress scraper (Wave 1A — `congresomorelos.gob.mx`) |
| `apps/scraper/state/yucatan.py` | Yucatán state congress scraper (Wave 1A — `congresoyucatan.gob.mx`) |
| `apps/scraper/federal/rmf_scraper.py` | SAT Resolución Miscelánea Fiscal scraper (annual + quarterly mods + annexes; tags `domains=["fiscal"]` for Karafiel webhook fanout) |
| `apps/api/management/commands/ingest_rmf.py` | Upserts RMF catalog into `Law` + `LawVersion` (sister to `ingest_non_legislative_laws`) |
| `apps/api/chat/__init__.py` | First-party AI assistant package — exports `SelvaClient`, `MockSelvaClient`, `get_selva_client()` |
| `apps/api/chat/selva_client.py` | OpenAI-compatible HTTP client + mock; selected via `CHAT_BACKEND` env. Tezca holds zero LLM API keys |
| `apps/api/chat/retriever.py` | RAG retrieval over articles ES index; builds system prompt with `[law_id#article_id]` citation format |
| `apps/api/chat/views.py` | `POST /api/v1/chat/preguntar/` view with 4 gating layers (CHAT_ENABLED → auth → RequireFeature("chat") → daily budget) |
| `apps/api/billing_stream_consumer.py` | Redis Streams consumer for `madfam:billing-events` (subscription.activated|cancelled → APIKey.tier) |
| `apps/web/app/cuenta/billing/page.tsx` | Customer-facing billing page — Dhanam-delegated portal CTA + invoice history (PDF + CFDI). Two modes via `MONETIZATION_ENABLED` |
| `packages/mcp-server/main.py` | MCP server entry point (FastMCP + uvicorn) |
| `packages/mcp-server/tools/` | 16 MCP tools proxying REST API |
| `apps/api/es_index_manager.py` | ES alias management (zero-downtime reindex) |
| `apps/api/management/commands/manage_es_alias.py` | CLI for ES alias status/migrate/rollback/cleanup |
| `apps/web/hooks/useBatchCrossRefs.ts` | Batch cross-reference fetching hook (eliminates N+1) |
| `apps/web/components/graph/graphConstants.ts` | Graph color modes, category/tier colors, sizing helpers |
| `apps/web/components/graph/GraphSearch.tsx` | Node search with autocomplete and camera animation |
| `apps/web/components/graph/GraphFilters.tsx` | Category filter pills for graph visualization |
| `apps/web/components/graph/GraphStats.tsx` | Collapsible graph statistics panel |
| `apps/web/components/graph/GraphTierMessage.tsx` | Institutional tier messaging for graph page (InterestGate or TierGate) |
| `apps/web/components/graph/useGraphExport.ts` | PNG export via Sigma canvas compositing |
| `apps/web/components/DevApiCta.tsx` | Developer docs API access CTA for non-paid users |
| `apps/scraper/playwright_base.py` | Shared Playwright ABC for browser-automated scrapers |
| `apps/scraper/judicial/scjn_playwright.py` | SJF browser scraper (Playwright, 4 extraction strategies + detail page enrichment) |
| `scripts/scraping/ojn_multipath_recovery.py` | OJN 3-path waterfall recovery for failed downloads (partial result persistence) |
| `scripts/scraping/wayback_bulk_recovery.py` | CDX API bulk mining for dead legal domains |
| `scripts/scraping/dof_historical_scan.py` | DOF 2000-2026 scan for gap-filling + NOM detection + checkpointing + cross-reference |
| `scripts/scraping/probe_datos_gob.py` | datos.gob.mx CKAN API probe, resource download, and legal relevance assessment |
| `scripts/utils/audit_silent_excepts.py` | AST-based scanner that fails CI on `except Exception: pass`-style swallows missing `# noqa: BLE001` |
| `scripts/utils/audit_file_sizes.py` | File-size audit with allowlist; fails CI on files >800 LOC outside the allowlist |
| `scripts/utils/capture_tls_fingerprint.py` | Captures leaf-cert SHA-256 fingerprint for `HOST_FINGERPRINTS` pinning |
| `apps/scraper/http.py` | Two-layer TLS trust: `HOST_FINGERPRINTS` (pinned) + `INSECURE_HOSTS` (verify=False fallback). `_FingerprintPinnedAdapter` validates leaf cert via urllib3 `assert_fingerprint`. |
| `apps/api/search_views.py` | Full-text search with function_score recency boost, phrase matching, zero-result rescue |
| `apps/api/admin_views.py` | Admin endpoints: metrics, jobs, config, pipeline, coverage, quarantine, task-health |
| `apps/web/components/JsonLd.tsx` | Shared JSON-LD structured data component (used across 10+ pages) |

---

## Common Gotchas

1. **ES_HOST outside Docker:** Must set `ES_HOST=http://localhost:9200`. The default (`http://elasticsearch:9200`) only resolves inside Docker Compose.

2. **NPM private packages:** `.npmrc` needs `NPM_MADFAM_TOKEN` for `@janua/*` and `@tezca/*` scoped packages. Without it, `npm install` fails.

3. **Lockfile integrity errors:** If `npm ci` fails on integrity hash, run `npm cache clean --force` then `npm install` to regenerate `package-lock.json`.

4. **`Map` icon collision:** `Map` from `lucide-react` shadows the global `Map` constructor. Always import as `MapIcon`.

5. **Optional Python deps:** These are not installed by default and will cause `ImportError` if missing:
   - WeasyPrint: `poetry install -E pdf`
   - pytesseract + pdf2image: `poetry install -E ocr`
   - boto3: `poetry install -E r2`
   - python-docx, ebooklib, jinja2: `poetry install -E export`

6. **Black version:** Always use `poetry run black` (not system black) to match the version pinned in `poetry.lock` (26.x).

7. **Poetry lockfile:** Always run `poetry lock` after changing `pyproject.toml` deps before committing.

8. **ESLint JSX rule:** No JSX inside try/catch blocks. Build data in the try block, return JSX outside.

9. **Admin `'use client'`:** Only add the directive to admin components that actually use hooks or event handlers. Presentational components should be server components.

10. **Test mocks:** Admin tests mock `@tezca/ui` and `next/link` inline via `vi.mock()`. When adding fields to shared types, update these mocks.

11. **`@janua/*` transpiling:** `@janua/ui` and `@janua/nextjs` must be listed in `transpilePackages` in `next.config.ts`. Without this, Turbopack fails with "Unknown module type" on their TypeScript source.

12. **ES ICU plugin:** The default ES Docker image does not include `analysis-icu`. Use `asciifolding` (built-in) instead of `icu_folding` for accent normalization.

13. **`@types/react` lockfile dedup:** The monorepo can end up with multiple `@types/react` versions (e.g. 19.2.10 in workspaces, 19.2.14 at root), causing Radix component type errors (`Key` type mismatch). Fix by removing nested `node_modules/@types/react` entries from `package-lock.json` and running `npm install`.

14. **`Protect` component:** `@janua/nextjs` `Protect` uses `redirectTo` prop, not `redirectUrl`.

15. **`_protected()` sets class attrs directly:** DRF's `authentication_classes`/`permission_classes` decorators from `rest_framework.decorators` set attributes on the function, not on the `WrappedAPIView` class, so they have no effect when applied after `@api_view`. `_protected()` in `urls.py` works around this by setting `view_func.cls.authentication_classes` and `view_func.cls.permission_classes` directly.

16. **Admin endpoint test pattern:** Tests for `_protected()` endpoints must patch both `JanuaJWTAuthentication.authenticate` (returns `(admin_user, "fake-token")`) and `IsTezcaAdmin.has_permission` (returns `True`). Patching `CombinedAuthentication.authenticate` has no effect on admin endpoints. See `_start_admin_patches()` in `tests/api/test_admin_views.py` for the canonical pattern.

17. **`APIKey.rate_limit_per_hour` is capped:** Custom per-key rate limit overrides are capped at 100,000/hour in `TieredRateThrottle._get_limits()`. Model validators enforce 1–100,000 range.

18. **`.doc` extraction deps:** `retry_failed_non_leg` and the pipeline `.doc` extraction require either `antiword` or `libreoffice` on the system for legacy `.doc` files. `.docx` uses `python-docx` from `poetry install -E export`.

---

## CI/CD

- Python CI runs `poetry run black --check` and `poetry run pytest` (matrix: Python 3.11 + 3.12)
- Node CI runs `npm run lint:all` and `npm run build:all` (matrix: Node 20 + 22)
- E2E tests run against `docker-compose.e2e.yml` stack (blocking gate, Playwright with 2 CI retries)
- Security audits are blocking: `pip-audit` (runs inside Poetry venv) and `npm audit --audit-level=high` (Node)
- CodeQL/SAST runs on push/PR to main and weekly (Monday 6am UTC) for Python + JavaScript/TypeScript
- MCP server tests run in CI via `uv sync && uv run pytest`
- MCP server publishes to PyPI on `mcp-v*` tags via OIDC trusted publisher
- Deploy workflows push digest commits that can race with subsequent pushes -- use `git pull --rebase` before pushing
- R2 storage tests use `pytest.mark.skipif(not _has_boto3)` -- they skip in CI where boto3 is not installed
- WeasyPrint and other optional deps are similarly skipped in CI
- Docker Compose services have resource limits (cpu/memory) to prevent runaway containers

### Quality gates (PR-blocking)

These gates run as discrete CI steps and fail the merge on regression:

| Gate | Threshold | Source |
|---|---|---|
| Backend coverage | `--cov-fail-under=60` (actual ~64%) | `.github/workflows/ci.yml` |
| Frontend coverage (`all: true`) | stmts 61 / branches 54 / funcs 58 / lines 62 (floor−2pp; actuals ~63/57/60/64) | `apps/web/vitest.config.mts` |
| Silent bare-except | 0 findings | `scripts/utils/audit_silent_excepts.py` |
| File size | 0 files >800 LOC outside allowlist | `scripts/utils/audit_file_sizes.py` |
| pip-audit | 0 high-severity CVEs in locked deps | CI step |
| npm audit | 0 high-severity CVEs (`--audit-level=high`) | CI step |
| CodeQL | 0 new alerts on PR | weekly + on-push |

Backend coverage gate has been ratcheted 44 → 48 → 51 → 54 → 56 → 60 across PRs #56, #77–80, and the WS-R1 push (PR #82). WS-R1 is now done; next ratchet is gated on WS-R5/R6 maturing per `docs/strategy/A_PLUS_PROGRESS_2026-04-27.md`.

## Strategy Documentation

`docs/strategy/` is the authoritative home for product/architectural strategy. Read these before assuming a feature priority. Index: [`docs/strategy/INDEX.md`](docs/strategy/INDEX.md).

| Doc | Purpose |
|---|---|
| `STRATEGIC_OVERVIEW.md` | High-level product vision (legacy, refresh pending) |
| `PRD.md` | Product requirements (legacy, refresh pending) |
| `COMPETITIVE_BENCHMARK_2026-04-27.md` | Tezca vs Buho/vLex/Tirant/Lexius/Help-AI gap analysis |
| `FEATURE_PARITY_PLAN_2026-04-27.md` | Gap-by-gap implementation plan, ecosystem-anchored. Source-of-truth for which tracks are in flight |
| `KARAFIEL_INTEGRATION_AUDIT_2026-04-27.md` | Tezca-side readiness for Karafiel as anchor paying customer; P0 SQL queries for operator |
| `SELVA_ONBOARDING_TICKET_2026-04-27.md` | Operator-side spec for provisioning the Selva relay client (unblocks `CHAT_BACKEND=selva`) |
| `CNPG_MIGRATION_PREP_2026-04-27.md` | Tezca-side connection-pool prep + cutover runbook (gated on RFC 0012 cluster) |
| `DOCKET_WATCHER_BOOTSTRAP_2026-04-27.md` | Bootstrap kit for the `madfam-org/docket-watcher` sibling repo (Q1-2027) |
| `A_PLUS_REMEDIATION_PLAN_2026-04-27.md` | Original 8-workstream A+ plan + rubric (still authoritative on dimensions) |
| `A_PLUS_PROGRESS_2026-04-27.md` | **Live A+ progress + forward plan.** Tracks PRs #55–80 (44%→61% backend coverage, 0 silent excepts, TLS pinning architecture). 6 remaining workstreams (WS-R1…WS-R6) with sequencing |
| `partnerships/` | Partner-specific integration agreements |

**Tracks shipped 2026-04-27 (PRs #46–52):** RMF scraper, `/preguntar` chat scaffold, state scrapers Wave 1A (4 states), `/cuenta/billing` scaffold, Karafiel audit doc, CNPG settings prep, docket-watcher spec, Selva onboarding ticket spec.

**A+ remediation shipped (PRs #55, #56, #75–83):** backend coverage 44%→**64%** (gate 60), frontend coverage 56%→**63%** with `all:true` (gates 61/54/58/62), 0 silent bare-except, 0 files >800 LOC, TLS fingerprint pinning architecture, silent-except CI gate, file-size CI gate, CVE SLO + Dependabot, scraper first-run checklist. **Composite grade: B+/B → A.** WS-R1 + WS-R2 ✅ DONE; remaining work (R3–R6: TLS capture, ISO 27001, synthetic monitoring, HA, Grafana) is operator/platform-side. See `A_PLUS_PROGRESS_2026-04-27.md`.

## Known Issues

See `/Users/aldoruizluna/labspace/claudedocs/ECOSYSTEM_AUDIT_2026-04-23.md` for the original ecosystem audit.

Open:
- **🟡 H7 (architecture fix landed; capture sweep pending)** — `apps/scraper/http.py` now supports per-host SHA-256 fingerprint pinning via `HOST_FINGERPRINTS` and a `_FingerprintPinnedAdapter`. The 10 hosts still in `INSECURE_HOSTS` need fingerprint capture (`scripts/utils/capture_tls_fingerprint.py <host>`) before the residual MITM window closes. Operator task: schedule a capture sweep on stable network.
- **🟡 State coverage incomplete** — 16 of 32 states have scrapers (Wave 1A added Aguascalientes, Hidalgo, Morelos, Yucatán). Wave 1B/1C remaining for full parity claim per `FEATURE_PARITY_PLAN_2026-04-27.md` §3.5.
- **🟡 ES single-node** — Postgres HA prep done (Track 6); ES HA is a separate pending project.
- **🟡 First-paid-customer blockers** — Selva onboarding (CHAT_BACKEND flip), Stripe live keys + Tezca price IDs in Dhanam (MONETIZATION_ENABLED flip), and Karafiel team's Wave 1 Month 1 deliverables. All operator-side; specs are landed.

Resolved:
- ~~**🟠 H2: CORS echoes `*` when `Origin` header missing on API-key preflight**~~ — Fixed 2026-04-23 (#37, #40): missing Origin now 403s, allowed Origins echo back with `Vary: Origin`.
- ~~**🟡 M3: `DEBUG=True` in `.env`**~~ — Resolved 2026-04-27: `.env` is not tracked and not present in repo; `.env.example` ships `DEBUG=False`. No prod workload risk from this vector.
- ~~**🟡 H13: `.env` committed**~~ — Resolved: `.gitignore` covers `.env`, `.env.local`, `.env.*.local`, `.env.production`. Verified absent from `git ls-files`.
- ~~**🟡 RMF scraper stub deleted with no replacement**~~ — Resolved 2026-04-27 (#46): full RMF scraper + ingest command + Celery beat schedule. SAT regulatory feed available for Karafiel's compliance use case.
- ~~**🟡 No first-party AI assistant**~~ — Resolved 2026-04-27 (#47, #49): `/api/v1/chat/preguntar/` scaffold ships behind `CHAT_ENABLED=false`. Selva onboarding ticket spec landed; flip is one env-var change once Selva provisions `tezca-selva-relay`.
- ~~**🟡 No subscription billing UI**~~ — Resolved 2026-04-27 (#51): `/cuenta/billing` scaffold ships behind `MONETIZATION_ENABLED=false`. Tezca delegates to Dhanam — zero Stripe keys held.

<!-- END LEGACY_CLAUDE_IMPORT -->
