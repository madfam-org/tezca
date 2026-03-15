"""
Nuevo León State Congress Scraper

Scrapes legislation from the Nuevo León state congress portal.
Portal: https://www.hcnl.gob.mx
Expected catalog size: ~300-500 laws.
Also useful as municipal source for Monterrey.
"""

import logging
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .base import StateCongressScraper

logger = logging.getLogger(__name__)


class NuevoLeonScraper(StateCongressScraper):
    """
    Scraper for the Nuevo León state congress (HCNL) website.

    The HCNL portal provides legislation under various paths. This scraper
    tries multiple known locations and extracts law links from tables,
    lists, and card patterns.
    """

    CATALOG_PATHS = [
        "/trabajo-legislativo/leyes",
        "/leyes",
        "/legislacion",
        "/trabajo-legislativo/legislacion",
        "/trabajo_legislativo/leyes",
        "/transparencia/leyes-y-reglamentos",
        "/marco-juridico",
    ]

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
            "lineamiento",
            "norma",
            "bando",
        }
    )

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
            "javascript:",
        }
    )

    def __init__(self) -> None:
        super().__init__(
            state="Nuevo León",
            base_url="https://www.hcnl.gob.mx",
        )
        logger.info("Initialized %s scraper - %s", self.state, self.base_url)

    def scrape_catalog(self) -> List[Dict]:
        """Scrape the Nuevo León legislation catalog."""
        html = self._fetch_catalog_page()
        if not html:
            logger.error("Could not fetch any catalog page for %s", self.state)
            return []

        soup = BeautifulSoup(html, "html.parser")
        laws: List[Dict] = []

        # Strategy 1: Table rows (HCNL often uses tabular layout)
        laws.extend(self._extract_from_tables(soup))

        # Strategy 2: List items
        if not laws:
            laws.extend(self._extract_from_lists(soup))

        # Strategy 3: Card/div patterns
        if not laws:
            laws.extend(self._extract_from_cards(soup))

        # Strategy 4: All law-related links
        if not laws:
            laws.extend(self._extract_all_law_links(soup))

        # Follow sub-pages if the catalog has pagination or section links
        if len(laws) < 20:
            extra = self._follow_section_links(soup)
            laws.extend(extra)

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
        """Download and extract content of a specific Nuevo León law."""
        output_dir = "data/state/nuevo_leon/raw"
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
        """Extract law links from card/article patterns."""
        laws: List[Dict] = []
        for container in soup.find_all(["article", "div"], class_=True):
            classes = " ".join(container.get("class", []))
            if any(
                kw in classes
                for kw in ("card", "entry", "post", "item", "ley", "legisl")
            ):
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

    def _follow_section_links(self, soup: BeautifulSoup) -> List[Dict]:
        """Follow section links that might lead to sub-catalogs of laws."""
        laws: List[Dict] = []
        section_keywords = {"leyes", "codigos", "códigos", "reglamentos", "decretos"}

        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True).lower()
            if any(kw in text for kw in section_keywords):
                section_url = self.normalize_url(link["href"])
                # Only follow same-domain links
                if self.base_url in section_url:
                    html = self.fetch_page(section_url)
                    if html:
                        sub_soup = BeautifulSoup(html, "html.parser")
                        laws.extend(self._extract_from_tables(sub_soup))
                        laws.extend(self._extract_from_lists(sub_soup))

        return laws

    def _parse_link(self, link, parent_element=None) -> Optional[Dict]:
        """Parse a single anchor tag into a law dictionary."""
        href = link["href"].strip()

        if any(ex in href.lower() for ex in self.EXCLUDE_KEYWORDS):
            return None

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

    parser = argparse.ArgumentParser(description="Scrape Nuevo León state congress")
    parser.add_argument(
        "--dry-run", action="store_true", help="Just probe, don't download"
    )
    parser.add_argument("--limit", type=int, help="Limit number of laws")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    scraper = NuevoLeonScraper()
    catalog = scraper.scrape_catalog()

    if args.limit:
        catalog = catalog[: args.limit]

    print(f"\nFound {len(catalog)} laws")
    for law in catalog[:10]:
        print(f"  - {law['name'][:80]} [{law['category']}]")

    if not args.dry_run and catalog:
        output_path = "data/state/nuevo_leon/catalog.json"
        from pathlib import Path

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {output_path}")
