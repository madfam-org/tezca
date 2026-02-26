"""
CONAMER CNARTyS Scraper

Scrapes the Catálogo Nacional de Regulaciones, Trámites y Servicios.
113,373 regulations listed. Significant overlap expected with existing
reglamentos + state non-legislative corpus -- dedup required.

The original portal (cnartys.conamer.gob.mx) was decommissioned circa 2025.
The successor portal is catalogonacional.gob.mx, which requires browser-based
access (WAF blocks automated HTTP requests with 403).

An alternative legacy endpoint at conamer.gob.mx/cnartys-t/ had an expired
SSL certificate as of Feb 2026.

Usage:
    python -m apps.scraper.federal.conamer_scraper
    python -m apps.scraper.federal.conamer_scraper --max-pages 10
    python -m apps.scraper.federal.conamer_scraper --resume-from 5
"""

import json
import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Primary: successor portal (requires browser-based access, blocks automated HTTP)
BASE_URL = "https://catalogonacional.gob.mx"
# Fallback: legacy CONAMER portal (expired SSL cert as of Feb 2026)
LEGACY_URL = "https://conamer.gob.mx/cnartys-t"
# Original (DNS-dead since ~2025): https://cnartys.conamer.gob.mx

_USER_AGENT = "Tezca/1.0 (+https://github.com/madfam-org/tezca)"
_REQUEST_TIMEOUT = 30  # seconds
_MIN_REQUEST_INTERVAL = 1.0  # 1 req/sec to be respectful

# Common API path patterns to probe on the successor portal.
_API_PROBE_PATHS = [
    "/api/regulaciones",
    "/api/v1/regulaciones",
    "/api/v2/regulaciones",
    "/api/catalogos",
    "/api/v1/catalogos",
    "/api/search",
    "/api/v1/search",
    "/api/",
    "/api/v1/",
    # Legacy CNARTyS patterns
    "/FichaTramite",
    "/Busqueda",
    "/Catalogo",
]

# Words stripped during title normalisation for dedup.
_STOP_WORDS = frozenset(
    {
        "de",
        "del",
        "la",
        "las",
        "los",
        "el",
        "en",
        "y",
        "a",
        "por",
        "para",
        "que",
        "con",
        "al",
        "se",
        "su",
        "una",
        "un",
        "es",
    }
)


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class ConamerScraper:
    """
    Scraper for the CONAMER CNARTyS regulation catalog.

    Attempts to discover a structured JSON API first. Falls back to HTML
    scraping with BeautifulSoup when no API is available. Yields regulation
    records in paginated batches and supports dedup against an existing
    corpus of titles.
    """

    def __init__(self) -> None:
        self.session = self._setup_session()
        self.last_request_time: float = 0.0
        self._api_endpoint: Optional[str] = None

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
                "Accept": "application/json, text/html, */*",
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
    # API probing
    # ------------------------------------------------------------------

    def probe_api(self) -> Dict[str, Any]:
        """
        Try common API patterns on the CONAMER site to find structured data.

        Returns a findings dict with:
            - found (bool): Whether a usable API endpoint was discovered.
            - endpoint (str | None): The working API URL.
            - sample (dict | None): A sample response payload.
            - probed (list[str]): All paths attempted.
        """
        findings: Dict[str, Any] = {
            "found": False,
            "endpoint": None,
            "sample": None,
            "probed": [],
        }

        for path in _API_PROBE_PATHS:
            url = f"{BASE_URL}{path}"
            findings["probed"].append(url)
            logger.info("Probing API: %s", url)

            resp = self._get(url, headers={"Accept": "application/json"})
            if resp is None:
                continue

            content_type = resp.headers.get("Content-Type", "")
            if "json" not in content_type:
                continue

            try:
                data = resp.json()
            except (ValueError, json.JSONDecodeError):
                continue

            # Heuristic: a useful API returns a list or a dict with results.
            if isinstance(data, list) and len(data) > 0:
                findings.update(found=True, endpoint=url, sample=data[0])
                self._api_endpoint = url
                logger.info("Found API endpoint (list): %s", url)
                break

            if isinstance(data, dict):
                for key in ("results", "data", "items", "regulaciones", "records"):
                    if key in data and isinstance(data[key], list) and data[key]:
                        findings.update(found=True, endpoint=url, sample=data[key][0])
                        self._api_endpoint = url
                        logger.info("Found API endpoint (dict.%s): %s", key, url)
                        break
                if findings["found"]:
                    break

        if not findings["found"]:
            logger.info(
                "No JSON API found after probing %d paths", len(findings["probed"])
            )

        return findings

    # ------------------------------------------------------------------
    # Catalog scraping
    # ------------------------------------------------------------------

    def scrape_catalog(
        self,
        page_size: int = 50,
        max_pages: Optional[int] = None,
        resume_from_page: int = 0,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Paginated scraping of the CONAMER catalog.

        If an API endpoint was discovered via probe_api(), uses JSON
        pagination. Otherwise falls back to HTML scraping.

        Args:
            page_size: Number of items per page / batch.
            max_pages: Stop after this many pages (None = unlimited).
            resume_from_page: Skip pages before this index (0-based).

        Yields:
            Batches (lists) of regulation dicts.
        """
        if self._api_endpoint:
            yield from self._scrape_via_api(page_size, max_pages, resume_from_page)
        else:
            yield from self._scrape_via_html(page_size, max_pages, resume_from_page)

    def _scrape_via_api(
        self,
        page_size: int,
        max_pages: Optional[int],
        resume_from_page: int,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Paginate through a discovered JSON API endpoint."""
        page = resume_from_page
        empty_streak = 0

        while True:
            if max_pages is not None and (page - resume_from_page) >= max_pages:
                logger.info("Reached max_pages=%d, stopping.", max_pages)
                break

            url = f"{self._api_endpoint}?page={page}&page_size={page_size}"
            logger.info("Fetching API page %d: %s", page, url)

            resp = self._get(url)
            if resp is None:
                empty_streak += 1
                if empty_streak >= 3:
                    logger.warning("3 consecutive failures, stopping pagination.")
                    break
                page += 1
                continue

            try:
                data = resp.json()
            except (ValueError, json.JSONDecodeError):
                logger.warning("Invalid JSON on page %d", page)
                empty_streak += 1
                page += 1
                continue

            items = self._extract_items_from_json(data)
            if not items:
                empty_streak += 1
                if empty_streak >= 3:
                    logger.info("3 consecutive empty pages, assuming end of catalog.")
                    break
                page += 1
                continue

            empty_streak = 0
            batch = [self._normalize_item(item) for item in items]
            batch = [item for item in batch if item is not None]

            if batch:
                yield batch

            page += 1

    def _scrape_via_html(
        self,
        page_size: int,
        max_pages: Optional[int],
        resume_from_page: int,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Paginate through HTML pages of the CONAMER catalog."""
        page = resume_from_page
        empty_streak = 0

        while True:
            if max_pages is not None and (page - resume_from_page) >= max_pages:
                logger.info("Reached max_pages=%d, stopping.", max_pages)
                break

            url = f"{BASE_URL}/catalogo?page={page}"
            logger.info("Fetching HTML page %d: %s", page, url)

            resp = self._get(url)
            if resp is None:
                empty_streak += 1
                if empty_streak >= 3:
                    logger.warning("3 consecutive failures, stopping.")
                    break
                page += 1
                continue

            items = self._parse_html_catalog(resp.text)
            if not items:
                empty_streak += 1
                if empty_streak >= 3:
                    logger.info("3 consecutive empty pages, assuming end of catalog.")
                    break
                page += 1
                continue

            empty_streak = 0
            yield items
            page += 1

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_items_from_json(data: Any) -> List[Dict[str, Any]]:
        """Pull the item list out of a JSON response with unknown structure."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("results", "data", "items", "regulaciones", "records"):
                if key in data and isinstance(data[key], list):
                    return data[key]
        return []

    @staticmethod
    def _normalize_item(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize a raw API item into the canonical regulation schema.

        Returns None if the record cannot be salvaged.
        """
        name = (
            raw.get("nombre")
            or raw.get("name")
            or raw.get("titulo")
            or raw.get("title")
            or ""
        ).strip()
        if not name:
            return None

        return {
            "id": str(raw.get("id", "")),
            "name": name,
            "issuing_body": (
                raw.get("dependencia")
                or raw.get("issuing_body")
                or raw.get("organismo")
                or ""
            ).strip(),
            "date": str(raw.get("fecha_publicacion") or raw.get("date") or ""),
            "url": str(raw.get("url") or raw.get("enlace") or ""),
            "regulation_type": (
                raw.get("tipo") or raw.get("regulation_type") or ""
            ).strip(),
            "source": "conamer_cnartys",
        }

    def _parse_html_catalog(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse an HTML catalog page and extract regulation entries.

        Attempts multiple selector strategies to handle layout variations.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        items: List[Dict[str, Any]] = []

        # Strategy 1: table rows
        for row in soup.select("table tbody tr"):
            try:
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                name = cells[0].get_text(strip=True)
                if not name or len(name) < 5:
                    continue

                link = row.find("a", href=True)
                url = link["href"] if link else ""
                if url and not url.startswith("http"):
                    url = f"{BASE_URL}/{url.lstrip('/')}"

                items.append(
                    {
                        "id": "",
                        "name": name,
                        "issuing_body": (
                            cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        ),
                        "date": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                        "url": url,
                        "regulation_type": (
                            cells[3].get_text(strip=True) if len(cells) > 3 else ""
                        ),
                        "source": "conamer_cnartys",
                    }
                )
            except Exception:
                logger.debug("Failed to parse table row", exc_info=True)
                continue

        if items:
            return items

        # Strategy 2: card / list-item pattern
        for card in soup.select(".card, .list-item, .regulacion-item, article"):
            try:
                title_el = card.find(["h2", "h3", "h4", "a", "strong"])
                if not title_el:
                    continue
                name = title_el.get_text(strip=True)
                if not name or len(name) < 5:
                    continue

                link = card.find("a", href=True)
                url = link["href"] if link else ""
                if url and not url.startswith("http"):
                    url = f"{BASE_URL}/{url.lstrip('/')}"

                items.append(
                    {
                        "id": "",
                        "name": name,
                        "issuing_body": "",
                        "date": "",
                        "url": url,
                        "regulation_type": "",
                        "source": "conamer_cnartys",
                    }
                )
            except Exception:
                logger.debug("Failed to parse card element", exc_info=True)
                continue

        return items

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def dedup_against_existing(
        items: List[Dict[str, Any]],
        existing_titles: Set[str],
    ) -> List[Dict[str, Any]]:
        """
        Basic title-similarity dedup using normalised lowercase comparison.

        Strips accents, removes common stop words, and compares the
        resulting tokens. Items whose normalised title matches an entry
        in *existing_titles* (also normalised) are dropped.

        Args:
            items: Incoming regulation dicts.
            existing_titles: Set of titles already in the corpus.

        Returns:
            Filtered list with probable duplicates removed.
        """
        normalised_existing = {_normalise_title(t) for t in existing_titles}

        kept: List[Dict[str, Any]] = []
        duplicates = 0

        for item in items:
            norm = _normalise_title(item.get("name", ""))
            if not norm:
                continue
            if norm in normalised_existing:
                duplicates += 1
                continue
            kept.append(item)

        if duplicates:
            logger.info(
                "Dedup: dropped %d duplicates, kept %d of %d",
                duplicates,
                len(kept),
                len(items),
            )

        return kept

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def save_batch(
        items: List[Dict[str, Any]],
        output_dir: Path,
        batch_number: int,
    ) -> Path:
        """
        Save a batch of regulation dicts to a numbered JSON file.

        Args:
            items: Regulation dicts to persist.
            output_dir: Target directory (created if missing).
            batch_number: Batch sequence number.

        Returns:
            Path to the written file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"batch_{batch_number:04d}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        logger.info("Saved %d items to %s", len(items), path)
        return path

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        output_dir: str = "data/conamer",
        resume_from_page: int = 0,
        max_pages: Optional[int] = None,
        existing_titles: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run the full CONAMER scraping pipeline.

        1. Probe for a JSON API.
        2. Paginate through the catalog.
        3. Dedup each batch against *existing_titles* (if provided).
        4. Save batches to *output_dir*.

        Args:
            output_dir: Directory for batch JSON files.
            resume_from_page: Page index to resume from.
            max_pages: Maximum pages to scrape (None = all).
            existing_titles: Known titles for dedup.

        Returns:
            Summary dict with total_items, total_batches, output_dir.
        """
        out_path = Path(output_dir)
        existing = existing_titles or set()

        logger.info(
            "Starting CONAMER scraper (resume=%d, max_pages=%s)",
            resume_from_page,
            max_pages,
        )

        # Step 1: probe API
        probe_result = self.probe_api()
        logger.info("API probe result: found=%s", probe_result["found"])

        # Step 2: paginate and save
        total_items = 0
        batch_number = 0

        for batch in self.scrape_catalog(
            page_size=50,
            max_pages=max_pages,
            resume_from_page=resume_from_page,
        ):
            if existing:
                batch = self.dedup_against_existing(batch, existing)

            if not batch:
                continue

            self.save_batch(batch, out_path, batch_number)
            total_items += len(batch)
            batch_number += 1
            logger.info(
                "Progress: %d items across %d batches", total_items, batch_number
            )

        summary = {
            "total_items": total_items,
            "total_batches": batch_number,
            "output_dir": str(out_path),
            "api_found": probe_result["found"],
        }
        logger.info("CONAMER scraper complete: %s", summary)
        return summary


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _strip_accents(text: str) -> str:
    """Remove diacritical marks from *text*."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _normalise_title(title: str) -> str:
    """
    Normalise a title for dedup comparison.

    Lowercase, strip accents, remove punctuation, drop stop words,
    and collapse whitespace.
    """
    text = _strip_accents(title.lower())
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = [t for t in text.split() if t not in _STOP_WORDS]
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the CONAMER scraper."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Scrape the CONAMER CNARTyS regulation catalog.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/conamer",
        help="Directory to save batch JSON files (default: data/conamer).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of pages to scrape (default: all).",
    )
    parser.add_argument(
        "--resume-from",
        type=int,
        default=0,
        help="Page index to resume from (0-based, default: 0).",
    )
    parser.add_argument(
        "--existing-titles",
        type=str,
        default=None,
        help="Path to JSON file with list of existing law titles for dedup.",
    )
    args = parser.parse_args()

    existing: Set[str] = set()
    if args.existing_titles:
        titles_path = Path(args.existing_titles)
        if titles_path.exists():
            with open(titles_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and isinstance(data[0], dict):
                    existing = {entry.get("name", "") for entry in data}
                else:
                    existing = set(data)
            logger.info("Loaded %d existing titles for dedup", len(existing))

    scraper = ConamerScraper()
    result = scraper.run(
        output_dir=args.output_dir,
        resume_from_page=args.resume_from,
        max_pages=args.max_pages,
        existing_titles=existing,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
