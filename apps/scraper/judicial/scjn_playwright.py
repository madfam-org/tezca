"""
SCJN Judicial Playwright Scraper (W3 — Phase 17)

Browser-based scraper for the Semanario Judicial de la Federación (SJF).
The SJF portal renders search results via JavaScript, making it inaccessible
to requests-based scrapers. Uses Playwright to automate Chromium.

Architecture:
    1. Launch Chromium via PlaywrightBase
    2. Navigate to SJF search interface
    3. Fill search form: epoca, materia, tipo filters
    4. Wait for JS-rendered results table to populate
    5. Extract record fields: registro, rubro, texto, epoca, instancia, materia
    6. Paginate via "Siguiente" button clicks
    7. Checkpoint every 100 items, save batches

Epoch-by-epoch strategy:
    1. Epoch 11 first (~10K items, fastest validation)
    2. Epoch 10 (~60K jurisprudencia, highest legal value)
    3. Epochs 9→1 (historical, lower priority)

Open data probe first — datos.scjn.gob.mx may have bulk CSV/JSON.

Usage:
    python -m apps.scraper.judicial.scjn_playwright --check-only
    python -m apps.scraper.judicial.scjn_playwright --epoca 11 --max-items 500
    python -m apps.scraper.judicial.scjn_playwright --epoca 10 --tipo jurisprudencia
    python -m apps.scraper.judicial.scjn_playwright --no-headless
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeout

from apps.scraper.judicial.scjn_scraper import EPOCAS, ScjnScraper
from apps.scraper.playwright_base import PlaywrightBase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SJF_BASE_URL = "https://sjfsemanal.scjn.gob.mx"
SJF_BASE_URL_LEGACY = "https://sjf.scjn.gob.mx"
# The SJF search interface lives on a separate subdomain (as of 2026)
SJF_SEARCH_URL = "https://sjfsemanal.scjn.gob.mx/busqueda-principal-tesis"
SJF_SEARCH_URL_LEGACY = "https://sjf2.scjn.gob.mx/busqueda-principal-tesis"
SJF_DETAIL_URL = "https://sjfsemanal.scjn.gob.mx/detalle/tesis"

_BATCH_SIZE = 50
_CHECKPOINT_EVERY = 100  # items
_MAX_EMPTY_PAGES = 5  # consecutive empty pages before stopping
_RESULT_WAIT_TIMEOUT = 15_000  # 15s for JS results to render
_ENRICH_CHECKPOINT_EVERY = 50  # items between enrichment checkpoints
_ENRICH_RATE_LIMIT = 1.5  # seconds between detail page fetches


class ScjnPlaywrightScraper(PlaywrightBase):
    """
    Browser-based scraper for the SCJN Semanario Judicial de la Federación.

    Inherits browser lifecycle, WAF handling, checkpointing from PlaywrightBase.
    Implements SJF-specific search form interaction and result extraction.
    """

    def __init__(
        self,
        headless: bool = True,
        output_dir: str = "data/judicial",
    ) -> None:
        super().__init__(
            headless=headless,
            output_dir=output_dir,
            page_load_delay=1.5,  # Respectful rate for judicial portal
            checkpoint_interval=5,
            batch_size=_BATCH_SIZE,
        )
        self._total_items = 0
        self._epoca: int = 10
        self._tipo: str = "jurisprudencia"

    # ------------------------------------------------------------------
    # Search form interaction
    # ------------------------------------------------------------------

    def _navigate_to_search(self) -> bool:
        """Navigate to the SJF search interface and wait for form."""
        # Try the current search URL first, then legacy subdomain
        search_urls = [
            SJF_SEARCH_URL,
            SJF_SEARCH_URL_LEGACY,
            f"{SJF_BASE_URL}/SJFHome/home",
            SJF_BASE_URL,
        ]
        for url in search_urls:
            if self._navigate(url):
                # Check if we actually got a search page (not a 404 or redirect)
                title = self._page.title() if self._page else ""
                current_url = self._page.url if self._page else ""
                if "404" not in title and "Error" not in title:
                    logger.info(
                        "Search page loaded: %s (title: %s)", current_url, title[:60]
                    )
                    return True
        return False

    def _fill_search_form(self, epoca: int, tipo: str) -> bool:
        """Fill and submit the SJF search form.

        Args:
            epoca: Judicial epoch number (1-11).
            tipo: "jurisprudencia" or "tesis_aislada".

        Returns:
            True if form was found and submitted.
        """
        if not self._page:
            return False

        try:
            # Wait for any search form to be ready
            self._page.wait_for_load_state("networkidle", timeout=10_000)

            # Strategy 1: Look for select/input elements by name or label
            form_filled = False

            # Try to find and fill epoca selector
            epoca_selectors = [
                f"select[name*='epoca'] >> option[value='{epoca}']",
                f"select[name*='Epoca'] >> option[value='{epoca}']",
                f"#epoca option[value='{epoca}']",
            ]
            for selector in epoca_selectors:
                try:
                    self._page.locator(selector).first.click(timeout=3000)
                    form_filled = True
                    break
                except Exception:
                    continue

            if not form_filled:
                # Try generic dropdown approach
                try:
                    selects = self._page.query_selector_all("select")
                    for select in selects:
                        name = (select.get_attribute("name") or "").lower()
                        if "epoca" in name or "epoch" in name:
                            select.select_option(value=str(epoca))
                            form_filled = True
                            break
                except Exception:
                    pass

            # Try to set tipo (jurisprudencia vs tesis aislada)
            tipo_value = "J" if tipo == "jurisprudencia" else "TA"
            tipo_selectors = [
                f"select[name*='tipo'] >> option[value='{tipo_value}']",
                f"input[name*='tipo'][value='{tipo_value}']",
                f"input[type='radio'][value='{tipo_value}']",
            ]
            for selector in tipo_selectors:
                try:
                    self._page.locator(selector).first.click(timeout=3000)
                    break
                except Exception:
                    continue

            # Submit the form
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Buscar')",
                "a:has-text('Buscar')",
                "#btnBuscar",
                ".btn-search",
            ]
            for selector in submit_selectors:
                try:
                    btn = self._page.query_selector(selector)
                    if btn and btn.is_visible():
                        btn.click()
                        logger.info("Search submitted via: %s", selector)
                        return True
                except Exception:
                    continue

            # If no submit button found, try pressing Enter
            try:
                self._page.keyboard.press("Enter")
                return True
            except Exception:
                pass

            logger.warning("Could not find or submit search form")
            self._screenshot("no_search_form")
            return form_filled

        except PlaywrightTimeout:
            logger.warning("Search form interaction timed out")
            self._screenshot("search_form_timeout")
            return False

    # ------------------------------------------------------------------
    # Result extraction
    # ------------------------------------------------------------------

    def _wait_for_results(self) -> bool:
        """Wait for JavaScript-rendered search results to appear."""
        if not self._page:
            return False

        result_selectors = [
            ".resultado",
            ".tesis-item",
            ".result-item",
            "table tbody tr",
            "article",
            "[class*='result']",
            "[class*='tesis']",
            "dl",
        ]

        for selector in result_selectors:
            try:
                self._page.wait_for_selector(
                    selector,
                    state="visible",
                    timeout=_RESULT_WAIT_TIMEOUT,
                )
                logger.debug("Results appeared with selector: %s", selector)
                return True
            except PlaywrightTimeout:
                continue
            except Exception:
                continue

        logger.debug("No results appeared within timeout")
        return False

    def _parse_page(self) -> List[Dict[str, Any]]:
        """Extract judicial records from the current page DOM.

        Tries multiple extraction strategies to handle SJF layout variations.

        Returns:
            List of normalized judicial record dicts.
        """
        if not self._page:
            return []

        items: List[Dict[str, Any]] = []

        # Strategy 1: Structured result containers
        containers = self._page.query_selector_all(
            ".resultado, .tesis-item, .result-item, article"
        )
        if containers:
            logger.debug("Found %d result containers.", len(containers))
            for container in containers:
                record = self._extract_from_container(container)
                if record:
                    items.append(record)
            if items:
                return items

        # Strategy 2: Table rows
        rows = self._page.query_selector_all("table tbody tr")
        if rows:
            logger.debug("Found %d table rows.", len(rows))
            for row in rows:
                record = self._extract_from_table_row(row)
                if record:
                    items.append(record)
            if items:
                return items

        # Strategy 3: Definition lists (dl/dt/dd)
        dls = self._page.query_selector_all("dl")
        if dls:
            logger.debug("Found %d definition lists.", len(dls))
            for dl in dls:
                record = self._extract_from_dl(dl)
                if record:
                    items.append(record)
            if items:
                return items

        # Strategy 4: Any links with tesis-like patterns
        links = self._page.query_selector_all("a[href*='tesis'], a[href*='detalle']")
        for link in links:
            try:
                text = (link.inner_text() or "").strip()
                if text and len(text) > 20:
                    href = link.get_attribute("href") or ""
                    url = (
                        href
                        if href.startswith("http")
                        else f"{SJF_BASE_URL}/{href.lstrip('/')}"
                    )

                    registro = ""
                    for segment in reversed(href.strip("/").split("/")):
                        if segment.isdigit():
                            registro = segment
                            break

                    items.append(
                        self._make_record(rubro=text, registro=registro, url=url)
                    )
            except Exception:
                continue

        return items

    def _extract_from_container(self, container) -> Optional[Dict[str, Any]]:
        """Extract a judicial record from a result container element."""
        try:
            # Title/rubro
            title_el = container.query_selector(
                "h2, h3, h4, strong, b, .rubro, .titulo"
            )
            rubro = (title_el.inner_text() if title_el else "").strip()
            if not rubro or len(rubro) < 10:
                return None

            # Full text
            text_el = container.query_selector("[class*='texto'], .contenido, p")
            texto = (text_el.inner_text() if text_el else "").strip()

            # Registro number from link
            registro = ""
            url = ""
            link = container.query_selector("a[href]")
            if link:
                href = link.get_attribute("href") or ""
                url = (
                    href
                    if href.startswith("http")
                    else f"{SJF_BASE_URL}/{href.lstrip('/')}"
                )
                for segment in reversed(href.strip("/").split("/")):
                    if segment.isdigit():
                        registro = segment
                        break

            # Metadata labels
            instancia = self._extract_label(container, "instancia")
            materia = self._extract_label(container, "materia")
            tesis_num = self._extract_label(container, "tesis")

            return self._make_record(
                registro=registro,
                rubro=rubro,
                texto=texto,
                instancia=instancia,
                materia=materia,
                tesis_num=tesis_num,
                url=url,
            )

        except Exception:
            logger.debug("Failed to parse container", exc_info=True)
            return None

    def _extract_from_table_row(self, row) -> Optional[Dict[str, Any]]:
        """Extract a judicial record from a table row."""
        try:
            cells = row.query_selector_all("td")
            if len(cells) < 2:
                return None

            rubro = (cells[0].inner_text() or "").strip()
            if not rubro or len(rubro) < 10:
                return None

            registro = ""
            url = ""
            link = row.query_selector("a[href]")
            if link:
                href = link.get_attribute("href") or ""
                url = (
                    href
                    if href.startswith("http")
                    else f"{SJF_BASE_URL}/{href.lstrip('/')}"
                )
                for segment in reversed(href.strip("/").split("/")):
                    if segment.isdigit():
                        registro = segment
                        break

            return self._make_record(
                registro=registro,
                rubro=rubro,
                instancia=(
                    (cells[1].inner_text() or "").strip() if len(cells) > 1 else ""
                ),
                materia=(cells[2].inner_text() or "").strip() if len(cells) > 2 else "",
                tesis_num=(
                    (cells[3].inner_text() or "").strip() if len(cells) > 3 else ""
                ),
                texto=(cells[4].inner_text() or "").strip() if len(cells) > 4 else "",
                url=url,
            )
        except Exception:
            return None

    def _extract_from_dl(self, dl) -> Optional[Dict[str, Any]]:
        """Extract a judicial record from a definition list."""
        try:
            fields: Dict[str, str] = {}
            dts = dl.query_selector_all("dt")
            dds = dl.query_selector_all("dd")

            for dt, dd in zip(dts, dds):
                key = (dt.inner_text() or "").strip().lower().rstrip(":")
                value = (dd.inner_text() or "").strip()
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
            url = f"{SJF_DETAIL_URL}/{registro}" if registro else ""

            return self._make_record(
                registro=registro,
                rubro=rubro,
                texto=fields.get("texto", fields.get("contenido", "")),
                instancia=fields.get("instancia", ""),
                materia=fields.get("materia", ""),
                tesis_num=fields.get("tesis", fields.get("numero", "")),
                url=url,
            )
        except Exception:
            return None

    def _extract_label(self, container, label: str) -> str:
        """Extract text associated with a label inside a container."""
        try:
            # By class name
            el = container.query_selector(f"[class*='{label}']")
            if el:
                return (el.inner_text() or "").strip()

            # By text content in label elements
            labels = container.query_selector_all("span, strong, b, label")
            for tag in labels:
                text = (tag.inner_text() or "").strip().lower()
                if label.lower() in text:
                    sibling = tag.evaluate(
                        "el => el.nextElementSibling && el.nextElementSibling.textContent"
                    )
                    if sibling:
                        return sibling.strip()
        except Exception:
            pass
        return ""

    def _make_record(self, **kwargs) -> Dict[str, Any]:
        """Create a normalized judicial record dict."""
        registro = kwargs.get("registro", "")
        url = kwargs.get("url", "")
        if not url and registro:
            url = f"{SJF_DETAIL_URL}/{registro}"

        return {
            "registro": registro,
            "tipo": self._tipo,
            "epoca": self._epoca,
            "epoca_nombre": EPOCAS.get(self._epoca, f"Epoca {self._epoca}"),
            "instancia": kwargs.get("instancia", ""),
            "materia": kwargs.get("materia", ""),
            "tesis_num": kwargs.get("tesis_num", ""),
            "rubro": kwargs.get("rubro", ""),
            "texto": kwargs.get("texto", ""),
            "precedentes": kwargs.get("precedentes", ""),
            "url": url,
            "source": "sjf_scjn_playwright",
        }

    # ------------------------------------------------------------------
    # Detail page enrichment
    # ------------------------------------------------------------------

    def _fetch_detail_page(self, registro: str) -> Dict[str, str]:
        """Fetch and parse a single SJF detail page for full record fields.

        Navigates to sjfsemanal.scjn.gob.mx/detalle/tesis/{registro} and
        extracts labeled fields from the rendered page text.

        Args:
            registro: The registro digital number.

        Returns:
            Dict of extracted fields (materia, tesis_num, instancia, ponente,
            rubro, texto). Empty strings for fields not found.
        """
        if not self._page:
            return {}

        url = f"{SJF_DETAIL_URL}/{registro}"
        fields: Dict[str, str] = {}

        try:
            self._page.goto(url, wait_until="networkidle", timeout=30_000)
            time.sleep(3)  # SPA rendering time

            raw_text = self._page.inner_text("body")
            if not raw_text or len(raw_text) < 100:
                logger.debug("Detail page empty for registro %s", registro)
                return fields

            # Extract labeled fields via regex
            label_patterns = {
                "materia": r"Materia\(s\):\s*(.+)",
                "tesis_num": r"Tesis:\s*(.+)",
                "instancia": r"Instancia:\s*(.+)",
                "ponente": r"Ponente:\s*(.+)",
                "tipo_tesis": r"Tipo:\s*(.+)",
            }
            for key, pattern in label_patterns.items():
                match = re.search(pattern, raw_text)
                if match:
                    fields[key] = match.group(1).strip()

            # Extract rubro: first ALL-CAPS paragraph after metadata section.
            # Typically appears after "Fuente:" or the publication timestamp line.
            lines = raw_text.split("\n")
            rubro_start = None
            rubro_lines: List[str] = []
            in_rubro = False

            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped:
                    if in_rubro and rubro_lines:
                        break  # end of rubro block
                    continue

                # Skip metadata labels
                if any(
                    stripped.startswith(lbl)
                    for lbl in (
                        "Registro digital:",
                        "Materia(s):",
                        "Tesis:",
                        "Instancia:",
                        "Tipo:",
                        "Fuente:",
                        "Publicación:",
                        "Ponente:",
                    )
                ):
                    continue

                # Detect rubro: paragraph that is mostly uppercase, length > 20
                if (
                    not in_rubro
                    and len(stripped) > 20
                    and sum(1 for c in stripped if c.isupper()) / max(len(stripped), 1)
                    > 0.6
                ):
                    in_rubro = True
                    rubro_start = i
                    rubro_lines.append(stripped)
                elif in_rubro:
                    # Continue rubro if still mostly uppercase or continuation
                    if (
                        sum(1 for c in stripped if c.isupper()) / max(len(stripped), 1)
                        > 0.5
                        or len(stripped) < 30
                    ):
                        rubro_lines.append(stripped)
                    else:
                        break

            if rubro_lines:
                fields["rubro"] = " ".join(rubro_lines)

            # Extract texto: content between rubro and the court name line
            # Court name lines: "PLENO.", "PRIMERA SALA.", "SEGUNDA SALA.", etc.
            court_pattern = re.compile(
                r"^(PLENO|PRIMERA SALA|SEGUNDA SALA|"
                r"TRIBUNAL COLEGIADO|TRIBUNAL PLENO)\.",
                re.IGNORECASE,
            )
            if rubro_start is not None:
                texto_lines: List[str] = []
                started = False
                for line in lines[rubro_start + len(rubro_lines) :]:
                    stripped = line.strip()
                    if not stripped:
                        if started:
                            texto_lines.append("")
                        continue
                    if court_pattern.match(stripped):
                        break
                    started = True
                    texto_lines.append(stripped)
                texto = "\n".join(texto_lines).strip()
                if texto and len(texto) > 50:
                    fields["texto"] = texto

            # Debug screenshot on first successful extraction
            if fields.get("rubro") and not hasattr(self, "_detail_screenshot_taken"):
                self._screenshot("detail_enrichment_sample")
                self._detail_screenshot_taken = True

        except PlaywrightTimeout:
            logger.debug("Detail page timeout for registro %s", registro)
        except Exception:
            logger.debug("Detail page error for registro %s", registro, exc_info=True)

        return fields

    def _enrich_records(self, records: List[Dict]) -> List[Dict]:
        """Enrich records by fetching detail pages for those missing texto.

        Args:
            records: List of judicial record dicts from scrape_catalog().

        Returns:
            The same list with enriched fields merged in.
        """
        needs_enrichment = [(i, r) for i, r in enumerate(records) if not r.get("texto")]
        if not needs_enrichment:
            logger.info(
                "All %d records already have texto, skipping enrichment.", len(records)
            )
            return records

        logger.info(
            "Enriching %d/%d records missing texto...",
            len(needs_enrichment),
            len(records),
        )

        enriched_count = 0
        for idx, (orig_idx, record) in enumerate(needs_enrichment, 1):
            registro = record.get("registro")
            if not registro:
                continue

            detail = self._fetch_detail_page(registro)
            if detail:
                # Merge non-empty fields into record
                for key, value in detail.items():
                    if value and not record.get(key):
                        record[key] = value
                if detail.get("rubro") or detail.get("texto"):
                    enriched_count += 1

            # Rate limit
            time.sleep(_ENRICH_RATE_LIMIT)

            # Checkpoint and partial save
            if idx % _ENRICH_CHECKPOINT_EVERY == 0:
                self._save_checkpoint(
                    0,
                    records,
                    extra={
                        "epoca": self._epoca,
                        "tipo": self._tipo,
                        "enrichment_progress": idx,
                        "enrichment_total": len(needs_enrichment),
                    },
                )
                subdir = (
                    "jurisprudencia"
                    if self._tipo == "jurisprudencia"
                    else "tesis_aisladas"
                )
                partial_path = (
                    self._output_dir / subdir / f"enriched_partial_{idx}.json"
                )
                partial_path.parent.mkdir(parents=True, exist_ok=True)
                with open(partial_path, "w", encoding="utf-8") as f:
                    json.dump(records, f, indent=2, ensure_ascii=False)

                logger.info(
                    "Enrichment progress: %d/%d (enriched: %d)",
                    idx,
                    len(needs_enrichment),
                    enriched_count,
                )

        logger.info(
            "Enrichment complete: %d/%d records enriched with detail page data.",
            enriched_count,
            len(needs_enrichment),
        )
        return records

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def scrape_catalog(
        self,
        max_pages: Optional[int] = None,
        resume_from_page: int = 0,
    ) -> List[Dict[str, Any]]:
        """Paginate through SJF search results.

        Uses button-click pagination since the SJF portal is JS-rendered.

        Args:
            max_pages: Max pages to scrape (None = unlimited).
            resume_from_page: Page to start from.

        Returns:
            All extracted judicial records.
        """
        all_items: List[Dict[str, Any]] = []
        pages_scraped = 0
        empty_streak = 0
        batch_number = 0

        while True:
            if max_pages is not None and pages_scraped >= max_pages:
                logger.info("Reached max_pages=%d, stopping.", max_pages)
                break

            # Wait for results to render
            has_results = self._wait_for_results()
            if not has_results:
                # First page may need search submission
                if pages_scraped == 0:
                    logger.info("No results on first page — form may need interaction")
                    self._screenshot("no_initial_results")

            items = self._parse_page()

            if not items:
                empty_streak += 1
                logger.info(
                    "No items on page %d (empty streak: %d/%d).",
                    resume_from_page + pages_scraped,
                    empty_streak,
                    _MAX_EMPTY_PAGES,
                )
                if empty_streak >= _MAX_EMPTY_PAGES:
                    logger.info("Max empty pages reached, assuming end of results.")
                    break

                # Try clicking next anyway
                if not self._try_click_next():
                    break
                self._rate_limit()
                pages_scraped += 1
                continue

            empty_streak = 0
            all_items.extend(items)
            pages_scraped += 1
            self._total_items += len(items)

            logger.info(
                "Page %d: found %d items (total: %d, pages: %d).",
                resume_from_page + pages_scraped,
                len(items),
                len(all_items),
                pages_scraped,
            )

            # Save batches
            while len(all_items) >= (batch_number + 1) * _BATCH_SIZE:
                start = batch_number * _BATCH_SIZE
                batch = all_items[start : start + _BATCH_SIZE]
                subdir = (
                    "jurisprudencia"
                    if self._tipo == "jurisprudencia"
                    else "tesis_aisladas"
                )
                self.save_batch(batch, batch_number, subdirectory=subdir)
                batch_number += 1

            # Checkpoint
            if self._total_items % _CHECKPOINT_EVERY < len(items):
                self._save_checkpoint(
                    resume_from_page + pages_scraped,
                    all_items,
                    extra={"epoca": self._epoca, "tipo": self._tipo},
                )

            # Paginate
            if not self._try_click_next():
                logger.info("No next button found, assuming last page.")
                break

            self._rate_limit()

        # Save remaining items
        remaining_start = batch_number * _BATCH_SIZE
        if remaining_start < len(all_items):
            subdir = (
                "jurisprudencia" if self._tipo == "jurisprudencia" else "tesis_aisladas"
            )
            self.save_batch(
                all_items[remaining_start:], batch_number, subdirectory=subdir
            )

        return all_items

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def run(
        self,
        epoca: int = 10,
        tipo: str = "jurisprudencia",
        max_pages: Optional[int] = None,
        max_items: Optional[int] = None,
        resume_from_page: int = 0,
        enrich: bool = True,
    ) -> Dict[str, Any]:
        """Run the full SCJN Playwright scraping pipeline.

        1. Optionally probe open data portal for bulk dumps.
        2. Launch browser and navigate to SJF search.
        3. Fill search form for the target epoca/tipo.
        4. Paginate and extract records.
        5. Enrich records with detail page data.

        Args:
            epoca: Judicial epoch number (default: 10, Décima Época).
            tipo: "jurisprudencia" or "tesis_aislada".
            max_pages: Max pages to scrape.
            max_items: Max items to collect (approximate).
            resume_from_page: Page to resume from.
            enrich: Whether to enrich records via detail pages (default True).

        Returns:
            Summary dict.
        """
        self._epoca = epoca
        self._tipo = tipo

        logger.info(
            "Starting SCJN Playwright scraper (epoca=%d, tipo=%s, headless=%s)",
            epoca,
            tipo,
            self._headless,
        )

        summary: Dict[str, Any] = {
            "epoca": epoca,
            "tipo": tipo,
            "total_items": 0,
            "output_dir": str(self._output_dir),
        }

        try:
            self._launch()

            # Navigate to search
            if not self._navigate_to_search():
                logger.error("Cannot reach SJF search at %s", SJF_SEARCH_URL)
                summary["error"] = "navigation_failed"
                return summary

            # Fill and submit search form
            self._fill_search_form(epoca, tipo)

            # Allow JS rendering time
            time.sleep(3)

            # Compute max_pages from max_items if needed
            effective_max_pages = max_pages
            if max_items and not max_pages:
                # Estimate ~20 items per page
                effective_max_pages = (max_items // 20) + 2

            # Scrape
            items = self.scrape_catalog(
                max_pages=effective_max_pages,
                resume_from_page=resume_from_page,
            )

            if max_items and len(items) > max_items:
                items = items[:max_items]

            # Enrich records with detail page data
            if enrich and items:
                items = self._enrich_records(items)
                enriched = sum(1 for it in items if it.get("texto"))
                summary["enriched_count"] = enriched

            # Save consolidated results
            filename = f"scjn_{tipo}_epoca{epoca}.json"
            self.save_results(items, filename=filename)

            summary["total_items"] = len(items)
            summary["total_scraped"] = len(items)
            logger.info("SCJN Playwright scraper complete: %d items", len(items))
            return summary

        except Exception as exc:
            logger.error("SCJN scraper failed: %s", exc, exc_info=True)
            self._screenshot("fatal_error")
            summary["error"] = str(exc)
            return summary

        finally:
            self.close()

    def run_enrich_only(
        self,
        input_path: str,
        epoca: int = 10,
        tipo: str = "jurisprudencia",
    ) -> Dict[str, Any]:
        """Load existing results and run enrichment without re-searching.

        Args:
            input_path: Path to existing JSON results file.
            epoca: Epoch for record metadata.
            tipo: Type for record metadata.

        Returns:
            Summary dict.
        """
        self._epoca = epoca
        self._tipo = tipo

        logger.info("Enrich-only mode: loading %s", input_path)

        with open(input_path, "r", encoding="utf-8") as f:
            items = json.load(f)

        summary: Dict[str, Any] = {
            "epoca": epoca,
            "tipo": tipo,
            "input_path": input_path,
            "total_items": len(items),
            "output_dir": str(self._output_dir),
        }

        try:
            self._launch()
            items = self._enrich_records(items)
            enriched = sum(1 for it in items if it.get("texto"))
            summary["enriched_count"] = enriched

            filename = f"scjn_{tipo}_epoca{epoca}_enriched.json"
            self.save_results(items, filename=filename)

            logger.info("Enrich-only complete: %d/%d enriched", enriched, len(items))
            return summary

        except Exception as exc:
            logger.error("Enrich-only failed: %s", exc, exc_info=True)
            summary["error"] = str(exc)
            return summary

        finally:
            self.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="SCJN judicial Playwright scraper for SJF portal (Phase 17 W3).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/judicial",
        help="Root output directory (default: data/judicial).",
    )
    parser.add_argument(
        "--epoca",
        type=int,
        default=11,
        choices=list(EPOCAS.keys()),
        help="Judicial epoch to scrape (default: 11, Undécima Época).",
    )
    parser.add_argument(
        "--tipo",
        type=str,
        choices=["jurisprudencia", "tesis_aislada"],
        default="jurisprudencia",
        help="Record type (default: jurisprudencia).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Max pages to scrape.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Max items to collect.",
    )
    parser.add_argument(
        "--resume-from",
        type=int,
        default=None,
        help="Page to resume from (loads checkpoint if not specified).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        dest="headless",
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run with visible browser window.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only probe SCJN open data portal, do not scrape.",
    )
    parser.add_argument(
        "--enrich-only",
        type=str,
        default=None,
        metavar="FILE",
        help="Load existing results JSON and run detail page enrichment only.",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip detail page enrichment after scraping.",
    )

    args = parser.parse_args()

    # Check-only mode: use the existing HTTP-based ScjnScraper
    if args.check_only:
        http_scraper = ScjnScraper()
        print("=== Open Data Portal Probe ===")
        open_data = http_scraper.check_open_data()
        print(json.dumps(open_data, indent=2, ensure_ascii=False))
        print("\n=== SJF Search API Probe ===")
        search_api = http_scraper.probe_search_api()
        print(json.dumps(search_api, indent=2, ensure_ascii=False))
        return

    scraper = ScjnPlaywrightScraper(
        headless=args.headless,
        output_dir=args.output_dir,
    )

    # Enrich-only mode: load existing results and enrich
    if args.enrich_only:
        result = scraper.run_enrich_only(
            input_path=args.enrich_only,
            epoca=args.epoca,
            tipo=args.tipo,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Determine resume page
    resume_from = 0
    if args.resume_from is not None:
        resume_from = args.resume_from
    else:
        checkpoint = scraper.load_checkpoint()
        if checkpoint:
            resume_from = checkpoint["current_page"] + 1
            logger.info(
                "Resuming from checkpoint: page %d (%d items previously collected).",
                resume_from,
                checkpoint["items_collected"],
            )

    result = scraper.run(
        epoca=args.epoca,
        tipo=args.tipo,
        max_pages=args.max_pages,
        max_items=args.max_items,
        resume_from_page=resume_from,
        enrich=not args.no_enrich,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
