"""
SINEC Scraper -- Sistema Nacional de Informacion sobre Normalizacion

Scrapes Mexico's national NOM (Normas Oficiales Mexicanas) information system
at sinec.gob.mx. SINEC is maintained by the Secretaria de Economia and serves
as the authoritative catalog of all official Mexican standards.

The catalog provides:
- NOM identifier and full title
- Issuing agency (secretaria/dependencia)
- DOF publication date and status (vigente/cancelada/en proyecto)
- Cross-references to DOF entries

Usage:
    python -m apps.scraper.federal.sinec_scraper
    python -m apps.scraper.federal.sinec_scraper --limit 100
    python -m apps.scraper.federal.sinec_scraper --agency SSA
    python -m apps.scraper.federal.sinec_scraper --status vigente
    python -m apps.scraper.federal.sinec_scraper --checkpoint
"""

import json
import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SINEC_BASE_URL = "https://sinec.gob.mx"
SINEC_SEARCH_URL = f"{SINEC_BASE_URL}/SINEC/Vista/Normalizacion/BuscadorNormas.xhtml"
_USER_AGENT = "Tezca/1.0 (+https://github.com/madfam-org/tezca)"
_REQUEST_TIMEOUT = 30  # seconds
_MIN_REQUEST_INTERVAL = 1.0  # 1 req/sec
_MAX_RETRIES = 3
_BACKOFF_FACTOR = 2  # exponential backoff base

# Output directory
_DEFAULT_OUTPUT_DIR = "data/federal/noms"
_OUTPUT_FILENAME = "sinec_noms.json"
_CHECKPOINT_FILENAME = "sinec_checkpoint.json"

# NOM identifier pattern: NOM-001-SSA1-2010
_NOM_PATTERN = re.compile(
    r"((?:NOM|PROY-NOM|NMX)-\d{3,4}-[A-Z0-9]+-\d{4})",
    re.IGNORECASE,
)

# Status normalization
_STATUS_MAP = {
    "vigente": "vigente",
    "en vigor": "vigente",
    "cancelada": "cancelada",
    "cancelado": "cancelada",
    "en proyecto": "en_proyecto",
    "proyecto": "en_proyecto",
}

# Agency abbreviation mapping (reuses nom_scraper convention)
_AGENCY_ABBREVIATIONS: Dict[str, str] = {
    "SSA": "Secretaria de Salud",
    "SEMARNAT": "Secretaria de Medio Ambiente y Recursos Naturales",
    "STPS": "Secretaria del Trabajo y Prevision Social",
    "SE": "Secretaria de Economia",
    "SCFI": "Secretaria de Comercio y Fomento Industrial",
    "SCT": "Secretaria de Comunicaciones y Transportes",
    "SICT": "Secretaria de Infraestructura, Comunicaciones y Transportes",
    "CONAGUA": "Comision Nacional del Agua",
    "CNA": "Comision Nacional del Agua",
    "SENER": "Secretaria de Energia",
    "SAGARPA": "Secretaria de Agricultura",
    "SADER": "Secretaria de Agricultura y Desarrollo Rural",
    "SEDATU": "Secretaria de Desarrollo Agrario, Territorial y Urbano",
    "COFEPRIS": "Comision Federal para la Proteccion contra Riesgos Sanitarios",
}


# ---------------------------------------------------------------------------
# Text normalization utilities
# ---------------------------------------------------------------------------


def _normalize_text(text: str) -> str:
    """Strip accents, collapse whitespace, lowercase."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def _clean_text(raw: str) -> str:
    """Collapse whitespace and strip surrounding blanks."""
    return re.sub(r"\s+", " ", raw).strip()


def _normalize_status(raw_status: str) -> str:
    """Normalize a raw status string to canonical form."""
    normalized = _normalize_text(raw_status)
    for key, value in _STATUS_MAP.items():
        if key in normalized:
            return value
    return raw_status.strip().lower()


def _extract_agency_from_nom(nom_id: str) -> str:
    """Extract the agency abbreviation from a NOM identifier.

    NOM-001-SSA1-2010 -> SSA1
    NOM-059-SEMARNAT-2010 -> SEMARNAT
    """
    parts = nom_id.upper().split("-")
    if len(parts) >= 3:
        return parts[2]
    return ""


def _resolve_agency_name(abbr: str) -> str:
    """Resolve an agency abbreviation to its full name."""
    upper = abbr.upper()
    if upper in _AGENCY_ABBREVIATIONS:
        return _AGENCY_ABBREVIATIONS[upper]
    # Try prefix match (e.g., SSA1 -> SSA)
    for key, value in _AGENCY_ABBREVIATIONS.items():
        if upper.startswith(key) or key.startswith(upper):
            return value
    return abbr


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


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class SinecScraper:
    """Scrapes the SINEC NOM catalog at sinec.gob.mx.

    SINEC is a JSF (JavaServer Faces) application, so form submissions
    carry a javax.faces.ViewState token and use POST-based pagination.
    The scraper handles this by:
    1. Loading the search page to obtain the ViewState token
    2. Submitting search queries via POST
    3. Paginating through results via POST with ViewState continuity
    """

    def __init__(self) -> None:
        self.session = self._setup_session()
        self.last_request_time: float = 0.0
        self._view_state: Optional[str] = None

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
                    "Connection failed (attempt %d/%d): %s",
                    attempt,
                    _MAX_RETRIES,
                    url,
                )
            except requests.Timeout:
                logger.error(
                    "Request timed out (attempt %d/%d): %s",
                    attempt,
                    _MAX_RETRIES,
                    url,
                )
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response else "unknown"
                logger.warning(
                    "HTTP %s (attempt %d/%d): %s", status, attempt, _MAX_RETRIES, url
                )
                # Do not retry client errors (4xx) except 429
                if exc.response and 400 <= exc.response.status_code < 500:
                    if exc.response.status_code != 429:
                        return None
            except requests.RequestException as exc:
                logger.error("Request error for %s: %s", url, exc)

            if attempt < _MAX_RETRIES:
                wait = _BACKOFF_FACTOR**attempt
                logger.info("Retrying in %ds...", wait)
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
                    "Connection failed POST (attempt %d/%d): %s",
                    attempt,
                    _MAX_RETRIES,
                    url,
                )
            except requests.Timeout:
                logger.error(
                    "Request timed out POST (attempt %d/%d): %s",
                    attempt,
                    _MAX_RETRIES,
                    url,
                )
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response else "unknown"
                logger.warning(
                    "HTTP %s POST (attempt %d/%d): %s",
                    status,
                    attempt,
                    _MAX_RETRIES,
                    url,
                )
                if exc.response and 400 <= exc.response.status_code < 500:
                    if exc.response.status_code != 429:
                        return None
            except requests.RequestException as exc:
                logger.error("Request error for POST %s: %s", url, exc)

            if attempt < _MAX_RETRIES:
                wait = _BACKOFF_FACTOR**attempt
                logger.info("Retrying in %ds...", wait)
                time.sleep(wait)

        return None

    # ------------------------------------------------------------------
    # ViewState handling (JSF applications)
    # ------------------------------------------------------------------

    def _extract_view_state(self, html: str) -> Optional[str]:
        """Extract javax.faces.ViewState from a JSF page."""
        soup = BeautifulSoup(html, "html.parser")
        vs_input = soup.find("input", {"name": "javax.faces.ViewState"})
        if vs_input:
            value = vs_input.get("value", "")
            if value:
                self._view_state = str(value)
                return self._view_state

        # Fallback: regex extraction
        match = re.search(r'javax\.faces\.ViewState["\s]*value="([^"]+)"', html)
        if match:
            self._view_state = match.group(1)
            return self._view_state

        return None

    def _initialize_search_page(self) -> bool:
        """Load the SINEC search page and capture the initial ViewState.

        Returns True if the search page was loaded successfully.
        """
        logger.info("Initializing SINEC search page...")
        resp = self._get(SINEC_SEARCH_URL)
        if resp is None:
            logger.error("Failed to load SINEC search page")
            return False

        vs = self._extract_view_state(resp.text)
        if vs:
            logger.info("ViewState captured (length=%d)", len(vs))
            return True

        # If there is no ViewState, SINEC may not be JSF-based at this URL.
        # Proceed anyway -- parsing will attempt both JSF and plain HTML.
        logger.warning("No ViewState found; SINEC page may be plain HTML")
        return True

    # ------------------------------------------------------------------
    # Search and parse
    # ------------------------------------------------------------------

    def search_catalog(
        self,
        query: str = "NOM-",
        agency: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 0,
    ) -> List[Dict[str, Any]]:
        """Search the SINEC catalog and collect NOM entries.

        Args:
            query: Search term (default "NOM-").
            agency: Filter by agency abbreviation (e.g. "SSA").
            status_filter: Filter by status ("vigente", "cancelada").
            limit: Maximum entries to collect (0 = unlimited).

        Returns:
            List of NOM metadata dicts.
        """
        if not self._initialize_search_page():
            logger.error("Cannot proceed without SINEC search page")
            return []

        if agency:
            query = f"NOM- {agency.upper()}"

        logger.info(
            "Searching SINEC catalog: query='%s', agency=%s, status=%s, limit=%d",
            query,
            agency,
            status_filter,
            limit,
        )

        all_noms: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()
        page = 1
        consecutive_empty = 0
        max_consecutive_empty = 3  # stop after 3 pages with no new results

        while True:
            if limit and len(all_noms) >= limit:
                break

            logger.info("Fetching SINEC results page %d", page)

            # Build POST data for JSF form submission
            form_data: Dict[str, Any] = {
                "javax.faces.partial.ajax": "true",
                "javax.faces.source": "formBusqueda:btnBuscar",
                "javax.faces.partial.execute": "@all",
                "javax.faces.partial.render": "@all",
                "formBusqueda": "formBusqueda",
                "formBusqueda:txtBusqueda": query,
                "formBusqueda:btnBuscar": "formBusqueda:btnBuscar",
            }

            if self._view_state:
                form_data["javax.faces.ViewState"] = self._view_state

            # For pagination, modify the source component
            if page > 1:
                form_data["formBusqueda:tblResultados:page"] = str(page)
                form_data["javax.faces.source"] = "formBusqueda:tblResultados"

            resp = self._post(SINEC_SEARCH_URL, data=form_data)
            if resp is None:
                logger.warning("Failed to fetch SINEC page %d, stopping.", page)
                break

            # Update ViewState from response
            self._extract_view_state(resp.text)

            noms = self._parse_sinec_results(resp.text)
            if not noms:
                # Try plain HTML parsing as fallback
                noms = self._parse_sinec_plain_html(resp.text)

            if not noms:
                consecutive_empty += 1
                if consecutive_empty >= max_consecutive_empty:
                    logger.info(
                        "No results for %d consecutive pages, stopping.",
                        consecutive_empty,
                    )
                    break
                page += 1
                continue

            consecutive_empty = 0
            new_count = 0

            for nom in noms:
                nom_id = nom.get("nom_id", "")
                if not nom_id or nom_id in seen_ids:
                    continue

                # Apply filters
                if agency and agency.upper() not in nom_id.upper():
                    continue
                if status_filter:
                    nom_status = nom.get("status", "")
                    if _normalize_status(nom_status) != _normalize_status(
                        status_filter
                    ):
                        continue

                seen_ids.add(nom_id)
                all_noms.append(nom)
                new_count += 1

                if limit and len(all_noms) >= limit:
                    break

            logger.info(
                "Page %d: %d new NOMs (total: %d)", page, new_count, len(all_noms)
            )

            if new_count == 0:
                consecutive_empty += 1
                if consecutive_empty >= max_consecutive_empty:
                    logger.info(
                        "No new NOMs for %d pages, stopping.", consecutive_empty
                    )
                    break

            page += 1

        logger.info("SINEC search complete: %d NOMs found", len(all_noms))
        return all_noms

    def _parse_sinec_results(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse SINEC AJAX response (JSF partial response with CDATA).

        JSF AJAX responses wrap HTML in <update><![CDATA[...]]></update>.
        """
        results: List[Dict[str, Any]] = []

        # Extract CDATA content from JSF partial response
        cdata_match = re.search(r"<!\[CDATA\[(.*?)\]\]>", html_content, re.DOTALL)
        if cdata_match:
            html_fragment = cdata_match.group(1)
        else:
            html_fragment = html_content

        soup = BeautifulSoup(html_fragment, "html.parser")

        # Strategy 1: table rows in results table
        for row in soup.select("table tbody tr, .resultado, .norma-item"):
            try:
                entry = self._parse_result_row(row)
                if entry:
                    results.append(entry)
            except Exception:
                logger.debug("Failed to parse SINEC result row", exc_info=True)
                continue

        return results

    def _parse_sinec_plain_html(self, html_content: str) -> List[Dict[str, Any]]:
        """Fallback parser for plain HTML SINEC responses."""
        results: List[Dict[str, Any]] = []
        soup = BeautifulSoup(html_content, "html.parser")

        # Try various selectors that government sites typically use
        for item in soup.select(
            "table tr, .list-group-item, .panel, .card, div[class*='result']"
        ):
            try:
                text = item.get_text(" ", strip=True)
                nom_match = _NOM_PATTERN.search(text)
                if not nom_match:
                    continue

                nom_id = nom_match.group(1).upper()
                agency_abbr = _extract_agency_from_nom(nom_id)
                agency_name = _resolve_agency_name(agency_abbr)

                # Extract date
                date_str = _extract_date(text)

                # Detect status
                status = "vigente"
                text_lower = text.lower()
                if "cancelad" in text_lower:
                    status = "cancelada"
                elif "proyecto" in text_lower:
                    status = "en_proyecto"

                # Build title: everything after the NOM ID, before the date
                title = _clean_text(text)

                # Extract URL if present
                url = ""
                link = item.find("a", href=True)
                if link:
                    href = link.get("href", "")
                    if href and not href.startswith("http"):
                        href = f"{SINEC_BASE_URL}/{href.lstrip('/')}"
                    url = href

                results.append(
                    {
                        "nom_id": nom_id,
                        "title": title,
                        "agency_abbr": agency_abbr,
                        "agency_name": agency_name,
                        "date_published": date_str,
                        "status": status,
                        "url": url,
                        "dof_reference": "",
                        "source": "sinec",
                    }
                )
            except Exception:
                logger.debug("Failed to parse SINEC plain HTML item", exc_info=True)
                continue

        return results

    def _parse_result_row(self, row: Any) -> Optional[Dict[str, Any]]:
        """Parse a single result row (table tr or card element).

        Returns a NOM dict or None if the row does not contain a valid NOM.
        """
        cells = row.find_all("td")
        text = row.get_text(" ", strip=True)

        nom_match = _NOM_PATTERN.search(text)
        if not nom_match:
            return None

        nom_id = nom_match.group(1).upper()
        agency_abbr = _extract_agency_from_nom(nom_id)
        agency_name = _resolve_agency_name(agency_abbr)

        # Try to extract structured fields from table cells
        title = ""
        date_str = ""
        status = "vigente"
        dof_reference = ""
        url = ""

        if len(cells) >= 2:
            # Typical layout: [NOM ID] [Title] [Agency] [Date] [Status]
            title = _clean_text(cells[1].get_text(strip=True)) if len(cells) > 1 else ""
            if len(cells) > 3:
                date_str = _extract_date(cells[3].get_text(strip=True))
            if len(cells) > 4:
                status = _normalize_status(cells[4].get_text(strip=True))
        else:
            # Compact layout: extract from full text
            title = _clean_text(text)
            date_str = _extract_date(text)

        if not title:
            title = _clean_text(text)

        # Status detection from text
        text_lower = text.lower()
        if "cancelad" in text_lower:
            status = "cancelada"
        elif "proyecto" in text_lower:
            status = "en_proyecto"

        # DOF reference
        dof_match = re.search(r"DOF[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})", text)
        if dof_match:
            dof_reference = dof_match.group(0)

        # URL extraction
        link = row.find("a", href=True)
        if link:
            href = link.get("href", "")
            if href and not href.startswith("http"):
                href = f"{SINEC_BASE_URL}/{href.lstrip('/')}"
            url = href

        return {
            "nom_id": nom_id,
            "title": title,
            "agency_abbr": agency_abbr,
            "agency_name": agency_name,
            "date_published": date_str,
            "status": status,
            "url": url,
            "dof_reference": dof_reference,
            "source": "sinec",
        }

    # ------------------------------------------------------------------
    # Checkpoint support
    # ------------------------------------------------------------------

    def save_checkpoint(self, noms: List[Dict[str, Any]], output_dir: Path) -> None:
        """Save a checkpoint of current progress for resumption."""
        checkpoint_path = output_dir / _CHECKPOINT_FILENAME
        checkpoint_data = {
            "total_collected": len(noms),
            "last_nom_id": noms[-1]["nom_id"] if noms else "",
            "noms": noms,
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        logger.info("Checkpoint saved: %d NOMs to %s", len(noms), checkpoint_path)

    def load_checkpoint(self, output_dir: Path) -> List[Dict[str, Any]]:
        """Load a previous checkpoint if available.

        Returns:
            List of previously collected NOMs, or empty list.
        """
        checkpoint_path = output_dir / _CHECKPOINT_FILENAME
        if not checkpoint_path.exists():
            logger.info("No checkpoint found at %s", checkpoint_path)
            return []

        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            noms = data.get("noms", [])
            logger.info(
                "Loaded checkpoint: %d NOMs (last: %s)",
                len(noms),
                data.get("last_nom_id", ""),
            )
            return noms
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load checkpoint: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def save_results(noms: List[Dict[str, Any]], output_path: Path) -> None:
        """Save NOM results to a JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(noms, f, indent=2, ensure_ascii=False)
        logger.info("Saved %d NOMs to %s", len(noms), output_path)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        output_dir: str = _DEFAULT_OUTPUT_DIR,
        agency: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 0,
        use_checkpoint: bool = False,
    ) -> Dict[str, Any]:
        """Run the SINEC scraping pipeline.

        Args:
            output_dir: Directory for output files.
            agency: Filter by agency abbreviation.
            status_filter: Filter by status.
            limit: Maximum entries (0 = unlimited).
            use_checkpoint: Resume from a previous checkpoint.

        Returns:
            Summary dict with total_noms, output_path, filters.
        """
        out_path = Path(output_dir)

        logger.info(
            "Starting SINEC scraper (agency=%s, status=%s, limit=%d, " "checkpoint=%s)",
            agency,
            status_filter,
            limit,
            use_checkpoint,
        )

        # Resume from checkpoint if requested
        existing_noms: List[Dict[str, Any]] = []
        if use_checkpoint:
            existing_noms = self.load_checkpoint(out_path)

        # Scrape
        new_noms = self.search_catalog(
            agency=agency,
            status_filter=status_filter,
            limit=limit,
        )

        # Merge with checkpoint data (dedup by nom_id)
        if existing_noms:
            seen_ids: Set[str] = {n["nom_id"] for n in existing_noms}
            for nom in new_noms:
                if nom["nom_id"] not in seen_ids:
                    existing_noms.append(nom)
                    seen_ids.add(nom["nom_id"])
            all_noms = existing_noms
        else:
            all_noms = new_noms

        # Save results
        output_file = out_path / _OUTPUT_FILENAME
        self.save_results(all_noms, output_file)

        # Save checkpoint for future resumption
        self.save_checkpoint(all_noms, out_path)

        summary = {
            "total_noms": len(all_noms),
            "new_noms": len(new_noms),
            "output_path": str(output_file),
            "agency_filter": agency,
            "status_filter": status_filter,
            "source": "sinec",
        }
        logger.info("SINEC scraper complete: %s", summary)
        return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the SINEC scraper."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Scrape NOM catalog from SINEC (sinec.gob.mx).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=_DEFAULT_OUTPUT_DIR,
        help=f"Directory to save results (default: {_DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum NOMs to collect (0 = unlimited).",
    )
    parser.add_argument(
        "--agency",
        type=str,
        default=None,
        help="Filter by agency abbreviation (e.g. SSA, SEMARNAT, STPS).",
    )
    parser.add_argument(
        "--status",
        type=str,
        choices=["vigente", "cancelada", "en_proyecto"],
        default=None,
        help="Filter by NOM status.",
    )
    parser.add_argument(
        "--checkpoint",
        action="store_true",
        help="Resume from a previous checkpoint.",
    )
    args = parser.parse_args()

    scraper = SinecScraper()
    result = scraper.run(
        output_dir=args.output_dir,
        agency=args.agency,
        status_filter=args.status,
        limit=args.limit,
        use_checkpoint=args.checkpoint,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
