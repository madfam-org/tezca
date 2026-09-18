"""
Feriados legales de México — the días de descanso obligatorio (LFT Art. 74) and
the días inhábiles bancarios (CNBV), as a machine-readable dates artifact for
kalya, alongside the SEP school calendar (:mod:`sep_calendario_dates`).

Two layers, two provenances — the same discipline the fiscal/labor feeds use
(:class:`apps.api.fiscal_models.Provenance`):

``descanso_obligatorio`` — LFT Artículo 74.
    The federal statutory holidays. These are **computed from the statute**,
    whose text tezca already serves (``lft.json``): fixed dates and the
    "primer/tercer lunes" movable rules leave no ambiguity, so every one is
    ``published`` — it *is* the law. Banks close on all of them, so each also
    carries the ``bancario`` domain.

``inhabil_bancario`` — CNBV días inhábiles beyond Art. 74.
    Banks are also closed Jueves and Viernes Santo, el 2 de noviembre and el 12
    de diciembre. These are set by the CNBV's annual "días inhábiles" calendar
    (published in the DOF), **not** by Art. 74. Semana Santa is computable
    (Gauss/Butcher), and the two fixed additions are well known — but the
    authoritative list is the CNBV publication, so until each year's calendar is
    read against its primary DOF source these are emitted ``seed-unverified``:
    honest that they orient but do not yet *assert* a bank-closed day. A consumer
    that drives a real payment vence (nauta's estado de cuenta) must require
    ``published`` before it goes client-visible — which is exactly the gate that
    keeps an unverified date from ever calling a client late.

NOT computed here (item IX, LFT Art. 74): the jornada electoral. Election days
are fixed by the electoral decree of the year, not by a perpetual rule, so they
are a pinned add when they apply (e.g. the 2027 federal mid-term), never guessed.

Artifact schema: ``tezca.feriados_legales/v1`` (mirrors ``tezca.sep_calendario/v1``).
PURE: no Django, no DB, no network — a year in, an artifact out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

SCHEMA = "tezca.feriados_legales/v1"

# Mirrors apps.api.fiscal_models.Provenance without importing Django here (this
# module stays import-light so the artifact producer runs outside a Django app).
PUBLISHED = "published"
SEED_UNVERIFIED = "seed-unverified"


@dataclass(frozen=True)
class FeriadoFact:
    """One legal non-working date, with its statutory basis and provenance.

    ``tipo`` is the tezca-side kind (``descanso_obligatorio`` | ``inhabil_bancario``);
    ``domains`` says which sectors observe it (``laboral``, ``bancario``), so a
    consumer selects the applicable set (a payment vence takes ``bancario``).
    ``fundamento`` cites the statute or calendar; ``provenance`` is
    ``published`` (primary-verified) or ``seed-unverified`` (orients only).
    """

    date: str
    tipo: str
    domains: tuple[str, ...]
    title: str
    fundamento: str
    provenance: str

    def to_json(self) -> Dict[str, object]:
        return {
            "date": self.date,
            "tipo": self.tipo,
            "domains": list(self.domains),
            "title": self.title,
            "fundamento": self.fundamento,
            "provenance": self.provenance,
        }


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The ``n``-th ``weekday`` (Mon=0 … Sun=6) of ``month`` — e.g. the third
    Monday of March. ``n`` is 1-based; no month has a 5th of most weekdays but
    Art. 74 only ever asks for the 1st or 3rd."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _easter(year: int) -> date:
    """Gregorian Easter Sunday (Anonymous Gregorian / "Butcher" algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month = (h + ell - 7 * m + 114) // 31
    day = ((h + ell - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _is_transmision_ejecutivo(year: int) -> bool:
    """Art. 74 fr. VII: 1° de diciembre de cada seis años, en la transmisión del
    Poder Ejecutivo Federal. The 2024 term began 2024-10-01 under the reformed
    calendar, so transmissions land 2024, 2030, 2036 … — every sixth year from
    2024."""
    return year >= 2024 and (year - 2024) % 6 == 0


_MON = 0  # date.weekday() Monday


def dias_descanso_obligatorio(year: int) -> List[FeriadoFact]:
    """LFT Art. 74 fr. I–VIII for ``year``, computed from the statute. Every one
    is ``published`` (it is the law) and observed by banks, so all carry both
    ``laboral`` and ``bancario`` domains. Ordered by date."""
    both = ("laboral", "bancario")

    def f(d: date, title: str, fr: str) -> FeriadoFact:
        return FeriadoFact(
            d.isoformat(), "descanso_obligatorio", both, title, f"LFT Art. 74 fr. {fr}", PUBLISHED
        )

    out = [
        f(date(year, 1, 1), "Año Nuevo", "I"),
        f(_nth_weekday(year, 2, _MON, 1), "Conmemoración del 5 de febrero (Constitución)", "II"),
        f(_nth_weekday(year, 3, _MON, 3), "Conmemoración del 21 de marzo (Natalicio de Juárez)", "III"),
        f(date(year, 5, 1), "Día del Trabajo", "IV"),
        f(date(year, 9, 16), "Independencia de México", "V"),
        f(_nth_weekday(year, 11, _MON, 3), "Conmemoración del 20 de noviembre (Revolución)", "VI"),
        f(date(year, 12, 25), "Navidad", "VIII"),
    ]
    if _is_transmision_ejecutivo(year):
        out.append(
            f(date(year, 12, 1), "Transmisión del Poder Ejecutivo Federal", "VII")
        )
    return sorted(out, key=lambda x: x.date)


# ── The source documents: the ingested legal corpus the bank dates are read from ─
#
# The dates below are not invented here — they are READ FROM the legal sources
# tezca ingests, the same way the SEP dates are read from the acuerdo tezca
# ingests. The días de descanso obligatorio come from the LFT (Art. 74, already
# a corpus Law); the bank-only additions come from the CNBV's annual
# «Disposiciones … días inhábiles bancarios», a DOF publication tezca REGISTERS
# as a corpus Law (`manage.py ingest_feriados`) and whose Artículo 1 enumerates
# them. Each year's disposición is a pinned DOF `codigo`, verified against
# primary text — the registry IS the source of truth, the same posture as
# `SEP_CALENDAR_DOCUMENTS`. A year with a registered disposición is `published`;
# a year without one falls back to the computed default, `seed-unverified`.

SIDOF_NOTE_URL = "https://sidof.segob.gob.mx/notas/docFuente/{codigo}"
DOF_NOTE_URL = "https://dof.gob.mx/nota_detalle.php?codigo={codigo}&fecha={fecha}"

FERIADOS_CATEGORY = "dias_inhabiles_bancarios"
FERIADOS_DOMAINS = ["banking"]


def _dof_fecha(iso_date: str) -> str:
    """`YYYY-MM-DD` → the DOF's `DD/MM/YYYY` query format."""
    year, month, day = iso_date.split("-")
    return f"{day}/{month}/{year}"


@dataclass
class FeriadosDocument:
    """One CNBV días-inhábiles disposición, pinned by DOF `codigo` with enough
    metadata to register a Law + LawVersion (the corpus side) and to cite the
    bank dates read from it (the dates side). Mirrors `SepCalendarDocument`."""

    official_id: str
    name: str
    short_name: str
    dof_codigo: str
    publication_date: str  # ISO, DOF publication date
    valid_from: Optional[str]  # ISO, the year the calendar governs from
    anio: int
    verified_on: str  # ISO, when the enumerated dates were read against primary text
    status: str = "vigente"
    vigencia_note: str = ""
    category: str = FERIADOS_CATEGORY
    domains: List[str] = field(default_factory=lambda: list(FERIADOS_DOMAINS))

    @property
    def dof_url(self) -> str:
        return DOF_NOTE_URL.format(codigo=self.dof_codigo, fecha=_dof_fecha(self.publication_date))

    @property
    def sidof_url(self) -> str:
        return SIDOF_NOTE_URL.format(codigo=self.dof_codigo)

    @property
    def text_filename(self) -> str:
        return f"{self.official_id}.xml"


# Verified against primary DOF (codigo 5775684) on 2026-09-18: the disposición's
# Artículo 1 for 2026, cross-checked so LFT ∪ these additions equals its full
# eleven-day list (the test encodes that list).
FERIADOS_DOCUMENTS: List[FeriadosDocument] = [
    FeriadosDocument(
        official_id="cnbv-dias-inhabiles-bancarios-2026",
        name=(
            "Disposiciones que señalan los días del año 2026 en que las instituciones "
            "de crédito deberán cerrar sus puertas y suspender operaciones"
        ),
        short_name="Días inhábiles bancarios CNBV 2026",
        dof_codigo="5775684",
        publication_date="2025-12-10",
        valid_from="2026-01-01",
        anio=2026,
        verified_on="2026-09-18",
        vigencia_note="Calendario anual de días inhábiles bancarios (CNBV), Artículo 1.",
    ),
]

FERIADOS_DOCUMENTS_BY_ID: Dict[str, FeriadosDocument] = {
    d.official_id: d for d in FERIADOS_DOCUMENTS
}
FERIADOS_DOCUMENTS_BY_ANIO: Dict[int, FeriadosDocument] = {d.anio: d for d in FERIADOS_DOCUMENTS}


# The bank-only days (beyond Art. 74) READ FROM each year's disposición Artículo 1
# — the dates the ingested legal source enumerates, keyed by año. A year here has
# a matching FeriadosDocument; the two together make the additions `published`.
_CNBV_ADICIONALES: Dict[int, List[Tuple[str, str]]] = {
    2026: [
        ("2026-04-02", "Jueves Santo"),
        ("2026-04-03", "Viernes Santo"),
        ("2026-11-02", "Día de Muertos"),
        ("2026-12-12", "Día de la Virgen de Guadalupe"),
    ],
}


def is_bancario_verified(year: int) -> bool:
    """Whether ``year``'s bank additions are read from an ingested DOF disposición
    (``published``) rather than the computed default. A payment vence that must be
    exact and client-visible reads this before trusting the year's calendar."""
    return year in FERIADOS_DOCUMENTS_BY_ANIO and year in _CNBV_ADICIONALES


def inhabiles_bancarios_adicionales(year: int) -> List[FeriadoFact]:
    """CNBV bank-closed days that are NOT Art. 74 holidays. For a year whose CNBV
    disposición tezca has registered, these are the dates READ FROM it
    (``published``), each citing that corpus document; otherwise the computed
    default (Semana Santa via Easter + 2 nov + 12 dic), ``seed-unverified`` —
    orienting, never asserting a closed day for a payment vence until the year's
    disposición is ingested and read. Ordered by date."""
    banco = ("bancario",)
    doc = FERIADOS_DOCUMENTS_BY_ANIO.get(year)
    adicionales = _CNBV_ADICIONALES.get(year)
    if doc is not None and adicionales is not None:
        cite = (
            f"CNBV días inhábiles {year} — DOF {doc.dof_codigo} "
            f"({doc.publication_date}), Art. 1 · corpus {doc.official_id}"
        )
        return sorted(
            (
                FeriadoFact(d, "inhabil_bancario", banco, title, cite, PUBLISHED)
                for d, title in adicionales
            ),
            key=lambda x: x.date,
        )

    easter = _easter(year)

    def f(d: date, title: str) -> FeriadoFact:
        return FeriadoFact(
            d.isoformat(),
            "inhabil_bancario",
            banco,
            title,
            "CNBV — calendario anual de días inhábiles bancarios (sin fijar)",
            SEED_UNVERIFIED,
        )

    return sorted(
        [
            f(easter - timedelta(days=3), "Jueves Santo"),
            f(easter - timedelta(days=2), "Viernes Santo"),
            f(date(year, 11, 2), "Día de Muertos"),
            f(date(year, 12, 12), "Día de la Virgen de Guadalupe"),
        ],
        key=lambda x: x.date,
    )


def feriados_bancarios(year: int) -> List[FeriadoFact]:
    """The full set a bank observes: Art. 74 (published) ∪ CNBV additions
    (seed-unverified). This is the calendar a día-hábil-bancario payment window
    subtracts from. Ordered by date."""
    return sorted(
        dias_descanso_obligatorio(year) + inhabiles_bancarios_adicionales(year),
        key=lambda x: x.date,
    )


def extract_feriados(year: int) -> Dict[str, object]:
    """The ``tezca.feriados_legales/v1`` artifact for one calendar ``year`` —
    the shape kalya's organizational-calendar ingestion consumes, mirroring the
    SEP artifact. Events carry Art. 74 (published) and the CNBV bank additions
    (seed-unverified). ``end_date`` never appears: legal feriados are single
    days."""
    events = feriados_bancarios(year)
    doc = FERIADOS_DOCUMENTS_BY_ANIO.get(year)
    if doc is not None and year in _CNBV_ADICIONALES:
        bancario_source = {
            "instrumento": doc.name,
            "corpus_official_id": doc.official_id,
            "dof_codigo": doc.dof_codigo,
            "dof_fecha": doc.publication_date,
            "dof_url": doc.dof_url,
            "verified_on": doc.verified_on,
            "provenance": PUBLISHED,
        }
    else:
        bancario_source = {
            "instrumento": "CNBV — calendario anual de días inhábiles bancarios (DOF)",
            "metodo": "computed default — Semana Santa (Gauss/Butcher) + 2 nov + 12 dic",
            "provenance": SEED_UNVERIFIED,
            "nota": (
                "This year's CNBV calendar has not been pinned from its DOF "
                "publication; these bank additions orient but are not yet verified."
            ),
        }
    return {
        "schema": SCHEMA,
        "anio": year,
        "bancario_verificado": is_bancario_verified(year),
        "source": {
            "descanso_obligatorio": {
                "instrumento": "Ley Federal del Trabajo, Artículo 74",
                "metodo": "computed from the statute (fixed dates + primer/tercer lunes rules)",
                "provenance": PUBLISHED,
            },
            "inhabil_bancario": bancario_source,
        },
        "events": [e.to_json() for e in events],
    }
