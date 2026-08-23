# SEP Calendario Escolar — corpus + dates feed

Each school year the Secretaría de Educación Pública (SEP) fixes the
**calendario escolar para la educación básica** and publishes it in the DOF
as an *acuerdo*. Tezca is the MADFAM ecosystem's Mexican-law oracle, so it is
where that yearly calendar is captured — both as a corpus document (the legal
instrument) and as a machine-readable dates artifact that **kalya**'s
organizational-calendar generator consumes to draft each tenant's ciclo (see
`internal-devops/docs/clients/2026-08-22-ctm-calendario-anual-spec.md`).

This doc is the contract for that dates artifact and the description of the
**year-over-year watch** that flags next year's acuerdo when it is published.

---

## The instrument (ciclo 2026-2027)

| Field | Value |
|---|---|
| Acuerdo | **07/07/26** |
| Título | ACUERDO número 07/07/26 por el que se establecen los calendarios escolares para el ciclo lectivo 2026-2027, aplicables en toda la República para la educación preescolar, primaria, secundaria, normal y demás para la formación de maestras y maestros de educación básica |
| Emisor | Secretaría de Educación Pública (Mario Delgado Carrillo) |
| DOF código | **5793645** |
| DOF fecha | **2026-07-15** (edición matutina) |
| DOF URL | https://dof.gob.mx/nota_detalle.php?codigo=5793645&fecha=15/07/2026 |
| SIDOF URL | https://sidof.segob.gob.mx/notas/docFuente/5793645 |
| Vigor | día siguiente a publicación (2026-07-16), Transitorio Primero |
| Abroga | Acuerdo 18/06/25 (calendario 2025-2026, DOF 2025-06-09) |

Modeled in the corpus as `law_type="non_legislative"`,
`category="calendario_escolar"`, `domains=["education"]`, `tier="federal"` —
the same discipline the JCF Reglas de Operación use (an administrative
instrument, **not** a `ley`). `official_id = sep-calendario-escolar-2026-2027`.

### What the *prose* fixes vs. what the *annex* fixes

The acuerdo's operative body has only **three articles**:

- **ARTÍCULO PRIMERO** — 185 días for educación básica (preescolar, primaria,
  secundaria).
- **ARTÍCULO SEGUNDO** — 190 días for educación normal.
- **ARTÍCULO TERCERO** — inicio de cursos **lunes 31 de agosto de 2026**;
  conclusión **viernes 9 de julio de 2027** (básica) / **martes 13 de julio
  de 2027** (normal).

The day-level **suspensiones, periodos vacacionales, and sesiones de Consejo
Técnico Escolar** are **not** in the articulado. They are published only as a
**rasterized DGPPyEE calendar grid** annexed inside the DOF note (the two PNG
images `sep_1_Cimg_0.png` = básica, `sep_1_Cimg_225832.png` = normal). Those
images are archived at
`data/sep_calendario/sep-calendario-2026-2027-basica-annex.png` (and
`...-normal-annex.png`).

Because a rasterized grid has no deterministic machine-readable form, the
day-level dates are **read cell-by-cell from the annex and pinned** in
`apps/scraper/federal/sep_calendario_scraper.py` (`SEP_CALENDAR_DATES`),
**not OCR'd at runtime** — an image the corpus cannot re-parse deterministically
must never silently drift the dates kalya subtracts from availability. Every
pinned date carries a `source_ref` tracing it to an article of the prose or
the annex grid + its legend. They were verified on **2026-08-22** against the
annex, SEP's own summary (educacionbasica.sep.gob.mx), and the client's
independently-printed calendar.

---

## The dates artifact (kalya's input contract)

**Path:** `data/sep_calendario/dates-<ciclo>.json` (e.g. `dates-2026-2027.json`).
**Producer:** `apps.scraper.federal.sep_calendario_scraper.extract_calendar_dates(ciclo)`
— re-run any time via `python -m apps.scraper.federal.sep_calendario_scraper`.
**Schema id:** `tezca.sep_calendario/v1`.

```jsonc
{
  "schema": "tezca.sep_calendario/v1",
  "ciclo": "2026-2027",          // consecutive years — kalya's OrganizationalCalendar.ciclo
  "nivel": "educacion_basica",
  "dias_habiles": 185,
  "source": {                    // the acuerdo this was extracted from
    "instrumento": "ACUERDO número 07/07/26 …",
    "acuerdo": "07/07/26",
    "dof_codigo": "5793645",
    "dof_fecha_publicacion": "2026-07-15",
    "dof_url": "https://dof.gob.mx/nota_detalle.php?codigo=5793645&fecha=15/07/2026",
    "sidof_url": "https://sidof.segob.gob.mx/notas/docFuente/5793645",
    "emisor": "Secretaría de Educación Pública",
    "vigente_desde": "2026-07-16"
  },
  "extraction": {                // provenance of the day-level reading
    "verified_on": "2026-08-22",
    "method": "cell-by-cell read of the DOF annex grid image, …",
    "annex_image": "data/sep_calendario/sep-calendario-2026-2027-basica-annex.png"
  },
  "events": [                    // flat list, ordered by date
    {
      "date": "2026-08-31",      // ISO local date (inclusive range start)
      "end_date": "2026-09-04",  // OPTIONAL: inclusive range end; absent = single day
      "type": "regreso_a_clases",// kalya CalendarEvent taxonomy (below)
      "title": "Inicio de cursos …",
      "source": "sep",           // always "sep" in this artifact
      "source_ref": "acuerdo 07/07/26, ARTÍCULO TERCERO"  // traceability
    }
    // …
  ]
}
```

### `type` values emitted

The artifact uses kalya's `CalendarEvent` taxonomy. This SEP feed emits only
the SEP-sourced subset (kalya's `rule`/`manual` events are produced on the
kalya side, not here):

| `type` | Cardinality | Meaning |
|---|---|---|
| `regreso_a_clases` | single | Inicio de cursos (ciclo start). |
| `cierre_ciclo_preescolar` | single | Conclusión de cursos (ciclo end, básica). |
| `suspension_sep` | single | Suspensión de labores docentes (black-circle days). |
| `periodo_vacacional` | range | Vacaciones (winter, spring) — inclusive `date`..`end_date`. |
| `junta_consejo_tecnico` | single or range | Consejo Técnico Escolar: 8 sesiones ordinarias (single) + fase intensiva (range). |

Mapping into kalya: each artifact `event` becomes one `CalendarEvent` with
`source = "sep"`, `date`/`endDate` copied through, and `type`/`title` as
given. `source_ref` maps to `CalendarEvent.notes`. Every SEP-sourced closure
(`suspension_sep`, `periodo_vacacional`) subtracts from derived availability
when the `OrganizationalCalendar.affectsAvailability` flag is set. The generator
consumes the artifact for the matching `ciclo`; kalya adds its recurring-rule
and manual events on top.

### The ciclo 2026-2027 events (22 total)

- **regreso_a_clases:** 2026-08-31
- **cierre_ciclo_preescolar:** 2027-07-09
- **suspension_sep (9):** 2026-09-16, 2026-11-02, 2026-11-16, 2026-12-25,
  2027-01-01, 2027-01-06, 2027-02-01, 2027-03-15, 2027-05-05
- **periodo_vacacional (2):** 2026-12-21 → 2027-01-05 (invierno, regreso
  2027-01-07); 2027-03-22 → 2027-04-03 (primavera, regreso 2027-04-05)
- **junta_consejo_tecnico:** fase intensiva 2026-08-24 → 2026-08-28; ordinarias
  2026-09-25, 2026-10-30, 2026-11-27, 2027-01-29, 2027-02-26, 2027-04-30,
  2027-05-28, 2027-06-25

#### Modeling note — winter break vs. holiday singles

SEP's annex renders the winter break as **grey "vacaciones" spans**
(Dic 21–24, Dic 28–31, Ene 4–5) punctuated by **black "suspensión" holidays**
(Dic 25 Navidad, Ene 1 Año Nuevo, Ene 6 Reyes). The artifact models the
`periodo_vacacional` as the **inclusive envelope SEP publishes in its summary**
(Dic 21 2026 – Ene 5 2027, regreso Ene 7), and **also** emits the three holiday
`suspension_sep` singles. This is deliberate and safe both ways: a consumer that
reads only `periodo_vacacional` still closes the whole span; one that reads both
sees SEP's own day typing. The holiday singles fall inside/adjacent to the
envelope, so availability subtraction (which unions closures) is unaffected by
the overlap.

---

## Divergences vs. the client's printed calendar

The CTM spec's seed is the client's **private preschool program calendar**,
which the client *derived from* SEP's — divergences are expected and fine;
tezca sources the **SEP layer only**. Checked against the SEP básica calendar:

| Item | SEP 2026-2027 (this feed) | Client printed | Verdict |
|---|---|---|---|
| Suspensiones Sep 16 / Nov 2 / Nov 16 / Feb 1 / Mar 15 / May 5 | all present | all present | **match** |
| Winter vacation | Dic 21 – Ene 5 (regreso Ene 7) | "Dic 21 – Ene 6" | client extends ~1 day (Ene 6 is a SEP *suspensión*, inside client's range) — **expected** |
| Spring vacation | Mar 22 – Abr 3 (regreso Abr 5) | "Mar 22 – Abr 4" | client extends ~1 day — **expected** |
| Consejo Técnico (last-Fridays) | 8 SEP-fixed dates: Sep 25, Oct 30, Nov 27, Ene 29, Feb 26, Abr 30, May 28, Jun 25 | same eight dates + the client's own preschool CTE rule extending into Jun/Jul | **the eight overlap exactly**; client adds its own beyond the SEP básica set — **expected** |
| Dic 25 / Ene 1 / Ene 6 suspensión singles | present | absent (fall inside client's vacation block) | **expected** (client folds them into its range) |
| Ciclo start / end | 31-ago-2026 / 9-jul-2027 (básica) | client preschool uses its own cierre (8-jul-2027) + Jul vacaciones | **expected** (private program) |

No divergence indicates a SEP-layer error: every SEP-sourced date the client's
calendar also carries matches, and every difference is the client's private
program layered on top — exactly the separation the architecture intends.

---

## Year-over-year watch (the trigger)

The loop is: **SEP publishes next ciclo's acuerdo → tezca flags it → an
operator adds the pinned entry + extracts dates → kalya drafts the new ciclo.**
Step 2 is automated by the **corpus watch**
(`apps/scraper/scheduling/corpus_watch.py`).

**Why a dedicated watch and not the generic DOF change detector:** the generic
detector (`DofScraper.detect_law_changes`) filters DOF entries to
`DECRETO`/`LEY`/`REGLAMENTO`/`CÓDIGO`-type titles. An SEP *acuerdo* establishing
a *calendario* matches none of those keywords, so it would slip through
silently — and the loop would never get its trigger.

**How it works:** `CORPUS_WATCHES` is a declarative registry of yearly-reissued
pinned instruments. The `SEP_CALENDARIO_WATCH` entry fires on a DOF entry whose
title matches **both** `calendario` and `ciclo lectivo` **and** whose issuer is
`SECRETARIA DE EDUCACION PUBLICA` (so it catches the yearly calendario acuerdo
but not every SEP acuerdo). `scan_entries(entries)` returns a `WatchHit` for
each match, carrying the operator instruction (`action`).

**Where it runs:**

- **Daily, automatically** — `check_dof_daily` (Celery Beat, 07:00) calls
  `scan_entries` on every DOF edition it fetches. Hits are logged at WARNING
  with their instruction and recorded on the `AcquisitionLog`
  (`parameters.corpus_watch_hits`, and summarized in `error_summary`).
- **On demand** — `python manage.py check_corpus_watches` scans an arbitrary
  date or window (detection only; writes nothing):

  ```bash
  # Back-check the month next year's calendario was expected:
  python manage.py check_corpus_watches --from 2027-05-01 --to 2027-07-31 \
      --watch sep_calendario_escolar
  ```

**On a hit, the operator:**

1. Verifies the new DOF `codigo` against primary text (the fetcher's identity
   guard rejects a mis-pinned one — an opaque codigo can resolve to the wrong
   instrument).
2. Adds a pinned `SepCalendarDocument` for the new ciclo in
   `sep_calendario_scraper.py` and extends `SEP_CALENDAR_DATES` from the new
   annex grid.
3. Runs `python -m apps.scraper.federal.sep_calendario_scraper --download` then
   `python manage.py ingest_sep_calendario` (and `manage.py index_laws`).
4. Notifies kalya so its generator can draft the new ciclo, and marks the prior
   acuerdo `abrogada`.

The watch is **detect-and-notify only**: it never mutates the corpus, because
pinning a codigo is a human decision that the automated path must not make.
`JCF_REGLAS_WATCH` applies the same machinery to the JCF ROP (~December).
