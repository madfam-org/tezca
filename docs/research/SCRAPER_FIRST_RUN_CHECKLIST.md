# Scraper First-Run Checklist

**Last Updated:** 2026-04-27
**Purpose:** Each new scraper merged to main must execute at least once against its real source portal in production before it can be considered "validated." This doc captures the per-scraper acceptance criteria operators run after deploy.
**Track:** A+ Item 3 (Workstream 6 Phase 1 of [`A_PLUS_REMEDIATION_PLAN_2026-04-27.md`](../strategy/A_PLUS_REMEDIATION_PLAN_2026-04-27.md)).

---

## Why this exists

Tezca's scrapers have unit tests with mocked HTML — they verify our parsing logic. They cannot verify URL guesses against the real portal. This is fine for code review but unsafe for production: a scraper that 404s silently is the difference between "we have Hidalgo coverage" and "we shipped a broken claim."

The first-run checklist closes the loop. After every scraper-PR merge, an operator runs the scraper once via Enclii, captures the actual catalog size + first 3 law titles + AcquisitionLog row, and either flips the coverage tile green or files a follow-up.

---

## How to run a scraper from production

### Option A — via Celery dispatch (recommended)

```bash
# Trigger via the dataops.run_state_scraper Celery task
enclii jobs run dataops.run_state_scraper -- state_key=hidalgo --service tezca-worker --env production

# Watch logs
enclii logs tezca-worker -f --since 5m | grep -i "state.*scraper\|laws.*found"
```

Result: a `data/state_laws/<state>/catalog.json` file lands in the worker's R2-backed volume, and an `AcquisitionLog` row records `found`/`downloaded`/`failed` counts.

### Option B — via Django shell (when the dispatch table doesn't have it yet)

```bash
enclii shell tezca-worker --env production
>>> from apps.scraper.state.<state> import <Class>Scraper
>>> s = <Class>Scraper()
>>> catalog = s.scrape_catalog()
>>> print(f"Found {len(catalog)} laws. First 3 titles:")
>>> for law in catalog[:3]: print(f"  - {law['name']}")
```

### Capturing the AcquisitionLog row

```bash
enclii shell tezca-api --env production
>>> from apps.scraper.dataops.models import AcquisitionLog
>>> latest = AcquisitionLog.objects.filter(operation__startswith="state_scraper_").order_by("-started_at").first()
>>> print(latest.operation, latest.found, latest.downloaded, latest.failed, latest.error_summary)
```

---

## Per-scraper acceptance criteria

Each row below is a single first-run target. Tick it (`[x]`) once the operator completes the live run + captures the `AcquisitionLog` row + verifies the expected size band.

### Federal scrapers

| Scraper | Operation key | Expected catalog | First-run command | Acceptance |
|---|---|---|---|---|
| RMF (SAT) | `rmf_scrape` | 5–35 documents (annual + ≤4 modifications + ≤31 annexes) | `enclii jobs run dataops.run_rmf_scraper -- year=2026` | [ ] catalog has annual RMF + at least Anexo 1; `domains: ["fiscal"]` set on Law rows |
| RMF quarterly modifications | `rmf_scrape` (year=2026) | each new modification adds 1 doc | quarterly Beat tick (8th of Jan/Apr/Jul/Oct) | [ ] 1st quarterly mod ingested when SAT publishes (typically Feb–Mar) |
| NOM scraper (priority) | `nom_priority_scrape` | ~500–800 NOMs | (already running per `nom-weekly-discovery` Beat) | [x] currently green |
| NOM agency scrapers (full) | `nom_full_scrape` | ~3000-4000 NOMs | (already running per `nom-monthly-full` Beat 15th) | [x] currently green |
| Treaty scraper | `treaty_scrape` | ~1500 treaties | (already running per `treaty-weekly-check` Beat) | [x] currently green |
| CONAMER (Playwright) | `conamer_playwright_scrape` | ~50k unique items across ~200 pages | (already running per `conamer-playwright-weekly` Beat) | [x] currently green |
| DOF historical | `dof_historical_scan` | year-dependent | (already running per `dof-historical-quarterly` Beat) | [x] currently green |
| SCJN judicial | `scjn_jurisprudencia_scrape` | ~5000 items per run | (already running per `scjn-weekly-scrape` Beat) | [x] currently green |

### State scrapers (16/32 — coverage tracker)

| State key | Status | Expected catalog | Notes |
|---|---|---|---|
| baja_california | ✅ live | ~340 laws | `congresobc.gob.mx`, mature scraper |
| durango | ✅ live | ~250 laws | `congresodurango.gob.mx` |
| quintana_roo | ✅ live | ~200 laws | `congresoqroo.gob.mx` |
| guerrero | ✅ live | ~280 laws | mature |
| nuevo_leon | ✅ live | ~350 laws | mature |
| cdmx | ✅ live | ~300 laws | newly registered in dispatch table 2026-04-27 |
| estado_de_mexico | ✅ live | ~400 laws | newly registered |
| michoacan | ✅ live | ~280 laws | newly registered |
| san_luis_potosi | ✅ live | ~220 laws | newly registered |
| zacatecas | ✅ live | ~180 laws | newly registered |
| **aguascalientes** | 🆕 **PENDING FIRST RUN** | 150–200 (estimated) | URL: `congresoags.gob.mx`. First-run: `enclii jobs run dataops.run_state_scraper -- state_key=aguascalientes` |
| **hidalgo** | 🆕 **PENDING FIRST RUN** | 250–300 (estimated) | URL: `congreso-hidalgo.gob.mx`. First-run: `enclii jobs run dataops.run_state_scraper -- state_key=hidalgo` |
| **morelos** | 🆕 **PENDING FIRST RUN** | 150–200 (estimated) | URL: `congresomorelos.gob.mx`. First-run: `enclii jobs run dataops.run_state_scraper -- state_key=morelos` |
| **yucatan** | 🆕 **PENDING FIRST RUN** | 250–300 (estimated) | URL: `congresoyucatan.gob.mx`. First-run: `enclii jobs run dataops.run_state_scraper -- state_key=yucatan` |
| campeche | ⏳ Wave 1B | TBD | not yet implemented |
| chiapas | ⏳ Wave 1B | TBD | not yet implemented |
| chihuahua | ⏳ Wave 1B | TBD | not yet implemented |
| coahuila | ⏳ Wave 1B | TBD | not yet implemented |
| colima | ⏳ Wave 1B | TBD | not yet implemented |
| guanajuato | ⏳ Wave 1B | TBD | not yet implemented |
| jalisco | ⏳ Wave 1B | TBD | not yet implemented |
| puebla | ⏳ Wave 1B | TBD | not yet implemented |
| sinaloa | ⏳ Wave 1B | TBD | not yet implemented |
| sonora | ⏳ Wave 1B | TBD | not yet implemented |
| tamaulipas | ⏳ Wave 1B | TBD | not yet implemented |
| veracruz | ⏳ Wave 1B | TBD | not yet implemented |
| oaxaca | ⏳ Wave 1C | TBD | known WAF/JS-heavy |
| puebla | ⏳ Wave 1C | TBD | known WAF |
| nayarit | ⏳ Wave 1C | TBD | known WAF |
| tabasco | ⏳ Wave 1C | TBD | known WAF |
| tlaxcala | ⏳ Wave 1C | TBD | known WAF |
| baja_california_sur | ⏳ Wave 1C | TBD | known WAF |
| queretaro | ⏳ Wave 1C | TBD | known WAF |

---

## Per-scraper template for new additions

Copy this template into the table above when a Wave 1B/1C state ships:

```markdown
| **<state_key>** | 🆕 **PENDING FIRST RUN** | <low>–<high> (estimated from catalog page count) | URL: `<congress URL>`. First-run: `enclii jobs run dataops.run_state_scraper -- state_key=<state_key>` |
```

Once the first run completes:

- Update Status to ✅ live
- Replace estimated count with actual `len(catalog)` from the AcquisitionLog row
- Add a per-state Beat schedule entry to `apps/indigo/settings.py` `CELERY_BEAT_SCHEDULE` (suggested cadence: monthly, 03:00 UTC, varied day-of-month per state to avoid thundering herd)

---

## Failure-mode protocol

If a first-run finds 0 laws or returns an error:

1. **Don't auto-disable.** A flaky portal is different from a broken scraper. Leave the scraper registered.
2. **Capture the AcquisitionLog row's `error_summary`** (truncated to 2000 chars per `MAX_ERROR_LENGTH`).
3. **Run twice more** at 1-hour intervals to rule out transient issues.
4. If 3 consecutive failures: file an issue against the scraper (`tezca` repo), tag `bug:scraper:<state>`. Include the error_summary, the URLs attempted (primary + alternates), and any 4xx/5xx response codes captured.
5. **Don't flip the coverage tile.** The state stays "🆕 pending" until a real run succeeds.

The `check-scraper-health-daily` Beat task (08:00 UTC) catches scrapers with 3+ failures in the last 7 days and emits WARN logs — it should also catch these.

---

## Synthetic monitoring (post-Wave 1B)

Once 24/32 states have first-run-validated scrapers, set up Grafana panels per RFC 0012-style runbook:

- **Per-state catalog freshness:** alert if `AcquisitionLog.started_at` for `state_scraper_<key>` is >2× the configured Beat interval old (using `_EXPECTED_INTERVALS` map in `tasks.py`).
- **Catalog size drift:** alert if `found` count drops >50% week-over-week (signals a portal layout change that broke scraping).
- **Error rate:** alert if `error_summary` is non-empty for ≥3 of the last 7 daily runs.

Implement in Workstream 8 of the A+ plan.

---

## Related

- [`A_PLUS_REMEDIATION_PLAN_2026-04-27.md`](../strategy/A_PLUS_REMEDIATION_PLAN_2026-04-27.md) — workstream 6 (production-path validation)
- [`STATE_LAW_SCRAPING_REPORT.md`](./STATE_LAW_SCRAPING_REPORT.md) — historical state-scraping notes
- `apps/scraper/scheduling/tasks.py` — `run_state_scraper` dispatch table
- `apps/scraper/dataops/health_monitor.py` — staleness detection logic
- `apps/api/management/commands/verify_dof_health.py` — sister command for DOF freshness
