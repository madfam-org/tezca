"""Law-name normalisation for the Cámara de Diputados catalog.

The LeyesBiblio index (``index.htm``) prints, in ONE table cell, the law's
title followed by its DOF publication date and an optional status marker,
separated by line breaks and runs of tabs::

    LEY Federal de Protección de Datos Personales en Posesión de los
    Particulares \\t\\t\\t\\t \\t\\t\\t\\tDOF 20/03/2025 \\t\\t\\t\\t \\t\\t\\t\\tNueva reforma

``catalog_spider`` used the cell's whole ``text_content()`` as the name, so the
date and the marker were stored inside ``Law.name`` (287 of the 341 registry
entries). This module splits that cell text into its parts.

The date printed in the cell is the law's ORIGINAL DOF publication date (Ley
Aduanera → ``DOF 15/12/1995``), not the date of its latest reform. «Nueva
reforma» only flags that the index was updated recently. The latest-reform date
lives in the PDF header, see ``apps.parsers.diputados_pdf``.

Pure (``re`` only): safe to call from the scraper, the registry loader, the
database saver and data-fix commands. Every function is idempotent.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

_D = r"\d{1,2}/\d{1,2}/\d{4}"

# "DOF 20/03/2025"; the Ordenanza General de la Armada prints a range
# ("DOF 01 al 08/01/1912"), which has no single date to capture.
_DOF_TOKEN = rf"DOF\s+(?:(?P<range>\d{{1,2}}\s+al\s+{_D})|(?P<date>{_D}))"

# Parenthetical notes the index appends to a title. They start with one of a
# few fixed words, which keeps a parenthesis that belongs to the title itself
# ("… (LEY que establece, reforma y adiciona …)") in the name.
_NOTE = r"\((?:Antes\b|\"Recupera|“Recupera|Declaratoria\b|Abrogad[oa]\b)[^()]*\)"

# Status markers printed after the date.
_MARKER = (
    r"(?:"
    rf"Nueva\s+reforma"
    rf"|Nueva\s+Ley(?:\s+en\s+vigor(?:\s+a\s+partir\s+del)?\s+{_D})?"
    rf"|Nuevo\s+(?:Presupuesto|C[óo]digo|Reglamento)"
    rf"(?:\s+en\s+vigor(?:\s+a\s+partir\s+del)?\s+{_D})?"
    rf"|En\s+actualizaci[óo]n"
    rf"|Ley\s+abrogada(?:\s+a\s+partir\s+del\s+{_D})?"
    r")"
)

# title [note] DOF-date [marker|note]… — anchored at both ends, so a title
# that merely mentions "DOF dd/mm/yyyy" in running text is left alone.
_CATALOG_CELL_RE = re.compile(
    rf"^(?P<title>.+?)"
    rf"(?:\s+(?P<pre_note>{_NOTE}))?"
    rf"\s+{_DOF_TOKEN}"
    rf"(?P<trail>(?:\s+(?:{_MARKER}|{_NOTE}))*)\s*$",
    re.IGNORECASE | re.DOTALL,
)

# A cell with no date but a trailing marker ("… \t Nueva reforma").
_TRAILING_MARKERS_RE = re.compile(
    rf"^(?P<title>.+?)(?P<trail>(?:\s+{_MARKER})+)\s*$",
    re.IGNORECASE | re.DOTALL,
)

_LAYOUT_RE = re.compile(r"[\t\r\n]")

_TRAIL_PART_RE = re.compile(rf"{_MARKER}|{_NOTE}", re.IGNORECASE)

SHORT_NAME_LENGTH = 50


@dataclass
class CatalogTitle:
    """The parts of one catalog cell."""

    name: str
    # ISO date (YYYY-MM-DD) of the original DOF publication, when printed.
    publication_date: Optional[str] = None
    # Status markers and parenthetical notes, in the order printed.
    notes: List[str] = field(default_factory=list)


def collapse_whitespace(text: Optional[str]) -> str:
    """Collapse every whitespace run (tabs, newlines, NBSP) to one space."""
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def _iso_date(dmy: str) -> Optional[str]:
    day, month, year = (int(part) for part in dmy.split("/"))
    if not (1 <= day <= 31 and 1 <= month <= 12 and 1800 <= year <= 2200):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_catalog_title(raw: Optional[str]) -> CatalogTitle:
    """Split a LeyesBiblio index cell into name, publication date and notes.

    A string that is already a clean name comes back unchanged (apart from
    collapsed whitespace), so this is safe to apply to any law name.
    """
    text = collapse_whitespace(raw)
    if not text:
        return CatalogTitle(name="")

    match = _CATALOG_CELL_RE.match(text)
    if match:
        notes = []
        if match.group("pre_note"):
            notes.append(match.group("pre_note"))
        notes.extend(m.group(0) for m in _TRAIL_PART_RE.finditer(match.group("trail")))
        date = _iso_date(match.group("date")) if match.group("date") else None
        return CatalogTitle(
            name=match.group("title").strip(),
            publication_date=date,
            notes=[collapse_whitespace(n) for n in notes],
        )

    # Without a date the only evidence of a marker is the cell layout, so the
    # fallback needs the raw tabs/line breaks: "Reglamento de la Nueva Ley" is
    # a name, "Ley X \t Nueva Ley" is a name plus a marker.
    match = _TRAILING_MARKERS_RE.match(text) if _LAYOUT_RE.search(raw) else None
    if match:
        notes = [m.group(0) for m in _TRAIL_PART_RE.finditer(match.group("trail"))]
        return CatalogTitle(name=match.group("title").strip(), notes=notes)

    return CatalogTitle(name=text)


def normalize_law_name(raw: Optional[str]) -> str:
    """The law's name without catalog debris. Idempotent."""
    return parse_catalog_title(raw).name


def has_catalog_debris(raw: Optional[str]) -> bool:
    """True when ``raw`` would be changed by ``normalize_law_name``."""
    return (raw or "") != normalize_law_name(raw)


def build_short_name(name: str, length: int = SHORT_NAME_LENGTH) -> str:
    """The registry's short-name convention: first 50 chars plus "..."."""
    return name[:length] + "..." if len(name) > length else name


def normalize_short_name(short_name: Optional[str], raw_name: Optional[str]) -> str:
    """Repair a short name that was cut from a debris-carrying name.

    ``merge_discovery`` built ``short_name`` as the first 50 characters of the
    raw cell text, so short titles kept the tabs and the date
    ("LEY Aduanera \\t\\t\\t\\t \\t\\t\\t\\tDOF 15/12/1995 …"). Such a derived
    short name is rebuilt from the clean name; a curated one ("Reglamento de
    la LFPDPPP") is kept.
    """
    clean_name = normalize_law_name(raw_name)
    if not short_name or short_name == build_short_name(raw_name or ""):
        return build_short_name(clean_name)
    return collapse_whitespace(short_name)
