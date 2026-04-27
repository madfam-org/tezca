"""Tests for ``apps.scraper.playwright_base``.

Playwright is an optional system dependency, so these tests shim
``playwright.sync_api`` via ``sys.modules`` before importing the module
under test. That keeps the test suite runnable in environments where
Playwright is not installed (CI without browsers, dev machines that
``poetry install`` without the scraper extras).

Coverage focus:
* Constants (defaults, WAF selectors)
* PlaywrightBase abstract contract
* Subclass instantiation + attribute defaults
* close() teardown swallows per-resource errors
* _detect_waf, _wait_for_waf_resolution branches
* _navigate retry/timeout branches
* _save_checkpoint / load_checkpoint round-trip
* save_results / save_batch persistence
* _try_click_next selector iteration
* _rate_limit (sleep delegation)
* _screenshot guard when page is None / write failure
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Shim playwright.sync_api so the module under test can be imported even when
# Playwright is not installed. The shim provides the names referenced at
# module-import time (Browser, BrowserContext, Page, Playwright, sync_playwright,
# TimeoutError).
# ---------------------------------------------------------------------------

if "playwright" not in sys.modules:
    _pw = ModuleType("playwright")
    _pw_sync = ModuleType("playwright.sync_api")

    class _PlaywrightTimeoutError(Exception):
        pass

    _pw_sync.Browser = type("Browser", (), {})  # type: ignore[attr-defined]
    _pw_sync.BrowserContext = type("BrowserContext", (), {})  # type: ignore[attr-defined]
    _pw_sync.Page = type("Page", (), {})  # type: ignore[attr-defined]
    _pw_sync.Playwright = type("Playwright", (), {})  # type: ignore[attr-defined]
    _pw_sync.TimeoutError = _PlaywrightTimeoutError  # type: ignore[attr-defined]
    _pw_sync.sync_playwright = MagicMock()  # type: ignore[attr-defined]

    _pw.sync_api = _pw_sync  # type: ignore[attr-defined]
    sys.modules["playwright"] = _pw
    sys.modules["playwright.sync_api"] = _pw_sync


from apps.scraper import playwright_base as pb  # noqa: E402

# ---------------------------------------------------------------------------
# Concrete subclass for testing the abstract contract
# ---------------------------------------------------------------------------


class _ConcreteScraper(pb.PlaywrightBase):
    """Minimal concrete subclass that satisfies the abstract interface."""

    def _parse_page(self):
        return []

    def scrape_catalog(self, max_pages=None, resume_from_page=0):
        return []


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_default_constants_have_expected_values():
    assert pb.DEFAULT_PAGE_LOAD_DELAY == 2.0
    assert pb.DEFAULT_WAF_TIMEOUT == 30_000
    assert pb.DEFAULT_NAVIGATION_TIMEOUT == 60_000
    assert pb.DEFAULT_CHECKPOINT_INTERVAL == 10
    assert pb.DEFAULT_BATCH_SIZE == 50
    assert "Mozilla" in pb.DEFAULT_USER_AGENT
    assert "#challenge-form" in pb.WAF_SELECTORS


# ---------------------------------------------------------------------------
# Abstract contract
# ---------------------------------------------------------------------------


def test_playwright_base_is_abstract():
    with pytest.raises(TypeError, match="abstract"):
        pb.PlaywrightBase()  # type: ignore[abstract]


def test_concrete_subclass_can_be_instantiated(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    assert s._headless is True
    assert s._output_dir == tmp_path
    assert s._debug_dir == tmp_path / "debug"
    assert s._debug_dir.exists()
    assert s._page_load_delay == pb.DEFAULT_PAGE_LOAD_DELAY


def test_constructor_accepts_overrides(tmp_path):
    s = _ConcreteScraper(
        output_dir=str(tmp_path),
        headless=False,
        user_agent="Custom/1.0",
        page_load_delay=0.5,
        waf_timeout=15_000,
        navigation_timeout=10_000,
        checkpoint_interval=5,
        batch_size=20,
    )
    assert s._headless is False
    assert s._user_agent == "Custom/1.0"
    assert s._page_load_delay == 0.5
    assert s._waf_timeout == 15_000
    assert s._navigation_timeout == 10_000
    assert s._checkpoint_interval == 5
    assert s._batch_size == 20


# ---------------------------------------------------------------------------
# close() — teardown swallows per-resource errors
# ---------------------------------------------------------------------------


def test_close_when_no_browser_is_idempotent(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    # No browser launched — close() should be a no-op
    s.close()
    assert s._browser is None
    assert s._page is None


def test_close_swallows_per_resource_errors(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._context = MagicMock()
    s._context.close.side_effect = RuntimeError("ctx blip")
    s._browser = MagicMock()
    s._browser.close.side_effect = RuntimeError("browser blip")
    s._playwright = MagicMock()
    s._playwright.stop.side_effect = RuntimeError("pw blip")

    # Must not raise, must clear all four refs
    s.close()
    assert s._page is None
    assert s._context is None
    assert s._browser is None
    assert s._playwright is None


# ---------------------------------------------------------------------------
# _detect_waf
# ---------------------------------------------------------------------------


def test_detect_waf_returns_false_when_page_missing(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    assert s._detect_waf() is False


def test_detect_waf_returns_true_when_selector_matches(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    s._page.query_selector.return_value = SimpleNamespace()  # truthy
    assert s._detect_waf() is True


def test_detect_waf_skips_failing_selectors(tmp_path):
    """If query_selector raises on one selector, keep trying the rest."""
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    # First raises, second returns a match
    s._page.query_selector.side_effect = [
        RuntimeError("frame detached"),
        SimpleNamespace(),
    ] + [None] * 10
    assert s._detect_waf() is True


def test_detect_waf_returns_false_when_no_selector_matches(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    s._page.query_selector.return_value = None
    assert s._detect_waf() is False


# ---------------------------------------------------------------------------
# _wait_for_waf_resolution
# ---------------------------------------------------------------------------


def test_wait_for_waf_resolution_returns_true_when_no_waf(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    s._page.query_selector.return_value = None  # no WAF
    assert s._wait_for_waf_resolution() is True


def test_wait_for_waf_resolution_handles_timeout(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    # Initial detect: WAF present
    s._page.query_selector.return_value = SimpleNamespace()

    # wait_for_selector raises PlaywrightTimeout for every selector
    s._page.wait_for_selector.side_effect = pb.PlaywrightTimeout("timeout")
    s._page.wait_for_load_state.side_effect = pb.PlaywrightTimeout("timeout")
    s._page.screenshot = MagicMock()

    out = s._wait_for_waf_resolution()
    assert out is False
    s._page.screenshot.assert_called()


def test_wait_for_waf_resolution_returns_false_when_no_page(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    assert s._wait_for_waf_resolution() is False


# ---------------------------------------------------------------------------
# _navigate
# ---------------------------------------------------------------------------


def test_navigate_returns_false_without_page(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    assert s._navigate("https://example.com") is False


def test_navigate_succeeds_on_first_try(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    s._page.query_selector.return_value = None  # no WAF detected
    assert s._navigate("https://example.com") is True
    s._page.goto.assert_called_once()


def test_navigate_retries_on_timeout(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    s._page.query_selector.return_value = None
    # First two goto() raise PlaywrightTimeout, third succeeds
    s._page.goto.side_effect = [
        pb.PlaywrightTimeout("t"),
        pb.PlaywrightTimeout("t"),
        None,
    ]

    with patch("apps.scraper.playwright_base.time.sleep"):
        result = s._navigate("https://example.com", retries=3)
    assert result is True
    assert s._page.goto.call_count == 3


def test_navigate_returns_false_after_all_retries_exhausted(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    s._page.query_selector.return_value = None
    s._page.goto.side_effect = pb.PlaywrightTimeout("t")

    with patch("apps.scraper.playwright_base.time.sleep"):
        result = s._navigate("https://example.com", retries=2)
    assert result is False
    assert s._page.goto.call_count == 2


def test_navigate_handles_generic_exception(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    s._page.query_selector.return_value = None
    s._page.goto.side_effect = RuntimeError("boom")

    with patch("apps.scraper.playwright_base.time.sleep"):
        result = s._navigate("https://example.com", retries=2)
    assert result is False


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


def test_rate_limit_sleeps_for_configured_delay(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path), page_load_delay=1.5)
    with patch("apps.scraper.playwright_base.time.sleep") as msleep:
        s._rate_limit()
    msleep.assert_called_once_with(1.5)


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------


def test_screenshot_no_op_without_page(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._screenshot("nothing")  # no exception, no file written


def test_screenshot_swallows_write_failure(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    s._page.screenshot.side_effect = RuntimeError("disk full")
    s._screenshot("fail-label")  # must not raise


def test_screenshot_writes_to_debug_dir(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    captured = {}

    def fake_screenshot(path):
        captured["path"] = path
        Path(path).write_bytes(b"img")

    s._page.screenshot.side_effect = fake_screenshot
    s._screenshot("hello")
    assert captured["path"].startswith(str(s._debug_dir))
    assert "hello" in captured["path"]


# ---------------------------------------------------------------------------
# Checkpoint round-trip
# ---------------------------------------------------------------------------


def test_save_and_load_checkpoint_round_trip(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._save_checkpoint(
        current_page=42, items=[{"a": 1}, {"b": 2}], extra={"foo": "bar"}
    )

    loaded = s.load_checkpoint()
    assert loaded["current_page"] == 42
    assert loaded["items_collected"] == 2
    assert loaded["foo"] == "bar"
    assert "timestamp" in loaded


def test_load_checkpoint_returns_none_when_missing(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    assert s.load_checkpoint() is None


# ---------------------------------------------------------------------------
# save_results / save_batch
# ---------------------------------------------------------------------------


def test_save_results_writes_json(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    items = [{"id": 1}, {"id": 2}]
    out = s.save_results(items, filename="my-output.json")
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8")) == items


def test_save_batch_writes_numbered_file(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    items = [{"id": 1}]
    out = s.save_batch(items, batch_number=7, subdirectory="batches")
    assert out.exists()
    assert out.parent == tmp_path / "batches"
    assert out.name == "batch_0007.json"
    assert json.loads(out.read_text(encoding="utf-8")) == items


def test_save_batch_without_subdirectory(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    out = s.save_batch([{"id": 1}], batch_number=3)
    assert out.parent == tmp_path
    assert out.name == "batch_0003.json"


# ---------------------------------------------------------------------------
# _try_click_next
# ---------------------------------------------------------------------------


def test_try_click_next_returns_false_without_page(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    assert s._try_click_next() is False


def test_try_click_next_clicks_first_visible_match(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    fake_elem = MagicMock()
    fake_elem.is_visible.return_value = True
    s._page.query_selector.side_effect = [None, fake_elem] + [None] * 10
    assert s._try_click_next() is True
    fake_elem.click.assert_called_once()


def test_try_click_next_skips_invisible_match(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    invisible = MagicMock()
    invisible.is_visible.return_value = False
    s._page.query_selector.return_value = invisible
    assert s._try_click_next() is False
    invisible.click.assert_not_called()


def test_try_click_next_swallows_selector_failure(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    s._page = MagicMock()
    # First selector raises, the rest return None
    s._page.query_selector.side_effect = [RuntimeError("stale")] + [None] * 10
    assert s._try_click_next() is False


# ---------------------------------------------------------------------------
# _launch — uses sync_playwright()
# ---------------------------------------------------------------------------


def test_launch_wires_up_browser_context_page(tmp_path):
    s = _ConcreteScraper(output_dir=str(tmp_path))
    fake_pw_runner = MagicMock()
    fake_pw = MagicMock()
    fake_browser = MagicMock()
    fake_context = MagicMock()
    fake_page = MagicMock()
    fake_pw_runner.start.return_value = fake_pw
    fake_pw.chromium.launch.return_value = fake_browser
    fake_browser.new_context.return_value = fake_context
    fake_context.new_page.return_value = fake_page

    with patch(
        "apps.scraper.playwright_base.sync_playwright", return_value=fake_pw_runner
    ):
        s._launch()

    assert s._playwright is fake_pw
    assert s._browser is fake_browser
    assert s._context is fake_context
    assert s._page is fake_page
    fake_pw.chromium.launch.assert_called_once_with(headless=True)
