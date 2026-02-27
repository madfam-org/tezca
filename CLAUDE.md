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

**License:** AGPL-3.0

---

## Dev Setup

### Prerequisites

- Python 3.11+, Poetry
- Node 20+, npm (workspaces)
- Docker and Docker Compose

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
# Backend (pytest + django)
poetry run pytest tests/ -v
poetry run pytest tests/parsers/test_parser_v2.py    # parser tests (100 tests)

# Web (vitest, 193 tests across 29 files)
cd apps/web && npx vitest run

# Admin (vitest, 51 tests across 8 files)
cd apps/admin && npx vitest run

# E2E
cd apps/web && npx playwright test
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

### Rate Limiting

`TieredRateThrottle` in `apps/api/tier_throttles.py`, sliding window via Redis cache:

| Tier | Per Minute | Per Hour |
|------|-----------|----------|
| anon | 10 | 100 |
| free | 30 | 500 |
| pro | 60 | 2,000 |
| enterprise | 120 | 10,000 |
| internal | 200 | 50,000 |

### Route Conventions

- **API endpoints are English:** `/api/v1/laws/`, `/api/v1/search/`, `/api/v1/categories/`
- **Web routes are Spanish:** `/leyes/`, `/busqueda/`, `/comparar/`, `/categorias/`, `/estados/`
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

### Storage

- `apps/api/storage.py` -- `StorageBackend` abstraction (local filesystem or Cloudflare R2)
- Controlled by `STORAGE_BACKEND` env var (`local` or `r2`)
- boto3 is an optional dependency (`poetry install -E r2`)
- `apps/api/utils/paths.py` -- `read_data_content()`, `data_exists()`, `read_metadata_json()` provide R2 fallback for all data reads
- R2 fallback pattern: try local filesystem first → fall back to R2 via `read_data_content()`. Used by:
  - `law_views.py::_load_universe_registry()` — coverage stats (TTL-cached 5 min)
  - All ingestion management commands (`index_laws`, `ingest_state_laws`, etc.)
  - **Not yet**: `coverage_dashboard.py` — still uses local-only `_load_json()`

---

## Design Tokens and Conventions

### UI Components

All UI primitives come from `@tezca/ui` (Card, Badge, Button, etc.). Import from `@tezca/ui`, not from raw radix or shadcn directly.

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
| `apps/api/constants.py` | KNOWN_STATES (32 states), DOMAIN_MAP |
| `apps/api/tier_throttles.py` | Rate limiting by tier |
| `apps/api/storage.py` | StorageBackend (local + R2) |
| `apps/api/export_views.py` | PDF/TXT/LaTeX/DOCX/EPUB/JSON export |
| `apps/api/export_throttles.py` | Export-specific rate limits by tier |
| `apps/api/models.py` | Law, Article, ExportLog, AcquisitionLog |
| `apps/indigo/settings.py` | Django settings, Celery Beat schedule |
| `apps/web/lib/config.ts` | API_BASE_URL, INTERNAL_API_URL |
| `apps/web/components/providers/AuthContext.tsx` | Janua JWT auth state |
| `apps/web/contexts/LanguageContext.tsx` | i18n with LOCALE_MAP |

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

---

## CI/CD

- Python CI runs `poetry run black --check` and `poetry run pytest`
- Node CI runs `npm run lint:all` and `npm run build:all`
- Deploy workflows push digest commits that can race with subsequent pushes -- use `git pull --rebase` before pushing
- R2 storage tests use `pytest.mark.skipif(not _has_boto3)` -- they skip in CI where boto3 is not installed
- WeasyPrint and other optional deps are similarly skipped in CI
