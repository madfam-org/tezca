# Data restore & disaster recovery runbook

Covers the Tezca data tier: Postgres (shared `data` instance, tenant DB
`tezca`), Elasticsearch (single node, 3.5M-doc index), and Redis (broker /
result backend — ephemeral, not backed up by design).

Backups produced by this repo:

- **Postgres** — `tezca-db-backup` CronJob (`k8s/production/tezca-db-backup-cronjob.yaml`),
  daily `pg_dump --format=custom` → `s3://<R2_BUCKET>/backups/db/tezca-<TS>.dump`.
- **Elasticsearch** — SLM snapshots to R2 (`_snapshot/tezca_r2`), set up below.

> RPO with daily jobs is 24h. Measure RTO by running the drill in §1 and
> record the wall-clock in the table at the bottom.

---

## 1. Postgres — restore drill (run quarterly)

Restore the latest dump into a throwaway DB on the same instance and verify,
without touching the live `tezca` DB.

```sh
# 1. Pull the latest dump from R2 to a scratch pod (or the backup image).
LATEST=$(aws --endpoint-url "$R2_ENDPOINT_URL" s3 ls "s3://$R2_BUCKET_NAME/backups/db/" \
  | sort | tail -1 | awk '{print $4}')
aws --endpoint-url "$R2_ENDPOINT_URL" s3 cp "s3://$R2_BUCKET_NAME/backups/db/$LATEST" /tmp/restore.dump

# 2. Restore into a scratch DB (never the live one).
createdb -h "$DB_HOST" -U "$DB_USER" tezca_restore_scratch
pg_restore --no-owner --no-privileges -h "$DB_HOST" -U "$DB_USER" \
  -d tezca_restore_scratch /tmp/restore.dump

# 3. Verify row counts against live (spot check the big tables).
psql -h "$DB_HOST" -U "$DB_USER" -d tezca_restore_scratch \
  -c "select count(*) from api_law; select count(*) from api_lawversion;"

# 4. Drop the scratch DB and record the measured RTO below.
dropdb -h "$DB_HOST" -U "$DB_USER" tezca_restore_scratch
```

## 2. Elasticsearch — one-time snapshot setup, then restore

ES has no volume-independent backup out of the box. Register an R2-backed
snapshot repository and a daily SLM policy. Run these once (they mutate ES
config, not source data) via a port-forward or a one-shot Job.

```sh
# a) Add R2 creds to the ES keystore (S3 client secrets can't be env vars),
#    then restart the ES pod so it reloads the keystore.
elasticsearch-keystore add s3.client.tezca_r2.access_key   # = R2_ACCESS_KEY_ID
elasticsearch-keystore add s3.client.tezca_r2.secret_key   # = R2_SECRET_ACCESS_KEY

# b) Register the repository (endpoint = the R2 S3 endpoint host, path-style).
curl -X PUT "localhost:9200/_snapshot/tezca_r2" -H 'Content-Type: application/json' -d '{
  "type": "s3",
  "settings": {
    "bucket": "<R2_BUCKET_NAME>",
    "base_path": "backups/es",
    "client": "tezca_r2",
    "path_style_access": true,
    "endpoint": "<R2 S3 endpoint host, no scheme>"
  }
}'

# c) Daily SLM policy, 30-day retention.
curl -X PUT "localhost:9200/_slm/policy/tezca-daily" -H 'Content-Type: application/json' -d '{
  "schedule": "0 30 8 * * ?",
  "name": "<tezca-{now/d}>",
  "repository": "tezca_r2",
  "config": { "indices": ["*"], "include_global_state": true },
  "retention": { "expire_after": "30d", "min_count": 5, "max_count": 30 }
}'
```

Restore (into `*-restore` indices, verify, then swap the alias):

```sh
curl -X POST "localhost:9200/_snapshot/tezca_r2/<snapshot>/_restore" \
  -H 'Content-Type: application/json' -d '{
    "indices": "laws-*",
    "rename_pattern": "(.+)",
    "rename_replacement": "$1-restore"
  }'
# verify doc counts, then repoint the read alias to the restored index
curl "localhost:9200/_cat/indices?v"
```

> SLM is a Basic-license feature and works with `xpack.security.enabled=false`.
> If ES is unrecoverable and no snapshot exists, the index can be rebuilt by
> re-running the ingestion pipeline — hours-to-days and involves the
> side-effectful scrapers, which is exactly what snapshots avoid.

## 3. Full-tenant disaster recovery

1. Provision an empty `tezca` DB on the (restored) `data` Postgres instance.
2. `pg_restore` the latest dump (§1).
3. Deploy Tezca (`kubectl apply -k k8s/production`) — the API init container
   runs `manage.py migrate` (a no-op on a restored schema).
4. Restore ES from the latest SLM snapshot (§2); repoint the read alias.
5. Redis needs no restore (broker/result backend rebuilds itself).
6. Smoke: `GET https://api.tezca.mx/api/v1/admin/health/` → `database: connected`
   and `GET /api/v1/stats/` → non-zero `total_laws` / `total_articles`.

---

## Measured RTO/RPO log

| Date | Component | Backup age (RPO) | Restore time (RTO) | Notes |
|------|-----------|------------------|--------------------|-------|
| _run the §1 drill and fill this in_ | | | | |
