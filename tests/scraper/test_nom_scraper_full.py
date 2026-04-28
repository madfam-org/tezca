"""Comprehensive tests for ``apps.scraper.federal.nom_scraper``.

The pre-existing test_federal_scrapers.py covers a handful of init/method-
existence smoke tests. This file adds the bulk of the coverage: pure
helpers, HTML parsing, HTTP error matrix, and high-level orchestration
via mocked sessions.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.scraper.federal.nom_scraper import (
    NomScraper,
    _clean_text,
    _extract_date,
    _extract_secretaria,
)

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_clean_text_collapses_whitespace():
    assert _clean_text("  multiple   spaces\n\there  ") == "multiple spaces here"


def test_clean_text_handles_empty():
    assert _clean_text("") == ""


def test_extract_secretaria_known_agency():
    out = _extract_secretaria("NOM-001-SSA1-2010")
    assert "Salud" in out


def test_extract_secretaria_prefix_match():
    """SSA1 should resolve via prefix match if not exact."""
    out = _extract_secretaria("NOM-001-SSA1-2010")
    assert out  # non-empty


def test_extract_secretaria_returns_empty_for_short():
    assert _extract_secretaria("NOM-001") == ""


def test_extract_secretaria_returns_empty_for_unknown():
    assert _extract_secretaria("NOM-001-UNKNOWNAGENCY-2010") == ""


def test_extract_date_dd_slash_mm_yyyy():
    assert _extract_date("Publicado el 15/03/2024") == "2024-03-15"


def test_extract_date_dd_dash_mm_yyyy():
    assert _extract_date("DOF: 15-03-2024") == "2024-03-15"


def test_extract_date_iso():
    assert _extract_date("2024-01-15") == "2024-01-15"


def test_extract_date_returns_empty_on_no_match():
    assert _extract_date("no date") == ""
    assert _extract_date("") == ""


# ---------------------------------------------------------------------------
# Scraper instance setup
# ---------------------------------------------------------------------------


@pytest.fixture
def scraper():
    """Build a scraper without invoking the real session setup."""
    s = NomScraper.__new__(NomScraper)
    s.session = MagicMock()
    s.last_request_time = 0.0
    return s


def test_init_creates_session():
    scraper = NomScraper()
    assert scraper.session is not None
    assert scraper.last_request_time == 0.0


def test_rate_limit_sleeps_when_too_fast(scraper):
    import time

    scraper.last_request_time = time.time()
    with patch("apps.scraper.federal.nom_scraper.time.sleep") as msleep:
        scraper._rate_limit()
    msleep.assert_called_once()


# ---------------------------------------------------------------------------
# _get / _post — error matrix
# ---------------------------------------------------------------------------


def test_get_returns_response_on_success(scraper):
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    scraper.session.get.return_value = fake_resp
    with patch.object(scraper, "_rate_limit"):
        out = scraper._get("https://x.com")
    assert out is fake_resp


@pytest.mark.parametrize(
    "exc_cls",
    [requests.ConnectionError, requests.Timeout, requests.RequestException],
)
def test_get_returns_none_on_exception(scraper, exc_cls):
    scraper.session.get.side_effect = exc_cls
    with patch.object(scraper, "_rate_limit"):
        assert scraper._get("https://x.com") is None


def test_get_returns_none_on_http_error(scraper):
    fake_resp = MagicMock()
    fake_resp.status_code = 500
    err = requests.HTTPError(response=fake_resp)
    fake_resp.raise_for_status.side_effect = err
    scraper.session.get.return_value = fake_resp
    with patch.object(scraper, "_rate_limit"):
        assert scraper._get("https://x.com") is None


def test_post_returns_response_on_success(scraper):
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    scraper.session.post.return_value = fake_resp
    with patch.object(scraper, "_rate_limit"):
        out = scraper._post("https://x.com", data={"k": "v"})
    assert out is fake_resp


@pytest.mark.parametrize(
    "exc_cls",
    [requests.ConnectionError, requests.Timeout, requests.RequestException],
)
def test_post_returns_none_on_exception(scraper, exc_cls):
    scraper.session.post.side_effect = exc_cls
    with patch.object(scraper, "_rate_limit"):
        assert scraper._post("https://x.com", data={}) is None


def test_post_returns_none_on_http_error(scraper):
    fake_resp = MagicMock()
    fake_resp.status_code = 500
    err = requests.HTTPError(response=fake_resp)
    fake_resp.raise_for_status.side_effect = err
    scraper.session.post.return_value = fake_resp
    with patch.object(scraper, "_rate_limit"):
        assert scraper._post("https://x.com", data={}) is None


# ---------------------------------------------------------------------------
# _parse_search_results — HTML extraction strategies
# ---------------------------------------------------------------------------


def test_parse_search_results_strategy1_dof_layout(scraper):
    """Current DOF layout: td.txt_azul cells with nota_detalle links."""
    html = """
    <html><body>
      <table>
        <tr>
          <td class="txt_azul">
            <a href="/nota_detalle.php?codigo=12345">NOM-001-SSA1-2010</a>
            <b>Publicado: 15/03/2010</b>
          </td>
        </tr>
      </table>
    </body></html>
    """
    out = scraper._parse_search_results(html)
    assert len(out) == 1
    assert out[0]["nom_number"] == "NOM-001-SSA1-2010"
    assert out[0]["secretaria"]  # populated
    assert out[0]["date_published"] == "2010-03-15"
    assert out[0]["status"] == "vigente"
    assert out[0]["source"] == "dof_archive"


def test_parse_search_results_resolves_relative_href(scraper):
    html = """
    <table><tr><td class="txt_azul">
      <a href="/nota_detalle.php?codigo=999">NOM-002-SSA1-2015</a>
    </td></tr></table>
    """
    out = scraper._parse_search_results(html)
    assert out[0]["url"].startswith("https://")


def test_parse_search_results_skips_non_nom_titles(scraper):
    html = """
    <table><tr><td class="txt_azul">
      <a href="/nota_detalle.php?codigo=1">Not a NOM document</a>
    </td></tr></table>
    """
    out = scraper._parse_search_results(html)
    assert out == []


def test_parse_search_results_strategy2_fallback_layout(scraper):
    """Fallback when no .txt_azul cells: scan .resultado / .nota / tr."""
    html = """
    <html><body>
      <div class="resultado">
        <a href="/x.html">NOM-005-SCFI-2020 — alguna norma</a>
      </div>
    </body></html>
    """
    out = scraper._parse_search_results(html)
    # Either strategy 1 (td.txt_azul absent) or strategy 2 picks it up
    assert any(item["nom_number"] == "NOM-005-SCFI-2020" for item in out)


def test_parse_search_results_id_is_lowercase_underscore(scraper):
    html = """
    <table><tr><td class="txt_azul">
      <a href="/x.html">NOM-007-SSA1-2020</a>
    </td></tr></table>
    """
    out = scraper._parse_search_results(html)
    assert out[0]["id"] == "nom_007_ssa1_2020"


def test_parse_search_results_empty_html(scraper):
    assert scraper._parse_search_results("<html></html>") == []


def test_parse_search_results_skips_link_with_empty_title(scraper):
    html = """
    <table><tr><td class="txt_azul">
      <a href="/x.html"></a>
    </td></tr></table>
    """
    out = scraper._parse_search_results(html)
    assert out == []


# ---------------------------------------------------------------------------
# scrape_dof_archive — pagination + dedup
# ---------------------------------------------------------------------------


def test_scrape_dof_archive_stops_on_get_failure(scraper):
    """If _post returns None on the first page, scraper bails immediately."""
    with patch.object(scraper, "_post", return_value=None):
        out = scraper.scrape_dof_archive(max_results=10)
    assert out == []


def test_scrape_dof_archive_stops_on_empty_page(scraper):
    fake_resp = MagicMock(text="<html></html>")
    with patch.object(scraper, "_post", return_value=fake_resp), patch.object(
        scraper, "_parse_search_results", return_value=[]
    ):
        out = scraper.scrape_dof_archive(max_results=10)
    assert out == []


def test_scrape_dof_archive_dedups_across_pages(scraper):
    """A NOM number seen on page 1 is skipped if it reappears on page 2."""
    fake_resp = MagicMock(text="<html>placeholder</html>")
    nom_a = {"nom_number": "NOM-001-SSA1-2010", "name": "A"}
    nom_b = {"nom_number": "NOM-002-SSA1-2010", "name": "B"}

    call_count = {"n": 0}

    def _parse(*_args, **_kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return [nom_a, nom_b]
        if call_count["n"] == 2:
            return [nom_a]  # all duplicates → triggers stop
        return []

    with patch.object(scraper, "_post", return_value=fake_resp), patch.object(
        scraper, "_parse_search_results", side_effect=_parse
    ):
        out = scraper.scrape_dof_archive(max_results=100)

    # Both unique entries collected
    assert len(out) == 2


def test_scrape_dof_archive_respects_max_results(scraper):
    fake_resp = MagicMock(text="<html>x</html>")
    noms = [
        {"nom_number": f"NOM-{i:03d}-SSA1-2024", "name": f"N{i}"} for i in range(20)
    ]
    with patch.object(scraper, "_post", return_value=fake_resp), patch.object(
        scraper, "_parse_search_results", return_value=noms
    ):
        out = scraper.scrape_dof_archive(max_results=5)
    assert len(out) == 5


# ---------------------------------------------------------------------------
# _merge_nom_lists
# ---------------------------------------------------------------------------


def test_merge_nom_lists_dedupes_by_nom_number():
    a = [{"nom_number": "NOM-001-SSA1-2010", "name": "X", "extra": "from-a"}]
    b = [{"nom_number": "NOM-001-SSA1-2010", "name": "X", "extra": "from-b"}]
    out = NomScraper._merge_nom_lists(a, b)
    assert len(out) == 1
    assert out[0]["extra"] == "from-a"  # first-seen wins


def test_merge_nom_lists_skips_entries_without_nom_number():
    a = [{"nom_number": "", "name": "no-id"}, {"nom_number": "NOM-1", "name": "ok"}]
    out = NomScraper._merge_nom_lists(a)
    assert len(out) == 1
    assert out[0]["nom_number"] == "NOM-1"


def test_merge_nom_lists_preserves_uniques_across_sources():
    a = [{"nom_number": "NOM-1", "name": "A"}]
    b = [{"nom_number": "NOM-2", "name": "B"}]
    c = [{"nom_number": "NOM-3", "name": "C"}]
    out = NomScraper._merge_nom_lists(a, b, c)
    assert len(out) == 3


# ---------------------------------------------------------------------------
# save_results
# ---------------------------------------------------------------------------


def test_save_results_writes_json(tmp_path):
    out = tmp_path / "out" / "result.json"
    NomScraper.save_results([{"nom_number": "NOM-001"}], out)
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8")) == [{"nom_number": "NOM-001"}]


# ---------------------------------------------------------------------------
# run — high-level orchestration
# ---------------------------------------------------------------------------


def test_run_default_invokes_general_search(scraper, tmp_path):
    with patch.object(
        scraper, "scrape_dof_archive", return_value=[{"nom_number": "NOM-1"}]
    ) as m, patch.object(NomScraper, "save_results"):
        summary = scraper.run(output_dir=str(tmp_path), max_results=10)
    m.assert_called_once()
    assert summary["total_noms"] == 1
    assert "general" in summary["modes_used"]


def test_run_priority_only_skips_general_search(scraper, tmp_path):
    with patch.object(
        scraper, "scrape_priority_noms", return_value=[]
    ) as priority_mock, patch.object(
        scraper, "scrape_dof_archive"
    ) as general_mock, patch.object(
        NomScraper, "save_results"
    ):
        summary = scraper.run(
            output_dir=str(tmp_path), priority_only=True, max_results=10
        )
    priority_mock.assert_called_once()
    general_mock.assert_not_called()
    assert "priority" in summary["modes_used"]


def test_run_all_agencies_combines_modes(scraper, tmp_path):
    with patch.object(scraper, "scrape_dof_archive", return_value=[]), patch.object(
        scraper, "scrape_all_agencies", return_value=[]
    ) as all_mock, patch.object(NomScraper, "save_results"):
        summary = scraper.run(
            output_dir=str(tmp_path), all_agencies=True, max_results=10
        )
    all_mock.assert_called_once()
    assert "all_agencies" in summary["modes_used"]


def test_run_with_year_range_invokes_year_scraper(scraper, tmp_path):
    with patch.object(scraper, "scrape_dof_archive", return_value=[]), patch.object(
        scraper, "scrape_by_year_range", return_value=[]
    ) as year_mock, patch.object(NomScraper, "save_results"):
        summary = scraper.run(
            output_dir=str(tmp_path), year_range=(2020, 2022), max_results=10
        )
    year_mock.assert_called_once()
    assert summary["year_range"] == [2020, 2022]
    assert any("year_range" in m for m in summary["modes_used"])
