"""
The pinned, verified day-level dates of the SEP calendario escolar.

Split from :mod:`apps.scraper.federal.sep_calendario_scraper` (which fetches
the acuerdo and emits the artifact) so the *reading of the annex grid* lives
in one auditable place — a data module, not tangled with the fetcher logic.

These are the facts kalya's organizational-calendar generator consumes. They
are **pinned, not OCR'd at runtime**: the acuerdo publishes the day-level
markers only as a rasterized DGPPyEE grid inside the DOF note, which has no
deterministic machine-readable form, so the dates were read cell-by-cell from
the annex image
(``data/sep_calendario/sep-calendario-2026-2027-basica-annex.png``) and
cross-checked against SEP's own summary (educacionbasica.sep.gob.mx) and the
client's independently-printed calendar, all on 2026-08-22. Each fact carries
a ``source_ref`` tracing it to the acuerdo's prose (an article) or the annex
grid + its legend, so the extraction is auditable rather than asserted.
Correcting a date means correcting it here, under review.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

# Legend of the DGPPyEE annex grid (educación básica, 185 días):
#   black filled circle = "suspensión de labores docentes"
#   grey                = "vacaciones"
#   dark teal           = "receso de clases"
#   wine                = "Consejo Técnico Escolar fase intensiva"
#   pink                = "Consejo Técnico Escolar sesión ordinaria"
#   hollow circle       = "jornada de concientización sobre el abuso ..."
#   black chevron       = "inicio / fin de clases del ciclo"
_ANNEX_REF = (
    "acuerdo 07/07/26, anexo: Calendario Escolar 2026-2027 educación "
    "básica (185 días), grid DGPPyEE"
)
_ANNEX_PLUS_SUMMARY_REF = (
    "acuerdo 07/07/26, anexo (grid DGPPyEE) + resumen SEP educacionbasica.sep.gob.mx"
)
_ARTICULO_TERCERO_REF = "acuerdo 07/07/26, ARTÍCULO TERCERO"


@dataclass
class CalendarEventFact:
    """One SEP-sourced calendar fact, in kalya's CalendarEvent taxonomy.

    ``date`` and ``end_date`` are inclusive ISO local dates (``end_date`` is
    ``None`` for a single-day event). ``event_type`` is one of kalya's
    taxonomy values (``suspension_sep``, ``periodo_vacacional``,
    ``junta_consejo_tecnico``, ``regreso_a_clases``,
    ``cierre_ciclo_preescolar``). ``source_ref`` traces the fact to the
    acuerdo text or its annex.
    """

    date: str
    end_date: Optional[str]
    event_type: str
    title: str
    source_ref: str

    def to_json(self) -> Dict[str, Optional[str]]:
        payload: Dict[str, Optional[str]] = {
            "date": self.date,
            "type": self.event_type,
            "title": self.title,
            "source": "sep",
            "source_ref": self.source_ref,
        }
        if self.end_date:
            payload["end_date"] = self.end_date
        return payload


def _suspension(date: str, label: str) -> CalendarEventFact:
    return CalendarEventFact(
        date,
        None,
        "suspension_sep",
        f"Suspensión de labores docentes ({label})",
        _ANNEX_REF,
    )


def _cte_ordinaria(date: str, nth: str) -> CalendarEventFact:
    return CalendarEventFact(
        date,
        None,
        "junta_consejo_tecnico",
        f"Consejo Técnico Escolar — {nth} sesión ordinaria",
        _ANNEX_REF,
    )


# Suspensión de labores docentes — single days marked with a black filled
# circle on the annex grid. Dic 25, Ene 1 and Ene 6 are the holidays that
# frame/punctuate the winter vacation block (they carry their own suspensión
# marker rather than the grey vacaciones fill).
_SUSPENSIONS_2026_2027: List[CalendarEventFact] = [
    _suspension("2026-09-16", "16 de septiembre"),
    _suspension("2026-11-02", "2 de noviembre"),
    _suspension("2026-11-16", "16 de noviembre"),
    _suspension("2026-12-25", "25 de diciembre"),
    _suspension("2027-01-01", "1 de enero"),
    _suspension("2027-01-06", "6 de enero"),
    _suspension("2027-02-01", "1 de febrero"),
    _suspension("2027-03-15", "15 de marzo"),
    _suspension("2027-05-05", "5 de mayo"),
]

# Periodos vacacionales — the two breaks. SEP's own summary states the
# envelope ("del 21 de diciembre de 2026 al 5 de enero de 2027, con regreso a
# clases el 7 de enero" — Ene 6 being the Reyes suspensión; and "del 22 de
# marzo al 3 de abril de 2027"). Modeled as the inclusive envelope SEP
# publishes, so kalya's availability subtraction closes the whole span; the
# holiday singles inside/adjacent are ALSO emitted above (a consumer that only
# reads periodo_vacacional still closes correctly, and one that reads both
# sees SEP's own typing).
_VACATIONS_2026_2027: List[CalendarEventFact] = [
    CalendarEventFact(
        "2026-12-21",
        "2027-01-05",
        "periodo_vacacional",
        "Periodo vacacional de invierno (regreso a clases 7 de enero de 2027)",
        _ANNEX_PLUS_SUMMARY_REF,
    ),
    CalendarEventFact(
        "2027-03-22",
        "2027-04-03",
        "periodo_vacacional",
        "Periodo vacacional de primavera (regreso a clases 5 de abril de 2027)",
        _ANNEX_PLUS_SUMMARY_REF,
    ),
]

# Consejo Técnico Escolar. The annex fixes a fase intensiva (a range, late
# August) plus eight sesiones ordinarias (SEP: "ocho sesiones ordinarias de
# CTE"). These are SEP-fixed dates, not a "last Friday" rule — kalya can still
# recognize they mostly fall on last Fridays, but the acuerdo pins the
# specific days, so they are emitted as sep-sourced.
_CONSEJO_TECNICO_2026_2027: List[CalendarEventFact] = [
    CalendarEventFact(
        "2026-08-24",
        "2026-08-28",
        "junta_consejo_tecnico",
        "Consejo Técnico Escolar — fase intensiva",
        _ANNEX_REF,
    ),
    _cte_ordinaria("2026-09-25", "1a"),
    _cte_ordinaria("2026-10-30", "2a"),
    _cte_ordinaria("2026-11-27", "3a"),
    _cte_ordinaria("2027-01-29", "4a"),
    _cte_ordinaria("2027-02-26", "5a"),
    _cte_ordinaria("2027-04-30", "6a"),
    _cte_ordinaria("2027-05-28", "7a"),
    _cte_ordinaria("2027-06-25", "8a"),
]

# Ciclo bounds — the ONLY day-level facts fixed in the acuerdo's prose
# (Artículo Tercero). básica: inicio 31-ago-2026, fin 9-jul-2027.
_CICLO_BOUNDS_2026_2027: List[CalendarEventFact] = [
    CalendarEventFact(
        "2026-08-31",
        None,
        "regreso_a_clases",
        "Inicio de cursos del ciclo lectivo 2026-2027 (educación básica)",
        _ARTICULO_TERCERO_REF,
    ),
    CalendarEventFact(
        "2027-07-09",
        None,
        "cierre_ciclo_preescolar",
        "Conclusión de cursos del ciclo lectivo 2026-2027 (educación básica)",
        _ARTICULO_TERCERO_REF,
    ),
]

# The extraction, keyed by ciclo. Adding next year's acuerdo means adding its
# document (in sep_calendario_scraper) and its dates here (the corpus watch
# flags when to do so).
SEP_CALENDAR_DATES: Dict[str, Dict[str, List[CalendarEventFact]]] = {
    "2026-2027": {
        "ciclo_bounds": _CICLO_BOUNDS_2026_2027,
        "suspensiones": _SUSPENSIONS_2026_2027,
        "periodos_vacacionales": _VACATIONS_2026_2027,
        "consejo_tecnico": _CONSEJO_TECNICO_2026_2027,
    },
}
