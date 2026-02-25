"""
Durango State Congress Scraper

Scrapes legislation from the Durango state congress portal.
Portal: https://congresodurango.gob.mx
Expected catalog size: ~160 laws.
"""

import logging
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .base import StateCongressScraper

logger = logging.getLogger(__name__)


class DurangoScraper(StateCongressScraper):
    """
    Scraper for the Durango state congress website.

    The legislation catalog is at /trabajo-legislativo/legislacion-estatal/
    and typically lists laws with links to PDF/DOCX documents.
    """

    CATALOG_PATH = "/trabajo-legislativo/legislacion-estatal/"
    ALTERNATIVE_PATHS = [
        "/legislacion-estatal",
        "/legislacion",
        "/leyes",
        "/trabajo-legislativo/leyes",
    ]

    def __init__(self) -> None:
        super().__init__(
            state="Durango",
            base_url="https://congresodurango.gob.mx",
        )
        logger.info("Initialized %s scraper - %s", self.state, self.base_url)

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape the Durango legislation catalog.

        Tries the primary path, then falls back to alternatives.
        Handles both paginated and single-page catalog layouts.

        Returns:
            List of law dictionaries.
        """
        html = self._fetch_catalog_page()
        if not html:
            logger.error("Could not fetch any catalog page for %s", self.state)
            return []

        laws: List[Dict] = []
        page_num = 1

        while html:
            soup = BeautifulSoup(html, "html.parser")
            page_laws = self._extract_laws_from_page(soup)
            laws.extend(page_laws)
            logger.debug("Page %d: found %d laws", page_num, len(page_laws))

            # Check for pagination
            next_url = self._find_next_page(soup)
            if next_url and page_num < 50:  # Safety cap
                page_num += 1
                html = self.fetch_page(next_url)
            else:
                break

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
        Download and extract content of a specific Durango law.

        Args:
            url: URL of the law document.

        Returns:
            Dict with url, file_type, file_path, size_bytes, or None on failure.
        """
        output_dir = "data/state/durango/raw"
        return self.download_file(url, output_dir)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_catalog_page(self) -> Optional[str]:
        """Try primary and alternative catalog paths."""
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

    def _extract_laws_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Extract law entries from a single catalog page.

        Searches for downloadable document links inside article elements,
        content divs, tables, and lists.

        Args:
            soup: Parsed HTML of the catalog page.

        Returns:
            List of law dictionaries found on this page.
        """
        laws: List[Dict] = []

        # Look in content containers first (WordPress-style layouts)
        content_areas = soup.find_all(
            ["article", "div", "section"],
            class_=lambda c: c
            and any(
                kw in (c if isinstance(c, str) else " ".join(c))
                for kw in ["content", "entry", "post", "legislacion", "leyes"]
            ),
        )

        # Fall back to full page if no content areas found
        search_areas = content_areas if content_areas else [soup]

        for area in search_areas:
            for link in area.find_all("a", href=True):
                try:
                    law = self._parse_law_link(link)
                    if law:
                        laws.append(law)
                except Exception as e:
                    logger.debug("Error parsing link: %s", e)
                    continue

        return laws

    def _parse_law_link(self, link) -> Optional[Dict]:
        """
        Parse an anchor tag into a law dictionary.

        Args:
            link: BeautifulSoup anchor tag.

        Returns:
            Law dict or None if the link is not a valid law reference.
        """
        href = link["href"].strip()
        text = link.get_text(strip=True)

        if not text or len(text) < 8:
            return None

        absolute_url = self.normalize_url(href)

        # Accept downloadable files or links with law keywords
        if not self.is_downloadable(absolute_url) and not self._is_law_keyword(text):
            return None

        law = {
            "name": text[:500],
            "url": absolute_url,
            "state": self.state,
            "tier": "state",
            "category": self.extract_category(text),
            "law_type": self._infer_law_type(text),
        }

        if self.validate_law_data(law):
            return law
        return None

    def _find_next_page(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Find the URL of the next pagination page.

        Handles common WordPress and custom pagination patterns.

        Args:
            soup: Parsed HTML of the current page.

        Returns:
            Absolute URL of the next page, or None if no next page.
        """
        # WordPress-style pagination
        next_link = soup.find("a", class_="next")
        if next_link and next_link.get("href"):
            return self.normalize_url(next_link["href"])

        # "Siguiente" / "Next" link text
        for link in soup.find_all("a", href=True):
            link_text = link.get_text(strip=True).lower()
            if link_text in ("siguiente", "next", ">>", ">"):
                return self.normalize_url(link["href"])

        # aria-label based pagination
        next_link = soup.find(
            "a", attrs={"aria-label": lambda v: v and "next" in v.lower()}
        )
        if next_link and next_link.get("href"):
            return self.normalize_url(next_link["href"])

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
