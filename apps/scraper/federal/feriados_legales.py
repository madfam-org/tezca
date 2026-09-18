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

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional

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


# The CNBV annual bank-inhábil calendar, PINNED from its DOF publication and
# verified against primary text — the same discipline the SEP dates use, and for
# the same reason: the CNBV list is set year by year (banks close 2 nov, 12 dic
# and Semana Santa on top of Art. 74, and the Comisión can vary it), so it must
# be READ from the year's DOF, never assumed from a perpetual rule. Each entry
# lists the bank-only days BEYOND the Art. 74 set (Art. 74 is computed and
# already carries the bancario domain). A pinned year is ``published``. A year
# absent here falls back to the computed default below, ``seed-unverified``,
# until that year's CNBV calendar is published and read — which is exactly the
# gate that keeps an unverified bank date out of a client-facing payment vence.
_CNBV_PINNED: Dict[int, Dict[str, object]] = {
    2026: {
        "source": {
            "instrumento": (
                "CNBV — Disposiciones que señalan los días del año 2026 en que las "
                "instituciones de crédito deberán cerrar sus puertas (Artículo 1)"
            ),
            "dof_codigo": "5775684",
            "dof_fecha": "2025-12-10",
            "dof_url": "https://dof.gob.mx/nota_detalle.php?codigo=5775684&fecha=10/12/2025",
            "verified_on": "2026-09-18",
        },
        # The bank-only days beyond Art. 74, exactly as the DOF Artículo 1
        # enumerates them (2 y 3 de abril; 2 de noviembre; 12 de diciembre).
        "adicionales": [
            ("2026-04-02", "Jueves Santo"),
            ("2026-04-03", "Viernes Santo"),
            ("2026-11-02", "Día de Muertos"),
            ("2026-12-12", "Día de la Virgen de Guadalupe"),
        ],
    },
}


def is_bancario_verified(year: int) -> bool:
    """Whether ``year``'s bank additions are pinned from the DOF (``published``)
    rather than the computed default. A payment vence that must be exact and
    client-visible reads this before trusting the year's bancario calendar."""
    return year in _CNBV_PINNED


def inhabiles_bancarios_adicionales(year: int) -> List[FeriadoFact]:
    """CNBV bank-closed days that are NOT Art. 74 holidays: Jueves y Viernes
    Santo, el 2 de noviembre and el 12 de diciembre. For a pinned year these are
    the DOF-verified list (``published``); otherwise the computed default
    (Semana Santa via Easter + the two fixed dates), emitted ``seed-unverified``
    — orienting, but never asserting a closed day for a payment vence until the
    year's CNBV calendar is read. Ordered by date."""
    banco = ("bancario",)
    pin = _CNBV_PINNED.get(year)
    if pin is not None:
        source = pin["source"]  # type: ignore[index]
        cite = (
            f"CNBV días inhábiles {year} — DOF {source['dof_codigo']} "  # type: ignore[index]
            f"({source['dof_fecha']})"  # type: ignore[index]
        )
        return sorted(
            (
                FeriadoFact(d, "inhabil_bancario", banco, title, cite, PUBLISHED)
                for d, title in pin["adicionales"]  # type: ignore[index]
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
    pin = _CNBV_PINNED.get(year)
    if pin is not None:
        bancario_source = {
            **pin["source"],  # type: ignore[dict-item]
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
