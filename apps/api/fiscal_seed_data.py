"""Seed values for the fiscal feed — with honest provenance.

**Read this before trusting a number in this file.**

Tezca's own law corpus carries law *text*, not fiscal *values*: there is no
UMA figure, no CONASAMI resolution and no LISR Art. 96 bracket table
anywhere under ``data/`` (verified 2026-08-22 — ``data/federal/mx-fed-lisr.xml``
is a two-article stub, and ``grep -i conasami data/law_registry.json``
returns nothing). So none of these seeds could be derived from the corpus.

They are therefore all stamped ``seed-unverified``: well-known published
figures, entered so the feed is useful on day one, but **not verified by
this repo against a DOF document**. The API says so on every response, and
``is_verified`` is False for all of them. Promoting a row to ``published``
is a deliberate operator act performed after reading the actual DOF
publication — that is what the admin surface is for.

The alternative — shipping an empty feed — would have left every consumer
on its hardcoded fallback, which is the exact failure this feed exists to
end. Shipping values that *announce their own uncertainty* is strictly
better than silent hardcoded constants, and strictly weaker than a DOF
citation. That is the honest middle, and it is deliberate.

The ISR/subsidio tables are transcribed from
``symbiosis-hcm/packages/mx-payroll/mx_payroll/isr.py`` (the 2025 SAT
monthly tables the consumer already computes with). Serving them here does
not make them more true — it makes them *one* value with *one* provenance
stamp instead of a constant copied into every consumer.
"""

SEED_NOTE = (
    "Seeded 2026-08-22 from published figures; NOT verified against a DOF "
    "document by Tezca. Promote to provenance='published' only after an "
    "operator reads the cited DOF publication."
)

ISR_NOTE = (
    "Transcribed from symbiosis-hcm/packages/mx-payroll/mx_payroll/isr.py "
    "(2025 SAT monthly tables), so the ecosystem holds one copy instead of "
    "one per consumer. NOT independently verified against the DOF/RMF anexo "
    "by Tezca."
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
# ISR retención mensual — LISR Art. 96.
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
        "fixed_fee": "1639.32",
        "rate": "0.2136",
    },
    {
        "lower": "31236.50",
        "upper": "49233.00",
        "fixed_fee": "4005.47",
        "rate": "0.2352",
    },
    {
        "lower": "49233.01",
        "upper": "93993.90",
        "fixed_fee": "8236.89",
        "rate": "0.3000",
    },
    {
        "lower": "93993.91",
        "upper": "125325.20",
        "fixed_fee": "21665.17",
        "rate": "0.3200",
    },
    {
        "lower": "125325.21",
        "upper": "375975.61",
        "fixed_fee": "31691.18",
        "rate": "0.3400",
    },
    {
        "lower": "375975.62",
        "upper": None,
        "fixed_fee": "116890.10",
        "rate": "0.3500",
    },
]

# ---------------------------------------------------------------------------
# Subsidio al empleo mensual.
# ---------------------------------------------------------------------------
SUBSIDIO_MONTHLY_2025 = [
    {"lower": "0.01", "upper": "1768.96", "subsidio": "407.02"},
    {"lower": "1768.97", "upper": "2653.38", "subsidio": "406.83"},
    {"lower": "2653.39", "upper": "3472.84", "subsidio": "406.62"},
    {"lower": "3472.85", "upper": "3537.87", "subsidio": "392.77"},
    {"lower": "3537.88", "upper": "4446.15", "subsidio": "382.46"},
    {"lower": "4446.16", "upper": "4717.18", "subsidio": "354.23"},
    {"lower": "4717.19", "upper": "5335.42", "subsidio": "324.87"},
    {"lower": "5335.43", "upper": "6224.67", "subsidio": "294.63"},
    {"lower": "6224.68", "upper": "7113.90", "subsidio": "253.54"},
    {"lower": "7113.91", "upper": "7382.33", "subsidio": "217.61"},
    {"lower": "7382.34", "upper": None, "subsidio": "0.00"},
]

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
    (
        "subsidio_monthly",
        2025,
        "monthly",
        SUBSIDIO_MONTHLY_2025,
        "Decreto de subsidio al empleo",
        "2025-01-01",
        "2025-12-31",
    ),
]
