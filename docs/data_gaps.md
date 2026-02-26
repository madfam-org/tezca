# Tezca Data Gaps Registry

Last updated: 2026-02-26

## Current State

| Tier | Source | In DB | Known Universe | Gap |
|------|--------|------:|---------------:|----:|
| Federal Laws | Leyes Vigentes | 336 | 336 | 0 |
| Federal Reglamentos | Camara de Diputados | 150 | 150 | 0 |
| Federal NOMs | DOF / CONAMER | 0 | ~4,000 | ~4,000 |
| Federal CONAMER CNARTyS | catalogonacional.gob.mx (successor) | 0 | 150,000+ | 150,000+ |
| Federal Treaties | SRE | 0 | ~1,500 | ~1,500 |
| Judicial Jurisprudencia | SCJN | 0 | ~60,000 | ~60,000 |
| Judicial Tesis Aisladas | SCJN | 0 | ~440,000 | ~440,000 |
| State Legislative | OJN poder=2 | 12,465 | 12,120 | 782 dead links |
| State Non-Legislative | OJN poderes 1/3/4 | 18,439 | 23,660 | 4,438 permanent |
| Municipal | City portals | ~208 | Unknown | Unknown |

**Total laws in database**: ~31,598 (336 federal + 150 reglamentos + 12,465 state legislative + 18,439 state non-legislative + ~208 municipal).

**Pending ingest** (scraped but not yet in DB): ~3,379 files (BC 483 + DGO 305 + QR 316 + municipal 2,195 + NOMs 80).

---

## Per-Source Gap Analysis

### Federal

#### 1. Leyes Vigentes

| Field | Value |
|-------|-------|
| Institution | Camara de Diputados |
| URL | https://www.diputados.gob.mx/LeyesBiblio/ |
| Expected | 336 |
| Current | 336 |
| Gap | 0 |
| Status | **Complete** |
| Freshness SLA | Weekly (DOF daily check via Celery Beat) |

No action required. DOF daily task (`dof-daily-check`) runs at 7 AM to detect new publications.

#### 2. Reglamentos

| Field | Value |
|-------|-------|
| Institution | Camara de Diputados |
| URL | https://www.diputados.gob.mx/LeyesBiblio/regla.htm |
| Expected | 150 |
| Current | 150 |
| Gap | 0 |
| Status | **Complete** |
| Freshness SLA | Monthly (spider re-crawl) |

All 150 federal reglamentos scraped and ingested as of 2026-02-07.

#### 3. NOMs (Normas Oficiales Mexicanas)

| Field | Value |
|-------|-------|
| Institution | CONAMER / DOF |
| URL | https://www.gob.mx/conamer |
| Expected | ~4,000 across all secretarias |
| Current | 80 cataloged, 0 ingested |
| Gap | ~3,920 |
| Status | `downloaded_pending_ingest` |
| Freshness SLA | Quarterly |

**Recovery strategy:**

1. Ingest the 80 cataloged NOMs from DOF search results.
2. Expand DOF search to cover additional secretarias and date ranges.
3. Cross-reference with CONAMER catalog if it comes back online.

**Key files:**
- Scraper: `apps/scraper/federal/nom_scraper.py`
- DOF search form fields: `textobusqueda` (not `busqueda`), `vienede=header`, `s=s`
- Parser selector: `td.txt_azul`
- SSL: `verify=False` required for DOF

#### 4. CONAMER CNARTyS

| Field | Value |
|-------|-------|
| Institution | CONAMER (now under ATDT) |
| Original URL | https://cnartys.conamer.gob.mx/ (DNS-dead) |
| Successor URL | https://catalogonacional.gob.mx |
| Expected | 150,000+ |
| Current | 0 |
| Gap | 150,000+ |
| Status | `successor_found_blocked` |
| Freshness SLA | Quarterly |

**Original portal DNS-dead since ~2025.** CONAMER was dissolved; regulatory functions transferred to ATDT. The CNARTyS catalog migrated to `catalogonacional.gob.mx`.

**Successor portal status (2026-02-26):**
- `catalogonacional.gob.mx` — returns HTTP 403 to automated requests (WAF/Cloudflare protection). Needs browser-based scraping.
- `conamer.gob.mx/cnartys-t/Login` — expired SSL certificate.
- `www.gob.mx/conamer` — institutional page, no link to regulation catalog.

**Recovery strategy:**

1. Browser-based scraping of `catalogonacional.gob.mx` (Playwright or Selenium).
2. Investigate if the portal exposes an API behind authentication.
3. Dedup against existing corpus (significant overlap expected with reglamentos + state non-legislative).
4. File INAI transparency request for bulk data export.

**Key file:** `apps/scraper/federal/conamer_scraper.py` (updated with successor URLs)

#### 5. International Treaties (SRE)

| Field | Value |
|-------|-------|
| Institution | Secretaría de Relaciones Exteriores |
| Original URL | https://tratados.sre.gob.mx/ (DNS-dead) |
| Successor URL | https://cja.sre.gob.mx/tratadosmexico/ |
| Expected | 1,509 |
| Current | 0 |
| Gap | 1,509 |
| Status | `successor_found_ready` |
| Freshness SLA | Annual |

**Original portal DNS-dead since ~2025.** The SRE migrated the treaty database to `cja.sre.gob.mx/tratadosmexico/` (Biblioteca Virtual de Tratados Internacionales).

**Successor portal status (2026-02-26):**
- `cja.sre.gob.mx/tratadosmexico/buscador` — **live and working**. Server-rendered HTML, paginated (?page=N), 151 pages, 1,509 treaties. Scraper tested successfully (20 treaties from 2 pages, correct bilateral/multilateral classification, Spanish date parsing).
- Search filters: category, theme, country, organization, keywords.
- Alternative sources: `aplicaciones.sre.gob.mx/tratados/depositario.php`, Senado treaty database.

**Recovery strategy:**

1. Run full treaty scraper: `python -m apps.scraper.federal.treaty_scraper` (~151 pages, ~25 min at 1 req/sec).
2. Optionally fetch detail pages: `--fetch-details` for full text and PDF links.
3. Cross-reference with UN Treaty Collection for multilateral treaties.
4. Cross-reference with Senate approved treaties database.

**Key file:** `apps/scraper/federal/treaty_scraper.py` (updated with successor URLs, Spanish date parsing)

#### 6. SCJN Judicial Corpus

| Field | Value |
|-------|-------|
| Institution | Suprema Corte de Justicia de la Nacion |
| URL | https://sjf.scjn.gob.mx/ |
| Expected | ~60,000 jurisprudencia + ~440,000 tesis aisladas |
| Current | 0 |
| Gap | ~500,000 |
| Status | `partnership_outreach` |
| Freshness SLA | Monthly (once ingested) |

**Recovery strategy:**

1. Continue partnership outreach to SCJN Coordinacion de Compilacion.
2. If partnership stalls, deploy fallback scraper (`apps/scraper/judicial/scjn_scraper.py`).
3. Bulk import format: SCJN provides XML/JSON dumps on request for institutional partners.

---

### State

#### 1. State Legislative (OJN poder=2)

| Field | Value |
|-------|-------|
| Institution | OJN (Orden Juridico Nacional) |
| URL | https://compilacion.ordenjuridico.gob.mx/ |
| Expected | 12,120 |
| Current (DB) | 12,465 |
| Permanent dead links | 782 |
| Status | Partially complete; 3 states scraped from portals, pending ingest |
| Freshness SLA | Monthly (OJN re-scrape) |

The current DB count (12,465) exceeds the OJN known count (12,120) because state portal scrapers recovered laws that OJN lacked.

**State portal scraper results (pending ingest):**

| State | OJN Count | Portal Count | Files Downloaded | Status |
|-------|----------:|-----------:|--------:|--------|
| Baja California | 3 | ~340 | 483 | `scraped_pending_ingest` |
| Durango | 1 | ~160 | 305 | `scraped_pending_ingest` |
| Quintana Roo | 1 | ~356 | 316 | `scraped_pending_ingest` |
| Hidalgo | 38 | ~740 | N/A | `mostly_covered` (740+ already in DB) |

**Permanent dead links by state (top contributors):**
- Michoacan: 504
- Estado de Mexico: 141
- San Luis Potosi: 47
- Others: < 30 each

**Recovery strategy for pending ingest:**

1. Verify metadata JSON files exist for each state (`data/state_laws/{state}/`).
2. Parse PDFs through `StateLawParser`.
3. Batch insert to PostgreSQL.
4. Index articles to Elasticsearch.
5. Update `universe_registry.json` counts.

**Key files:**
- State scraper base: `apps/scraper/state/base.py`
- BC scraper: `apps/scraper/state/baja_california.py`
- DGO scraper: `apps/scraper/state/durango.py`
- QR scraper: `apps/scraper/state/quintana_roo.py`
- Glue script: `scripts/scraping/scrape_and_prepare.py`

#### 2. State Non-Legislative (OJN poderes 1/3/4)

| Field | Value |
|-------|-------|
| Institution | OJN |
| URL | https://compilacion.ordenjuridico.gob.mx/ |
| Expected | 23,660 |
| Current | 18,439 |
| Permanent gaps | 4,438 |
| Corrupt PDFs | ~165 (unrecoverable) |
| Status | Stable |
| Freshness SLA | Quarterly (OJN re-scrape) |

**Permanent failure breakdown:**
- Michoacan: ~2,291
- San Luis Potosi: ~700
- Estado de Mexico: ~600
- Baja California: ~200
- 3 states returned 0 laws: CDMX, Durango, Zacatecas

**OCR recovery results (2026-02-25):**
- First pass: 1,847/3,018 succeeded.
- Second pass (tessdata fix): ~1,006 additional recoveries.
- Remaining: ~165 corrupt PDFs with no valid PDF structure. These are unrecoverable.

Parse success rate: 99.9% (18,416/18,439).

---

### Municipal

#### 1. Current Database

| Field | Value |
|-------|-------|
| Source | Municipal government portals |
| Current (DB) | ~208 |
| Cities covered | 5 (CDMX, Guadalajara, Monterrey, Puebla, Leon) |
| Total municipalities in Mexico | 2,468 |
| Known universe | Unknown (no authoritative census exists) |
| Freshness SLA | Quarterly (portal re-scrape) |

#### 2. Scraped, Pending Ingest

| City | Files Downloaded | Status |
|------|--------:|--------|
| Guadalajara | 186 | `scraped_pending_ingest` |
| Monterrey | 307 | `scraped_pending_ingest` |
| Leon | 1,693 | `scraped_pending_ingest` |
| Zapopan | 9 | `scraped_pending_ingest` |
| **Total** | **2,195** | 4.5 GB on disk |

#### 3. Blocked or Not Attempted

| City | Status | Blocker |
|------|--------|---------|
| Merida | Blocked | Radware captcha after initial probe (531 items found) |
| Tijuana | Not attempted | No scraper built |
| Ciudad Juarez | Not attempted | No scraper built |
| Cancun | Not attempted | No scraper built |

**Recovery strategy for pending ingest:**

1. Verify metadata JSONs exist per city (`data/municipal/{city}/`).
2. Parse PDFs through `StateLawParser`.
3. Batch insert to PostgreSQL.
4. Index articles to Elasticsearch.
5. Update `universe_registry.json` counts.

**Key files:**
- Municipal scraper: `scripts/scraping/scrape_municipal.py`
- Generic scraper: `apps/scraper/municipal/generic.py`
- Probe script: `scripts/scraping/probe_all.py`

---

## Recovery Playbooks

### Playbook 1: Decommissioned Sources (CONAMER, Treaties)

Both original portals are DNS-dead. Successor portals have been identified (2026-02-26):

**Treaties (READY TO RUN):**
- Successor: `cja.sre.gob.mx/tratadosmexico/buscador` (live, 1,509 treaties)
- Run: `python -m apps.scraper.federal.treaty_scraper`
- Scraper tested and working. Spanish date parsing included.

**CONAMER (BLOCKED — needs browser scraping):**
- Successor: `catalogonacional.gob.mx` (150K+ regulations)
- Portal returns HTTP 403 to automated HTTP requests (WAF protection).
- Next steps: (1) Browser-based scraping with Playwright/Selenium, or (2) INAI transparency request for bulk data.
- Dedup required against existing corpus (reglamentos + state non-legislative overlap expected).

**Probe script:** `scripts/scraping/probe_dead_sources.py` (updated with confirmed successor URLs)

### Playbook 2: Pending Ingestion Pipeline

For municipal, state portal, and NOM files already on disk:

1. **Verify metadata**: Confirm JSON metadata files exist alongside each PDF.
2. **Parse**: Run PDFs through `StateLawParser` (with OCR fallback for scanned documents).
3. **Deduplicate**: Check against existing DB entries by name, state, and DOF date.
4. **Insert**: Batch insert to PostgreSQL via Django ORM.
5. **Index**: Index articles to Elasticsearch.
6. **Update registry**: Update `data/universe_registry.json` with new counts.
7. **Validate**: Run `apps/api/management/commands/` verification commands.

### Playbook 3: State Low-Count Recovery

For states where OJN severely undercounts:

1. **Identify**: Check `LOW_COUNT_STATES` and `STATE_PORTAL_INVESTIGATION` in `gap_registry.py`.
2. **Build scraper**: Use `apps/scraper/state/base.py` as the base class.
3. **Download**: Run scraper against state congress portal.
4. **Prepare**: Generate metadata JSON via `scripts/scraping/scrape_and_prepare.py`.
5. **Ingest**: Follow Playbook 2 steps 2-7.

Current state: BC, DGO, and QR scrapers complete. Files downloaded, pending ingest. Hidalgo mostly covered (740+ in DB).

### Playbook 4: Captcha-Blocked Sites

For municipal portals with bot protection (Merida):

1. **Manual session**: Open browser, solve captcha, export cookies.
2. **Cookie replay**: Inject session cookies into scraper for time-limited access.
3. **Rate limiting**: Reduce request rate to 1 per 5 seconds.
4. **Headless browser**: Use Playwright for JavaScript-rendered portals.
5. **Alternative**: Check if the municipality publishes a PDF compilation or open data portal.

---

## Freshness SLAs

| Source | SLA | Method | Automation |
|--------|-----|--------|------------|
| Federal Laws | Weekly | DOF daily check | Celery Beat (`dof-daily-check`, 7 AM) |
| Federal Reglamentos | Monthly | Spider re-crawl | Manual trigger |
| Federal NOMs | Quarterly | DOF search | Manual trigger |
| State Legislative | Monthly | OJN re-scrape | Manual trigger |
| State Non-Legislative | Quarterly | OJN re-scrape | Manual trigger |
| Municipal | Quarterly | Portal re-scrape | Manual trigger |
| SCJN Judicial | Monthly | Partnership sync or scraper | Not yet automated |
| CONAMER | Quarterly | Successor found (WAF-blocked) | Browser scraping needed |
| Treaties | Annual | Successor found (ready) | Run scraper |

---

## Data Quality Notes

- **OCR pipeline**: Recovers ~95% of previously failed PDFs (pytesseract + pdf2image).
- **Corrupt PDFs**: ~165 files have no valid PDF structure and are unrecoverable.
- **State non-legislative parse rate**: 99.9% (18,416/18,439).
- **State legislative**: 782 permanent dead links on OJN; no recovery path for these specific URLs.
- **Deduplication**: CONAMER's 150K+ count likely overlaps with federal reglamentos and NOMs. Dedup required before ingestion.
- **Elasticsearch totals**: 3,480,563 articles indexed across 40,539 laws (as of 2026-02-07 full re-index).

---

## Related Files

| File | Purpose |
|------|---------|
| `data/universe_registry.json` | Canonical source counts and coverage metrics |
| `apps/scraper/dataops/gap_registry.py` | Programmatic gap tracking (Django models + constants) |
| `apps/scraper/dataops/models.py` | `DataSource` and `GapRecord` Django models |
| `scripts/scraping/scrape_and_prepare.py` | State scraper glue to OJN pipeline |
| `scripts/scraping/scrape_municipal.py` | Municipal download + metadata generation |
| `scripts/scraping/probe_all.py` | Catalog probes for all municipal + federal scrapers |
| `apps/scraper/state/base.py` | State congress scraper base class |
| `apps/scraper/federal/nom_scraper.py` | DOF NOM scraper |
| `apps/scraper/federal/conamer_scraper.py` | CONAMER scraper (successor: catalogonacional.gob.mx, WAF-blocked) |
| `apps/scraper/federal/treaty_scraper.py` | SRE treaty scraper (successor: cja.sre.gob.mx, working) |
| `scripts/scraping/probe_dead_sources.py` | DNS/HTTP/Wayback probe for decommissioned sources |
| `apps/scraper/judicial/scjn_scraper.py` | SCJN fallback scraper |
