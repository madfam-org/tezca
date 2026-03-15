"""
Guerrero State Congress Scraper

Scrapes legislation from the Guerrero state congress portal.
Portal: https://congresoguerrero.gob.mx
Expected catalog size: ~200-400 laws.
"""

import logging
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .base import StateCongressScraper

logger = logging.getLogger(__name__)


class GuerreroScraper(StateCongressScraper):
    """
    Scraper for the Guerrero state congress website.

    The portal organizes legislation under /legislacion or /leyes. Multiple
    alternative paths are tried since Mexican congress portals frequently
    restructure their URLs.
    """

    CATALOG_PATHS = [
        "/legislacion",
        "/leyes",
        "/trabajo-legislativo/leyes",
        "/legislacion/leyes-vigentes",
        "/marco-juridico",
        "/transparencia/legislacion",
    ]

    # Keywords for link filtering
    LAW_KEYWORDS = frozenset(
        {
            "ley",
            "codigo",
            "código",
            "reglamento",
            "decreto",
            "constitución",
            "constitucion",
            "acuerdo",
            "bando",
            "lineamiento",
            "norma",
        }
    )

    # Navigation/noise exclusions
    EXCLUDE_KEYWORDS = frozenset(
        {
            "facebook",
            "twitter",
            "instagram",
            "youtube",
            "contacto",
            "inicio",
            "home",
            "login",
            "mailto:",
            "#",
        }
    )

    def __init__(self) -> None:
        super().__init__(
            state="Guerrero",
            base_url="https://congresoguerrero.gob.mx",
        )
        logger.info("Initialized %s scraper - %s", self.state, self.base_url)

    def scrape_catalog(self) -> List[Dict]:
        """Scrape the Guerrero legislation catalog."""
        html = self._fetch_catalog_page()
        if not html:
            logger.error("Could not fetch any catalog page for %s", self.state)
            return []

        soup = BeautifulSoup(html, "html.parser")
        laws: List[Dict] = []

        # Strategy 1: Table-based layout
        laws.extend(self._extract_from_tables(soup))

        # Strategy 2: List-based layout
        if not laws:
            laws.extend(self._extract_from_lists(soup))

        # Strategy 3: Card/div patterns common in modern congress portals
        if not laws:
            laws.extend(self._extract_from_cards(soup))

        # Strategy 4: All law-related links as fallback
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
        """Download and extract content of a specific Guerrero law."""
        output_dir = "data/state/guerrero/raw"
        return self.download_file(url, output_dir)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_catalog_page(self) -> Optional[str]:
        """Try multiple catalog paths until one succeeds."""
        for path in self.CATALOG_PATHS:
            url = self.normalize_url(path)
            html = self.fetch_page(url)
            if html:
                logger.info("Found catalog at: %s", url)
                return html
        return None

    def _extract_from_tables(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract law links from HTML table rows."""
        laws: List[Dict] = []
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                for link in row.find_all("a", href=True):
                    law = self._parse_link(link, row)
                    if law:
                        laws.append(law)
        return laws

    def _extract_from_lists(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract law links from unordered/ordered lists."""
        laws: List[Dict] = []
        for ul in soup.find_all(["ul", "ol"]):
            for li in ul.find_all("li"):
                link = li.find("a", href=True)
                if link:
                    law = self._parse_link(link, li)
                    if law:
                        laws.append(law)
        return laws

    def _extract_from_cards(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract law links from card/article/div patterns."""
        laws: List[Dict] = []
        for container in soup.find_all(["article", "div"], class_=True):
            classes = " ".join(container.get("class", []))
            if any(kw in classes for kw in ("card", "entry", "post", "item", "ley")):
                for link in container.find_all("a", href=True):
                    law = self._parse_link(link, container)
                    if law:
                        laws.append(law)
        return laws

    def _extract_all_law_links(self, soup: BeautifulSoup) -> List[Dict]:
        """Fallback: scan all anchor tags for downloadable law documents."""
        laws: List[Dict] = []
        for link in soup.find_all("a", href=True):
            law = self._parse_link(link)
            if law:
                laws.append(law)
        return laws

    def _parse_link(self, link, parent_element=None) -> Optional[Dict]:
        """Parse a single anchor tag into a law dictionary."""
        href = link["href"].strip()

        # Skip noise links
        if any(ex in href.lower() for ex in self.EXCLUDE_KEYWORDS):
            return None

        text = link.get_text(strip=True)

        # Try parent element for more complete title
        if parent_element and (not text or len(text) < 10):
            text = parent_element.get_text(strip=True)

        if not text or len(text) < 10:
            return None

        absolute_url = self.normalize_url(href)

        # Must be downloadable or contain law keywords
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

    def _is_law_keyword(self, text: str) -> bool:
        """Check if text contains law-related keywords."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.LAW_KEYWORDS)

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


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Scrape Guerrero state congress")
    parser.add_argument(
        "--dry-run", action="store_true", help="Just probe, don't download"
    )
    parser.add_argument("--limit", type=int, help="Limit number of laws")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    scraper = GuerreroScraper()
    catalog = scraper.scrape_catalog()

    if args.limit:
        catalog = catalog[: args.limit]

    print(f"\nFound {len(catalog)} laws")
    for law in catalog[:10]:
        print(f"  - {law['name'][:80]} [{law['category']}]")

    if not args.dry_run and catalog:
        output_path = "data/state/guerrero/catalog.json"
        from pathlib import Path

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {output_path}")
