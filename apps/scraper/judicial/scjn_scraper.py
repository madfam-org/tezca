"""
SCJN Judicial Corpus Scraper

Fallback scraper for the Semanario Judicial de la Federacion (sjf.scjn.gob.mx).
Primary strategy: institutional partnership with SCJN for bulk data dump.
Fallback: headless browser scraping at 1 req/sec (~140 hours for 500K items).

Targets:
- Jurisprudencia: ~60,000 binding precedents (10th epoch)
- Tesis aisladas: ~440,000 non-binding isolated opinions (all epochs)
"""

import argparse
import csv
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://sjf.scjn.gob.mx"
OPEN_DATA_URL = "https://datos.scjn.gob.mx"
_USER_AGENT = "Tezca/1.0 (+https://github.com/madfam-org/tezca)"
_REQUEST_TIMEOUT = 30  # seconds
_MIN_REQUEST_INTERVAL = 1.0  # 1 req/sec — respectful rate for judicial portal
_BATCH_SIZE = 50
_MAX_CONSECUTIVE_FAILURES = 3

# Paths to probe on the open data portal.
_OPEN_DATA_PROBE_PATHS = [
    "/datasets",
    "/data",
    "/api",
    "/api/v1",
    "/api/v1/datasets",
    "/api/3/action/package_list",  # CKAN convention
    "/api/3/action/package_search?q=tesis",
    "/catalogo",
    "/descargas",
]

# Paths to probe on the SJF search portal.
_SJF_PROBE_PATHS = [
    "/api/",
    "/api/v1/",
    "/api/tesis/",
    "/api/busqueda/",
    "/busqueda/",
    "/Busqueda",
    "/IUSQuery/",
    "/iusfnav/",
]

# Known SCJN judicial epochs (epocas).
EPOCAS = {
    1: "Primera Epoca",
    2: "Segunda Epoca",
    3: "Tercera Epoca",
    4: "Cuarta Epoca",
    5: "Quinta Epoca",
    6: "Sexta Epoca",
    7: "Septima Epoca",
    8: "Octava Epoca",
    9: "Novena Epoca",
    10: "Decima Epoca",
    11: "Undecima Epoca",
}


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class ScjnScraper:
    """
    Fallback scraper for the SCJN judicial corpus.

    Probes the SCJN open data portal and the SJF search interface for
    structured data endpoints. Falls back to HTML scraping when no API
    is available. Yields judicial records in paginated batches.

    Usage:
        scraper = ScjnScraper()
        scraper.run(output_dir="data/judicial")
    """

    def __init__(self) -> None:
        self.session = self._setup_session()
        self.last_request_time: float = 0.0
        self._search_endpoint: Optional[str] = None
        self._open_data_endpoint: Optional[str] = None

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
        """Rate-limited GET with comprehensive error handling."""
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
    # Open data probing
    # ------------------------------------------------------------------

    def check_open_data(self) -> Dict[str, Any]:
        """
        Probe datos.scjn.gob.mx for existing bulk datasets (CSV/JSON).

        Checks common open-data and CKAN endpoints for downloadable
        judicial datasets. This is the preferred data source over scraping.

        Returns:
            Findings dict with:
                - found (bool): Whether bulk data was discovered.
                - endpoint (str | None): The working endpoint URL.
                - datasets (list): Discovered dataset metadata.
                - download_urls (list): Direct download links found.
                - probed (list): All paths attempted.
        """
        findings: Dict[str, Any] = {
            "found": False,
            "endpoint": None,
            "datasets": [],
            "download_urls": [],
            "probed": [],
        }

        for path in _OPEN_DATA_PROBE_PATHS:
            url = f"{OPEN_DATA_URL}{path}"
            findings["probed"].append(url)
            logger.info("Probing open data: %s", url)

            resp = self._get(url, headers={"Accept": "application/json"})
            if resp is None:
                continue

            content_type = resp.headers.get("Content-Type", "")

            # JSON response — likely an API or CKAN endpoint.
            if "json" in content_type:
                try:
                    data = resp.json()
                except (ValueError, json.JSONDecodeError):
                    continue

                datasets = self._extract_datasets_from_json(data)
                if datasets:
                    findings["found"] = True
                    findings["endpoint"] = url
                    findings["datasets"].extend(datasets)
                    logger.info("Found %d datasets at %s", len(datasets), url)

            # HTML response — scan for download links.
            elif "html" in content_type:
                download_urls = self._extract_download_links(resp.text, url)
                if download_urls:
                    findings["found"] = True
                    findings["endpoint"] = url
                    findings["download_urls"].extend(download_urls)
                    logger.info(
                        "Found %d download links at %s",
                        len(download_urls),
                        url,
                    )

        if not findings["found"]:
            logger.info(
                "No bulk data found after probing %d paths on %s",
                len(findings["probed"]),
                OPEN_DATA_URL,
            )

        return findings

    @staticmethod
    def _extract_datasets_from_json(data: Any) -> List[Dict[str, Any]]:
        """Extract dataset entries from a JSON API response."""
        datasets: List[Dict[str, Any]] = []

        # CKAN package_list response
        if isinstance(data, dict) and "result" in data:
            result = data["result"]
            if isinstance(result, list):
                for item in result:
                    if isinstance(item, str):
                        datasets.append({"name": item, "type": "ckan_package"})
                    elif isinstance(item, dict):
                        datasets.append(item)
                return datasets

        # Generic list of datasets
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    datasets.append(item)
            return datasets

        # Dict with common wrapper keys
        if isinstance(data, dict):
            for key in ("datasets", "data", "results", "items", "resources"):
                if key in data and isinstance(data[key], list):
                    for item in data[key]:
                        if isinstance(item, dict):
                            datasets.append(item)
                    return datasets

        return datasets

    @staticmethod
    def _extract_download_links(html: str, base_url: str) -> List[str]:
        """Scan HTML for CSV/JSON/XLSX download links."""
        soup = BeautifulSoup(html, "html.parser")
        download_urls: List[str] = []

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            lower_href = href.lower()
            if any(
                lower_href.endswith(ext)
                for ext in (".csv", ".json", ".xlsx", ".xml", ".zip")
            ):
                if not href.startswith("http"):
                    href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                download_urls.append(href)

        return download_urls

    # ------------------------------------------------------------------
    # SJF search API probing
    # ------------------------------------------------------------------

    def probe_search_api(self) -> Dict[str, Any]:
        """
        Probe the SJF search functionality for API endpoints.

        Tries common patterns on sjf.scjn.gob.mx to discover structured
        search APIs with pagination support.

        Returns:
            Findings dict with:
                - found (bool): Whether a search API was discovered.
                - endpoint (str | None): The working search URL.
                - sample (dict | None): A sample response payload.
                - pagination (dict | None): Pagination info if detected.
                - search_form (dict | None): HTML form details if found.
                - probed (list): All paths attempted.
        """
        findings: Dict[str, Any] = {
            "found": False,
            "endpoint": None,
            "sample": None,
            "pagination": None,
            "search_form": None,
            "probed": [],
        }

        # Phase 1: probe JSON API endpoints.
        for path in _SJF_PROBE_PATHS:
            url = f"{BASE_URL}{path}"
            findings["probed"].append(url)
            logger.info("Probing SJF API: %s", url)

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

            # Check if response looks like a search result.
            if self._looks_like_search_result(data):
                findings["found"] = True
                findings["endpoint"] = url
                findings["sample"] = data if not isinstance(data, list) else data[0]
                findings["pagination"] = self._detect_pagination(data)
                self._search_endpoint = url
                logger.info("Found search API: %s", url)
                break

        # Phase 2: inspect HTML search form for action URL.
        if not findings["found"]:
            form_info = self._inspect_search_form()
            if form_info:
                findings["search_form"] = form_info
                logger.info(
                    "Found HTML search form: action=%s",
                    form_info.get("action"),
                )

        if not findings["found"] and not findings["search_form"]:
            logger.info(
                "No search API found after probing %d paths on %s",
                len(findings["probed"]),
                BASE_URL,
            )

        return findings

    @staticmethod
    def _looks_like_search_result(data: Any) -> bool:
        """Heuristic: does this JSON look like judicial search results?"""
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict):
                keys = set(data[0].keys())
                judicial_keys = {
                    "tesis",
                    "rubro",
                    "texto",
                    "registro",
                    "materia",
                    "instancia",
                    "epoca",
                    "tipo",
                }
                if keys & judicial_keys:
                    return True
            return False

        if isinstance(data, dict):
            # Paginated wrapper
            for key in ("results", "data", "items", "tesis", "records"):
                if key in data and isinstance(data[key], list) and data[key]:
                    return True
            # Total count indicator
            if any(
                k in data for k in ("total", "totalRegistros", "count", "total_count")
            ):
                return True

        return False

    @staticmethod
    def _detect_pagination(data: Any) -> Optional[Dict[str, Any]]:
        """Extract pagination metadata from a search response."""
        if not isinstance(data, dict):
            return None

        pagination: Dict[str, Any] = {}
        for total_key in ("total", "totalRegistros", "count", "total_count"):
            if total_key in data:
                pagination["total"] = data[total_key]
                break

        for page_key in ("page", "pagina", "currentPage", "offset"):
            if page_key in data:
                pagination["current_page_key"] = page_key
                pagination["current_page"] = data[page_key]
                break

        for size_key in ("pageSize", "page_size", "limit", "per_page"):
            if size_key in data:
                pagination["page_size_key"] = size_key
                pagination["page_size"] = data[size_key]
                break

        return pagination if pagination else None

    def _inspect_search_form(self) -> Optional[Dict[str, Any]]:
        """Fetch the SJF homepage and inspect search forms."""
        resp = self._get(BASE_URL)
        if resp is None:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for search forms.
        for form in soup.find_all("form"):
            action = form.get("action", "")
            method = form.get("method", "GET").upper()

            # Heuristic: search-related form.
            action_lower = action.lower()
            if any(
                kw in action_lower
                for kw in ("busq", "search", "consulta", "query", "ius")
            ):
                fields = {}
                for inp in form.find_all(["input", "select"]):
                    name = inp.get("name")
                    if name:
                        fields[name] = {
                            "type": inp.get("type", inp.name),
                            "value": inp.get("value", ""),
                        }

                return {
                    "action": (
                        action
                        if action.startswith("http")
                        else f"{BASE_URL}/{action.lstrip('/')}"
                    ),
                    "method": method,
                    "fields": fields,
                }

        return None

    # ------------------------------------------------------------------
    # Jurisprudencia scraping
    # ------------------------------------------------------------------

    def scrape_jurisprudencia(
        self,
        epoca: int = 10,
        max_items: Optional[int] = None,
        resume_from: int = 0,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Scrape binding jurisprudencia records from the SJF portal.

        Paginates through search results for the given epoch and yields
        batches of normalized records.

        Args:
            epoca: Judicial epoch number (default: 10, Decima Epoca).
            max_items: Stop after this many items (None = unlimited).
            resume_from: Item offset to resume from (0-based).

        Yields:
            Batches of up to 50 jurisprudencia dicts, each containing:
                registro, tipo, epoca, instancia, materia, tesis_num,
                rubro, texto, precedentes, url, source.
        """
        yield from self._scrape_tesis(
            tipo="jurisprudencia",
            epoca=epoca,
            max_items=max_items,
            resume_from=resume_from,
        )

    # ------------------------------------------------------------------
    # Tesis aisladas scraping
    # ------------------------------------------------------------------

    def scrape_tesis_aisladas(
        self,
        epoca: int = 10,
        max_items: Optional[int] = None,
        resume_from: int = 0,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Scrape non-binding tesis aisladas from the SJF portal.

        Same interface as scrape_jurisprudencia but for isolated theses.

        Args:
            epoca: Judicial epoch number (default: 10, Decima Epoca).
            max_items: Stop after this many items (None = unlimited).
            resume_from: Item offset to resume from (0-based).

        Yields:
            Batches of up to 50 tesis_aislada dicts with the same schema
            as jurisprudencia records.
        """
        yield from self._scrape_tesis(
            tipo="tesis_aislada",
            epoca=epoca,
            max_items=max_items,
            resume_from=resume_from,
        )

    def _scrape_tesis(
        self,
        tipo: str,
        epoca: int,
        max_items: Optional[int],
        resume_from: int,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Internal scraping loop shared by jurisprudencia and tesis aisladas.

        Attempts API-based scraping first, then falls back to HTML parsing.
        """
        logger.info(
            "Starting %s scrape: epoca=%d, resume_from=%d, max_items=%s",
            tipo,
            epoca,
            resume_from,
            max_items,
        )

        if self._search_endpoint:
            yield from self._scrape_tesis_via_api(tipo, epoca, max_items, resume_from)
        else:
            yield from self._scrape_tesis_via_html(tipo, epoca, max_items, resume_from)

    def _scrape_tesis_via_api(
        self,
        tipo: str,
        epoca: int,
        max_items: Optional[int],
        resume_from: int,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Paginate through a discovered JSON search API."""
        offset = resume_from
        total_yielded = 0
        consecutive_failures = 0

        while True:
            if max_items is not None and total_yielded >= max_items:
                logger.info("Reached max_items=%d for %s, stopping.", max_items, tipo)
                break

            # Build query params — actual parameter names depend on the
            # discovered API; we try common conventions.
            params = {
                "tipo": tipo,
                "epoca": epoca,
                "offset": offset,
                "limit": _BATCH_SIZE,
            }
            url = self._search_endpoint
            logger.debug("Fetching %s API page offset=%d: %s", tipo, offset, url)

            resp = self._get(url, params=params)
            if resp is None:
                consecutive_failures += 1
                if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                    logger.warning(
                        "%d consecutive failures for %s, stopping.",
                        _MAX_CONSECUTIVE_FAILURES,
                        tipo,
                    )
                    break
                offset += _BATCH_SIZE
                continue

            try:
                data = resp.json()
            except (ValueError, json.JSONDecodeError):
                logger.warning("Invalid JSON at offset %d for %s", offset, tipo)
                consecutive_failures += 1
                offset += _BATCH_SIZE
                continue

            raw_items = self._extract_items_from_json(data)
            if not raw_items:
                consecutive_failures += 1
                if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                    logger.info(
                        "%d consecutive empty pages for %s, assuming end.",
                        _MAX_CONSECUTIVE_FAILURES,
                        tipo,
                    )
                    break
                offset += _BATCH_SIZE
                continue

            consecutive_failures = 0
            batch = [self._normalize_tesis(item, tipo, epoca) for item in raw_items]
            batch = [item for item in batch if item is not None]

            if batch:
                if max_items is not None:
                    remaining = max_items - total_yielded
                    batch = batch[:remaining]

                yield batch
                total_yielded += len(batch)

            offset += _BATCH_SIZE

        logger.info("Finished %s API scrape: %d items yielded.", tipo, total_yielded)

    def _scrape_tesis_via_html(
        self,
        tipo: str,
        epoca: int,
        max_items: Optional[int],
        resume_from: int,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Paginate through HTML search results on the SJF portal."""
        page = resume_from // _BATCH_SIZE
        total_yielded = 0
        consecutive_failures = 0

        # Map tipo to search parameter values — these are guesses based on
        # common SJF URL patterns and may need adjustment.
        tipo_param = "J" if tipo == "jurisprudencia" else "TA"

        while True:
            if max_items is not None and total_yielded >= max_items:
                logger.info("Reached max_items=%d for %s, stopping.", max_items, tipo)
                break

            # Construct search URL — structure is speculative and must be
            # validated against the live site.
            url = (
                f"{BASE_URL}/busqueda"
                f"?tipo={tipo_param}"
                f"&epoca={epoca}"
                f"&pagina={page + 1}"
            )
            logger.debug("Fetching %s HTML page %d: %s", tipo, page, url)

            resp = self._get(url)
            if resp is None:
                consecutive_failures += 1
                if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                    logger.warning(
                        "%d consecutive failures for %s HTML, stopping.",
                        _MAX_CONSECUTIVE_FAILURES,
                        tipo,
                    )
                    break
                page += 1
                continue

            items = self._parse_tesis_html(resp.text, tipo, epoca)
            if not items:
                consecutive_failures += 1
                if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                    logger.info(
                        "%d consecutive empty HTML pages for %s, assuming end.",
                        _MAX_CONSECUTIVE_FAILURES,
                        tipo,
                    )
                    break
                page += 1
                continue

            consecutive_failures = 0

            if max_items is not None:
                remaining = max_items - total_yielded
                items = items[:remaining]

            yield items
            total_yielded += len(items)
            page += 1

        logger.info("Finished %s HTML scrape: %d items yielded.", tipo, total_yielded)

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_items_from_json(data: Any) -> List[Dict[str, Any]]:
        """Pull the item list out of a JSON response with unknown structure."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in (
                "results",
                "data",
                "items",
                "tesis",
                "records",
                "jurisprudencias",
            ):
                if key in data and isinstance(data[key], list):
                    return data[key]
        return []

    @staticmethod
    def _normalize_tesis(
        raw: Dict[str, Any], tipo: str, epoca: int
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize a raw tesis record into the canonical schema.

        Returns None if the record lacks critical fields.
        """
        # Try multiple field name conventions — the SCJN API/HTML may use
        # any of these depending on the endpoint.
        rubro = (
            raw.get("rubro")
            or raw.get("titulo")
            or raw.get("title")
            or raw.get("Rubro")
            or ""
        ).strip()

        texto = (
            raw.get("texto")
            or raw.get("text")
            or raw.get("Texto")
            or raw.get("contenido")
            or ""
        ).strip()

        registro = str(
            raw.get("registro")
            or raw.get("Registro")
            or raw.get("id")
            or raw.get("numero_registro")
            or ""
        ).strip()

        # A valid record must have at least a rubro or registro.
        if not rubro and not registro:
            return None

        tesis_num = (
            raw.get("tesis")
            or raw.get("Tesis")
            or raw.get("tesis_num")
            or raw.get("numero_tesis")
            or ""
        )

        instancia = (
            raw.get("instancia") or raw.get("Instancia") or raw.get("tribunal") or ""
        )

        materia = raw.get("materia") or raw.get("Materia") or raw.get("materias") or ""

        precedentes = (
            raw.get("precedentes")
            or raw.get("Precedentes")
            or raw.get("precedents")
            or ""
        )

        # Build canonical URL if not provided.
        url = raw.get("url") or raw.get("enlace") or ""
        if not url and registro:
            url = f"{BASE_URL}/detalle/tesis/{registro}"

        return {
            "registro": registro,
            "tipo": tipo,
            "epoca": epoca,
            "epoca_nombre": EPOCAS.get(epoca, f"Epoca {epoca}"),
            "instancia": str(instancia).strip(),
            "materia": str(materia).strip(),
            "tesis_num": str(tesis_num).strip(),
            "rubro": rubro,
            "texto": texto,
            "precedentes": str(precedentes).strip(),
            "url": str(url).strip(),
            "source": "sjf_scjn",
        }

    def _parse_tesis_html(
        self, html: str, tipo: str, epoca: int
    ) -> List[Dict[str, Any]]:
        """
        Parse an HTML search results page from the SJF portal.

        Uses multiple selector strategies to handle layout variations.
        The SJF portal is known to change its markup; this method is
        intentionally defensive.
        """
        soup = BeautifulSoup(html, "html.parser")
        items: List[Dict[str, Any]] = []

        # Strategy 1: structured result containers.
        for container in soup.select(".resultado, .tesis-item, .result-item, article"):
            try:
                record = self._parse_tesis_container(container, tipo, epoca)
                if record:
                    items.append(record)
            except Exception:
                logger.debug("Failed to parse tesis container", exc_info=True)
                continue

        if items:
            return items

        # Strategy 2: table rows.
        for row in soup.select("table tbody tr"):
            try:
                record = self._parse_tesis_table_row(row, tipo, epoca)
                if record:
                    items.append(record)
            except Exception:
                logger.debug("Failed to parse tesis table row", exc_info=True)
                continue

        if items:
            return items

        # Strategy 3: definition lists (dl/dt/dd) — some SCJN pages use this.
        for dl in soup.find_all("dl"):
            try:
                record = self._parse_tesis_dl(dl, tipo, epoca)
                if record:
                    items.append(record)
            except Exception:
                logger.debug("Failed to parse tesis dl", exc_info=True)
                continue

        return items

    def _parse_tesis_container(
        self, container: Any, tipo: str, epoca: int
    ) -> Optional[Dict[str, Any]]:
        """Extract a tesis record from a result container element."""
        # Title / rubro
        title_el = container.find(["h2", "h3", "h4", "strong", "b"])
        rubro = title_el.get_text(strip=True) if title_el else ""

        if not rubro or len(rubro) < 5:
            return None

        # Full text
        text_el = (
            container.find(class_=lambda c: c and "texto" in c.lower())
            if container
            else None
        )
        texto = text_el.get_text(strip=True) if text_el else ""
        if not texto:
            # Fallback: longest paragraph in the container.
            paragraphs = container.find_all("p")
            if paragraphs:
                texto = max(
                    (p.get_text(strip=True) for p in paragraphs),
                    key=len,
                    default="",
                )

        # Registro number — look for a link or data attribute.
        registro = ""
        link = container.find("a", href=True)
        if link:
            href = link["href"]
            # Extract registro from URL patterns like /detalle/tesis/123456
            for segment in reversed(href.strip("/").split("/")):
                if segment.isdigit():
                    registro = segment
                    break

        url = ""
        if link:
            href = link["href"]
            url = href if href.startswith("http") else f"{BASE_URL}/{href.lstrip('/')}"

        # Metadata spans/labels.
        instancia = self._extract_labeled_text(container, "instancia")
        materia = self._extract_labeled_text(container, "materia")
        tesis_num = self._extract_labeled_text(container, "tesis")

        return {
            "registro": registro,
            "tipo": tipo,
            "epoca": epoca,
            "epoca_nombre": EPOCAS.get(epoca, f"Epoca {epoca}"),
            "instancia": instancia,
            "materia": materia,
            "tesis_num": tesis_num,
            "rubro": rubro,
            "texto": texto,
            "precedentes": "",
            "url": url,
            "source": "sjf_scjn",
        }

    def _parse_tesis_table_row(
        self, row: Any, tipo: str, epoca: int
    ) -> Optional[Dict[str, Any]]:
        """Extract a tesis record from a table row."""
        cells = row.find_all("td")
        if len(cells) < 2:
            return None

        rubro = cells[0].get_text(strip=True)
        if not rubro or len(rubro) < 5:
            return None

        registro = ""
        url = ""
        link = row.find("a", href=True)
        if link:
            href = link["href"]
            url = href if href.startswith("http") else f"{BASE_URL}/{href.lstrip('/')}"
            for segment in reversed(href.strip("/").split("/")):
                if segment.isdigit():
                    registro = segment
                    break

        return {
            "registro": registro,
            "tipo": tipo,
            "epoca": epoca,
            "epoca_nombre": EPOCAS.get(epoca, f"Epoca {epoca}"),
            "instancia": cells[1].get_text(strip=True) if len(cells) > 1 else "",
            "materia": cells[2].get_text(strip=True) if len(cells) > 2 else "",
            "tesis_num": cells[3].get_text(strip=True) if len(cells) > 3 else "",
            "rubro": rubro,
            "texto": cells[4].get_text(strip=True) if len(cells) > 4 else "",
            "precedentes": "",
            "url": url,
            "source": "sjf_scjn",
        }

    def _parse_tesis_dl(
        self, dl: Any, tipo: str, epoca: int
    ) -> Optional[Dict[str, Any]]:
        """Extract a tesis record from a definition list (dl/dt/dd)."""
        fields: Dict[str, str] = {}
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")

        for dt, dd in zip(dts, dds):
            key = dt.get_text(strip=True).lower().rstrip(":").strip()
            value = dd.get_text(strip=True)
            fields[key] = value

        rubro = (
            fields.get("rubro")
            or fields.get("titulo")
            or fields.get("localizacion")
            or ""
        )
        if not rubro:
            return None

        registro = fields.get("registro", "")
        url = ""
        if registro:
            url = f"{BASE_URL}/detalle/tesis/{registro}"

        return {
            "registro": registro,
            "tipo": tipo,
            "epoca": epoca,
            "epoca_nombre": EPOCAS.get(epoca, f"Epoca {epoca}"),
            "instancia": fields.get("instancia", ""),
            "materia": fields.get("materia", ""),
            "tesis_num": fields.get("tesis", fields.get("numero", "")),
            "rubro": rubro,
            "texto": fields.get("texto", fields.get("contenido", "")),
            "precedentes": fields.get("precedentes", ""),
            "url": url,
            "source": "sjf_scjn",
        }

    @staticmethod
    def _extract_labeled_text(container: Any, label: str) -> str:
        """
        Extract text following a label element inside a container.

        Handles patterns like:
            <span class="label">Materia:</span> <span>Civil</span>
            <strong>Instancia:</strong> Primera Sala
        """
        # By class name
        el = container.find(class_=lambda c: c and label.lower() in c.lower())
        if el:
            return el.get_text(strip=True)

        # By label text content
        for tag in container.find_all(["span", "strong", "b", "label"]):
            text = tag.get_text(strip=True).lower()
            if label.lower() in text:
                sibling = tag.find_next_sibling()
                if sibling:
                    return sibling.get_text(strip=True)
                # Text might be in the parent after the label tag.
                parent_text = tag.parent.get_text(strip=True) if tag.parent else ""
                parts = parent_text.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()

        return ""

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def save_batch(
        items: List[Dict[str, Any]],
        output_dir: str,
        batch_type: str,
        batch_number: int,
    ) -> Path:
        """
        Save a batch of tesis records to a numbered JSON file.

        Args:
            items: Tesis dicts to persist.
            output_dir: Root output directory.
            batch_type: Subdirectory name (jurisprudencia / tesis_aisladas).
            batch_number: Batch sequence number.

        Returns:
            Path to the written file.
        """
        out_path = Path(output_dir) / "judicial" / batch_type
        out_path.mkdir(parents=True, exist_ok=True)

        file_path = out_path / f"batch_{batch_number:04d}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)

        logger.info("Saved %d %s items to %s", len(items), batch_type, file_path)
        return file_path

    # ------------------------------------------------------------------
    # Bulk dump import
    # ------------------------------------------------------------------

    def import_bulk_dump(
        self,
        dump_path: str,
        output_dir: str,
    ) -> Dict[str, Any]:
        """
        Parse a CSV/JSON bulk data dump from the SCJN partnership into
        the standard tesis format.

        This method handles the institutional data dump when it arrives.
        Supports CSV and JSON input formats.

        Args:
            dump_path: Path to the bulk dump file (CSV or JSON).
            output_dir: Directory for output batch files.

        Returns:
            Summary dict with total_items, total_batches, output_dir.
        """
        dump_file = Path(dump_path)
        if not dump_file.exists():
            raise FileNotFoundError(f"Bulk dump not found: {dump_path}")

        suffix = dump_file.suffix.lower()
        logger.info("Importing bulk dump from %s (format: %s)", dump_path, suffix)

        if suffix == ".json":
            records = self._load_json_dump(dump_file)
        elif suffix == ".csv":
            records = self._load_csv_dump(dump_file)
        else:
            raise ValueError(
                f"Unsupported dump format: {suffix} (expected .json or .csv)"
            )

        # Normalize and batch-save.
        total_items = 0
        batch_number = 0
        current_batch: List[Dict[str, Any]] = []

        for raw in records:
            # Detect tipo from raw data.
            raw_tipo = str(
                raw.get("tipo", raw.get("Tipo", raw.get("type", "")))
            ).lower()
            if "jurisprudencia" in raw_tipo:
                tipo = "jurisprudencia"
            else:
                tipo = "tesis_aislada"

            # Detect epoca.
            raw_epoca = raw.get("epoca", raw.get("Epoca", 10))
            try:
                epoca = int(raw_epoca)
            except (ValueError, TypeError):
                epoca = 10

            normalized = self._normalize_tesis(raw, tipo, epoca)
            if normalized is None:
                continue

            current_batch.append(normalized)

            if len(current_batch) >= _BATCH_SIZE:
                batch_type = "mixed"  # Bulk dumps may contain both types.
                self.save_batch(current_batch, output_dir, batch_type, batch_number)
                total_items += len(current_batch)
                batch_number += 1
                current_batch = []

                if total_items % 1000 == 0:
                    logger.info(
                        "Bulk import progress: %d items processed",
                        total_items,
                    )

        # Save remaining items.
        if current_batch:
            self.save_batch(current_batch, output_dir, "mixed", batch_number)
            total_items += len(current_batch)
            batch_number += 1

        summary = {
            "total_items": total_items,
            "total_batches": batch_number,
            "output_dir": output_dir,
            "source_file": str(dump_file),
        }
        logger.info("Bulk import complete: %s", summary)
        return summary

    @staticmethod
    def _load_json_dump(path: Path) -> List[Dict[str, Any]]:
        """Load records from a JSON dump file (array or newline-delimited)."""
        content = path.read_text(encoding="utf-8").strip()

        # Try standard JSON array first.
        if content.startswith("["):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass

        # Fall back to newline-delimited JSON (NDJSON).
        records: List[Dict[str, Any]] = []
        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if isinstance(record, dict):
                    records.append(record)
            except json.JSONDecodeError:
                logger.warning("Skipping invalid JSON on line %d of %s", line_num, path)
        return records

    @staticmethod
    def _load_csv_dump(path: Path) -> List[Dict[str, Any]]:
        """Load records from a CSV dump file."""
        records: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))
        return records

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        output_dir: str = "data",
        tipo: str = "all",
        max_items: Optional[int] = None,
        resume_from: int = 0,
    ) -> Dict[str, Any]:
        """
        Run the full SCJN judicial scraping pipeline.

        1. Check open data portal for bulk datasets.
        2. If bulk data found, log instructions and return.
        3. Probe the SJF search API.
        4. Scrape jurisprudencia and/or tesis aisladas.

        Args:
            output_dir: Root directory for batch JSON files.
            tipo: What to scrape — "jurisprudencia", "tesis_aisladas", or "all".
            max_items: Maximum items per tipo (None = unlimited).
            resume_from: Item offset to resume from (0-based).

        Returns:
            Summary dict with results per tipo and probe findings.
        """
        logger.info(
            "Starting SCJN scraper (tipo=%s, max_items=%s, resume_from=%d)",
            tipo,
            max_items,
            resume_from,
        )

        summary: Dict[str, Any] = {
            "open_data": None,
            "search_api": None,
            "jurisprudencia": {"total_items": 0, "total_batches": 0},
            "tesis_aisladas": {"total_items": 0, "total_batches": 0},
            "output_dir": output_dir,
        }

        # Step 1: check open data portal.
        open_data = self.check_open_data()
        summary["open_data"] = open_data

        if open_data["found"]:
            logger.info(
                "=== BULK DATA FOUND ON OPEN DATA PORTAL ===\n"
                "Endpoint: %s\n"
                "Datasets: %d\n"
                "Download URLs: %d\n"
                "RECOMMENDATION: Use institutional data dump instead of "
                "scraping. Download from:\n%s",
                open_data["endpoint"],
                len(open_data["datasets"]),
                len(open_data["download_urls"]),
                "\n".join(f"  - {url}" for url in open_data["download_urls"][:10]),
            )
            return summary

        # Step 2: probe search API.
        search_api = self.probe_search_api()
        summary["search_api"] = search_api

        # Step 3: scrape based on tipo.
        if tipo in ("jurisprudencia", "all"):
            total_items = 0
            batch_number = 0

            for batch in self.scrape_jurisprudencia(
                max_items=max_items, resume_from=resume_from
            ):
                self.save_batch(batch, output_dir, "jurisprudencia", batch_number)
                total_items += len(batch)
                batch_number += 1

                if total_items % 100 == 0 or batch_number == 1:
                    logger.info(
                        "Jurisprudencia progress: %d items, %d batches",
                        total_items,
                        batch_number,
                    )

            summary["jurisprudencia"] = {
                "total_items": total_items,
                "total_batches": batch_number,
            }

        if tipo in ("tesis_aisladas", "all"):
            total_items = 0
            batch_number = 0

            for batch in self.scrape_tesis_aisladas(
                max_items=max_items, resume_from=resume_from
            ):
                self.save_batch(batch, output_dir, "tesis_aisladas", batch_number)
                total_items += len(batch)
                batch_number += 1

                if total_items % 100 == 0 or batch_number == 1:
                    logger.info(
                        "Tesis aisladas progress: %d items, %d batches",
                        total_items,
                        batch_number,
                    )

            summary["tesis_aisladas"] = {
                "total_items": total_items,
                "total_batches": batch_number,
            }

        logger.info("SCJN scraper complete: %s", summary)
        return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the SCJN judicial scraper."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description=(
            "SCJN judicial corpus scraper. "
            "Fallback for when institutional data dump is unavailable."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data",
        help="Root directory for output files (default: data).",
    )
    parser.add_argument(
        "--tipo",
        type=str,
        choices=["jurisprudencia", "tesis_aisladas", "all"],
        default="all",
        help="Type of judicial records to scrape (default: all).",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Maximum items to scrape per tipo (default: unlimited).",
    )
    parser.add_argument(
        "--resume-from",
        type=int,
        default=0,
        help="Item offset to resume from (0-based, default: 0).",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only probe endpoints, do not scrape.",
    )
    parser.add_argument(
        "--import-dump",
        type=str,
        default=None,
        help="Path to bulk dump file (CSV/JSON) from SCJN partnership.",
    )

    args = parser.parse_args()

    scraper = ScjnScraper()

    # Import mode: parse a bulk data dump.
    if args.import_dump:
        result = scraper.import_bulk_dump(args.import_dump, args.output_dir)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Check-only mode: probe endpoints without scraping.
    if args.check_only:
        print("=== Open Data Portal Probe ===")
        open_data = scraper.check_open_data()
        print(json.dumps(open_data, indent=2, ensure_ascii=False))

        print("\n=== SJF Search API Probe ===")
        search_api = scraper.probe_search_api()
        print(json.dumps(search_api, indent=2, ensure_ascii=False))
        return

    # Full scrape mode.
    result = scraper.run(
        output_dir=args.output_dir,
        tipo=args.tipo,
        max_items=args.max_items,
        resume_from=args.resume_from,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
