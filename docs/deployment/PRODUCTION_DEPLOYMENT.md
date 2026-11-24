# Tezca Production Deployment

> **Running a command inside Tezca.** `enclii exec`, `enclii shell` and
> `enclii jobs run` do not exist. Enclii's path for a one-off command is
> `enclii jobs run-once` in the `tezca-api` image with
> `--network-identity service`, which copies onto the job pod the labels
> Tezca's NetworkPolicies select on, so it reaches Postgres, Redis and
> Elasticsearch as the service does. That path has not yet been run against
> Tezca (it was verified on another service on 2026-11-24). Until it has, the
> documented break-glass path remains the fallback, on an explicit operator
> request only: `ssh ssh.madfam.io`, then `sudo -n kubectl -n tezca exec` into
> the `tezca-api` or `tezca-worker` deployment (madfam-org/enclii#455). Blocks
> below marked "in the tezca-api image" show the command that runs inside the
> pod. The Enclii form, for one of them:

```bash
SERVICE_ID=$(enclii releases tezca-api --project tezca --limit 1 | awk '/^Resolved /{gsub(/[()]/, "", $NF); print $NF}')
JOB_ID=$(enclii jobs run-once --name tezca-check-deploy --command "sleep 20 && python manage.py check --deploy" --service-id "$SERVICE_ID" --project tezca --network-identity service | awk '/^  ID:/{print $2}')
enclii jobs get "$JOB_ID"
enclii jobs logs "$JOB_ID"
```

`enclii releases` prints the service id on its `Resolved` line, and
`enclii jobs run-once` prints the job id on its `ID:` line; the `awk` filters
read them. `sleep 20` covers a known start-up race (a new job pod can start
before its network rules apply). Read the output with `enclii jobs logs` once
`enclii jobs get` shows the job finished. Another in-pod command runs the same
way with its own `--name` and `--command`.

**Brand**: Tezca (tezca.mx)
**Org**: madfam-org
**K8s Namespace**: tezca
**Registry**: ghcr.io/madfam-org/tezca
**Last Updated**: 2026-11-24

---

## Deployment Progress

### Completed

| Phase | Scope | Status |
|-------|-------|--------|
| **1. Dockerfile Hardening** | Multi-stage builds, non-root users, HEALTHCHECK, .dockerignore | Done |
| **2. Django Production Hardening** | HSTS, secure cookies, SSL redirect, STATIC_ROOT, structured logging | Done |
| **3. Janua JWT Middleware** | RS256 JWKS validation, admin-only auth, public endpoints open | Done |
| **4. Janua Admin Integration** | JanuaProvider, middleware.ts, /sign-in page, UserButton | Done |
| **5. Enclii Service Specs** | enclii.yaml + 7 per-service specs | Done |
| **6. K8s Manifests** | 16 manifests: deployments, services, PVCs, HPA, kustomization | Done |
| **7. CI/CD Workflows** | 3 GitHub Actions (api, web, admin) with GHCR + digest tracking | Done |
| **8. Next.js Standalone** | `output: "standalone"` in both web and admin configs | Done |
| **9. Health Endpoints** | `GET /api/health` on web and admin apps | Done |
| **10. Python Deps** | PyJWT[crypto] + cryptography added and locked | Done |

### Remaining (Manual / Requires Credentials)

| # | Task | Owner | Requires | Notes |
|---|------|-------|----------|-------|
| **M1** | Install `@janua/nextjs` in admin | Dev | Private npm registry config | Package is on MADFAM private registry, not public npm. Configure `@janua:registry` in `.npmrc` |
| **M2** | Set GitHub secrets | Repo Admin | GitHub repo admin access | `MADFAM_BOT_PAT` (GHCR push), `ENCLII_CALLBACK_TOKEN` (lifecycle events) |
| **M3** | Create K8s `tezca-secrets` | DevOps | Enclii secret intake | See [Secrets Reference](#secrets-reference) below |
| **M4** | Register Janua OAuth client | DevOps | Janua admin API access | `client_id: tezca-admin`, redirect: `https://admin.tezca.mx/auth/callback`, scopes: `openid email profile` |
| **M5** | Configure Cloudflare DNS | DevOps | Cloudflare account | Zone: `tezca.mx`. Enclii auto-provisions CNAME records to `tunnel.enclii.dev` |
| **M6** | Add to ArgoCD root application | DevOps | Infra repo access | Add `tezca` to `infra/argocd/root-application.yaml`, source: `k8s/production/`, destination: `tezca` namespace |
| **M7** | Run initial database migration | — | Nothing manual | The `migrate` initContainer of `tezca-api` runs `python manage.py migrate --noinput` on every rollout (`k8s/production/tezca-api-deployment.yaml`) |
| **M8** | Collect static files | — | Nothing manual | The API image runs `python manage.py collectstatic --noinput` at build time (`apps/indigo/Dockerfile`) |
| **M9** | Build Elasticsearch indices | DevOps | Enclii CLI (see the note at the top) | In the tezca-api image: `python manage.py index_laws --all --create-indices` |
| **M10** | Smoke test all domains | QA | All above complete | See [Verification Checklist](#verification-checklist) |
| **M11** | Create `tezca-r2-credentials` K8s Secret | DevOps | R2 API token | See [R2 Credentials](#k8s-secret-tezca-r2-credentials) |
| **M12** | Create `tezca-sentry` K8s Secret | DevOps | Sentry DSN | See [Sentry Secret](#k8s-secret-tezca-sentry) |
| **M13** | Create `tezca-documents` R2 bucket | DevOps | Cloudflare dashboard | On existing CF R2 account (same as PG backups) |
| **M14** | Run R2 data migration | DevOps | enclii CLI + R2 bucket | `scripts/migrate_to_r2.py --dry-run` then without flag |

**Recommended execution order**: M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 → M9 → M10 → M11 → M12 → M13 → M14

---

## Service Topology

```
                 ┌──────────────────────────────────────────────────┐
                 │                  Cloudflare Tunnel                │
                 │    tezca.mx    api.tezca.mx    admin.tezca.mx   │
                 └───────┬──────────────┬───────────────┬──────────┘
                         │              │               │
                 ┌───────▼───┐  ┌───────▼───┐  ┌───────▼───┐
                 │ tezca-web │  │ tezca-api │  │tezca-admin│
                 │ :3000     │  │ :8000     │  │ :3001     │
                 │ 2-5 pods  │  │ 2-6 pods  │  │ 2 pods    │
                 └───────────┘  └─────┬─────┘  └───────────┘
                                      │
                     ┌────────────────┼────────────────┐
                     │                │                │
              ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
              │ tezca-redis │ │  tezca-es   │ │  MADFAM PG  │
              │ :6379       │ │ :9200       │ │  (shared)   │
              │ 5Gi PVC     │ │ 50Gi PVC    │ │  db: tezca  │
              └──────┬──────┘ └─────────────┘ └─────────────┘
                     │
              ┌──────▼──────┐ ┌─────────────┐
              │tezca-worker │ │ tezca-beat  │
              │ concurrency4│ │ singleton   │
              └─────────────┘ └─────────────┘
```

| Service | Image | Port | Replicas | Domain |
|---------|-------|------|----------|--------|
| tezca-api | ghcr.io/madfam-org/tezca/api | 8000 | 2-6 (HPA) | api.tezca.mx |
| tezca-web | ghcr.io/madfam-org/tezca/web | 3000 | 2-5 | tezca.mx, www.tezca.mx |
| tezca-admin | ghcr.io/madfam-org/tezca/admin | 3001 | 2 | admin.tezca.mx |
| tezca-worker | ghcr.io/madfam-org/tezca/api | — | 1 | — |
| tezca-beat | ghcr.io/madfam-org/tezca/api | — | 1 (singleton) | — |
| tezca-redis | redis:7-alpine | 6379 | 1 | — |
| tezca-es | elasticsearch:8.17.0 | 9200 | 1 | — |

PostgreSQL uses the shared MADFAM cluster (database: `tezca`).

---

## File Inventory

### Dockerfiles
| File | Purpose |
|------|---------|
| `apps/web/Dockerfile` | Next.js portal — 3-stage (deps→build→runtime), standalone, non-root |
| `apps/admin/Dockerfile` | Admin console — same pattern, port 3001 |
| `apps/indigo/Dockerfile` | Django API — 2-stage (builder→runtime), venv copy, gunicorn 4w/2t. The builder installs `-E production`, which includes WeasyPrint 70.0 for PDF export. The runtime installs Pango/Cairo/HarfBuzz (`libpango-1.0-0`, `libpangocairo-1.0-0`, `libcairo2`, …), which WeasyPrint needs at import time, plus tesseract-ocr (+ spa lang data) and poppler-utils for the OCR pipeline. |
| `packages/mcp-server/Dockerfile` | MCP server, for local runs and `docker compose` only. It installs from `uv.lock` (`uv sync --locked`) and starts with `uv run --no-sync`. No workflow builds or deploys this image; the package ships to PyPI on `mcp-v*` tags (`publish-mcp.yml`). |
| `.dockerignore` | Excludes data/, node_modules/, .git/, engines/, tests/, docs/ |

### Auth
| File | Purpose |
|------|---------|
| `apps/api/middleware/janua_auth.py` | DRF auth backend: RS256 JWT via Janua JWKS (cached, thread-safe) |
| `apps/api/urls.py` | Admin endpoints protected, public endpoints open, health unauthenticated |
| `apps/admin/middleware.ts` | Next.js middleware: all routes require login except /sign-in, /api/health |
| `apps/admin/app/sign-in/page.tsx` | Janua sign-in form |
| `apps/admin/app/layout.tsx` | JanuaProvider + UserButton in header |

### Django Production
| File | Purpose |
|------|---------|
| `apps/indigo/settings.py` | HSTS, secure cookies, SSL redirect, STATIC_ROOT, JANUA_BASE_URL, structured logging |

### Enclii
| File | Purpose |
|------|---------|
| `enclii.yaml` | Root onboarding spec (all 7 services + secrets) |
| `deployment/enclii/tezca-*.yaml` | 7 detailed per-service specs |

### Kubernetes
| File | Purpose |
|------|---------|
| `k8s/production/kustomization.yaml` | ArgoCD entry point, image tag/digest overrides |
| `k8s/production/namespace.yaml` | `tezca` namespace |
| `k8s/production/tezca-*-deployment.yaml` | 7 deployments (API has HPA, beat uses Recreate strategy) |
| `k8s/production/tezca-*-service.yaml` | 5 ClusterIP services (api, web, admin, redis, es) |
| `k8s/production/tezca-api-servicemonitor.yaml` | Prometheus scrape of the API's private metrics port 9464 |
| `k8s/production/tezca-*-pvc.yaml` | 2 PVCs (redis 5Gi, es 50Gi) |

### CI/CD
| File | Trigger Paths |
|------|---------------|
| `.github/workflows/deploy-api.yml` | `apps/api/**`, `apps/indigo/**`, `apps/parsers/**`, `apps/scraper/**`, `pyproject.toml`, `poetry.lock` (the worker and beat Deployments run the same image) |
| `.github/workflows/deploy-web.yml` | `apps/web/**`, `packages/ui/**`, `packages/lib/**` |
| `.github/workflows/deploy-admin.yml` | `apps/admin/**`, `packages/ui/**`, `packages/lib/**` |

**Not a trigger for web or admin:** the root `package-lock.json`. A change that
touches only the root lockfile (a transitive npm security fix, for example) merges
without rebuilding either frontend image. Ship it by dispatching `deploy-web.yml`
and `deploy-admin.yml` with `deploy_ack=production` and a `reason` of at least
12 characters — the command is in [`SECURITY.md`](../../SECURITY.md#security-baseline-2026-09-30).

---

## Secrets Reference

Secret values are never written in a doc, a commit, a PR or chat, and never
typed as a command-line literal. They go through the Enclii secret intake:
`enclii secrets intake targets` lists the registered targets, and
`enclii secrets intake submit` for the Tezca target writes the values with a
masked prompt (it requires `--reason`; `--generate` with a key name, where the
target allows it, has Enclii mint a random value such as `DJANGO_SECRET_KEY`
itself, so nobody sees it). If no Tezca target is listed, there is no intake
path for these Secrets yet: no Enclii adapter: this is an adapter gap, to be
recorded rather than worked around with a literal.

### K8s Secret: `tezca-secrets`

| Key | Value |
|-----|-------|
| `DJANGO_SECRET_KEY` | random, at least 50 bytes (generate it) |
| `DB_USER` | `tezca` |
| `DB_PASSWORD` | random (generate it) |
| `DB_HOST` | the shared cluster PostgreSQL endpoint (see [`CNPG_MIGRATION_PREP_2026-04-27.md`](../strategy/CNPG_MIGRATION_PREP_2026-04-27.md) for the planned cutover) |
| `JANUA_API_KEY`, `JANUA_PUBLISHABLE_KEY`, `JANUA_SECRET_KEY` | from Janua |

### K8s Secret: `tezca-r2-credentials`

| Key | Value |
|-----|-------|
| `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | an R2 API token on the existing Cloudflare account |
| `R2_ENDPOINT_URL` | the account's R2 S3 endpoint, `https://` + account id + `.r2.cloudflarestorage.com` |
| `R2_BUCKET_NAME` | `tezca-documents` |
| `STORAGE_BACKEND` | `r2` |

### K8s Secret: `tezca-sentry`

| Key | Value |
|-----|-------|
| `SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN` | the DSN of the Tezca Sentry project |
| `SENTRY_ENVIRONMENT` | `production` |

### GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `MADFAM_BOT_PAT` | GHCR image push + kustomization digest commit |
| `ENCLII_CALLBACK_TOKEN` | CI lifecycle event reporting to enclii API |
| `NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY` | Admin Docker build arg for Janua client-side auth |

---

## CI/CD Flow

```
Push to main (matching paths)
  │
  ├─ Build Docker image (multi-stage)
  ├─ Push to ghcr.io/madfam-org/tezca-{service}
  ├─ Update k8s/production/kustomization.yaml with image digest
  ├─ Commit + push digest (retry loop for concurrency)
  └─ Report lifecycle event to enclii API
       │
       └─ ArgoCD detects kustomization change
            │
            └─ Syncs K8s resources → rolling update
```

**Loop prevention**: All deploy workflows exclude `!k8s/production/kustomization.yaml` in their `paths:` filter.

**Digest concurrency**: Commit step has a 5-retry loop with `git pull --rebase` to handle simultaneous pushes from multiple workflows.

---

## Verification Checklist

After completing all manual steps (M1-M9), verify:

| # | Check | Command / URL | Expected |
|---|-------|---------------|----------|
| 1 | Docker builds | `docker build -f apps/web/Dockerfile .` | Success for all 3 Dockerfiles |
| 2 | Web health | `curl https://tezca.mx/api/health` | `{"status":"ok"}` |
| 3 | API health | `curl https://api.tezca.mx/api/v1/admin/health/` | `{"status":"healthy","database":"connected"}` |
| 4 | Admin health | `curl https://admin.tezca.mx/api/health` | `{"status":"ok"}` |
| 5 | Public API (no auth) | `curl https://api.tezca.mx/api/v1/laws/` | 200 with law list |
| 6 | Admin API (no auth) | `curl https://api.tezca.mx/api/v1/admin/metrics/` | 401 Unauthorized |
| 7 | Admin API (valid JWT) | `curl -H "Authorization: Bearer <token>" .../admin/metrics/` | 200 with metrics |
| 8 | Admin login flow | Navigate to `admin.tezca.mx` | Redirect to /sign-in → login → dashboard |
| 9 | Django security | In the tezca-api image: `python manage.py check --deploy` (the Enclii form is the example at the top) | No critical warnings |
| 10 | CI/CD pipeline | Push to `main` touching `apps/api/` | Image built → digest committed → ArgoCD syncs |
| 11 | Metrics not public | `curl -s -o /dev/null -w '%{http_code}' https://api.tezca.mx/metrics` (and `/metrics/`) | `404` |
| 12 | Metrics listener up | `ENCLII_PROJECT=tezca enclii logs tezca-api --env production --since 30m \| grep "Prometheus metrics"` | One `Prometheus metrics (in-cluster only) on :9464/metrics` line per pod |
| 13 | PDF export renders | `curl -H "Authorization: Bearer <free-account token>" -o law.pdf -w '%{http_code} %{content_type}' https://api.tezca.mx/api/v1/laws/<law_id>/export/pdf/` | `200 application/pdf`, and `law.pdf` opens. A 501 means WeasyPrint is missing from the image; a 500 is a render failure (see Gotcha 13) |

---

## Gotchas

1. **`provenance: false` + `sbom: false`** in all CI build-push-action steps — prevents ArgoCD SHA confusion with attestation manifests
2. **Celery Beat singleton**: `replicas: 1`, Recreate strategy — multiple instances cause duplicate scheduling
3. **Monorepo build context**: All Dockerfiles use project root (`.`) as context since `packages/ui` and `packages/lib` are shared
4. **ES memory_lock**: Requires init container setting `vm.max_map_count=262144` on the node (privileged)
5. **Health check unauthenticated**: `/api/v1/admin/health/` stays open — K8s liveness probes need direct access
6. **JanuaProvider placement**: Must wrap inside `<html><body>` but before all other providers
7. **Internal DNS pattern**: `{service}.tezca.svc.cluster.local:{port}` — used in env vars for inter-service communication. In-cluster callers speak plain HTTP with no `X-Forwarded-Proto`, so `SECURE_SSL_REDIRECT` would answer them 301 → `https://…`; `/health` and every `/api/` path are therefore exempt (`PRODUCTION_SECURE_REDIRECT_EXEMPT` in `apps/indigo/settings.py`, pinned by `tests/test_production_ssl_redirect.py`). Public plain-HTTP visitors never reach the origin: Cloudflare redirects them at the edge. Every other path (e.g. `/admin/`) still redirects
8. **ENCLII_PORT**: Enclii may set this env var — apps should respect it if present
9. **R2 storage backend**: `STORAGE_BACKEND=r2` must be set in production K8s env; defaults to `local` for dev. boto3 is an optional dep — only imported when R2 is active
10. **Sentry optional**: Both `sentry-sdk` (API) and `@sentry/nextjs` (web) are optional. Code gracefully degrades when not installed
11. **Prometheus metrics are private**: the API serves `http_requests_total` and `http_request_duration_seconds` (by method, route pattern and status) plus `process_*`/`python_info` on port 9464, `GET /metrics` only, from the gunicorn master (`apps/indigo/gunicorn.conf.py`, `apps/api/metrics_server.py`). Workers write to `PROMETHEUS_MULTIPROC_DIR` and the master serves the sum (prometheus_client multiprocess mode). The public port 8000 has no metrics route; never add one to "fix" a scrape. Scraped through the `tezca-api` Service's `prometheus.io/*` annotations and `ServiceMonitor/tezca-api-monitor` (port `metrics`), admitted by NetworkPolicy `allow-monitoring-ingress` (monitoring namespace, TCP 9464 only). A bad `METRICS_PORT`, or 9464 already bound, makes gunicorn exit at boot
12. **Root lockfile changes do not redeploy the frontends**: see the note under [CI/CD](#cicd). Dispatch `deploy-web.yml` / `deploy-admin.yml` by hand after merging one.
13. **WeasyPrint and pydyf must move together**: WeasyPrint 62.3 with the locked pydyf 0.12.1 raised `AttributeError: 'super' object has no attribute 'transform'` inside `write_pdf()`, so `GET /api/v1/laws/<id>/export/pdf/` was most likely failing with a 500 on every image built from that lock. #263 moved WeasyPrint to 70.0 (`^70.0`), which renders correctly with pydyf 0.12.1 and also clears three advisories (see [`SECURITY.md`](../../SECURITY.md#security-baseline-2026-09-30)). `deploy-api.yml` rebuilt the API image and pinned digest `b46c282a` on 2026-10-01. CI does not install the `pdf`/`export`/`production` extras, so it cannot catch a broken WeasyPrint/pydyf pairing. After any change to either package, run the manual render check in [`docs/guides/TESTING_STRATEGY.md`](../guides/TESTING_STRATEGY.md#pdf-export-rendering-manual-check), then check 13 above once the image is deployed.
14. **The Janua SDK leaks one interval per server render (2026-11)**: `@janua/typescript-sdk` 0.1.x starts a never-cleared `setInterval(…, 60 000)` in the `JanuaClient` constructor, and `<JanuaProvider>` builds a client on every server render, so each server-rendered page view pinned its request (~110 KB) for good. tezca-web OOM-restarted every 20–46 h (`Ineffective mark-compacts near heap limit`, exit 139). The app-wide providers (`apps/web/lib/janua.tsx`, `apps/admin/lib/auth.tsx`) now build the server-side client with `autoRefreshTokens: false` (`lib/janua-config.ts` in each app); the browser config is unchanged. Never render `@janua/nextjs`'s `JanuaProvider` directly from a layout: import the app's wrapper. Regression tests: `__tests__/lib/janua-provider-ssr.test.tsx` in both apps (20 server renders, 0 intervals). The SDK fix is `@janua/typescript-sdk` 0.1.5; after the bump the characterisation test in `__tests__/lib/janua-config.test.ts` fails, and the guard can go. Defence in depth: `NODE_OPTIONS=--max-old-space-size` at 62.5% of the memory limit (web 320 of 512Mi, admin 160 of 256Mi), pinned by `tests/test_web_runtime_manifests.py` together with probe timeouts ≥ 3 s and the `deployment/enclii/` mirrors. Read-only check after a rollout: `kubectl get pods -n tezca -l app.kubernetes.io/name=tezca-web` (restart count flat) and `kubectl top pods -n tezca` (memory plateaus instead of climbing).

---

**Document Version**: 1.1
**Created**: 2026-02-06
**Updated**: 2026-11-24 (in-pod commands: `enclii exec` does not exist; Enclii one-off job form; secrets via the intake). Earlier: 2026-11-09 (Gotcha 14: Janua SDK SSR interval leak, heap caps); 2026-10-01 (WeasyPrint 70 and the PDF export fix; MCP server image scope); 2026-09-30 (deploy trigger table; root-lockfile gap)
