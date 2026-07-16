"""Tests for ``apps.scraper.judicial.scjn_playwright``.

Playwright is an optional dep — uses the same shim pattern as
``test_playwright_base.py`` so the tests run when Playwright isn't
installed. Targets the SJF-specific extraction logic by stubbing the
Playwright element interface (query_selector / query_selector_all /
inner_text / get_attribute / etc.).
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Playwright shim (same pattern as test_playwright_base.py)
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


# httpx is an optional dep used by MadfamBridge. Shim if missing.
# NOTE: this stub is installed into sys.modules for the whole test process
# (not just this file), so it must look enough like the real package that
# unrelated tests collected later (e.g. elastic_transport's httpx probe in
# test_dataops.py) don't crash on missing attributes such as __version__.
if "httpx" not in sys.modules:
    _httpx = ModuleType("httpx")
    _httpx.__version__ = "0.0.0-shim"  # type: ignore[attr-defined]
    _httpx.Client = MagicMock()  # type: ignore[attr-defined]
    _httpx.AsyncClient = MagicMock()  # type: ignore[attr-defined]
    _httpx.HTTPError = type("HTTPError", (Exception,), {})  # type: ignore[attr-defined]
    _httpx.TimeoutException = type("TimeoutException", (Exception,), {})  # type: ignore[attr-defined]
    sys.modules["httpx"] = _httpx


from apps.scraper.judicial.scjn_playwright import (  # noqa: E402
    SJF_BASE_URL,
    SJF_DETAIL_URL,
    ScjnPlaywrightScraper,
)

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def scraper(tmp_path):
    """Build a scraper without invoking the bridge — patch where it would fire."""
    with patch("apps.scraper.judicial.scjn_playwright.MadfamBridge"):
        s = ScjnPlaywrightScraper(output_dir=str(tmp_path / "out"))
    s._epoca = 10
    s._tipo = "jurisprudencia"
    return s


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_constants_use_sjfsemanal_subdomain():
    assert "sjfsemanal" in SJF_BASE_URL
    assert "sjfsemanal" in SJF_DETAIL_URL


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_inherits_playwright_base(scraper):
    from apps.scraper.playwright_base import PlaywrightBase

    assert isinstance(scraper, PlaywrightBase)


def test_init_default_epoca_and_tipo(tmp_path):
    with patch("apps.scraper.judicial.scjn_playwright.MadfamBridge"):
        s = ScjnPlaywrightScraper(output_dir=str(tmp_path / "out"))
    assert s._epoca == 10
    assert s._tipo == "jurisprudencia"


# ---------------------------------------------------------------------------
# _make_record
# ---------------------------------------------------------------------------


def test_make_record_full_fields(scraper):
    rec = scraper._make_record(
        registro="2031846",
        rubro="Some rubro",
        texto="Body",
        instancia="Pleno",
        materia="Civil",
        tesis_num="P./J. 1/2024",
        url="https://custom/url",
    )
    assert rec["registro"] == "2031846"
    assert rec["rubro"] == "Some rubro"
    assert rec["instancia"] == "Pleno"
    assert rec["url"] == "https://custom/url"
    assert rec["tipo"] == "jurisprudencia"
    assert rec["epoca"] == 10
    assert rec["epoca_nombre"]  # populated from EPOCAS
    assert rec["source"] == "sjf_scjn_playwright"


def test_make_record_synthesizes_url_from_registro(scraper):
    rec = scraper._make_record(registro="123456", rubro="Test")
    assert "123456" in rec["url"]
    assert "sjfsemanal" in rec["url"]


def test_make_record_unknown_epoca_falls_back(scraper):
    scraper._epoca = 99
    rec = scraper._make_record(registro="1", rubro="X")
    assert "99" in rec["epoca_nombre"]


# ---------------------------------------------------------------------------
# _extract_from_container
# ---------------------------------------------------------------------------


def _fake_element(text: str = "", attrs: dict | None = None) -> MagicMock:
    """Build a mock playwright element returning *text* on inner_text()."""
    el = MagicMock()
    el.inner_text.return_value = text
    el.get_attribute.side_effect = lambda key: (attrs or {}).get(key, "")
    el.query_selector.return_value = None
    el.query_selector_all.return_value = []
    return el


def test_extract_from_container_returns_none_short_rubro(scraper):
    """Rubro shorter than 10 chars → return None."""
    container = MagicMock()
    container.query_selector.return_value = _fake_element("Short")
    assert scraper._extract_from_container(container) is None


def test_extract_from_container_returns_none_when_no_title(scraper):
    container = MagicMock()
    container.query_selector.return_value = None
    assert scraper._extract_from_container(container) is None


def test_extract_from_container_swallows_exception(scraper):
    """A runtime error during extraction yields None, not an exception."""
    container = MagicMock()
    container.query_selector.side_effect = RuntimeError("boom")
    assert scraper._extract_from_container(container) is None


def test_extract_from_container_full_extraction(scraper):
    """Happy path with all fields present."""
    title_el = _fake_element("LONG ENOUGH RUBRO TEXT")
    text_el = _fake_element("Body content here")
    link_el = _fake_element("", attrs={"href": "/detalle/tesis/2031846"})

    container = MagicMock()

    def _selector_dispatch(selector):
        if "h2" in selector or "rubro" in selector:
            return title_el
        if "texto" in selector or "contenido" in selector:
            return text_el
        if "a[href]" in selector:
            return link_el
        return None

    container.query_selector.side_effect = _selector_dispatch
    # _extract_label uses query_selector + query_selector_all on container
    container.query_selector_all.return_value = []

    rec = scraper._extract_from_container(container)
    assert rec is not None
    assert rec["registro"] == "2031846"
    assert "RUBRO" in rec["rubro"]
    assert rec["texto"] == "Body content here"


# ---------------------------------------------------------------------------
# _extract_from_table_row
# ---------------------------------------------------------------------------


def test_extract_from_table_row_too_few_cells(scraper):
    row = MagicMock()
    row.query_selector_all.return_value = [_fake_element("only")]
    assert scraper._extract_from_table_row(row) is None


def test_extract_from_table_row_short_rubro(scraper):
    row = MagicMock()
    row.query_selector_all.return_value = [_fake_element("X"), _fake_element("more")]
    assert scraper._extract_from_table_row(row) is None


def test_extract_from_table_row_extracts_all_cells(scraper):
    cells = [
        _fake_element("LONG RUBRO TEXT FOR EXTRACTION"),
        _fake_element("Pleno"),
        _fake_element("Civil"),
        _fake_element("P./J. 1/2024"),
        _fake_element("Body text"),
    ]
    row = MagicMock()
    row.query_selector_all.return_value = cells
    row.query_selector.return_value = _fake_element(
        "", attrs={"href": "/detalle/tesis/777"}
    )
    rec = scraper._extract_from_table_row(row)
    assert rec is not None
    assert rec["registro"] == "777"
    assert rec["instancia"] == "Pleno"
    assert rec["materia"] == "Civil"
    assert rec["tesis_num"] == "P./J. 1/2024"
    assert rec["texto"] == "Body text"


def test_extract_from_table_row_swallows_exception(scraper):
    row = MagicMock()
    row.query_selector_all.side_effect = RuntimeError("boom")
    assert scraper._extract_from_table_row(row) is None


# ---------------------------------------------------------------------------
# _extract_from_dl
# ---------------------------------------------------------------------------


def test_extract_from_dl_returns_none_when_no_rubro(scraper):
    dl = MagicMock()
    dl.query_selector_all.side_effect = [
        [_fake_element("Otro:")],
        [_fake_element("value")],
    ]
    assert scraper._extract_from_dl(dl) is None


def test_extract_from_dl_extracts_full_record(scraper):
    dts = [
        _fake_element("Rubro:"),
        _fake_element("Registro:"),
        _fake_element("Instancia:"),
    ]
    dds = [
        _fake_element("The rubro text"),
        _fake_element("999888"),
        _fake_element("Pleno"),
    ]
    dl = MagicMock()
    dl.query_selector_all.side_effect = [dts, dds]
    rec = scraper._extract_from_dl(dl)
    assert rec is not None
    assert rec["rubro"] == "The rubro text"
    assert rec["registro"] == "999888"
    assert rec["instancia"] == "Pleno"
    assert "999888" in rec["url"]


def test_extract_from_dl_swallows_exception(scraper):
    dl = MagicMock()
    dl.query_selector_all.side_effect = RuntimeError("boom")
    assert scraper._extract_from_dl(dl) is None


# ---------------------------------------------------------------------------
# _extract_label
# ---------------------------------------------------------------------------


def test_extract_label_via_class_match(scraper):
    container = MagicMock()
    container.query_selector.return_value = _fake_element("Civil")
    assert scraper._extract_label(container, "materia") == "Civil"


def test_extract_label_returns_empty_when_no_match(scraper):
    container = MagicMock()
    container.query_selector.return_value = None
    container.query_selector_all.return_value = []
    assert scraper._extract_label(container, "materia") == ""


def test_extract_label_swallows_exception(scraper):
    container = MagicMock()
    container.query_selector.side_effect = RuntimeError("boom")
    assert scraper._extract_label(container, "materia") == ""


# ---------------------------------------------------------------------------
# _enrich_records — short-circuits when records already populated
# ---------------------------------------------------------------------------


def test_enrich_records_skips_records_with_existing_texto(scraper):
    records = [
        {"registro": "1", "rubro": "X", "texto": "Already filled"},
        {"registro": "2", "rubro": "Y", "texto": "Also filled"},
    ]
    out = scraper._enrich_records(records)
    assert len(out) == 2
    # Untouched
    assert out[0]["texto"] == "Already filled"


# ---------------------------------------------------------------------------
# _parse_page — strategy waterfall
# ---------------------------------------------------------------------------


def test_parse_page_returns_empty_without_page(scraper):
    scraper._page = None
    assert scraper._parse_page() == []


def test_parse_page_strategy_1_containers(scraper):
    """When containers yield records, the table/dl strategies are skipped."""
    fake_page = MagicMock()
    container = MagicMock()
    title_el = _fake_element("Some sufficiently long rubro text")
    text_el = _fake_element("Body content")
    link_el = _fake_element("", attrs={"href": "/detalle/tesis/111"})

    def _container_dispatch(selector):
        if "h2" in selector or "rubro" in selector:
            return title_el
        if "texto" in selector or "contenido" in selector:
            return text_el
        if "a[href]" in selector:
            return link_el
        return None

    container.query_selector.side_effect = _container_dispatch
    container.query_selector_all.return_value = []

    def _page_query_all(selector):
        if "resultado" in selector or "tesis-item" in selector or "article" in selector:
            return [container]
        return []

    fake_page.query_selector_all.side_effect = _page_query_all
    scraper._page = fake_page

    items = scraper._parse_page()
    assert len(items) == 1
    assert items[0]["registro"] == "111"


def test_parse_page_strategy_4_link_fallback(scraper):
    """When all earlier strategies yield nothing, fall back to tesis links."""
    fake_page = MagicMock()
    long_text_link = _fake_element(
        "A very long tesis link text that survives the >20 chars check",
        attrs={"href": "/detalle/tesis/2031846"},
    )

    def _page_query_all(selector):
        # Strategies 1-3 return nothing
        if "tesis" in selector and "href" in selector:
            return [long_text_link]
        return []

    fake_page.query_selector_all.side_effect = _page_query_all
    scraper._page = fake_page

    items = scraper._parse_page()
    assert len(items) == 1
    assert items[0]["registro"] == "2031846"


def test_parse_page_skips_short_link_text(scraper):
    """Links with text <= 20 chars are skipped."""
    fake_page = MagicMock()
    short_link = _fake_element("Short", attrs={"href": "/x/1"})

    def _page_query_all(selector):
        if "tesis" in selector and "href" in selector:
            return [short_link]
        return []

    fake_page.query_selector_all.side_effect = _page_query_all
    scraper._page = fake_page

    items = scraper._parse_page()
    assert items == []


# ---------------------------------------------------------------------------
# API-first scraping (fix for #142)
# ---------------------------------------------------------------------------

from apps.scraper.judicial.sjf_api import SjfApiError  # noqa: E402


def _fake_doc(ius: str) -> dict:
    return {
        "ius": ius,
        "rubro": f"<b>RUBRO {ius}</b>",
        "texto": f"Texto {ius}",
        "instanciaAbr": "Pleno",
        "materias": "Civil",
        "claveTesis": f"P./J. {ius}/2024",
    }


class TestScrapeViaApi:
    """``_scrape_via_api`` — direct requests-based pagination, no browser."""

    def test_two_pages_then_empty_maps_and_saves_batches(self, scraper):
        page1 = [_fake_doc("1"), _fake_doc("2")]
        page2 = [_fake_doc("3")]
        scraper.api.list_tesis = MagicMock(
            side_effect=[
                (page1, 3, 2),
                (page2, 3, 2),
            ]
        )

        items = scraper._scrape_via_api()

        assert [it["registro"] for it in items] == ["1", "2", "3"]
        assert items[0]["rubro"] == "RUBRO 1"
        assert scraper.api.list_tesis.call_count == 2

    def test_saves_batches_to_output_dir(self, scraper, tmp_path):
        docs = [_fake_doc(str(i)) for i in range(3)]
        scraper.api.list_tesis = MagicMock(side_effect=[(docs, 3, 1)])

        items = scraper._scrape_via_api()

        assert len(items) == 3
        subdir = scraper._output_dir / "jurisprudencia"
        saved_files = list(subdir.glob("batch_*.json")) if subdir.exists() else []
        # scrape_via_api flushes any remaining (non-full) batch at the end.
        assert len(saved_files) >= 1

    def test_max_items_honored_and_truncates(self, scraper):
        docs = [_fake_doc(str(i)) for i in range(5)]
        scraper.api.list_tesis = MagicMock(side_effect=[(docs, 5, 1)])

        items = scraper._scrape_via_api(max_items=2)

        assert len(items) == 2

    def test_empty_first_page_returns_empty_list(self, scraper):
        scraper.api.list_tesis = MagicMock(return_value=([], 0, 0))
        items = scraper._scrape_via_api()
        assert items == []

    def test_stops_when_total_pages_reached(self, scraper):
        docs = [_fake_doc("1")]
        scraper.api.list_tesis = MagicMock(side_effect=[(docs, 1, 1)])
        items = scraper._scrape_via_api()
        assert len(items) == 1
        scraper.api.list_tesis.assert_called_once()


# ---------------------------------------------------------------------------
# run() — tier selection
# ---------------------------------------------------------------------------


class TestRunTierSelection:
    """run() should try API first, then in-page API, then DOM as a last resort."""

    def test_api_success_sets_method_api_and_skips_browser(self, scraper, tmp_path):
        scraper._scrape_via_api = MagicMock(
            return_value=[
                {
                    "registro": "1",
                    "rubro": "R",
                    "texto": "T",
                    "epoca": 10,
                    "epoca_nombre": "Decima Epoca",
                    "tipo": "jurisprudencia",
                }
            ]
        )
        with patch.object(scraper, "_launch") as mock_launch:
            summary = scraper.run(epoca=10, tipo="jurisprudencia", enrich=False)

        mock_launch.assert_not_called()
        assert summary["method"] == "api"
        assert summary["total_items"] == 1

    def test_api_error_falls_back_to_browser_and_launches(self, scraper):
        scraper._scrape_via_api = MagicMock(side_effect=SjfApiError("blocked"))
        scraper._navigate_to_search = MagicMock(return_value=True)
        scraper._scrape_via_inpage_api = MagicMock(return_value=[])
        scraper._fill_search_form = MagicMock(return_value=True)
        scraper.scrape_catalog = MagicMock(return_value=[])

        with patch.object(scraper, "_launch") as mock_launch, patch(
            "apps.scraper.judicial.scjn_playwright.time.sleep"
        ):
            summary = scraper.run(epoca=10, tipo="jurisprudencia", enrich=False)

        mock_launch.assert_called_once()
        scraper._scrape_via_inpage_api.assert_called_once()
        assert summary["method"] == "dom"

    def test_inpage_api_success_sets_method_inpage_api(self, scraper):
        scraper._scrape_via_api = MagicMock(side_effect=SjfApiError("blocked"))
        scraper._navigate_to_search = MagicMock(return_value=True)
        scraper._scrape_via_inpage_api = MagicMock(
            return_value=[
                {
                    "registro": "1",
                    "rubro": "R",
                    "texto": "T",
                    "epoca": 10,
                    "epoca_nombre": "Decima Epoca",
                    "tipo": "jurisprudencia",
                }
            ]
        )
        scraper._fill_search_form = MagicMock()
        scraper.scrape_catalog = MagicMock()

        with patch.object(scraper, "_launch") as mock_launch:
            summary = scraper.run(epoca=10, tipo="jurisprudencia", enrich=False)

        mock_launch.assert_called_once()
        assert summary["method"] == "inpage_api"
        scraper._fill_search_form.assert_not_called()
        scraper.scrape_catalog.assert_not_called()

    def test_falls_through_to_dom_when_inpage_api_also_empty(self, scraper):
        scraper._scrape_via_api = MagicMock(side_effect=SjfApiError("blocked"))
        scraper._navigate_to_search = MagicMock(return_value=True)
        scraper._scrape_via_inpage_api = MagicMock(return_value=[])
        scraper._fill_search_form = MagicMock(return_value=True)
        scraper.scrape_catalog = MagicMock(
            return_value=[
                {
                    "registro": "1",
                    "rubro": "R",
                    "texto": "T",
                    "epoca": 10,
                    "epoca_nombre": "Decima Epoca",
                    "tipo": "jurisprudencia",
                }
            ]
        )

        with patch.object(scraper, "_launch") as mock_launch, patch(
            "apps.scraper.judicial.scjn_playwright.time.sleep"
        ):
            summary = scraper.run(epoca=10, tipo="jurisprudencia", enrich=False)

        mock_launch.assert_called_once()
        scraper._fill_search_form.assert_called_once()
        scraper.scrape_catalog.assert_called_once()
        assert summary["method"] == "dom"
        assert summary["total_items"] == 1

    def test_navigation_failure_returns_error_summary(self, scraper):
        scraper._scrape_via_api = MagicMock(side_effect=SjfApiError("blocked"))
        scraper._navigate_to_search = MagicMock(return_value=False)

        with patch.object(scraper, "_launch"):
            summary = scraper.run(epoca=10, tipo="jurisprudencia", enrich=False)

        assert summary["error"] == "navigation_failed"


# ---------------------------------------------------------------------------
# _fetch_detail_page
# ---------------------------------------------------------------------------


class TestFetchDetailPage:
    def test_detail_api_returns_texto_madfam_not_called(self, scraper):
        scraper.api.fetch_detail = MagicMock(
            return_value={
                "rubro": "<b>Rubro</b>",
                "texto": "<p>Full body</p>",
                "precedentes": "Prec",
                "materias": "Civil",
                "claveTesis": "P./J. 1/2024",
                "instanciaAbr": "Pleno",
            }
        )
        scraper.madfam.extract_sync = MagicMock()

        result = scraper._fetch_detail_page("2031846", semanal=False)

        assert result["rubro"] == "Rubro"
        assert result["texto"] == "Full body"
        assert result["precedentes"] == "Prec"
        assert result["materia"] == "Civil"
        assert result["tesis_num"] == "P./J. 1/2024"
        assert result["instancia"] == "Pleno"
        scraper.madfam.extract_sync.assert_not_called()

    def test_both_semanal_variants_error_falls_back_to_madfam(self, scraper):
        scraper.api.fetch_detail = MagicMock(side_effect=SjfApiError("not found"))
        scraper.madfam.extract_sync = MagicMock(
            return_value={"rubro": "From madfam", "texto": "Madfam body"}
        )

        result = scraper._fetch_detail_page("2031846", semanal=False)

        assert result == {"rubro": "From madfam", "texto": "Madfam body"}
        assert scraper.api.fetch_detail.call_count == 2
        scraper.madfam.extract_sync.assert_called_once()

    def test_first_variant_empty_second_variant_has_texto_uses_second(self, scraper):
        scraper.api.fetch_detail = MagicMock(
            side_effect=[
                {},
                {"rubro": "R2", "texto": "T2"},
            ]
        )
        scraper.madfam.extract_sync = MagicMock()

        result = scraper._fetch_detail_page("2031846", semanal=False)

        assert result["texto"] == "T2"
        assert scraper.api.fetch_detail.call_count == 2
        scraper.madfam.extract_sync.assert_not_called()

    def test_madfam_tesis_key_remapped_to_tesis_num(self, scraper):
        scraper.api.fetch_detail = MagicMock(side_effect=SjfApiError("gone"))
        scraper.madfam.extract_sync = MagicMock(
            return_value={"rubro": "R", "texto": "T", "tesis": "P./J. 9/2024"}
        )

        result = scraper._fetch_detail_page("1", semanal=False)

        assert result["tesis_num"] == "P./J. 9/2024"
        assert "tesis" not in result


# ---------------------------------------------------------------------------
# run_enrich_only — no browser launch
# ---------------------------------------------------------------------------


class TestRunEnrichOnly:
    def test_run_enrich_only_does_not_launch_browser(self, scraper, tmp_path):
        input_path = tmp_path / "existing.json"
        input_path.write_text(
            '[{"registro": "1", "rubro": "R", "texto": "already there"}]',
            encoding="utf-8",
        )

        with patch.object(scraper, "_launch") as mock_launch:
            summary = scraper.run_enrich_only(
                input_path=str(input_path), epoca=10, tipo="jurisprudencia"
            )

        mock_launch.assert_not_called()
        assert summary["total_items"] == 1
        assert "error" not in summary
