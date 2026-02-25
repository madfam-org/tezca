"""
Baja California State Congress Scraper

Scrapes legislation from the Baja California state congress portal.
Portal: https://www.congresobc.gob.mx
Expected catalog size: ~340 laws.
"""

import logging
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .base import StateCongressScraper

logger = logging.getLogger(__name__)


class BajaCaliforniaScraper(StateCongressScraper):
    """
    Scraper for the Baja California state congress website.

    The catalog is located at /Trabajolegislativo/Leyes and typically
    lists laws in HTML tables or unordered lists with links to PDF/DOC
    documents.
    """

    CATALOG_PATH = "/Trabajolegislativo/Leyes"
    ALTERNATIVE_PATHS = [
        "/trabajo-legislativo/leyes",
        "/leyes",
        "/legislacion",
        "/Trabajolegislativo/Legislacion",
    ]

    def __init__(self) -> None:
        super().__init__(
            state="Baja California",
            base_url="https://www.congresobc.gob.mx",
        )
        logger.info("Initialized %s scraper - %s", self.state, self.base_url)

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape the Baja California legislation catalog.

        Attempts the primary catalog path first, then falls back to
        alternative paths commonly used by Mexican congress portals.

        Returns:
            List of law dictionaries with name, url, state, tier, category, law_type.
        """
        html = self._fetch_catalog_page()
        if not html:
            logger.error("Could not fetch any catalog page for %s", self.state)
            return []

        soup = BeautifulSoup(html, "html.parser")
        laws: List[Dict] = []

        # Strategy 1: Look for links inside tables (common layout)
        laws.extend(self._extract_from_tables(soup))

        # Strategy 2: Look for links inside lists
        if not laws:
            laws.extend(self._extract_from_lists(soup))

        # Strategy 3: Fallback - scan all links for downloadable documents
        if not laws:
            laws.extend(self._extract_all_law_links(soup))

        # Deduplicate by URL
        seen_urls: set = set()
        unique_laws: List[Dict] = []
        for law in laws:
            if law["url"] not in seen_urls:
                seen_urls.add(law["url"])
                unique_laws.append(law)

        logger.info("Scraped %d laws from %s", len(unique_laws), self.state)
        return unique_laws

    def scrape_law_content(self, url: str) -> Optional[Dict]:
        """
        Download and extract content of a specific Baja California law.

        Args:
            url: URL of the law document.

        Returns:
            Dict with url, file_type, file_path, size_bytes, or None on failure.
        """
        output_dir = f"data/state/baja_california/raw"
        return self.download_file(url, output_dir)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_catalog_page(self) -> Optional[str]:
        """Try primary and alternative catalog paths until one succeeds."""
        primary_url = self.normalize_url(self.CATALOG_PATH)
        html = self.fetch_page(primary_url)
        if html:
            return html

        logger.warning(
            "Primary catalog path failed (%s), trying alternatives", primary_url
        )
        for alt_path in self.ALTERNATIVE_PATHS:
            alt_url = self.normalize_url(alt_path)
            html = self.fetch_page(alt_url)
            if html:
                logger.info("Found catalog at alternative path: %s", alt_url)
                return html

        return None

    def _extract_from_tables(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract law links from HTML table rows."""
        laws: List[Dict] = []
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                try:
                    links = row.find_all("a", href=True)
                    for link in links:
                        law = self._parse_link(link, row)
                        if law:
                            laws.append(law)
                except Exception as e:
                    logger.debug("Error parsing table row: %s", e)
                    continue
        return laws

    def _extract_from_lists(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract law links from unordered/ordered lists."""
        laws: List[Dict] = []
        for ul in soup.find_all(["ul", "ol"]):
            for li in ul.find_all("li"):
                try:
                    link = li.find("a", href=True)
                    if link:
                        law = self._parse_link(link, li)
                        if law:
                            laws.append(law)
                except Exception as e:
                    logger.debug("Error parsing list item: %s", e)
                    continue
        return laws

    def _extract_all_law_links(self, soup: BeautifulSoup) -> List[Dict]:
        """Fallback: scan all anchor tags for downloadable law documents."""
        laws: List[Dict] = []
        for link in soup.find_all("a", href=True):
            try:
                law = self._parse_link(link)
                if law:
                    laws.append(law)
            except Exception as e:
                logger.debug("Error parsing link: %s", e)
                continue
        return laws

    def _parse_link(self, link, parent_element=None) -> Optional[Dict]:
        """
        Parse a single anchor tag into a law dictionary.

        Args:
            link: BeautifulSoup anchor tag.
            parent_element: Optional parent element for additional text context.

        Returns:
            Law dict if the link is a valid law reference, None otherwise.
        """
        href = link["href"].strip()
        text = link.get_text(strip=True)

        # Try parent element for a more complete title
        if parent_element and (not text or len(text) < 10):
            text = parent_element.get_text(strip=True)

        # Skip if no meaningful text
        if not text or len(text) < 10:
            return None

        # Must be a downloadable document or contain law-related keywords
        absolute_url = self.normalize_url(href)
        if not self.is_downloadable(absolute_url) and not self._is_law_keyword(text):
            return None

        law = {
            "name": text[:500],  # Truncate overly long titles
            "url": absolute_url,
            "state": self.state,
            "tier": "state",
            "category": self.extract_category(text),
            "law_type": self._infer_law_type(text),
        }

        if self.validate_law_data(law):
            return law
        return None

    @staticmethod
    def _is_law_keyword(text: str) -> bool:
        """Check if text contains law-related keywords."""
        keywords = [
            "ley",
            "codigo",
            "código",
            "reglamento",
            "decreto",
            "constitución",
            "constitucion",
            "acuerdo",
            "norma",
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)

    @staticmethod
    def _infer_law_type(text: str) -> str:
        """Infer the law_type classification from the title."""
        text_lower = text.lower()
        if "constitución" in text_lower or "constitucion" in text_lower:
            return "constitucion_estatal"
        elif "código" in text_lower or "codigo" in text_lower:
            return "codigo"
        elif "ley orgánica" in text_lower or "ley organica" in text_lower:
            return "ley_organica"
        elif "ley" in text_lower:
            return "ley"
        elif "reglamento" in text_lower:
            return "reglamento"
        elif "decreto" in text_lower:
            return "decreto"
        else:
            return "otro"
