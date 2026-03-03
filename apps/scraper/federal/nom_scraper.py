"""
NOM Scraper

Scrapes Normas Oficiales Mexicanas from DOF archive and/or CONAMER.
~4,000 NOMs across all secretarias. Priority NOMs: health (NOM-001
through NOM-260), construction, food safety, environment, labor, energy.

Usage:
    python -m apps.scraper.federal.nom_scraper
    python -m apps.scraper.federal.nom_scraper --priority-only
    python -m apps.scraper.federal.nom_scraper --max-results 5000
    python -m apps.scraper.federal.nom_scraper --all-agencies
    python -m apps.scraper.federal.nom_scraper --year-range 1990 2026
    python -m apps.scraper.federal.nom_scraper --all-agencies --year-range 1993 2026 --max-results 5000
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOF_BASE_URL = "https://dof.gob.mx"
DOF_SEARCH_URL = f"{DOF_BASE_URL}/busqueda_detalle.php"
_USER_AGENT = "Tezca/1.0 (+https://github.com/madfam-org/tezca)"
_REQUEST_TIMEOUT = 30  # seconds
_MIN_REQUEST_INTERVAL = 1.0  # 1 req/sec

# Pattern to extract NOM identifiers (e.g. NOM-001-SSA1-2010).
_NOM_PATTERN = re.compile(
    r"(NOM-\d{3,4}-[A-Z0-9]+-\d{4})",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Complete mapping of NOM-issuing agencies (20+ agencies, 40+ abbreviations)
# ---------------------------------------------------------------------------

_SECRETARIA_MAP: Dict[str, str] = {
    # Secretaría de Salud (multiple sub-numbering series)
    "SSA": "Secretaría de Salud",
    "SSA1": "Secretaría de Salud",
    "SSA2": "Secretaría de Salud",
    "SSA3": "Secretaría de Salud",
    # Medio Ambiente
    "SEMARNAT": "Secretaría de Medio Ambiente y Recursos Naturales",
    "INECC": "Instituto Nacional de Ecología y Cambio Climático",
    # Trabajo
    "STPS": "Secretaría del Trabajo y Previsión Social",
    # Comunicaciones y Transportes (SCT -> SICT)
    "SCT": "Secretaría de Comunicaciones y Transportes",
    "SICT": "Secretaría de Infraestructura, Comunicaciones y Transportes",
    # Economía (SE, formerly SCFI)
    "SE": "Secretaría de Economía",
    "SCFI": "Secretaría de Comercio y Fomento Industrial",
    # Agricultura (SAGARPA -> SADER)
    "SAGARPA": "Secretaría de Agricultura, Ganadería, Desarrollo Rural, Pesca y Alimentación",
    "SADER": "Secretaría de Agricultura y Desarrollo Rural",
    "SENASICA": "Servicio Nacional de Sanidad, Inocuidad y Calidad Agroalimentaria",
    "INAPESCA": "Instituto Nacional de Pesca y Acuacultura",
    "CONAPESCA": "Comisión Nacional de Acuacultura y Pesca",
    # Energía
    "SENER": "Secretaría de Energía",
    "ENER": "Secretaría de Energía",
    "CRE": "Comisión Reguladora de Energía",
    "CONUEE": "Comisión Nacional para el Uso Eficiente de la Energía",
    "ASEA": "Agencia de Seguridad, Energía y Ambiente",
    # Agua
    "CONAGUA": "Comisión Nacional del Agua",
    "CNA": "Comisión Nacional del Agua",
    # Desarrollo Territorial
    "SEDATU": "Secretaría de Desarrollo Agrario, Territorial y Urbano",
    # Gobernación
    "SEGOB": "Secretaría de Gobernación",
    # Seguridad
    "SSP": "Secretaría de Seguridad y Protección Ciudadana",
    "SSPC": "Secretaría de Seguridad y Protección Ciudadana",
    # Hacienda y SAT
    "SHCP": "Secretaría de Hacienda y Crédito Público",
    "SAT": "Servicio de Administración Tributaria",
    # Consumidor
    "PROFECO": "Procuraduría Federal del Consumidor",
    # Salud - riesgos sanitarios
    "COFEPRIS": "Comisión Federal para la Protección contra Riesgos Sanitarios",
    # Turismo
    "SECTUR": "Secretaría de Turismo",
    # Relaciones Exteriores
    "SRE": "Secretaría de Relaciones Exteriores",
    # Defensa y Marina
    "SEDENA": "Secretaría de la Defensa Nacional",
    "SEMAR": "Secretaría de Marina",
    # Educación
    "SEP": "Secretaría de Educación Pública",
    # Desarrollo Social / Bienestar
    "SEDESOL": "Secretaría de Desarrollo Social",
    "BIENESTAR": "Secretaría del Bienestar",
    # Otros organismos
    "INMUJERES": "Instituto Nacional de las Mujeres",
}

# All distinct agency abbreviations used in NOM numbering (for --all-agencies mode).
_ALL_AGENCY_ABBREVIATIONS: List[str] = sorted(
    {
        "SSA",
        "SEMARNAT",
        "STPS",
        "SCT",
        "SICT",
        "SE",
        "SCFI",
        "SAGARPA",
        "SADER",
        "SENER",
        "ENER",
        "CONAGUA",
        "CNA",
        "SEDATU",
        "SEGOB",
        "SSP",
        "SSPC",
        "SHCP",
        "SAT",
        "PROFECO",
        "COFEPRIS",
        "SECTUR",
        "SRE",
        "SEDENA",
        "SEMAR",
        "SEP",
        "SEDESOL",
        "BIENESTAR",
        "INMUJERES",
        "SENASICA",
        "INAPESCA",
        "CONAPESCA",
        "CRE",
        "CONUEE",
        "ASEA",
        "INECC",
    }
)

# ---------------------------------------------------------------------------
# Priority NOM series — major series across all key agencies
# ---------------------------------------------------------------------------

_PRIORITY_PREFIXES: List[str] = [
    # SSA (health) — NOM-001 through NOM-015
    "NOM-001-SSA",
    "NOM-002-SSA",
    "NOM-003-SSA",
    "NOM-004-SSA",
    "NOM-005-SSA",
    "NOM-006-SSA",
    "NOM-007-SSA",
    "NOM-008-SSA",
    "NOM-009-SSA",
    "NOM-010-SSA",
    "NOM-011-SSA",
    "NOM-012-SSA",
    "NOM-013-SSA",
    "NOM-014-SSA",
    "NOM-015-SSA",
    # SEMARNAT (environment) — NOM-001 through NOM-005
    "NOM-001-SEMARNAT",
    "NOM-002-SEMARNAT",
    "NOM-003-SEMARNAT",
    "NOM-004-SEMARNAT",
    "NOM-005-SEMARNAT",
    # STPS (labor safety) — NOM-001 through NOM-005
    "NOM-001-STPS",
    "NOM-002-STPS",
    "NOM-003-STPS",
    "NOM-004-STPS",
    "NOM-005-STPS",
    # SCFI (commerce/industry) — NOM-001 through NOM-003
    "NOM-001-SCFI",
    "NOM-002-SCFI",
    "NOM-003-SCFI",
    # SE (economy) — NOM-001 through NOM-003
    "NOM-001-SE",
    "NOM-002-SE",
    "NOM-003-SE",
    # CONAGUA (water) — NOM-001 through NOM-003
    "NOM-001-CONAGUA",
    "NOM-002-CONAGUA",
    "NOM-003-CONAGUA",
    # SENER (energy) — NOM-001 through NOM-003
    "NOM-001-SENER",
    "NOM-002-SENER",
    "NOM-003-SENER",
    # SEDATU (territorial development) — NOM-001
    "NOM-001-SEDATU",
    # SCT (transport) — NOM-001 through NOM-003
    "NOM-001-SCT",
    "NOM-002-SCT",
    "NOM-003-SCT",
]


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class NomScraper:
    """
    Scraper for Normas Oficiales Mexicanas (NOMs).

    Searches the DOF archive for NOM publications and parses result pages
    to extract structured NOM metadata. Supports priority filtering,
    per-agency targeted search, and year-range iteration to maximize
    coverage of the ~4,000 NOM universe.
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

    def _post(
        self, url: str, data: Dict[str, Any], **kwargs: Any
    ) -> Optional[requests.Response]:
        """Rate-limited POST with error handling."""
        self._rate_limit()
        try:
            response = self.session.post(
                url, data=data, timeout=_REQUEST_TIMEOUT, **kwargs
            )
            response.raise_for_status()
            return response
        except requests.ConnectionError:
            logger.error("Connection failed (POST): %s", url)
        except requests.Timeout:
            logger.error("Request timed out (POST): %s", url)
        except requests.HTTPError as exc:
            logger.warning("HTTP %s for POST %s", exc.response.status_code, url)
        except requests.RequestException as exc:
            logger.error("Request error for POST %s: %s", url, exc)
        return None

    # ------------------------------------------------------------------
    # DOF archive search
    # ------------------------------------------------------------------

    def scrape_dof_archive(
        self,
        search_term: str = "NOM-",
        max_results: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Search the DOF archive for NOM publications.

        Queries dof.gob.mx/busqueda_detalle.php and paginates through
        result pages to collect NOM entries.

        Args:
            search_term: Search query (default: "NOM-").
            max_results: Maximum number of results to collect.

        Returns:
            List of NOM dicts.
        """
        logger.info(
            "Searching DOF archive for '%s' (max_results=%d)",
            search_term,
            max_results,
        )

        all_noms: List[Dict[str, Any]] = []
        seen_ids: set = set()
        page = 1

        while len(all_noms) < max_results:
            logger.info("Fetching DOF search page %d", page)

            resp = self._post(
                DOF_SEARCH_URL,
                data={
                    "textobusqueda": search_term,
                    "vienede": "header",
                    "s": "s",
                    "p": page,
                },
            )
            if resp is None:
                logger.warning("Failed to fetch search page %d, stopping.", page)
                break

            noms = self._parse_search_results(resp.text)
            if not noms:
                logger.info("No more results on page %d, stopping.", page)
                break

            new_count = 0
            for nom in noms:
                nom_key = nom.get("nom_number") or nom.get("name", "")
                if nom_key in seen_ids:
                    continue
                seen_ids.add(nom_key)
                all_noms.append(nom)
                new_count += 1

                if len(all_noms) >= max_results:
                    break

            logger.info(
                "Page %d: %d new NOMs (total: %d)", page, new_count, len(all_noms)
            )

            if new_count == 0:
                logger.info("No new NOMs on page %d, stopping.", page)
                break

            page += 1

        logger.info("DOF archive search complete: %d NOMs found", len(all_noms))
        return all_noms

    def _parse_search_results(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse a DOF search results page and extract NOM entries.

        Tries multiple selector strategies to handle layout variations.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        results: List[Dict[str, Any]] = []

        # Strategy 1: DOF td.txt_azul result cells (current layout)
        for item in soup.select("td.txt_azul"):
            try:
                # Find the nota_detalle link (the main result link)
                link = item.find("a", href=lambda h: h and "nota_detalle" in h)
                if not link:
                    # Fallback: any link with text
                    link = item.find("a", href=True)
                    if not link:
                        continue

                title = link.get_text(strip=True)
                if not title:
                    continue

                # Only keep entries that look like NOMs.
                nom_match = _NOM_PATTERN.search(title)
                if not nom_match:
                    # Also check full item text.
                    full_text = item.get_text(strip=True)
                    nom_match = _NOM_PATTERN.search(full_text)
                    if not nom_match:
                        continue

                href = link.get("href", "")
                if href and not href.startswith("http"):
                    href = f"{DOF_BASE_URL}/{href.lstrip('/')}"

                nom_number = nom_match.group(1).upper()
                secretaria = _extract_secretaria(nom_number)

                # Try to find a date in the item (bold tag).
                date_str = _extract_date(item.get_text())

                results.append(
                    {
                        "id": nom_number.lower().replace("-", "_"),
                        "name": _clean_text(title),
                        "nom_number": nom_number,
                        "secretaria": secretaria,
                        "date_published": date_str,
                        "url": href,
                        "status": "vigente",
                        "source": "dof_archive",
                    }
                )
            except Exception:
                logger.debug("Failed to parse search result item", exc_info=True)
                continue

        # Strategy 2: Fallback for older layout (.resultado, .nota, tr)
        if not results:
            for item in soup.select(".resultado, .busqueda-item, .nota, tr"):
                try:
                    link = item.find("a", href=True)
                    if not link:
                        continue
                    title = link.get_text(strip=True)
                    if not title:
                        continue
                    nom_match = _NOM_PATTERN.search(title)
                    if not nom_match:
                        full_text = item.get_text(strip=True)
                        nom_match = _NOM_PATTERN.search(full_text)
                        if not nom_match:
                            continue
                    href = link.get("href", "")
                    if href and not href.startswith("http"):
                        href = f"{DOF_BASE_URL}/{href.lstrip('/')}"
                    nom_number = nom_match.group(1).upper()
                    secretaria = _extract_secretaria(nom_number)
                    date_str = _extract_date(item.get_text())
                    results.append(
                        {
                            "id": nom_number.lower().replace("-", "_"),
                            "name": _clean_text(title),
                            "nom_number": nom_number,
                            "secretaria": secretaria,
                            "date_published": date_str,
                            "url": href,
                            "status": "vigente",
                            "source": "dof_archive",
                        }
                    )
                except Exception:
                    continue

        return results

    # ------------------------------------------------------------------
    # Priority NOMs
    # ------------------------------------------------------------------

    def scrape_priority_noms(self) -> List[Dict[str, Any]]:
        """
        Focus on high-priority NOMs across all major agencies.

        Runs targeted searches for each priority prefix to maximise
        coverage of health, safety, environment, labor, energy, and
        commerce standards.

        Returns:
            List of priority NOM dicts.
        """
        logger.info("Scraping priority NOMs (%d prefixes)", len(_PRIORITY_PREFIXES))

        all_noms: List[Dict[str, Any]] = []
        seen_numbers: set = set()

        for prefix in _PRIORITY_PREFIXES:
            logger.info("Searching for prefix: %s", prefix)

            noms = self.scrape_dof_archive(
                search_term=prefix,
                max_results=50,
            )

            new_count = 0
            for nom in noms:
                num = nom.get("nom_number", "")
                if num in seen_numbers:
                    continue
                seen_numbers.add(num)
                all_noms.append(nom)
                new_count += 1

            logger.info("Prefix %s: %d new NOMs", prefix, new_count)

        logger.info("Priority NOM scrape complete: %d total", len(all_noms))
        return all_noms

    # ------------------------------------------------------------------
    # All-agencies targeted search
    # ------------------------------------------------------------------

    def scrape_all_agencies(
        self,
        max_results_per_agency: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Run targeted searches for each known NOM-issuing agency abbreviation.

        For each agency in _ALL_AGENCY_ABBREVIATIONS, searches DOF for
        "NOM- {agency}" to find NOMs specific to that agency. This catches
        NOMs that the generic "NOM-" search misses due to DOF pagination
        limits.

        Args:
            max_results_per_agency: Max results per individual agency search.

        Returns:
            Deduplicated list of NOM dicts across all agencies.
        """
        logger.info(
            "Scraping all %d agencies (max %d per agency)",
            len(_ALL_AGENCY_ABBREVIATIONS),
            max_results_per_agency,
        )

        all_noms: List[Dict[str, Any]] = []
        seen_numbers: set = set()

        for abbr in _ALL_AGENCY_ABBREVIATIONS:
            search_term = f"NOM- {abbr}"
            logger.info("Agency search: '%s'", search_term)

            noms = self.scrape_dof_archive(
                search_term=search_term,
                max_results=max_results_per_agency,
            )

            new_count = 0
            for nom in noms:
                num = nom.get("nom_number", "")
                if num in seen_numbers:
                    continue
                seen_numbers.add(num)
                all_noms.append(nom)
                new_count += 1

            logger.info(
                "Agency %s: %d new NOMs (running total: %d)",
                abbr,
                new_count,
                len(all_noms),
            )

        logger.info("All-agencies scrape complete: %d unique NOMs", len(all_noms))
        return all_noms

    # ------------------------------------------------------------------
    # Year-range iteration
    # ------------------------------------------------------------------

    def scrape_by_year_range(
        self,
        start_year: int = 1990,
        end_year: int = 2026,
        max_results_per_year: int = 300,
    ) -> List[Dict[str, Any]]:
        """
        Iterate year by year searching for NOMs published in each year.

        Searches for "NOM- {year}" for each year in the range. This catches
        historical NOMs that don't appear in the generic "NOM-" search due
        to DOF pagination limits (DOF only returns ~500 most recent results
        for a generic query).

        Args:
            start_year: First year to search (inclusive). Default 1990.
            end_year: Last year to search (inclusive). Default 2026.
            max_results_per_year: Max results per individual year search.

        Returns:
            Deduplicated list of NOM dicts across all years.
        """
        if start_year > end_year:
            raise ValueError(
                f"start_year ({start_year}) must be <= end_year ({end_year})"
            )

        total_years = end_year - start_year + 1
        logger.info(
            "Scraping NOMs by year range %d-%d (%d years, max %d per year)",
            start_year,
            end_year,
            total_years,
            max_results_per_year,
        )

        all_noms: List[Dict[str, Any]] = []
        seen_numbers: set = set()

        for year in range(start_year, end_year + 1):
            search_term = f"NOM- {year}"
            logger.info("Year search: '%s'", search_term)

            noms = self.scrape_dof_archive(
                search_term=search_term,
                max_results=max_results_per_year,
            )

            new_count = 0
            for nom in noms:
                num = nom.get("nom_number", "")
                if num in seen_numbers:
                    continue
                seen_numbers.add(num)
                all_noms.append(nom)
                new_count += 1

            logger.info(
                "Year %d: %d new NOMs (running total: %d)",
                year,
                new_count,
                len(all_noms),
            )

        logger.info(
            "Year-range scrape complete (%d-%d): %d unique NOMs",
            start_year,
            end_year,
            len(all_noms),
        )
        return all_noms

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def save_results(noms: List[Dict[str, Any]], output_path: Path) -> None:
        """
        Save NOM results to a JSON file.

        Args:
            noms: List of NOM dicts.
            output_path: Target file path.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(noms, f, indent=2, ensure_ascii=False)
        logger.info("Saved %d NOMs to %s", len(noms), output_path)

    # ------------------------------------------------------------------
    # Deduplication utility
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_nom_lists(*nom_lists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge multiple NOM lists, deduplicating by nom_number.

        Later entries with the same nom_number are discarded (first seen wins).

        Returns:
            Deduplicated merged list.
        """
        seen: set = set()
        merged: List[Dict[str, Any]] = []
        for nom_list in nom_lists:
            for nom in nom_list:
                num = nom.get("nom_number", "")
                if num and num not in seen:
                    seen.add(num)
                    merged.append(nom)
        return merged

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        output_dir: str = "data/noms",
        priority_only: bool = False,
        all_agencies: bool = False,
        year_range: Optional[Tuple[int, int]] = None,
        max_results: int = 500,
    ) -> Dict[str, Any]:
        """
        Run the full NOM scraping pipeline.

        Modes (can be combined for maximum coverage):
        - Default: generic "NOM-" search with pagination.
        - priority_only: targeted search for priority prefixes only.
        - all_agencies: targeted search for each agency abbreviation.
        - year_range: year-by-year iteration to catch historical NOMs.

        When multiple modes are active, results are merged and deduplicated.

        Args:
            output_dir: Directory for output files.
            priority_only: If True, only scrape priority NOMs.
            all_agencies: If True, run per-agency targeted searches.
            year_range: Optional (start_year, end_year) tuple.
            max_results: Maximum results for the general archive search.

        Returns:
            Summary dict with total_noms, output_path, modes_used.
        """
        out_path = Path(output_dir)
        modes_used: List[str] = []

        logger.info(
            "Starting NOM scraper (priority_only=%s, all_agencies=%s, "
            "year_range=%s, max_results=%d)",
            priority_only,
            all_agencies,
            year_range,
            max_results,
        )

        collected_lists: List[List[Dict[str, Any]]] = []

        if priority_only:
            modes_used.append("priority")
            collected_lists.append(self.scrape_priority_noms())
        else:
            # Always run the general search unless priority_only
            modes_used.append("general")
            collected_lists.append(
                self.scrape_dof_archive(
                    search_term="NOM-",
                    max_results=max_results,
                )
            )

        if all_agencies:
            modes_used.append("all_agencies")
            collected_lists.append(self.scrape_all_agencies())

        if year_range is not None:
            start_year, end_year = year_range
            modes_used.append(f"year_range_{start_year}_{end_year}")
            collected_lists.append(
                self.scrape_by_year_range(
                    start_year=start_year,
                    end_year=end_year,
                )
            )

        # Merge and deduplicate all collected results
        noms = self._merge_nom_lists(*collected_lists)

        output_file = out_path / "discovered_noms.json"
        self.save_results(noms, output_file)

        summary = {
            "total_noms": len(noms),
            "output_path": str(output_file),
            "modes_used": modes_used,
            "priority_only": priority_only,
            "all_agencies": all_agencies,
            "year_range": list(year_range) if year_range else None,
        }
        logger.info("NOM scraper complete: %s", summary)
        return summary


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _clean_text(raw: str) -> str:
    """Collapse whitespace and strip surrounding blanks."""
    return re.sub(r"\s+", " ", raw).strip()


def _extract_secretaria(nom_number: str) -> str:
    """
    Extract the issuing secretaria from a NOM identifier.

    NOM-001-SSA1-2010 -> "Secretaría de Salud"
    NOM-059-SEMARNAT-2010 -> "Secretaría de Medio Ambiente..."
    """
    parts = nom_number.split("-")
    if len(parts) >= 3:
        abbr = parts[2].upper()
        # Try exact match first, then prefix matching.
        if abbr in _SECRETARIA_MAP:
            return _SECRETARIA_MAP[abbr]
        for key, value in _SECRETARIA_MAP.items():
            if abbr.startswith(key) or key.startswith(abbr):
                return value
    return ""


def _extract_date(text: str) -> str:
    """
    Try to extract a date from free text.

    Looks for patterns like DD/MM/YYYY or DD-MM-YYYY.
    Returns ISO-format string or empty string.
    """
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
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the NOM scraper."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Scrape Normas Oficiales Mexicanas from DOF archive.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/noms",
        help="Directory to save results (default: data/noms).",
    )
    parser.add_argument(
        "--priority-only",
        action="store_true",
        help="Only scrape priority NOMs (major series across all key agencies).",
    )
    parser.add_argument(
        "--all-agencies",
        action="store_true",
        help="Run targeted searches for each of the 36 known agency abbreviations.",
    )
    parser.add_argument(
        "--year-range",
        type=int,
        nargs=2,
        metavar=("START", "END"),
        help="Search year by year (e.g. --year-range 1990 2026).",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=500,
        help="Maximum results for general search (default: 500, use 5000 for full coverage).",
    )
    args = parser.parse_args()

    year_range = None
    if args.year_range:
        start_y, end_y = args.year_range
        if start_y > end_y:
            parser.error("year-range START must be <= END")
        year_range = (start_y, end_y)

    scraper = NomScraper()
    result = scraper.run(
        output_dir=args.output_dir,
        priority_only=args.priority_only,
        all_agencies=args.all_agencies,
        year_range=year_range,
        max_results=args.max_results,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
