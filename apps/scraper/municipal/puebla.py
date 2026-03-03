"""
Puebla Municipal Scraper

Scrapes reglamentos municipales from Puebla's Orden Juridico Poblano portal
(ojp.puebla.gob.mx) and the municipal transparency portal (pueblacapital.gob.mx).

The OJP portal is the authoritative source for Puebla state and municipal legislation,
hosting PDF documents organized by legal category.
"""

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import MunicipalScraper
from .config import get_config

logger = logging.getLogger(__name__)

# Puebla-specific regulatory keywords (includes municipal-level terms)
PUEBLA_KEYWORDS = re.compile(
    r"reglamento|c[oó]digo|bando|decreto|normativ|acuerdo|lineamiento|ordenanza"
    r"|disposici[oó]n|manual\s+de|ley\s+de\s+ingresos",
    re.IGNORECASE,
)

# Exclude links that are navigation or non-regulatory
EXCLUDE_PATTERNS = re.compile(
    r"inicio|contacto|aviso\s+de\s+privacidad|mapa\s+del\s+sitio|rss|facebook|twitter"
    r"|instagram|youtube|gobierno\s+federal|gobierno\s+del\s+estado",
    re.IGNORECASE,
)


class PueblaScraper(MunicipalScraper):
    """
    Scraper for Puebla municipal regulations.

    Strategy:
    1. Attempt the OJP portal (ojp.puebla.gob.mx) for municipal regulations
    2. Fall back to pueblacapital.gob.mx transparency section
    3. Follow subpages one level deep to discover PDF links
    4. Deduplicate results by URL
    """

    # Portal paths to try, in priority order
    CATALOG_PATHS = [
        "/transparencia/normatividad",
        "/transparencia/i-marco-normativo",
        "/normatividad",
        "/reglamentos",
        "/marco-juridico",
        "/transparencia",
    ]

    # OJP portal for municipal reglamentos
    OJP_BASE = "https://ojp.puebla.gob.mx"
    OJP_PATHS = [
        "/index.php/leyes-702/reglamentos-702",
        "/index.php/leyes-702",
    ]

    def __init__(self):
        config = get_config("puebla")
        super().__init__(config=config)
        logger.info(f"Initialized {self.municipality} scraper - {self.base_url}")

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape Puebla's regulations catalog from multiple sources.

        Returns:
            List of law dictionaries with title, url, law_type, municipality, state.
        """
        laws: List[Dict] = []
        seen_urls: Set[str] = set()

        # Source 1: OJP portal (authoritative state legal portal)
        ojp_laws = self._scrape_ojp_portal(seen_urls)
        laws.extend(ojp_laws)

        # Source 2: Municipal transparency portal
        muni_laws = self._scrape_municipal_portal(seen_urls)
        laws.extend(muni_laws)

        logger.info(
            f"Total {self.municipality} regulations discovered: {len(laws)} "
            f"(OJP: {len(ojp_laws)}, Municipal: {len(muni_laws)})"
        )
        return laws

    def _scrape_ojp_portal(self, seen_urls: Set[str]) -> List[Dict]:
        """Scrape the Orden Juridico Poblano portal for municipal reglamentos."""
        laws: List[Dict] = []

        for path in self.OJP_PATHS:
            url = self.OJP_BASE + path
            logger.info(f"[puebla] Trying OJP portal: {url}")
            html = self.fetch_page(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            page_laws = self._extract_laws_from_page(soup, url, seen_urls)
            laws.extend(page_laws)

            # Follow subpages for PDF discovery
            subpage_laws = self._follow_subpages(soup, url, seen_urls)
            laws.extend(subpage_laws)

            if laws:
                logger.info(f"[puebla] Found {len(laws)} laws from OJP portal")
                break

        return laws

    def _scrape_municipal_portal(self, seen_urls: Set[str]) -> List[Dict]:
        """Scrape the municipal government transparency portal."""
        laws: List[Dict] = []

        for path in self.CATALOG_PATHS:
            catalog_url = urljoin(self.base_url, path)
            logger.info(f"[puebla] Trying municipal portal: {catalog_url}")
            html = self.fetch_page(catalog_url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            page_laws = self._extract_laws_from_page(soup, catalog_url, seen_urls)
            laws.extend(page_laws)

            # Follow subpages one level deep
            subpage_laws = self._follow_subpages(soup, catalog_url, seen_urls)
            laws.extend(subpage_laws)

            if laws:
                logger.info(
                    f"[puebla] Found {len(laws)} laws from municipal portal at {path}"
                )
                break

        return laws

    def _extract_laws_from_page(
        self, soup: BeautifulSoup, page_url: str, seen_urls: Set[str]
    ) -> List[Dict]:
        """Extract regulatory links from a parsed HTML page."""
        laws: List[Dict] = []

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            text = link.get_text(separator=" ", strip=True)

            # Skip short/empty links or navigation
            if not text or len(text) < 10:
                continue
            if EXCLUDE_PATTERNS.search(text):
                continue

            if not self._is_regulation_link(text, href):
                continue

            absolute_url = self.normalize_url(href, base=page_url)

            # Validate scheme
            parsed = urlparse(absolute_url)
            if parsed.scheme not in ("http", "https"):
                continue

            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)

            if self.is_pdf(absolute_url) or self._is_doc(absolute_url):
                law = self._build_law_dict(text, absolute_url)
                if self.validate_law_data(law):
                    laws.append(law)
                    logger.debug(f"[puebla] Found: {text}")

        return laws

    def _follow_subpages(
        self, soup: BeautifulSoup, page_url: str, seen_urls: Set[str]
    ) -> List[Dict]:
        """Follow HTML links one level deep to discover PDFs."""
        laws: List[Dict] = []
        subpage_candidates: List[tuple] = []

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            text = link.get_text(separator=" ", strip=True)

            if not text or len(text) < 10:
                continue
            if EXCLUDE_PATTERNS.search(text):
                continue
            if not PUEBLA_KEYWORDS.search(text) and not PUEBLA_KEYWORDS.search(href):
                continue

            absolute_url = self.normalize_url(href, base=page_url)
            parsed = urlparse(absolute_url)
            if parsed.scheme not in ("http", "https"):
                continue
            if absolute_url in seen_urls:
                continue
            if self.is_pdf(absolute_url) or self._is_doc(absolute_url):
                continue  # Already handled as direct links

            subpage_candidates.append((absolute_url, text))

        logger.info(f"[puebla] Following {len(subpage_candidates)} subpages")
        for sub_url, parent_text in subpage_candidates:
            seen_urls.add(sub_url)
            html = self.fetch_page(sub_url)
            if not html:
                continue

            sub_soup = BeautifulSoup(html, "html.parser")
            for link in sub_soup.find_all("a", href=True):
                href = link["href"].strip()
                text = link.get_text(separator=" ", strip=True)
                abs_url = self.normalize_url(href, base=sub_url)

                parsed = urlparse(abs_url)
                if parsed.scheme not in ("http", "https"):
                    continue
                if abs_url in seen_urls:
                    continue

                if self.is_pdf(abs_url) or self._is_doc(abs_url):
                    seen_urls.add(abs_url)
                    title = text if text and len(text) >= 10 else parent_text
                    law = self._build_law_dict(title, abs_url)
                    if self.validate_law_data(law):
                        laws.append(law)

        return laws

    def _is_regulation_link(self, text: str, href: str) -> bool:
        """Check if a link is a regulatory document."""
        if PUEBLA_KEYWORDS.search(text):
            return True
        if PUEBLA_KEYWORDS.search(href):
            return True
        # Also match PDF/DOC links on regulatory pages
        if self.is_pdf(href) or self._is_doc(href):
            return True
        return False

    def _is_doc(self, url: str) -> bool:
        """Check if URL points to a Word document."""
        path = urlparse(url.lower()).path
        return path.endswith(".doc") or path.endswith(".docx")

    def _build_law_dict(self, name: str, url: str) -> Dict:
        """Build a standardized law dictionary."""
        name = re.sub(r"\s+", " ", name).strip()

        return {
            "title": name,
            "url": url,
            "law_type": self._classify_law_type(name),
            "municipality": self.municipality,
            "state": self.state,
            "tier": "municipal",
            "category": self.extract_category(name),
            "status": "Discovered",
        }

    def _classify_law_type(self, name: str) -> str:
        """Classify the law type from its title."""
        name_lower = name.lower()
        if "bando" in name_lower:
            return "bando"
        elif "reglamento" in name_lower:
            return "reglamento"
        elif re.search(r"c[oó]digo", name_lower):
            return "codigo"
        elif "decreto" in name_lower:
            return "decreto"
        elif "lineamiento" in name_lower:
            return "lineamiento"
        elif "acuerdo" in name_lower:
            return "acuerdo"
        elif "manual" in name_lower:
            return "manual"
        elif "ley de ingresos" in name_lower:
            return "ley_de_ingresos"
        else:
            return "otro"

    def scrape_law_content(self, url: str, output_dir: str = None) -> Optional[Dict]:
        """Download and extract content of a specific law."""
        if output_dir is None:
            output_dir = "data/municipal/puebla/raw"
        return self.download_law_content(url, output_dir)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Scrape municipal regulations from Puebla"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="data/municipal/puebla",
        help="Output directory for JSON results (default: data/municipal/puebla)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of results displayed (0 = all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only discover laws, do not download content",
    )
    args = parser.parse_args()

    scraper = PueblaScraper()
    results = scraper.scrape_catalog()

    # Save results to JSON
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "catalog.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"City: {scraper.municipality} ({scraper.state})")
    print(f"Laws discovered: {len(results)}")
    print(f"Results saved to: {output_file}")
    print(f"{'=' * 60}")

    display = results[: args.limit] if args.limit > 0 else results
    for i, law in enumerate(display, 1):
        print(f"\n[{i}] {law['title']}")
        print(f"    URL: {law['url']}")
        print(f"    Type: {law['law_type']}")
        print(f"    Category: {law['category']}")
