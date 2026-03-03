"""
Ciudad de Mexico (CDMX) Legislation Scraper

Scrapes legislation from multiple CDMX sources since CDMX has 0 laws
on OJN and requires alternate portals.

Primary sources:
  1. Congreso CDMX: https://congresocdmx.gob.mx
  2. Consejeria Juridica: https://data.consejeria.cdmx.gob.mx

Target: all available legislation (leyes, reglamentos, decretos, etc.)
Gap size: 0 laws on OJN -- CDMX is entirely missing.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .base import StateCongressScraper

logger = logging.getLogger(__name__)

STATE_CODE = "cdmx"
OUTPUT_DIR = f"data/state/{STATE_CODE}"


class CDMXScraper(StateCongressScraper):
    """
    Scraper for Ciudad de Mexico legislation.

    CDMX is unique in that it has no laws in OJN at all. This scraper
    targets two complementary sources:

    1. The Congreso CDMX portal for legislative instruments.
    2. The Consejeria Juridica data portal for the broader regulatory
       framework (reglamentos, acuerdos, circulares, etc.).

    The Consejeria portal at data.consejeria.cdmx.gob.mx is the most
    comprehensive source, providing a structured legislation index with
    PDF downloads organized by document type.
    """

    # Consejeria Juridica is the primary source (most comprehensive)
    CONSEJERIA_BASE = "https://data.consejeria.cdmx.gob.mx"
    CONSEJERIA_PATHS = {
        "leyes": "/portal_old/uploads/gacetas/leyes/",
        "codigos": "/portal_old/uploads/gacetas/codigos/",
        "reglamentos": "/portal_old/uploads/gacetas/reglamentos/",
        "decretos": "/portal_old/uploads/gacetas/decretos/",
        "acuerdos": "/portal_old/uploads/gacetas/acuerdos/",
    }
    CONSEJERIA_CATALOG_PATHS = [
        "/index.php/leyes",
        "/index.php/codigos",
        "/index.php/reglamentos",
        "/index.php/decretos",
        "/leyes-y-reglamentos/",
        "/marco-juridico/",
    ]

    # Congreso CDMX as secondary source
    CONGRESO_BASE = "https://congresocdmx.gob.mx"
    CONGRESO_PATHS = [
        "/archivos/legislacion/",
        "/trabajo-legislativo/legislacion/",
        "/legislacion/",
        "/marco-juridico/",
    ]

    def __init__(self) -> None:
        super().__init__(
            state="Ciudad de Mexico",
            base_url="https://data.consejeria.cdmx.gob.mx",
        )
        logger.info("Initialized %s scraper - %s", self.state, self.base_url)

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape CDMX legislation from both Consejeria and Congreso portals.

        Scrapes the Consejeria Juridica portal first (more comprehensive),
        then supplements with the Congreso CDMX portal. Deduplicates
        across both sources.

        Returns:
            Deduplicated list of law dictionaries.
        """
        laws: List[Dict] = []

        # Source 1: Consejeria Juridica (primary, most comprehensive)
        logger.info("Scraping Consejeria Juridica portal")
        consejeria_laws = self._scrape_consejeria()
        laws.extend(consejeria_laws)
        logger.info("Consejeria Juridica: found %d laws", len(consejeria_laws))

        # Source 2: Congreso CDMX (supplementary)
        logger.info("Scraping Congreso CDMX portal")
        congreso_laws = self._scrape_congreso()
        laws.extend(congreso_laws)
        logger.info("Congreso CDMX: found %d laws", len(congreso_laws))

        # Deduplicate by URL
        seen_urls: set = set()
        unique_laws: List[Dict] = []
        for law in laws:
            if law["url"] not in seen_urls:
                seen_urls.add(law["url"])
                unique_laws.append(law)

        logger.info(
            "Scraped %d unique laws from %s (from %d total)",
            len(unique_laws),
            self.state,
            len(laws),
        )
        return unique_laws

    def scrape_law_content(self, url: str) -> Optional[Dict]:
        """
        Download and extract content of a specific CDMX law.

        Args:
            url: URL of the law document.

        Returns:
            Dict with url, file_type, file_path, size_bytes, or None on failure.
        """
        output_dir = f"{OUTPUT_DIR}/raw"
        return self.download_file(url, output_dir)

    # ------------------------------------------------------------------
    # Consejeria Juridica scraping
    # ------------------------------------------------------------------

    def _scrape_consejeria(self) -> List[Dict]:
        """
        Scrape the Consejeria Juridica data portal.

        Tries category-specific catalog pages first, then falls back
        to direct file directory listings.

        Returns:
            List of law dictionaries from the Consejeria portal.
        """
        laws: List[Dict] = []

        # Try structured catalog pages
        for path in self.CONSEJERIA_CATALOG_PATHS:
            url = f"{self.CONSEJERIA_BASE}{path}"
            html = self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, "html.parser")
                page_laws = self._extract_laws_from_page(soup, self.CONSEJERIA_BASE)
                laws.extend(page_laws)
                logger.debug("Consejeria %s: found %d laws", path, len(page_laws))

        # Try direct file directory listings
        if len(laws) < 20:
            for category_key, path in self.CONSEJERIA_PATHS.items():
                url = f"{self.CONSEJERIA_BASE}{path}"
                html = self.fetch_page(url)
                if html:
                    soup = BeautifulSoup(html, "html.parser")
                    dir_laws = self._extract_directory_listing(soup, url, category_key)
                    laws.extend(dir_laws)

        return laws

    def _extract_directory_listing(
        self, soup: BeautifulSoup, base_url: str, category_key: str
    ) -> List[Dict]:
        """
        Extract laws from an Apache/nginx-style directory listing.

        Some government portals serve raw file directories with PDF links.

        Args:
            soup: Parsed HTML of the directory listing.
            base_url: Base URL for resolving relative paths.
            category_key: Category label for classification.

        Returns:
            List of law dictionaries.
        """
        from urllib.parse import unquote

        laws: List[Dict] = []

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            abs_url = self.normalize_url(href, base=base_url)

            if not self.is_downloadable(abs_url):
                continue

            # Extract name from filename
            filename = unquote(href.split("/")[-1])
            name = filename.rsplit(".", 1)[0].strip()
            name = name.replace("_", " ").replace("-", " ").strip()

            if not name or len(name) < 5:
                continue

            law = {
                "name": name[:500],
                "url": abs_url,
                "state": self.state,
                "tier": "state",
                "category": (
                    self.extract_category(name)
                    if self._is_law_keyword(name)
                    else category_key.rstrip("s").capitalize()
                ),
                "law_type": self._infer_law_type(name),
            }

            if self.validate_law_data(law):
                laws.append(law)

        return laws

    # ------------------------------------------------------------------
    # Congreso CDMX scraping
    # ------------------------------------------------------------------

    def _scrape_congreso(self) -> List[Dict]:
        """
        Scrape the Congreso CDMX portal.

        Tries multiple known paths on the congress website.

        Returns:
            List of law dictionaries from the Congreso portal.
        """
        laws: List[Dict] = []

        for path in self.CONGRESO_PATHS:
            url = f"{self.CONGRESO_BASE}{path}"
            html = self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, "html.parser")
                page_laws = self._extract_laws_from_page(soup, self.CONGRESO_BASE)
                laws.extend(page_laws)
                if page_laws:
                    logger.info("Congreso %s: found %d laws", path, len(page_laws))

                    # Check for pagination on this page
                    more_laws = self._follow_pagination(soup, self.CONGRESO_BASE)
                    laws.extend(more_laws)

        return laws

    def _follow_pagination(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """
        Follow pagination links from a catalog page.

        Args:
            soup: Parsed HTML of the current page.
            base_url: Base URL for resolving relative paths.

        Returns:
            List of law dictionaries from subsequent pages.
        """
        laws: List[Dict] = []
        page_num = 1

        while page_num < 50:
            next_url = self._find_next_page(soup)
            if not next_url:
                break

            page_num += 1
            html = self.fetch_page(next_url)
            if not html:
                break

            soup = BeautifulSoup(html, "html.parser")
            page_laws = self._extract_laws_from_page(soup, base_url)
            laws.extend(page_laws)
            logger.debug("Pagination page %d: found %d laws", page_num, len(page_laws))

        return laws

    # ------------------------------------------------------------------
    # Shared extraction helpers
    # ------------------------------------------------------------------

    def _extract_laws_from_page(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """
        Extract law entries from a single catalog page.

        Args:
            soup: Parsed HTML of the catalog page.
            base_url: Base URL for resolving relative paths.

        Returns:
            List of law dictionaries found on this page.
        """
        laws: List[Dict] = []

        # Strategy 1: Tables
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                for link in row.find_all("a", href=True):
                    law = self._parse_law_link(link, row, base_url)
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
                        "legislacion",
                        "resultado",
                        "listado",
                    ]
                ),
            )

            search_areas = content_areas if content_areas else [soup]
            for area in search_areas:
                for link in area.find_all("a", href=True):
                    law = self._parse_law_link(link, base_url=base_url)
                    if law:
                        laws.append(law)

        # Strategy 3: List items
        if not laws:
            for li in soup.find_all("li"):
                link = li.find("a", href=True)
                if link:
                    law = self._parse_law_link(link, li, base_url)
                    if law:
                        laws.append(law)

        return laws

    def _parse_law_link(
        self, link, parent_element=None, base_url: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Parse an anchor tag into a law dictionary.

        Args:
            link: BeautifulSoup anchor tag.
            parent_element: Optional parent element for text context.
            base_url: Base URL for resolving relative paths.

        Returns:
            Law dict or None if the link is not a valid law reference.
        """
        href = link["href"].strip()
        text = link.get_text(strip=True)

        if parent_element and (not text or len(text) < 10):
            text = parent_element.get_text(strip=True)

        if not text or len(text) < 8:
            return None

        absolute_url = self.normalize_url(href, base=base_url)

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
        next_link = soup.find("a", class_="next")
        if next_link and next_link.get("href"):
            return self.normalize_url(next_link["href"])

        for link in soup.find_all("a", href=True):
            link_text = link.get_text(strip=True).lower()
            if link_text in ("siguiente", "next", ">>", ">"):
                return self.normalize_url(link["href"])

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
            "circular",
            "estatuto",
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
        elif "circular" in text_lower:
            return "circular"
        elif "estatuto" in text_lower:
            return "estatuto"
        else:
            return "otro"


def main() -> None:
    """Run the CDMX scraper from the command line."""
    parser = argparse.ArgumentParser(
        description="Scrape legislation from CDMX portals (Consejeria + Congreso)"
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
    parser.add_argument(
        "--source",
        choices=["all", "consejeria", "congreso"],
        default="all",
        help="Which source portal to scrape (default: all)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    scraper = CDMXScraper()

    if args.source == "consejeria":
        laws = scraper._scrape_consejeria()
    elif args.source == "congreso":
        laws = scraper._scrape_congreso()
    else:
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
