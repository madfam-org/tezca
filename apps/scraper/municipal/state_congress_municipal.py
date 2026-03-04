"""
State Congress Municipal Scraper

Scrapes state congress portals that centrally publish municipal income laws
(leyes de ingresos municipales). These portals aggregate laws for all
municipalities within a state, unlike individual municipal scrapers that
target a single city's transparency site.

Priority states: Jalisco, Nuevo Leon, CDMX, Queretaro, Yucatan.
"""

import argparse
import logging
import re
from os.path import basename, splitext
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from .base import MunicipalScraper

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Portal Registry
# ---------------------------------------------------------------------------
# Each entry describes how to navigate a state congress portal to find
# municipal income law PDFs. Fields:
#   base_url        - Root URL of the congress portal
#   catalog_path    - Relative path to the page listing municipal laws
#   state           - Official state name (used in output metadata)
#   state_id        - Short lowercase identifier
#   selectors       - CSS / keyword hints for link discovery
#       law_links   - CSS selector for candidate links on the catalog page
#       title       - CSS selector for extracting document titles
#       container   - CSS selector narrowing search to a specific page region
#   pagination      - Dict describing pagination, or None if single-page
#       param       - Query string parameter for page number
#       start       - First page index
#       max_pages   - Hard ceiling to prevent runaway crawls
#   keywords        - Regex patterns that indicate a municipal income law
#   exclude         - Regex patterns for links to skip

STATE_CONGRESS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "jalisco": {
        "base_url": "https://congresojal.gob.mx",
        "catalog_path": "/servicios/BibVirtual/busquedasleyes.aspx",
        "state": "Jalisco",
        "state_id": "jalisco",
        "selectors": {
            "law_links": "a[href$='.pdf'], a[href*='leyesmunicipales']",
            "title": "td, span.titulo, a",
            "container": "#contenido, .contenido, .main-content, body",
        },
        "pagination": {
            "param": "pagina",
            "start": 1,
            "max_pages": 50,
        },
        "keywords": re.compile(
            r"ley\s+de\s+ingresos|presupuesto\s+de\s+egresos|hacienda\s+municipal",
            re.IGNORECASE,
        ),
        "exclude": re.compile(
            r"ley\s+estatal|constituci[oó]n|c[oó]digo\s+civil|transparencia",
            re.IGNORECASE,
        ),
    },
    "nuevo_leon": {
        "base_url": "https://www.hcnl.gob.mx",
        "catalog_path": "/trabajo_legislativo/leyes.php",
        "state": "Nuevo Leon",
        "state_id": "nuevo_leon",
        "selectors": {
            "law_links": "a[href$='.pdf'], a[href*='leyes']",
            "title": "td, a, span",
            "container": ".contenido, #contenido, .main, body",
        },
        "pagination": None,
        "keywords": re.compile(
            r"ley\s+de\s+ingresos|ingresos\s+del\s+municipio|hacienda\s+municipal",
            re.IGNORECASE,
        ),
        "exclude": re.compile(
            r"ley\s+estatal|reforma\s+constitucional|transparencia",
            re.IGNORECASE,
        ),
    },
    "cdmx": {
        "base_url": "https://www.congresocdmx.gob.mx",
        "catalog_path": "/archivos-legislativos",
        "state": "Ciudad de Mexico",
        "state_id": "cdmx",
        "selectors": {
            "law_links": "a[href$='.pdf'], a[href*='alcaldia']",
            "title": "td, a, span.titulo",
            "container": ".field-items, .view-content, .contenido, body",
        },
        "pagination": {
            "param": "page",
            "start": 0,
            "max_pages": 30,
        },
        "keywords": re.compile(
            r"ley\s+de\s+ingresos|presupuesto.*alcald[ií]a|"
            r"alcald[ií]a|demarcaci[oó]n\s+territorial",
            re.IGNORECASE,
        ),
        "exclude": re.compile(
            r"constituci[oó]n\s+pol[ií]tica|ley\s+org[aá]nica\s+del\s+congreso",
            re.IGNORECASE,
        ),
    },
    "queretaro": {
        "base_url": "https://www.legislaturaqueretaro.gob.mx",
        "catalog_path": "/leyes-estatales",
        "state": "Queretaro",
        "state_id": "queretaro",
        "selectors": {
            "law_links": "a[href$='.pdf'], a[href*='ley']",
            "title": "td, a, span",
            "container": ".view-content, .contenido, body",
        },
        "pagination": None,
        "keywords": re.compile(
            r"ley\s+de\s+ingresos|hacienda\s+municipal|"
            r"ingresos.*municipio|presupuesto\s+de\s+egresos",
            re.IGNORECASE,
        ),
        "exclude": re.compile(
            r"constituci[oó]n|ley\s+org[aá]nica\s+del\s+poder",
            re.IGNORECASE,
        ),
    },
    "yucatan": {
        "base_url": "https://www.congresoyucatan.gob.mx",
        "catalog_path": "/leyes-vigentes",
        "state": "Yucatan",
        "state_id": "yucatan",
        "selectors": {
            "law_links": "a[href$='.pdf'], a[href*='ingreso']",
            "title": "td, a, span",
            "container": ".view-content, .contenido, .main-content, body",
        },
        "pagination": {
            "param": "page",
            "start": 0,
            "max_pages": 30,
        },
        "keywords": re.compile(
            r"ley\s+de\s+ingresos|hacienda\s+municipal|ingresos.*municipio",
            re.IGNORECASE,
        ),
        "exclude": re.compile(
            r"constituci[oó]n|ley\s+org[aá]nica\s+del\s+poder|transparencia",
            re.IGNORECASE,
        ),
    },
}

# Shared pattern for extracting municipality names from law titles
_MUNICIPALITY_PATTERN = re.compile(
    r"(?:municipio\s+de|del\s+municipio\s+de)\s+([A-Z\u00C0-\u024F][a-z\u00E0-\u024F]+"
    r"(?:\s+[A-Z\u00C0-\u024F][a-z\u00E0-\u024F]+)*)",
    re.IGNORECASE,
)

_FISCAL_YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")


class StateCongressMunicipalScraper(MunicipalScraper):
    """
    Scraper for state congress portals that publish municipal income laws.

    Unlike per-city municipal scrapers, this scraper targets a single state
    congress website and discovers laws for *all* municipalities within that
    state. It produces one catalog entry per PDF, tagged with the municipality
    name extracted from the document title.
    """

    def __init__(self, state_id: str, max_results: int = 0):
        """
        Initialize the scraper for a given state congress portal.

        Args:
            state_id: Key from STATE_CONGRESS_REGISTRY (e.g. 'jalisco').
            max_results: Maximum number of catalog entries to return.
                         0 means unlimited.

        Raises:
            ValueError: If state_id is not in the registry.
        """
        if state_id not in STATE_CONGRESS_REGISTRY:
            available = ", ".join(sorted(STATE_CONGRESS_REGISTRY.keys()))
            raise ValueError(f"Unknown state '{state_id}'. Available: {available}")

        portal = STATE_CONGRESS_REGISTRY[state_id]

        # Build a config dict compatible with MunicipalScraper.__init__
        config = {
            "name": portal["state"],
            "base_url": portal["base_url"],
            "state": portal["state"],
            "selectors": portal["selectors"],
        }
        super().__init__(config=config)

        self.state_id = state_id
        self.portal = portal
        self.max_results = max_results
        self.keywords: re.Pattern = portal["keywords"]
        self.exclude: re.Pattern = portal["exclude"]
        self.pagination = portal.get("pagination")

        logger.info(
            "Initialized StateCongressMunicipalScraper for %s (%s)",
            portal["state"],
            portal["base_url"],
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scrape_catalog(self) -> List[Dict]:
        """
        Navigate the state congress portal and discover municipal law PDFs.

        Returns:
            List of law dictionaries. Each dict contains:
                name, url, municipality, state, tier, category,
                fiscal_year (if detected), status.
        """
        catalog_url = urljoin(self.portal["base_url"], self.portal["catalog_path"])
        logger.info("[%s] Starting catalog scrape: %s", self.state_id, catalog_url)

        all_laws: List[Dict] = []
        seen_urls: Set[str] = set()

        if self.pagination:
            all_laws = self._scrape_paginated_catalog(catalog_url, seen_urls)
        else:
            page_laws = self._scrape_catalog_page(catalog_url, seen_urls)
            all_laws.extend(page_laws)

        if self.max_results > 0:
            all_laws = all_laws[: self.max_results]

        logger.info(
            "[%s] Catalog scrape complete: %d municipal laws discovered",
            self.state_id,
            len(all_laws),
        )
        return all_laws

    def scrape_law_content(self, url: str, output_dir: str = None) -> Optional[Dict]:
        """
        Download the content of a discovered municipal law PDF.

        Args:
            url: Absolute URL of the law document.
            output_dir: Directory to save the downloaded file.
                        Defaults to data/municipal/{state_id}/congress/.

        Returns:
            Dict with url, file_type, file_path, text_content, size_bytes
            or None on failure.
        """
        if output_dir is None:
            output_dir = f"data/municipal/{self.state_id}/congress"

        return self.download_law_content(url, output_dir)

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def _scrape_paginated_catalog(
        self, base_catalog_url: str, seen_urls: Set[str]
    ) -> List[Dict]:
        """
        Iterate through paginated catalog pages until no new results appear.

        Args:
            base_catalog_url: First page URL (without pagination parameter).
            seen_urls: Shared deduplication set.

        Returns:
            Aggregated list of law dictionaries from all pages.
        """
        param = self.pagination["param"]
        start = self.pagination["start"]
        max_pages = self.pagination["max_pages"]

        all_laws: List[Dict] = []
        consecutive_empty = 0

        for page_idx in range(start, start + max_pages):
            separator = "&" if "?" in base_catalog_url else "?"
            page_url = f"{base_catalog_url}{separator}{param}={page_idx}"

            logger.debug("[%s] Fetching page %d: %s", self.state_id, page_idx, page_url)

            page_laws = self._scrape_catalog_page(page_url, seen_urls)

            if not page_laws:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    logger.info(
                        "[%s] Two consecutive empty pages at index %d, stopping pagination",
                        self.state_id,
                        page_idx,
                    )
                    break
            else:
                consecutive_empty = 0
                all_laws.extend(page_laws)

            if self.max_results > 0 and len(all_laws) >= self.max_results:
                break

        return all_laws

    # ------------------------------------------------------------------
    # Single page scraping
    # ------------------------------------------------------------------

    def _scrape_catalog_page(self, page_url: str, seen_urls: Set[str]) -> List[Dict]:
        """
        Scrape a single catalog page for municipal law links.

        Args:
            page_url: URL of the catalog page.
            seen_urls: Shared deduplication set (modified in place).

        Returns:
            List of law dictionaries found on the page.
        """
        html = self.fetch_page(page_url)
        if not html:
            logger.warning("[%s] Failed to fetch: %s", self.state_id, page_url)
            return []

        soup = BeautifulSoup(html, "html.parser")
        container = self._find_container(soup)

        laws: List[Dict] = []
        subpage_candidates: List[tuple] = []

        for link in container.find_all("a", href=True):
            href = link["href"].strip()
            text = link.get_text(separator=" ", strip=True)

            if not self._is_municipal_law_link(text, href):
                continue

            absolute_url = self.normalize_url(href, page_url)

            parsed = urlparse(absolute_url)
            if parsed.scheme not in ("http", "https"):
                continue

            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)

            if self.is_pdf(absolute_url):
                law = self._build_law_entry(text, absolute_url)
                if self.validate_law_data(law):
                    laws.append(law)
                    logger.debug("[%s] Found PDF: %s", self.state_id, text[:80])
            else:
                subpage_candidates.append((absolute_url, text))

        # Follow HTML links one level deep to find PDFs behind detail pages
        if subpage_candidates:
            logger.info(
                "[%s] Following %d subpages for PDF discovery",
                self.state_id,
                len(subpage_candidates),
            )
            for sub_url, parent_text in subpage_candidates:
                sub_laws = self._scrape_subpage_for_pdfs(
                    sub_url, parent_text, seen_urls
                )
                laws.extend(sub_laws)

        return laws

    def _scrape_subpage_for_pdfs(
        self, url: str, parent_text: str, seen_urls: Set[str]
    ) -> List[Dict]:
        """
        Follow a non-PDF link one level deep to discover PDF documents.

        Args:
            url: Subpage URL.
            parent_text: Link text from the parent page (title context).
            seen_urls: Shared deduplication set (modified in place).

        Returns:
            List of law dictionaries found on the subpage.
        """
        html = self.fetch_page(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        laws: List[Dict] = []

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            text = link.get_text(separator=" ", strip=True)
            absolute_url = self.normalize_url(href, url)

            parsed = urlparse(absolute_url)
            if parsed.scheme not in ("http", "https"):
                continue

            if absolute_url in seen_urls:
                continue

            if self.is_pdf(absolute_url):
                seen_urls.add(absolute_url)
                title = text if text and len(text) > 10 else parent_text
                if not title:
                    title = self._title_from_url(absolute_url)

                law = self._build_law_entry(title, absolute_url)
                if self.validate_law_data(law):
                    laws.append(law)

        return laws

    # ------------------------------------------------------------------
    # Link classification
    # ------------------------------------------------------------------

    def _is_municipal_law_link(self, text: str, href: str) -> bool:
        """
        Determine whether a link points to a municipal income law.

        Args:
            text: Visible link text.
            href: Link href attribute.

        Returns:
            True if the link matches municipal income law patterns.
        """
        combined = f"{text} {href}"

        # Reject excluded patterns first
        if self.exclude.search(combined):
            return False

        # Accept if keywords match
        if self.keywords.search(combined):
            return True

        # Accept direct PDF links that mention "ingreso" in path
        href_lower = href.lower()
        if href_lower.endswith(".pdf") and "ingreso" in href_lower:
            return True

        return False

    def _find_container(self, soup: BeautifulSoup) -> Tag:
        """
        Narrow the search area to the main content region of the page.

        Falls back to the full document body if no configured container
        selector matches.

        Args:
            soup: Parsed HTML document.

        Returns:
            A BeautifulSoup Tag representing the content container.
        """
        container_selector = self.selectors.get("container", "body")

        for selector in container_selector.split(","):
            selector = selector.strip()
            match = soup.select_one(selector)
            if match:
                return match

        return soup

    # ------------------------------------------------------------------
    # Data construction helpers
    # ------------------------------------------------------------------

    def _build_law_entry(self, raw_title: str, url: str) -> Dict:
        """
        Build a standardized law dictionary from a discovered link.

        Extracts the municipality name and fiscal year from the title text
        when possible. Falls back to the state name as the municipality
        field if no municipality can be parsed from the title.

        Args:
            raw_title: Raw text from the link or page.
            url: Absolute URL to the document.

        Returns:
            Law dictionary with all required fields.
        """
        title = re.sub(r"\s+", " ", raw_title).strip()
        municipality = self._extract_municipality(title, url)
        fiscal_year = self._extract_fiscal_year(title, url)

        entry = {
            "name": title,
            "url": url,
            "municipality": municipality,
            "state": self.portal["state"],
            "tier": "municipal",
            "category": self._classify_document(title),
            "status": "Discovered",
            "source": "state_congress",
            "source_portal": self.portal["base_url"],
        }

        if fiscal_year:
            entry["fiscal_year"] = fiscal_year

        return entry

    def _extract_municipality(self, title: str, url: str) -> str:
        """
        Extract the municipality name from a law title or URL.

        Args:
            title: Document title text.
            url: Document URL.

        Returns:
            Municipality name, or the state name as fallback.
        """
        match = _MUNICIPALITY_PATTERN.search(title)
        if match:
            return match.group(1).strip()

        # Try extracting from the URL path segments
        path = unquote(urlparse(url).path).lower()
        path_parts = [p for p in path.split("/") if p and p != "pdf"]
        for part in reversed(path_parts):
            cleaned = part.replace("_", " ").replace("-", " ")
            # If the path segment looks like a municipality name (starts with
            # uppercase after cleaning, not a generic word)
            if len(cleaned) > 3 and not re.match(
                r"^(ley|decreto|acuerdo|ingreso|presupuesto|doc|archivo|download)",
                cleaned,
            ):
                # Only use path-based extraction if it could be a proper noun
                words = cleaned.split()
                if all(len(w) > 1 for w in words):
                    return cleaned.title()

        return self.portal["state"]

    def _extract_fiscal_year(self, title: str, url: str) -> Optional[str]:
        """
        Extract the fiscal year from title text or URL.

        Args:
            title: Document title text.
            url: Document URL.

        Returns:
            Four-digit year string, or None.
        """
        match = _FISCAL_YEAR_PATTERN.search(title)
        if match:
            return match.group(1)

        match = _FISCAL_YEAR_PATTERN.search(url)
        if match:
            return match.group(1)

        return None

    def _classify_document(self, title: str) -> str:
        """
        Classify a document based on its title.

        Args:
            title: Document title text.

        Returns:
            Category string.
        """
        title_lower = title.lower()

        if "ley de ingresos" in title_lower:
            return "Ley de Ingresos"
        if "presupuesto de egresos" in title_lower:
            return "Presupuesto de Egresos"
        if "hacienda municipal" in title_lower:
            return "Ley de Hacienda Municipal"
        if "tabla de valores" in title_lower:
            return "Tabla de Valores"

        return self.extract_category(title)

    def _title_from_url(self, url: str) -> str:
        """
        Derive a human-readable title from a URL filename.

        Args:
            url: Document URL.

        Returns:
            Cleaned title string.
        """
        filename = basename(unquote(urlparse(url).path))
        name_body = splitext(filename)[0]
        return name_body.replace("_", " ").replace("-", " ")


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def list_supported_states() -> List[str]:
    """
    Return sorted list of state IDs supported by this scraper.

    Returns:
        List of state identifier strings.
    """
    return sorted(STATE_CONGRESS_REGISTRY.keys())


def get_portal_info(state_id: str) -> Dict[str, str]:
    """
    Return summary information about a state congress portal.

    Args:
        state_id: Key from STATE_CONGRESS_REGISTRY.

    Returns:
        Dict with state, base_url, catalog_path.

    Raises:
        ValueError: If state_id is not registered.
    """
    if state_id not in STATE_CONGRESS_REGISTRY:
        available = ", ".join(sorted(STATE_CONGRESS_REGISTRY.keys()))
        raise ValueError(f"Unknown state '{state_id}'. Available: {available}")

    portal = STATE_CONGRESS_REGISTRY[state_id]
    return {
        "state": portal["state"],
        "state_id": state_id,
        "base_url": portal["base_url"],
        "catalog_path": portal["catalog_path"],
    }


def scrape_state(state_id: str, max_results: int = 0) -> List[Dict]:
    """
    Convenience function to scrape a state and return results.

    Args:
        state_id: Key from STATE_CONGRESS_REGISTRY.
        max_results: Maximum results (0 = unlimited).

    Returns:
        List of law dictionaries.
    """
    scraper = StateCongressMunicipalScraper(state_id, max_results=max_results)
    return scraper.scrape_catalog()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description=(
            "Scrape state congress portals for municipal income laws "
            "(leyes de ingresos municipales)."
        ),
    )
    parser.add_argument(
        "--state",
        type=str,
        help="State ID to scrape (e.g. jalisco, nuevo_leon, cdmx).",
    )
    parser.add_argument(
        "--list-states",
        action="store_true",
        help="List all supported state congress portals and exit.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=0,
        help="Maximum number of results to return (0 = unlimited).",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download discovered PDFs after catalog scrape.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Override default output directory for downloads.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug-level logging.",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.list_states:
        print("\nSupported state congress portals:")
        print(f"{'='*60}")
        for sid in list_supported_states():
            info = get_portal_info(sid)
            print(f"  {sid:<16} {info['state']:<20} {info['base_url']}")
        print(f"{'='*60}")
        raise SystemExit(0)

    if not args.state:
        parser.error("--state is required unless --list-states is used.")

    state_id = args.state.lower().replace(" ", "_").replace("-", "_")

    scraper = StateCongressMunicipalScraper(state_id, max_results=args.max_results)
    results = scraper.scrape_catalog()

    print(f"\n{'='*70}")
    print(f"State: {scraper.portal['state']} ({state_id})")
    print(f"Portal: {scraper.portal['base_url']}")
    print(f"Municipal laws discovered: {len(results)}")
    print(f"{'='*70}")

    # Group results by municipality for readability
    by_municipality: Dict[str, List[Dict]] = {}
    for law in results:
        muni = law.get("municipality", "Unknown")
        by_municipality.setdefault(muni, []).append(law)

    for muni_name in sorted(by_municipality.keys()):
        muni_laws = by_municipality[muni_name]
        print(f"\n  {muni_name} ({len(muni_laws)} laws):")
        for law in muni_laws:
            year = law.get("fiscal_year", "")
            year_str = f" [{year}]" if year else ""
            print(f"    - {law['name'][:70]}{year_str}")
            print(f"      {law['url']}")

    if args.download and results:
        print(f"\nDownloading {len(results)} documents...")
        success_count = 0
        fail_count = 0

        for i, law in enumerate(results, 1):
            output_dir = args.output_dir
            if output_dir is None:
                muni_slug = re.sub(
                    r"[^a-z0-9]+", "_", law["municipality"].lower()
                ).strip("_")
                output_dir = f"data/municipal/{state_id}/{muni_slug}"

            result = scraper.scrape_law_content(law["url"], output_dir=output_dir)
            if result:
                success_count += 1
                size_kb = result.get("size_bytes", 0) / 1024
                logger.info(
                    "[%d/%d] Downloaded: %s (%.1f KB)",
                    i,
                    len(results),
                    law["name"][:50],
                    size_kb,
                )
            else:
                fail_count += 1
                logger.warning("[%d/%d] Failed: %s", i, len(results), law["name"][:50])

        print(f"\nDownload complete: {success_count} succeeded, {fail_count} failed")
