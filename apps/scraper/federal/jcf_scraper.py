"""
JCF (Jóvenes Construyendo el Futuro) normative-corpus fetcher.

JCF is the STPS apprenticeship program (Ramo 14, categoría programática
S280). Unlike the laws in ``data/law_registry.json``, it is not governed by
a ``ley`` at all: its operative norm is a set of **Reglas de Operación**
re-issued annually by the Secretaría del Trabajo y Previsión Social and
published in the DOF. That is an *administrative* instrument, so these
documents are ingested as ``law_type="non_legislative"`` with
``category="reglas_de_operacion"`` — the same modeling the RMF
(``resolución_miscelánea_fiscal``) and NOM (``norma_oficial_mexicana``)
feeds use. Calling a Regla de Operación a "ley" would be a lie the corpus
would then propagate to every consumer.

Why a fetcher and not a scraper: JCF's corpus is a *small, enumerated* set
of DOF notes, not a discoverable index. Each document's DOF ``codigo`` is
known and pinned in ``JCF_DOCUMENTS`` below (verified against primary text
on 2026-08-22). There is nothing to crawl — we fetch by identity. This is
deliberate: the DOF has no working open-data API for note text (the
``diariooficial.gob.mx`` WS_* endpoints in
``apps/scraper/federal/dof_api_client.py`` serve daily PDFs, not per-note
HTML), so pinned ``codigo`` values are the only stable addressing.

Retrieval path (both verified live 2026-08-22, HTTP 200 with full text):

1. **SIDOF** ``https://sidof.segob.gob.mx/notas/docFuente/{codigo}`` —
   preferred. Serves the clean note HTML with no WAF interstitial.
2. **DOF** ``https://dof.gob.mx/nota_detalle.php?codigo=...&fecha=...`` —
   fallback, and the citable canonical URL recorded on the Law row.

Structure: the Reglas de Operación number their provisions as Spanish
feminine ordinals ("PRIMERA." … "VIGÉSIMA SEXTA."), not "Artículo N".
:func:`parse_reglas` converts them to AKN articles whose ``<num>`` is the
ordinal, so ``index_laws`` indexes one addressable article per Regla and
consumers can cite ``jcf-reglas-2026`` article ``DÉCIMA QUINTA`` (the beca
amount) rather than a 180KB blob.

Usage::

    python -m apps.scraper.federal.jcf_scraper                    # catalog only
    python -m apps.scraper.federal.jcf_scraper --download         # + fetch text
    python -m apps.scraper.federal.jcf_scraper --output-dir data/jcf
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

from apps.scraper.http import DEFAULT_TIMEOUT, DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Source endpoints
# ---------------------------------------------------------------------------

SIDOF_NOTE_URL = "https://sidof.segob.gob.mx/notas/docFuente/{codigo}"
DOF_NOTE_URL = "https://dof.gob.mx/nota_detalle.php?codigo={codigo}&fecha={fecha}"

# Category + domains assigned to ingested Law records. "reglas_de_operacion"
# is deliberately generic: JCF is one program among many federal programs
# whose operative norm is an annually re-issued ROP, so later programs land
# in the same bucket instead of each minting a private category.
JCF_CATEGORY = "reglas_de_operacion"
JCF_DOMAINS = ["labor"]

# Program identity (DOF/PEF, not our invention)
JCF_PROGRAM = "Jóvenes Construyendo el Futuro"
JCF_PROGRAMMATIC_CATEGORY = "S280"
JCF_RAMO = "14"

# ---------------------------------------------------------------------------
# Behavior knobs
# ---------------------------------------------------------------------------

_MIN_REQUEST_INTERVAL = 1.0  # seconds — polite to segob/DOF
_REQUEST_TIMEOUT = DEFAULT_TIMEOUT
_MAX_RETRIES = 3

# ---------------------------------------------------------------------------
# Regla heading grammar
#
# Reglas de Operación number provisions as feminine Spanish ordinals in
# caps: "PRIMERA.", "DÉCIMA QUINTA", "VIGÉSIMA SEXTA.". A heading may carry
# an inline rubric on the same line ("DÉCIMA TERCERA. Medidas por
# incumplimiento."), and the trailing period is inconsistently present.
# ---------------------------------------------------------------------------

_TENS = r"(?:D[EÉ]CIMA|VIG[EÉ]SIMA|TRIG[EÉ]SIMA|CUADRAG[EÉ]SIMA)"
_UNITS = r"(?:PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|S[EÉ]PTIMA|OCTAVA|NOVENA)"
_ORDINAL = rf"(?:{_TENS}(?:\s+{_UNITS})?|{_UNITS})"
_REGLA_HEADING = re.compile(rf"^({_ORDINAL})\s*\.?\s*(.*)$")

# The ROP body ends where the transitorios begin; the annexes (model
# contracts, carta compromiso) restart ordinal numbering and would collide
# with the Reglas namespace if parsed into the same article space.
_BODY_TERMINATORS = ("TRANSITORIOS", "TRANSITORIO")

# Ordinal sequence used to validate that parsed Reglas run consecutively.
_ORDINAL_SEQUENCE = [
    "PRIMERA",
    "SEGUNDA",
    "TERCERA",
    "CUARTA",
    "QUINTA",
    "SEXTA",
    "SÉPTIMA",
    "OCTAVA",
    "NOVENA",
    "DÉCIMA",
    "DÉCIMA PRIMERA",
    "DÉCIMA SEGUNDA",
    "DÉCIMA TERCERA",
    "DÉCIMA CUARTA",
    "DÉCIMA QUINTA",
    "DÉCIMA SEXTA",
    "DÉCIMA SÉPTIMA",
    "DÉCIMA OCTAVA",
    "DÉCIMA NOVENA",
    "VIGÉSIMA",
    "VIGÉSIMA PRIMERA",
    "VIGÉSIMA SEGUNDA",
    "VIGÉSIMA TERCERA",
    "VIGÉSIMA CUARTA",
    "VIGÉSIMA QUINTA",
    "VIGÉSIMA SEXTA",
    "VIGÉSIMA SÉPTIMA",
    "VIGÉSIMA OCTAVA",
    "VIGÉSIMA NOVENA",
    "TRIGÉSIMA",
]


@dataclass
class JcfDocument:
    """A single JCF normative artifact published in the DOF.

    Mirrors ``RmfDocument``: an ``official_id`` plus enough metadata to
    derive a Law + LawVersion row, plus the URLs needed to retrieve text.
    """

    official_id: str
    name: str
    short_name: str
    dof_codigo: str
    publication_date: str  # ISO, DOF publication date
    valid_from: Optional[str]  # ISO, entry into force
    document_type: str  # "reglas_de_operacion" | "acuerdo"
    status: str  # "vigente" | "abrogada"
    issuer: str = "Secretaría del Trabajo y Previsión Social"
    # Free-text note on vigencia/residual status. Surfaces on LawVersion
    # so downstream consumers see *why* a document is or isn't controlling.
    vigencia_note: str = ""
    # Fragment that MUST appear in the retrieved note for it to be accepted
    # as this document. DOF `codigo` values are opaque and adjacent codes
    # are unrelated notes, so a mis-pinned digit silently yields a valid
    # page for the wrong law — which is exactly how an early draft of this
    # registry pointed at a judicial edicto. The marker turns that class of
    # error into a loud failure instead of a corrupt corpus entry.
    title_marker: str = JCF_PROGRAM
    category: str = JCF_CATEGORY
    domains: List[str] = field(default_factory=lambda: list(JCF_DOMAINS))
    source: str = "jcf_dof_fetcher"

    @property
    def dof_url(self) -> str:
        """Canonical, citable DOF URL (the one recorded on the Law row)."""
        fecha = _dof_fecha(self.publication_date)
        return DOF_NOTE_URL.format(codigo=self.dof_codigo, fecha=fecha)

    @property
    def sidof_url(self) -> str:
        """SIDOF mirror — preferred for retrieval (clean HTML, no WAF)."""
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
# Every field below was verified against primary DOF text on 2026-08-22.
# This is an enumerated set, not a discovered one — see module docstring.
# ---------------------------------------------------------------------------

JCF_DOCUMENTS: List[JcfDocument] = [
    JcfDocument(
        official_id="jcf-reglas-2026",
        name=(
            "REGLAS de Operación del Programa Jóvenes Construyendo el Futuro "
            "para el ejercicio fiscal 2026"
        ),
        short_name="Reglas de Operación JCF 2026",
        dof_codigo="5777674",
        publication_date="2025-12-31",
        # Transitorio Primero: "entrarán en vigor el día siguiente de su
        # publicación en el Diario Oficial de la Federación".
        valid_from="2026-01-01",
        document_type="reglas_de_operacion",
        status="vigente",
        vigencia_note=(
            "Instrumento primario en vigor. Ramo 14, categoría programática "
            "S280. Abroga las Reglas de Operación publicadas el 31 de "
            "diciembre de 2024."
        ),
        # Title fragment used to verify the retrieved note is actually this
        # document — see JcfFetcher.fetch_html.
        title_marker="Jóvenes Construyendo el Futuro",
    ),
    JcfDocument(
        official_id="jcf-acuerdo-simplificacion-2026",
        name=(
            "ACUERDO por el que se establecen acciones de simplificación para "
            "trámites que se realizan ante la Secretaría del Trabajo y "
            "Previsión Social"
        ),
        short_name="Acuerdo de simplificación STPS 2026",
        dof_codigo="5788734",
        publication_date="2026-05-27",
        # Transitorio Primero: "entrará en vigor a partir del día hábil
        # siguiente a su publicación". 2026-05-27 is a Wednesday, so the
        # next business day is 2026-05-28.
        valid_from="2026-05-28",
        document_type="acuerdo",
        status="vigente",
        vigencia_note=(
            "En vigor. Modifica los trámites JCF STPS-03-025 (registro de "
            "Joven) y STPS-03-026 (registro de Centro de Trabajo; fusiona "
            "STPS-03-026-A/B/C). Transitorio Cuarto otorga a la STPS un "
            "plazo no mayor a un año (hasta ~2027-05) para actualizar "
            "plataformas, sistemas y normativa — reverificar el corpus JCF "
            "dentro de esa ventana."
        ),
        # This Acuerdo's title names the STPS, not the program.
        title_marker="acciones de simplificación",
    ),
    JcfDocument(
        official_id="jcf-lineamientos-2019",
        name=(
            "LINEAMIENTOS para la operación del Programa Jóvenes Construyendo el Futuro"
        ),
        short_name="Lineamientos JCF 2019",
        dof_codigo="5547857",
        publication_date="2019-01-10",
        valid_from="2019-01-10",
        document_type="acuerdo",
        # Deliberately NOT "abrogada": no instrument abrogates these
        # expressly, and the corpus must not assert an abrogation the DOF
        # never published. "unknown" is the honest status — Tezca's Law
        # model has exactly that value for this situation.
        status="unknown",
        vigencia_note=(
            "Estatus residual. Firmados el 9 de enero de 2019, sin cláusula "
            "de abrogación y con cláusula de autoprórroga; desplazados en la "
            "práctica por las sucesivas Reglas de Operación anuales, pero "
            "ningún instrumento los abroga expresamente. Documento "
            "controlante: jcf-reglas-2026. Requiere opinión legal antes de "
            "citar cualquier numeral como vigente."
        ),
    ),
    # NOTE — the abrogated 2025 ROP (DOF 2024-12-31) is deliberately NOT
    # listed. It is abrogated by jcf-reglas-2026 and therefore has no
    # bearing on any current citation, and its DOF `codigo` could not be
    # verified: the value a first pass assumed (5746288) actually resolves
    # to an unrelated judicial edicto, and neither the DOF daily index page
    # (which lists only a partial highlights set for that edition) nor
    # SIDOF exposes a searchable index to confirm the real one. Registering
    # an unverified codigo would point the ecosystem's source of law at the
    # wrong document — strictly worse than an acknowledged gap. Add it here
    # once an operator confirms the codigo against the DOF edition of
    # 2024-12-31.
]

# Indexed by official_id for O(1) lookup by the ingest command + tests.
JCF_DOCUMENTS_BY_ID: Dict[str, JcfDocument] = {
    doc.official_id: doc for doc in JCF_DOCUMENTS
}


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def html_to_lines(html: str) -> List[str]:
    """Flatten a DOF/SIDOF note into non-empty, stripped text lines."""
    text = BeautifulSoup(html, "html.parser").get_text("\n")
    return [line.strip() for line in text.split("\n") if line.strip()]


def _is_body_terminator(line: str) -> bool:
    stripped = line.rstrip(".").strip().upper()
    return stripped in _BODY_TERMINATORS


def parse_reglas(html: str) -> List[Dict[str, str]]:
    """Split a Reglas de Operación note into one entry per Regla.

    Returns a list of ``{"num", "heading", "text"}`` dicts in document
    order. Parsing stops at the transitorios: everything after them
    (annexes, model convenios, carta compromiso) restarts ordinal
    numbering and would collide with the Reglas article namespace.

    Returns ``[]`` when the note carries no ordinal headings — e.g. the
    simplification Acuerdo, which is prose. Callers fall back to raw text
    for those.
    """
    lines = html_to_lines(html)

    # Truncate at the transitorios.
    for idx, line in enumerate(lines):
        if _is_body_terminator(line):
            lines = lines[:idx]
            break

    reglas: List[Dict[str, str]] = []
    current: Optional[Dict[str, List[str]]] = None

    for line in lines:
        match = _REGLA_HEADING.match(line)
        if match:
            if current is not None:
                reglas.append(_finalize_regla(current))
            current = {
                "num": [match.group(1).strip()],
                "heading": [match.group(2).strip()],
                "body": [],
            }
            continue
        if current is not None:
            current["body"].append(line)

    if current is not None:
        reglas.append(_finalize_regla(current))

    return reglas


def _finalize_regla(acc: Dict[str, List[str]]) -> Dict[str, str]:
    num = acc["num"][0]
    heading = acc["heading"][0].strip()
    body_lines = list(acc["body"])

    # The DOF sometimes breaks the line between the ordinal and its
    # terminating period, so the rubric arrives as a separate line starting
    # with ".": "DÉCIMA QUINTA" / ". Recurso Federal asignado...". Without
    # this, every such Regla's text would open with a stray period.
    if not heading and body_lines and body_lines[0].startswith("."):
        heading = body_lines.pop(0).lstrip(". ").strip()

    if heading:
        body_lines.insert(0, heading)

    return {
        "num": num,
        "heading": heading,
        "text": _join_wrapped(body_lines),
    }


def _join_wrapped(lines: List[str]) -> str:
    """Rejoin DOF column wraps into readable paragraphs.

    The DOF's HTML hard-wraps mid-sentence at column width. A line that
    does not end a sentence is glued to the next with a space; a line that
    does keeps its break.
    """
    out: List[str] = []
    for line in lines:
        if out and not re.search(r"[.:;]$", out[-1]):
            out[-1] = f"{out[-1]} {line}"
        else:
            out.append(line)
    return "\n".join(out).strip()


def validate_regla_sequence(reglas: List[Dict[str, str]]) -> List[str]:
    """Return a list of sequence problems (empty list = clean parse).

    A ROP numbers its Reglas consecutively from PRIMERA. A gap or a
    repeat means the parser mis-split the note, which would silently
    corrupt every citation into it — so ingestion checks this rather than
    trusting the extraction.
    """
    problems: List[str] = []
    seen = [r["num"].upper() for r in reglas]

    if not seen:
        return ["no reglas parsed"]

    expected = _ORDINAL_SEQUENCE[: len(seen)]
    if len(seen) > len(_ORDINAL_SEQUENCE):
        problems.append(
            f"parsed {len(seen)} reglas, beyond known ordinal sequence "
            f"({len(_ORDINAL_SEQUENCE)})"
        )
        return problems

    for position, (got, want) in enumerate(zip(seen, expected), start=1):
        if got != want:
            problems.append(f"position {position}: expected {want!r}, got {got!r}")

    duplicates = {n for n in seen if seen.count(n) > 1}
    if duplicates:
        problems.append(f"duplicate ordinals: {sorted(duplicates)}")

    return problems


# ---------------------------------------------------------------------------
# AKN emission
#
# index_laws parses AKN XML into one ES article per <akn:article>, taking
# the article_id from <num>. Emitting AKN (rather than a raw-text blob) is
# what makes a single Regla addressable — which is the entire point of
# putting JCF in the corpus.
# ---------------------------------------------------------------------------

AKN_NS = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"


def _akn_eid(num: str) -> str:
    """Stable element id from an ordinal ("DÉCIMA QUINTA" → "regla-decima-quinta")."""
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
    return f"regla-{slug}"


def build_akn(document: JcfDocument, reglas: List[Dict[str, str]]) -> str:
    """Render parsed Reglas as an AKN act that ``index_laws`` can consume."""
    frbr_base = (
        f"/mx/fed/reglas-de-operacion/{document.publication_date}/"
        f"{document.official_id}"
    )
    parts = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<akomaNtoso xmlns="{AKN_NS}">',
        '  <act name="reglasDeOperacion">',
        "    <meta>",
        '      <identification source="#tezca-jcf-fetcher">',
        "        <FRBRWork>",
        f'          <FRBRthis value="{frbr_base}/main"/>',
        f'          <FRBRuri value="{frbr_base}"/>',
        f'          <FRBRdate date="{document.publication_date}" name="Generation"/>',
        '          <FRBRauthor href="#stps"/>',
        '          <FRBRcountry value="mx"/>',
        "        </FRBRWork>",
        "        <FRBRExpression>",
        f'          <FRBRthis value="{frbr_base}/spa@/main"/>',
        f'          <FRBRuri value="{frbr_base}/spa@"/>',
        f'          <FRBRdate date="{document.publication_date}" name="Generation"/>',
        '          <FRBRauthor href="#tezca-jcf-fetcher"/>',
        '          <FRBRlanguage language="spa"/>',
        "        </FRBRExpression>",
        "        <FRBRManifestation>",
        f'          <FRBRthis value="{frbr_base}/spa@/main.xml"/>',
        f'          <FRBRuri value="{frbr_base}/spa@/main.akn"/>',
        f'          <FRBRdate date="{document.publication_date}" name="Generation"/>',
        '          <FRBRauthor href="#tezca-jcf-fetcher"/>',
        "        </FRBRManifestation>",
        "      </identification>",
        "    </meta>",
        "    <body>",
    ]

    for regla in reglas:
        eid = _akn_eid(regla["num"])
        parts.append(f'      <article eId="{eid}" id="{eid}">')
        parts.append(f"        <num>{escape(regla['num'])}</num>")
        if regla.get("heading"):
            parts.append(f"        <heading>{escape(regla['heading'])}</heading>")
        parts.append(f'        <paragraph eId="{eid}-para-1">')
        parts.append("          <content>")
        parts.append(f"            <p>{escape(regla['text'])}</p>")
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


class JcfFetcher:
    """Retrieves the enumerated JCF corpus from SIDOF (falling back to DOF).

    Unlike the RMF/NOM scrapers there is no discovery step — the corpus is
    the pinned ``JCF_DOCUMENTS`` list. This class handles retrieval,
    parsing into AKN, and catalog emission for ``manage.py ingest_jcf``.
    """

    def __init__(self, output_dir: str = "data/jcf") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._session = self._build_session()
        self._last_request_at: float = 0.0

    @staticmethod
    def _build_session() -> requests.Session:
        """Session for sidof.segob.gob.mx / dof.gob.mx.

        Both have valid certificate chains (verified 2026-08-22), so no
        INSECURE_HOSTS bypass is needed.
        """
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
                    "HTTP %s for %s (attempt %d/%d)",
                    status,
                    url,
                    attempt,
                    _MAX_RETRIES,
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

    def fetch_html(self, document: JcfDocument) -> Optional[str]:
        """Retrieve a note's HTML: SIDOF first, DOF as fallback.

        Every retrieved note is identity-checked against the document's
        ``title_marker`` before being returned — see the field's docstring
        for why a merely-successful fetch proves nothing.
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
    def _identity_matches(document: JcfDocument, html: str) -> bool:
        """True when the retrieved note really is the pinned document."""
        marker = document.title_marker.strip().lower()
        if not marker:
            return True
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        # DOF notes carry the instrument name in <title>; SIDOF sometimes
        # serves a generic one, so fall back to the opening body text.
        if marker in title.lower():
            return True
        head = " ".join(html_to_lines(html)[:40]).lower()
        return marker in head

    def materialize(self, document: JcfDocument) -> Optional[Path]:
        """Fetch a document and write its parsed AKN to ``output_dir``.

        Returns the written path, or None when retrieval or parsing failed
        (never a partial/empty file — a broken fetch must not masquerade as
        an ingested document).
        """
        html = self.fetch_html(document)
        if not html:
            return None

        reglas = parse_reglas(html)
        if not reglas:
            logger.warning(
                "No ordinal Reglas parsed for %s — writing raw text instead",
                document.official_id,
            )
            raw_path = self.output_dir / f"{document.official_id}.txt"
            raw_path.write_text("\n".join(html_to_lines(html)), encoding="utf-8")
            return raw_path

        problems = validate_regla_sequence(reglas)
        if problems:
            logger.error(
                "Regla sequence validation failed for %s: %s",
                document.official_id,
                "; ".join(problems),
            )
            return None

        path = self.output_dir / document.text_filename
        path.write_text(build_akn(document, reglas), encoding="utf-8")
        logger.info(
            "Wrote %s (%d reglas) → %s", document.official_id, len(reglas), path
        )
        return path

    def write_catalog(self, documents: List[JcfDocument]) -> Path:
        """Write the catalog ``manage.py ingest_jcf`` consumes."""
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

    def run(self, download_documents: bool = False) -> Dict[str, object]:
        """Emit the catalog, optionally materializing each document's text."""
        documents = list(JCF_DOCUMENTS)

        downloaded = 0
        errors = 0
        if download_documents:
            for doc in documents:
                if self.materialize(doc):
                    downloaded += 1
                else:
                    errors += 1

        catalog_path = self.write_catalog(documents)

        by_type: Dict[str, int] = {}
        for doc in documents:
            by_type[doc.document_type] = by_type.get(doc.document_type, 0) + 1

        result = {
            "program": JCF_PROGRAM,
            "total": len(documents),
            "by_type": by_type,
            "downloaded": downloaded,
            "errors": errors,
            "catalog_path": str(catalog_path),
        }
        logger.info("JCF run complete: %s", result)
        return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch the Jóvenes Construyendo el Futuro normative corpus"
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Fetch each document from SIDOF/DOF and write parsed AKN (slow)",
    )
    parser.add_argument(
        "--output-dir", default="data/jcf", help="Where to write catalog + text"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    fetcher = JcfFetcher(output_dir=args.output_dir)
    result = fetcher.run(download_documents=args.download)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
