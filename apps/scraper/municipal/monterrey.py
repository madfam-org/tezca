"""
Monterrey Municipal Scraper

Scrapes regulations from Monterrey's transparency portal.
"""

import logging
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .base import MunicipalScraper
from .config import get_config

logger = logging.getLogger(__name__)


class MonterreyScraper(MunicipalScraper):
    def __init__(self):
        config = get_config("monterrey")
        super().__init__(config=config)
        self.session.verify = False
        logger.info(f"Initialized {self.municipality} scraper - {self.base_url}")

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape Monterrey's regulations catalog.

        Returns list of law dictionaries.
        """
        html = self.fetch_page(self.base_url + self.selectors.get("catalog_path", ""))

        if not html:
            logger.warning("Failed to fetch catalog")
            return []

        soup = BeautifulSoup(html, "html.parser")
        laws = []

        # Search for regulation links
        # Monterrey page lists federal, state and municipal laws mixed together.
        # We must filter strictly for municipal regulations.
        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            text = link.get_text(strip=True)

            if not text or len(text) < 10:
                continue

            # Normalize URL (handle relative)
            full_url = self.normalize_url(href, base=self.base_url)

            if self._is_regulation_link(text, full_url):
                law = {
                    "name": text,
                    "url": full_url,
                    "municipality": self.municipality,
                    "state": self.state,
                    "tier": "municipal",
                    "category": self.extract_category(text),
                }

                if self.validate_law_data(law):
                    laws.append(law)

        logger.info(f"Scraped {len(laws)} regulations from {self.municipality}")
        return laws

    def _is_regulation_link(self, text: str, href: str) -> bool:
        """Check if link appears to be a *municipal* regulation."""
        text_lower = text.lower()
        href_lower = href.lower()

        # Primary keywords for municipal regulations
        keywords = ["reglamento", "bando", "lineamientos", "bases", "criterios"]

        # Exclude federal/state laws, constitutions, treaties
        excludes = [
            "federal",
            "estatal",
            "constitución",
            "ley ",
            "código civil",
            "código penal",
            "pacto",
            "convención",
            "tratado",
            "estatuto",
            "general de",
            "nacional",
            "del estado",
            "de nuevo león",
        ]

        # Must match a keyword
        if not any(k in text_lower for k in keywords):
            return False

        # Must NOT match strict excludes
        if any(e in text_lower for e in excludes):
            return False

        return True

    def scrape_law_content(self, url: str, output_dir: str = None) -> Optional[Dict]:
        """Download and extract content of a specific law."""
        if output_dir is None:
            output_dir = "data/municipal/monterrey/raw"
        return self.download_law_content(url, output_dir)
