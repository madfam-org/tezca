# Total Capture Roadmap — the path to the full Mexican legal universe

**Date:** 2026-07-10 · **Status:** active · **Owner:** platform

This is the canonical plan for advancing Tezca from "the legislative core"
toward *total capture* of the Mexican legal universe. It consolidates the
2026-07-10 audit + deep dive, records the remediation shipped that day, and
sequences the remaining work by tier — separating what is **code-doable**
from what needs **operator/partnership action** or is **bot-wall-blocked**.

Numbers are sourced from `data/universe_registry.json` and cross-checked
against the live API (`/api/v1/stats/`). Where they disagree, trust the
registry and flag it.

---

## 1. Where we are

The registry estimates the full universe at **~652,136 instruments**; Tezca
captures **~5.5%** of it. That headline is dominated by two tiers that sit at
**0% capture and together are 94% of the universe**.

| Tier | Est. universe | Captured | Coverage | Confidence in denominator |
|---|---:|---:|---:|---|
| Federal leyes vigentes | 336 | 336 | ~100% | High |
| State legislativo (OJN p2) | 12,120 | 12,468 | ~100% | High |
| State non-legislativo (OJN p1/3/4) | 23,660 | 19,042 | 80.5% | High |
| International treaties (SRE) | 1,500 | 1,510 | ~100% | Medium |
| Federal reglamentos | ~800 | 150 | ~19% | Medium |
| Federal NOMs | ~4,000 | 428 | ~11% | Low |
| Municipal | unknown | 2,439 (6 cities) | undefined | None |
| **CONAMER CNARTyS** | **113,373** | **0** | **0%** | Medium |
| **SCJN jurisprudencia** | **60,000** | **0** | **0%** | High |
| **SCJN tesis aisladas** | **440,000** | **0** | **0%** | Medium |
| **Total** | **652,136** | **~35,945** | **5.5%** | denom. ~94% estimated |

**"Total capture" is only well-defined for the legislative core** (Tiers 1–3
have official, verifiable denominators; Tezca is ~90–100% there). Above it the
denominators are estimated, overlapping (CONAMER may double-count reglamentos +
NOMs), or literally `null` (municipal). Hard ceilings: ~5,220 permanently dead
OJN links (Michoacán/EDOMEX/SLP, recoverable only via FOIA to SEGOB), paper-only
municipal instruments, and government anti-bot walls (below). The practical
asymptote for the core is ~95–98%; for the full universe a single percentage
is undefinable.

---

## 2. What shipped 2026-07-10 (remediation)

The deep dive found that the two mega-tiers were 0% **despite having working
scrapers and scheduled Beat tasks** — the blockers were wiring/ingest bugs, not
missing scrapers. Merged to `main`:

| PR | Tier | Fix |
|---|---|---|
| tezca#140 | CONAMER | `ingest_conamer` was orphaned (called nowhere); wired `dataops.ingest_conamer_catalog` task + weekly Beat, mirroring the judicial pattern. |
| tezca#141 | SCJN | Auto-ingest read a dir no scraper writes to; now reads `data/judicial/` recursively and skips degenerate (empty-text) records. |
| tezca#144 | seam | Changelog emits `domains` so Karafiel's fiscal filter works on the catch-up path. |
| tezca#146 | DOF | `check_dof_daily` was detect-and-log only; wired detection → `IngestionPipeline.ingest_law` behind `DOF_AUTO_INGEST_ENABLED` (default off); fixed the `ingested` misnomer. |
| tezca#145 | infra | pg_dump CronJob → R2, ES heap 1g→2g, restore runbook (`docs/runbooks/data-restore.md`). |
| tezca#143 | hygiene | `makemigrations --check` in CI; corrected article/coverage/go-live claims. |
| internal-devops#201 + karafiel#110 | seam | `legal-alert.v1.json` contract + Karafiel-side reconciliation (serializer, `results`→`changes`, fiscal gate → `domains`). |

**Net:** the ingest plumbing for CONAMER, SCJN, and DOF is now correct. What
remains to actually *populate* those tiers is scraping data past the walls
below — which is not a wiring problem.

---

## 3. The path forward, by tier

Legend: 🟢 code-doable · 🟡 operator/runtime · 🔴 partnership / bot-wall-blocked.

### Phase A — the two mega-tiers (94% of the universe)

- **SCJN judicial (~500K) — 🔴 bot-wall.** The SJF portal
  (`sjfsemanal.scjn.gob.mx`) is behind an **Imperva WAF** — confirmed
  2026-07-10, it returns "Access denied / Error 15" to an ordinary browser,
  exactly as it blocks the Playwright scraper. Repairing DOM selectors
  (`scjn_playwright.py`) cannot be validated while the wall is up. **Realistic
  path: an SCJN data partnership / bulk dump** ingested via
  `ingest_judicial --dir` (the ingest side is fixed and tested). Fallback:
  residential-proxy / anti-bot infrastructure to reach SJF. Tracked in #142.
- **CONAMER CNARTyS (113,373) — 🔴 WAF + 🟢 dedup.** The catalog
  (`catalogonacional.gob.mx`) is WAF-protected (scraper docstrings note 403 +
  expired SSL on the legacy host). When the scrape returns data, the wired
  `ingest_conamer_catalog` task lands it — but first **dedup against the
  existing reglamentos/NOM corpus** (CONAMER writes the same
  `tier=federal, law_type=non_legislative` bucket) and replace the O(N×M)
  name-dedup in `ingest_conamer` with an indexed lookup, or 113K collapses or
  double-counts. The dedup hardening is code-doable now.

> After Phase A lands data, total capture jumps **5.5% → ~32%**. It is the
> single biggest move and is gated on getting past the walls, not on building.

### Phase B — state non-legislativo (4,618 uncaptured; 4,438 permanent) — 🟡

Run the built `ojn-recovery` + `wayback-recovery` monthly tasks harder; file
the SEGOB FOIA (Escalation Template 2) for the permanently-dead OJN links.
Realistic recovery ~2,000–3,000. Raises legislative-core coverage → ~92%.

### Phase C — federal secondary depth — 🟢 + 🟡

- Reglamentos 150 → ~800: `reglamentos_spider.py` works; discover the remaining
  URLs and add a Beat task.
- NOMs 428 → ~4,000: `nom_scraper.py` is already scheduled; widen discovery
  across secretarías / the DOF archive.

### Phase D — municipal — 🟢 config, then long tail

Run the **15 pre-configured tier-2 cities** in `municipal/config.py` (status
`"ready"`, never executed) and add the **first-ever municipal Beat task**
(today there is zero municipal freshness mechanism). Denominator stays unknown;
treat as absolute additions. The long tail (2,468 municipios, paper-only
bandos) is intractable to full automation.

### Phase E — tesis aisladas (440K) — 🔴 partnership

Same SJF wall as Phase A. Pursue an SCJN bulk dump rather than scraping 440K
pages through the WAF. If landed, nominal coverage → ~99% — but that figure is
only as real as the 500K estimate.

---

## 4. Freshness (staying captured)

"Total capture" also means staying current. Holes to close (🟢 code-doable):

- **DOF daily** froze the corpus at 2026-01-19 (no write path existed — fixed
  in #146, gated). Operator: confirm `tezca-beat` runs, backfill
  2026-01-20 → today, then enable `DOF_AUTO_INGEST_ENABLED` after staging
  validation of the nota→PDF resolution.
- **Municipal** — no Beat task (Phase D adds the first).
- **Bulk OJN state corpus (~30K)** — no scheduled full re-scrape; only
  dead-link recovery + staleness detection touch it. Add a periodic re-scrape.

---

## 5. Hard blockers (not code)

- **Government anti-bot walls** — SJF (Imperva, confirmed) and CONAMER. These
  gate ~94% of the universe. The durable answer is **data partnerships / bulk
  access**, with anti-bot infrastructure as a fallback. This is the highest-
  leverage non-engineering action for the mission.
- **Dead OJN links (~5,220)** — recoverable only via FOIA to SEGOB.
- **Expired CI/CD secrets** (`MADFAM_BOT_PAT`, `NPM_MADFAM_TOKEN`) block
  deploying the remediation above; rotate to ship. See tezca#148.

---

## 6. Sequenced coverage trajectory

`5.5% (today)` → **~32% after Phase A** (unblock the two mega-tiers) →
~33% after B/C/D (small vs. the mega-tiers) → **~99% after Phase E** — with the
standing caveat that everything above the legislative core is measured against
an estimated, partly-overlapping, partly-null denominator.

The honest framing: Tezca has **effectively completed its original mission**
(the legislative core, ~36K instruments, ~90–100%). "Total capture" of the
full 652K is a **data-access problem** (partnerships past government walls),
not a platform-engineering problem — the pipelines are now wired to receive it.
