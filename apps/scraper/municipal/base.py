"""
Municipal Scraper Base Class

Provides core functionality for scraping municipal legal texts.
Subclasses implement municipality-specific scraping logic.
"""

import logging
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class MunicipalScraper:
    """
    Base class for municipal scrapers.

    Provides:
    - HTTP session with retry logic
    - Rate limiting
    - URL normalization
    - PDF detection
    - Data validation
    """

    def __init__(
        self, config: Dict = None, municipality: str = None, base_url: str = None
    ):
        """
        Initialize scraper with either a config dict or explicit parameters.

        Args:
            config: Configuration dictionary from config.py
            municipality: Municipality name (fallback if no config)
            base_url: Base URL (fallback if no config)
        """
        if config:
            self.config = config
            self.municipality = config["name"]
            self.base_url = config["base_url"]
            self.state = config.get("state")
            self.selectors = config.get("selectors", {})
        else:
            # Fallback for backward compatibility
            self.config = {}
            self.municipality = municipality
            self.base_url = base_url
            self.state = None
            self.selectors = {}

        self.session = self._setup_session()
        self.last_request_time = 0
        self.min_request_interval = 1.0  # seconds between requests

    def _setup_session(self) -> requests.Session:
        """
        Configure session with retry logic and rate limiting.
        """
        session = requests.Session()

        # Retry strategy: 3 retries with exponential backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # User agent
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; LeyesMxBot/1.0; +https://leyes.mx)"
            }
        )

        return session

    def _rate_limit(self):
        """Ensure minimum time between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a web page with error handling and rate limiting.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None on error
        """
        try:
            self._rate_limit()
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def normalize_url(self, url: str, base: str = None) -> str:
        """
        Convert relative URLs to absolute URLs.

        Args:
            url: URL to normalize
            base: Base URL (defaults to self.base_url)

        Returns:
            Absolute URL
        """
        base = base or self.base_url
        return urljoin(base, url)

    def is_pdf(self, url: str) -> bool:
        """Check if URL points to a PDF file."""
        parsed = urlparse(url.lower())
        return parsed.path.endswith(".pdf")

    def validate_law_data(self, law: Dict) -> bool:
        """
        Validate that a law dictionary has required fields.

        Args:
            law: Dictionary with law metadata

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["name", "url", "municipality"]

        for field in required_fields:
            if field not in law or not law[field]:
                logger.warning(f"Law missing required field '{field}': {law}")
                return False

        # Validate URL format
        try:
            result = urlparse(law["url"])
            if not all([result.scheme, result.netloc]):
                logger.warning(f"Invalid URL format: {law['url']}")
                return False
        except Exception as e:
            logger.warning(f"Error validating URL {law.get('url')}: {e}")
            return False

        return True

    def extract_category(self, text: str) -> str:
        """
        Extract category from law name.

        Args:
            text: Law title or description

        Returns:
            Category string
        """
        text_lower = text.lower()

        if "reglamento" in text_lower:
            return "Reglamento"
        elif "código" in text_lower or "codigo" in text_lower:
            return "Código"
        elif "ley" in text_lower:
            return "Ley"
        elif "decreto" in text_lower:
            return "Decreto"
        else:
            return "Otro"

    def download_law_content(self, url: str, output_dir: str) -> Optional[Dict]:
        """
        Download law content (PDF or HTML) and extract text.

        Args:
            url: URL of the law document
            output_dir: Directory to save downloaded files

        Returns:
            Dict with file_type, file_path, text_content, or None on failure
        """
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            self._rate_limit()

            if self.is_pdf(url):
                return self._download_pdf(url, output_path)
            else:
                return self._download_html(url, output_path)
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return None

    def _download_pdf(self, url: str, output_dir) -> Optional[Dict]:
        """Download a PDF and extract text using pdfplumber."""
        from pathlib import Path

        response = self.session.get(url, timeout=60)
        response.raise_for_status()

        # Generate filename from URL
        filename = url.split("/")[-1]
        if not filename.endswith(".pdf"):
            filename = filename + ".pdf"
        # Sanitize
        filename = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)

        pdf_path = output_dir / filename
        pdf_path.write_bytes(response.content)

        # Extract text
        text_content = ""
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                text_content = "\n".join(text_parts)
        except ImportError:
            logger.warning(
                "pdfplumber not installed, saving PDF without text extraction"
            )
        except Exception as e:
            logger.warning(f"PDF text extraction failed: {e}")

        # Save extracted text alongside PDF
        text_path = pdf_path.with_suffix(".txt")
        if text_content:
            text_path.write_text(text_content, encoding="utf-8")

        return {
            "url": url,
            "file_type": "pdf",
            "file_path": str(pdf_path),
            "text_path": str(text_path) if text_content else None,
            "text_content": text_content,
            "size_bytes": len(response.content),
        }

    def _download_html(self, url: str, output_dir) -> Optional[Dict]:
        """Download an HTML page and extract text content."""
        html = self.fetch_page(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")

        # Remove script/style elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Extract text
        text_content = soup.get_text(separator="\n", strip=True)

        # Save text file
        filename = url.split("/")[-1].split("?")[0] or "page"
        filename = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)
        if not filename.endswith(".txt"):
            filename = filename + ".txt"

        text_path = output_dir / filename
        text_path.write_text(text_content, encoding="utf-8")

        return {
            "url": url,
            "file_type": "html",
            "file_path": str(text_path),
            "text_path": str(text_path),
            "text_content": text_content,
            "size_bytes": len(text_content),
        }

    # Abstract methods - must be implemented by subclasses

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape the main catalog page and return a list of laws/regulations.

        Each item should be a dict with:
        - name: str - Law title
        - url: str - Absolute URL to law document
        - municipality: str - Municipality name
        - state: str - State name
        - tier: str - 'municipal'
        - category: str - Document type (optional)

        Returns:
            List of law dictionaries
        """
        raise NotImplementedError("Subclasses must implement scrape_catalog")

    def scrape_law_content(self, url: str) -> Optional[Dict]:
        """
        Fetch the content of a specific law.

        Args:
            url: URL of the law document

        Returns:
            Dict with:
            - url: str - Document URL
            - file_type: str - 'pdf' or 'html'
            - content: str - Text content (if available)
        """
        raise NotImplementedError("Subclasses must implement scrape_law_content")
