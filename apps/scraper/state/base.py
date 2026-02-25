"""
State Congress Scraper Base Class

Provides core functionality for scraping state congress portals.
Subclasses implement state-specific scraping logic for each congress website.
"""

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DOWNLOADABLE_EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv"})


class StateCongressScraper(ABC):
    """
    Base class for state congress scrapers.

    Provides:
    - HTTP session with retry logic and exponential backoff
    - Rate limiting (1 second between requests)
    - URL normalization
    - Downloadable file detection (PDF, DOC, DOCX, XLS, XLSX, CSV)
    - Law data validation
    - Category extraction from law titles
    - Generic file download
    """

    def __init__(
        self,
        state: str,
        base_url: str,
        formats: Optional[List[str]] = None,
    ):
        """
        Initialize state congress scraper.

        Args:
            state: Full state name (e.g. "Baja California").
            base_url: Root URL of the congress portal.
            formats: Accepted document formats. Defaults to all downloadable types.
        """
        self.state = state
        self.base_url = base_url.rstrip("/")
        self.formats = formats or [ext.lstrip(".") for ext in DOWNLOADABLE_EXTENSIONS]
        self.session = self._setup_session()
        self.last_request_time: float = 0
        self.min_request_interval: float = 1.0  # seconds between requests

    # ------------------------------------------------------------------
    # HTTP session
    # ------------------------------------------------------------------

    def _setup_session(self) -> requests.Session:
        """Configure session with retry logic and rate limiting."""
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
                "User-Agent": (
                    "Mozilla/5.0 (compatible; TezcaBot/1.0; +https://leyes.mx)"
                ),
            }
        )

        return session

    def _rate_limit(self) -> None:
        """Ensure minimum time between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    # ------------------------------------------------------------------
    # Page fetching
    # ------------------------------------------------------------------

    def fetch_page(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        Fetch a web page with error handling and rate limiting.

        Args:
            url: URL to fetch.
            timeout: Request timeout in seconds.

        Returns:
            HTML content or None on error.
        """
        try:
            self._rate_limit()
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error("Error fetching %s: %s", url, e)
            return None

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def normalize_url(self, url: str, base: Optional[str] = None) -> str:
        """
        Convert relative URLs to absolute URLs.

        Args:
            url: URL to normalize (may be relative).
            base: Base URL for resolution. Defaults to self.base_url.

        Returns:
            Absolute URL.
        """
        base = base or self.base_url
        return urljoin(base, url)

    def is_downloadable(self, url: str) -> bool:
        """
        Check if URL points to a downloadable file.

        Supported extensions: .pdf, .doc, .docx, .xls, .xlsx, .csv

        Args:
            url: URL to check.

        Returns:
            True if the URL path ends with a known downloadable extension.
        """
        parsed = urlparse(url.lower())
        path = parsed.path
        return any(path.endswith(ext) for ext in DOWNLOADABLE_EXTENSIONS)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_law_data(self, law: Dict) -> bool:
        """
        Validate that a law dictionary has required fields.

        Required: name, url, state.

        Args:
            law: Dictionary with law metadata.

        Returns:
            True if valid, False otherwise.
        """
        required_fields = ["name", "url", "state"]

        for field in required_fields:
            if field not in law or not law[field]:
                logger.warning("Law missing required field '%s': %s", field, law)
                return False

        try:
            result = urlparse(law["url"])
            if not all([result.scheme, result.netloc]):
                logger.warning("Invalid URL format: %s", law["url"])
                return False
        except Exception as e:
            logger.warning("Error validating URL %s: %s", law.get("url"), e)
            return False

        return True

    # ------------------------------------------------------------------
    # Category extraction
    # ------------------------------------------------------------------

    def extract_category(self, text: str) -> str:
        """
        Extract category from a law title.

        Args:
            text: Law title or description.

        Returns:
            Category string (Ley, Codigo, Reglamento, Decreto, Otro).
        """
        text_lower = text.lower()

        if "constitución" in text_lower or "constitucion" in text_lower:
            return "Constitucion"
        elif "código" in text_lower or "codigo" in text_lower:
            return "Codigo"
        elif "ley orgánica" in text_lower or "ley organica" in text_lower:
            return "Ley Organica"
        elif "ley" in text_lower:
            return "Ley"
        elif "reglamento" in text_lower:
            return "Reglamento"
        elif "decreto" in text_lower:
            return "Decreto"
        elif "acuerdo" in text_lower:
            return "Acuerdo"
        else:
            return "Otro"

    # ------------------------------------------------------------------
    # File download
    # ------------------------------------------------------------------

    def download_file(self, url: str, output_dir: str) -> Optional[Dict]:
        """
        Download a file to the output directory.

        Handles PDF, DOC, DOCX, XLS, XLSX, and CSV files. For PDFs,
        attempts text extraction via pdfplumber when available.

        Args:
            url: URL of the file to download.
            output_dir: Directory path to save the file.

        Returns:
            Dict with url, file_type, file_path, size_bytes, or None on failure.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            self._rate_limit()
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Error downloading %s: %s", url, e)
            return None

        # Derive filename from URL
        filename = urlparse(url).path.split("/")[-1] or "document"
        filename = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)

        file_path = output_path / filename
        file_path.write_bytes(response.content)

        result: Dict = {
            "url": url,
            "file_type": file_path.suffix.lstrip("."),
            "file_path": str(file_path),
            "size_bytes": len(response.content),
        }

        # Attempt PDF text extraction
        if file_path.suffix.lower() == ".pdf":
            result["text_content"] = self._extract_pdf_text(file_path)

        logger.debug("Downloaded %s (%d bytes)", filename, result["size_bytes"])
        return result

    @staticmethod
    def _extract_pdf_text(pdf_path: Path) -> str:
        """
        Extract text from a PDF file using pdfplumber.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Extracted text, or empty string on failure.
        """
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                parts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        parts.append(page_text)
                return "\n".join(parts)
        except ImportError:
            logger.warning("pdfplumber not installed, skipping PDF text extraction")
            return ""
        except Exception as e:
            logger.warning("PDF text extraction failed for %s: %s", pdf_path, e)
            return ""

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape the congress portal catalog and return a list of laws.

        Each item should be a dict with:
        - name: str - Law title
        - url: str - Absolute URL to the law document
        - state: str - State name
        - tier: str - "state"
        - category: str - Document type (Ley, Codigo, Reglamento, etc.)
        - law_type: str - Legislative classification

        Returns:
            List of law dictionaries.
        """
        ...

    @abstractmethod
    def scrape_law_content(self, url: str) -> Optional[Dict]:
        """
        Fetch the content of a specific law document.

        Args:
            url: URL of the law document.

        Returns:
            Dict with url, file_type, content (text), or None on failure.
        """
        ...
