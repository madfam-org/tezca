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

---

## Key Commands

### Testing

```bash
# Backend (pytest + django, 889 tests)
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

Admin endpoints use `_protected()` in `apps/api/urls.py`, which sets `JanuaJWTAuthentication` + `IsAuthenticated` + `IsTezcaAdmin` directly on the view class. `IsTezcaAdmin` (in `apps/api/middleware/admin_permission.py`) checks JWT `role == "admin"` claim OR user ID in `TEZCA_ADMIN_USER_IDS` env var.

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
- `RequireFeature.of("graph_api")` gates graph endpoints (institutional+ only)
- `RequireTier.of("academic")` for rank-based gating (monotonic features)
- `check_feature(tier, "search_analytics")` gates analytics view
- Feature flags and limits defined in `apps/api/tiers.json`
- `normalize_tier()` handles legacy names: `free`→`essentials`, `premium`/`enterprise`/`pro`→`academic`, `internal`→`madfam`
- `get_effective_tier()` caps tier at academic in self-hosted mode (`TEZCA_DEPLOYMENT=self-hosted`)

### Billing

- Checkout URL: `settings.DHANAM_CHECKOUT_URL` (env `DHANAM_CHECKOUT_URL`, default `https://dhanam.madfam.io/checkout`)
- Webhook: `POST /api/v1/billing/webhook/` — HMAC-SHA256 signed by Dhanam, upgrades/downgrades API key tiers
- Secret: `DHANAM_WEBHOOK_SECRET` env var
- Plan mappings: `tezca_community`, `tezca_essentials`, `tezca_academic`, `tezca_institutional`, `tezca_madfam` → corresponding tiers (legacy `tezca_pro`→`academic`)
- Downgrade fallback: `community` (free tier for authenticated users)

### Route Conventions

- **API endpoints are English:** `/api/v1/laws/`, `/api/v1/search/`, `/api/v1/categories/`, `/api/v1/coverage/`, `/api/v1/contributions/`, `/api/v1/judicial/`
- **Web routes are Spanish:** `/leyes/`, `/busqueda/`, `/comparar/`, `/categorias/`, `/estados/`, `/cobertura/`, `/contribuir/`, `/convocatoria/`, `/jurisprudencia/`, `/desarrolladores/`, `/grafo/`
- 301 redirects exist from old English web routes (`/laws/` -> `/leyes/`)

### Elasticsearch

- Singleton client in `apps/api/config.py` (`es_client`)
- Index name: `articles` (constant `INDEX_NAME`), also aliased via `INDEX_ALIAS`
- ES 8.17, timeout 30s, 3 retries, 10 connections per node
- Always use `es_client` from config, never instantiate a new client
- **Alias strategy**: `articles` is an alias pointing to a versioned concrete index (`articles_v{timestamp}`). Zero-downtime reindex via `index_laws --reindex` creates a new versioned index, indexes into it, then atomically swaps the alias. One-time migration from concrete to alias via `manage_es_alias --migrate` or `index_laws --migrate-alias`
- **Alias management**: `python manage.py manage_es_alias --status|--migrate|--rollback INDEX|--cleanup`

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
- **`TierComparison`** — Feature comparison table across Community/Essentials/Academic/Institutional tiers. Desktop table + mobile stacked cards. Use `compact` prop for inline usage.
- **`LinkifiedArticle`** — Cross-references are loaded in batch by `ArticleViewer` via `useBatchCrossRefs` hook (eliminates N+1). Individual articles receive refs via `preloadedRefs` prop. The `crossRefsDisabled` prop defaults to `false` when batch refs are available. Use the batch endpoint (`POST /api/v1/laws/{law_id}/articles/references/batch/`) for custom integrations.

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
| `apps/api/middleware/admin_permission.py` | `IsTezcaAdmin` permission (JWT role or user ID allow-list) |
| `apps/api/tier_permissions.py` | Single source of truth for tier naming, ranking, format access, rate limits. Re-exports `RequireTier`, `RequireFeature`, `check_feature`, `get_effective_tier` from middleware |
| `apps/api/middleware/tier_permissions.py` | `RequireTier` (rank-based), `RequireFeature` (feature-flag-based), `get_effective_tier()` (self-hosted cap) |
| `apps/api/tiers.json` | Feature flags and limits per tier (loaded by tier_permissions) |
| `apps/api/tier_throttles.py` | Rate limiting by tier (imports from tier_permissions) |
| `apps/api/billing_views.py` | Dhanam billing webhook receiver (HMAC-verified tier upgrades) |
| `apps/api/utils/responses.py` | `error_response()` helper — standard `{"error": ...}` format |
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
| `apps/api/es_index_manager.py` | ES alias management (zero-downtime reindex) |
| `apps/api/management/commands/manage_es_alias.py` | CLI for ES alias status/migrate/rollback/cleanup |
| `apps/web/hooks/useBatchCrossRefs.ts` | Batch cross-reference fetching hook (eliminates N+1) |

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

15. **`_protected()` sets class attrs directly:** DRF's `authentication_classes`/`permission_classes` decorators from `rest_framework.decorators` set attributes on the function, not on the `WrappedAPIView` class, so they have no effect when applied after `@api_view`. `_protected()` in `urls.py` works around this by setting `view_func.cls.authentication_classes` and `view_func.cls.permission_classes` directly.

16. **Admin endpoint test pattern:** Tests for `_protected()` endpoints must patch both `JanuaJWTAuthentication.authenticate` (returns `(admin_user, "fake-token")`) and `IsTezcaAdmin.has_permission` (returns `True`). Patching `CombinedAuthentication.authenticate` has no effect on admin endpoints. See `_start_admin_patches()` in `tests/api/test_admin_views.py` for the canonical pattern.

17. **`APIKey.rate_limit_per_hour` is capped:** Custom per-key rate limit overrides are capped at 100,000/hour in `TieredRateThrottle._get_limits()`. Model validators enforce 1–100,000 range.

---

## CI/CD

- Python CI runs `poetry run black --check` and `poetry run pytest` (matrix: Python 3.11 + 3.12)
- Node CI runs `npm run lint:all` and `npm run build:all` (matrix: Node 20 + 22)
- E2E tests run against `docker-compose.e2e.yml` stack (blocking gate, Playwright with 2 CI retries)
- Security audits are blocking: `pip-audit` (Python) and `npm audit --audit-level=high` (Node). Use `--ignore-vuln PYSEC-YYYY-NNNNN` in CI to allowlist triaged CVEs
- CodeQL/SAST runs on push/PR to main and weekly (Monday 6am UTC) for Python + JavaScript/TypeScript
- MCP server tests run in CI via `uv sync && uv run pytest`
- MCP server publishes to PyPI on `mcp-v*` tags via OIDC trusted publisher
- Deploy workflows push digest commits that can race with subsequent pushes -- use `git pull --rebase` before pushing
- R2 storage tests use `pytest.mark.skipif(not _has_boto3)` -- they skip in CI where boto3 is not installed
- WeasyPrint and other optional deps are similarly skipped in CI
- Docker Compose services have resource limits (cpu/memory) to prevent runaway containers
