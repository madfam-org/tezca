"""
NOM Scraper

Scrapes Normas Oficiales Mexicanas from DOF archive and/or CONAMER.
~4,000 NOMs across all secretarias. Priority NOMs: health (NOM-001
through NOM-260), construction, food safety.

Usage:
    python -m apps.scraper.federal.nom_scraper
    python -m apps.scraper.federal.nom_scraper --priority-only
    python -m apps.scraper.federal.nom_scraper --max-results 200
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

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

# Mapping of secretaria abbreviations to full names.
_SECRETARIA_MAP: Dict[str, str] = {
    "SSA": "Secretaria de Salud",
    "SSA1": "Secretaria de Salud",
    "SSA2": "Secretaria de Salud",
    "SSA3": "Secretaria de Salud",
    "SEMARNAT": "Secretaria de Medio Ambiente y Recursos Naturales",
    "STPS": "Secretaria del Trabajo y Prevision Social",
    "SCT": "Secretaria de Comunicaciones y Transportes",
    "SE": "Secretaria de Economia",
    "SAGARPA": "Secretaria de Agricultura",
    "SENER": "Secretaria de Energia",
    "CONAGUA": "Comision Nacional del Agua",
    "SCFI": "Secretaria de Comercio y Fomento Industrial",
    "CNA": "Comision Nacional del Agua",
    "SEDATU": "Secretaria de Desarrollo Agrario, Territorial y Urbano",
}

# Priority NOM series for health/safety scraping.
_PRIORITY_PREFIXES = [
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
]


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class NomScraper:
    """
    Scraper for Normas Oficiales Mexicanas (NOMs).

    Searches the DOF archive for NOM publications and parses result pages
    to extract structured NOM metadata. Supports priority filtering to
    focus on health and safety NOMs.
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
                link = item.find(
                    "a", href=lambda h: h and "nota_detalle" in h
                )
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
        Focus on health NOMs (NOM-001 through NOM-260 SSA series).

        Runs targeted searches for each priority prefix to maximise
        coverage of health and safety standards.

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
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        output_dir: str = "data/noms",
        priority_only: bool = False,
        max_results: int = 500,
    ) -> Dict[str, Any]:
        """
        Run the full NOM scraping pipeline.

        Args:
            output_dir: Directory for output files.
            priority_only: If True, only scrape priority health NOMs.
            max_results: Maximum results for the general archive search.

        Returns:
            Summary dict with total_noms, output_path, priority_only.
        """
        out_path = Path(output_dir)
        logger.info(
            "Starting NOM scraper (priority_only=%s, max_results=%d)",
            priority_only,
            max_results,
        )

        if priority_only:
            noms = self.scrape_priority_noms()
        else:
            noms = self.scrape_dof_archive(
                search_term="NOM-",
                max_results=max_results,
            )

        output_file = out_path / "discovered_noms.json"
        self.save_results(noms, output_file)

        summary = {
            "total_noms": len(noms),
            "output_path": str(output_file),
            "priority_only": priority_only,
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

    NOM-001-SSA1-2010 -> "Secretaria de Salud"
    NOM-059-SEMARNAT-2010 -> "Secretaria de Medio Ambiente..."
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
        help="Only scrape priority health NOMs (SSA series).",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=500,
        help="Maximum number of results for general search (default: 500).",
    )
    args = parser.parse_args()

    scraper = NomScraper()
    result = scraper.run(
        output_dir=args.output_dir,
        priority_only=args.priority_only,
        max_results=args.max_results,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
