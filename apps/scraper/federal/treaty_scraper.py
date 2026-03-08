"""
International Treaties Scraper

Scrapes bilateral and multilateral treaties from SRE (Secretaria de
Relaciones Exteriores). ~1,509 treaties ratified by Mexico. Per SCJN,
treaties sit above federal laws in the normative hierarchy.

The original portal (tratados.sre.gob.mx) was decommissioned circa 2025.
The successor portal is cja.sre.gob.mx/tratadosmexico/ (Biblioteca Virtual
de Tratados Internacionales), with a search interface at
cja.sre.gob.mx/tratadosmexico/buscador.

The search page is server-rendered HTML with pagination (?page=N),
151 pages, 1,509 total treaties. Columns: name, adoption date, place,
category (Bilateral/Multilateral).

Supplementary source: Senate catalog at
www.senado.gob.mx/65/tratados_internacionales_aprobados (simpler table,
useful to fill gaps).

Usage:
    python -m apps.scraper.federal.treaty_scraper
    python -m apps.scraper.federal.treaty_scraper --output-dir data/treaties
    python -m apps.scraper.federal.treaty_scraper --fetch-details
    python -m apps.scraper.federal.treaty_scraper --retry-failed
    python -m apps.scraper.federal.treaty_scraper --merge-sources
"""

import json
import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Primary: successor portal (Biblioteca Virtual de Tratados Internacionales)
BASE_URL = "https://cja.sre.gob.mx/tratadosmexico"
# Original (DNS-dead since ~2025): https://tratados.sre.gob.mx
# Alternative: https://aplicaciones.sre.gob.mx/tratados/depositario.php
SENATE_URL = "https://www.senado.gob.mx/65/tratados_internacionales_aprobados"
_USER_AGENT = "Tezca/1.0 (+https://github.com/madfam-org/tezca)"
_REQUEST_TIMEOUT = 30  # seconds
_MIN_REQUEST_INTERVAL = 1.0  # 1 req/sec
_ITEMS_PER_PAGE = 10  # expected items per full catalog page

# Patterns for treaty type classification.
_BILATERAL_KEYWORDS = [
    "bilateral",
    "acuerdo entre",
    "convenio entre",
    "tratado entre",
    "protocolo entre",
]
_MULTILATERAL_KEYWORDS = [
    "multilateral",
    "convencion",
    "convenci\u00f3n",
    "protocolo de",
    "carta de",
    "pacto",
    "estatuto de",
]

# Words stripped during title normalisation for dedup (shared with CONAMER).
_STOP_WORDS = frozenset(
    {
        "de",
        "del",
        "la",
        "las",
        "los",
        "el",
        "en",
        "y",
        "a",
        "por",
        "para",
        "que",
        "con",
        "al",
        "se",
        "su",
        "una",
        "un",
        "es",
    }
)

# Fields that indicate a treaty detail has been successfully fetched.
_DETAIL_FIELDS = ("full_text", "date_ratified", "parties")


# ---------------------------------------------------------------------------
# Normalisation helpers (accent stripping + stop-word removal for dedup)
# ---------------------------------------------------------------------------


def _strip_accents(text: str) -> str:
    """Remove diacritical marks from *text*."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _normalise_title(title: str) -> str:
    """
    Normalise a title for dedup comparison.

    Lowercase, strip accents, remove punctuation, drop stop words,
    and collapse whitespace. Matches the logic in conamer_scraper.py.
    """
    text = _strip_accents(title.lower())
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = [t for t in text.split() if t not in _STOP_WORDS]
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class TreatyScraper:
    """
    Scraper for international treaties ratified by Mexico.

    Fetches the SRE (Secretaria de Relaciones Exteriores) treaty portal
    catalog, parses treaty listings, and optionally fetches individual
    treaty detail pages for full text and PDF links.

    Supplementary source: Senate catalog for gap-filling.
    """

    def __init__(self) -> None:
        self.session = self._setup_session()
        self.last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Session setup
    # ------------------------------------------------------------------

    @staticmethod
    def _setup_session() -> requests.Session:
        """Configure HTTP session with retry logic and polite headers."""
        session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        session.headers.update(
            {
                "User-Agent": _USER_AGENT,
                "Accept": "text/html, application/xhtml+xml, */*",
                "Accept-Language": "es-MX,es;q=0.9,en;q=0.5",
            }
        )
        return session

    def _rate_limit(self) -> None:
        """Enforce minimum interval between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def _get(self, url: str, **kwargs: Any) -> Optional[requests.Response]:
        """Rate-limited GET with error handling."""
        self._rate_limit()
        try:
            response = self.session.get(url, timeout=_REQUEST_TIMEOUT, **kwargs)
            response.raise_for_status()
            return response
        except requests.ConnectionError:
            logger.error("Connection failed: %s", url)
        except requests.Timeout:
            logger.error("Request timed out: %s", url)
        except requests.HTTPError as exc:
            logger.warning("HTTP %s for %s", exc.response.status_code, url)
        except requests.RequestException as exc:
            logger.error("Request error for %s: %s", url, exc)
        return None

    # ------------------------------------------------------------------
    # Catalog scraping (SRE portal)
    # ------------------------------------------------------------------

    def scrape_catalog(
        self,
        max_pages: Optional[int] = None,
        resume_from_page: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Fetch the SRE treaty portal catalog and parse treaty listings.

        The successor portal at cja.sre.gob.mx/tratadosmexico/buscador
        serves server-rendered paginated HTML with ~10 treaties per page.
        Total: 1,509 treaties across ~151 pages.

        Last-page detection: a page returning fewer than _ITEMS_PER_PAGE
        items is treated as the final page. Consecutive HTTP failures
        (3 in a row) also trigger a stop.

        Args:
            max_pages: Stop after this many pages (None = unlimited).
            resume_from_page: Start from this page number (1-based).

        Returns:
            List of treaty dicts with basic metadata.
        """
        logger.info("Scraping treaty catalog from %s", BASE_URL)

        all_treaties: List[Dict[str, Any]] = []
        seen_norms: Set[str] = set()
        page = resume_from_page
        consecutive_failures = 0

        while True:
            if max_pages is not None and (page - resume_from_page) >= max_pages:
                logger.info("Reached max_pages=%d, stopping.", max_pages)
                break

            url = f"{BASE_URL}/buscador?page={page}"
            logger.info("Fetching catalog page %d: %s", page, url)

            resp = self._get(url)
            if resp is None:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    logger.warning("3 consecutive HTTP failures, stopping.")
                    break
                page += 1
                continue

            # Reset failure counter on successful HTTP response.
            consecutive_failures = 0

            treaties = self._parse_catalog_page(resp.text)

            # Last-page detection: if fewer than expected items, this is
            # the final page (or close to it). Process what we got, then stop.
            is_last_page = 0 < len(treaties) < _ITEMS_PER_PAGE

            if not treaties:
                # Truly empty page (0 items). Could be a gap or the end.
                # Allow up to 2 empty pages before giving up to handle
                # occasional server-side gaps, but stop on the third.
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    logger.info(
                        "3 consecutive empty pages at page %d, assuming end of catalog.",
                        page,
                    )
                    break
                page += 1
                continue

            new_count = 0
            for treaty in treaties:
                norm = _normalise_title(treaty.get("name", ""))
                if not norm:
                    continue
                if norm in seen_norms:
                    continue
                seen_norms.add(norm)
                all_treaties.append(treaty)
                new_count += 1

            logger.info(
                "Page %d: %d items parsed, %d new (total: %d)",
                page,
                len(treaties),
                new_count,
                len(all_treaties),
            )

            if is_last_page:
                logger.info(
                    "Page %d returned %d items (< %d expected), treating as last page.",
                    page,
                    len(treaties),
                    _ITEMS_PER_PAGE,
                )
                break

            page += 1

        logger.info("Catalog scrape complete: %d treaties", len(all_treaties))
        return all_treaties

    def _parse_catalog_page(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse a catalog page and extract treaty listings.

        Tries multiple selector strategies to handle layout variations.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        treaties: List[Dict[str, Any]] = []

        # Strategy 1: table rows
        for row in soup.select("table tbody tr"):
            try:
                treaty = self._parse_table_row(row)
                if treaty:
                    treaties.append(treaty)
            except Exception:
                logger.debug("Failed to parse table row", exc_info=True)
                continue

        if treaties:
            return treaties

        # Strategy 2: list items or card layout
        for item in soup.select(
            ".tratado, .treaty-item, .resultado, .list-item, article, .card"
        ):
            try:
                treaty = self._parse_list_item(item)
                if treaty:
                    treaties.append(treaty)
            except Exception:
                logger.debug("Failed to parse list item", exc_info=True)
                continue

        if treaties:
            return treaties

        # Strategy 3: scan all links that look like treaty detail pages
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if not text or len(text) < 10:
                continue
            # Heuristic: treaty links typically contain identifiable paths.
            if any(
                kw in href.lower()
                for kw in ("tratado", "treaty", "convenio", "acuerdo", "detail")
            ):
                abs_url = self._resolve_url(href)
                treaty_type = _classify_treaty_type(text)
                treaties.append(
                    {
                        "id": _generate_id(text),
                        "name": _clean_text(text),
                        "treaty_type": treaty_type,
                        "parties": "",
                        "date_signed": "",
                        "date_ratified": "",
                        "url": abs_url,
                        "pdf_url": "",
                        "source": "sre_tratados",
                    }
                )

        return treaties

    def _parse_table_row(self, row: Any) -> Optional[Dict[str, Any]]:
        """
        Extract treaty data from a table row.

        Successor portal columns (cja.sre.gob.mx/tratadosmexico/buscador):
            0: Nombre (Treaty Name)
            1: Fecha de adopcion (Adoption Date)
            2: Lugar de adopcion (Place of Adoption)
            3: Categoria (Bilateral/Multilateral)
        """
        cells = row.find_all("td")
        if len(cells) < 2:
            return None

        link = row.find("a", href=True)
        name = cells[0].get_text(strip=True)
        if not name or len(name) < 5:
            return None

        href = link.get("href", "") if link else ""
        abs_url = self._resolve_url(href) if href else ""

        # Column 3 has explicit category on successor portal.
        category_text = cells[3].get_text(strip=True).lower() if len(cells) > 3 else ""
        if "bilateral" in category_text:
            treaty_type = "bilateral"
        elif "multilateral" in category_text:
            treaty_type = "multilateral"
        else:
            treaty_type = _classify_treaty_type(name)

        date_adopted = cells[1].get_text(strip=True) if len(cells) > 1 else ""
        place_adopted = cells[2].get_text(strip=True) if len(cells) > 2 else ""

        # Check for PDF link.
        pdf_link = row.find("a", href=lambda h: h and h.endswith(".pdf"))
        pdf_url = self._resolve_url(pdf_link["href"]) if pdf_link else ""

        return {
            "id": _generate_id(name),
            "name": _clean_text(name),
            "treaty_type": treaty_type,
            "parties": "",
            "date_signed": _extract_date(date_adopted),
            "date_ratified": "",
            "place_adopted": _clean_text(place_adopted),
            "url": abs_url,
            "pdf_url": pdf_url,
            "source": "sre_tratados",
        }

    def _parse_list_item(self, item: Any) -> Optional[Dict[str, Any]]:
        """Extract treaty data from a card/list-item element."""
        title_el = item.find(["h2", "h3", "h4", "a", "strong"])
        if not title_el:
            return None

        name = title_el.get_text(strip=True)
        if not name or len(name) < 5:
            return None

        link = item.find("a", href=True)
        href = link.get("href", "") if link else ""
        abs_url = self._resolve_url(href) if href else ""

        treaty_type = _classify_treaty_type(name)

        # Try to find parties and dates in the item text.
        full_text = item.get_text()
        date_signed = _extract_date(full_text)

        pdf_link = item.find("a", href=lambda h: h and h.endswith(".pdf"))
        pdf_url = self._resolve_url(pdf_link["href"]) if pdf_link else ""

        return {
            "id": _generate_id(name),
            "name": _clean_text(name),
            "treaty_type": treaty_type,
            "parties": "",
            "date_signed": date_signed,
            "date_ratified": "",
            "url": abs_url,
            "pdf_url": pdf_url,
            "source": "sre_tratados",
        }

    # ------------------------------------------------------------------
    # Senate catalog scraping (supplementary source)
    # ------------------------------------------------------------------

    def scrape_senate_catalog(self) -> List[Dict[str, Any]]:
        """
        Scrape the Senate's approved international treaties catalog.

        The page at senado.gob.mx/65/tratados_internacionales_aprobados
        contains an HTML table of approved treaties with columns typically
        including: treaty name, approval date, publication (DOF), and
        sometimes parties involved.

        This is a simpler, single-page (or lightly paginated) source
        useful for filling gaps not covered by the SRE portal.

        Returns:
            List of treaty dicts with basic metadata sourced from the Senate.
        """
        logger.info("Scraping Senate treaty catalog from %s", SENATE_URL)
        all_treaties: List[Dict[str, Any]] = []
        seen_norms: Set[str] = set()

        # The Senate page may be single-page or have pagination links.
        # Start with the base URL, then follow pagination if present.
        page_url: Optional[str] = SENATE_URL
        page_num = 0

        while page_url:
            page_num += 1
            logger.info("Fetching Senate catalog page %d: %s", page_num, page_url)

            resp = self._get(page_url)
            if resp is None:
                logger.warning("Failed to fetch Senate page %d, stopping.", page_num)
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            treaties = self._parse_senate_page(soup)

            new_count = 0
            for treaty in treaties:
                norm = _normalise_title(treaty.get("name", ""))
                if not norm:
                    continue
                if norm in seen_norms:
                    continue
                seen_norms.add(norm)
                all_treaties.append(treaty)
                new_count += 1

            logger.info(
                "Senate page %d: %d items parsed, %d new (total: %d)",
                page_num,
                len(treaties),
                new_count,
                len(all_treaties),
            )

            # Check for a "next page" link.
            page_url = self._find_senate_next_page(soup)

            # Safety: cap at 50 pages to avoid infinite loops.
            if page_num >= 50:
                logger.warning("Senate pagination safety limit reached (50 pages).")
                break

        logger.info("Senate catalog scrape complete: %d treaties", len(all_treaties))
        return all_treaties

    def _parse_senate_page(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Parse a Senate catalog page for treaty entries.

        Tries table rows first, then falls back to list/card items.
        """
        treaties: List[Dict[str, Any]] = []

        # Strategy 1: table rows (most common layout for Senate pages)
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue

                # Skip header rows.
                if row.find("th"):
                    continue

                name = cells[0].get_text(strip=True)
                if not name or len(name) < 5:
                    continue

                # Try to extract a date from the second or third column.
                date_text = ""
                for cell in cells[1:]:
                    candidate = cell.get_text(strip=True)
                    extracted = _extract_date(candidate)
                    if extracted:
                        date_text = extracted
                        break

                link = row.find("a", href=True)
                href = link.get("href", "") if link else ""
                abs_url = ""
                if href:
                    if href.startswith(("http://", "https://")):
                        abs_url = href
                    else:
                        abs_url = urljoin(SENATE_URL, href)

                pdf_link = row.find("a", href=lambda h: h and h.endswith(".pdf"))
                pdf_url = ""
                if pdf_link:
                    pdf_href = pdf_link["href"]
                    if pdf_href.startswith(("http://", "https://")):
                        pdf_url = pdf_href
                    else:
                        pdf_url = urljoin(SENATE_URL, pdf_href)

                treaty_type = _classify_treaty_type(name)

                treaties.append(
                    {
                        "id": _generate_id(name),
                        "name": _clean_text(name),
                        "treaty_type": treaty_type,
                        "parties": "",
                        "date_signed": date_text,
                        "date_ratified": "",
                        "url": abs_url,
                        "pdf_url": pdf_url,
                        "source": "senado",
                    }
                )

        if treaties:
            return treaties

        # Strategy 2: list/card items
        for item in soup.select(".tratado, .treaty, .resultado, article, .card, li"):
            title_el = item.find(["h2", "h3", "h4", "a", "strong"])
            if not title_el:
                continue

            name = title_el.get_text(strip=True)
            if not name or len(name) < 10:
                continue

            link = item.find("a", href=True)
            href = link.get("href", "") if link else ""
            abs_url = ""
            if href:
                if href.startswith(("http://", "https://")):
                    abs_url = href
                else:
                    abs_url = urljoin(SENATE_URL, href)

            date_text = _extract_date(item.get_text())
            treaty_type = _classify_treaty_type(name)

            treaties.append(
                {
                    "id": _generate_id(name),
                    "name": _clean_text(name),
                    "treaty_type": treaty_type,
                    "parties": "",
                    "date_signed": date_text,
                    "date_ratified": "",
                    "url": abs_url,
                    "pdf_url": "",
                    "source": "senado",
                }
            )

        return treaties

    @staticmethod
    def _find_senate_next_page(soup: BeautifulSoup) -> Optional[str]:
        """
        Find the 'next page' link on a Senate catalog page.

        Returns the absolute URL of the next page, or None if not found.
        """
        # Look for common pagination patterns.
        for link in soup.select("a.next, a[rel='next'], li.next a, .pagination a"):
            text = link.get_text(strip=True).lower()
            href = link.get("href", "")
            if not href:
                continue
            if any(kw in text for kw in ("siguiente", "next", ">")):
                if href.startswith(("http://", "https://")):
                    return href
                return urljoin(SENATE_URL, href)

        return None

    # ------------------------------------------------------------------
    # Treaty detail scraping
    # ------------------------------------------------------------------

    def scrape_treaty_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch an individual treaty page for full text and PDF link.

        Args:
            url: Absolute URL to the treaty detail page.

        Returns:
            Dict with additional metadata (full_text, pdf_url, parties,
            dates) or None on failure.
        """
        if not url:
            return None

        logger.debug("Fetching treaty detail: %s", url)
        resp = self._get(url)
        if resp is None:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove navigation, footer, scripts.
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Extract full text from the main content area.
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(class_=re.compile(r"content|body|tratado|detail"))
            or soup.find("body")
        )
        full_text = ""
        if main_content:
            full_text = main_content.get_text(separator="\n", strip=True)

        # Find PDF links.
        pdf_link = soup.find("a", href=lambda h: h and h.lower().endswith(".pdf"))
        pdf_url = ""
        if pdf_link:
            pdf_url = self._resolve_url(pdf_link["href"])

        # Try to extract structured metadata from the page.
        parties = _extract_field(soup, ["partes", "parties", "paises", "signatarios"])
        date_signed = _extract_field(soup, ["fecha de firma", "date signed", "firma"])
        date_ratified = _extract_field(
            soup, ["fecha de ratificacion", "ratificacion", "aprobacion"]
        )

        return {
            "full_text": full_text[:50000] if full_text else "",
            "pdf_url": pdf_url,
            "parties": _clean_text(parties),
            "date_signed": _extract_date(date_signed) if date_signed else "",
            "date_ratified": _extract_date(date_ratified) if date_ratified else "",
        }

    # ------------------------------------------------------------------
    # Retry failed details
    # ------------------------------------------------------------------

    def retry_failed_details(
        self,
        treaties: List[Dict[str, Any]],
        max_retries: Optional[int] = None,
    ) -> int:
        """
        Re-fetch detail pages for treaties missing enriched metadata.

        A treaty is considered "missing detail data" if all of the key
        detail fields (full_text, date_ratified, parties) are empty.

        Args:
            treaties: Mutable list of treaty dicts (updated in-place).
            max_retries: Maximum number of detail pages to re-fetch
                         (None = retry all failed).

        Returns:
            Number of treaties successfully enriched in this pass.
        """
        candidates = [
            t
            for t in treaties
            if t.get("url") and not any(t.get(field) for field in _DETAIL_FIELDS)
        ]

        if not candidates:
            logger.info("No treaties with missing detail data found.")
            return 0

        if max_retries is not None:
            candidates = candidates[:max_retries]

        logger.info(
            "Retrying detail fetch for %d treaties with missing data.", len(candidates)
        )

        enriched = 0
        for i, treaty in enumerate(candidates, 1):
            url = treaty["url"]
            detail = self.scrape_treaty_detail(url)
            if detail:
                merged = False
                for key, value in detail.items():
                    if value and not treaty.get(key):
                        treaty[key] = value
                        merged = True
                if merged:
                    enriched += 1

            if i % 10 == 0:
                logger.info(
                    "Retry progress: %d/%d processed, %d enriched",
                    i,
                    len(candidates),
                    enriched,
                )

        logger.info(
            "Retry complete: %d/%d treaties enriched.", enriched, len(candidates)
        )
        return enriched

    # ------------------------------------------------------------------
    # Merge and dedup
    # ------------------------------------------------------------------

    @staticmethod
    def merge_treaty_lists(
        *sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Merge multiple treaty lists, deduplicating by normalised title.

        When duplicates are found, the entry from the earlier source list
        takes priority. Fields present in later duplicates but missing in
        the kept entry are back-filled.

        Args:
            *sources: Variable number of treaty lists to merge.

        Returns:
            Deduplicated merged list.
        """
        seen_norms: Dict[str, int] = {}  # norm -> index in result
        merged: List[Dict[str, Any]] = []

        for source in sources:
            for treaty in source:
                norm = _normalise_title(treaty.get("name", ""))
                if not norm:
                    continue

                if norm in seen_norms:
                    # Back-fill missing fields from the duplicate.
                    idx = seen_norms[norm]
                    existing = merged[idx]
                    for key, value in treaty.items():
                        if value and not existing.get(key):
                            existing[key] = value
                else:
                    seen_norms[norm] = len(merged)
                    merged.append(treaty)

        logger.info(
            "Merge complete: %d unique treaties from %d source(s).",
            len(merged),
            len(sources),
        )
        return merged

    # ------------------------------------------------------------------
    # URL resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_url(href: str) -> str:
        """Resolve a potentially relative href against the base URL."""
        if not href:
            return ""
        if href.startswith(("http://", "https://")):
            return href
        return urljoin(BASE_URL + "/", href)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def save_results(treaties: List[Dict[str, Any]], output_path: Path) -> None:
        """
        Save treaty results to a JSON file.

        Args:
            treaties: List of treaty dicts.
            output_path: Target file path.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(treaties, f, indent=2, ensure_ascii=False)
        logger.info("Saved %d treaties to %s", len(treaties), output_path)

    @staticmethod
    def load_existing(output_path: Path) -> List[Dict[str, Any]]:
        """
        Load previously saved treaty results from a JSON file.

        Args:
            output_path: Path to the JSON file.

        Returns:
            List of treaty dicts, or empty list if file does not exist
            or is not valid JSON.
        """
        if not output_path.is_file():
            logger.info("No existing results at %s", output_path)
            return []

        try:
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                logger.info(
                    "Loaded %d existing treaties from %s", len(data), output_path
                )
                return data
            logger.warning(
                "Unexpected JSON structure in %s, expected list.", output_path
            )
            return []
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load %s: %s", output_path, exc)
            return []

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        output_dir: str = "data/treaties",
        fetch_details: bool = False,
        max_details: int = 50,
        max_pages: Optional[int] = None,
        resume_from_page: int = 1,
        retry_failed: bool = False,
        max_retries: Optional[int] = None,
        merge_sources: bool = False,
    ) -> Dict[str, Any]:
        """
        Run the full treaty scraping pipeline.

        1. Scrape the SRE catalog for all treaty listings.
        2. Optionally scrape the Senate catalog and merge.
        3. Optionally fetch detail pages for richer metadata.
        4. Optionally retry failed detail fetches.
        5. Save results.
        6. Log summary.

        Args:
            output_dir: Directory for output files.
            fetch_details: Whether to fetch individual detail pages.
            max_details: Maximum number of detail pages to fetch.
            max_pages: Maximum catalog pages to scrape (None = all).
            resume_from_page: Page number to resume from (1-based).
            retry_failed: Re-fetch detail pages for treaties missing data.
            max_retries: Maximum retries when using --retry-failed.
            merge_sources: Scrape both SRE and Senate, then merge.

        Returns:
            Summary dict with total_treaties, output_path, details_fetched.
        """
        out_path = Path(output_dir)
        output_file = out_path / "discovered_treaties.json"
        logger.info(
            "Starting treaty scraper (fetch_details=%s, retry_failed=%s, merge_sources=%s)",
            fetch_details,
            retry_failed,
            merge_sources,
        )

        # ----------------------------------------------------------
        # Retry-failed mode: load existing data and re-fetch details
        # ----------------------------------------------------------
        if retry_failed:
            treaties = self.load_existing(output_file)
            if not treaties:
                logger.warning("No existing data to retry. Run a normal scrape first.")
                return {
                    "total_treaties": 0,
                    "details_retried": 0,
                    "output_path": str(output_file),
                }

            retried = self.retry_failed_details(treaties, max_retries=max_retries)
            self.save_results(treaties, output_file)

            summary = self._build_summary(treaties, output_file)
            summary["details_retried"] = retried
            logger.info("Treaty scraper (retry) complete: %s", summary)
            return summary

        # ----------------------------------------------------------
        # Normal scrape
        # ----------------------------------------------------------

        # Step 1: scrape SRE catalog
        treaties = self.scrape_catalog(
            max_pages=max_pages,
            resume_from_page=resume_from_page,
        )

        # Step 1b: optionally scrape Senate and merge
        if merge_sources:
            senate_treaties = self.scrape_senate_catalog()
            treaties = self.merge_treaty_lists(treaties, senate_treaties)

        # Step 2: optionally enrich with detail pages
        details_fetched = 0
        if fetch_details and treaties:
            for i, treaty in enumerate(treaties):
                if details_fetched >= max_details:
                    logger.info("Reached max_details=%d, stopping.", max_details)
                    break

                url = treaty.get("url", "")
                if not url:
                    continue

                # Skip treaties that already have detail data.
                if any(treaty.get(field) for field in _DETAIL_FIELDS):
                    continue

                detail = self.scrape_treaty_detail(url)
                if detail:
                    # Merge detail data into the treaty dict without
                    # overwriting existing non-empty fields.
                    for key, value in detail.items():
                        if value and not treaty.get(key):
                            treaty[key] = value
                    details_fetched += 1

                if (i + 1) % 10 == 0:
                    logger.info(
                        "Detail progress: %d/%d treaties enriched",
                        details_fetched,
                        min(len(treaties), max_details),
                    )

        # Step 3: save
        self.save_results(treaties, output_file)

        # Step 4: summary
        summary = self._build_summary(treaties, output_file)
        summary["details_fetched"] = details_fetched
        if merge_sources:
            summary["senate_scraped"] = True
        logger.info("Treaty scraper complete: %s", summary)
        return summary

    @staticmethod
    def _build_summary(
        treaties: List[Dict[str, Any]], output_file: Path
    ) -> Dict[str, Any]:
        """Build a summary dict from the treaty list."""
        bilateral = sum(1 for t in treaties if t.get("treaty_type") == "bilateral")
        multilateral = sum(
            1 for t in treaties if t.get("treaty_type") == "multilateral"
        )
        with_details = sum(
            1 for t in treaties if any(t.get(field) for field in _DETAIL_FIELDS)
        )
        missing_details = sum(
            1
            for t in treaties
            if t.get("url") and not any(t.get(field) for field in _DETAIL_FIELDS)
        )

        return {
            "total_treaties": len(treaties),
            "bilateral": bilateral,
            "multilateral": multilateral,
            "unknown_type": len(treaties) - bilateral - multilateral,
            "with_details": with_details,
            "missing_details": missing_details,
            "output_path": str(output_file),
        }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _clean_text(raw: str) -> str:
    """Collapse whitespace and strip surrounding blanks."""
    return re.sub(r"\s+", " ", raw).strip()


def _generate_id(name: str) -> str:
    """Generate a slug-style ID from a treaty name."""
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"\s+", "_", slug.strip())
    return slug[:80] if slug else "unknown"


def _classify_treaty_type(text: str) -> str:
    """
    Classify a treaty as bilateral or multilateral based on its title.

    Returns 'bilateral', 'multilateral', or 'unknown'.
    """
    text_lower = text.lower()

    for kw in _BILATERAL_KEYWORDS:
        if kw in text_lower:
            return "bilateral"

    for kw in _MULTILATERAL_KEYWORDS:
        if kw in text_lower:
            return "multilateral"

    return "unknown"


_SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def _extract_date(text: str) -> str:
    """
    Try to extract a date from free text.

    Handles:
      - "3 de febrero de 2004" (Spanish, used by successor portal)
      - DD/MM/YYYY or DD-MM-YYYY
      - YYYY-MM-DD (ISO)

    Returns ISO-format string or empty string.
    """
    if not text:
        return ""

    # Spanish format: "3 de febrero de 2004"
    match = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", text, re.IGNORECASE)
    if match:
        day_str, month_str, year_str = match.group(1), match.group(2), match.group(3)
        month_num = _SPANISH_MONTHS.get(month_str.lower())
        if month_num:
            try:
                return f"{year_str}-{month_num:02d}-{int(day_str):02d}"
            except (ValueError, TypeError):
                pass

    # DD/MM/YYYY or DD-MM-YYYY
    match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if match:
        day, month, year = match.group(1), match.group(2), match.group(3)
        try:
            return f"{year}-{int(month):02d}-{int(day):02d}"
        except (ValueError, TypeError):
            pass

    # YYYY-MM-DD already ISO
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return match.group(0)

    return ""


def _extract_field(soup: BeautifulSoup, labels: List[str]) -> str:
    """
    Search for a labeled field in the page DOM.

    Looks for elements containing any of the *labels* (case-insensitive)
    and returns the adjacent/following text content.
    """
    for label in labels:
        # Try label/value patterns: <dt>label</dt><dd>value</dd>
        for dt in soup.find_all("dt"):
            if label in dt.get_text().lower():
                dd = dt.find_next_sibling("dd")
                if dd:
                    return dd.get_text(strip=True)

        # Try table header/cell patterns.
        for th in soup.find_all("th"):
            if label in th.get_text().lower():
                td = th.find_next_sibling("td")
                if td:
                    return td.get_text(strip=True)

        # Try label + span/div patterns.
        for el in soup.find_all(["label", "strong", "b", "span"]):
            if label in el.get_text().lower():
                sibling = el.find_next_sibling()
                if sibling:
                    return sibling.get_text(strip=True)
                # Maybe the value is in the parent's remaining text.
                parent = el.parent
                if parent:
                    parent_text = parent.get_text(strip=True)
                    el_text = el.get_text(strip=True)
                    remainder = parent_text.replace(el_text, "", 1).strip()
                    if remainder:
                        return remainder

    return ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the treaty scraper."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Scrape international treaties from the SRE portal.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/treaties",
        help="Directory to save results (default: data/treaties).",
    )
    parser.add_argument(
        "--fetch-details",
        action="store_true",
        help="Fetch individual treaty detail pages for richer metadata.",
    )
    parser.add_argument(
        "--max-details",
        type=int,
        default=50,
        help="Maximum number of detail pages to fetch (default: 50).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum catalog pages to scrape (default: all ~151 pages).",
    )
    parser.add_argument(
        "--resume-from",
        type=int,
        default=1,
        help="Page number to resume from (1-based, default: 1).",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help=(
            "Load existing discovered_treaties.json and re-fetch detail pages "
            "for entries missing enriched data (full_text, date_ratified, parties)."
        ),
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Maximum number of detail pages to re-fetch in retry mode (default: all).",
    )
    parser.add_argument(
        "--merge-sources",
        action="store_true",
        help=(
            "Scrape both SRE and Senate portals, then merge results "
            "with deduplication by normalised treaty name."
        ),
    )
    args = parser.parse_args()

    scraper = TreatyScraper()
    result = scraper.run(
        output_dir=args.output_dir,
        fetch_details=args.fetch_details,
        max_details=args.max_details,
        max_pages=args.max_pages,
        resume_from_page=args.resume_from,
        retry_failed=args.retry_failed,
        max_retries=args.max_retries,
        merge_sources=args.merge_sources,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
