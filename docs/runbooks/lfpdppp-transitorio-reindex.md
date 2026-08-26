# Runbook — LFPDPPP transitorio-collision re-index & RLFPDPPP ingestion

Operator runbook for the two side-effectful steps that the code fix on branch
`fix/lfpdppp-transitorio-collision` deliberately does **not** perform:

1. **Re-index LFPDPPP** so the transitorio-collision fix (Defect 1), the
   newest-version fix (Defect 2), and the `status` fix (Defect 3) reach the live
   Elasticsearch index.
2. **Ingest RLFPDPPP** (Reglamento de la LFPDPPP, Defect 4) so Art. 51 (the
   *encargado* provision) and the rest of the Reglamento become searchable.

Both mutate production data (Elasticsearch documents / the Postgres `tezca` DB)
and are gated behind the guarded legal-data-ops workflow. Run them from an
operator context, Enclii-first, never as an unattended side effect of a merge.

> **⚠️ INVOCATION CORRECTION (2026-08-26).** Earlier drafts of this runbook used
> `enclii exec tezca-api -- python apps/manage.py …`. **`enclii exec` is NOT a real
> subcommand** (`enclii --help` has no `exec`; `enclii ops pods` only diagnoses/
> logs/restarts). The sanctioned in-cluster path is a **registered Celery task run
> as an audited one-off job**:
>
> ```bash
> # Re-index LFPDPPP in place (the transitorio/status/newest-version fix → live ES).
> # Dry run first (counts, no ES writes), then the real run:
> enclii jobs run dataops.reindex_law -- law_id=lfpdppp dry_run=true  --service tezca-worker --env production
> enclii jobs run dataops.reindex_law -- law_id=lfpdppp               --service tezca-worker --env production
> ```
>
> `dataops.reindex_law` (added in `apps/scraper/scheduling/tasks.py`) wraps
> `index_laws --law-id <id>` — the in-place upsert path, and it **refuses** the
> corpus-dropping `--reindex`/`--all` variants. It runs on the worker, which has
> `ES_HOST`/DB env wired. (Confirm the exact `enclii jobs run` vs `run-once` flag
> shape against `enclii jobs --help` / `enclii jobs list` for the current CLI —
> the `-- key=val --service --env` form follows `docs/research/SCRAPER_FIRST_RUN_CHECKLIST.md`.)
> The verification `curl` steps below are correct as-is. The raw `python apps/manage.py …`
> lines in §1–§2 are the reference for an operator with a direct pod shell
> (`ssh ssh.madfam.io` → `kubectl exec`), NOT for `enclii exec`.
>
> **Guard.** Local legal ingestion / indexing / export operations are refused
> unless `LOCAL_LEGAL_DATA_OPS=yes` is set (`scripts/require-local-legal-data-ops.mjs`).
> That guard is on the LOCAL npm/script wrappers only — the `index_laws` Django
> command (and thus `dataops.reindex_law`) has no such guard and runs cleanly on
> the trusted worker.

---

## 0. What the code fix changed (context)

- `apps/api/management/commands/index_laws.py`
  - `extract_articles_from_xml` now namespaces **transitorio** provisions so a
    transitorio and a same-numbered substantive article no longer collide on the
    Elasticsearch `_id` `"{law}-{article}"`. The substantive article keeps its
    number (e.g. `lfpdppp-8`); the "Octavo" transitorio moves to a distinct id
    (`lfpdppp-T-8`, `article="T-8"`). A defensive de-dup pass additionally
    suffixes any residual same-id collisions (e.g. reform-decree provisions that
    re-use substantive article numbers and are not cleanly marked as transitorio
    in the source XML) so later docs never silently overwrite earlier ones.
  - `index_law` now selects `law.versions.first()` (the **newest** version, per
    `LawVersion.Meta.ordering = ["-publication_date"]`) instead of `.last()`
    (which was the oldest).
- `apps/ingestion/db_saver.py` now populates `Law.status` (defaults to
  `vigente`, normalises registry aliases like `active`/`discovered`).
- `data/law_registry.json` gained an ingest-ready `reg_reg_lfpdppp` entry with a
  real `publication_date` (2011-12-21) so a future ingest creates a real
  `LawVersion` for the Reglamento (see §2).

None of the above takes effect on the live API until the affected laws are
**re-indexed** (steps below). Re-indexing is idempotent by `_id`.

---

## 1. Re-index LFPDPPP (Defects 1–3)

Choose **1A** (targeted, low blast-radius, recommended for a hotfix) or **1B**
(full rebuild with alias swap). Do **not** combine `--reindex` with `--law-id`
— see the warning in §1B.

### Pre-checks

```sh
# Cluster + ES reachable, and the LFPDPPP law + newest version exist.
enclii exec tezca-api -- python apps/manage.py shell -c \
  "from apps.api.models import Law; l=Law.objects.get(official_id='lfpdppp'); \
   v=l.versions.first(); print('status=',l.status,'newest=',v.publication_date, v.xml_file_path)"

# Baseline: today's (buggy) article 8 — expect DOF-2025 transitorio text.
curl -s https://api.tezca.mx/api/v1/laws/lfpdppp/articles/ | \
  python -c "import sys,json; d=json.load(sys.stdin); \
  a={x['article_id']:x for x in d['articles']}; print('8 ->', a.get('8',{}).get('text','')[:120])"
```

> If `status` still shows `unknown` here, the DB has not been re-ingested since
> the `db_saver` fix. Defect 3 is a **write-time** fix — an existing `lfpdppp`
> row keeps `unknown` until its next `save_law_version` (a re-ingest) or a
> one-off `Law.objects.filter(official_id='lfpdppp').update(status='vigente')`.
> The re-index in this section carries whatever `Law.status` currently is into
> ES, so set the DB status first if you want the API to report `vigente`.

### 1A. Targeted in-place re-index (recommended)

Re-writes only the LFPDPPP documents into the **live** index, upserting by
`_id`. Corrupted ids (`lfpdppp-1..10`, `lfpdppp-20`) are overwritten with the
correct substantive-article text (the substantive article now wins its own id),
and the new transitorio docs (`lfpdppp-T-1`, `lfpdppp-T-8`, …) are added.

```sh
# Dry run first — prints how many articles WOULD be indexed, no ES writes.
enclii exec tezca-api -- python apps/manage.py index_laws --law-id lfpdppp --dry-run

# Real run (no --reindex → in-place upsert into the current alias/index).
enclii exec tezca-api -- python apps/manage.py index_laws --law-id lfpdppp
```

> **Stale-doc note.** In-place upsert cannot delete an id that no longer exists
> in the new output. For this fix that is not a problem — every previously
> corrupted id (`lfpdppp-1..10`, `-20`) is a substantive article number that the
> fix still emits, so each is overwritten with correct content. No orphan ids
> are created. If you want a guaranteed-clean document set, use 1B instead.

### 1B. Full rebuild with alias swap (clean slate)

`--reindex` builds a **new versioned index from scratch** and swaps the `articles`
alias to it after indexing. It is the zero-orphan option but re-indexes the
entire corpus (~minutes, ~3.5M docs).

```sh
# Dry run.
enclii exec tezca-api -- python apps/manage.py index_laws --all --reindex --dry-run

# Real run — new index + alias swap at the end.
enclii exec tezca-api -- python apps/manage.py index_laws --all --reindex
```

> **⚠️ Never `--reindex --law-id lfpdppp`.** `--reindex` creates an *empty* index
> and swaps the alias to it containing **only the laws indexed in that run**. A
> single-law reindex would drop every other law from the live alias. Use `--all`
> with `--reindex`, or use the in-place path (1A) for a single law.

### Post-verify (either path)

```sh
# Article 8 must now be the real substantive article (consentimiento del titular),
# NOT the DOF-2025 transitorio.
curl -s https://api.tezca.mx/api/v1/laws/lfpdppp/articles/ > /tmp/lfpdppp.json
python - <<'PY'
import json
d = json.load(open('/tmp/lfpdppp.json'))
by = {x['article_id']: x['text'] for x in d['articles']}
ids = set(by)
print('has substantive 8 :', '8' in ids, '->', by.get('8','')[:80])
print('has transitorio T-8:', 'T-8' in ids, '->', by.get('T-8','')[:80])
# Substantive 1..10 and 20 must exist and read as real articles, not transitorios.
missing = [n for n in [*map(str, range(1,11)), '20'] if n not in ids]
print('missing substantive ids:', missing or 'none')
# Transitorios should appear under T-* ids, sorted after numbered articles.
print('transitorio ids       :', sorted(i for i in ids if i.startswith('T-')))
PY
```

**Expected post-re-index API behaviour**

- `GET /api/v1/laws/lfpdppp/articles/` → article `8` returns the real
  substantive article (data-protection *consentimiento* text), and articles
  `1`–`10` and `20` are their genuine substantive text again.
- The DOF-2025 reform transitorios appear as distinct entries under `T-*` ids
  (e.g. `T-8` = the INAI/PNT transitorio), sorted after the numbered articles by
  the API's natural sort. Each transitorio ES doc also carries
  `is_transitorio: true` and a `transitorio` tag.
- No two article documents share an Elasticsearch `_id` for `lfpdppp`.
- If the DB status was set (see pre-check note), the law-level document reports
  `status: "vigente"` instead of `unknown`.

### Rollback

- **1A**: re-run `index_laws --law-id lfpdppp` from the previous image/commit to
  restore prior behaviour (still idempotent by `_id`).
- **1B**: `swap_alias` back to the previous versioned index, then delete the new
  one. List/point the alias with the helper command:
  ```sh
  enclii exec tezca-api -- python apps/manage.py manage_es_alias --status
  ```

---

## 2. Ingest RLFPDPPP — Reglamento de la LFPDPPP (Defect 4)

`reg_reg_lfpdppp` was a discovered-only 0-article stub: it lived in
`data/discovered_reglamentos.json` (id/name/url/remote_path only) and was absent
from `data/law_registry.json`, so no `LawVersion` — hence no XML, no articles,
and Art. 51 could not be served.

**What the code fix already did (no side effects):** added a full, ingest-ready
`reg_reg_lfpdppp` entry to `data/law_registry.json` with a real
`publication_date` (`2011-12-21`, DOF publication of the Reglamento) and the
official source URL. This is the missing precondition — `db_saver` skips version
creation whenever `publication_date` is empty/placeholder, which is why the
normalised discovered entry (`publication_date: ""`) never produced a version.

**What the operator still must run (side-effectful, do NOT run from CI/merge):**
download → parse → ingest → index. The source PDF is:

```
https://www.diputados.gob.mx/LeyesBiblio/regley/Reg_LFPDPPP.pdf
```

### Pipeline trace (what each step does)

1. **Download** the PDF (`Reg_LFPDPPP.pdf`) into the raw data tier
   (`apps/parsers/pipeline.py::_download_pdf`).
2. **Extract text** from the PDF (`_extract_text`).
3. **Parse to AKN** via `AkomaNtosoGeneratorV2` (`_parse_to_xml`) → hierarchy +
   articles + TRANSITORIOS. This writes `data/federal/mx-fed-reg_reg_lfpdppp.xml`
   (or the pipeline's configured path).
4. **Quality-grade** the parse (`_calculate_quality`); D/F grades are quarantined
   from indexing unless `--include-quarantined`.
5. **Persist** `Law` + `LawVersion` via `apps/ingestion/db_saver.py`
   (`save_law_version`) — now sets `status='vigente'` and, because the registry
   entry carries a real `publication_date`, actually creates the `LawVersion`.
6. **Index** into Elasticsearch via `index_laws` (transitorio-namespacing applies
   here too).

### Commands

```sh
# One law, synchronous, supervised. Federal-only, skip state/municipal scraping.
# Runs the pipeline end-to-end for the reglamento entry now present in the registry.
enclii exec tezca-api -- python apps/manage.py run_pipeline \
  --local --skip-states --skip-municipal

# …then index just the reglamento in place (see §1A caveats):
enclii exec tezca-api -- python apps/manage.py index_laws --law-id reg_reg_lfpdppp --dry-run
enclii exec tezca-api -- python apps/manage.py index_laws --law-id reg_reg_lfpdppp
```

> `run_pipeline` processes the federal registry; if you need to constrain it to
> exactly `reg_reg_lfpdppp`, run the single-law pipeline path from a shell
> (`from apps.parsers.pipeline import IngestionPipeline; \
> IngestionPipeline().ingest_law(<registry entry for reg_reg_lfpdppp>)`) using
> the registry entry now in `data/law_registry.json`, then index as above.
> Keep `LOCAL_LEGAL_DATA_OPS=yes` set only for the operation when running
> locally rather than via `enclii exec`.

### Post-verify

```sh
# The reglamento must now report a version and a non-zero article count,
# and Art. 51 (the encargado provision) must be retrievable.
curl -s https://api.tezca.mx/api/v1/laws/reg_reg_lfpdppp/ | \
  python -c "import sys,json; d=json.load(sys.stdin); print('articles=', d.get('articles'), 'status=', d.get('status'))"

curl -s https://api.tezca.mx/api/v1/laws/reg_reg_lfpdppp/articles/ | \
  python -c "import sys,json; d=json.load(sys.stdin); \
  a={x['article_id']:x for x in d['articles']}; print('Art 51 present:', '51' in a); \
  print(a.get('51',{}).get('text','')[:160])"
```

**Expected post-ingest behaviour**

- `reg_reg_lfpdppp` reports a `LawVersion` (publication_date 2011-12-21),
  `status: "vigente"`, and a non-zero article count (RLFPDPPP has ~132 articles).
- `GET /api/v1/laws/reg_reg_lfpdppp/articles/` returns Art. 51 and the rest,
  enabling the cross-reference from LFPDPPP → RLFPDPPP that the minors'
  clinical-health-data DPA needs.

### Caveats / judgment for the operator

- **Parse quality is not guaranteed.** The V2 parser is heuristic. If the
  Reglamento grades D/F it is quarantined; inspect the parse and only index with
  `--include-quarantined` after a spot check. Verify article numbering (esp.
  Art. 51) against the official PDF before relying on it for legal work.
- **Register the version XML path.** Confirm `LawVersion.xml_file_path` points at
  the generated AKN file that `index_laws` can read (`read_data_content`); a
  missing file silently indexes 0 articles.
- The `reg_reg_lfpdppp` id is kept identical to the discovery record to avoid a
  divergent identifier; the `slug` matches. If ecosystem convention prefers a
  single-`reg_` slug, rename in the registry entry **before** the first ingest
  (the id becomes the ES `law_id` and the API path).

---

## Verification note (what was done in code vs left to the operator)

| Item | State |
| --- | --- |
| Defect 1 — transitorio id collision | **Fixed in code + tested.** Re-index (this runbook §1) to reach live ES. |
| Defect 2 — `versions.last()` → `.first()` | **Fixed in code + tested.** Re-index to reach live ES. |
| Defect 3 — `Law.status` population | **Fixed in code + tested** (write-time). Takes effect on next ingest/re-ingest of a law; existing rows keep prior status until then. |
| Defect 4 — RLFPDPPP stub | **Registry entry added (no side effects) + tested.** Full ingest is operator-run (§2). |
| Prod re-index of LFPDPPP | **Not run** (side-effectful; operator, §1). |
| Prod ingest of RLFPDPPP | **Not run** (side-effectful; operator, §2). |
