"""
Quintana Roo State Congress Scraper

Scrapes legislation from the Quintana Roo state congress portal.
Portal: https://www.congresoqroo.gob.mx
Expected catalog size: ~356 laws.

Special: This portal may expose CSV/XLS export endpoints for structured
data access alongside the standard HTML catalog.
"""

import logging
from typing import Dict, List, Optional
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from .base import StateCongressScraper

logger = logging.getLogger(__name__)


class QuintanaRooScraper(StateCongressScraper):
    """
    Scraper for the Quintana Roo state congress website.

    Supports two data acquisition strategies:
    1. Standard HTML catalog scraping from /leyes/
    2. Structured data export via CSV/XLS endpoints when available
    """

    CATALOG_PATH = "/leyes/"
    ALTERNATIVE_PATHS = [
        "/legislacion",
        "/leyes-vigentes",
        "/trabajo-legislativo/leyes",
        "/marco-juridico",
    ]

    # Common patterns for export/download endpoints on congress portals
    EXPORT_PATTERNS = [
        "/leyes/export",
        "/leyes/descargar",
        "/api/leyes",
        "/legislacion/export",
        "/datos-abiertos",
    ]

    def __init__(self) -> None:
        super().__init__(
            state="Quintana Roo",
            base_url="https://www.congresoqroo.gob.mx",
            formats=["pdf", "doc", "docx", "xls", "xlsx", "csv"],
        )
        logger.info("Initialized %s scraper - %s", self.state, self.base_url)

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape the Quintana Roo legislation catalog.

        First attempts structured data export (CSV/XLS). Falls back to
        HTML catalog scraping if no export endpoint is available.

        Returns:
            List of law dictionaries.
        """
        # Try structured export first (faster, more reliable)
        structured_laws = self.scrape_structured_data()
        if structured_laws:
            logger.info(
                "Retrieved %d laws via structured export for %s",
                len(structured_laws),
                self.state,
            )
            return structured_laws

        # Fall back to HTML scraping
        logger.info("No structured export available, falling back to HTML scraping")
        return self._scrape_html_catalog()

    def scrape_law_content(self, url: str) -> Optional[Dict]:
        """
        Download and extract content of a specific Quintana Roo law.

        Args:
            url: URL of the law document.

        Returns:
            Dict with url, file_type, file_path, size_bytes, or None on failure.
        """
        output_dir = "data/state/quintana_roo/raw"
        return self.download_file(url, output_dir)

    # ------------------------------------------------------------------
    # Structured data export
    # ------------------------------------------------------------------

    def scrape_structured_data(self) -> List[Dict]:
        """
        Attempt to retrieve legislation data from export endpoints.

        Probes known export URL patterns for CSV or XLS downloads.
        Parses the structured data into law dictionaries when found.

        Returns:
            List of law dictionaries if an export endpoint is found,
            empty list otherwise.
        """
        for pattern in self.EXPORT_PATTERNS:
            for fmt in ["csv", "xlsx", "xls"]:
                export_url = self.normalize_url(pattern)
                # Try with format query parameter
                url_with_format = f"{export_url}?format={fmt}"

                try:
                    self._rate_limit()
                    response = self.session.head(url_with_format, timeout=15)
                    if response.status_code == 200:
                        content_type = response.headers.get("Content-Type", "")
                        if self._is_structured_content_type(content_type, fmt):
                            logger.info(
                                "Found structured export endpoint: %s",
                                url_with_format,
                            )
                            return self._parse_export_data(url_with_format, fmt)
                except Exception as e:
                    logger.debug("Export probe failed for %s: %s", url_with_format, e)
                    continue

        # Also look for export links on the catalog page itself
        return self._find_export_links_on_page()

    def _is_structured_content_type(self, content_type: str, fmt: str) -> bool:
        """Check if the response content type matches the expected format."""
        structured_types = {
            "csv": ["text/csv", "application/csv"],
            "xls": [
                "application/vnd.ms-excel",
                "application/octet-stream",
            ],
            "xlsx": [
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/octet-stream",
            ],
        }
        expected = structured_types.get(fmt, [])
        return any(ct in content_type for ct in expected)

    def _parse_export_data(self, url: str, fmt: str) -> List[Dict]:
        """
        Download and parse a structured export file.

        Args:
            url: URL of the export endpoint.
            fmt: File format (csv, xls, xlsx).

        Returns:
            List of law dictionaries parsed from the export data.
        """
        try:
            self._rate_limit()
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
        except Exception as e:
            logger.error("Failed to download export from %s: %s", url, e)
            return []

        if fmt == "csv":
            return self._parse_csv_export(response.text)
        else:
            return self._parse_excel_export(response.content, fmt)

    def _parse_csv_export(self, csv_text: str) -> List[Dict]:
        """Parse CSV export data into law dictionaries."""
        import csv
        import io

        laws: List[Dict] = []
        reader = csv.DictReader(io.StringIO(csv_text))

        for row in reader:
            try:
                name = (
                    row.get("nombre")
                    or row.get("name")
                    or row.get("ley")
                    or row.get("titulo")
                    or ""
                ).strip()
                doc_url = (
                    row.get("url")
                    or row.get("enlace")
                    or row.get("documento")
                    or row.get("link")
                    or ""
                ).strip()

                if not name or not doc_url:
                    continue

                absolute_url = self.normalize_url(doc_url)
                law = {
                    "name": name[:500],
                    "url": absolute_url,
                    "state": self.state,
                    "tier": "state",
                    "category": self.extract_category(name),
                    "law_type": self._infer_law_type(name),
                }

                if self.validate_law_data(law):
                    laws.append(law)
            except Exception as e:
                logger.debug("Error parsing CSV row: %s", e)
                continue

        return laws

    def _parse_excel_export(self, content: bytes, fmt: str) -> List[Dict]:
        """
        Parse XLS/XLSX export data into law dictionaries.

        Requires openpyxl (xlsx) or xlrd (xls) to be installed.
        """
        try:
            import openpyxl
        except ImportError:
            logger.warning("openpyxl not installed, cannot parse %s export", fmt)
            return []

        import io

        laws: List[Dict] = []

        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
            ws = wb.active
            if ws is None:
                return []

            rows = list(ws.iter_rows(values_only=True))
            if len(rows) < 2:
                return []

            # Use first row as headers
            headers = [str(h).lower().strip() if h else "" for h in rows[0]]

            # Find name and url columns
            name_col = self._find_column_index(
                headers, ["nombre", "name", "ley", "titulo"]
            )
            url_col = self._find_column_index(
                headers, ["url", "enlace", "documento", "link"]
            )

            if name_col is None:
                logger.warning("Could not identify name column in export")
                return []

            for row in rows[1:]:
                try:
                    name = str(row[name_col]).strip() if row[name_col] else ""
                    doc_url = (
                        str(row[url_col]).strip()
                        if url_col is not None and row[url_col]
                        else ""
                    )

                    if not name:
                        continue

                    if doc_url:
                        absolute_url = self.normalize_url(doc_url)
                    else:
                        # No URL in export; skip entry
                        continue

                    law = {
                        "name": name[:500],
                        "url": absolute_url,
                        "state": self.state,
                        "tier": "state",
                        "category": self.extract_category(name),
                        "law_type": self._infer_law_type(name),
                    }

                    if self.validate_law_data(law):
                        laws.append(law)
                except Exception as e:
                    logger.debug("Error parsing Excel row: %s", e)
                    continue

            wb.close()
        except Exception as e:
            logger.error("Failed to parse Excel export: %s", e)

        return laws

    @staticmethod
    def _find_column_index(headers: List[str], candidates: List[str]) -> Optional[int]:
        """Find the index of the first header matching any candidate name."""
        for candidate in candidates:
            for i, header in enumerate(headers):
                if candidate in header:
                    return i
        return None

    def _find_export_links_on_page(self) -> List[Dict]:
        """
        Scan the HTML catalog page for export/download links.

        Some portals place CSV/XLS download buttons directly on the
        legislation listing page.

        Returns:
            Parsed law list if an export link is found, empty list otherwise.
        """
        html = self._fetch_catalog_page()
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link["href"].strip().lower()
            text = link.get_text(strip=True).lower()

            # Look for export-related links
            export_keywords = [
                "exportar",
                "descargar",
                "download",
                "csv",
                "excel",
                "datos abiertos",
            ]
            if any(kw in text or kw in href for kw in export_keywords):
                absolute_url = self.normalize_url(link["href"].strip())
                if absolute_url.endswith((".csv", ".xls", ".xlsx")):
                    fmt = absolute_url.rsplit(".", 1)[-1]
                    logger.info("Found export link on page: %s", absolute_url)
                    return self._parse_export_data(absolute_url, fmt)

        return []

    # ------------------------------------------------------------------
    # HTML catalog scraping (fallback)
    # ------------------------------------------------------------------

    def _scrape_html_catalog(self) -> List[Dict]:
        """Scrape the HTML catalog page for law links."""
        html = self._fetch_catalog_page()
        if not html:
            logger.error("Could not fetch any catalog page for %s", self.state)
            return []

        soup = BeautifulSoup(html, "html.parser")
        laws: List[Dict] = []

        # Extract from content areas, tables, and lists
        for link in soup.find_all("a", href=True):
            try:
                law = self._parse_law_link(link)
                if law:
                    laws.append(law)
            except Exception as e:
                logger.debug("Error parsing link: %s", e)
                continue

        # Handle pagination
        page_num = 1
        while page_num < 50:  # Safety cap
            next_url = self._find_next_page(soup)
            if not next_url:
                break
            page_num += 1
            html = self.fetch_page(next_url)
            if not html:
                break
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.find_all("a", href=True):
                try:
                    law = self._parse_law_link(link)
                    if law:
                        laws.append(law)
                except Exception as e:
                    logger.debug("Error parsing link: %s", e)
                    continue

        # Deduplicate
        seen_urls: set = set()
        unique_laws: List[Dict] = []
        for law in laws:
            if law["url"] not in seen_urls:
                seen_urls.add(law["url"])
                unique_laws.append(law)

        logger.info("Scraped %d laws from %s (HTML)", len(unique_laws), self.state)
        return unique_laws

    def _fetch_catalog_page(self) -> Optional[str]:
        """Try primary and alternative catalog paths."""
        primary_url = self.normalize_url(self.CATALOG_PATH)
        html = self.fetch_page(primary_url)
        if html:
            return html

        logger.warning(
            "Primary catalog path failed (%s), trying alternatives", primary_url
        )
        for alt_path in self.ALTERNATIVE_PATHS:
            alt_url = self.normalize_url(alt_path)
            html = self.fetch_page(alt_url)
            if html:
                logger.info("Found catalog at alternative path: %s", alt_url)
                return html

        return None

    def _parse_law_link(self, link) -> Optional[Dict]:
        """Parse an anchor tag into a law dictionary."""
        href = link["href"].strip()
        text = link.get_text(strip=True)

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
        """Find the URL of the next pagination page."""
        next_link = soup.find("a", class_="next")
        if next_link and next_link.get("href"):
            return self.normalize_url(next_link["href"])

        for link in soup.find_all("a", href=True):
            link_text = link.get_text(strip=True).lower()
            if link_text in ("siguiente", "next", ">>", ">"):
                return self.normalize_url(link["href"])

        next_link = soup.find(
            "a", attrs={"aria-label": lambda v: v and "next" in v.lower()}
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
        else:
            return "otro"
