# Tezca Production Audit — Enclii Agent Prompt

## Context

Tezca (tezca.mx) is a Mexican legal search platform deployed on Kubernetes via Enclii. The codebase lives at `github.com/madfam-org/tezca`. We've completed a major data migration but several production issues need investigation and resolution.

---

## Current State of Production

### What's Working
- **PostgreSQL**: 30,496 laws ingested (486 federal, 29,802 state, 208 municipal)
- **API** (`api.tezca.mx`): Responding 200 on `/api/v1/stats/`, `/api/v1/search/`, `/api/v1/laws/`
- **Web frontend** (`tezca.mx`): All pages returning 200 (homepage, /leyes, /busqueda, /categorias, /estados)
- **Admin** (`admin.tezca.mx`): Running (2 replicas)
- **Redis**: Running, healthy
- **Elasticsearch**: Running, 195MB used of 20Gi PVC, has ~168K articles (partial index)
- **R2 Storage**: ~80% of 91,473 files uploaded (ongoing, will complete independently). Bucket: `tezca-documents`

### What's Broken

#### 1. CRITICAL: Beat and Worker pods in CrashLoopBackOff
Both `tezca-beat` and `tezca-worker` (new revision) are crash-looping with:
```
OSError: cannot load library 'gobject-2.0-0': gobject-2.0-0: cannot open shared object file: No such file or directory.
```
**Root cause**: The Dockerfile was updated to `poetry install -E production` which pulls in `weasyprint` (PDF export). WeasyPrint requires system-level libraries (`gobject-2.0`, `pango`, `cairo`) that are NOT installed in the Docker image's runtime stage. The runtime stage only has: `libpq5 libxml2 libxslt1.1 libgmp10 wget`.

**Fix needed**: Either:
- (A) Add WeasyPrint's system dependencies to the Dockerfile runtime stage: `libglib2.0-0 libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info`
- (B) Or make WeasyPrint a lazy/optional import so the worker/beat don't crash on startup (it's only needed for PDF export endpoints, not for Celery tasks)

Option (A) is the straightforward fix. The Dockerfile at `apps/indigo/Dockerfile` line 49-55 needs the additional apt packages in the runtime stage.

#### 2. IMPORTANT: Elasticsearch indexing incomplete — OOM killed
The ES indexing command was OOM-killed (exit code 137) after processing 1,650/30,496 laws (168,656 articles). The API pod has a 2Gi memory limit. The command `python manage.py index_laws --all --batch-size 500` accumulates too much in memory.

**What needs to happen**: Resume ES indexing with a smaller batch size (`--batch-size 50` or `--batch-size 100`). The command is:
```bash
PYTHONPATH=/tmp/pylibs python /tmp/run_ingest.py index_laws --all --create-indices --batch-size 50
```

However, since pods were restarted, the temporary files (`/tmp/pylibs` with boto3, `/tmp/run_ingest.py` monkeypatch) are gone. Two options:
- (A) Rebuild and deploy the Docker image with the Dockerfile fix (which includes boto3 via `-E production`), then run `python manage.py index_laws --all --batch-size 50` directly
- (B) Reinstall boto3 manually (`pip install --target /tmp/pylibs boto3`) and recreate the monkeypatch wrapper

Option (A) is strongly preferred — it's a permanent fix.

**Note**: The `index_laws` command should handle re-indexing gracefully (it overwrites existing docs by ID), so running it again from the start is safe, just slower.

**Target**: ~30,496 laws in `laws` index, ~3.4M articles in `articles` index.

#### 3. MODERATE: ES PVC provisioned at 20Gi, manifest says 50Gi
The PVC `tezca-es-data` shows 20Gi capacity but the manifest requests 50Gi. With 3.4M articles expected, we may need the full 50Gi. Current usage is only 195MB (partial index). Verify this won't be a problem at full scale — estimate ~5-8GB for the full index.

#### 4. LOW: No Ingress resources
`kubectl get ingress -n tezca` returns empty. Traffic routing to `tezca.mx`, `api.tezca.mx`, and `admin.tezca.mx` must be handled outside K8s (Cloudflare Tunnel or similar). Confirm this is intentional and working correctly.

---

## Infrastructure Inventory

### Deployments
| Deployment | Replicas | Image | Memory Limit | Status |
|------------|----------|-------|--------------|--------|
| tezca-api | 4 (HPA 2-6) | ghcr.io/madfam-org/tezca/api | 2Gi | Running |
| tezca-web | 2 | ghcr.io/madfam-org/tezca/web | 512Mi | Running |
| tezca-admin | 2 | ghcr.io/madfam-org/tezca/admin | 256Mi | Running |
| tezca-worker | 1 | ghcr.io/madfam-org/tezca/api | 2Gi | CrashLoopBackOff |
| tezca-beat | 1 | ghcr.io/madfam-org/tezca/api | 512Mi | CrashLoopBackOff |
| tezca-es | 1 | elasticsearch:7.17.9 | 4Gi (JVM 1g) | Running |
| tezca-redis | 1 | redis:7-alpine | 512Mi | Running |

### Secrets
- `tezca-secrets`: Django, DB, Celery, ES, CORS, Janua auth
- `tezca-r2-credentials`: STORAGE_BACKEND, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL, R2_BUCKET_NAME
- `ghcr-credentials`: Docker registry auth

### PVCs
- `tezca-es-data`: 20Gi (Longhorn) — ES data
- `tezca-redis-data`: 5Gi (Longhorn) — Redis persistence

### Services (all ClusterIP)
- tezca-api: 8000
- tezca-web: 3000
- tezca-admin: 3001
- tezca-es: 9200
- tezca-redis: 6379

---

## Dockerfile Fix Required

File: `apps/indigo/Dockerfile`

The runtime stage (line 49-55) currently installs:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libxml2 \
    libxslt1.1 \
    libgmp10 \
    wget \
    && rm -rf /var/lib/apt/lists/*
```

It needs WeasyPrint's runtime dependencies added:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libxml2 \
    libxslt1.1 \
    libgmp10 \
    wget \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*
```

After this fix is committed and pushed, the CI/CD pipeline (`deploy-api.yml`) will automatically build a new image and update the `kustomization.yaml` digest, which Enclii should then roll out.

---

## CI/CD Pipeline

Three deploy workflows in `.github/workflows/`:
- `deploy-api.yml` — triggers on changes to `apps/api/`, `apps/indigo/`, `pyproject.toml`, `poetry.lock`, `apps/indigo/Dockerfile`
- `deploy-web.yml` — triggers on `apps/web/`, `packages/ui/`, `packages/lib/`
- `deploy-admin.yml` — triggers on `apps/admin/`, `packages/ui/`, `packages/lib/`

Each workflow:
1. Builds and pushes to `ghcr.io/madfam-org/tezca/{service}`
2. Signs with cosign
3. Updates `k8s/production/kustomization.yaml` with new digest (3-attempt retry loop)
4. Reports lifecycle event to Enclii API

---

## Verification Checklist

After fixes are deployed, verify:

### Pod Health
- [ ] All pods in Running state (no CrashLoopBackOff)
- [ ] `tezca-beat` running with DatabaseScheduler
- [ ] `tezca-worker` running with concurrency=4
- [ ] API pods passing liveness/readiness probes

### Data Integrity
- [ ] `python manage.py shell -c "from apps.api.models import Law; print(Law.objects.count())"` returns 30,496
- [ ] Tier distribution: 486 federal, 29,802 state, 208 municipal
- [ ] Law types: 11,907 legislative, 18,439 non_legislative, 150 reglamento

### Elasticsearch (after re-indexing)
- [ ] `curl http://tezca-es:9200/laws/_count` — target: ~30,000+
- [ ] `curl http://tezca-es:9200/articles/_count` — target: ~3,400,000
- [ ] Search returns results: `curl 'http://tezca-es:9200/articles/_search?q=constitucion&size=1'`

### API Endpoints
- [ ] `GET /api/v1/stats/` — returns total_laws=30496
- [ ] `GET /api/v1/search/?q=constitucion` — returns results with total > 0
- [ ] `GET /api/v1/laws/` — returns paginated law list
- [ ] `GET /api/v1/categories/` — returns categories with counts
- [ ] `GET /api/v1/laws/{id}/` — returns law detail with articles

### Frontend Smoke Test
- [ ] `https://tezca.mx/` — homepage loads with stats, featured laws
- [ ] `https://tezca.mx/busqueda?q=constitucion` — search returns results
- [ ] `https://tezca.mx/leyes` — browse page shows paginated laws
- [ ] `https://tezca.mx/categorias` — categories with counts
- [ ] `https://tezca.mx/estados` — states with counts
- [ ] `https://tezca.mx/leyes/{id}` — law detail page with articles, TOC

### R2 Storage
- [ ] `STORAGE_BACKEND=r2` env var is set on API + worker pods
- [ ] R2 credentials are valid and pods can access the bucket
- [ ] `storage.get("law_registry.json")` returns content (not None)
- [ ] `storage.exists("state_laws_metadata.json")` returns True

### Celery Tasks
- [ ] Beat scheduler is creating periodic task entries
- [ ] Worker can execute a test task
- [ ] DOF daily check task is scheduled (`dof-daily-check` at 7 AM)

---

## Priority Order

1. **Fix Dockerfile** (add WeasyPrint system deps) → rebuild image → deploy
2. **Verify beat + worker recover** after new image rolls out
3. **Run ES indexing** with smaller batch size (`--batch-size 50`) on an API pod
4. **Verify all endpoints** per checklist above
5. **Monitor** ES disk usage during full indexing (~5-8GB expected)
