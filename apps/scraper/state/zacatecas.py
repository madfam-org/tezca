"""
Zacatecas State Congress Scraper

Scrapes legislation from the Zacatecas state congress portal.
Portal: https://congresozac.gob.mx
Target: all available legislation (0 laws currently on OJN).
Gap size: entire state missing from OJN.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote

from bs4 import BeautifulSoup

from .base import StateCongressScraper

logger = logging.getLogger(__name__)

STATE_CODE = "zacatecas"
OUTPUT_DIR = f"data/state/{STATE_CODE}"


class ZacatecasScraper(StateCongressScraper):
    """
    Scraper for the Zacatecas state congress website.

    The Zacatecas congress portal at congresozac.gob.mx hosts a
    legislation catalog under /legislacion/ with links to PDF documents.
    Since OJN has 0 Zacatecas laws, this scraper targets all available
    legislation including leyes, codigos, reglamentos, and decretos.
    """

    CATALOG_PATHS = {
        "leyes": "/legislacion/leyes/",
        "codigos": "/legislacion/codigos/",
        "reglamentos": "/legislacion/reglamentos/",
        "decretos": "/legislacion/decretos/",
    }
    ALTERNATIVE_PATHS = [
        "/legislacion/",
        "/trabajo-legislativo/legislacion/",
        "/marco-juridico/",
        "/leyes/",
        "/trabajo-legislativo/leyes/",
        "/legislacion-vigente/",
    ]

    def __init__(self) -> None:
        super().__init__(
            state="Zacatecas",
            base_url="https://congresozac.gob.mx",
        )
        logger.info("Initialized %s scraper - %s", self.state, self.base_url)

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape the Zacatecas legislation catalog.

        Iterates over each category path (leyes, codigos, reglamentos,
        decretos) with pagination. Falls back to the general legislation
        page and alternative paths if category paths fail.

        Returns:
            Deduplicated list of law dictionaries.
        """
        laws: List[Dict] = []

        # Try each category path
        for category_key, path in self.CATALOG_PATHS.items():
            url = self.normalize_url(path)
            logger.info("Scraping %s catalog: %s", category_key, url)
            category_laws = self._scrape_paginated_catalog(url, category_key)
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
                        logger.info(
                            "Found %d laws at alternative: %s",
                            len(laws),
                            alt_url,
                        )
                        # Continue checking other alternatives for completeness
                        # since this state is entirely missing

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
        Download and extract content of a specific Zacatecas law.

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

    def _scrape_paginated_catalog(
        self, start_url: str, category_key: str
    ) -> List[Dict]:
        """
        Scrape a paginated catalog section.

        Follows pagination links up to 50 pages.

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
            if next_url and page_num < 50:
                page_num += 1
                html = self.fetch_page(next_url)
            else:
                break

        return laws

    def _extract_laws_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Extract law entries from a single catalog page.

        Handles multiple page layouts: tables, content containers,
        list items, and direct file links.

        Args:
            soup: Parsed HTML of the catalog page.

        Returns:
            List of law dictionaries found on this page.
        """
        laws: List[Dict] = []

        # Strategy 1: Tables
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                for link in row.find_all("a", href=True):
                    law = self._parse_law_link(link, row)
                    if law:
                        laws.append(law)

        # Strategy 2: Content containers
        if not laws:
            content_areas = soup.find_all(
                ["article", "div", "section"],
                class_=lambda c: c
                and any(
                    kw in (c if isinstance(c, str) else " ".join(c))
                    for kw in [
                        "content",
                        "entry",
                        "post",
                        "legislacion",
                        "leyes",
                        "marco",
                    ]
                ),
            )

            search_areas = content_areas if content_areas else [soup]
            for area in search_areas:
                for li in area.find_all("li"):
                    link = li.find("a", href=True)
                    if link:
                        law = self._parse_law_link(link, li)
                        if law:
                            laws.append(law)

        # Strategy 3: All downloadable links as fallback
        if not laws:
            for link in soup.find_all("a", href=True):
                law = self._parse_law_link(link)
                if law:
                    laws.append(law)

        return laws

    def _parse_law_link(self, link, parent_element=None) -> Optional[Dict]:
        """
        Parse an anchor tag into a law dictionary.

        Handles links with descriptive text as well as links where the
        law name is encoded in the filename (common on government portals
        that use file directory listings).

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

        # Try extracting name from filename if text is missing
        if (not text or len(text) < 8) and self.is_downloadable(
            self.normalize_url(href)
        ):
            filename = unquote(href.split("/")[-1])
            name = filename.rsplit(".", 1)[0].strip()
            name = name.replace("_", " ").replace("-", " ").strip()
            if name and len(name) >= 5:
                text = name

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
            if link_text in ("siguiente", "next", ">>", ">"):
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
        else:
            return "otro"


def main() -> None:
    """Run the Zacatecas scraper from the command line."""
    parser = argparse.ArgumentParser(
        description="Scrape all legislation from the Zacatecas state congress"
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

    scraper = ZacatecasScraper()
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
