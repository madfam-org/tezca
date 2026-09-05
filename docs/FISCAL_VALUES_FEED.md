# Fiscal Values Feed

Tezca is the MADFAM ecosystem's Mexican-law oracle. Until now it served law
*text*; this feed makes it serve law-derived *values* — so consumers
(`symbiosis-hcm` first, `karafiel` second) never re-implement fiscal-value
lookup or hardcode a UMA in a default argument.

**Base path:** `/api/v1/fiscal/`
**Auth:** API key (`X-API-Key`) or Janua JWT, with the `read` scope — the same
key scheme as `/changelog/` and `/bulk/articles/`. Usage is recorded in
`APIUsageLog` by the global usage-logging middleware.

---

## The honesty contract

This feed's defining property is that **it states how well it knows each
number**. Every row carries a `provenance`:

| `provenance` | `is_verified` | Meaning |
|---|---|---|
| `published` | `true` | Transcribed from the cited DOF publication. Safe to cite. |
| `seed-unverified` | `false` | A well-known published figure, entered so the feed is useful on day one, **not verified against a DOF document by Tezca**. |
| `operator` | `false` | Entered by a staff operator via the admin, e.g. between a DOF publication and the ingestion run. |

Consumers **must not** present a value whose provenance is not `published` as
a compliance assertion. Tezca states what it knows and how well; the caller
decides what to assert. Every response repeats this as a `disclaimer` field.

### Status

The seed (2026-08-22) entered every row as `seed-unverified`: Tezca's law
corpus carries law text, not fiscal values — there is no UMA figure, no
CONASAMI resolution and no LISR Art. 96 bracket table anywhere under `data/`.
So no seed could be derived from the corpus, and none claimed to be.

**2026 has since been verified against the DOF** (2026-09-05) and published.
See [`fiscal/2026-publicacion-dof.md`](fiscal/2026-publicacion-dof.md) for the
full table, the pending items and the operator's deploy checklist.

| Dataset | Coverage | Provenance |
|---|---|---|
| UMA | 2016–2025 | `seed-unverified` |
| UMA | **2026** (117.31 / 3,566.22 / 42,794.64) | **`published`**, DOF 09-01-2026 codigo 5778072 |
| Salario mínimo | 2016–2025 general; 2019–2025 ZLFN | `seed-unverified` |
| Salario mínimo | **2026** general 315.04 · ZLFN 440.87 | **`published`**, DOF 09-12-2025 codigo 5775534 |
| `isr_monthly` | 2025 | `seed-unverified` |
| `isr_monthly` | **2026** (11 tramos) | **`published`**, DOF 28-12-2025 codigo 5777219 |
| `subsidio_monthly` | 2025 (brackets) | `seed-unverified` |
| `subsidio_rule` | **2026**, two vigencias | **`published`**, DOF 31-12-2024 codigo 5746529 |

Still absent for 2026, because no primary source was read for them: the annual
Art. 152 tarifa, the 61 salarios mínimos profesionales, `imss_rates` and
`isn_rates`. They return `null` — absent, never substituted — so
`all_published` for 2026 is `false` even though what is there is verified.

---

## Endpoints

### `GET /fiscal/uma/`

Unidad de Medida y Actualización — daily, monthly and annual, per year. Set by
INEGI, DOF-published each January, in force from 1 February (LFVUMA).

> **UMA is not the minimum wage.** LFVUMA Art. 4 (DOF 27-01-2016) severed them:
> obligations, fines and caps are denominated in UMA; wages in salario mínimo.
> They are separate endpoints on purpose.

| Query param | Meaning |
|---|---|
| `on=YYYY-MM-DD` | **Primary query shape** — the value in force on that date |
| `year=YYYY` | Filter to one fiscal year |

```bash
curl -H "X-API-Key: tzk_..." \
  "https://api.tezca.mx/api/v1/fiscal/uma/?on=2025-06-15"
```

```json
{
  "count": 1,
  "on": "2025-06-15",
  "value": "113.1400",
  "year": 2025,
  "effective_date": "2025-02-01",
  "provenance": "seed-unverified",
  "results": [
    {
      "year": 2025,
      "value": "113.1400",
      "daily_value": "113.1400",
      "monthly_value": "3439.4600",
      "annual_value": "41273.5200",
      "unit": "MXN/day",
      "vigencia_from": "2025-02-01",
      "vigencia_to": "2026-01-31",
      "in_force": false,
      "provenance": "seed-unverified",
      "is_verified": false,
      "source_citation": "INEGI, valor de la UMA 2025 (DOF, enero 2025); LFVUMA Art. 4",
      "dof_date": null
    }
  ],
  "disclaimer": "..."
}
```

When `?on=` is given, the flat top-level `value` / `year` / `effective_date`
keys mirror what `symbiosis-hcm`'s `TezcaFiscalClient.get_uma_for_date()`
reads, so the client needs no reshaping.

### `GET /fiscal/uma/current/`

The UMA in force today, as a single object with the same flat keys
(`TezcaFiscalClient.get_current_uma()`).

**Returns 404 when no row covers today.** This is deliberate: a consumer must
never silently fall back to a stale hardcoded UMA. A 404 here means an
operator has to publish the current value — which is a loud, fixable problem,
unlike a silently wrong IMSS cap.

### `GET /fiscal/minimos/`

Salario mínimo general and Zona Libre de la Frontera Norte, per CONASAMI
resolutions published in the DOF, in force each 1 January.

| Query param | Meaning |
|---|---|
| `on=YYYY-MM-DD` | Value(s) in force on that date |
| `year=YYYY` | Filter to one year |
| `zone=general\|zlfn` | Filter to one zone |

### `GET /fiscal/tables/`

Structured tables that do not reduce to a scalar.

| `kind` | Contents | Legal basis |
|---|---|---|
| `isr_monthly` | Retention brackets: `lower`, `upper`, `fixed_fee`, `rate` | LISR Art. 96 |
| `isr_annual` | Annual tarifa, same bracket shape | LISR Art. 152 |
| `subsidio_monthly` | `lower`, `upper`, `subsidio` — the pre-2025 bracket table | Decreto de subsidio al empleo |
| `subsidio_rule` | `rate_of_uma`, `uma_monthly`, `monthly_amount`, `income_cap`, `days_divisor`, `formula` | Decreto DOF 01-05-2024 (mod. 31-12-2024) |
| `imss_rates` | Cuotas obrero-patronales | LSS 25, 106, 107, 147, 168 |
| `isn_rates` | Impuesto sobre nóminas by entidad | Ley de Hacienda de cada entidad |

A bracket's `upper` is `null` in the top (open-ended) row. Filter with
`?kind=`, `?year=` or `?on=`.

> **`subsidio_rule` is not a bracket table.** The DOF 01-05-2024 decreto
> replaced the subsidio's rate table with a single amount — 13.8 % of the
> monthly UMA, payable while the ingreso base does not exceed a fixed cap — so
> it gets its own `kind` instead of being flattened into fake brackets. A
> consumer that only knows `subsidio_monthly` sees no row for such a year and
> fails closed, which is correct: it must not apply repealed brackets. Because
> the amount derives from the UMA, and the UMA changes on 1 February, a year
> holds **more than one `subsidio_rule` vigencia** — use `?on=` to pin a day.

### `GET /fiscal/tables/<year>/`

Every table for one fiscal year, grouped under the field names
`symbiosis-hcm`'s `TezcaFiscalClient.get_fiscal_tables(year)` consumes:

```json
{
  "year": 2025,
  "isr_brackets": [ ... ],
  "subsidio": [ ... ],
  "imss_rates": null,
  "isn_rates": null,
  "tables": { "isr_monthly": { ...with provenance... } },
  "provenance_summary": { "isr_monthly": "seed-unverified" },
  "all_published": false,
  "disclaimer": "..."
}
```

`all_published` is the single boolean a consumer can gate on before treating a
year's tables as citable. A kind with no row for that year is `null` — absent,
never substituted from another year. A year with no tables at all returns 404.

This endpoint also accepts **`?on=YYYY-MM-DD`**. Without it, a kind holding
several vigencias in one year (the UMA-derived `subsidio_rule` does) reports
its **latest** period at the top level and lists the earlier ones under
`superseded_within_year`. With `?on=`, you get exactly the row in force that
day. Pass `?on=` whenever the figure feeds a dated calculation.

### Provenance fields

Every row in every response carries:

| Field | Meaning |
|---|---|
| `provenance` / `is_verified` | The honesty contract above |
| `dof_date` | Publication date in the DOF |
| `dof_codigo` | The DOF `nota_detalle` identifier, e.g. `"5778072"` |
| `source_url` | The resolved `nota_detalle` URL |
| `source_citation` | Human-readable citation |
| `notes` | Caveats — including anything the row deliberately does not assert |

`dof_codigo` with `dof_date` resolves to exactly one document:
`https://dof.gob.mx/nota_detalle.php?codigo=<codigo>&fecha=<dd/mm/yyyy>`. It is
the same identity discipline `apps.scraper` applies to pinned corpus documents:
an opaque codigo can resolve to the wrong instrument, so it is pinned together
with its date. Empty when a row is not tied to a single DOF publication.

---

## Data model

Four models in `apps/api/fiscal_models.py`: `UMAValue`, `MinimumWage`,
`TipoDeCambio`, `FiscalTable`. All share the same provenance and vigencia
shape.

**Append-only.** A value is never edited in place once published; a correction
is a new row with a later `vigencia_from`. `vigencia_from` / `vigencia_to`
(inclusive; `null` = still in force) make "what was the UMA on 2019-03-04"
answerable forever. The admin refuses to delete a `published` row — an
operator retracting one closes its `vigencia_to` instead of erasing history.

## Operator workflow

Staff CRUD lives in the Django admin at `/admin/` (gated to `is_staff`):

1. Read the DOF publication.
2. Create the row (or edit the `seed-unverified` one), filling
   `source_citation`, `source_url` and `dof_date`.
3. Set `provenance` to `published`.
4. Close the previous row's `vigencia_to` to the day before the new one starts.

To load the initial seed:

```bash
python manage.py seed_fiscal_values --dry-run    # report only
LOCAL_DB=yes python manage.py seed_fiscal_values # write
```

The command is idempotent and, per AGENTS.md, refuses to write without the
`LOCAL_DB=yes` guard.

To publish the DOF-verified 2026 values (see
[`fiscal/2026-publicacion-dof.md`](fiscal/2026-publicacion-dof.md)):

```bash
python manage.py publish_fiscal_values_2026 --dry-run    # report only
LOCAL_DB=yes python manage.py publish_fiscal_values_2026 # write
```

It writes `published` rows with their `dof_codigo`, promotes the matching
`seed-unverified` rows rather than duplicating them, closes the prior year's
vigencia, and **never touches a row that is already `published`** — an
operator's hand correction is respected.

## Provenance of this feed's existence

Built per gate **G1** of
`internal-devops/docs/strategy/2026-08-22-symbiosis-hcm-benchmarking-scoping.md`,
which recorded that `symbiosis-hcm` calls `/api/v1/fiscal/uma/current/`,
`/fiscal/uma/` and `/fiscal/tables/{year}/` against a Tezca URLconf that had no
`fiscal/` routes at all — so every UMA-dependent number in that product came
from a hardcoded 2025 default. The owner's resolution was that Tezca builds the
feed, because it serves the whole ecosystem rather than one consumer.
