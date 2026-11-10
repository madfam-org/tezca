# Runbook: RMF rule-by-rule ingestion and publication tracking

How the Resolución Miscelánea Fiscal is ingested **rule by rule**
(`/api/v1/laws/rmf_<year>/articles/3.13.7`), how new RMF publications are
detected, and the production specifics learned on the first run
(2026-11-10). Code: `apps/parsers/rmf/`,
`apps/api/management/commands/ingest_rmf_rules.py` (#293, #294).

> **Guard.** Ingestion and indexing are legal-data operations. Run them only
> on an explicit operator request. The command refuses to run without
> `LOCAL_LEGAL_DATA_OPS=yes`, except `--dry-run` over local files.

---

## What exists

| Piece | Where | Notes |
|---|---|---|
| Pinned sources | `apps/parsers/rmf/manifests/rmf_<year>.json` | Each text gets URL, DOF date, `valid_from`/`valid_to` (half-open) and SHA-256. Also holds `instruments` (every DOF resolution) and `pending` (published but not yet compiled by SAT). |
| Parser | `apps/parsers/rmf/` | `lines.py` reads pdfplumber lines with style and alignment, 40 pages per open. `segmenter.py` is pure: rule, epígrafe, references, notes, transitorios. `akn.py` writes AKN that `index_laws` reads unchanged. |
| Ingest | `manage.py ingest_rmf_rules` | Checks the hash, parses, validates, writes `data/rmf/rmf_<year>-<key>.xml`, uploads it to R2 (`rmf/…`) when `STORAGE_BACKEND=r2`, then upserts Law + one LawVersion per manifest entry. Runs at nice 19. |
| Article ids | `index_laws` | Rule `3.13.7`; transitorios `T-N` (base) and `T-RK-N` (block K = the (K−1)-th resolución de modificaciones); `Glosario`. |
| Catalog row (legacy) | `ingest_rmf` / `dataops.ingest_rmf_catalog` | Registers that SAT published a document. It creates a text-less version dated 1 January; `ingest_rmf_rules` reports it and leaves it alone. |

RMF 2026 as ingested on 2026-11-10: versions DOF 2025-12-28, compilada 1a RM,
2a RM and 3a RM (the newest is valid 2026-10-02 to 10-30), 1,247 articles.
The **4a RMRMF (DOF 2026-10-30) is `pending`** until SAT publishes its
compiled edition; it does not touch Capítulo 3.13.

## Tracking: how a new publication reaches an operator

1. **DOF, daily (in-cluster).** `dataops.check_dof_daily` reads all three DOF
   editions (matutina, vespertina, extraordinaria) plus yesterday's
   vespertina/extraordinaria. The corpus watch `rmf_resolucion_miscelanea_fiscal`
   fires on any Hacienda entry titled "… Resolución Miscelánea Fiscal …":
   the annual RMF, modifications and anexos. A hit is logged at WARNING,
   recorded in AcquisitionLog (`corpus_watch_alert`), and pushed through
   `deliver_operator_alert`.
2. **SAT, weekly (off-cluster).** `.github/workflows/sat-rmf-watch.yml` runs
   `scripts/check_sat_rmf_compilations.py` on a GitHub-hosted runner every
   Monday. When SAT lists an RMF document (DOF-format resolution or
   `Compilado_*`) the manifest does not know, it opens the issue "SAT RMF:
   publications not yet in the manifest", or comments on it if it is open.
   A failed run means SAT was unreachable from GitHub too.
3. **Health check, daily.** `dataops.check_scraper_health` flags a stale or
   failed **last** run of `rmf_scrape`/`rmf_catalog_ingest` (quarterly jobs can
   never reach "3 failures in 7 days"). It sends one consolidated
   `scraper_health.problems` operator alert per run.

> **Operator alerts are a no-op until `OPERATOR_ALERT_WEBHOOK_URL` and
> `OPERATOR_ALERT_WEBHOOK_SECRET` are set** (unset in production on
> 2026-11-10; there is no `SENTRY_DSN` either). Until then, (1) and (3) only
> reach the worker log and AcquisitionLog; (2) reaches people through GitHub
> issue notifications.

### Why SAT is checked from outside the cluster

`www.sat.gob.mx` is served by CloudFront. From the production egress
(Hetzner, 65.109.68.42) every request returns **504 "Error from cloudfront /
can't connect to the server for this app"**, while the same URLs return 200
from Mexico. The in-cluster `dataops.run_rmf_scraper` therefore finds 0
documents. A zero-document run is now recorded as an error, so the health check flags
it. `ingest_rmf_rules --download` fails in-cluster for the same reason; stage
the PDFs instead (below).

## Adding a new compiled edition (or the next year's RMF)

1. Download the PDF from SAT (from outside the cluster), verify it, and
   compute `shasum -a 256`. Confirm the DOF date and código of the instrument
   it incorporates on `https://dof.gob.mx/index.php?year=…&month=…&day=…&edicion=MAT|VES`.
2. Add a `versions` entry: `key`, `publication_date` (DOF date of the last
   incorporated resolution), `valid_from` (that resolution's transitorio:
   usually the day after publication), `document_url`, `filename`, `sha256`,
   `dof_url`, `change_summary`. Set the previous version's `valid_to` to the
   new `valid_from`, and move the instrument out of `pending`.
3. Dry-run locally (`--dry-run --source-dir <dir>`): rule count, 0 problems.
   Merge. Merging deploys the API (`deploy-api.yml`); wait for Argo.
4. Stage the PDF into the worker and ingest, one version per exec:

```bash
ssh ssh.madfam.io "sudo -n kubectl -n tezca exec -i deploy/tezca-worker -c worker -- sh -c 'mkdir -p data/rmf/sources && cat > data/rmf/sources/<file>.pdf && sha256sum data/rmf/sources/<file>.pdf'" < <file>.pdf
ssh ssh.madfam.io 'sudo -n kubectl -n tezca exec deploy/tezca-worker -c worker -- env LOCAL_LEGAL_DATA_OPS=yes python manage.py ingest_rmf_rules --only <key>'
ssh ssh.madfam.io 'sudo -n kubectl -n tezca exec deploy/tezca-worker -c worker -- python manage.py index_laws --law-id rmf_<year> --dry-run'
ssh ssh.madfam.io 'sudo -n kubectl -n tezca exec deploy/tezca-worker -c worker -- python manage.py index_laws --law-id rmf_<year>'
```

5. Verify `/api/v1/laws/rmf_<year>/articles/` (count, a sample rule's
   text) and `/api/v1/laws/rmf_<year>/` (versions and dates).

### Worker constraints (do not skip)

- The worker is **1 CPU / 2 GiB**, shared with Celery. On 2026-11-10 an
  ingest at normal priority starved Celery and failed the liveness probe
  (container restart). A single-open parse of an 860-page PDF then passed
  1 GB and got the container **OOM-killed**. #294 fixed both: the command
  self-nices, and reading in 40-page chunks keeps it near 370 MB RSS (cgroup
  peak 848 MB).
- Staged files live on the container's ephemeral filesystem; any restart
  wipes them. The AKN survives because it is uploaded to R2.
- Watch memory while it runs. The image has no `ps`/`pgrep`/`pkill`, so pipe
  a Python script over stdin (`kubectl exec -i … python -`) that reads
  `/sys/fs/cgroup/memory.current` and `/proc/*/cmdline`. Nested quoting
  through ssh breaks `python -c`.
- `enclii exec` does not exist; this ssh + `kubectl exec` path is the
  documented Enclii adapter gap.

## Elasticsearch `articles` index (state since 2026-11-10)

`articles` is an **alias** → `articles_v20261110`, with `status`, `law_type` and
`domains` mapped as `keyword`. Until then `articles` was a concrete index
whose dynamic mapping had made those fields `text`. `SearchView` aggregates
on them, so every `/search/` query returned 500. The rebuild used
server-side `_reindex` into a correctly mapped index, then one atomic
`update_aliases` (`add` alias + `remove_index`).

- Rollback: point the alias at `articles_backup_20261110` (old mapping).
- `index_laws --reindex` copies mappings from the **current** index, not from
  `_create_indices`. It keeps whatever the live index has, so check
  `get_field_mapping` after any in-place indexing that adds a field.
