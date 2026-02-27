# Admin Console

The administrative dashboard for operating the Tezca platform (law ingestion, monitoring, coverage tracking).

## Features
- **Ingestion Control**: Trigger new ingestion runs (All Laws or High Priority), view real-time job status.
- **System Metrics**: Law counts by tier and law_type, coverage percentages, article counts.
- **DataOps Dashboard**: Coverage by tier with progress bars, state coverage table with quality indicators (Buena/Media/Baja), gap summary, health source grid.
- **Expansion Roadmap**: Phase tracking with status updates, next priorities.
- **Settings**: System configuration, environment info, Elasticsearch status.
- **Job History**: Real job history from AcquisitionLog (last 20 runs).
- **Authentication**: Janua SSO (hardcoded SSO button + email/password fallback), dev-mode bypass when unconfigured.

## Pages

| Route | Description |
|-------|-------------|
| `/dashboard` | Main dashboard with navigation to all sections |
| `/dashboard/ingestion` | Ingestion job monitoring and triggers |
| `/dashboard/metrics` | System metrics and jurisdiction breakdown |
| `/dashboard/dataops` | Coverage dashboard, state table, gaps, health |
| `/dashboard/roadmap` | Expansion roadmap with phase tracking |
| `/dashboard/settings` | System configuration and health |
| `/sign-in` | Janua SSO button + email/password fallback (dev bypass when unconfigured) |

## Auth Architecture

Authentication uses `@janua/nextjs` with server-side OIDC and a module-level token injection pattern:

- **SSO Flow** (`app/api/auth/sso/route.ts`): Initiates OIDC Authorization Code flow — generates state, stores in cookie, redirects to `auth.madfam.io/api/v1/oauth/authorize`.
- **Callback** (`app/api/auth/callback/route.ts`): Exchanges authorization code for tokens server-side, creates `janua-session` cookie (HS256 JWT), sets short-lived `janua-sso-tokens` bridge cookie for client SDK hydration, redirects to `/`.
- **`AdminAuthBridge`** (`lib/auth.tsx`): Wraps the app in `layout.tsx`. On mount, reads the `janua-sso-tokens` bridge cookie to hydrate SDK localStorage, then wires `client.getAccessToken()` into the API client via `setTokenSource()`.
- **`setTokenSource()`** (`lib/api.ts`): Module-level setter that injects Bearer tokens into all API requests. Includes 401 retry (re-fetches token in case the SDK auto-refreshed).
- **Middleware** (`middleware.ts`): When `JANUA_SECRET_KEY` is set, protects all routes except `/sign-in`, `/api/health`, and `/api/auth/*`. When absent, all routes are open (dev mode).
- **`useAdminAuth()`** (`lib/auth.tsx`): Convenience hook returning `{ isAuthenticated, isLoading, user, signOut }`.

### Env Vars

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_JANUA_BASE_URL` | Janua server URL (e.g. `https://auth.madfam.io`) |
| `NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY` | OAuth client ID (`jnc_...`) |
| `JANUA_SECRET_KEY` | OAuth client secret (`jns_...`) for session cookie verification |

When none are set, the admin panel runs in open dev mode with no auth.

## Tech Stack
- **Framework**: Next.js 16 (App Router)
- **UI**: React 19, Tailwind CSS 4, @tezca/ui (Shadcn)
- **Auth**: @janua/nextjs (optional, open dev mode when unconfigured)
- **State**: React Hooks for polling and data fetching
- **Testing**: Vitest + @testing-library/react (10 test files, 72 tests)

## Development

Start the development server from the root of the monorepo:

```bash
npm run dev --workspace=apps/admin
```

The console will be available at [http://localhost:3001](http://localhost:3001).

## Testing

```bash
cd apps/admin && npx vitest run
```
