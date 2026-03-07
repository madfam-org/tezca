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

---

## Key Commands

### Testing

```bash
# Backend (pytest + django, 782 tests)
poetry run pytest tests/ -v
poetry run pytest tests/parsers/test_parser_v2.py    # parser tests (100 tests)

# Spot-check tests (data integrity across pipeline layers)
poetry run pytest -m spotcheck -v
python manage.py spot_check --golden-set             # management command

# Web (vitest, 402 tests across 50 files)
cd apps/web && npx vitest run

# Admin (vitest, 72 tests across 10 files)
cd apps/admin && npx vitest run

# MCP server (pytest + respx, 18 tests)
cd packages/mcp-server && uv run pytest tests/ -v

# E2E (84 tests across 15 specs, 4 browser projects)
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

### Integration Policy (Zero Touch)

Tezca is a generic multi-tenant platform. The codebase must NEVER contain:
- Hardcoded references to specific consuming services (Karafiel, Forgesight, PravaraMES, etc.)
- Client-specific routing, middleware, or business logic
- Organization-specific webhook filters or API key handling

All integrations happen through standard, client-agnostic mechanisms:
- **API Keys** (`tzk_*`) — provisioned via `provision_api_key` command, scoped by tier/domains/scopes
- **Webhooks** — any subscriber can register via `/api/v1/webhooks/`, receives HMAC-signed events
- **REST API** — standard endpoints, rate-limited by tier
- **Django signals** — `post_save` on `Law`/`LawVersion` triggers generic `dispatch_webhook_event()`

Consuming services configure themselves to connect to Tezca, not the other way around.

### Rate Limiting

`TieredRateThrottle` in `apps/api/tier_throttles.py`, sliding window via Redis cache:

| Tier | Aliases | Per Minute | Per Hour |
|------|---------|-----------|----------|
| anon | — | 10 | 100 |
| essentials | `free` | 30 | 500 |
| community | — | 60 | 2,000 |
| pro | `premium`, `enterprise` | 60 | 2,000 |
| madfam | `internal` | 200 | 50,000 |

### Tier-Based Access Control

5-tier hierarchy defined in `apps/api/tier_permissions.py` (single source of truth):

| Tier | Rank | Search page_size | Bulk/Webhooks | Premium Export |
|------|------|-----------------|---------------|----------------|
| anon | 0 | 25 | no | no |
| essentials | 1 | 25 | no | no |
| community | 2 | 100 | yes | no |
| pro | 3 | 100 | yes | yes |
| madfam | 4 | 100 | yes | yes |

- `RequireTier.of("community")` gates `bulk_articles` and `create_webhook`
- `check_feature(tier, "search_analytics")` gates analytics view
- Feature flags and limits defined in `apps/api/tiers.json`
- `normalize_tier()` handles legacy names: `free`→`essentials`, `premium`/`enterprise`→`pro`, `internal`→`madfam`

### Billing

- Checkout URL: `https://dhanam.madfam.io/checkout` (via `apps/web/lib/billing.ts`)
- Webhook: `POST /api/v1/billing/webhook/` — HMAC-SHA256 signed by Dhanam, upgrades/downgrades API key tiers
- Secret: `DHANAM_WEBHOOK_SECRET` env var

### Route Conventions

- **API endpoints are English:** `/api/v1/laws/`, `/api/v1/search/`, `/api/v1/categories/`, `/api/v1/coverage/`, `/api/v1/contributions/`, `/api/v1/judicial/`
- **Web routes are Spanish:** `/leyes/`, `/busqueda/`, `/comparar/`, `/categorias/`, `/estados/`, `/cobertura/`, `/contribuir/`, `/convocatoria/`, `/jurisprudencia/`, `/desarrolladores/`, `/grafo/`
- 301 redirects exist from old English web routes (`/laws/` -> `/leyes/`)

### Elasticsearch

- Singleton client in `apps/api/config.py` (`es_client`)
- Index name: `articles` (constant `INDEX_NAME`)
- ES 8.17, timeout 30s, 3 retries, 10 connections per node
- Always use `es_client` from config, never instantiate a new client

### Celery

- Broker and result backend: Redis
- Beat scheduler: `django_celery_beat.schedulers:DatabaseScheduler`
- Scheduled tasks defined in `apps/indigo/settings.py` (`CELERY_BEAT_SCHEDULE`)
- Worker concurrency: 4
- 12 scheduled tasks: health checks (daily/weekly), staleness detection, DOF daily, treaty/NOM/CONAMER/municipal scraping, coverage reports, parser pipeline (weekly)

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
- **`TierComparison`** — Feature comparison table across Essentials/Community/Pro tiers. Desktop table + mobile stacked cards. Use `compact` prop for inline usage.
- **`LinkifiedArticle`** — `crossRefsDisabled` defaults to `true`. Pass `crossRefsDisabled={false}` explicitly to enable per-article cross-reference fetching. Use the batch endpoint (`POST /api/v1/laws/{law_id}/articles/references/batch/`) to load refs for all articles in a single request instead of N+1 individual calls.

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
| `apps/api/constants.py` | KNOWN_STATES (32 states), DOMAIN_MAP (generic + SCIAN 2023-aligned) |
| `apps/api/management/commands/provision_api_key.py` | CLI API key provisioning |
| `apps/api/tier_permissions.py` | Single source of truth for tier naming, ranking, format access, rate limits |
| `apps/api/tiers.json` | Feature flags and limits per tier (loaded by tier_permissions) |
| `apps/api/tier_throttles.py` | Rate limiting by tier (imports from tier_permissions) |
| `apps/api/billing_views.py` | Dhanam billing webhook receiver (HMAC-verified tier upgrades) |
| `apps/api/storage.py` | StorageBackend (local + R2) |
| `apps/api/export_views.py` | PDF/TXT/LaTeX/DOCX/EPUB/JSON export |
| `apps/api/graph_views.py` | Law graph API (ego graph + global overview for Sigma.js) |
| `apps/api/export_throttles.py` | Export-specific rate limits by tier (imports from tier_permissions) |
| `apps/api/models.py` | Law, Article, ExportLog, AcquisitionLog, Contribution, JudicialRecord |
| `apps/indigo/settings.py` | Django settings, Celery Beat schedule |
| `apps/web/lib/config.ts` | API_BASE_URL, INTERNAL_API_URL |
| `apps/web/lib/auth-token.ts` | Shared Janua auth token retrieval utility |
| `apps/web/components/providers/AuthContext.tsx` | Janua JWT auth state |
| `apps/web/components/TierGate.tsx` | Tier-gating upgrade prompts (4 variants, i18n, countdown) |
| `apps/web/components/TierComparison.tsx` | Tier feature comparison table |
| `apps/web/contexts/LanguageContext.tsx` | i18n with LOCALE_MAP |
| `apps/web/lib/sentry.ts` | Sentry init + `captureError()` (conditional on `@sentry/nextjs`) |
| `apps/web/components/ErrorBoundary.tsx` | Class-based error boundary (wraps layout children), reports to Sentry |
| `apps/web/components/RouteError.tsx` | Shared i18n route error component (used by 11 route `error.tsx` files) |
| `apps/web/app/global-error.tsx` | Layout-level catch-all (raw styles, Sentry) |
| `apps/api/management/commands/spot_check.py` | Data integrity spot-check (samples laws, traces DB→file→ES→API) |
| `apps/parsers/error_tracker.py` | ErrorTracker + ErrorRecord for pipeline error logging |
| `apps/parsers/pipeline.py` | Ingestion pipeline (Download→Extract→Parse→Validate→Quality) with ErrorTracker |
| `packages/mcp-server/main.py` | MCP server entry point (FastMCP + uvicorn) |
| `packages/mcp-server/tools/` | 16 MCP tools proxying REST API |

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

6. **Black version:** Always use `poetry run black` (not system black) to match the version pinned in `poetry.lock` (24.x).

7. **Poetry lockfile:** Always run `poetry lock` after changing `pyproject.toml` deps before committing.

8. **ESLint JSX rule:** No JSX inside try/catch blocks. Build data in the try block, return JSX outside.

9. **Admin `'use client'`:** Only add the directive to admin components that actually use hooks or event handlers. Presentational components should be server components.

10. **Test mocks:** Admin tests mock `@tezca/ui` and `next/link` inline via `vi.mock()`. When adding fields to shared types, update these mocks.

11. **`@janua/*` transpiling:** `@janua/ui` and `@janua/nextjs` must be listed in `transpilePackages` in `next.config.ts`. Without this, Turbopack fails with "Unknown module type" on their TypeScript source.

12. **ES ICU plugin:** The default ES Docker image does not include `analysis-icu`. Use `asciifolding` (built-in) instead of `icu_folding` for accent normalization.

13. **`@types/react` lockfile dedup:** The monorepo can end up with multiple `@types/react` versions (e.g. 19.2.10 in workspaces, 19.2.14 at root), causing Radix component type errors (`Key` type mismatch). Fix by removing nested `node_modules/@types/react` entries from `package-lock.json` and running `npm install`.

14. **`Protect` component:** `@janua/nextjs` `Protect` uses `redirectTo` prop, not `redirectUrl`.

---

## CI/CD

- Python CI runs `poetry run black --check` and `poetry run pytest`
- Node CI runs `npm run lint:all` and `npm run build:all`
- Deploy workflows push digest commits that can race with subsequent pushes -- use `git pull --rebase` before pushing
- R2 storage tests use `pytest.mark.skipif(not _has_boto3)` -- they skip in CI where boto3 is not installed
- WeasyPrint and other optional deps are similarly skipped in CI
