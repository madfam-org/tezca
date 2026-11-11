"""Text clean-up for Cámara de Diputados consolidated-law PDFs (LeyesBiblio).

Every page of those PDFs carries the same furniture::

    LEY FEDERAL DE PROTECCIÓN DE DATOS PERSONALES EN POSESIÓN DE LOS PARTICULARES
    CÁMARA DE DIPUTADOS DEL H. CONGRESO DE LA UNIÓN     Última Reforma DOF 14-11-2025
    Secretaría General
    Secretaría de Servicios Parlamentarios
    … page body …
    1 de 24

``IngestionPipeline`` joined the pages as extracted, so the footer of one page
and the header of the next landed in the middle of whatever article straddled
the page break, sometimes mid-sentence.

This module removes that furniture, reads the «Última Reforma DOF» date the
header states, and cuts the decree closing (signatures, promulgation, the
"ARTÍCULOS TRANSITORIOS DE DECRETOS DE REFORMA" preamble) off the end of a
provision. Two entry points for the furniture, because the text exists in two
shapes:

* ``strip_page_furniture`` — one page as extracted, line by line. Used at
  extraction time, where the page boundaries are known.
* ``strip_furniture`` — any text that already has the furniture embedded
  (legacy extracted text, article text read back from a stored XML). Used at
  index time so a re-index of an existing XML is clean without a re-download.

Pure (``re`` and ``datetime`` only).
"""

import re
from datetime import date
from typing import Iterable, List, Optional, Sequence, Set

_CHAMBER = r"C[ÁA]MARA\s+DE\s+DIPUTADOS\s+DEL\s+H\.\s+CONGRESO\s+DE\s+LA\s+UNI[ÓO]N"
_SERVICES = r"Secretar[íi]a\s+de\s+Servicios\s+Parlamentarios"
_GENERAL = r"Secretar[íi]a\s+General"

_CHAMBER_RE = re.compile(_CHAMBER)
_SERVICES_RE = re.compile(_SERVICES)

# "1 de 24" on a line of its own. "el 21 de enero de 2025" never matches: the
# counter is the whole line.
_COUNTER_LINE_RE = re.compile(r"^[ \t]*(\d{1,4}) de (\d{1,4})[ \t]*$")

# How many leading lines of a page may belong to the header.
_HEADER_SCAN_LINES = 8

# The header as it appears inside running text. Between a page counter and the
# chamber line, everything is header (the law's title, which is printed in
# capitals and may wrap); without a counter only capitals on the chamber's own
# line are taken, so a real heading above the header is never swallowed.
_NO_LOWER = r"[^a-záéíóúüñ\n]"
_EMBEDDED_HEADER_RE = re.compile(
    r"(?:(?P<counter>(?:^|(?<=\n))[ \t]*(?P<n>\d{1,4}) de (?P<m>\d{1,4})[ \t]*\n)"
    rf"(?:{_NO_LOWER}*\n){{0,3}}?)?"
    rf"(?:^|(?<=\n))[ \t]*{_NO_LOWER}{{0,600}}?{_CHAMBER}"
    r"[^\n]{0,80}"  # "Última Reforma DOF 14-11-2025", "Nueva Ley DOF …"
    rf"\s+{_GENERAL}\s+{_SERVICES}[ \t]*\n?"
)

_LAST_REFORM_RE = re.compile(
    r"[ÚU]ltimas?\s+Reformas?(?:\s+publicadas?)?(?:\s+en\s+el)?\s+DOF\s+"
    r"(\d{1,2})-(\d{1,2})-(\d{4})",
    re.IGNORECASE,
)

# Where the header is looked for. It is on page 1; legacy extracted text keeps
# it within the first few hundred characters.
_HEADER_WINDOW = 6000

_MONTH = r"[a-záéíóúñ]+"
# Lines that close a decree. Everything from the first of them to the end of a
# provision is not the provision's text.
_DECREE_TAIL_RE = re.compile(
    r"^[ \t]*(?:"
    # Section heading of the reform decrees appended to a consolidated law.
    r"ART[ÍI]CULOS\s+TRANSITORIOS\s+DE\s+(?:LOS\s+)?DECRETOS\s+DE\s+REFORMA\b"
    # Congress signature block: "Ciudad de México, a 20 de marzo de 2025.- Sen. …"
    r"|(?:Ciudad\s+de\s+M[ée]xico|M[ée]xico,\s*D\.\s?F\.),?\s+a\s+(?:los\s+)?"
    rf"\d{{1,2}}\S{{0,2}}\s+(?:d[ií]as\s+del\s+mes\s+)?de\s+{_MONTH}\s+de\s+"
    r"\d{4}\s*\.\s*-"
    # Promulgation by the Executive.
    r"|En\s+cumplimiento\s+de\s+lo\s+dispuesto\s+por\s+la\s+fracci[óo]n\s+I\s+"
    r"del\s+Art[íi]culo\s+89\b"
    r")",
    re.MULTILINE | re.IGNORECASE,
)
# A reform decree's title, on a new line right after a sentence ended. The
# preceding full stop keeps a wrapped reference to «… el\nDECRETO por el que …»
# inside a provision.
_DECREE_TITLE_RE = re.compile(r"(?<=[.\"”])[ \t]*\n[ \t]*DECRETO\s+por\s+el\s+que\b")

_ORDINAL = (
    r"(?:primer|segund|tercer|cuart|quint|sext|s[ée]ptim|octav|noven|"
    r"und[ée]cim|duod[ée]cim|d[ée]cim|vig[ée]sim|trig[ée]sim|cuadrag[ée]sim|"
    r"quincuag[ée]sim|[úu]nic)[oa]"
)
# "Artículo Cuarto.- ……..": the stub a consolidated law keeps for the articles
# of its publishing decree that concern OTHER laws. Only a stub whose whole
# content is an ellipsis is furniture; a decree article with text is kept.
_DECREE_STUB_LINE_RE = re.compile(
    rf"^[ \t]*Art[íi]culo\s+{_ORDINAL}(?:\s+{_ORDINAL})?\s*\.\s*-?[ \t]*[.…\s]+$",
    re.IGNORECASE,
)
_TRANSITORIOS_LINE_RE = re.compile(
    r"^[ \t]*(?:ART[ÍI]CULOS?\s+)?TRANSITORIOS?[ \t]*$", re.IGNORECASE
)


def extract_last_reform_date(text: Optional[str]) -> Optional[date]:
    """The «Última Reforma DOF dd-mm-yyyy» date stated by the PDF header.

    ``None`` when the header states no reform ("Nueva Ley DOF …", "Sin
    reforma") or the date is not a real one. Call it BEFORE the furniture is
    stripped.
    """
    if not text:
        return None
    match = _LAST_REFORM_RE.search(text[:_HEADER_WINDOW])
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _last_line_counter(lines: Sequence[str]):
    """``(index, n, m)`` of a page's last non-empty line if it is ``N de M``."""
    last = len(lines) - 1
    while last >= 0 and not lines[last].strip():
        last -= 1
    if last < 0:
        return None
    counter = _COUNTER_LINE_RE.match(lines[last])
    if not counter:
        return None
    n, m = int(counter.group(1)), int(counter.group(2))
    return (last, n, m) if 1 <= n <= m else None


def strip_page_furniture(
    page_text: Optional[str], page_total: Optional[int] = None
) -> str:
    """Remove the Diputados header and the ``N de M`` footer from ONE page.

    The header is only removed when both the chamber line and the «Secretaría
    de Servicios Parlamentarios» line are within the first lines of the page,
    so a page of any other source comes back untouched. The footer is only
    removed when it is the page's last line and, if the caller knows the
    document's page total, its ``M`` is that total.
    """
    if not page_text:
        return ""
    lines = page_text.split("\n")

    counter = _last_line_counter(lines)
    if counter and (page_total is None or counter[2] == page_total):
        lines = lines[: counter[0]]

    # Header: the first lines, through the "Servicios Parlamentarios" line.
    seen_chamber = False
    scanned = 0
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        scanned += 1
        if scanned > _HEADER_SCAN_LINES:
            break
        if _CHAMBER_RE.search(line):
            seen_chamber = True
        services = _SERVICES_RE.search(line)
        if services and seen_chamber:
            remainder = line[services.end() :].strip()
            lines = ([remainder] if remainder else []) + lines[idx + 1 :]
            break

    return "\n".join(lines).strip("\n")


def join_pages(pages: Sequence[Optional[str]]) -> str:
    """Join per-page text into one document, without the page furniture.

    The footer total is taken from the pages themselves — the ``M`` that most
    pages end with — not from ``len(pages)``: pages with no extractable text
    are missing from ``pages``, so positions and counts need not agree with
    what the footers print. With no total shared by most pages, footers are
    left in place.
    """
    pages = [page for page in pages if page]
    counts = {}
    for page in pages:
        counter = _last_line_counter(page.split("\n"))
        if counter:
            counts[counter[2]] = counts.get(counter[2], 0) + 1
    page_total = None
    if counts:
        best = max(counts, key=counts.get)
        if counts[best] * 2 > len(pages):
            page_total = best

    cleaned = (
        strip_page_furniture(page, page_total=page_total if page_total else -1)
        for page in pages
    )
    return "\n".join(part for part in cleaned if part)


def find_page_totals(texts: Iterable[Optional[str]]) -> Set[int]:
    """The ``M`` of every ``N de M`` counter that sits right above a header.

    Those totals identify, for one document, which bare ``N de M`` lines are
    page counters (see ``strip_furniture``).
    """
    totals = set()
    for text in texts:
        for match in _EMBEDDED_HEADER_RE.finditer(text or ""):
            if match.group("m"):
                totals.add(int(match.group("m")))
    return totals


def _rejoin(before: str, after: str) -> str:
    """The separator that replaces furniture between ``before`` and ``after``.

    A page break inside a sentence ("…anterior, se" / "sustanciarán conforme…")
    is a line wrap, so the sentence is joined back with a space; anywhere else
    the line break the page break stood for is kept.
    """
    before = before.rstrip()
    after = after.lstrip()
    if not before or not after:
        return ""
    if re.search(r"[a-záéíóúüñ,;]$", before) and re.match(r"[a-záéíóúüñ]", after):
        return " "
    return "\n"


def strip_furniture(
    text: Optional[str], page_totals: Optional[Iterable[int]] = None
) -> str:
    """Remove Diputados page furniture embedded anywhere in ``text``.

    Removes every header (with the ``N de M`` counter above it, when present)
    and joins the text back across it. Bare counter lines with no header after
    them — the document's last page — are removed only when their total is one
    of ``page_totals`` or was seen above a header in this same text, so a line
    that merely looks like a counter is left alone. Idempotent.
    """
    if not text:
        return ""
    totals = set(page_totals or ())
    totals |= find_page_totals([text])

    parts: List[str] = []
    cursor = 0
    for match in _EMBEDDED_HEADER_RE.finditer(text):
        parts.append(text[cursor : match.start()])
        parts.append(None)  # furniture
        cursor = match.end()
    parts.append(text[cursor:])

    if len(parts) > 1:
        out = parts[0]
        for idx in range(1, len(parts), 2):
            following = parts[idx + 1]
            out = out.rstrip() + _rejoin(out, following) + following.lstrip()
        text = out

    if totals:
        kept = []
        for line in text.split("\n"):
            counter = _COUNTER_LINE_RE.match(line)
            if counter and int(counter.group(2)) in totals:
                if 1 <= int(counter.group(1)) <= int(counter.group(2)):
                    continue
            kept.append(line)
        text = "\n".join(kept)

    return text.strip()


def trim_decree_tail(text: Optional[str]) -> str:
    """Cut the decree closing off the end of a transitorio.

    The last transitorio of each decree block is followed by the signatures
    ("Ciudad de México, a 20 de marzo de 2025.- Sen. …"), the promulgation
    ("En cumplimiento de lo dispuesto por la fracción I del Artículo 89 …")
    and, in consolidated laws, the «ARTÍCULOS TRANSITORIOS DE DECRETOS DE
    REFORMA» heading plus the next decree's title. None of it is the
    transitorio's text. The cut never starts on the first line, so a provision
    is never emptied.
    """
    if not text:
        return ""
    first_break = text.find("\n")
    if first_break == -1:
        return text.strip()

    cut = len(text)
    tail = _DECREE_TAIL_RE.search(text, first_break + 1)
    if tail:
        cut = min(cut, tail.start())
    title = _DECREE_TITLE_RE.search(text)
    if title:
        cut = min(cut, title.start())
    return text[:cut].strip()


def strip_trailing_decree_stubs(text: Optional[str]) -> str:
    """Drop trailing ``Artículo Cuarto.- ……..`` stubs and a ``Transitorios`` line.

    The last body article of a law published inside a multi-article decree is
    followed by the ellipsis stubs of the decree's other articles and by the
    «Transitorios» heading; the legacy parser kept both in the article.
    """
    if not text:
        return ""
    lines = text.rstrip().split("\n")
    while len(lines) > 1 and (
        not lines[-1].strip()
        or _DECREE_STUB_LINE_RE.match(lines[-1])
        or _TRANSITORIOS_LINE_RE.match(lines[-1])
    ):
        lines.pop()
    return "\n".join(lines).rstrip()
