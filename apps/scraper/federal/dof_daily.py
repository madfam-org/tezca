"""
DOF Daily Edition Scraper.

Parses the Diario Oficial de la Federacion (DOF) daily index page to extract
published entries (decrees, laws, reforms, regulations) organized by section
and issuing authority. Provides change detection against a known set of laws.

Usage:
    python -m apps.scraper.federal.dof_daily --date 2026-02-05
"""

import datetime
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from lxml import html

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SECTION_PATTERN = re.compile(
    r"(PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|S[EÉ]PTIMA|OCTAVA|[UÚ]NICA)"
    r"\s+SECCI[OÓ]N",
    re.IGNORECASE,
)

# The DOF index renders each issuing authority as
# <td class="subtitle_azul">SECRETARIA DE HACIENDA Y CREDITO PUBLICO …</td>.
# Reading category only from h3/h4/strong/b left it empty on every entry, so
# corpus watches with an issuer filter (SEP calendario, JCF, RMF) never fired.
_CATEGORY_CLASSES = frozenset({"subtitle_azul"})

_CHANGE_KEYWORDS: Dict[str, List[str]] = {
    "reform": ["REFORMA", "ADICIONA", "MODIFICA"],
    "abrogation": ["DEROGA", "ABROGA"],
    "new_law": ["EXPIDE", "SE CREA", "LEY GENERAL DE", "LEY FEDERAL DE"],
}

_LEGAL_INSTRUMENT_KEYWORDS: List[str] = [
    "DECRETO",
    "LEY",
    "REGLAMENTO",
    "CODIGO",
    "CÓDIGO",
    "CONSTITUCIÓN",
    "CONSTITUCION",
    "ESTATUTO",
]

_REQUEST_TIMEOUT = 30  # seconds
_USER_AGENT = "Tezca/1.0 (+https://github.com/madfam-org/tezca)"


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class DofScraper:
    """
    Scraper for the Diario Oficial de la Federacion (DOF) daily index.

    Fetches and parses the daily edition page, extracting structured metadata
    for every published entry. Optionally detects legislative changes by
    comparing entry titles against a list of known law names.
    """

    BASE_URL = "https://dof.gob.mx"

    # The DOF publishes up to three editions a day: matutina (MAT),
    # vespertina (VES, evening) and extraordinaria (EXT). Without an explicit
    # ``edicion`` the index serves the day's LATEST edition — at the 07:00 run
    # that is MAT, and the evening edition is never read: the 2a and 3a
    # RMRMF 2026 (DOF 2026-10-01/02, vespertina) were invisible.
    EDITIONS = ("MAT", "VES", "EXT")
    LATE_EDITIONS = ("VES", "EXT")

    def __init__(
        self,
        date: Optional[datetime.date] = None,
        include_previous_late_editions: bool = False,
    ) -> None:
        """``include_previous_late_editions`` also reads the previous day's
        VES/EXT editions — for a morning run, which happens before that
        day's evening edition exists."""
        self.date = date or datetime.date.today()
        self.include_previous_late_editions = include_previous_late_editions
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": _USER_AGENT})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_daily_edition(self) -> List[Dict[str, str]]:
        """
        Fetch and parse every DOF edition (MAT, VES, EXT) for *self.date*,
        plus the previous day's VES/EXT when ``include_previous_late_editions``.

        Returns a list of dicts, each with keys:
            - title:    Full title of the entry (decree / regulation text).
            - section:  Section name (e.g. "PRIMERA SECCION").
            - category: Issuing authority (e.g. "SECRETARIA DE GOBERNACION").
            - url:      Absolute URL to the detail page.
            - date:     ISO-formatted date string.
            - edition:  "MAT", "VES" or "EXT".

        Entries are de-duplicated by URL. Returns an empty list when no
        edition exists (weekends, holidays, or network errors).
        """
        targets = [(self.date, edition) for edition in self.EDITIONS]
        if self.include_previous_late_editions:
            previous = self.date - datetime.timedelta(days=1)
            targets = [(previous, e) for e in self.LATE_EDITIONS] + targets

        entries: List[Dict[str, str]] = []
        seen_urls = set()
        for date, edition in targets:
            for entry in self._fetch_edition(date, edition):
                if entry["url"] in seen_urls:
                    continue
                seen_urls.add(entry["url"])
                entries.append(entry)

        if not entries:
            logger.info("No DOF entries found for %s (weekend/holiday?)", self.date)
        else:
            logger.info("Found %d entries in DOF for %s", len(entries), self.date)
        return entries

    def _fetch_edition(self, date: datetime.date, edition: str) -> List[Dict[str, str]]:
        index_url = (
            f"{self.BASE_URL}/index.php"
            f"?year={date.year}"
            f"&month={date.month:02d}"
            f"&day={date.day:02d}"
            f"&edicion={edition}"
        )
        logger.info("Fetching DOF daily index: %s", index_url)

        try:
            response = self.session.get(index_url, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.ConnectionError:
            logger.error("Connection failed for DOF index at %s", index_url)
            return []
        except requests.Timeout:
            logger.error("Request timed out for DOF index at %s", index_url)
            return []
        except requests.HTTPError as exc:
            logger.error(
                "HTTP %s for DOF index: %s", exc.response.status_code, index_url
            )
            return []
        except requests.RequestException as exc:
            logger.error("Unexpected request error for DOF index: %s", exc)
            return []

        tree = html.fromstring(response.content)
        entries = self._parse_index_page(tree)
        for entry in entries:
            entry["date"] = date.isoformat()
            entry["edition"] = edition
        return entries

    @staticmethod
    def detect_law_changes(
        entries: List[Dict[str, str]],
        existing_laws: Optional[List[str]] = None,
    ) -> List[Dict[str, Optional[str]]]:
        """
        Classify DOF entries by the type of legislative change they represent.

        Args:
            entries:        Output of *fetch_daily_edition()*.
            existing_laws:  Optional list of known law names. When provided,
                            each entry is matched to the closest existing law.

        Returns a list of dicts (one per relevant entry) with keys:
            - title:        Original entry title.
            - change_type:  One of "new_law", "reform", "abrogation", or "other".
            - related_law:  Best-matching law name from *existing_laws*, or None.
            - url:          Detail URL for the entry.
        """
        existing_upper: List[str] = []
        if existing_laws:
            existing_upper = [name.upper() for name in existing_laws]

        results: List[Dict[str, Optional[str]]] = []

        for entry in entries:
            title_upper = entry["title"].upper()

            # Skip entries that clearly are not legislative instruments.
            if not _is_legal_instrument(title_upper):
                continue

            change_type = _classify_change(title_upper)
            related_law = _find_related_law(title_upper, existing_laws, existing_upper)

            results.append(
                {
                    "title": entry["title"],
                    "change_type": change_type,
                    "related_law": related_law,
                    "url": entry["url"],
                }
            )

        logger.info(
            "Detected %d law-related entries out of %d total",
            len(results),
            len(entries),
        )
        return results

    def run(
        self,
        existing_laws: Optional[List[str]] = None,
    ) -> Dict[str, object]:
        """
        Execute the full scrape-and-detect pipeline.

        Returns a dict with:
            - date:     ISO date string.
            - entries:  Raw entries from the daily edition.
            - changes:  Classified law-change entries.
        """
        entries = self.fetch_daily_edition()
        changes = self.detect_law_changes(entries, existing_laws=existing_laws)
        return {
            "date": self.date.isoformat(),
            "entries": entries,
            "changes": changes,
        }

    # ------------------------------------------------------------------
    # Parsing internals
    # ------------------------------------------------------------------

    def _parse_index_page(self, tree: html.HtmlElement) -> List[Dict[str, str]]:
        """
        Walk the DOM of the DOF daily index and extract structured entries.

        The DOF index page organises content under section headings
        (PRIMERA SECCION ... QUINTA SECCION). Within each section, entries
        are grouped by issuing authority and listed as linked titles.

        The parser uses multiple strategies to accommodate layout variations:
        1. Look for explicit section containers (divs / tables with section text).
        2. Walk all link elements and infer section + category from context.
        """
        entries: List[Dict[str, str]] = []
        date_str = self.date.isoformat()

        # Strategy 1: Section-based div containers.
        # DOF often wraps content in <div class="contenedor"> or similar.
        entries = self._extract_from_section_divs(tree, date_str)
        if entries:
            return entries

        # Strategy 2: Table-row layout.
        entries = self._extract_from_table_rows(tree, date_str)
        if entries:
            return entries

        # Strategy 3: Flat link scan -- fallback for unusual layouts.
        entries = self._extract_from_flat_links(tree, date_str)
        return entries

    def _extract_from_section_divs(
        self,
        tree: html.HtmlElement,
        date_str: str,
    ) -> List[Dict[str, str]]:
        """
        Extract entries from div-based section containers.

        Typical structure:
            <div class="contenedor">
              <h2>PRIMERA SECCION</h2>
              <h3>SECRETARIA DE GOBERNACION</h3>
              <ul>
                <li><a href="nota_detalle.php?...">Entry title</a></li>
              </ul>
            </div>
        """
        entries: List[Dict[str, str]] = []
        current_section = ""
        current_category = ""

        # Gather all meaningful text nodes + links in document order.
        for element in tree.iter():
            text = (element.text or "").strip()
            tag = element.tag

            # Detect section headings.
            section_match = _SECTION_PATTERN.search(text)
            if section_match:
                current_section = _normalise_section(section_match.group(0))
                continue

            # Detect category headings: the DOF's own authority cells, or
            # bold / h3 / strong in other layouts.
            if _CATEGORY_CLASSES & set((element.get("class") or "").split()):
                candidate = _clean_text(element.text_content())
                if candidate:
                    current_category = candidate
                    continue
            if tag in ("h3", "h4", "strong", "b") and text and not section_match:
                candidate = text.strip()
                if len(candidate) > 5 and candidate.isupper():
                    current_category = _clean_text(candidate)
                    continue

            # Detect entry links.
            if tag == "a":
                href = element.get("href", "")
                if "nota_detalle" in href or "nota_to_doc" in href:
                    title = _clean_text(element.text_content())
                    if not title:
                        continue
                    absolute_url = self._resolve_url(href)
                    entries.append(
                        {
                            "title": title,
                            "section": current_section,
                            "category": current_category,
                            "url": absolute_url,
                            "date": date_str,
                        }
                    )

        return entries

    def _extract_from_table_rows(
        self,
        tree: html.HtmlElement,
        date_str: str,
    ) -> List[Dict[str, str]]:
        """
        Extract entries from table-based layouts.

        Some DOF pages render the index as an HTML table where each row
        contains the section, authority, and title with a link.
        """
        entries: List[Dict[str, str]] = []
        current_section = ""
        current_category = ""

        for row in tree.xpath("//tr"):
            row_text = row.text_content()

            section_match = _SECTION_PATTERN.search(row_text)
            if section_match:
                current_section = _normalise_section(section_match.group(0))

            cells = row.findall("td")
            if not cells:
                continue

            # Check if this row is a category header (single-cell, all-caps).
            if len(cells) == 1:
                candidate = _clean_text(cells[0].text_content())
                if candidate and candidate.isupper() and len(candidate) > 5:
                    current_category = candidate
                    continue

            # Look for entry links within this row.
            links = row.xpath(
                './/a[contains(@href, "nota_detalle") or contains(@href, "nota_to_doc")]'
            )
            for link in links:
                title = _clean_text(link.text_content())
                href = link.get("href", "")
                if not title or not href:
                    continue
                absolute_url = self._resolve_url(href)
                entries.append(
                    {
                        "title": title,
                        "section": current_section,
                        "category": current_category,
                        "url": absolute_url,
                        "date": date_str,
                    }
                )

        return entries

    def _extract_from_flat_links(
        self,
        tree: html.HtmlElement,
        date_str: str,
    ) -> List[Dict[str, str]]:
        """
        Fallback: scan all links that look like DOF detail pages.

        Section and category are inferred from surrounding text nodes.
        """
        entries: List[Dict[str, str]] = []

        links = tree.xpath(
            '//a[contains(@href, "nota_detalle") or contains(@href, "nota_to_doc")]'
        )
        for link in links:
            href = link.get("href", "")
            title = _clean_text(link.text_content())
            if not title or not href:
                continue

            section, category = _infer_context(link)
            absolute_url = self._resolve_url(href)

            entries.append(
                {
                    "title": title,
                    "section": section,
                    "category": category,
                    "url": absolute_url,
                    "date": date_str,
                }
            )

        return entries

    def _resolve_url(self, href: str) -> str:
        """Resolve a potentially relative href against the DOF base URL."""
        if href.startswith(("http://", "https://")):
            return href
        return urljoin(self.BASE_URL + "/", href)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _clean_text(raw: str) -> str:
    """Collapse whitespace and strip surrounding blanks."""
    return re.sub(r"\s+", " ", raw).strip()


def _normalise_section(raw: str) -> str:
    """
    Normalise a section heading string.

    "Primera  Sección" -> "PRIMERA SECCION"
    """
    normalised = re.sub(r"\s+", " ", raw).strip().upper()
    # Unify accented forms: SECCIÓN -> SECCION
    normalised = normalised.replace("Ó", "O")
    return normalised


def _infer_context(link_element: html.HtmlElement) -> tuple:
    """
    Walk up the DOM from *link_element* to infer section and category.

    Returns (section, category) -- either or both may be empty strings.
    """
    section = ""
    category = ""

    # Walk ancestors looking for contextual text.
    for ancestor in link_element.iterancestors():
        ancestor_text = (ancestor.text or "").strip()

        if not section:
            match = _SECTION_PATTERN.search(ancestor_text)
            if match:
                section = _normalise_section(match.group(0))

        # Look at preceding siblings for category headings.
        if not category:
            for sibling in ancestor.itersiblings(preceding=True):
                sibling_text = _clean_text(sibling.text_content())
                if sibling_text and sibling_text.isupper() and len(sibling_text) > 5:
                    category = sibling_text
                    break

        if section and category:
            break

    return section, category


def _is_legal_instrument(title_upper: str) -> bool:
    """Return True if the title refers to a legislative instrument."""
    return any(kw in title_upper for kw in _LEGAL_INSTRUMENT_KEYWORDS)


def _classify_change(title_upper: str) -> str:
    """
    Classify the type of legislative change described by *title_upper*.

    Returns one of: "new_law", "reform", "abrogation", "other".
    The first matching category wins; ordering is from most specific
    (abrogation) to least (new_law).
    """
    # Check abrogation first -- it is the most destructive action and
    # should not be confused with a simple reform.
    for kw in _CHANGE_KEYWORDS["abrogation"]:
        if kw in title_upper:
            return "abrogation"

    for kw in _CHANGE_KEYWORDS["reform"]:
        if kw in title_upper:
            return "reform"

    for kw in _CHANGE_KEYWORDS["new_law"]:
        if kw in title_upper:
            return "new_law"

    return "other"


def _find_related_law(
    title_upper: str,
    existing_laws: Optional[List[str]],
    existing_upper: List[str],
) -> Optional[str]:
    """
    Find the best matching law from *existing_laws* mentioned in *title_upper*.

    Uses a simple longest-match heuristic: the law whose name appears in the
    title and is the longest match wins. Returns None when no match is found
    or when *existing_laws* is empty / None.
    """
    if not existing_laws or not existing_upper:
        return None

    best_match: Optional[str] = None
    best_length = 0

    for original, upper in zip(existing_laws, existing_upper):
        if upper in title_upper and len(upper) > best_length:
            best_match = original
            best_length = len(upper)

    return best_match


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Fetch and analyse the DOF daily edition.",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date in YYYY-MM-DD format (defaults to today).",
    )
    parser.add_argument(
        "--laws-file",
        type=str,
        default=None,
        help="Path to a JSON file with a list of known law names for change detection.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to write JSON results (prints to stdout if omitted).",
    )
    args = parser.parse_args()

    target_date = datetime.date.fromisoformat(args.date) if args.date else None

    known_laws: Optional[List[str]] = None
    if args.laws_file:
        with open(args.laws_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Accept both a plain list and a list of objects with a "name" key.
            if data and isinstance(data[0], dict):
                known_laws = [entry["name"] for entry in data]
            else:
                known_laws = data

    scraper = DofScraper(date=target_date)
    result = scraper.run(existing_laws=known_laws)

    output_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        from pathlib import Path

        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_json, encoding="utf-8")
        logger.info("Results written to %s", out_path)
    else:
        print(output_json)
