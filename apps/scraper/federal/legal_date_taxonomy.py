"""
The tagging vocabulary for tezca's legal-date groupings — robust and broad, so a
consumer selects «the banking dates» or «the fiscal inhábiles» by a stable tag,
and a new source (the SAT, the Poder Judicial, an electoral decree) slots in by
adding a member here, not by inventing a string.

TWO AXES, deliberately separate:

  DOMAIN — which SECTOR observes or is bound by the date. English codes, aligned
    with the corpus ``DOMAIN_MAP`` (apps/api/constants.py) so a legal date and a
    law speak the same sector vocabulary. A date carries the domain of EVERY
    source that lists it: a día de descanso obligatorio is ``labor`` by the LFT
    and ``banking`` when the CNBV disposición lists it — the union, not one home.

  TIPO — the KIND of the dated fact within its source (the legal-instrument name,
    kept in Spanish). Each tipo has one PRIMARY domain (its source's sector); a
    fact may span more.

BROAD ON PURPOSE. Only ``labor`` + ``banking`` (and, via the SEP feed,
``education``) are populated today, but the vocabulary already carries fiscal,
civic, judicial, electoral and public-sector — the categories tezca is positioned
to capture next, so a future feed tags itself against a member that already
exists. Extending either axis is a deliberate, reviewed change — the same closed-
vocabulary posture as the kalya CalendarEvent taxonomy and the SEP simbología.
"""

from typing import Dict, FrozenSet, Iterable

# ── DOMAINS (sectors that observe a date) ────────────────────────────────────
LABOR = "labor"
BANKING = "banking"
FISCAL = "fiscal"
EDUCATION = "education"
CIVIC = "civic"
JUDICIAL = "judicial"
ELECTORAL = "electoral"
PUBLIC_SECTOR = "public_sector"

LEGAL_DATE_DOMAINS: FrozenSet[str] = frozenset(
    {LABOR, BANKING, FISCAL, EDUCATION, CIVIC, JUDICIAL, ELECTORAL, PUBLIC_SECTOR}
)

# The legal source each domain draws its dates from — documentation the consumers
# and the next source-author read to know what a tag means and where it comes from.
LEGAL_DATE_DOMAIN_SOURCES: Dict[str, str] = {
    LABOR: "Ley Federal del Trabajo, Art. 74 — días de descanso obligatorio",
    BANKING: "CNBV — Disposiciones de días inhábiles de las instituciones de crédito",
    FISCAL: "SAT / CFF Art. 12 — días inhábiles para plazos fiscales",
    EDUCATION: "SEP — calendario escolar de educación básica (acuerdo anual)",
    CIVIC: "Conmemoraciones cívicas oficiales (sin descanso obligatorio)",
    JUDICIAL: "Poder Judicial de la Federación — suspensión de plazos",
    ELECTORAL: "INE / decretos electorales — jornadas electorales",
    PUBLIC_SECTOR: "LFTSE / calendarios oficiales — descanso del servicio público",
}

# ── TIPOS (the kind of a dated fact, within its source) ──────────────────────
DESCANSO_OBLIGATORIO = "descanso_obligatorio"
INHABIL_BANCARIO = "inhabil_bancario"
INHABIL_FISCAL = "inhabil_fiscal"
SUSPENSION_ESCOLAR = "suspension_escolar"
PERIODO_VACACIONAL = "periodo_vacacional"
DIA_CIVICO = "dia_civico"
INHABIL_JUDICIAL = "inhabil_judicial"
JORNADA_ELECTORAL = "jornada_electoral"

LEGAL_DATE_TIPOS: FrozenSet[str] = frozenset(
    {
        DESCANSO_OBLIGATORIO,
        INHABIL_BANCARIO,
        INHABIL_FISCAL,
        SUSPENSION_ESCOLAR,
        PERIODO_VACACIONAL,
        DIA_CIVICO,
        INHABIL_JUDICIAL,
        JORNADA_ELECTORAL,
    }
)

# Each tipo's PRIMARY domain — the sector of the source that defines it. A fact
# may carry more domains than this (a descanso_obligatorio is also banking), but
# every tipo has a home, and the map is total over LEGAL_DATE_TIPOS (a test pins
# that, so a new tipo cannot land without declaring its home).
LEGAL_DATE_TIPO_PRIMARY_DOMAIN: Dict[str, str] = {
    DESCANSO_OBLIGATORIO: LABOR,
    INHABIL_BANCARIO: BANKING,
    INHABIL_FISCAL: FISCAL,
    SUSPENSION_ESCOLAR: EDUCATION,
    PERIODO_VACACIONAL: EDUCATION,
    DIA_CIVICO: CIVIC,
    INHABIL_JUDICIAL: JUDICIAL,
    JORNADA_ELECTORAL: ELECTORAL,
}


def is_valid_domain(domain: str) -> bool:
    return domain in LEGAL_DATE_DOMAINS


def is_valid_tipo(tipo: str) -> bool:
    return tipo in LEGAL_DATE_TIPOS


def validate_domains(domains: Iterable[str]) -> None:
    """Raise ValueError if any domain is outside the vocabulary — the guard a
    dates-emitting module runs so a typo'd or invented sector tag is refused at
    the source, not carried into an artifact a consumer then cannot select on."""
    unknown = sorted({d for d in domains if d not in LEGAL_DATE_DOMAINS})
    if unknown:
        raise ValueError(
            f"unknown legal-date domain(s) {unknown}; valid: {sorted(LEGAL_DATE_DOMAINS)}"
        )


def validate_tipo(tipo: str) -> None:
    if tipo not in LEGAL_DATE_TIPOS:
        raise ValueError(
            f"unknown legal-date tipo {tipo!r}; valid: {sorted(LEGAL_DATE_TIPOS)}"
        )
