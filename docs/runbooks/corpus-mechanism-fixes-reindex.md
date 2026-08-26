# Runbook — corpus mechanism fixes: encoding fidelity, transitorio cap, version supersession

Operator runbook for the side-effectful backfills that three data-quality
mechanism fixes on branch `fix/lfpdppp-transitorio-collision` deliberately do
**not** perform. These are corpus-wide (not one-law) fixes, so they live here
rather than in the LFPDPPP-specific runbook
(`lfpdppp-transitorio-reindex.md`).

| Defect | Layer | Code state | Operator backfill |
| --- | --- | --- | --- |
| #2 — `errors="ignore"` silently deleted accents | read (`paths.py`) | **Fixed + tested** | **Re-index** affected laws (re-reads source with correct decode) |
| #3 — transitorio parsing capped at the 12th ordinal | parse (`akn_generator_v2`) | **Fixed + tested** | **Re-parse** (re-run pipeline) affected laws, then re-index |
| #7 — `valid_to` written nowhere (no supersession signal) | ingest (`db_saver`) | **Fixed + tested** (write-time) | **Backfill** `valid_to` on existing multi-version laws |

> **Guard.** Local legal ingestion / indexing / parsing operations are refused
> unless `LOCAL_LEGAL_DATA_OPS=yes` is set
> (`scripts/require-local-legal-data-ops.mjs`). Set it only for the duration of
> an explicit, supervised operation. In-cluster execution goes through
> `enclii exec tezca-api -- …` against the production API pod (already has
> `ES_HOST` / DB env wired). Enclii-first, never an unattended side effect of a
> merge.

---

## What the code fix changed (context)

- **`apps/api/utils/paths.py` — `read_data_content` / `_decode_bytes` (Defect #2).**
  Both data-read call sites (local filesystem and R2) previously decoded with
  `errors="ignore"`. A latin-1 / cp1252 source (SAT, some OJN feeds) decoded as
  UTF-8 does **not** raise and does **not** emit the U+FFFD replacement char —
  `errors="ignore"` **DELETES** every high byte (á/é/í/ñ/ó/ú, °, §) silently, so
  the accented text entered Elasticsearch stripped of its accents and the
  encoding spot-check (which only counts U+FFFD) never saw it. `_decode_bytes`
  now (1) decodes strict UTF-8 (unchanged fast path), (2) on failure detects the
  real encoding with `charset_normalizer` — biased to the Western-European code
  pages Mexican sources actually use, so `ñ`/`año` decode correctly — and (3)
  falls back to `errors="replace"` (U+FFFD, which the spot-check CAN see), never
  `errors="ignore"`.
- **`apps/parsers/patterns/structure.py` + `apps/parsers/akn_generator_v2.py`
  `_find_transitorios` (Defect #3).** The transitorio finder iterated only the
  1–12 `ORDINAL_PATTERNS` map, so a law's 13th and later transitorios were
  silently dropped (CCF ~50, LFT ~33, LIVA ~27). It now splits the transitorios
  section at every ordinal heading — single (`PRIMERO.-`) and two-word compound
  (`DÉCIMO TERCERO.-`, `VIGÉSIMO QUINTO.-`, `TRIGÉSIMO.-`) alike — and resolves
  the number via `apps.parsers.patterns.articles.ordinal_to_number` (extended
  with tens 30–90). Each transitorio still emits `id="trans-N"`, which the
  indexer reads to namespace it (`T-N`), so the parser fix and the branch's
  indexer collision fix stay consistent. Ordinal-numbered **substantive**
  articles (JCF Reglas: PRIMERA, DÉCIMA QUINTA) are unaffected: the finder only
  looks at text after the `TRANSITORIOS` header, so reglas before it are never
  reclassified.
- **`apps/ingestion/db_saver.py` — `save_law_version` /
  `_close_superseded_version_validity` (Defect #7).** `LawVersion.valid_to` was
  READ by the API/UI (`law_views.py`, `VersionTimeline.tsx`) but WRITTEN
  nowhere, so every superseded version stayed `valid_to=null` and an older text
  looked "current". Creating a new version now closes the prior version's
  interval using the half-open convention (`prior.valid_to = new.valid_from`),
  robust to out-of-order ingestion. This is a **write-time** fix — existing
  versions already in the DB keep `valid_to=null` until a re-ingest or the
  backfill in §3.

None of the read/parse fixes reaches the live corpus until the affected laws
are re-processed. Re-indexing and re-parsing are idempotent.

---

## 1. Defect #2 — re-index laws whose source was mis-encoded

The fix is read-time: `read_data_content` now decodes the source correctly, so
**re-indexing re-reads the XML/text and writes the accented text into ES.** No
re-parse is required if the AKN XML on disk is already correct UTF-8; re-index
is enough. If the stored XML itself was written stripped of accents by an
earlier parse (parser also reads via `read_data_content`), re-parse per §2.

### Which laws are affected

Any law whose source XML/text file is latin-1 / cp1252 rather than UTF-8.
Realistic candidates: SAT-sourced fiscal instruments, some OJN state feeds.
Detect suspects (accent-free Spanish text is the signature):

```sh
# Sample ES text for a law and eyeball for missing accents (no á/é/í/ó/ú/ñ where
# Spanish legal prose should have them, e.g. "Articulo", "informacion", "ano").
curl -s "https://api.tezca.mx/api/v1/laws/<law_id>/articles/" | \
  python -c "import sys,json; d=json.load(sys.stdin); \
  t=' '.join(x.get('text','') for x in d['articles'][:5]); \
  print('accented chars present:', any(c in t for c in 'áéíóúñ')); print(t[:200])"
```

### Re-index

```sh
# Targeted in-place upsert (recommended for a hotfix). See the LFPDPPP runbook
# §1A caveats — never combine --reindex with --law-id.
enclii exec tezca-api -- python apps/manage.py index_laws --law-id <law_id> --dry-run
enclii exec tezca-api -- python apps/manage.py index_laws --law-id <law_id>
```

### Post-verify

Re-run the sample above — accented characters must now be present. The encoding
spot-check should PASS (`encoding_check`, `es_text_sample`):

```sh
enclii exec tezca-api -- python apps/manage.py spot_check --law-id <law_id>
```

---

## 2. Defect #3 — re-parse laws with transitorios past the 12th

Because the cap was in the **parser** (text → AKN), the dropped transitorios are
absent from the AKN XML on disk, so a plain re-index will not recover them. The
law must be **re-parsed** (re-run the ingestion pipeline) to regenerate the AKN
XML with the full transitorios block, then re-indexed.

### Which laws are affected

Any law with more than 12 transitorios. Known long blocks: **CCF (~50)**, **LFT
(~33)**, **LIVA (~27)**. Any code (`codigo`) or long federal law is a candidate.
Quick check — compare the transitorio count in the current AKN vs the source:

```sh
# Count transitorio nodes currently in ES for a law.
curl -s "https://api.tezca.mx/api/v1/laws/<law_id>/articles/" | \
  python -c "import sys,json; d=json.load(sys.stdin); \
  ids=[x['article_id'] for x in d['articles'] if str(x['article_id']).startswith('T-')]; \
  print('transitorio ids:', sorted(ids)); print('count:', len(ids))"
```

If the count caps at 12 (ids `T-1`…`T-12` only) but the source PDF has more,
the law needs a re-parse.

### Re-parse + re-index

```sh
# Re-run the pipeline for the law (download → extract → parse → grade → save).
# This regenerates the AKN XML with ALL transitorios and updates the LawVersion.
# Constrain to the single law from a shell if run_pipeline is too broad:
enclii exec tezca-api -- python apps/manage.py shell -c \
  "import json; from apps.parsers.pipeline import IngestionPipeline; \
   reg=json.load(open('data/law_registry.json')); \
   entry=next(e for e in (reg if isinstance(reg,list) else reg.get('laws',reg.values())) if e.get('id')=='<law_id>'); \
   print(IngestionPipeline().ingest_law(entry))"

# Then re-index in place (§1A caveats apply).
enclii exec tezca-api -- python apps/manage.py index_laws --law-id <law_id>
```

> Adjust the registry-lookup shell snippet to the actual shape of
> `data/law_registry.json` in your checkout. The essential step is
> `IngestionPipeline().ingest_law(<registry entry>)` for the affected law.

### Post-verify

The transitorio ids must now extend past `T-12` to the law's real count:

```sh
curl -s "https://api.tezca.mx/api/v1/laws/<law_id>/articles/" | \
  python -c "import sys,json; d=json.load(sys.stdin); \
  ids=sorted(int(str(x['article_id'])[2:]) for x in d['articles'] \
             if str(x['article_id']).startswith('T-') and str(x['article_id'])[2:].isdigit()); \
  print('transitorio numbers:', ids); print('max:', max(ids) if ids else None)"
```

Spot-check parity (the branch's `akn_es_parity` gate) should still PASS — the
AKN `<article>` count and the distinct ES doc count move together.

---

## 3. Defect #7 — backfill `valid_to` on existing multi-version laws

The supersession write is write-time, so it only fires on the **next** version
creation. Laws already holding multiple versions in the DB keep the older
versions' `valid_to=null` until backfilled. The backfill closes each older
version's interval against its immediate successor (half-open:
`prior.valid_to = successor.valid_from`).

### Preview (no writes)

```sh
enclii exec tezca-api -- python apps/manage.py shell -c "
from apps.api.models import Law, LawVersion
open_older = 0
for law in Law.objects.all():
    vs = list(law.versions.order_by('publication_date'))
    for older, newer in zip(vs, vs[1:]):
        if older.valid_to is None:
            open_older += 1
print('older versions missing valid_to:', open_older)
"
```

### Backfill (writes `valid_to`)

> Side-effectful DB write. Requires an explicit operator request and
> `LOCAL_LEGAL_DATA_OPS=yes` when run locally. No dedicated management command
> ships for this one-off — run the guarded shell below.

```sh
enclii exec tezca-api -- python apps/manage.py shell -c "
from apps.api.models import Law
closed = 0
for law in Law.objects.all():
    vs = list(law.versions.order_by('publication_date'))
    for older, newer in zip(vs, vs[1:]):
        if older.valid_to is None:
            older.valid_to = newer.valid_from or newer.publication_date
            older.save(update_fields=['valid_to'])
            closed += 1
print('closed intervals:', closed)
"
```

### Post-verify

```sh
# The newest version of each law stays current (valid_to null); every older
# version now has valid_to == the next version's valid_from.
enclii exec tezca-api -- python apps/manage.py shell -c "
from apps.api.models import Law
bad = []
for law in Law.objects.all():
    vs = list(law.versions.order_by('publication_date'))
    for older, newer in zip(vs, vs[1:]):
        if older.valid_to is None:
            bad.append((law.official_id, older.publication_date))
    if vs and vs[-1].valid_to is not None:
        bad.append((law.official_id, 'newest-not-current'))
print('anomalies:', bad[:20], '...' if len(bad)>20 else '')
print('total anomalies:', len(bad))
"
```

---

## Scope note — the fuller "flag served law stale on detected reform" (Defect #7)

Defect #7's code fix writes `valid_to` **when a new `LawVersion` is created**.
The DOF change-detector (`apps/scraper/scheduling/dof_ingest.py`) detects
reforms, but auto-ingest is gated by `DOF_AUTO_INGEST_ENABLED` (default **off**).
So a reform that is *detected but not yet ingested* does not create a version
and therefore does not close the prior version's `valid_to` — the served law can
still read as current between detection and ingestion.

Closing that gap fully (out of scope for this fix) would need one of:

1. **Enable `DOF_AUTO_INGEST_ENABLED`** so detected new-law/reform publications
   materialize a `LawVersion` automatically (which now closes `valid_to`). This
   is the cleanest path and reuses the shipped fix end-to-end — but it turns on
   unattended production ingestion and must be an explicit operator decision.
2. **A "pending reform" flag** distinct from `valid_to`: on a detected (not yet
   ingested) reform, mark the current version/law as "reform pending
   `<DOF date>`" so the API/UI can surface a staleness banner before the new
   version lands. This needs a new model field + a detector write + a UI
   surface, and is a separate change.

Until one of those ships, treat `valid_to` as a *post-ingestion* supersession
signal, not a real-time reform alarm.
