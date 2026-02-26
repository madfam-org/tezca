# Tezca Production Deployment

**Brand**: Tezca (tezca.mx)
**Org**: madfam-org
**K8s Namespace**: tezca
**Registry**: ghcr.io/madfam-org/tezca
**Last Updated**: 2026-02-06

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
| **M3** | Create K8s `tezca-secrets` | DevOps | enclii CLI + secret values | See [Secrets Reference](#secrets-reference) below |
| **M4** | Register Janua OAuth client | DevOps | Janua admin API access | `client_id: tezca-admin`, redirect: `https://admin.tezca.mx/auth/callback`, scopes: `openid email profile` |
| **M5** | Configure Cloudflare DNS | DevOps | Cloudflare account | Zone: `tezca.mx`. Enclii auto-provisions CNAME records to `tunnel.enclii.dev` |
| **M6** | Add to ArgoCD root application | DevOps | Infra repo access | Add `tezca` to `infra/argocd/root-application.yaml`, source: `k8s/production/`, destination: `tezca` namespace |
| **M7** | Run initial database migration | DevOps | enclii CLI, cluster access | `enclii exec tezca-api -- python apps/manage.py migrate` |
| **M8** | Collect static files | DevOps | enclii CLI | `enclii exec tezca-api -- python apps/manage.py collectstatic --noinput` |
| **M9** | Build Elasticsearch indices | DevOps | enclii CLI | `enclii exec tezca-api -- python apps/manage.py index_laws --all --create-indices` |
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
| tezca-es | elasticsearch:7.17.9 | 9200 | 1 | — |

PostgreSQL uses the shared MADFAM cluster (database: `tezca`).

---

## File Inventory

### Dockerfiles
| File | Purpose |
|------|---------|
| `apps/web/Dockerfile` | Next.js portal — 3-stage (deps→build→runtime), standalone, non-root |
| `apps/admin/Dockerfile` | Admin console — same pattern, port 3001 |
| `apps/indigo/Dockerfile` | Django API — 2-stage (builder→runtime), venv copy, gunicorn 4w/2t. Runtime includes tesseract-ocr (+ spa lang data) and poppler-utils for OCR pipeline. |
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
| `k8s/production/tezca-*-pvc.yaml` | 2 PVCs (redis 5Gi, es 50Gi) |

### CI/CD
| File | Trigger Paths |
|------|---------------|
| `.github/workflows/deploy-api.yml` | `apps/api/**`, `apps/indigo/**`, `apps/parsers/**`, `apps/scraper/**` |
| `.github/workflows/deploy-web.yml` | `apps/web/**`, `packages/ui/**`, `packages/lib/**` |
| `.github/workflows/deploy-admin.yml` | `apps/admin/**`, `packages/ui/**`, `packages/lib/**` |

---

## Secrets Reference

### K8s Secret: `tezca-secrets`

```bash
enclii secrets set DJANGO_SECRET_KEY "$(openssl rand -base64 50)" --env production
enclii secrets set DB_USER "tezca" --env production
enclii secrets set DB_PASSWORD "$(openssl rand -base64 32)" --env production
enclii secrets set DB_HOST "<shared-cluster-endpoint>" --env production
enclii secrets set JANUA_API_KEY "sk_live_..." --env production
enclii secrets set JANUA_PUBLISHABLE_KEY "pk_live_..." --env production
enclii secrets set JANUA_SECRET_KEY "sk_live_..." --env production
```

### K8s Secret: `tezca-r2-credentials`

```bash
enclii secrets set R2_ACCESS_KEY_ID "<from-existing-cf-account>" --env production
enclii secrets set R2_SECRET_ACCESS_KEY "<from-existing-cf-account>" --env production
enclii secrets set R2_ENDPOINT_URL "https://<account_id>.r2.cloudflarestorage.com" --env production
enclii secrets set R2_BUCKET_NAME "tezca-documents" --env production
enclii secrets set STORAGE_BACKEND "r2" --env production
```

### K8s Secret: `tezca-sentry`

```bash
enclii secrets set SENTRY_DSN "https://<key>@o<org>.ingest.sentry.io/<proj>" --env production
enclii secrets set SENTRY_ENVIRONMENT "production" --env production
enclii secrets set NEXT_PUBLIC_SENTRY_DSN "https://<key>@o<org>.ingest.sentry.io/<proj>" --env production
```

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
  ├─ Push to ghcr.io/madfam-org/tezca/{service}
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
| 9 | Django security | `enclii exec tezca-api -- python apps/manage.py check --deploy` | No critical warnings |
| 10 | CI/CD pipeline | Push to `main` touching `apps/api/` | Image built → digest committed → ArgoCD syncs |

---

## Gotchas

1. **`provenance: false` + `sbom: false`** in all CI build-push-action steps — prevents ArgoCD SHA confusion with attestation manifests
2. **Celery Beat singleton**: `replicas: 1`, Recreate strategy — multiple instances cause duplicate scheduling
3. **Monorepo build context**: All Dockerfiles use project root (`.`) as context since `packages/ui` and `packages/lib` are shared
4. **ES memory_lock**: Requires init container setting `vm.max_map_count=262144` on the node (privileged)
5. **Health check unauthenticated**: `/api/v1/admin/health/` stays open — K8s liveness probes need direct access
6. **JanuaProvider placement**: Must wrap inside `<html><body>` but before all other providers
7. **Internal DNS pattern**: `{service}.tezca.svc.cluster.local:{port}` — used in env vars for inter-service communication
8. **ENCLII_PORT**: Enclii may set this env var — apps should respect it if present
9. **R2 storage backend**: `STORAGE_BACKEND=r2` must be set in production K8s env; defaults to `local` for dev. boto3 is an optional dep — only imported when R2 is active
10. **Sentry optional**: Both `sentry-sdk` (API) and `@sentry/nextjs` (web) are optional. Code gracefully degrades when not installed

---

**Document Version**: 1.1
**Created**: 2026-02-06
**Updated**: 2026-02-07 (R2 storage, Sentry, ES resilience)
