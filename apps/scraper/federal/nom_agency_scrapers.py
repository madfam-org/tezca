"""
NOM Agency Scrapers -- Individual agency NOM catalogs

Scrapes NOMs directly from the websites of Mexico's main NOM-issuing agencies.
Each agency maintains its own catalog that may contain NOMs not yet indexed in
SINEC or the DOF archive, or that provides richer metadata (full text links,
amendment history, compliance guides).

Supported agencies:
  - SSA (Secretaria de Salud) -- normas.salud.gob.mx
  - SEMARNAT -- semarnat.gob.mx/gobmx/normas
  - SE (Secretaria de Economia) -- economia.gob.mx
  - STPS (Secretaria del Trabajo) -- stps.gob.mx
  - CONAGUA -- conagua.gob.mx

Usage:
    python -m apps.scraper.federal.nom_agency_scrapers
    python -m apps.scraper.federal.nom_agency_scrapers --agency ssa
    python -m apps.scraper.federal.nom_agency_scrapers --agency all --limit 100
    python -m apps.scraper.federal.nom_agency_scrapers --merge
    python -m apps.scraper.federal.nom_agency_scrapers --agency semarnat --checkpoint
"""

import json
import logging
import re
import time
import unicodedata
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Set

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_USER_AGENT = "Tezca/1.0 (+https://github.com/madfam-org/tezca)"
_REQUEST_TIMEOUT = 30  # seconds
_MIN_REQUEST_INTERVAL = 1.0  # 1 req/sec
_MAX_RETRIES = 3
_BACKOFF_FACTOR = 2

_DEFAULT_OUTPUT_DIR = "data/federal/noms"
_EXISTING_CATALOG_PATH = "data/federal/noms/discovered_noms.json"

# NOM identifier pattern
_NOM_PATTERN = re.compile(
    r"((?:NOM|PROY-NOM|NMX)-\d{3,4}-[A-Z0-9]+-\d{4})",
    re.IGNORECASE,
)

# Stop words for title normalization (deduplication)
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
        "que",
        "por",
        "para",
        "con",
        "una",
        "un",
        "se",
        "al",
        "su",
        "a",
        "o",
        "e",
    }
)


# ---------------------------------------------------------------------------
# Text normalization utilities
# ---------------------------------------------------------------------------


def normalize_title(title: str) -> str:
    """Normalize a NOM title for deduplication comparison.

    Strips accents, lowercases, removes stop words, collapses whitespace,
    and strips punctuation. Two NOMs with the same normalized title are
    considered duplicates even if their raw titles differ in formatting.
    """
    # Strip accents via NFKD decomposition
    nfkd = unicodedata.normalize("NFKD", title)
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))

    # Lowercase and strip punctuation
    text = ascii_text.lower()
    text = re.sub(r"[^\w\s]", " ", text)

    # Remove stop words
    words = [w for w in text.split() if w not in _STOP_WORDS]

    return " ".join(words).strip()


def _clean_text(raw: str) -> str:
    """Collapse whitespace and strip surrounding blanks."""
    return re.sub(r"\s+", " ", raw).strip()


def _extract_date(text: str) -> str:
    """Extract a date from free text, return ISO format or empty string."""
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


def _normalize_status(raw: str) -> str:
    """Normalize status string to canonical form."""
    lower = raw.strip().lower()
    if "vigente" in lower or "vigor" in lower:
        return "vigente"
    if "cancelad" in lower:
        return "cancelada"
    if "proyecto" in lower:
        return "en_proyecto"
    return lower


def _extract_agency_from_nom(nom_id: str) -> str:
    """Extract agency abbreviation from NOM identifier."""
    parts = nom_id.upper().split("-")
    if len(parts) >= 3:
        return parts[2]
    return ""


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class AgencyNOMScraper(ABC):
    """Base class for agency-specific NOM scrapers.

    Subclasses must implement:
    - ``agency_code``: Short identifier (e.g. "ssa", "semarnat").
    - ``agency_name``: Full Spanish name of the agency.
    - ``base_url``: Root URL of the agency's NOM catalog.
    - ``scrape()``: The main scraping logic.

    The base class provides:
    - HTTP session with retry/backoff
    - Rate limiting
    - Result persistence
    - Checkpoint support
    """

    agency_code: ClassVar[str] = ""
    agency_name: ClassVar[str] = ""
    base_url: ClassVar[str] = ""

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
            total=_MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"],
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
        """Rate-limited GET with error handling and exponential backoff."""
        for attempt in range(1, _MAX_RETRIES + 1):
            self._rate_limit()
            try:
                response = self.session.get(url, timeout=_REQUEST_TIMEOUT, **kwargs)
                response.raise_for_status()
                return response
            except requests.ConnectionError:
                logger.error(
                    "[%s] Connection failed (attempt %d/%d): %s",
                    self.agency_code,
                    attempt,
                    _MAX_RETRIES,
                    url,
                )
            except requests.Timeout:
                logger.error(
                    "[%s] Timeout (attempt %d/%d): %s",
                    self.agency_code,
                    attempt,
                    _MAX_RETRIES,
                    url,
                )
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response else "unknown"
                logger.warning(
                    "[%s] HTTP %s (attempt %d/%d): %s",
                    self.agency_code,
                    status,
                    attempt,
                    _MAX_RETRIES,
                    url,
                )
                if exc.response and 400 <= exc.response.status_code < 500:
                    if exc.response.status_code != 429:
                        return None
            except requests.RequestException as exc:
                logger.error("[%s] Request error: %s — %s", self.agency_code, url, exc)

            if attempt < _MAX_RETRIES:
                wait = _BACKOFF_FACTOR**attempt
                logger.info("[%s] Retrying in %ds...", self.agency_code, wait)
                time.sleep(wait)

        return None

    def _post(
        self, url: str, data: Dict[str, Any], **kwargs: Any
    ) -> Optional[requests.Response]:
        """Rate-limited POST with error handling and exponential backoff."""
        for attempt in range(1, _MAX_RETRIES + 1):
            self._rate_limit()
            try:
                response = self.session.post(
                    url, data=data, timeout=_REQUEST_TIMEOUT, **kwargs
                )
                response.raise_for_status()
                return response
            except requests.ConnectionError:
                logger.error(
                    "[%s] Connection failed POST (attempt %d/%d): %s",
                    self.agency_code,
                    attempt,
                    _MAX_RETRIES,
                    url,
                )
            except requests.Timeout:
                logger.error(
                    "[%s] Timeout POST (attempt %d/%d): %s",
                    self.agency_code,
                    attempt,
                    _MAX_RETRIES,
                    url,
                )
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response else "unknown"
                logger.warning(
                    "[%s] HTTP %s POST (attempt %d/%d): %s",
                    self.agency_code,
                    status,
                    attempt,
                    _MAX_RETRIES,
                    url,
                )
                if exc.response and 400 <= exc.response.status_code < 500:
                    if exc.response.status_code != 429:
                        return None
            except requests.RequestException as exc:
                logger.error("[%s] POST error: %s — %s", self.agency_code, url, exc)

            if attempt < _MAX_RETRIES:
                wait = _BACKOFF_FACTOR**attempt
                logger.info("[%s] Retrying in %ds...", self.agency_code, wait)
                time.sleep(wait)

        return None

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def scrape(self, limit: int = 0) -> List[Dict[str, Any]]:
        """Scrape NOMs from this agency's catalog.

        Args:
            limit: Maximum entries to collect (0 = unlimited).

        Returns:
            List of NOM metadata dicts with keys:
            nom_id, title, agency_code, agency_name, status,
            date_published, url, source.
        """

    # ------------------------------------------------------------------
    # Shared parsing helpers
    # ------------------------------------------------------------------

    def _build_nom_entry(
        self,
        nom_id: str,
        title: str,
        date_published: str = "",
        status: str = "vigente",
        url: str = "",
        dof_reference: str = "",
    ) -> Dict[str, Any]:
        """Build a standardized NOM entry dict."""
        return {
            "nom_id": nom_id.upper(),
            "title": _clean_text(title),
            "agency_code": self.agency_code,
            "agency_name": self.agency_name,
            "date_published": date_published,
            "status": _normalize_status(status) if status else "vigente",
            "url": url,
            "dof_reference": dof_reference,
            "source": f"agency_{self.agency_code}",
        }

    def _extract_noms_from_html(
        self,
        html: str,
        selectors: List[str],
        limit: int = 0,
    ) -> List[Dict[str, Any]]:
        """Generic NOM extraction from HTML using CSS selectors.

        Tries each selector in order and returns the first set of results
        that yields any matches. This handles layout variations across
        different agency sites.

        Args:
            html: Raw HTML content.
            selectors: CSS selectors to try in order.
            limit: Maximum entries (0 = unlimited).

        Returns:
            List of NOM dicts.
        """
        soup = BeautifulSoup(html, "html.parser")
        results: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()

        for selector in selectors:
            items = soup.select(selector)
            if not items:
                continue

            for item in items:
                try:
                    text = item.get_text(" ", strip=True)
                    nom_match = _NOM_PATTERN.search(text)
                    if not nom_match:
                        continue

                    nom_id = nom_match.group(1).upper()
                    if nom_id in seen_ids:
                        continue
                    seen_ids.add(nom_id)

                    # Extract link URL
                    url = ""
                    link = item.find("a", href=True)
                    if link:
                        href = link.get("href", "")
                        if href and not href.startswith("http"):
                            href = f"{self.base_url.rstrip('/')}/{href.lstrip('/')}"
                        url = href

                    # Extract date and status from text
                    date_str = _extract_date(text)
                    status = "vigente"
                    if "cancelad" in text.lower():
                        status = "cancelada"
                    elif "proyecto" in text.lower():
                        status = "en_proyecto"

                    # DOF reference
                    dof_ref = ""
                    dof_match = re.search(
                        r"DOF[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})", text
                    )
                    if dof_match:
                        dof_ref = dof_match.group(0)

                    entry = self._build_nom_entry(
                        nom_id=nom_id,
                        title=_clean_text(text),
                        date_published=date_str,
                        status=status,
                        url=url,
                        dof_reference=dof_ref,
                    )
                    results.append(entry)

                    if limit and len(results) >= limit:
                        return results
                except Exception:
                    logger.debug(
                        "[%s] Failed to parse item", self.agency_code, exc_info=True
                    )
                    continue

            # If we found results with this selector, stop trying others
            if results:
                break

        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_results(
        self, noms: List[Dict[str, Any]], output_dir: str = _DEFAULT_OUTPUT_DIR
    ) -> Path:
        """Save agency results to JSON file.

        Returns the output file path.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        output_file = out_path / f"{self.agency_code}_noms.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(noms, f, indent=2, ensure_ascii=False)
        logger.info(
            "[%s] Saved %d NOMs to %s", self.agency_code, len(noms), output_file
        )
        return output_file

    def save_checkpoint(
        self, noms: List[Dict[str, Any]], output_dir: str = _DEFAULT_OUTPUT_DIR
    ) -> None:
        """Save a checkpoint for resumption."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        checkpoint_file = out_path / f"{self.agency_code}_checkpoint.json"
        checkpoint = {
            "agency_code": self.agency_code,
            "total": len(noms),
            "last_nom_id": noms[-1]["nom_id"] if noms else "",
            "noms": noms,
        }
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)
        logger.info("[%s] Checkpoint saved: %d NOMs", self.agency_code, len(noms))

    def load_checkpoint(
        self, output_dir: str = _DEFAULT_OUTPUT_DIR
    ) -> List[Dict[str, Any]]:
        """Load a previous checkpoint.

        Returns list of previously collected NOMs, or empty list.
        """
        checkpoint_file = Path(output_dir) / f"{self.agency_code}_checkpoint.json"
        if not checkpoint_file.exists():
            return []
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            noms = data.get("noms", [])
            logger.info("[%s] Loaded checkpoint: %d NOMs", self.agency_code, len(noms))
            return noms
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("[%s] Failed to load checkpoint: %s", self.agency_code, exc)
            return []


# ---------------------------------------------------------------------------
# SSA Scraper -- Secretaria de Salud
# ---------------------------------------------------------------------------


class SSAScraper(AgencyNOMScraper):
    """Scrapes NOMs from the Secretaria de Salud (SSA).

    Source: normas.salud.gob.mx -- The SSA NOM catalog includes health-related
    standards covering hospital safety, food handling, disease surveillance,
    medical devices, and pharmaceutical products. SSA NOMs use numbering
    suffixes SSA1, SSA2, SSA3 for sub-series.
    """

    agency_code = "ssa"
    agency_name = "Secretaria de Salud"
    base_url = "https://normas.salud.gob.mx"

    # Known catalog pages
    _CATALOG_PATHS = [
        "/normas/normas-oficiales-mexicanas",
        "/normas/vigentes",
        "/normas",
    ]

    def scrape(self, limit: int = 0) -> List[Dict[str, Any]]:
        """Scrape SSA NOM catalog."""
        logger.info("[ssa] Starting SSA NOM scraper (limit=%d)", limit)

        all_noms: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()

        for path in self._CATALOG_PATHS:
            url = f"{self.base_url}{path}"
            logger.info("[ssa] Trying catalog URL: %s", url)

            resp = self._get(url)
            if resp is None:
                logger.warning("[ssa] Failed to load: %s", url)
                continue

            noms = self._extract_noms_from_html(
                resp.text,
                selectors=[
                    "table tbody tr",
                    ".views-row",
                    ".node--type-norma",
                    "article",
                    ".field-content",
                    "li",
                ],
                limit=limit,
            )

            for nom in noms:
                if nom["nom_id"] not in seen_ids:
                    seen_ids.add(nom["nom_id"])
                    all_noms.append(nom)

            if all_noms:
                logger.info("[ssa] Found %d NOMs from %s", len(all_noms), url)
                break  # Got results from this path, no need to try others

        # Paginate if there are pagination links
        if all_noms and resp:
            all_noms = self._paginate(resp.text, all_noms, seen_ids, limit)

        if not all_noms:
            logger.warning("[ssa] No NOMs found. SSA site structure may have changed.")

        logger.info("[ssa] Scrape complete: %d NOMs", len(all_noms))
        return all_noms

    def _paginate(
        self,
        first_page_html: str,
        collected: List[Dict[str, Any]],
        seen_ids: Set[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Follow pagination links to collect more results."""
        soup = BeautifulSoup(first_page_html, "html.parser")

        # Common Drupal/WordPress pagination patterns
        next_links = soup.select(
            "a[rel='next'], .pager__item--next a, .next a, a.page-link"
        )
        page = 2

        for next_link in next_links:
            if limit and len(collected) >= limit:
                break

            href = next_link.get("href", "")
            if not href:
                continue

            if not href.startswith("http"):
                href = f"{self.base_url}/{href.lstrip('/')}"

            logger.info("[ssa] Following pagination to page %d: %s", page, href)
            resp = self._get(href)
            if resp is None:
                break

            noms = self._extract_noms_from_html(
                resp.text,
                selectors=["table tbody tr", ".views-row", "article", "li"],
                limit=limit - len(collected) if limit else 0,
            )

            new_count = 0
            for nom in noms:
                if nom["nom_id"] not in seen_ids:
                    seen_ids.add(nom["nom_id"])
                    collected.append(nom)
                    new_count += 1

            if new_count == 0:
                break

            # Look for next page link in the new page
            soup = BeautifulSoup(resp.text, "html.parser")
            next_links = soup.select("a[rel='next'], .pager__item--next a, .next a")
            page += 1

            if not next_links:
                break

        return collected


# ---------------------------------------------------------------------------
# SEMARNAT Scraper -- Secretaria de Medio Ambiente
# ---------------------------------------------------------------------------


class SEMARNATScraper(AgencyNOMScraper):
    """Scrapes NOMs from SEMARNAT (environmental standards).

    Source: semarnat.gob.mx/gobmx/normas -- Environmental protection standards
    covering air quality, water quality, soil contamination, waste management,
    noise limits, and species protection (NOM-059-SEMARNAT is the endangered
    species list).
    """

    agency_code = "semarnat"
    agency_name = "Secretaria de Medio Ambiente y Recursos Naturales"
    base_url = "https://www.semarnat.gob.mx"

    _CATALOG_PATHS = [
        "/gobmx/normas",
        "/gobmx/normas-oficiales-mexicanas",
        "/normas-oficiales-mexicanas-vigentes",
    ]

    def scrape(self, limit: int = 0) -> List[Dict[str, Any]]:
        """Scrape SEMARNAT NOM catalog."""
        logger.info("[semarnat] Starting SEMARNAT NOM scraper (limit=%d)", limit)

        all_noms: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()

        for path in self._CATALOG_PATHS:
            url = f"{self.base_url}{path}"
            logger.info("[semarnat] Trying catalog URL: %s", url)

            resp = self._get(url)
            if resp is None:
                logger.warning("[semarnat] Failed to load: %s", url)
                continue

            noms = self._extract_noms_from_html(
                resp.text,
                selectors=[
                    "table tbody tr",
                    ".field-item table tr",
                    ".article-body table tr",
                    ".node-content table tr",
                    "article table tr",
                    ".views-row",
                    "li",
                ],
                limit=limit,
            )

            for nom in noms:
                if nom["nom_id"] not in seen_ids:
                    seen_ids.add(nom["nom_id"])
                    all_noms.append(nom)

            if all_noms:
                logger.info("[semarnat] Found %d NOMs from %s", len(all_noms), url)
                break

        if not all_noms:
            logger.warning(
                "[semarnat] No NOMs found. SEMARNAT site structure may have changed."
            )

        logger.info("[semarnat] Scrape complete: %d NOMs", len(all_noms))
        return all_noms


# ---------------------------------------------------------------------------
# SE Scraper -- Secretaria de Economia
# ---------------------------------------------------------------------------


class SEScraper(AgencyNOMScraper):
    """Scrapes NOMs from the Secretaria de Economia (SE).

    Source: economia.gob.mx -- SE (formerly SCFI) maintains standards for
    commercial products, labeling requirements, measurement units, and
    consumer protection.
    """

    agency_code = "se"
    agency_name = "Secretaria de Economia"
    base_url = "https://www.economia.gob.mx"

    _CATALOG_PATHS = [
        "/normas-oficiales-mexicanas",
        "/gobmx/normas",
        "/normatividad/normas-oficiales-mexicanas",
    ]

    def scrape(self, limit: int = 0) -> List[Dict[str, Any]]:
        """Scrape SE NOM catalog."""
        logger.info("[se] Starting SE NOM scraper (limit=%d)", limit)

        all_noms: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()

        for path in self._CATALOG_PATHS:
            url = f"{self.base_url}{path}"
            logger.info("[se] Trying catalog URL: %s", url)

            resp = self._get(url)
            if resp is None:
                logger.warning("[se] Failed to load: %s", url)
                continue

            noms = self._extract_noms_from_html(
                resp.text,
                selectors=[
                    "table tbody tr",
                    ".field-item table tr",
                    ".article-body table tr",
                    ".views-row",
                    "article",
                    "li",
                ],
                limit=limit,
            )

            for nom in noms:
                if nom["nom_id"] not in seen_ids:
                    seen_ids.add(nom["nom_id"])
                    all_noms.append(nom)

            if all_noms:
                logger.info("[se] Found %d NOMs from %s", len(all_noms), url)
                break

        if not all_noms:
            logger.warning("[se] No NOMs found. SE site structure may have changed.")

        logger.info("[se] Scrape complete: %d NOMs", len(all_noms))
        return all_noms


# ---------------------------------------------------------------------------
# STPS Scraper -- Secretaria del Trabajo
# ---------------------------------------------------------------------------


class STPSScraper(AgencyNOMScraper):
    """Scrapes NOMs from the Secretaria del Trabajo (STPS).

    Source: stps.gob.mx/bp/secciones/conoce/marco_juridico/noms.html --
    Occupational health and safety standards. STPS NOMs cover workplace
    hazards, fire safety, electrical safety, chemical handling, PPE, and
    ergonomics. There are approximately 44 STPS NOMs (NOM-001 through
    NOM-036).
    """

    agency_code = "stps"
    agency_name = "Secretaria del Trabajo y Prevision Social"
    base_url = "https://www.stps.gob.mx"

    _CATALOG_URL = (
        "https://www.stps.gob.mx/bp/secciones/conoce/marco_juridico/noms.html"
    )

    def scrape(self, limit: int = 0) -> List[Dict[str, Any]]:
        """Scrape STPS NOM catalog."""
        logger.info("[stps] Starting STPS NOM scraper (limit=%d)", limit)

        resp = self._get(self._CATALOG_URL)
        if resp is None:
            # Try alternate paths
            for alt_path in [
                "/bp/secciones/conoce/marco_juridico/normas_oficiales.html",
                "/gobmx/normas",
            ]:
                alt_url = f"{self.base_url}{alt_path}"
                logger.info("[stps] Trying alternate URL: %s", alt_url)
                resp = self._get(alt_url)
                if resp is not None:
                    break

        if resp is None:
            logger.warning("[stps] Failed to load STPS NOM catalog. Site may be down.")
            return []

        noms = self._extract_noms_from_html(
            resp.text,
            selectors=[
                "table tbody tr",
                "table tr",
                ".contenido table tr",
                ".article-body table tr",
                "li",
                "p",
            ],
            limit=limit,
        )

        if not noms:
            # STPS page sometimes uses plain text with NOM references
            noms = self._parse_stps_text(resp.text, limit)

        logger.info("[stps] Scrape complete: %d NOMs", len(noms))
        return noms

    def _parse_stps_text(self, html: str, limit: int = 0) -> List[Dict[str, Any]]:
        """Parse STPS page by scanning all text for NOM patterns.

        The STPS page may list NOMs in plain paragraphs or formatted
        lists rather than tables.
        """
        soup = BeautifulSoup(html, "html.parser")
        results: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()

        # Get all text content
        body = soup.find("body")
        if not body:
            return results

        # Split into paragraphs/sections
        for element in body.find_all(["p", "li", "td", "div", "span"]):
            text = element.get_text(" ", strip=True)
            if not text:
                continue

            for nom_match in _NOM_PATTERN.finditer(text):
                nom_id = nom_match.group(1).upper()
                if nom_id in seen_ids:
                    continue
                seen_ids.add(nom_id)

                # Only keep STPS NOMs
                agency_abbr = _extract_agency_from_nom(nom_id)
                if agency_abbr not in ("STPS",):
                    continue

                # Extract link
                url = ""
                link = element.find("a", href=True)
                if link:
                    href = link.get("href", "")
                    if href and not href.startswith("http"):
                        href = f"{self.base_url}/{href.lstrip('/')}"
                    url = href

                entry = self._build_nom_entry(
                    nom_id=nom_id,
                    title=_clean_text(text),
                    date_published=_extract_date(text),
                    url=url,
                )
                results.append(entry)

                if limit and len(results) >= limit:
                    return results

        return results


# ---------------------------------------------------------------------------
# CONAGUA Scraper -- Comision Nacional del Agua
# ---------------------------------------------------------------------------


class CONAGUAScraper(AgencyNOMScraper):
    """Scrapes NOMs from CONAGUA (water standards).

    Source: conagua.gob.mx -- CONAGUA maintains standards for water quality,
    wastewater discharge, water infrastructure, and measurement of water
    resources. CONAGUA NOMs use the CNA and CONAGUA suffixes.
    """

    agency_code = "conagua"
    agency_name = "Comision Nacional del Agua"
    base_url = "https://www.gob.mx/conagua"

    _CATALOG_PATHS = [
        "/documentos/normas-oficiales-mexicanas-702",
        "/acciones-y-programas/normas-oficiales-mexicanas",
        "/normas-oficiales-mexicanas",
    ]

    def scrape(self, limit: int = 0) -> List[Dict[str, Any]]:
        """Scrape CONAGUA NOM catalog."""
        logger.info("[conagua] Starting CONAGUA NOM scraper (limit=%d)", limit)

        all_noms: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()

        for path in self._CATALOG_PATHS:
            url = f"{self.base_url}{path}"
            logger.info("[conagua] Trying catalog URL: %s", url)

            resp = self._get(url)
            if resp is None:
                logger.warning("[conagua] Failed to load: %s", url)
                continue

            noms = self._extract_noms_from_html(
                resp.text,
                selectors=[
                    "table tbody tr",
                    ".article-body table tr",
                    ".documentos-702 li",
                    ".document-list li",
                    "article",
                    ".views-row",
                    "li",
                ],
                limit=limit,
            )

            for nom in noms:
                if nom["nom_id"] not in seen_ids:
                    seen_ids.add(nom["nom_id"])
                    all_noms.append(nom)

            if all_noms:
                logger.info("[conagua] Found %d NOMs from %s", len(all_noms), url)
                break

        # Also try gob.mx API endpoint for CONAGUA documents
        if not all_noms:
            all_noms = self._try_gobmx_api(limit)

        if not all_noms:
            logger.warning(
                "[conagua] No NOMs found. CONAGUA site structure may have changed."
            )

        logger.info("[conagua] Scrape complete: %d NOMs", len(all_noms))
        return all_noms

    def _try_gobmx_api(self, limit: int = 0) -> List[Dict[str, Any]]:
        """Try the gob.mx JSON API for CONAGUA documents.

        The gob.mx portal sometimes provides a JSON API endpoint for
        document listings.
        """
        api_url = "https://www.gob.mx/cms/uploads/attachment/file/conagua/normas"
        logger.info("[conagua] Trying gob.mx API: %s", api_url)

        resp = self._get(
            "https://www.gob.mx/busqueda",
            params={
                "utf8": "true",
                "site": "conagua",
                "q": "NOM norma oficial",
                "format": "json",
            },
        )
        if resp is None:
            return []

        try:
            data = resp.json()
        except (ValueError, json.JSONDecodeError):
            logger.debug("[conagua] Non-JSON response from gob.mx API")
            return []

        results_list = data.get("results", [])
        noms: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()

        for item in results_list:
            title = item.get("title", "")
            description = item.get("description", "")
            text = f"{title} {description}"

            nom_match = _NOM_PATTERN.search(text)
            if not nom_match:
                continue

            nom_id = nom_match.group(1).upper()
            if nom_id in seen_ids:
                continue
            seen_ids.add(nom_id)

            entry = self._build_nom_entry(
                nom_id=nom_id,
                title=_clean_text(title or description),
                date_published=item.get("published_at", "")[:10],
                url=item.get("url", ""),
            )
            noms.append(entry)

            if limit and len(noms) >= limit:
                break

        return noms


# ---------------------------------------------------------------------------
# Agency registry
# ---------------------------------------------------------------------------

AGENCY_SCRAPERS: Dict[str, type] = {
    "ssa": SSAScraper,
    "semarnat": SEMARNATScraper,
    "se": SEScraper,
    "stps": STPSScraper,
    "conagua": CONAGUAScraper,
}


# ---------------------------------------------------------------------------
# Merge / deduplication
# ---------------------------------------------------------------------------


def merge_with_existing_catalog(
    new_noms: List[Dict[str, Any]],
    existing_catalog_path: str = _EXISTING_CATALOG_PATH,
) -> Dict[str, Any]:
    """Merge newly scraped NOMs with the existing NOM catalog.

    Uses title normalization for fuzzy deduplication: two entries are
    considered duplicates if they share the same NOM identifier OR if
    their normalized titles match.

    Args:
        new_noms: Newly scraped NOM entries.
        existing_catalog_path: Path to the existing discovered_noms.json.

    Returns:
        Summary dict with merge statistics.
    """
    catalog_path = Path(existing_catalog_path)

    # Load existing catalog
    existing_noms: List[Dict[str, Any]] = []
    if catalog_path.exists():
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                existing_noms = json.load(f)
            logger.info(
                "Loaded existing catalog: %d entries from %s",
                len(existing_noms),
                catalog_path,
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load existing catalog: %s", exc)
    else:
        logger.info("No existing catalog at %s, creating new.", catalog_path)

    # Build dedup indices from existing catalog
    existing_ids: Set[str] = set()
    existing_titles: Set[str] = set()

    for nom in existing_noms:
        # Index by nom_number (DOF scraper field) or nom_id (agency scraper field)
        nom_key = nom.get("nom_number") or nom.get("nom_id", "")
        if nom_key:
            existing_ids.add(nom_key.upper())

        # Index by normalized title
        title = nom.get("name") or nom.get("title", "")
        if title:
            existing_titles.add(normalize_title(title))

    # Merge new entries
    added = 0
    skipped_id = 0
    skipped_title = 0

    for nom in new_noms:
        nom_id = nom.get("nom_id", "").upper()

        # Check ID dedup
        if nom_id and nom_id in existing_ids:
            skipped_id += 1
            continue

        # Check title dedup
        title = nom.get("title", "")
        norm_title = normalize_title(title) if title else ""
        if norm_title and norm_title in existing_titles:
            skipped_title += 1
            continue

        # Add new entry (convert to DOF catalog format for compatibility)
        merged_entry = {
            "id": nom_id.lower().replace("-", "_") if nom_id else "",
            "name": title,
            "nom_number": nom_id,
            "secretaria": nom.get("agency_name", ""),
            "date_published": nom.get("date_published", ""),
            "url": nom.get("url", ""),
            "status": nom.get("status", "vigente"),
            "source": nom.get("source", "agency"),
        }
        existing_noms.append(merged_entry)
        existing_ids.add(nom_id)
        if norm_title:
            existing_titles.add(norm_title)
        added += 1

    # Save merged catalog
    if added > 0:
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump(existing_noms, f, indent=2, ensure_ascii=False)
        logger.info("Saved merged catalog: %d total entries", len(existing_noms))

    summary = {
        "existing_count": len(existing_noms) - added,
        "new_entries": len(new_noms),
        "added": added,
        "skipped_duplicate_id": skipped_id,
        "skipped_duplicate_title": skipped_title,
        "total_after_merge": len(existing_noms),
        "catalog_path": str(catalog_path),
    }
    logger.info("Merge complete: %s", summary)
    return summary


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_agency_scrapers(
    agency: str = "all",
    limit: int = 0,
    output_dir: str = _DEFAULT_OUTPUT_DIR,
    merge: bool = False,
    use_checkpoint: bool = False,
) -> Dict[str, Any]:
    """Run one or all agency scrapers.

    Args:
        agency: Agency code ("ssa", "semarnat", "se", "stps", "conagua", "all").
        limit: Maximum entries per agency (0 = unlimited).
        output_dir: Directory for output files.
        merge: Whether to merge results with the existing NOM catalog.
        use_checkpoint: Resume from checkpoint if available.

    Returns:
        Summary dict with per-agency results and merge statistics.
    """
    if agency == "all":
        agencies_to_run = list(AGENCY_SCRAPERS.keys())
    else:
        agency_lower = agency.lower()
        if agency_lower not in AGENCY_SCRAPERS:
            raise ValueError(
                f"Unknown agency '{agency}'. "
                f"Valid choices: {', '.join(AGENCY_SCRAPERS.keys())}, all"
            )
        agencies_to_run = [agency_lower]

    all_results: Dict[str, Any] = {}
    all_noms: List[Dict[str, Any]] = []

    for code in agencies_to_run:
        scraper_class = AGENCY_SCRAPERS[code]
        scraper = scraper_class()

        logger.info("=" * 60)
        logger.info("Running %s scraper (%s)", code.upper(), scraper.agency_name)
        logger.info("=" * 60)

        # Load checkpoint if requested
        existing = []
        if use_checkpoint:
            existing = scraper.load_checkpoint(output_dir)

        try:
            noms = scraper.scrape(limit=limit)
        except Exception:
            logger.error("Scraper %s failed with unexpected error", code, exc_info=True)
            all_results[code] = {"error": "scraper_failed", "count": 0}
            continue

        # Merge with checkpoint
        if existing:
            seen_ids = {n["nom_id"] for n in existing}
            for nom in noms:
                if nom["nom_id"] not in seen_ids:
                    existing.append(nom)
                    seen_ids.add(nom["nom_id"])
            noms = existing

        # Save per-agency results
        output_file = scraper.save_results(noms, output_dir)
        scraper.save_checkpoint(noms, output_dir)

        all_results[code] = {
            "count": len(noms),
            "output_file": str(output_file),
        }
        all_noms.extend(noms)

    # Merge with existing catalog if requested
    merge_summary = None
    if merge and all_noms:
        merge_summary = merge_with_existing_catalog(all_noms)

    summary = {
        "agencies_run": agencies_to_run,
        "results": all_results,
        "total_noms_scraped": len(all_noms),
        "merge_summary": merge_summary,
    }
    logger.info("Agency scraper run complete: %s", summary)
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for agency NOM scrapers."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Scrape NOMs from individual agency catalogs.",
    )
    parser.add_argument(
        "--agency",
        choices=["ssa", "semarnat", "se", "stps", "conagua", "all"],
        default="all",
        help="Agency to scrape (default: all).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum NOMs per agency (0 = unlimited).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=_DEFAULT_OUTPUT_DIR,
        help=f"Directory to save results (default: {_DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge results with existing NOM catalog for deduplication.",
    )
    parser.add_argument(
        "--checkpoint",
        action="store_true",
        help="Resume from a previous checkpoint.",
    )
    args = parser.parse_args()

    result = run_agency_scrapers(
        agency=args.agency,
        limit=args.limit,
        output_dir=args.output_dir,
        merge=args.merge,
        use_checkpoint=args.checkpoint,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
