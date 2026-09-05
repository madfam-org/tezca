"""Seed values for the fiscal feed — with honest provenance.

**Read this before trusting a number in this file.**

Tezca's own law corpus carries law *text*, not fiscal *values*: there is no
UMA figure, no CONASAMI resolution and no LISR Art. 96 bracket table
anywhere under ``data/`` (verified 2026-08-22 — ``data/federal/mx-fed-lisr.xml``
is a two-article stub, and ``grep -i conasami data/law_registry.json``
returns nothing). So none of these seeds could be derived from the corpus.

They are therefore all stamped ``seed-unverified``: well-known published
figures, entered so the feed is useful on day one, but **not verified by
this repo against a DOF document**.

.. note::

   The **2026** values have since been verified. They live in
   :mod:`apps.api.fiscal_dof_2026`, transcribed from the DOF text with each
   publication's ``codigo``, and ``manage.py publish_fiscal_values_2026``
   promotes the seeded 2026 rows to ``published``. The 2026 entries below
   remain as the seed floor — for a database that has never had the publish
   command run — and are deliberately left ``seed-unverified``. Where the two
   disagree, ``fiscal_dof_2026`` is right: the seed's UMA 2026 monthly/annual
   (3,566.28 / 42,795.36) were derived by hand; INEGI published 3,566.22 /
   42,794.64. The API says so on every response, and
``is_verified`` is False for all of them. Promoting a row to ``published``
is a deliberate operator act performed after reading the actual DOF
publication — that is what the admin surface is for.

The alternative — shipping an empty feed — would have left every consumer
on its hardcoded fallback, which is the exact failure this feed exists to
end. Shipping values that *announce their own uncertainty* is strictly
better than silent hardcoded constants, and strictly weaker than a DOF
citation. That is the honest middle, and it is deliberate.

.. note::

   Los valores **2025** también se verificaron (2026-09-05) y viven en
   :mod:`apps.api.fiscal_dof_2025`, con ``manage.py
   publish_fiscal_values_2025`` para promoverlos. Esa verificación encontró
   que la tarifa ISR de este seed traía **seis cuotas fijas equivocadas**
   —transcritas de ``symbiosis-hcm``, con un dígito de millar perdido— y que
   la tabla de subsidio al empleo estaba **derogada**. Ambas cosas ya están
   corregidas aquí: las cuotas fijas coinciden con el Anexo 8 de la RMF 2025
   y la tabla derogada se retiró en lugar de conservarse «por
   compatibilidad». El diseño fail-closed funcionó — el seed nunca afirmó
   estar verificado — pero un piso equivocado es peor que ninguno.

The ISR table was originally transcribed from
``symbiosis-hcm/packages/mx-payroll/mx_payroll/isr.py`` (the 2025 SAT
monthly tables the consumer already computes with). Serving it here does
not make it more true — it makes it *one* value with *one* provenance
stamp instead of a constant copied into every consumer. That upstream file
is where the errata originated and, unlike this seed, it probably computes
production payroll: correcting it is a separate, higher-priority lane.
"""

SEED_NOTE = (
    "Seeded 2026-08-22 from published figures; NOT verified against a DOF "
    "document by Tezca. Promote to provenance='published' only after an "
    "operator reads the cited DOF publication."
)

ISR_NOTE = (
    "Originally transcribed from symbiosis-hcm/packages/mx-payroll/"
    "mx_payroll/isr.py (2025 SAT monthly tables), so the ecosystem holds one "
    "copy instead of one per consumer. Six fixed fees were WRONG there and "
    "were corrected on 2026-09-05 against Anexo 8 de la RMF 2025 (DOF "
    "30-12-2024, codigo 5746354). This row still says seed-unverified because "
    "the seed command never asserts a citation: run "
    "'manage.py publish_fiscal_values_2025' to publish it with its DOF "
    "citation."
)

# ---------------------------------------------------------------------------
# UMA — INEGI, published in the DOF each January, in force 1 Feb → 31 Jan.
# (year, daily, monthly, annual, vigencia_from, vigencia_to)
# 2016 is the UMA's first year: created by the DOF 27-01-2016 constitutional
# reform, it ran from 28-01-2016 under the LFVUMA transitional regime.
# ---------------------------------------------------------------------------
UMA_SEEDS = [
    (2016, "73.04", "2220.42", "26645.04", "2016-01-28", "2017-01-31"),
    (2017, "75.49", "2294.90", "27538.80", "2017-02-01", "2018-01-31"),
    (2018, "80.60", "2450.24", "29402.88", "2018-02-01", "2019-01-31"),
    (2019, "84.49", "2568.50", "30822.00", "2019-02-01", "2020-01-31"),
    (2020, "86.88", "2641.15", "31693.80", "2020-02-01", "2021-01-31"),
    (2021, "89.62", "2724.45", "32693.40", "2021-02-01", "2022-01-31"),
    (2022, "96.22", "2925.09", "35101.08", "2022-02-01", "2023-01-31"),
    (2023, "103.74", "3153.70", "37844.40", "2023-02-01", "2024-01-31"),
    (2024, "108.57", "3300.53", "39606.36", "2024-02-01", "2025-01-31"),
    (2025, "113.14", "3439.46", "41273.52", "2025-02-01", "2026-01-31"),
    # NOTE: monthly/annual here are hand-derived and DIFFER from the figures
    # INEGI actually published (3,566.22 / 42,794.64 — DOF 09-01-2026, codigo
    # 5778072). Left as-is so this file stays a record of what the unverified
    # seed claimed; apps/api/fiscal_dof_2026.py carries the verified values and
    # `manage.py publish_fiscal_values_2026` corrects the row in place while
    # promoting it to provenance='published'.
    (2026, "117.31", "3566.28", "42795.36", "2026-02-01", None),
]

# ---------------------------------------------------------------------------
# Salario mínimo general — CONASAMI resolution, DOF, in force 1 Jan.
# The Zona Libre de la Frontera Norte was created for 2019, so ZLFN rows
# start there. (year, general, zlfn)
# ---------------------------------------------------------------------------
MINIMUM_WAGE_SEEDS = [
    (2016, "73.04", None),
    (2017, "80.04", None),
    (2018, "88.36", None),
    (2019, "102.68", "176.72"),
    (2020, "123.22", "185.56"),
    (2021, "141.70", "213.39"),
    (2022, "172.87", "260.34"),
    (2023, "207.44", "312.41"),
    (2024, "248.93", "374.89"),
    (2025, "278.80", "419.88"),
    (2026, "315.04", "440.87"),
]

# ---------------------------------------------------------------------------
# Tipo de cambio (DOF) — Banco de México daily USD/MXN reference rate.
# Unlike UMA/salario mínimo (annual constants), this is a daily series, so we
# seed only ONE recent operator-entered placeholder so /fiscal/tipo-cambio/
# current returns 200 in dev/demo. It is provenance=OPERATOR (not seed history)
# and MUST be superseded by the automated source (Banxico SF60653) in prod.
# (from_currency, to_currency, value, vigencia_from)
TIPO_CAMBIO_SEEDS = [
    ("USD", "MXN", "18.5100", "2026-08-21"),
]

TIPO_CAMBIO_NOTE = (
    "Operator-entered placeholder so the DOF-rate endpoint is live in dev/demo; "
    "a single day, NOT a maintained series. Prod must feed this from the "
    "automated source (Banxico SIE SF60653) or an operator's daily DOF read."
)

# ---------------------------------------------------------------------------
# ISR retención mensual — LISR Art. 96.
#
# ERRATA 2026-09-05: seis de estas once cuotas fijas estaban MAL transcritas
# (tramos 6 a 11: 1639.32, 4005.47, 8236.89, 21665.17, 31691.18, 116890.10),
# con un patrón de dígito de millar perdido — la tarifa sembrada subestimaba
# el ISR retenido hasta ≈$1,022 mensuales por trabajador. Corregidas contra el
# Anexo 8 de la RMF 2025 (DOF 30-12-2024, codigo 5746354, apartado A fr. V).
# Los once límites y las once tasas ya eran correctos.
#
# Las cifras verificadas viven en :mod:`apps.api.fiscal_dof_2025` con su cita;
# aquí se repiten porque este seed es el piso para una base que nunca corrió
# el comando de publicación, y un piso equivocado es peor que ninguno. La
# prueba ``test_toda_tarifa_isr_sembrada_es_coherente`` impide que la errata
# vuelva a entrar.
# ---------------------------------------------------------------------------
ISR_MONTHLY_2025 = [
    {"lower": "0.01", "upper": "746.04", "fixed_fee": "0.00", "rate": "0.0192"},
    {"lower": "746.05", "upper": "6332.05", "fixed_fee": "14.32", "rate": "0.0640"},
    {"lower": "6332.06", "upper": "11128.01", "fixed_fee": "371.83", "rate": "0.1088"},
    {"lower": "11128.02", "upper": "12935.82", "fixed_fee": "893.63", "rate": "0.1600"},
    {
        "lower": "12935.83",
        "upper": "15487.71",
        "fixed_fee": "1182.88",
        "rate": "0.1792",
    },
    {
        "lower": "15487.72",
        "upper": "31236.49",
        "fixed_fee": "1640.18",
        "rate": "0.2136",
    },
    {
        "lower": "31236.50",
        "upper": "49233.00",
        "fixed_fee": "5004.12",
        "rate": "0.2352",
    },
    {
        "lower": "49233.01",
        "upper": "93993.90",
        "fixed_fee": "9236.89",
        "rate": "0.3000",
    },
    {
        "lower": "93993.91",
        "upper": "125325.20",
        "fixed_fee": "22665.17",
        "rate": "0.3200",
    },
    {
        "lower": "125325.21",
        "upper": "375975.61",
        "fixed_fee": "32691.18",
        "rate": "0.3400",
    },
    {
        "lower": "375975.62",
        "upper": None,
        "fixed_fee": "117912.32",
        "rate": "0.3500",
    },
]

# ---------------------------------------------------------------------------
# Subsidio al empleo — RETIRADO del seed el 2026-09-05.
#
# Aquí vivía ``SUBSIDIO_MONTHLY_2025``: once renglones de montos por tramos,
# de $407.02 a $0.00, con límite superior $7,382.33. Esa tabla está
# **DEROGADA**. El «Decreto que otorga el subsidio para el empleo» (DOF
# 01-05-2024), modificado el 31-12-2024 (codigo 5746529), la sustituyó por
# una cuota fija: 13.8 % de la UMA mensual, para ingresos base que no excedan
# $10,171.00. El considerando de ese decreto cita precisamente ese límite de
# 7,382.33 como el defecto que vino a corregir — es decir, el seed sembraba
# literalmente la tabla que el legislador declaró obsoleta.
#
# NO se conserva «por compatibilidad». Un consumidor que aplique tramos
# derogados a 2025 calcula mal y no se entera; uno que reciba ``null`` en
# ``subsidio`` falla en claro, que es el comportamiento que este feed existe
# para producir. La regla vigente se publica como ``subsidio_rule`` desde
# :mod:`apps.api.fiscal_dof_2025` (dos vigencias: enero al 14.39 %,
# febrero-diciembre al 13.8 %), el mismo ``kind`` que usa 2026.
#
# Una base ya sembrada conserva la fila vieja hasta que el operador corra
# ``manage.py publish_fiscal_values_2025``, que la retira.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Fiscal tables to seed: (kind, year, period, rows, legal_basis, from, to)
#
# 2026 is DELIBERATELY ABSENT. The 2026 SAT tables are not in Tezca's corpus
# and were not verified for this seed, so no 2026 row is written: a consumer
# asking /fiscal/tables/2026/ gets a 404 that says "an operator must publish
# this year's tables" rather than silently receiving 2025 brackets stamped
# 2026. Fail-closed is the whole point of the feed.
# ---------------------------------------------------------------------------
FISCAL_TABLE_SEEDS = [
    (
        "isr_monthly",
        2025,
        "monthly",
        ISR_MONTHLY_2025,
        "LISR Art. 96",
        "2025-01-01",
        "2025-12-31",
    ),
]
