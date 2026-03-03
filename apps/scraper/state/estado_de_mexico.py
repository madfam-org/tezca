"""
Estado de Mexico State Legislation Scraper

Scrapes non-legislative instruments from the Estado de Mexico legislation portal.
Portal: https://legislacion.edomex.gob.mx
Target: reglamentos, decretos
Gap size: ~600 non-legislative laws.
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from .base import StateCongressScraper

logger = logging.getLogger(__name__)

STATE_CODE = "estado_de_mexico"
OUTPUT_DIR = f"data/state/{STATE_CODE}"


class EstadoDeMexicoScraper(StateCongressScraper):
    """
    Scraper for the Estado de Mexico legislation portal.

    Unlike most state congress websites, Estado de Mexico has a dedicated
    legislation portal at legislacion.edomex.gob.mx with a structured
    search interface. The catalog is organized by document type with
    server-side pagination.
    """

    CATALOG_PATHS = {
        "reglamentos": "/Sites/legislacion/Reglamentos",
        "decretos": "/Sites/legislacion/Decretos",
        "acuerdos": "/Sites/legislacion/Acuerdos",
    }
    ALTERNATIVE_PATHS = [
        "/Sites/legislacion/",
        "/legislacion/",
        "/",
    ]
    SEARCH_PATH = "/Sites/legislacion/busqueda"

    def __init__(self) -> None:
        super().__init__(
            state="Estado de Mexico",
            base_url="https://legislacion.edomex.gob.mx",
        )
        logger.info("Initialized %s scraper - %s", self.state, self.base_url)

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape the Estado de Mexico non-legislative catalog.

        Iterates over each document type path (reglamentos, decretos,
        acuerdos), handling server-side pagination. Falls back to the
        general legislation portal if category paths fail.

        Returns:
            Deduplicated list of law dictionaries.
        """
        laws: List[Dict] = []

        # Try each category path with pagination
        for category_key, path in self.CATALOG_PATHS.items():
            url = self.normalize_url(path)
            logger.info("Scraping %s catalog: %s", category_key, url)
            category_laws = self._scrape_paginated_section(url, category_key)
            laws.extend(category_laws)

        # Fallback to alternative paths
        if not laws:
            logger.warning("Category paths yielded no results, trying alternatives")
            for alt_path in self.ALTERNATIVE_PATHS:
                alt_url = self.normalize_url(alt_path)
                html = self.fetch_page(alt_url)
                if html:
                    soup = BeautifulSoup(html, "html.parser")
                    page_laws = self._extract_laws_from_page(soup)
                    laws.extend(page_laws)
                    if laws:
                        logger.info("Found %d laws at %s", len(laws), alt_url)
                        break

        # Deduplicate by URL
        seen_urls: set = set()
        unique_laws: List[Dict] = []
        for law in laws:
            if law["url"] not in seen_urls:
                seen_urls.add(law["url"])
                unique_laws.append(law)

        logger.info("Scraped %d unique laws from %s", len(unique_laws), self.state)
        return unique_laws

    def scrape_law_content(self, url: str) -> Optional[Dict]:
        """
        Download and extract content of a specific Estado de Mexico law.

        Args:
            url: URL of the law document.

        Returns:
            Dict with url, file_type, file_path, size_bytes, or None on failure.
        """
        output_dir = f"{OUTPUT_DIR}/raw"
        return self.download_file(url, output_dir)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _scrape_paginated_section(
        self, start_url: str, category_key: str
    ) -> List[Dict]:
        """
        Scrape a paginated catalog section.

        The edomex portal uses server-side pagination. This method
        follows pagination links up to 100 pages.

        Args:
            start_url: URL of the first catalog page.
            category_key: Category label for logging context.

        Returns:
            List of law dictionaries from all pages.
        """
        laws: List[Dict] = []
        html = self.fetch_page(start_url)
        page_num = 1

        while html:
            soup = BeautifulSoup(html, "html.parser")
            page_laws = self._extract_laws_from_page(soup)
            laws.extend(page_laws)
            logger.debug(
                "%s page %d: found %d laws", category_key, page_num, len(page_laws)
            )

            next_url = self._find_next_page(soup)
            if next_url and page_num < 100:
                page_num += 1
                html = self.fetch_page(next_url)
            else:
                break

        return laws

    def _extract_laws_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Extract law entries from a single catalog page.

        The edomex portal typically uses structured tables or card-style
        layouts with PDF download links.

        Args:
            soup: Parsed HTML of the catalog page.

        Returns:
            List of law dictionaries found on this page.
        """
        laws: List[Dict] = []

        # Strategy 1: Table rows with document links
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                for link in row.find_all("a", href=True):
                    law = self._parse_law_link(link, row)
                    if law:
                        laws.append(law)

        # Strategy 2: Content div patterns (card/list layouts)
        if not laws:
            content_areas = soup.find_all(
                ["div", "article", "section"],
                class_=lambda c: c
                and any(
                    kw in (c if isinstance(c, str) else " ".join(c))
                    for kw in [
                        "content",
                        "resultado",
                        "listado",
                        "documento",
                        "legislacion",
                    ]
                ),
            )

            search_areas = content_areas if content_areas else [soup]
            for area in search_areas:
                for link in area.find_all("a", href=True):
                    law = self._parse_law_link(link)
                    if law:
                        laws.append(law)

        # Strategy 3: List items
        if not laws:
            for li in soup.find_all("li"):
                link = li.find("a", href=True)
                if link:
                    law = self._parse_law_link(link, li)
                    if law:
                        laws.append(law)

        return laws

    def _parse_law_link(self, link, parent_element=None) -> Optional[Dict]:
        """
        Parse an anchor tag into a law dictionary.

        Args:
            link: BeautifulSoup anchor tag.
            parent_element: Optional parent element for text context.

        Returns:
            Law dict or None if the link is not a valid law reference.
        """
        href = link["href"].strip()
        text = link.get_text(strip=True)

        if parent_element and (not text or len(text) < 10):
            text = parent_element.get_text(strip=True)

        if not text or len(text) < 8:
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

    def _find_next_page(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Find the URL of the next pagination page.

        Handles the edomex portal's pagination which may use query
        parameters (?pagina=N) or standard WordPress patterns.

        Args:
            soup: Parsed HTML of the current page.

        Returns:
            Absolute URL of the next page, or None.
        """
        # Standard next link
        next_link = soup.find("a", class_="next")
        if next_link and next_link.get("href"):
            return self.normalize_url(next_link["href"])

        # "Siguiente" text
        for link in soup.find_all("a", href=True):
            link_text = link.get_text(strip=True).lower()
            if link_text in ("siguiente", "next", ">>", ">", "sig."):
                return self.normalize_url(link["href"])

        # aria-label
        next_link = soup.find(
            "a",
            attrs={
                "aria-label": lambda v: v
                and ("next" in v.lower() or "siguiente" in v.lower())
            },
        )
        if next_link and next_link.get("href"):
            return self.normalize_url(next_link["href"])

        # Pagination container with numbered links
        pager = soup.find(
            ["div", "nav", "ul"],
            class_=lambda c: c
            and any(
                kw in (c if isinstance(c, str) else " ".join(c))
                for kw in ["pager", "pagination", "paginacion"]
            ),
        )
        if pager:
            # Find the "active" page and get the next sibling link
            active = pager.find(class_=lambda c: c and "active" in str(c))
            if active:
                next_sibling = active.find_next_sibling("a", href=True)
                if not next_sibling:
                    parent = active.parent
                    if parent:
                        next_sibling = parent.find_next_sibling()
                        if next_sibling:
                            next_sibling = next_sibling.find("a", href=True)
                if next_sibling and next_sibling.get("href"):
                    return self.normalize_url(next_sibling["href"])

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
            "lineamiento",
            "bando",
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
        elif "acuerdo" in text_lower:
            return "acuerdo"
        elif "bando" in text_lower:
            return "bando"
        else:
            return "otro"


def main() -> None:
    """Run the Estado de Mexico scraper from the command line."""
    parser = argparse.ArgumentParser(
        description="Scrape non-legislative laws from the Estado de Mexico portal"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of laws to scrape (0 = unlimited)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results without saving to disk",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    scraper = EstadoDeMexicoScraper()
    laws = scraper.scrape_catalog()

    if args.limit > 0:
        laws = laws[: args.limit]

    logger.info("Total laws collected: %d", len(laws))

    if args.dry_run:
        for law in laws:
            print(f"  {law['category']:20s} | {law['name'][:80]}")
        print(f"\nTotal: {len(laws)} laws (dry run, not saved)")
        return

    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / f"scraped_{STATE_CODE}_non_leg.json"
    output_file.write_text(json.dumps(laws, ensure_ascii=False, indent=2))
    logger.info("Saved %d laws to %s", len(laws), output_file)


if __name__ == "__main__":
    main()
