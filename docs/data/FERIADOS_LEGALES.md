# Feriados legales — corpus + dates feed

Mexico's legal non-working days, captured as a machine-readable dates artifact
for **kalya**, the sibling of the SEP school calendar (`SEP_CALENDARIO_ESCOLAR.md`).
Two layers, two provenances — the discipline the fiscal/labor feeds use
(`apps.api.fiscal_models.Provenance`):

- **`descanso_obligatorio`** — LFT Artículo 74 días de descanso obligatorio.
  **Computed** from the statute, whose text tezca already serves (`lft.json`):
  fixed dates and the *primer/tercer lunes* rules leave no ambiguity, so every
  one is `published` — it *is* the law. Banks close on all of them, so each also
  carries the `banking` domain.
- **`inhabil_bancario`** — CNBV días inhábiles bancarios beyond Art. 74 (Jueves
  y Viernes Santo, 2 nov, 12 dic). Set by the CNBV's **annual DOF publication**,
  not a perpetual rule, so **read from the ingested disposición and pinned per
  year**, exactly like the SEP dates are read from the acuerdo.

Producer: `apps.scraper.federal.feriados_legales`. Vocabulary:
`apps.scraper.federal.legal_date_taxonomy`.

---

## The tagging vocabulary (`legal_date_taxonomy.py`)

Every dated legal fact carries two axes, both a **closed, documented
vocabulary** so a consumer selects «the banking dates» or «the fiscal inhábiles»
by a stable tag, and a new source (SAT, the Poder Judicial, an electoral decree)
slots in by adding a member, never by inventing a string.

- **`domains`** — which SECTOR observes the date. English codes, aligned with the
  corpus `DOMAIN_MAP` (`apps/api/constants.py`). A date carries the domain of
  EVERY source that lists it: a día de descanso obligatorio is `labor` by the LFT
  AND `banking` when the CNBV lists it — the union, not one home.

  | domain | source |
  |---|---|
  | `labor` | LFT Art. 74 — días de descanso obligatorio |
  | `banking` | CNBV — días inhábiles de las instituciones de crédito |
  | `fiscal` | SAT / CFF Art. 12 — días inhábiles para plazos fiscales |
  | `education` | SEP — calendario escolar (the SEP feed) |
  | `civic` | conmemoraciones cívicas sin descanso |
  | `judicial` | Poder Judicial — suspensión de plazos |
  | `electoral` | INE / decretos — jornadas electorales |
  | `public_sector` | LFTSE / calendarios oficiales |

  Only `labor` + `banking` are populated today (`education` via the SEP feed);
  the rest exist so a future feed tags itself against a member that is already
  there.

- **`tipo`** — the KIND of dated fact (the legal-instrument name, Spanish). Each
  has one PRIMARY domain (`LEGAL_DATE_TIPO_PRIMARY_DOMAIN`, total over the tipos):
  `descanso_obligatorio` (labor), `inhabil_bancario` (banking), `inhabil_fiscal`
  (fiscal), `suspension_escolar`/`periodo_vacacional` (education), `dia_civico`
  (civic), `inhabil_judicial` (judicial), `jornada_electoral` (electoral).

`FeriadoFact.__post_init__` validates its `tipo` and `domains` against the
vocabulary — an off-vocabulary tag is refused at the source and never reaches an
artifact a consumer then cannot select on.

---

## The source documents (`FERIADOS_DOCUMENTS`)

The bank dates are **read from the legal sources tezca ingests**, not hand-typed.
Each year's CNBV disposición is a corpus document, registered by
`manage.py ingest_feriados` as a `Law` + `LawVersion`
(`law_type="non_legislative"`, `category="dias_inhabiles_bancarios"`,
`domains=["banking"]`, `tier="federal"`), so
`GET /api/v1/laws/<official_id>/` resolves and each bank date cites
`corpus <official_id>`. Like SEP, the registry is a small enumerated set of
pinned DOF `codigo` values — the registry IS the source of truth.

Ciclo 2026 (verified against primary DOF on 2026-09-18):

| Field | Value |
|---|---|
| official_id | `cnbv-dias-inhabiles-bancarios-2026` |
| Instrumento | Disposiciones … días del año 2026 en que las instituciones de crédito deberán cerrar sus puertas (Art. 1) |
| DOF código | **5775684** |
| DOF fecha | **2025-12-10** |

The 2026 set (LFT ∪ CNBV additions), verbatim from Art. 1: 1 ene, 1er lun feb,
3er lun mar, **2 y 3 abr**, 1 may, 16 sep, **2 nov**, 3er lun nov, **12** y 25
dic — eleven days. (A secondary web summary claimed «5 de mayo»; the DOF Art. 1
does **not** list it. Verify against the DOF primary, never a web summary.)

**NOT computed** (LFT Art. 74 fr. IX): the jornada electoral — fixed by each
year's electoral decree, not a perpetual rule; a pinned add when it applies.

---

## The dates artifact (kalya's input contract)

**Producer:** `apps.scraper.federal.feriados_legales.extract_feriados(year)`.
**Schema id:** `tezca.feriados_legales/v1`.

```jsonc
{
  "schema": "tezca.feriados_legales/v1",
  "anio": 2026,
  "bancario_verificado": true,        // are the bank additions read from a pinned DOF disposición?
  "source": {
    "descanso_obligatorio": { "instrumento": "Ley Federal del Trabajo, Artículo 74", "provenance": "published" },
    "inhabil_bancario": {            // the ingested corpus document, when a year is pinned
      "instrumento": "…", "corpus_official_id": "cnbv-dias-inhabiles-bancarios-2026",
      "dof_codigo": "5775684", "dof_fecha": "2025-12-10", "provenance": "published"
    }
  },
  "events": [
    { "date": "2026-01-01", "tipo": "descanso_obligatorio", "domains": ["labor", "banking"],
      "title": "Año Nuevo", "fundamento": "LFT Art. 74 fr. I", "provenance": "published" },
    { "date": "2026-04-02", "tipo": "inhabil_bancario", "domains": ["banking"],
      "title": "Jueves Santo", "fundamento": "CNBV días inhábiles 2026 — DOF 5775684 (2025-12-10), Art. 1 · corpus cnbv-dias-inhabiles-bancarios-2026", "provenance": "published" }
    // …
  ]
}
```

Legal feriados are **single days** — no `end_date` ever appears. Events are
ordered by date.

### Provenance gates client-visibility

A year with a registered disposición is `published`; a year without one falls
back to a **computed default** (Semana Santa via Easter + 2 nov + 12 dic),
`seed-unverified`. `is_bancario_verified(year)` / the artifact's
`bancario_verificado` flag is the gate a downstream consumer that must be exact
(nauta's estado de cuenta payment vence) reads before it trusts a bank date — so
an unverified date never calls a client late a día feriado early.

---

## kalya consumption

kalya ingests this artifact as a second tagged grouping beside SEP
(`applyLegalFeriadosDates`, migration 0016): a calendar-year container
(`ciclo="YYYY"`), the `feriado_ley_federal` / `feriado_bancario` event types
(deliberately NOT availability-closures — a bank holiday does not close the
school), converging on `sourceTag = feriados-YYYY`. nauta reads the `banking`
grouping from kalya's public org-calendar feed for the exact payment vence.

---

## Year-over-year refresh

Each December the CNBV publishes the next year's disposición in the DOF. The loop
mirrors SEP's: **operator adds the pinned `FeriadosDocument` for the new year (a
verified DOF `codigo`) + the `_CNBV_ADICIONALES` dates read from its Artículo 1 →
`manage.py ingest_feriados` → re-vendor the artifact into kalya**. A year not yet
pinned stays honestly `seed-unverified` and out of any client-facing vence.
