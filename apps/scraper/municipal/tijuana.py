"""
Tijuana Municipal Scraper

Scrapes bandos and reglamentos municipales from Tijuana's municipal portal
(tijuana.gob.mx) and its marco juridico / transparencia sections.

Tijuana's portal typically organizes regulations under transparency obligations
(Art. 70-83 of the Ley General de Transparencia), with PDF documents linked
from categorized listing pages.
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

# Tijuana-specific regulatory keywords (includes border-city specific terms)
TIJUANA_KEYWORDS = re.compile(
    r"reglamento|c[oó]digo|bando|decreto|normativ|acuerdo|lineamiento"
    r"|disposici[oó]n|circular|manual\s+de|ley\s+de\s+ingresos|marco\s+jur[ií]dico",
    re.IGNORECASE,
)

# Exclude navigation and non-regulatory links
EXCLUDE_PATTERNS = re.compile(
    r"inicio|contacto|aviso\s+de\s+privacidad|mapa\s+del\s+sitio|rss"
    r"|facebook|twitter|instagram|youtube|login|registro|english",
    re.IGNORECASE,
)


class TijuanaScraper(MunicipalScraper):
    """
    Scraper for Tijuana municipal regulations.

    Strategy:
    1. Try the marco juridico section of the portal
    2. Fall back to transparency/normatividad paths
    3. Follow subpages one level deep for PDF discovery
    4. Also check for SIPOT (transparency platform) integration
    5. Deduplicate by URL
    """

    # Catalog paths to try, in priority order
    CATALOG_PATHS = [
        "/Transparencia/MarcoJuridico",
        "/transparencia/marco-juridico",
        "/marco-juridico",
        "/transparencia/normatividad",
        "/transparencia/i-marco-normativo",
        "/Dependencias/Sindicatura/Reglamentos",
        "/reglamentos",
        "/normatividad",
        "/transparencia",
    ]

    def __init__(self):
        config = get_config("tijuana")
        super().__init__(config=config)
        logger.info(f"Initialized {self.municipality} scraper - {self.base_url}")

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape Tijuana's regulations catalog from the municipal portal.

        Returns:
            List of law dictionaries with title, url, law_type, municipality, state.
        """
        laws: List[Dict] = []
        seen_urls: Set[str] = set()

        # Try each catalog path until we find results
        for path in self.CATALOG_PATHS:
            catalog_url = urljoin(self.base_url, path)
            logger.info(f"[tijuana] Trying catalog: {catalog_url}")

            html = self.fetch_page(catalog_url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")

            # Direct PDF/document links
            page_laws = self._extract_laws_from_page(soup, catalog_url, seen_urls)
            laws.extend(page_laws)

            # Follow subpages one level deep
            subpage_laws = self._follow_subpages(soup, catalog_url, seen_urls)
            laws.extend(subpage_laws)

            if laws:
                logger.info(f"[tijuana] Found {len(laws)} laws from catalog at {path}")
                break

        # If first pass found nothing, try a broader search on the main transparency page
        if not laws:
            laws = self._broad_transparency_search(seen_urls)

        logger.info(f"[tijuana] Total regulations discovered: {len(laws)}")
        return laws

    def _extract_laws_from_page(
        self, soup: BeautifulSoup, page_url: str, seen_urls: Set[str]
    ) -> List[Dict]:
        """Extract regulatory links from a parsed HTML page."""
        laws: List[Dict] = []

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            text = link.get_text(separator=" ", strip=True)

            # Skip short/empty or navigation links
            if not text or len(text) < 8:
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
                    logger.debug(f"[tijuana] Found: {text}")

        return laws

    def _follow_subpages(
        self, soup: BeautifulSoup, page_url: str, seen_urls: Set[str]
    ) -> List[Dict]:
        """Follow HTML links one level deep to discover PDF documents."""
        laws: List[Dict] = []
        subpage_candidates: List[tuple] = []

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            text = link.get_text(separator=" ", strip=True)

            if not text or len(text) < 8:
                continue
            if EXCLUDE_PATTERNS.search(text):
                continue
            if not TIJUANA_KEYWORDS.search(text) and not TIJUANA_KEYWORDS.search(href):
                continue

            absolute_url = self.normalize_url(href, base=page_url)
            parsed = urlparse(absolute_url)
            if parsed.scheme not in ("http", "https"):
                continue
            if absolute_url in seen_urls:
                continue
            if self.is_pdf(absolute_url) or self._is_doc(absolute_url):
                continue  # Already handled as direct links

            # Only follow links on the same domain
            if parsed.netloc and parsed.netloc != urlparse(self.base_url).netloc:
                continue

            subpage_candidates.append((absolute_url, text))

        logger.info(f"[tijuana] Following {len(subpage_candidates)} subpages")
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
                    title = text if text and len(text) >= 8 else parent_text
                    law = self._build_law_dict(title, abs_url)
                    if self.validate_law_data(law):
                        laws.append(law)

        return laws

    def _broad_transparency_search(self, seen_urls: Set[str]) -> List[Dict]:
        """
        Broader search on the main transparency page.

        Some Tijuana portals use iframe-based SIPOT integration or
        JavaScript-rendered tables. This attempts a direct crawl.
        """
        laws: List[Dict] = []
        transparency_url = urljoin(self.base_url, "/transparencia")

        logger.info(f"[tijuana] Broad search on {transparency_url}")
        html = self.fetch_page(transparency_url)
        if not html:
            return laws

        soup = BeautifulSoup(html, "html.parser")

        # Look for all PDF links regardless of keyword
        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            text = link.get_text(separator=" ", strip=True)
            absolute_url = self.normalize_url(href, base=transparency_url)

            parsed = urlparse(absolute_url)
            if parsed.scheme not in ("http", "https"):
                continue
            if absolute_url in seen_urls:
                continue

            if self.is_pdf(absolute_url):
                seen_urls.add(absolute_url)
                # For broad search, only include if title looks regulatory
                title = (
                    text
                    if text and len(text) >= 8
                    else self._title_from_url(absolute_url)
                )
                if TIJUANA_KEYWORDS.search(title) or TIJUANA_KEYWORDS.search(
                    absolute_url
                ):
                    law = self._build_law_dict(title, absolute_url)
                    if self.validate_law_data(law):
                        laws.append(law)

        return laws

    def _is_regulation_link(self, text: str, href: str) -> bool:
        """Check if a link is a regulatory document."""
        if TIJUANA_KEYWORDS.search(text):
            return True
        if TIJUANA_KEYWORDS.search(href):
            return True
        if self.is_pdf(href) or self._is_doc(href):
            # PDF on a normatividad page is likely regulatory
            return True
        return False

    def _is_doc(self, url: str) -> bool:
        """Check if URL points to a Word document."""
        path = urlparse(url.lower()).path
        return path.endswith(".doc") or path.endswith(".docx")

    def _title_from_url(self, url: str) -> str:
        """Extract a human-readable title from a URL path."""
        from os.path import basename, splitext
        from urllib.parse import unquote

        filename = basename(unquote(urlparse(url).path))
        name_body = splitext(filename)[0]
        return name_body.replace("_", " ").replace("-", " ")

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
        elif "circular" in name_lower:
            return "circular"
        elif "manual" in name_lower:
            return "manual"
        elif "ley de ingresos" in name_lower:
            return "ley_de_ingresos"
        else:
            return "otro"

    def scrape_law_content(self, url: str, output_dir: str = None) -> Optional[Dict]:
        """Download and extract content of a specific law."""
        if output_dir is None:
            output_dir = "data/municipal/tijuana/raw"
        return self.download_law_content(url, output_dir)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Scrape municipal regulations from Tijuana"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="data/municipal/tijuana",
        help="Output directory for JSON results (default: data/municipal/tijuana)",
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

    scraper = TijuanaScraper()
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
