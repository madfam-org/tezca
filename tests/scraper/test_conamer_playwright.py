"""Tests for ``apps.scraper.federal.conamer_playwright``.

Uses the same playwright-shim pattern as test_playwright_base.py so the
module imports cleanly without the optional Playwright package. Targets
pure DOM-extraction logic and dedup.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Playwright shim
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


from apps.scraper.federal.conamer_playwright import (  # noqa: E402
    ConamerPlaywrightScraper,
)

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def scraper(tmp_path):
    return ConamerPlaywrightScraper(output_dir=str(tmp_path / "out"))


def _fake_element(text: str = "", attrs: dict | None = None) -> MagicMock:
    el = MagicMock()
    el.inner_text.return_value = text
    el.get_attribute.side_effect = lambda key: (attrs or {}).get(key, "")
    el.query_selector.return_value = None
    el.query_selector_all.return_value = []
    return el


# ---------------------------------------------------------------------------
# __init__ — inherits PlaywrightBase
# ---------------------------------------------------------------------------


def test_init_inherits_playwright_base(scraper):
    from apps.scraper.playwright_base import PlaywrightBase

    assert isinstance(scraper, PlaywrightBase)


def test_init_sets_output_dir(tmp_path):
    s = ConamerPlaywrightScraper(output_dir=str(tmp_path / "x"))
    assert s._output_dir == tmp_path / "x"


# ---------------------------------------------------------------------------
# _parse_page — strategy waterfall
# ---------------------------------------------------------------------------


def test_parse_page_returns_empty_without_page(scraper):
    scraper._page = None
    assert scraper._parse_page() == []


def test_parse_page_strategy1_table_rows(scraper):
    """Tables with td cells produce one item per row."""
    cells = [
        _fake_element("Reglamento de Aguas"),
        _fake_element("CONAGUA"),
        _fake_element("2024-03-15"),
        _fake_element("Reglamento"),
    ]
    row = MagicMock()
    row.query_selector_all.return_value = cells
    row.query_selector.return_value = _fake_element("", attrs={"href": "/r/1"})

    fake_page = MagicMock()

    def _query_all(selector):
        if "table tbody tr" in selector:
            return [row]
        return []

    fake_page.query_selector_all.side_effect = _query_all
    scraper._page = fake_page

    items = scraper._parse_page()
    assert len(items) == 1
    assert items[0]["name"] == "Reglamento de Aguas"
    assert items[0]["issuing_body"] == "CONAGUA"
    assert items[0]["date"] == "2024-03-15"
    assert items[0]["regulation_type"] == "Reglamento"
    assert items[0]["url"].startswith("http")
    assert items[0]["source"] == "conamer_cnartys_playwright"


def test_parse_page_strategy1_skips_too_few_cells(scraper):
    row = MagicMock()
    row.query_selector_all.return_value = [_fake_element("only cell")]

    fake_page = MagicMock()

    def _query_all(selector):
        if "table tbody tr" in selector:
            return [row]
        return []

    fake_page.query_selector_all.side_effect = _query_all
    scraper._page = fake_page

    assert scraper._parse_page() == []


def test_parse_page_strategy1_skips_short_name(scraper):
    cells = [_fake_element("X"), _fake_element("body")]
    row = MagicMock()
    row.query_selector_all.return_value = cells
    row.query_selector.return_value = None

    fake_page = MagicMock()

    def _query_all(selector):
        if "table tbody tr" in selector:
            return [row]
        return []

    fake_page.query_selector_all.side_effect = _query_all
    scraper._page = fake_page
    assert scraper._parse_page() == []


def test_parse_page_strategy1_handles_exception_per_row(scraper):
    """A failing row doesn't stop processing of other rows."""
    bad_row = MagicMock()
    bad_row.query_selector_all.side_effect = RuntimeError("boom")

    good_cells = [_fake_element("Decent Title"), _fake_element("body")]
    good_row = MagicMock()
    good_row.query_selector_all.return_value = good_cells
    good_row.query_selector.return_value = None

    fake_page = MagicMock()

    def _query_all(selector):
        if "table tbody tr" in selector:
            return [bad_row, good_row]
        return []

    fake_page.query_selector_all.side_effect = _query_all
    scraper._page = fake_page

    items = scraper._parse_page()
    assert len(items) == 1
    assert items[0]["name"] == "Decent Title"


# ---------------------------------------------------------------------------
# dedup
# ---------------------------------------------------------------------------


def test_dedup_drops_internal_duplicates():
    items = [
        {"name": "Reglamento de Aguas"},
        {"name": "Reglamento de Aguas"},
    ]
    out = ConamerPlaywrightScraper.dedup(items)
    assert len(out) == 1


def test_dedup_against_existing_titles():
    items = [
        {"name": "Reglamento Existente"},
        {"name": "Reglamento Nuevo"},
    ]
    out = ConamerPlaywrightScraper.dedup(
        items, existing_titles={"reglamento existente"}
    )
    assert len(out) == 1
    assert out[0]["name"] == "Reglamento Nuevo"


def test_dedup_skips_empty_names():
    items = [{"name": ""}, {"name": "Real"}]
    out = ConamerPlaywrightScraper.dedup(items)
    assert len(out) == 1
    assert out[0]["name"] == "Real"


def test_dedup_normalises_accents():
    items = [{"name": "Regulación X"}]
    out = ConamerPlaywrightScraper.dedup(items, existing_titles={"regulacion x"})
    assert out == []
