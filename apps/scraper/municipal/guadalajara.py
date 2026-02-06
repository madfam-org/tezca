"""
Guadalajara Municipal Scraper

Scrapes regulations from Guadalajara's transparency portal.
"""

import logging
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .base import MunicipalScraper
from .config import get_config

logger = logging.getLogger(__name__)


class GuadalajaraScraper(MunicipalScraper):
    def __init__(self):
        config = get_config("guadalajara")
        super().__init__(config=config)
        logger.info(f"Initialized {self.municipality} scraper - {self.base_url}")

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape Guadalajara's regulations catalog.

        Returns list of law dictionaries with name, URL, category.
        """
        # Try catalog path from config
        catalog_path = self.selectors.get("catalog_path", "/normatividad")
        catalog_url = self.normalize_url(catalog_path)

        html = self.fetch_page(catalog_url)
        if not html:
            logger.warning(f"Failed to fetch catalog from {catalog_url}")
            return []

        soup = BeautifulSoup(html, "html.parser")
        laws = []

        # Look for links containing "reglamento" or similar keywords
        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            text = link.get_text(strip=True)

            # Filter for regulation-related links
            if not text or len(text) < 10:
                continue

            if self._is_regulation_link(text, href):
                # Normalize URL
                absolute_url = self.normalize_url(href, base=catalog_url)

                law = {
                    "name": text,
                    "url": absolute_url,
                    "municipality": self.municipality,
                    "state": self.state,
                    "tier": "municipal",
                    "category": self.extract_category(text),
                }

                if self.validate_law_data(law):
                    laws.append(law)
                    logger.debug(f"Found regulation: {text}")

        logger.info(f"Scraped {len(laws)} regulations from {self.municipality}")
        return laws

    def _is_regulation_link(self, text: str, href: str) -> bool:
        """Check if link appears to be a regulation."""
        text_lower = text.lower()
        href_lower = href.lower()

        keywords = ["reglamento", "código", "codigo", "normativ", "regla"]

        # Exclude navigation links
        excludes = ["abrogado", "federal", "estatal", "transparencia"]
        if any(ex in text_lower for ex in excludes):
            return False

        return any(
            keyword in text_lower or keyword in href_lower for keyword in keywords
        )

    def scrape_law_content(self, url: str, output_dir: str = None) -> Optional[Dict]:
        """
        Download and extract content of a specific law.

        Most Guadalajara regulations are PDFs hosted on the transparency portal.
        """
        if output_dir is None:
            output_dir = f"data/municipal/guadalajara/raw"
        return self.download_law_content(url, output_dir)
