# CNPG Migration — Tezca-Side Preparation

**Last Updated:** 2026-04-27
**Track:** Track 6 of [FEATURE_PARITY_PLAN_2026-04-27](./FEATURE_PARITY_PLAN_2026-04-27.md) §3.2.
**Gates on:** RFC 0012 (CloudNativePG cluster) shipping in `madfam-org/enclii`. Tezca-side prep is small; this doc captures it so the cutover is a one-line env-var flip when the platform is ready.
**Status:** Tezca-side ready (this PR). Cutover deferred to platform-side timeline (Q4-2026 per the plan).

---

## 1. What changes on the Tezca side

The whole reason CNPG is the right shape (per RFC 0012 §2.2.5) is that **clients change nothing** except eventually the connection-string host. PgBouncer hides the topology; Django still talks to PgBouncer.

The only Tezca-side changes:

### 1.1 `apps/indigo/settings.py` — connection knobs (this PR)

Added to the production-Postgres `DATABASES["default"]`:

```python
"CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "0")),
"OPTIONS": {
    "connect_timeout": 5,
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 3,
},
```

Why each:
- `connect_timeout=5` — primary promotion takes <60s per RFC 0012. Without a tight connect timeout, Django + PgBouncer queue requests against a dead primary for the kernel-default TCP-connect timeout (~2 min). 5s fails fast, queue rotates.
- `keepalives_*` — detect dropped connections within ~60s instead of Linux's default ~2h. Without this, stale connections in a long-lived worker pool can outlive a failover and silently lose writes.
- `CONN_MAX_AGE=0` — no connection persistence; Django opens + closes per request. This is the simplest configuration that survives primary promotion without a service reload. Trade-off: ~5ms per request for the connect roundtrip. Acceptable; we can revisit (and bump to 60s) post-cutover if PgBouncer's transaction-pooling layer needs Django's pooling out of the way.

### 1.2 `enclii.yaml` — declares dependency on the `data/postgres-ha` Cluster (deferred)

Once RFC 0014 zero-touch onboarding lands the `runtime.databases[]` schema, Tezca's `enclii.yaml` should declare:

```yaml
spec:
  runtime:
    databases:
      - name: tezca
        cluster: postgres-ha     # CNPG Cluster name in data namespace
        access: read-write
```

Switchyard projects this into the K8s NetworkPolicy + ExternalSecrets that hand the tezca pods a DSN pointing at `postgres-ha-rw.data.svc.cluster.local`.

This is **not** in this PR — it depends on the RFC 0014 schema being live. Tracking comment added inline in `enclii.yaml` so the next person editing it sees the intent.

### 1.3 Cutover env-var flip (operator)

When the CNPG cluster is live + Tezca's database has been migrated:

```bash
# Flip the host. PgBouncer continues to front the cluster — same string
# as today plus the CNPG-managed Service.
enclii secrets set DB_HOST="postgres-ha-rw.data.svc.cluster.local" \
  --service tezca-api --secret
enclii secrets set DB_HOST="postgres-ha-rw.data.svc.cluster.local" \
  --service tezca-worker --secret
enclii secrets set DB_HOST="postgres-ha-rw.data.svc.cluster.local" \
  --service tezca-beat --secret

enclii deploy --env production --service tezca-api
enclii deploy --env production --service tezca-worker
enclii deploy --env production --service tezca-beat
```

The Postgres user/password/DB-name don't change — only the host.

---

## 2. What does NOT change on the Tezca side

- **Django models.** The CNPG primary is still Postgres 15+; all current migrations apply.
- **Read-replica routing.** This PR does NOT use the `postgres-ha-ro` Service — a future enhancement could split read-only queries (search list, coverage stats) to the standby for additional headroom, but the v1 shape is single-Service-via-PgBouncer.
- **Storage backend.** Cloudflare R2 (`apps/api/storage.py`) is independent of Postgres HA.
- **Elasticsearch.** ES HA is a sister project (sister of RFC 0012). Per CLAUDE.md known gaps, it remains single-node post-cutover. Out of scope for Track 6.

---

## 3. Cutover runbook (when CNPG ships)

This is the abbreviated Tezca-side view. The full platform-side runbook lives at `internal-devops/runbooks/postgres-failover-drill.md` (per RFC 0012 §1).

### Pre-flight
- [ ] CNPG `Cluster: postgres-ha` deployed + soaked in staging for ≥1 week (per RFC 0012 §6 cutover-window plan)
- [ ] Tezca's database has been migrated to the CNPG cluster (`pg_dump` from old single-instance + `pg_restore` into the CNPG primary, run during a maintenance window)
- [ ] Staging tezca cutover green for ≥48 hours

### Cutover
- [ ] Maintenance window declared on `status.tezca.mx` (~10 min budget)
- [ ] Operator updates `DB_HOST` secret on tezca-api / tezca-worker / tezca-beat (§1.3)
- [ ] `enclii deploy` rolls all three Deployments
- [ ] Smoke test: hit `https://api.tezca.mx/api/v1/admin/health/`, expect 200 with `database: connected`
- [ ] Synthetic write: fire one webhook event via `POST /api/v1/webhooks/<id>/test/`, observe Karafiel-staging receives it
- [ ] Failover drill (per RFC 0012 §3.2): kill the CNPG primary pod; verify writes resume in <60s

### Rollback
- [ ] If anything fails, flip `DB_HOST` back to the original single-instance Service. Documented in RFC 0012 §6.

---

## 4. Risk register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Tezca's `_pg_options` conflicts with PgBouncer transaction-pooling | Low | Medium | Already validated against PgBouncer's known-incompat list (autocommit, prepared statements). Our settings touch keepalives + connect_timeout only — both compatible. |
| `CONN_MAX_AGE=0` creates connection-thrashing under load | Low | Medium | Existing tezca traffic is <10 RPS in production; PgBouncer absorbs the open/close churn. Revisit if RPS crosses ~100. |
| Failover takes >60s (RFC 0012 §3.2 target) | Medium | Material | We accept the documented SLA caveat (Institutional 99.9% best-effort) until HA is fully soaked. Per benchmark §6.1 decision: ship Institutional with the caveat. |
| Read-replica routing isn't enabled | Low | Low | Not a regression — same as today. Future enhancement post-cutover. |

---

## 5. Done criterion

Per the feature-parity plan §3.2:

- [x] `apps/indigo/settings.py` updated with CNPG-friendly connection knobs (this PR)
- [ ] `enclii.yaml` declares `runtime.databases[]` dependency (gated on RFC 0014 schema landing)
- [ ] Tezca DB migrated to `postgres-ha-rw` (gated on RFC 0012 cluster shipping)
- [ ] Failover drill passes in production (per RFC 0012 §3.2)
- [ ] No client code change required ✅ (already true; this is the architectural goal)

---

## 6. Related

- `internal-devops/rfcs/0012-postgres-ha-via-cnpg.md` — the upstream RFC
- `internal-devops/rfcs/0014-zero-touch-onboarding.md` — `runtime.databases[]` schema
- `internal-devops/runbooks/postgres-failover-drill.md` — full platform runbook
- `enclii.yaml` — Tezca's service declaration (will be updated post-RFC-0014)
- `apps/indigo/settings.py` — connection settings (this PR)
