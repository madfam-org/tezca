"""
SEP calendario-escolar normative-corpus fetcher + date extractor.

Each school year the Secretaría de Educación Pública (SEP) fixes the
**calendario escolar para la educación básica** and publishes it in the DOF
as an *acuerdo* (an administrative instrument, not a ``ley``). For the ciclo
lectivo 2026-2027 that is **Acuerdo número 07/07/26**, DOF 2026-07-15,
``codigo`` 5793645. Modeled — like the JCF Reglas de Operación
(:mod:`apps.scraper.federal.jcf_scraper`) and the RMF/NOM feeds — as
``law_type="non_legislative"`` with ``category="calendario_escolar"`` and
``domains=["education"]``. Calling this acuerdo a "ley" would be a lie the
corpus would then propagate to every consumer.

Why a fetcher and not a scraper: the corpus is a *small, enumerated* set of
DOF notes, one per ciclo, each with a known pinned ``codigo`` (verified
against primary DOF/SEP text on 2026-08-22). There is nothing to crawl — we
fetch by identity, exactly as the JCF fetcher does. The
:mod:`apps.scraper.federal.dof_daily` corpus-watch (see
``SEP_CALENDARIO_WATCH`` below) is what discovers *next* year's acuerdo so a
new pinned entry can be added.

Two distinct artifacts come out of this module:

1. **The legal corpus** — the acuerdo's operative prose (Artículos PRIMERO
   a TERCERO, which fix the 185/190-day counts and the ciclo start/end
   dates) rendered as AKN so ``index_laws`` makes each article addressable,
   plus the archived note text. This is what ``ingest_sep_calendario``
   registers as a Law + LawVersion.

2. **The machine-readable dates artifact** (``extract_calendar_dates``) —
   the day-level suspensiones, periodos vacacionales, juntas de Consejo
   Técnico Escolar and ciclo bounds, in the shape kalya's organizational-
   calendar generator consumes (``docs/data/SEP_CALENDARIO_ESCOLAR.md``).
   The acuerdo's *prose* fixes only the counts and the ciclo bounds; the
   day-level markers live in the acuerdo's **annex calendar images** (the
   DGPPyEE grid published inside the DOF note). Those images are the source
   of the singles/ranges, so every extracted date cites either an article
   of the prose or the annex grid + its legend, and the values are pinned
   and verified rather than OCR'd at runtime — an image the corpus cannot
   re-parse deterministically must not silently drift the dates kalya
   subtracts from availability.

Retrieval path (both verified live 2026-08-22, HTTP 200 with full text):

1. **SIDOF** ``https://sidof.segob.gob.mx/notas/docFuente/{codigo}`` —
   preferred, clean note HTML.
2. **DOF** ``https://dof.gob.mx/nota_detalle.php?codigo=...&fecha=...`` —
   fallback, and the citable canonical URL recorded on the Law row.

Usage::

    python -m apps.scraper.federal.sep_calendario_scraper                # catalog + dates
    python -m apps.scraper.federal.sep_calendario_scraper --download     # + fetch note text
    python -m apps.scraper.federal.sep_calendario_scraper --output-dir data/sep_calendario
"""

import argparse
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from xml.sax.saxutils import escape

import requests
from bs4 import BeautifulSoup

from apps.scraper.federal.sep_calendario_dates import (
    SEP_CALENDAR_DATES,
    CalendarEventFact,
)
from apps.scraper.http import DEFAULT_TIMEOUT, DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Source endpoints
# ---------------------------------------------------------------------------

SIDOF_NOTE_URL = "https://sidof.segob.gob.mx/notas/docFuente/{codigo}"
DOF_NOTE_URL = "https://dof.gob.mx/nota_detalle.php?codigo={codigo}&fecha={fecha}"

# Category + domains assigned to ingested Law records. "calendario_escolar"
# is deliberately its own type (as "reglas_de_operacion" is for JCF): the
# instrument is a yearly SEP acuerdo, not a ley, and later ciclos land in
# the same bucket instead of each minting a private category.
SEP_CATEGORY = "calendario_escolar"
SEP_DOMAINS = ["education"]

SEP_ISSUER = "Secretaría de Educación Pública"

# ---------------------------------------------------------------------------
# Behavior knobs
# ---------------------------------------------------------------------------

_MIN_REQUEST_INTERVAL = 1.0  # seconds — polite to segob/DOF
_REQUEST_TIMEOUT = DEFAULT_TIMEOUT
_MAX_RETRIES = 3

# ---------------------------------------------------------------------------
# Article heading grammar
#
# The acuerdo's operative body numbers its provisions with masculine Spanish
# ordinals as "ARTÍCULO PRIMERO.-", "ARTÍCULO SEGUNDO.-", "ARTÍCULO
# TERCERO.-". index_laws already strips the "ARTÍCULO " prefix, so <num>
# carries the full "ARTÍCULO PRIMERO" and consumers cite article "PRIMERO".
# The DOF hard-wraps the heading across lines ("ARTÍCULO" / "PRIMERO.-"), so
# the matcher tolerates the ordinal arriving on the line after the keyword.
# ---------------------------------------------------------------------------

_ARTICLE_ORDINALS = ("PRIMERO", "SEGUNDO", "TERCERO", "CUARTO", "QUINTO")
_ARTICLE_HEADING = re.compile(
    r"^ART[IÍ]CULO\s+(" + "|".join(_ARTICLE_ORDINALS) + r")\s*\.?-?\s*(.*)$"
)
# Body ends at the transitorios (which restart ordinal numbering).
_BODY_TERMINATORS = ("TRANSITORIOS", "TRANSITORIO")


@dataclass
class SepCalendarDocument:
    """A single SEP calendario-escolar acuerdo published in the DOF.

    Mirrors :class:`~apps.scraper.federal.jcf_scraper.JcfDocument`: an
    ``official_id`` plus enough metadata to derive a Law + LawVersion row,
    the URLs needed to retrieve text, and the ``ciclo`` this calendar
    governs (the year-over-year identity kalya keys its
    ``OrganizationalCalendar`` on).
    """

    official_id: str
    name: str
    short_name: str
    ciclo: str  # "2026-2027" — consecutive years, matches kalya's OrganizationalCalendar.ciclo
    dof_codigo: str
    publication_date: str  # ISO, DOF publication date
    valid_from: Optional[str]  # ISO, entry into force
    document_type: str = "acuerdo"
    status: str = "vigente"  # "vigente" | "abrogada" | "unknown"
    issuer: str = SEP_ISSUER
    # Free-text note on vigencia surfaced on LawVersion.change_summary.
    vigencia_note: str = ""
    # Fragment that MUST appear in the retrieved note for it to be accepted
    # as this document. DOF `codigo` values are opaque and adjacent codes are
    # unrelated notes, so a mis-pinned digit silently yields a valid page for
    # the wrong law — the marker turns that class of error into a loud
    # failure instead of a corrupt corpus entry (the JCF fetcher's first pass
    # pinned a code that resolved to a judicial edicto; the marker is why).
    title_marker: str = "calendario"
    category: str = SEP_CATEGORY
    domains: List[str] = field(default_factory=lambda: list(SEP_DOMAINS))
    source: str = "sep_calendario_dof_fetcher"

    @property
    def dof_url(self) -> str:
        """Canonical, citable DOF URL (the one recorded on the Law row)."""
        return DOF_NOTE_URL.format(
            codigo=self.dof_codigo, fecha=_dof_fecha(self.publication_date)
        )

    @property
    def sidof_url(self) -> str:
        """SIDOF mirror — preferred for retrieval (clean HTML)."""
        return SIDOF_NOTE_URL.format(codigo=self.dof_codigo)

    @property
    def text_filename(self) -> str:
        return f"{self.official_id}.xml"


def _dof_fecha(iso_date: str) -> str:
    """Convert ``YYYY-MM-DD`` to the DOF's ``DD/MM/YYYY`` query format."""
    year, month, day = iso_date.split("-")
    return f"{day}/{month}/{year}"


# ---------------------------------------------------------------------------
# The corpus.
#
# Every field below was verified against primary DOF (codigo 5793645) and
# SEP (educacionbasica.sep.gob.mx) text on 2026-08-22. This is an enumerated
# set, one acuerdo per ciclo — see module docstring.
# ---------------------------------------------------------------------------

SEP_CALENDAR_DOCUMENTS: List[SepCalendarDocument] = [
    SepCalendarDocument(
        official_id="sep-calendario-escolar-2026-2027",
        name=(
            "ACUERDO número 07/07/26 por el que se establecen los "
            "calendarios escolares para el ciclo lectivo 2026-2027, "
            "aplicables en toda la República para la educación preescolar, "
            "primaria, secundaria, normal y demás para la formación de "
            "maestras y maestros de educación básica"
        ),
        short_name="Calendario Escolar SEP 2026-2027 (educación básica)",
        ciclo="2026-2027",
        dof_codigo="5793645",
        publication_date="2026-07-15",
        # Transitorio Primero: "entrará en vigor al día siguiente de su
        # publicación en el Diario Oficial de la Federación". 2026-07-15 is
        # a Wednesday, so the next day is 2026-07-16.
        valid_from="2026-07-16",
        document_type="acuerdo",
        status="vigente",
        vigencia_note=(
            "Instrumento primario en vigor para el ciclo lectivo 2026-2027. "
            "185 días para educación básica (preescolar, primaria, "
            "secundaria) y 190 días para educación normal. Inicio de cursos "
            "lunes 31 de agosto de 2026; conclusión viernes 9 de julio de "
            "2027 (básica) y martes 13 de julio de 2027 (normal). "
            "Transitorio Segundo abroga el Acuerdo 18/06/25 (calendario "
            "2025-2026, DOF 2025-06-09) una vez concluida su vigencia. Las "
            "suspensiones, periodos vacacionales y sesiones de Consejo "
            "Técnico Escolar constan en la imagen del calendario anexa a la "
            "nota (grid DGPPyEE), no en el articulado; ver "
            "docs/data/SEP_CALENDARIO_ESCOLAR.md."
        ),
        # The instrument title is a "calendario ... calendarios escolares";
        # this fragment appears in both the DOF <title> and the body.
        title_marker="calendario",
    ),
    # NOTE — the abrogated 2025-2026 acuerdo (Acuerdo 18/06/25, DOF
    # 2025-06-09) is deliberately NOT listed. It is abrogated by
    # 07/07/26 and has no bearing on any current ciclo. Add a historical
    # entry here only if an operator confirms its DOF `codigo` against the
    # edition of 2025-06-09 (the daily index lists a partial highlights set,
    # so the codigo must be verified, not assumed — same discipline the JCF
    # corpus applied to its own abrogated ROP).
]

# Indexed by official_id for O(1) lookup by the ingest command + tests.
SEP_CALENDAR_DOCUMENTS_BY_ID: Dict[str, SepCalendarDocument] = {
    doc.official_id: doc for doc in SEP_CALENDAR_DOCUMENTS
}
SEP_CALENDAR_DOCUMENTS_BY_CICLO: Dict[str, SepCalendarDocument] = {
    doc.ciclo: doc for doc in SEP_CALENDAR_DOCUMENTS
}


# The pinned day-level dates + the CalendarEventFact taxonomy live in
# sep_calendario_dates.py (split out so the annex-grid reading is one
# auditable data module). extract_calendar_dates below assembles them
# into the artifact kalya consumes.


def extract_calendar_dates(ciclo: str = "2026-2027") -> Dict[str, object]:
    """Return the machine-readable dates artifact for a ciclo.

    The shape is documented in ``docs/data/SEP_CALENDARIO_ESCOLAR.md`` and
    matches kalya's organizational-calendar input contract: a header
    identifying the source acuerdo, then ``events`` — a flat list in kalya's
    CalendarEvent taxonomy (``date``/``end_date``/``type``/``title``/
    ``source``/``source_ref``), ordered by date. Raises ``KeyError`` for an
    unknown ciclo rather than inventing one.
    """
    document = SEP_CALENDAR_DOCUMENTS_BY_CICLO[ciclo]
    buckets = SEP_CALENDAR_DATES[ciclo]

    facts: List[CalendarEventFact] = (
        list(buckets["ciclo_bounds"])
        + list(buckets["suspensiones"])
        + list(buckets["periodos_vacacionales"])
        + list(buckets["consejo_tecnico"])
    )
    facts.sort(key=lambda f: (f.date, f.end_date or f.date, f.event_type))

    return {
        "schema": "tezca.sep_calendario/v1",
        "ciclo": ciclo,
        "nivel": "educacion_basica",
        "dias_habiles": 185,
        "source": {
            "instrumento": document.name,
            "acuerdo": "07/07/26",
            "dof_codigo": document.dof_codigo,
            "dof_fecha_publicacion": document.publication_date,
            "dof_url": document.dof_url,
            "sidof_url": document.sidof_url,
            "emisor": document.issuer,
            "vigente_desde": document.valid_from,
        },
        "extraction": {
            "verified_on": "2026-08-22",
            "method": (
                "cell-by-cell read of the DOF annex grid image, cross-checked "
                "against the SEP summary and the client's printed calendar"
            ),
            "annex_image": (
                "data/sep_calendario/sep-calendario-2026-2027-basica-annex.png"
            ),
        },
        "events": [fact.to_json() for fact in facts],
    }


# ---------------------------------------------------------------------------
# Text extraction (the legal corpus prose → AKN)
# ---------------------------------------------------------------------------


def html_to_lines(html: str) -> List[str]:
    """Flatten a DOF/SIDOF note into non-empty, stripped text lines."""
    text = BeautifulSoup(html, "html.parser").get_text("\n")
    return [line.strip() for line in text.split("\n") if line.strip()]


def _is_body_terminator(line: str) -> bool:
    stripped = line.rstrip(".").strip().upper()
    return stripped in _BODY_TERMINATORS


# A bare "ARTÍCULO" heading line (the DOF hard-wraps the ordinal onto the
# next line: "ARTÍCULO" / "PRIMERO.-"). Only the exact keyword, so a
# considerando that happens to end a wrapped line with the word "artículo"
# does not trip it.
_BARE_ARTICLE_KEYWORD = re.compile(r"^ART[IÍ]CULO$", re.IGNORECASE)
_BARE_ORDINAL = re.compile(
    r"^(" + "|".join(_ARTICLE_ORDINALS) + r")\b.*$", re.IGNORECASE
)


def _rejoin_split_headings(lines: List[str]) -> List[str]:
    """Glue a lone ``ARTÍCULO`` line to the ordinal on the following line.

    The DOF's column layout sometimes breaks the heading right after the
    keyword, so "ARTÍCULO" and "PRIMERO.-" arrive as two lines. Left split,
    the heading matcher misses the article entirely (it happened to
    ARTÍCULO PRIMERO in the 2026-2027 acuerdo). This normalizes the pair back
    into one "ARTÍCULO PRIMERO.-" line before parsing.
    """
    out: List[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if (
            _BARE_ARTICLE_KEYWORD.match(line.strip())
            and idx + 1 < len(lines)
            and _BARE_ORDINAL.match(lines[idx + 1].strip())
        ):
            out.append(f"ARTÍCULO {lines[idx + 1].strip()}")
            idx += 2
            continue
        out.append(line)
        idx += 1
    return out


def parse_articles(html: str) -> List[Dict[str, str]]:
    """Split the acuerdo's operative body into one entry per artículo.

    Returns ``{"num", "heading", "text"}`` dicts in document order, stopping
    at the transitorios. Returns ``[]`` when no article headings are found
    (callers fall back to raw text). The acuerdo body starts only after the
    resolutive heading ("ACUERDO NÚMERO 07/07/26 POR EL QUE ..."), so the
    considerandos — which also contain no "ARTÍCULO" lines — are naturally
    skipped: nothing before the first ARTÍCULO heading is captured.
    """
    lines = html_to_lines(html)

    # Truncate at the transitorios first (so their bare "PRIMERO.-" /
    # "SEGUNDO.-" lines can never be misread as articles), then rejoin any
    # DOF-split "ARTÍCULO" / ordinal heading pairs in the body that remains.
    for idx, line in enumerate(lines):
        if _is_body_terminator(line):
            lines = lines[:idx]
            break

    lines = _rejoin_split_headings(lines)

    articles: List[Dict[str, str]] = []
    current: Optional[Dict[str, List[str]]] = None

    for line in lines:
        match = _ARTICLE_HEADING.match(line)
        if match:
            if current is not None:
                articles.append(_finalize_article(current))
            current = {
                "num": [f"ARTÍCULO {match.group(1).strip()}"],
                "heading": [match.group(2).strip()],
                "body": [],
            }
            continue
        if current is not None:
            current["body"].append(line)

    if current is not None:
        articles.append(_finalize_article(current))

    return articles


def _finalize_article(acc: Dict[str, List[str]]) -> Dict[str, str]:
    num = acc["num"][0]
    heading = acc["heading"][0].strip()
    body_lines = list(acc["body"])

    # DOF sometimes breaks the line right after the ordinal, dropping the
    # rubric onto the next line starting with a stray ".-".
    if not heading and body_lines and body_lines[0].lstrip().startswith(".-"):
        heading = body_lines.pop(0).lstrip(".- ").strip()

    if heading:
        body_lines.insert(0, heading)

    return {"num": num, "heading": heading, "text": _join_wrapped(body_lines)}


def _join_wrapped(lines: List[str]) -> str:
    """Rejoin DOF column wraps into readable paragraphs."""
    out: List[str] = []
    for line in lines:
        if out and not re.search(r"[.:;]$", out[-1]):
            out[-1] = f"{out[-1]} {line}"
        else:
            out.append(line)
    return "\n".join(out).strip()


def validate_article_sequence(articles: List[Dict[str, str]]) -> List[str]:
    """Return sequence problems (empty list = clean parse).

    The acuerdo numbers its articles consecutively from PRIMERO. A gap or a
    repeat means the parser mis-split the note.
    """
    if not articles:
        return ["no articles parsed"]

    seen = [a["num"].replace("ARTÍCULO", "").strip().upper() for a in articles]
    expected = list(_ARTICLE_ORDINALS[: len(seen)])
    problems: List[str] = []

    if len(seen) > len(_ARTICLE_ORDINALS):
        return [f"parsed {len(seen)} articles, beyond known ordinal sequence"]

    for position, (got, want) in enumerate(zip(seen, expected), start=1):
        if got != want:
            problems.append(f"position {position}: expected {want!r}, got {got!r}")

    duplicates = {n for n in seen if seen.count(n) > 1}
    if duplicates:
        problems.append(f"duplicate ordinals: {sorted(duplicates)}")

    return problems


# ---------------------------------------------------------------------------
# AKN emission (same shape index_laws consumes for JCF)
# ---------------------------------------------------------------------------

AKN_NS = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"


def _akn_eid(num: str) -> str:
    """Stable element id ("ARTÍCULO PRIMERO" → "articulo-primero")."""
    slug = num.lower()
    for accented, plain in (
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ú", "u"),
        ("ñ", "n"),
    ):
        slug = slug.replace(accented, plain)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


def build_akn(document: SepCalendarDocument, articles: List[Dict[str, str]]) -> str:
    """Render parsed articles as an AKN act that ``index_laws`` can consume."""
    frbr_base = f"/mx/fed/acuerdo/{document.publication_date}/{document.official_id}"
    parts = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<akomaNtoso xmlns="{AKN_NS}">',
        '  <act name="acuerdo">',
        "    <meta>",
        '      <identification source="#tezca-sep-calendario-fetcher">',
        "        <FRBRWork>",
        f'          <FRBRthis value="{frbr_base}/main"/>',
        f'          <FRBRuri value="{frbr_base}"/>',
        f'          <FRBRdate date="{document.publication_date}" name="Generation"/>',
        '          <FRBRauthor href="#sep"/>',
        '          <FRBRcountry value="mx"/>',
        "        </FRBRWork>",
        "        <FRBRExpression>",
        f'          <FRBRthis value="{frbr_base}/spa@/main"/>',
        f'          <FRBRuri value="{frbr_base}/spa@"/>',
        f'          <FRBRdate date="{document.publication_date}" name="Generation"/>',
        '          <FRBRauthor href="#tezca-sep-calendario-fetcher"/>',
        '          <FRBRlanguage language="spa"/>',
        "        </FRBRExpression>",
        "        <FRBRManifestation>",
        f'          <FRBRthis value="{frbr_base}/spa@/main.xml"/>',
        f'          <FRBRuri value="{frbr_base}/spa@/main.akn"/>',
        f'          <FRBRdate date="{document.publication_date}" name="Generation"/>',
        '          <FRBRauthor href="#tezca-sep-calendario-fetcher"/>',
        "        </FRBRManifestation>",
        "      </identification>",
        "    </meta>",
        "    <body>",
    ]

    for article in articles:
        eid = _akn_eid(article["num"])
        parts.append(f'      <article eId="{eid}" id="{eid}">')
        parts.append(f"        <num>{escape(article['num'])}</num>")
        if article.get("heading"):
            parts.append(f"        <heading>{escape(article['heading'])}</heading>")
        parts.append(f'        <paragraph eId="{eid}-para-1">')
        parts.append("          <content>")
        parts.append(f"            <p>{escape(article['text'])}</p>")
        parts.append("          </content>")
        parts.append("        </paragraph>")
        parts.append("      </article>")

    parts.append("    </body>")
    parts.append("  </act>")
    parts.append("</akomaNtoso>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------


class SepCalendarFetcher:
    """Retrieves the enumerated SEP calendario corpus (SIDOF, then DOF).

    Like the JCF fetcher there is no discovery step — the corpus is the
    pinned ``SEP_CALENDAR_DOCUMENTS`` list. This class handles retrieval,
    parsing into AKN, dates-artifact emission, and catalog emission for
    ``manage.py ingest_sep_calendario``.
    """

    def __init__(self, output_dir: str = "data/sep_calendario") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._session = self._build_session()
        self._last_request_at: float = 0.0

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "text/html, application/xhtml+xml, */*",
                "Accept-Language": "es-MX,es;q=0.9,en;q=0.5",
            }
        )
        return session

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_at
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_at = time.time()

    def _get(self, url: str) -> Optional[str]:
        """Polite GET returning decoded text, or None when unavailable."""
        for attempt in range(1, _MAX_RETRIES + 1):
            self._rate_limit()
            try:
                resp = self._session.get(url, timeout=_REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp.text
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response else None
                if status in (403, 404):
                    logger.warning("HTTP %s for %s", status, url)
                    return None
                logger.warning(
                    "HTTP %s for %s (attempt %d/%d)", status, url, attempt, _MAX_RETRIES
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                logger.warning(
                    "Network error for %s (attempt %d/%d): %s",
                    url,
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )
            time.sleep(2**attempt)
        logger.error("Giving up on %s after %d attempts", url, _MAX_RETRIES)
        return None

    def fetch_html(self, document: SepCalendarDocument) -> Optional[str]:
        """Retrieve a note's HTML: SIDOF first, DOF as fallback.

        Every retrieved note is identity-checked against the document's
        ``title_marker`` before being returned — a merely-successful fetch
        proves nothing, because an opaque mis-pinned ``codigo`` resolves to a
        perfectly valid page for the wrong instrument.
        """
        for url in (document.sidof_url, document.dof_url):
            html = self._get(url)
            if not html:
                logger.warning(
                    "Miss for %s (codigo %s) at %s",
                    document.official_id,
                    document.dof_codigo,
                    url,
                )
                continue
            if not self._identity_matches(document, html):
                logger.error(
                    "IDENTITY MISMATCH: codigo %s does not resolve to %r "
                    "(expected title marker %r). Refusing the document — "
                    "verify the codigo against the DOF edition of %s.",
                    document.dof_codigo,
                    document.official_id,
                    document.title_marker,
                    document.publication_date,
                )
                return None
            return html
        return None

    @staticmethod
    def _identity_matches(document: SepCalendarDocument, html: str) -> bool:
        """True when the retrieved note really is the pinned document."""
        marker = document.title_marker.strip().lower()
        if not marker:
            return True
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        if marker in title.lower():
            return True
        head = " ".join(html_to_lines(html)[:40]).lower()
        return marker in head

    def materialize(self, document: SepCalendarDocument) -> Optional[Path]:
        """Fetch a document and write its parsed AKN to ``output_dir``.

        Returns the written path, or None when retrieval or parsing failed
        (never a partial/empty file — a broken fetch must not masquerade as
        an ingested document).
        """
        html = self.fetch_html(document)
        if not html:
            return None

        articles = parse_articles(html)
        if not articles:
            logger.warning(
                "No articles parsed for %s — writing raw text instead",
                document.official_id,
            )
            raw_path = self.output_dir / f"{document.official_id}.txt"
            raw_path.write_text("\n".join(html_to_lines(html)), encoding="utf-8")
            return raw_path

        problems = validate_article_sequence(articles)
        if problems:
            logger.error(
                "Article sequence validation failed for %s: %s",
                document.official_id,
                "; ".join(problems),
            )
            return None

        path = self.output_dir / document.text_filename
        path.write_text(build_akn(document, articles), encoding="utf-8")
        logger.info(
            "Wrote %s (%d articles) → %s", document.official_id, len(articles), path
        )
        return path

    def write_catalog(self, documents: List[SepCalendarDocument]) -> Path:
        """Write the catalog ``manage.py ingest_sep_calendario`` consumes."""
        catalog_path = self.output_dir / "catalog.json"
        payload = []
        for doc in documents:
            entry = asdict(doc)
            entry["dof_url"] = doc.dof_url
            entry["sidof_url"] = doc.sidof_url
            entry["text_filename"] = doc.text_filename
            payload.append(entry)
        catalog_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return catalog_path

    def write_dates(self, ciclo: str) -> Path:
        """Write the machine-readable dates artifact for a ciclo."""
        artifact = extract_calendar_dates(ciclo)
        dates_path = self.output_dir / f"dates-{ciclo}.json"
        dates_path.write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return dates_path

    def run(self, download_documents: bool = False) -> Dict[str, object]:
        """Emit catalog + dates, optionally materializing note text."""
        documents = list(SEP_CALENDAR_DOCUMENTS)

        downloaded = 0
        errors = 0
        if download_documents:
            for doc in documents:
                if self.materialize(doc):
                    downloaded += 1
                else:
                    errors += 1

        catalog_path = self.write_catalog(documents)
        dates_paths = [self.write_dates(doc.ciclo) for doc in documents]

        result = {
            "corpus": "sep_calendario_escolar",
            "total": len(documents),
            "ciclos": [doc.ciclo for doc in documents],
            "downloaded": downloaded,
            "errors": errors,
            "catalog_path": str(catalog_path),
            "dates_paths": [str(p) for p in dates_paths],
        }
        logger.info("SEP calendario run complete: %s", result)
        return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch the SEP calendario-escolar corpus and emit dates"
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Fetch each acuerdo from SIDOF/DOF and write parsed AKN (slow)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/sep_calendario",
        help="Where to write catalog + dates + text",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    fetcher = SepCalendarFetcher(output_dir=args.output_dir)
    result = fetcher.run(download_documents=args.download)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
