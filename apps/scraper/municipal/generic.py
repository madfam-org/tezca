"""
Generic Municipal Scraper

A configuration-driven scraper that works for any municipality in config.py.
Fetches the catalog page, extracts regulatory links by keyword matching,
follows HTML links one level deep to find PDFs, and returns standard law dicts.
"""

import argparse
import logging
import re
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import MunicipalScraper
from .config import MUNICIPALITY_CONFIGS, get_config

logger = logging.getLogger(__name__)

# Keywords that indicate a regulatory document
REGULATORY_KEYWORDS = re.compile(
    r"reglamento|código|codigo|ley|bando|decreto|normativ|acuerdo|lineamiento",
    re.IGNORECASE,
)


class GenericMunicipalScraper(MunicipalScraper):
    """
    Generic scraper that works for any configured municipality.

    Uses broad keyword matching on link text and URLs to discover
    regulatory documents. Follows HTML links one level deep to find
    PDF documents that may not be directly linked from the catalog page.
    """

    def __init__(self, city_key: str):
        """
        Initialize the generic scraper for a specific city.

        Args:
            city_key: Municipality identifier from config.py (e.g., 'merida', 'juarez')

        Raises:
            ValueError: If city_key is not in MUNICIPALITY_CONFIGS
        """
        config = get_config(city_key)
        super().__init__(config=config)
        self.city_key = city_key
        self.tier = config.get("tier", 2)

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape the catalog page and return a list of discovered laws.

        Strategy:
        1. Fetch the catalog page at base_url + catalog_path
        2. Extract all links whose text or URL matches regulatory keywords
        3. For PDF links, add them directly
        4. For HTML links, follow one level deep to find PDF links
        5. Deduplicate by URL

        Returns:
            List of law dictionaries with name, url, municipality, state, tier, category
        """
        catalog_path = self.selectors.get("catalog_path", "")
        catalog_url = urljoin(self.base_url, catalog_path)

        logger.info(f"[{self.city_key}] Fetching catalog: {catalog_url}")
        html = self.fetch_page(catalog_url)
        if not html:
            logger.error(f"[{self.city_key}] Failed to fetch catalog page")
            return []

        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=True)

        laws: List[Dict] = []
        seen_urls: Set[str] = set()
        subpage_urls: List[tuple] = []  # (url, link_text) pairs to follow

        for link in links:
            href = link["href"].strip()
            text = link.get_text(separator=" ", strip=True)

            if not self._is_regulatory_link(href, text):
                continue

            absolute_url = self.normalize_url(href, catalog_url)

            # Skip non-http links (mailto, javascript, etc.)
            parsed = urlparse(absolute_url)
            if parsed.scheme not in ("http", "https"):
                continue

            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)

            if self.is_pdf(absolute_url):
                law = self._build_law_dict(
                    text or self._title_from_url(absolute_url), absolute_url
                )
                if self.validate_law_data(law):
                    laws.append(law)
            else:
                # Queue HTML page for one-level-deep crawl
                subpage_urls.append((absolute_url, text))

        # Follow HTML links one level deep
        logger.info(
            f"[{self.city_key}] Found {len(laws)} direct PDFs, "
            f"following {len(subpage_urls)} subpages"
        )
        for subpage_url, parent_text in subpage_urls:
            subpage_laws = self._scrape_subpage(subpage_url, parent_text, seen_urls)
            laws.extend(subpage_laws)

        logger.info(f"[{self.city_key}] Total laws discovered: {len(laws)}")
        return laws

    def scrape_law_content(self, url: str) -> Optional[Dict]:
        """
        Fetch the content of a specific law document.

        Args:
            url: URL of the law document

        Returns:
            Dict with url, file_type, content, or None on failure
        """
        if self.is_pdf(url):
            try:
                self._rate_limit()
                response = self.session.get(url, timeout=60)
                response.raise_for_status()
                return {
                    "url": url,
                    "file_type": "pdf",
                    "content": None,  # Binary content; use download_law_content for extraction
                    "size_bytes": len(response.content),
                }
            except Exception as e:
                logger.error(f"[{self.city_key}] Error fetching PDF {url}: {e}")
                return None
        else:
            html = self.fetch_page(url)
            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text_content = soup.get_text(separator="\n", strip=True)
            return {
                "url": url,
                "file_type": "html",
                "content": text_content,
                "size_bytes": len(text_content),
            }

    def _is_regulatory_link(self, href: str, text: str) -> bool:
        """
        Check if a link looks like it points to a regulatory document.

        Matches against link text and URL path using REGULATORY_KEYWORDS.

        Args:
            href: Link href attribute
            text: Link visible text

        Returns:
            True if the link appears regulatory
        """
        if REGULATORY_KEYWORDS.search(text):
            return True
        if REGULATORY_KEYWORDS.search(href):
            return True
        return False

    def _scrape_subpage(
        self, url: str, parent_text: str, seen_urls: Set[str]
    ) -> List[Dict]:
        """
        Follow an HTML page one level deep to find PDF links.

        Args:
            url: Subpage URL to crawl
            parent_text: Text from the parent link (used as fallback title context)
            seen_urls: Set of already-seen URLs for deduplication (modified in place)

        Returns:
            List of law dictionaries found on the subpage
        """
        html = self.fetch_page(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        laws: List[Dict] = []

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            text = link.get_text(separator=" ", strip=True)
            absolute_url = self.normalize_url(href, url)

            parsed = urlparse(absolute_url)
            if parsed.scheme not in ("http", "https"):
                continue

            if absolute_url in seen_urls:
                continue

            if self.is_pdf(absolute_url):
                seen_urls.add(absolute_url)
                title = text or parent_text or self._title_from_url(absolute_url)
                law = self._build_law_dict(title, absolute_url)
                if self.validate_law_data(law):
                    laws.append(law)

        return laws

    def _build_law_dict(self, name: str, url: str) -> Dict:
        """
        Build a standardized law dictionary.

        Args:
            name: Law title
            url: Absolute URL to the document

        Returns:
            Law dictionary with all required fields
        """
        # Clean up whitespace in name
        name = re.sub(r"\s+", " ", name).strip()

        return {
            "name": name,
            "url": url,
            "municipality": self.municipality,
            "state": self.state,
            "tier": "municipal",
            "category": self.extract_category(name),
            "status": "Discovered",
            "source_tier": self.tier,
        }

    def _title_from_url(self, url: str) -> str:
        """
        Extract a human-readable title from a URL path.

        Args:
            url: Document URL

        Returns:
            Cleaned title derived from the filename
        """
        from os.path import basename, splitext
        from urllib.parse import unquote

        filename = basename(unquote(urlparse(url).path))
        name_body = splitext(filename)[0]
        return name_body.replace("_", " ").replace("-", " ")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Generic municipal scraper for any configured city"
    )
    parser.add_argument(
        "--city",
        required=True,
        help=f"City key from config. Available: {', '.join(MUNICIPALITY_CONFIGS.keys())}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of results displayed (0 = all)",
    )
    args = parser.parse_args()

    scraper = GenericMunicipalScraper(city_key=args.city)
    results = scraper.scrape_catalog()

    print(f"\n{'=' * 60}")
    print(f"City: {scraper.municipality} ({scraper.state})")
    print(f"Laws discovered: {len(results)}")
    print(f"{'=' * 60}")

    display = results[: args.limit] if args.limit > 0 else results
    for i, law in enumerate(display, 1):
        print(f"\n[{i}] {law['name']}")
        print(f"    URL: {law['url']}")
        print(f"    Category: {law['category']}")
