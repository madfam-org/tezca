"""
International Treaties Scraper

Scrapes bilateral and multilateral treaties from tratados.sre.gob.mx.
~1,500 treaties ratified by Mexico. Per SCJN, treaties sit above
federal laws in the normative hierarchy.

Usage:
    python -m apps.scraper.federal.treaty_scraper
    python -m apps.scraper.federal.treaty_scraper --output-dir data/treaties
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://tratados.sre.gob.mx"
_USER_AGENT = "Tezca/1.0 (+https://github.com/madfam-org/tezca)"
_REQUEST_TIMEOUT = 30  # seconds
_MIN_REQUEST_INTERVAL = 1.0  # 1 req/sec

# Patterns for treaty type classification.
_BILATERAL_KEYWORDS = [
    "bilateral",
    "acuerdo entre",
    "convenio entre",
    "tratado entre",
    "protocolo entre",
]
_MULTILATERAL_KEYWORDS = [
    "multilateral",
    "convencion",
    "convenci\u00f3n",
    "protocolo de",
    "carta de",
    "pacto",
    "estatuto de",
]


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class TreatyScraper:
    """
    Scraper for international treaties ratified by Mexico.

    Fetches the SRE (Secretaria de Relaciones Exteriores) treaty portal
    catalog, parses treaty listings, and optionally fetches individual
    treaty detail pages for full text and PDF links.
    """

    def __init__(self) -> None:
        self.session = self._setup_session()
        self.last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Session setup
    # ------------------------------------------------------------------

    @staticmethod
    def _setup_session() -> requests.Session:
        """Configure HTTP session with retry logic and polite headers."""
        session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        session.headers.update(
            {
                "User-Agent": _USER_AGENT,
                "Accept": "text/html, application/xhtml+xml, */*",
                "Accept-Language": "es-MX,es;q=0.9,en;q=0.5",
            }
        )
        return session

    def _rate_limit(self) -> None:
        """Enforce minimum interval between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def _get(self, url: str, **kwargs: Any) -> Optional[requests.Response]:
        """Rate-limited GET with error handling."""
        self._rate_limit()
        try:
            response = self.session.get(url, timeout=_REQUEST_TIMEOUT, **kwargs)
            response.raise_for_status()
            return response
        except requests.ConnectionError:
            logger.error("Connection failed: %s", url)
        except requests.Timeout:
            logger.error("Request timed out: %s", url)
        except requests.HTTPError as exc:
            logger.warning("HTTP %s for %s", exc.response.status_code, url)
        except requests.RequestException as exc:
            logger.error("Request error for %s: %s", url, exc)
        return None

    # ------------------------------------------------------------------
    # Catalog scraping
    # ------------------------------------------------------------------

    def scrape_catalog(self) -> List[Dict[str, Any]]:
        """
        Fetch the SRE treaty portal catalog and parse treaty listings.

        Handles pagination if the portal splits results across pages.

        Returns:
            List of treaty dicts with basic metadata.
        """
        logger.info("Scraping treaty catalog from %s", BASE_URL)

        all_treaties: List[Dict[str, Any]] = []
        seen_urls: set = set()
        page = 1
        empty_streak = 0

        while True:
            url = f"{BASE_URL}/tratados?page={page}"
            logger.info("Fetching catalog page %d: %s", page, url)

            resp = self._get(url)
            if resp is None:
                empty_streak += 1
                if empty_streak >= 3:
                    logger.warning("3 consecutive failures, stopping.")
                    break
                page += 1
                continue

            treaties = self._parse_catalog_page(resp.text)
            if not treaties:
                # Also try the root URL on first page.
                if page == 1:
                    resp_root = self._get(BASE_URL)
                    if resp_root:
                        treaties = self._parse_catalog_page(resp_root.text)

                if not treaties:
                    empty_streak += 1
                    if empty_streak >= 3:
                        logger.info(
                            "3 consecutive empty pages, assuming end of catalog."
                        )
                        break
                    page += 1
                    continue

            empty_streak = 0
            new_count = 0
            for treaty in treaties:
                treaty_url = treaty.get("url", "")
                if treaty_url in seen_urls:
                    continue
                seen_urls.add(treaty_url)
                all_treaties.append(treaty)
                new_count += 1

            logger.info(
                "Page %d: %d new treaties (total: %d)",
                page,
                new_count,
                len(all_treaties),
            )

            if new_count == 0:
                empty_streak += 1
                if empty_streak >= 3:
                    break

            page += 1

        logger.info("Catalog scrape complete: %d treaties", len(all_treaties))
        return all_treaties

    def _parse_catalog_page(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse a catalog page and extract treaty listings.

        Tries multiple selector strategies to handle layout variations.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        treaties: List[Dict[str, Any]] = []

        # Strategy 1: table rows
        for row in soup.select("table tbody tr"):
            try:
                treaty = self._parse_table_row(row)
                if treaty:
                    treaties.append(treaty)
            except Exception:
                logger.debug("Failed to parse table row", exc_info=True)
                continue

        if treaties:
            return treaties

        # Strategy 2: list items or card layout
        for item in soup.select(
            ".tratado, .treaty-item, .resultado, .list-item, article, .card"
        ):
            try:
                treaty = self._parse_list_item(item)
                if treaty:
                    treaties.append(treaty)
            except Exception:
                logger.debug("Failed to parse list item", exc_info=True)
                continue

        if treaties:
            return treaties

        # Strategy 3: scan all links that look like treaty detail pages
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if not text or len(text) < 10:
                continue
            # Heuristic: treaty links typically contain identifiable paths.
            if any(
                kw in href.lower()
                for kw in ("tratado", "treaty", "convenio", "acuerdo", "detail")
            ):
                abs_url = self._resolve_url(href)
                treaty_type = _classify_treaty_type(text)
                treaties.append(
                    {
                        "id": _generate_id(text),
                        "name": _clean_text(text),
                        "treaty_type": treaty_type,
                        "parties": "",
                        "date_signed": "",
                        "date_ratified": "",
                        "url": abs_url,
                        "pdf_url": "",
                        "source": "sre_tratados",
                    }
                )

        return treaties

    def _parse_table_row(self, row: Any) -> Optional[Dict[str, Any]]:
        """Extract treaty data from a table row."""
        cells = row.find_all("td")
        if len(cells) < 2:
            return None

        link = row.find("a", href=True)
        name = cells[0].get_text(strip=True)
        if not name or len(name) < 5:
            return None

        href = link.get("href", "") if link else ""
        abs_url = self._resolve_url(href) if href else ""

        treaty_type = _classify_treaty_type(name)
        parties = cells[1].get_text(strip=True) if len(cells) > 1 else ""
        date_signed = cells[2].get_text(strip=True) if len(cells) > 2 else ""
        date_ratified = cells[3].get_text(strip=True) if len(cells) > 3 else ""

        # Check for PDF link.
        pdf_link = row.find("a", href=lambda h: h and h.endswith(".pdf"))
        pdf_url = self._resolve_url(pdf_link["href"]) if pdf_link else ""

        return {
            "id": _generate_id(name),
            "name": _clean_text(name),
            "treaty_type": treaty_type,
            "parties": _clean_text(parties),
            "date_signed": _extract_date(date_signed),
            "date_ratified": _extract_date(date_ratified),
            "url": abs_url,
            "pdf_url": pdf_url,
            "source": "sre_tratados",
        }

    def _parse_list_item(self, item: Any) -> Optional[Dict[str, Any]]:
        """Extract treaty data from a card/list-item element."""
        title_el = item.find(["h2", "h3", "h4", "a", "strong"])
        if not title_el:
            return None

        name = title_el.get_text(strip=True)
        if not name or len(name) < 5:
            return None

        link = item.find("a", href=True)
        href = link.get("href", "") if link else ""
        abs_url = self._resolve_url(href) if href else ""

        treaty_type = _classify_treaty_type(name)

        # Try to find parties and dates in the item text.
        full_text = item.get_text()
        date_signed = _extract_date(full_text)

        pdf_link = item.find("a", href=lambda h: h and h.endswith(".pdf"))
        pdf_url = self._resolve_url(pdf_link["href"]) if pdf_link else ""

        return {
            "id": _generate_id(name),
            "name": _clean_text(name),
            "treaty_type": treaty_type,
            "parties": "",
            "date_signed": date_signed,
            "date_ratified": "",
            "url": abs_url,
            "pdf_url": pdf_url,
            "source": "sre_tratados",
        }

    # ------------------------------------------------------------------
    # Treaty detail scraping
    # ------------------------------------------------------------------

    def scrape_treaty_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch an individual treaty page for full text and PDF link.

        Args:
            url: Absolute URL to the treaty detail page.

        Returns:
            Dict with additional metadata (full_text, pdf_url, parties,
            dates) or None on failure.
        """
        if not url:
            return None

        logger.debug("Fetching treaty detail: %s", url)
        resp = self._get(url)
        if resp is None:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove navigation, footer, scripts.
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Extract full text from the main content area.
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(class_=re.compile(r"content|body|tratado|detail"))
            or soup.find("body")
        )
        full_text = ""
        if main_content:
            full_text = main_content.get_text(separator="\n", strip=True)

        # Find PDF links.
        pdf_link = soup.find("a", href=lambda h: h and h.lower().endswith(".pdf"))
        pdf_url = ""
        if pdf_link:
            pdf_url = self._resolve_url(pdf_link["href"])

        # Try to extract structured metadata from the page.
        parties = _extract_field(soup, ["partes", "parties", "paises", "signatarios"])
        date_signed = _extract_field(soup, ["fecha de firma", "date signed", "firma"])
        date_ratified = _extract_field(
            soup, ["fecha de ratificacion", "ratificacion", "aprobacion"]
        )

        return {
            "full_text": full_text[:50000] if full_text else "",
            "pdf_url": pdf_url,
            "parties": _clean_text(parties),
            "date_signed": _extract_date(date_signed) if date_signed else "",
            "date_ratified": _extract_date(date_ratified) if date_ratified else "",
        }

    # ------------------------------------------------------------------
    # URL resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_url(href: str) -> str:
        """Resolve a potentially relative href against the base URL."""
        if not href:
            return ""
        if href.startswith(("http://", "https://")):
            return href
        return urljoin(BASE_URL + "/", href)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def save_results(treaties: List[Dict[str, Any]], output_path: Path) -> None:
        """
        Save treaty results to a JSON file.

        Args:
            treaties: List of treaty dicts.
            output_path: Target file path.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(treaties, f, indent=2, ensure_ascii=False)
        logger.info("Saved %d treaties to %s", len(treaties), output_path)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        output_dir: str = "data/treaties",
        fetch_details: bool = False,
        max_details: int = 50,
    ) -> Dict[str, Any]:
        """
        Run the full treaty scraping pipeline.

        1. Scrape the catalog for all treaty listings.
        2. Optionally fetch detail pages for richer metadata.
        3. Save results.
        4. Log summary.

        Args:
            output_dir: Directory for output files.
            fetch_details: Whether to fetch individual detail pages.
            max_details: Maximum number of detail pages to fetch.

        Returns:
            Summary dict with total_treaties, output_path, details_fetched.
        """
        out_path = Path(output_dir)
        logger.info("Starting treaty scraper (fetch_details=%s)", fetch_details)

        # Step 1: scrape catalog
        treaties = self.scrape_catalog()

        # Step 2: optionally enrich with detail pages
        details_fetched = 0
        if fetch_details and treaties:
            for i, treaty in enumerate(treaties):
                if details_fetched >= max_details:
                    logger.info("Reached max_details=%d, stopping.", max_details)
                    break

                url = treaty.get("url", "")
                if not url:
                    continue

                detail = self.scrape_treaty_detail(url)
                if detail:
                    # Merge detail data into the treaty dict without
                    # overwriting existing non-empty fields.
                    for key, value in detail.items():
                        if value and not treaty.get(key):
                            treaty[key] = value
                    details_fetched += 1

                if (i + 1) % 10 == 0:
                    logger.info(
                        "Detail progress: %d/%d treaties enriched",
                        details_fetched,
                        min(len(treaties), max_details),
                    )

        # Step 3: save
        output_file = out_path / "discovered_treaties.json"
        self.save_results(treaties, output_file)

        # Step 4: summary
        bilateral = sum(1 for t in treaties if t.get("treaty_type") == "bilateral")
        multilateral = sum(
            1 for t in treaties if t.get("treaty_type") == "multilateral"
        )

        summary = {
            "total_treaties": len(treaties),
            "bilateral": bilateral,
            "multilateral": multilateral,
            "unknown_type": len(treaties) - bilateral - multilateral,
            "details_fetched": details_fetched,
            "output_path": str(output_file),
        }
        logger.info("Treaty scraper complete: %s", summary)
        return summary


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _clean_text(raw: str) -> str:
    """Collapse whitespace and strip surrounding blanks."""
    return re.sub(r"\s+", " ", raw).strip()


def _generate_id(name: str) -> str:
    """Generate a slug-style ID from a treaty name."""
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"\s+", "_", slug.strip())
    return slug[:80] if slug else "unknown"


def _classify_treaty_type(text: str) -> str:
    """
    Classify a treaty as bilateral or multilateral based on its title.

    Returns 'bilateral', 'multilateral', or 'unknown'.
    """
    text_lower = text.lower()

    for kw in _BILATERAL_KEYWORDS:
        if kw in text_lower:
            return "bilateral"

    for kw in _MULTILATERAL_KEYWORDS:
        if kw in text_lower:
            return "multilateral"

    return "unknown"


def _extract_date(text: str) -> str:
    """
    Try to extract a date from free text.

    Returns ISO-format string or empty string.
    """
    if not text:
        return ""

    # DD/MM/YYYY or DD-MM-YYYY
    match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if match:
        day, month, year = match.group(1), match.group(2), match.group(3)
        try:
            return f"{year}-{int(month):02d}-{int(day):02d}"
        except (ValueError, TypeError):
            pass

    # YYYY-MM-DD already ISO
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return match.group(0)

    return ""


def _extract_field(soup: BeautifulSoup, labels: List[str]) -> str:
    """
    Search for a labeled field in the page DOM.

    Looks for elements containing any of the *labels* (case-insensitive)
    and returns the adjacent/following text content.
    """
    for label in labels:
        # Try label/value patterns: <dt>label</dt><dd>value</dd>
        for dt in soup.find_all("dt"):
            if label in dt.get_text().lower():
                dd = dt.find_next_sibling("dd")
                if dd:
                    return dd.get_text(strip=True)

        # Try table header/cell patterns.
        for th in soup.find_all("th"):
            if label in th.get_text().lower():
                td = th.find_next_sibling("td")
                if td:
                    return td.get_text(strip=True)

        # Try label + span/div patterns.
        for el in soup.find_all(["label", "strong", "b", "span"]):
            if label in el.get_text().lower():
                sibling = el.find_next_sibling()
                if sibling:
                    return sibling.get_text(strip=True)
                # Maybe the value is in the parent's remaining text.
                parent = el.parent
                if parent:
                    parent_text = parent.get_text(strip=True)
                    el_text = el.get_text(strip=True)
                    remainder = parent_text.replace(el_text, "", 1).strip()
                    if remainder:
                        return remainder

    return ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the treaty scraper."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Scrape international treaties from the SRE portal.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/treaties",
        help="Directory to save results (default: data/treaties).",
    )
    parser.add_argument(
        "--fetch-details",
        action="store_true",
        help="Fetch individual treaty detail pages for richer metadata.",
    )
    parser.add_argument(
        "--max-details",
        type=int,
        default=50,
        help="Maximum number of detail pages to fetch (default: 50).",
    )
    args = parser.parse_args()

    scraper = TreatyScraper()
    result = scraper.run(
        output_dir=args.output_dir,
        fetch_details=args.fetch_details,
        max_details=args.max_details,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
