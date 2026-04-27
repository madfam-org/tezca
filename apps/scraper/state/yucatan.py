"""
Yucatán State Congress Scraper

Scrapes legislation from the Yucatán state congress portal.
Portal: https://www.congresoyucatan.gob.mx
Expected catalog size: ~250-300 laws.
"""

import logging
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .base import StateCongressScraper

logger = logging.getLogger(__name__)


class YucatanScraper(StateCongressScraper):
    """Scraper for the Yucatán state congress website."""

    CATALOG_PATH = "/leyes"
    ALTERNATIVE_PATHS = [
        "/marco-juridico",
        "/legislacion",
        "/biblioteca-legislativa",
        "/normatividad",
    ]

    def __init__(self) -> None:
        super().__init__(
            state="Yucatán",
            base_url="https://www.congresoyucatan.gob.mx",
        )
        logger.info("Initialized %s scraper - %s", self.state, self.base_url)

    def scrape_catalog(self) -> List[Dict]:
        html = self._fetch_catalog_page()
        if not html:
            logger.error("Could not fetch any catalog page for %s", self.state)
            return []
        soup = BeautifulSoup(html, "html.parser")
        laws: List[Dict] = []
        laws.extend(self._extract_from_tables(soup))
        if not laws:
            laws.extend(self._extract_from_lists(soup))
        if not laws:
            laws.extend(self._extract_all_law_links(soup))
        seen: set = set()
        unique_laws: List[Dict] = []
        for law in laws:
            if law["url"] not in seen:
                seen.add(law["url"])
                unique_laws.append(law)
        logger.info("Scraped %d laws from %s", len(unique_laws), self.state)
        return unique_laws

    def scrape_law_content(self, url: str) -> Optional[Dict]:
        return self.download_file(url, "data/state/yucatan/raw")

    def _fetch_catalog_page(self) -> Optional[str]:
        primary_url = self.normalize_url(self.CATALOG_PATH)
        html = self.fetch_page(primary_url)
        if html:
            return html
        for alt_path in self.ALTERNATIVE_PATHS:
            alt_url = self.normalize_url(alt_path)
            html = self.fetch_page(alt_url)
            if html:
                logger.info("Found catalog at alternative path: %s", alt_url)
                return html
        return None

    def _extract_from_tables(self, soup: BeautifulSoup) -> List[Dict]:
        laws: List[Dict] = []
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                try:
                    for link in row.find_all("a", href=True):
                        law = self._parse_link(link, row)
                        if law:
                            laws.append(law)
                except Exception as e:  # pragma: no cover
                    logger.debug("Error parsing table row: %s", e)
        return laws

    def _extract_from_lists(self, soup: BeautifulSoup) -> List[Dict]:
        laws: List[Dict] = []
        for ul in soup.find_all(["ul", "ol"]):
            for li in ul.find_all("li"):
                try:
                    link = li.find("a", href=True)
                    if link:
                        law = self._parse_link(link, li)
                        if law:
                            laws.append(law)
                except Exception as e:  # pragma: no cover
                    logger.debug("Error parsing list item: %s", e)
        return laws

    def _extract_all_law_links(self, soup: BeautifulSoup) -> List[Dict]:
        laws: List[Dict] = []
        for link in soup.find_all("a", href=True):
            try:
                law = self._parse_link(link)
                if law:
                    laws.append(law)
            except Exception as e:  # pragma: no cover
                logger.debug("Error parsing link: %s", e)
        return laws

    def _parse_link(self, link, parent_element=None) -> Optional[Dict]:
        href = link["href"].strip()
        text = link.get_text(strip=True)
        if parent_element and (not text or len(text) < 10):
            text = parent_element.get_text(strip=True)
        if not text or len(text) < 10:
            return None
        absolute_url = self.normalize_url(href)
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
        return law if self.validate_law_data(law) else None

    @staticmethod
    def _is_law_keyword(text: str) -> bool:
        keywords = (
            "ley",
            "codigo",
            "código",
            "reglamento",
            "decreto",
            "constitución",
            "constitucion",
            "acuerdo",
            "norma",
        )
        return any(kw in text.lower() for kw in keywords)

    @staticmethod
    def _infer_law_type(text: str) -> str:
        t = text.lower()
        if "constitución" in t or "constitucion" in t:
            return "constitucion_estatal"
        if "código" in t or "codigo" in t:
            return "codigo"
        if "ley orgánica" in t or "ley organica" in t:
            return "ley_organica"
        if "ley" in t:
            return "ley"
        if "reglamento" in t:
            return "reglamento"
        if "decreto" in t:
            return "decreto"
        return "otro"
