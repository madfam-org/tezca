"""
Playwright Base Class for Browser-Automated Scrapers.

Provides shared browser lifecycle, WAF detection, navigation with retry,
checkpointing/resume, debug screenshots, and rate limiting. Subclasses
implement site-specific parsing and pagination logic.

Subclasses:
    - ConamerPlaywrightScraper (federal/conamer_playwright.py)
    - ScjnPlaywrightScraper (judicial/scjn_playwright.py)
    - MunicipalPlaywrightScraper (future)

Requires: pip install playwright && playwright install chromium
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import Browser, BrowserContext, Page, Playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# WAF challenge selectors (Cloudflare, Imperva, generic challenge pages)
WAF_SELECTORS = [
    "#challenge-form",
    "#challenge-running",
    ".cf-browser-verification",
    "#cf-challenge-running",
    "#trk_jschal_js",
    ".ray_id",
    "#challenge-stage",
]

# Realistic browser fingerprint
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

DEFAULT_PAGE_LOAD_DELAY = 2.0  # seconds between page loads
DEFAULT_WAF_TIMEOUT = 30_000  # 30s for WAF resolution (ms)
DEFAULT_NAVIGATION_TIMEOUT = 60_000  # 60s for page navigation (ms)
DEFAULT_CHECKPOINT_INTERVAL = 10  # save checkpoint every N pages
DEFAULT_BATCH_SIZE = 50  # items per batch file


class PlaywrightBase(ABC):
    """
    Abstract base class for Playwright-based web scrapers.

    Handles browser lifecycle, WAF bypass, navigation retry, checkpointing,
    and batch persistence. Subclasses implement site-specific extraction
    by overriding `_parse_page()` and `scrape_catalog()`.
    """

    def __init__(
        self,
        headless: bool = True,
        output_dir: str = "data/scraper_output",
        user_agent: str = DEFAULT_USER_AGENT,
        page_load_delay: float = DEFAULT_PAGE_LOAD_DELAY,
        waf_timeout: int = DEFAULT_WAF_TIMEOUT,
        navigation_timeout: int = DEFAULT_NAVIGATION_TIMEOUT,
        checkpoint_interval: int = DEFAULT_CHECKPOINT_INTERVAL,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self._headless = headless
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._debug_dir = self._output_dir / "debug"
        self._debug_dir.mkdir(parents=True, exist_ok=True)

        self._user_agent = user_agent
        self._page_load_delay = page_load_delay
        self._waf_timeout = waf_timeout
        self._navigation_timeout = navigation_timeout
        self._checkpoint_interval = checkpoint_interval
        self._batch_size = batch_size

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._items_collected: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Browser lifecycle
    # ------------------------------------------------------------------

    def _launch(self) -> None:
        """Launch headless Chromium with realistic browser fingerprint."""
        logger.info(
            "Launching Chromium (headless=%s)",
            self._headless,
        )
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self._headless,
        )
        self._context = self._browser.new_context(
            user_agent=self._user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="es-MX",
            timezone_id="America/Mexico_City",
            extra_http_headers={
                "Accept-Language": "es-MX,es;q=0.9,en;q=0.5",
            },
        )
        self._context.set_default_navigation_timeout(self._navigation_timeout)
        self._context.set_default_timeout(self._navigation_timeout)
        self._page = self._context.new_page()
        logger.info("Browser launched successfully.")

    def close(self) -> None:
        """Close browser and release Playwright resources."""
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
        logger.info("Browser closed.")

    # ------------------------------------------------------------------
    # WAF handling
    # ------------------------------------------------------------------

    def _detect_waf(self) -> bool:
        """Check if the current page shows a WAF challenge.

        Returns:
            True if a WAF challenge element is present.
        """
        if not self._page:
            return False

        for selector in WAF_SELECTORS:
            try:
                element = self._page.query_selector(selector)
                if element:
                    logger.warning(
                        "WAF challenge detected (selector: %s).",
                        selector,
                    )
                    return True
            except Exception:
                continue
        return False

    def _wait_for_waf_resolution(self) -> bool:
        """
        Detect and wait for WAF challenge page to resolve.

        Returns:
            True if WAF was resolved (or no WAF present).
            False if challenge did not resolve within timeout.
        """
        if not self._page:
            return False

        if not self._detect_waf():
            logger.debug("No WAF challenge detected.")
            return True

        logger.warning(
            "Waiting up to %ds for WAF resolution...",
            self._waf_timeout // 1000,
        )

        try:
            for selector in WAF_SELECTORS:
                try:
                    self._page.wait_for_selector(
                        selector,
                        state="hidden",
                        timeout=self._waf_timeout,
                    )
                except PlaywrightTimeout:
                    pass
                except Exception:
                    pass

            self._page.wait_for_load_state("networkidle", timeout=self._waf_timeout)
            logger.info("WAF challenge appears resolved.")
            return True

        except PlaywrightTimeout:
            logger.error(
                "WAF challenge did not resolve within %ds.",
                self._waf_timeout // 1000,
            )
            self._screenshot("waf_timeout")
            return False

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _navigate(self, url: str, retries: int = 3) -> bool:
        """
        Navigate to a URL with retry logic and WAF handling.

        Args:
            url: Target URL.
            retries: Number of retry attempts on failure.

        Returns:
            True if navigation succeeded, False otherwise.
        """
        if not self._page:
            return False

        for attempt in range(1, retries + 1):
            try:
                logger.info(
                    "Navigating to %s (attempt %d/%d)",
                    url,
                    attempt,
                    retries,
                )
                self._page.goto(url, wait_until="domcontentloaded")
                self._page.wait_for_load_state("networkidle", timeout=30_000)

                if not self._wait_for_waf_resolution():
                    logger.warning("WAF not resolved, retrying...")
                    time.sleep(5)
                    continue

                return True

            except PlaywrightTimeout:
                logger.warning(
                    "Navigation timeout for %s (attempt %d/%d)",
                    url,
                    attempt,
                    retries,
                )
                self._screenshot(f"nav_timeout_attempt_{attempt}")
                if attempt < retries:
                    time.sleep(3)
            except Exception as exc:
                logger.error(
                    "Navigation error for %s: %s (attempt %d/%d)",
                    url,
                    exc,
                    attempt,
                    retries,
                )
                self._screenshot(f"nav_error_attempt_{attempt}")
                if attempt < retries:
                    time.sleep(3)

        return False

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _rate_limit(self) -> None:
        """Sleep for the configured page load delay."""
        time.sleep(self._page_load_delay)

    # ------------------------------------------------------------------
    # Screenshot on failure
    # ------------------------------------------------------------------

    def _screenshot(self, label: str) -> None:
        """Save a debug screenshot with timestamp and label."""
        if not self._page:
            return
        try:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            path = self._debug_dir / f"{ts}_{label}.png"
            self._page.screenshot(path=str(path))
            logger.info("Debug screenshot saved: %s", path)
        except Exception as exc:
            logger.warning("Failed to save screenshot: %s", exc)

    # ------------------------------------------------------------------
    # Checkpoint / resume
    # ------------------------------------------------------------------

    def _save_checkpoint(
        self,
        current_page: int,
        items: List[Dict[str, Any]],
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save progress checkpoint for resume capability."""
        checkpoint = {
            "current_page": current_page,
            "items_collected": len(items),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            checkpoint.update(extra)

        checkpoint_path = self._output_dir / "checkpoint.json"
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)
        logger.info(
            "Checkpoint saved: page=%d, items=%d",
            current_page,
            len(items),
        )

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load a previously saved checkpoint.

        Returns:
            Checkpoint dict or None if no checkpoint exists.
        """
        checkpoint_path = self._output_dir / "checkpoint.json"
        if not checkpoint_path.exists():
            return None
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_results(
        self,
        items: List[Dict[str, Any]],
        filename: str = "discovered_items.json",
    ) -> Path:
        """Save all discovered items to a single JSON file.

        Args:
            items: Dicts to persist.
            filename: Output filename.

        Returns:
            Path to the written file.
        """
        file_path = self._output_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        logger.info("Saved %d items to %s", len(items), file_path)
        return file_path

    def save_batch(
        self,
        items: List[Dict[str, Any]],
        batch_number: int,
        subdirectory: Optional[str] = None,
    ) -> Path:
        """Save a batch of items to a numbered JSON file."""
        out_dir = self._output_dir
        if subdirectory:
            out_dir = out_dir / subdirectory
        out_dir.mkdir(parents=True, exist_ok=True)

        path = out_dir / f"batch_{batch_number:04d}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        logger.info("Saved %d items to %s", len(items), path)
        return path

    # ------------------------------------------------------------------
    # Pagination helpers
    # ------------------------------------------------------------------

    def _try_click_next(self) -> bool:
        """
        Attempt to click a pagination "Next" or "Siguiente" button.

        Returns:
            True if a next-page button was found and clicked.
        """
        if not self._page:
            return False

        next_selectors = [
            "a:has-text('Siguiente')",
            "button:has-text('Siguiente')",
            "a:has-text('Next')",
            "button:has-text('Next')",
            ".pagination .next a",
            ".pagination li:last-child a",
            "a[rel='next']",
            "[aria-label='Next']",
            "[aria-label='Siguiente']",
        ]

        for selector in next_selectors:
            try:
                element = self._page.query_selector(selector)
                if element and element.is_visible():
                    element.click()
                    logger.debug("Clicked next-page button: %s", selector)
                    return True
            except Exception:
                continue

        return False

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def _parse_page(self) -> List[Dict[str, Any]]:
        """Extract items from the current page DOM.

        Subclasses implement site-specific parsing strategies.

        Returns:
            List of extracted item dicts.
        """

    @abstractmethod
    def scrape_catalog(
        self,
        max_pages: Optional[int] = None,
        resume_from_page: int = 0,
    ) -> List[Dict[str, Any]]:
        """Navigate through catalog pages and extract items.

        Subclasses implement site-specific pagination logic.

        Args:
            max_pages: Maximum pages to scrape (None = unlimited).
            resume_from_page: Page to start from.

        Returns:
            Aggregated list of all item dicts found.
        """
