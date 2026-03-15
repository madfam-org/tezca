"""
CONAMER CNARTyS Playwright Scraper

Browser-based scraper for catalogonacional.gob.mx using headless Chromium.
The site blocks automated HTTP requests with a WAF (403), so we use
Playwright to render the page in a real browser context.

Complements conamer_scraper.py which provides the requests-based approach
and dedup/normalization utilities.

Now inherits from PlaywrightBase for shared browser lifecycle, WAF handling,
navigation, and checkpointing.

Usage:
    python -m apps.scraper.federal.conamer_playwright
    python -m apps.scraper.federal.conamer_playwright --max-pages 10
    python -m apps.scraper.federal.conamer_playwright --resume-from 5
    python -m apps.scraper.federal.conamer_playwright --no-headless
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeout

from apps.scraper.federal.conamer_scraper import (
    _STOP_WORDS,
    _normalise_title,
    _strip_accents,
)
from apps.scraper.playwright_base import PlaywrightBase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://catalogonacional.gob.mx"


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class ConamerPlaywrightScraper(PlaywrightBase):
    """
    Browser-based scraper for CONAMER's catalogonacional.gob.mx.

    Inherits browser lifecycle, WAF handling, navigation, and checkpointing
    from PlaywrightBase. Implements CONAMER-specific page parsing and
    catalog pagination.
    """

    def __init__(
        self,
        headless: bool = True,
        output_dir: str = "data/conamer",
    ) -> None:
        super().__init__(
            headless=headless,
            output_dir=output_dir,
        )

    # ------------------------------------------------------------------
    # Page parsing
    # ------------------------------------------------------------------

    def _parse_page(self) -> List[Dict[str, Any]]:
        """
        Extract regulation entries from the current DOM.

        Tries multiple strategies to handle different page layouts:
        1. Table rows (most common for catalog-style pages)
        2. Card/list-item patterns
        3. Generic link extraction as fallback

        Returns:
            List of regulation dicts extracted from the page.
        """
        if not self._page:
            return []

        items: List[Dict[str, Any]] = []

        # Strategy 1: Table rows
        rows = self._page.query_selector_all("table tbody tr")
        if rows:
            logger.debug("Found %d table rows.", len(rows))
            for row in rows:
                try:
                    cells = row.query_selector_all("td")
                    if len(cells) < 2:
                        continue

                    name = (cells[0].inner_text() or "").strip()
                    if not name or len(name) < 5:
                        continue

                    link = row.query_selector("a[href]")
                    url = ""
                    if link:
                        href = link.get_attribute("href") or ""
                        url = (
                            href
                            if href.startswith("http")
                            else f"{BASE_URL}/{href.lstrip('/')}"
                        )

                    items.append(
                        {
                            "id": "",
                            "name": name,
                            "issuing_body": (
                                (cells[1].inner_text() or "").strip()
                                if len(cells) > 1
                                else ""
                            ),
                            "date": (
                                (cells[2].inner_text() or "").strip()
                                if len(cells) > 2
                                else ""
                            ),
                            "url": url,
                            "regulation_type": (
                                (cells[3].inner_text() or "").strip()
                                if len(cells) > 3
                                else ""
                            ),
                            "source": "conamer_cnartys_playwright",
                        }
                    )
                except Exception:
                    logger.debug("Failed to parse table row.", exc_info=True)
                    continue

            if items:
                return items

        # Strategy 2: Card/list-item patterns
        card_selectors = [
            ".card",
            ".list-item",
            ".regulacion-item",
            "article",
            ".resultado",
            ".item-regulacion",
            "[class*='regulacion']",
            "[class*='result']",
        ]

        for selector in card_selectors:
            cards = self._page.query_selector_all(selector)
            if not cards:
                continue

            logger.debug("Found %d elements with selector '%s'.", len(cards), selector)
            for card in cards:
                try:
                    title_el = card.query_selector(
                        "h2, h3, h4, a, strong, .title, .nombre"
                    )
                    if not title_el:
                        continue

                    name = (title_el.inner_text() or "").strip()
                    if not name or len(name) < 5:
                        continue

                    link = card.query_selector("a[href]")
                    url = ""
                    if link:
                        href = link.get_attribute("href") or ""
                        url = (
                            href
                            if href.startswith("http")
                            else f"{BASE_URL}/{href.lstrip('/')}"
                        )

                    items.append(
                        {
                            "id": "",
                            "name": name,
                            "issuing_body": "",
                            "date": "",
                            "url": url,
                            "regulation_type": "",
                            "source": "conamer_cnartys_playwright",
                        }
                    )
                except Exception:
                    logger.debug("Failed to parse card element.", exc_info=True)
                    continue

            if items:
                return items

        # Strategy 3: Broad link extraction as last resort
        links = self._page.query_selector_all("a[href]")
        for link in links:
            try:
                name = (link.inner_text() or "").strip()
                if not name or len(name) < 10:
                    continue
                # Skip navigation links
                if name.lower() in {
                    "inicio",
                    "home",
                    "siguiente",
                    "anterior",
                    "next",
                    "prev",
                    "buscar",
                    "search",
                }:
                    continue
                href = link.get_attribute("href") or ""
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue

                url = (
                    href
                    if href.startswith("http")
                    else f"{BASE_URL}/{href.lstrip('/')}"
                )

                items.append(
                    {
                        "id": "",
                        "name": name,
                        "issuing_body": "",
                        "date": "",
                        "url": url,
                        "regulation_type": "",
                        "source": "conamer_cnartys_playwright",
                    }
                )
            except Exception:
                continue

        if items:
            logger.info("Fallback link extraction found %d items.", len(items))

        return items

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def scrape_catalog(
        self,
        max_pages: Optional[int] = None,
        resume_from_page: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Navigate through catalog pages and extract regulation entries.

        Tries URL-based pagination (?page=N) first. If a page returns
        no items, attempts to click a "Next"/"Siguiente" button.

        Args:
            max_pages: Maximum number of pages to scrape (None = unlimited).
            resume_from_page: Page number to start from (0-based).

        Returns:
            Aggregated list of all regulation dicts found.
        """
        all_items: List[Dict[str, Any]] = []
        page = resume_from_page
        empty_streak = 0
        pages_scraped = 0

        while True:
            if max_pages is not None and pages_scraped >= max_pages:
                logger.info("Reached max_pages=%d, stopping.", max_pages)
                break

            # Try URL-based pagination
            url = f"{BASE_URL}/catalogo?page={page}"
            if not self._navigate(url):
                # If the catalog URL fails, try the base URL on first page
                if page == resume_from_page:
                    logger.info("Catalog URL failed, trying base URL...")
                    if not self._navigate(BASE_URL):
                        logger.error("Cannot reach %s at all.", BASE_URL)
                        break
                else:
                    empty_streak += 1
                    if empty_streak >= 3:
                        logger.warning("3 consecutive navigation failures, stopping.")
                        break
                    page += 1
                    continue

            items = self._parse_page()

            if not items:
                # Try clicking "Next" / "Siguiente" button
                clicked = self._try_click_next()
                if clicked:
                    self._page.wait_for_load_state("networkidle", timeout=15_000)
                    items = self._parse_page()

            if not items:
                empty_streak += 1
                logger.info(
                    "No items on page %d (empty streak: %d/3).",
                    page,
                    empty_streak,
                )
                if empty_streak >= 3:
                    logger.info("3 consecutive empty pages, assuming end of catalog.")
                    break
                page += 1
                pages_scraped += 1
                continue

            empty_streak = 0
            all_items.extend(items)
            pages_scraped += 1
            logger.info(
                "Page %d: found %d items (total: %d, pages: %d).",
                page,
                len(items),
                len(all_items),
                pages_scraped,
            )

            # Checkpoint
            if pages_scraped % self._checkpoint_interval == 0:
                self._save_checkpoint(page, all_items)

            page += 1
            self._rate_limit()

        return all_items

    # _try_click_next, _save_checkpoint, load_checkpoint, _screenshot,
    # save_results, save_batch are all inherited from PlaywrightBase.

    # ------------------------------------------------------------------
    # Dedup
    # ------------------------------------------------------------------

    @staticmethod
    def dedup(
        items: List[Dict[str, Any]],
        existing_titles: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate items by normalized title.

        Uses the normalization logic from conamer_scraper (_normalise_title,
        _strip_accents, _STOP_WORDS) for consistency.

        Args:
            items: Raw regulation dicts.
            existing_titles: Optional set of already-known titles.

        Returns:
            Deduplicated list.
        """
        normalised_existing = set()
        if existing_titles:
            normalised_existing = {_normalise_title(t) for t in existing_titles}

        seen: set = set()
        kept: List[Dict[str, Any]] = []
        duplicates = 0

        for item in items:
            norm = _normalise_title(item.get("name", ""))
            if not norm:
                continue
            if norm in normalised_existing or norm in seen:
                duplicates += 1
                continue
            seen.add(norm)
            kept.append(item)

        if duplicates:
            logger.info(
                "Dedup: dropped %d duplicates, kept %d of %d.",
                duplicates,
                len(kept),
                len(items),
            )

        return kept

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def run(
        self,
        max_pages: Optional[int] = None,
        resume_from_page: int = 0,
        existing_titles: Optional[set] = None,
    ) -> Dict[str, Any]:
        """
        Run the full Playwright-based CONAMER scraping pipeline.

        1. Launch browser.
        2. Navigate to catalog and paginate through results.
        3. Dedup against existing titles and within discovered items.
        4. Save results to discovered_conamer.json and batch files.

        Args:
            max_pages: Maximum pages to scrape (None = unlimited).
            resume_from_page: Page to resume from (0-based).
            existing_titles: Known titles for dedup.

        Returns:
            Summary dict with total_items, output_dir, etc.
        """
        logger.info(
            "Starting CONAMER Playwright scraper "
            "(headless=%s, resume=%d, max_pages=%s).",
            self._headless,
            resume_from_page,
            max_pages,
        )

        try:
            self._launch()

            # Scrape
            items = self.scrape_catalog(
                max_pages=max_pages,
                resume_from_page=resume_from_page,
            )

            if not items:
                logger.warning("No items discovered.")
                return {
                    "total_items": 0,
                    "total_after_dedup": 0,
                    "output_dir": str(self._output_dir),
                }

            # Dedup
            deduped = self.dedup(items, existing_titles)

            # Save consolidated file
            self.save_results(deduped, filename="discovered_conamer.json")

            # Also save as batches (50 items each) for compatibility
            batch_size = 50
            for i in range(0, len(deduped), batch_size):
                batch = deduped[i : i + batch_size]
                self.save_batch(batch, i // batch_size)

            summary = {
                "total_items": len(items),
                "total_after_dedup": len(deduped),
                "duplicates_removed": len(items) - len(deduped),
                "output_dir": str(self._output_dir),
            }
            logger.info("CONAMER Playwright scraper complete: %s", summary)
            return summary

        except Exception as exc:
            logger.error("Scraper failed: %s", exc, exc_info=True)
            self._screenshot("fatal_error")
            raise

        finally:
            self.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the CONAMER Playwright scraper."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Scrape the CONAMER CNARTyS catalog via Playwright (headless browser).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/conamer",
        help="Directory to save output files (default: data/conamer).",
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
        default=None,
        help="Page number to resume from (0-based). Loads checkpoint if not specified.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        dest="headless",
        help="Run browser in headless mode (default: true).",
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run browser with visible window (for debugging).",
    )
    parser.add_argument(
        "--existing-titles",
        type=str,
        default=None,
        help="Path to JSON file with existing law titles for dedup.",
    )
    args = parser.parse_args()

    # Determine resume page
    scraper = ConamerPlaywrightScraper(
        headless=args.headless,
        output_dir=args.output_dir,
    )

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

    # Load existing titles for dedup
    existing: Optional[set] = None
    if args.existing_titles:
        titles_path = Path(args.existing_titles)
        if titles_path.exists():
            with open(titles_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and isinstance(data[0], dict):
                    existing = {entry.get("name", "") for entry in data}
                else:
                    existing = set(data)
            logger.info("Loaded %d existing titles for dedup.", len(existing))

    result = scraper.run(
        max_pages=args.max_pages,
        resume_from_page=resume_from,
        existing_titles=existing,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
