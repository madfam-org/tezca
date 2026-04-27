"""Tests for ``apps.scraper.federal.sinec_scraper``.

Covers pure helpers + HTTP-coupled paths via mocked sessions. Same
pattern as test_treaty_scraper_full.py and test_scjn_scraper_full.py.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests
from bs4 import BeautifulSoup

from apps.scraper.federal.sinec_scraper import (
    SinecScraper,
    _clean_text,
    _extract_agency_from_nom,
    _extract_date,
    _normalize_status,
    _normalize_text,
    _resolve_agency_name,
)

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_normalize_text_strips_accents_and_lowers():
    assert _normalize_text("Vigéntè") == "vigente"
    assert _normalize_text("  Multiple   Spaces  ") == "multiple spaces"


def test_clean_text_collapses_whitespace():
    assert _clean_text("  multiple   spaces\n\there  ") == "multiple spaces here"


def test_normalize_status_canonical_values():
    assert _normalize_status("Vigente") == "vigente"
    assert _normalize_status("EN VIGOR") == "vigente"
    assert _normalize_status("Cancelada") == "cancelada"
    assert _normalize_status("CANCELADO") == "cancelada"
    assert _normalize_status("En proyecto") == "en_proyecto"
    assert _normalize_status("Proyecto") == "en_proyecto"


def test_normalize_status_passthrough_when_no_match():
    out = _normalize_status("custom-status")
    assert out == "custom-status"


def test_extract_agency_from_nom_three_part():
    assert _extract_agency_from_nom("NOM-001-SSA1-2010") == "SSA1"
    assert _extract_agency_from_nom("NOM-059-SEMARNAT-2010") == "SEMARNAT"


def test_extract_agency_from_nom_handles_short_strings():
    assert _extract_agency_from_nom("nom-001") == ""
    assert _extract_agency_from_nom("") == ""


def test_resolve_agency_name_known_abbreviation():
    assert "Salud" in _resolve_agency_name("SSA")
    assert "Medio Ambiente" in _resolve_agency_name("SEMARNAT")


def test_resolve_agency_name_prefix_match():
    """SSA1 should resolve to SSA's full name via prefix matching."""
    assert "Salud" in _resolve_agency_name("SSA1")


def test_resolve_agency_name_passthrough_for_unknown():
    assert _resolve_agency_name("UNKNOWN-AGENCY") == "UNKNOWN-AGENCY"


def test_extract_date_dd_slash_mm_yyyy():
    assert _extract_date("Publicado 15/03/2024") == "2024-03-15"


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
    s = SinecScraper.__new__(SinecScraper)
    s.session = MagicMock()
    s.last_request_time = 0.0
    s._view_state = None
    return s


def test_init_creates_session():
    scraper = SinecScraper()
    assert scraper.session is not None
    assert scraper.last_request_time == 0.0
    assert scraper._view_state is None


def test_rate_limit_sleeps_when_too_fast(scraper):
    import time

    scraper.last_request_time = time.time()
    with patch("apps.scraper.federal.sinec_scraper.time.sleep") as msleep:
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


def test_get_returns_none_on_4xx_non_429(scraper):
    """Client errors (except 429) short-circuit without retry."""
    fake_resp = MagicMock()
    fake_resp.status_code = 404
    err = requests.HTTPError(response=fake_resp)
    fake_resp.raise_for_status.side_effect = err
    scraper.session.get.return_value = fake_resp
    with patch.object(scraper, "_rate_limit"), patch(
        "apps.scraper.federal.sinec_scraper.time.sleep"
    ):
        assert scraper._get("https://x.com") is None


def test_get_retries_on_connection_error(scraper):
    scraper.session.get.side_effect = requests.ConnectionError
    with patch.object(scraper, "_rate_limit"), patch(
        "apps.scraper.federal.sinec_scraper.time.sleep"
    ):
        out = scraper._get("https://x.com")
    assert out is None
    # Should have retried up to _MAX_RETRIES times
    assert scraper.session.get.call_count >= 2


def test_get_returns_none_on_timeout(scraper):
    scraper.session.get.side_effect = requests.Timeout
    with patch.object(scraper, "_rate_limit"), patch(
        "apps.scraper.federal.sinec_scraper.time.sleep"
    ):
        assert scraper._get("https://x.com") is None


def test_get_returns_none_on_request_exception(scraper):
    scraper.session.get.side_effect = requests.RequestException("generic")
    with patch.object(scraper, "_rate_limit"), patch(
        "apps.scraper.federal.sinec_scraper.time.sleep"
    ):
        assert scraper._get("https://x.com") is None


def test_post_returns_response_on_success(scraper):
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    scraper.session.post.return_value = fake_resp
    with patch.object(scraper, "_rate_limit"):
        out = scraper._post("https://x.com", data={"key": "val"})
    assert out is fake_resp


def test_post_returns_none_on_4xx_non_429(scraper):
    fake_resp = MagicMock()
    fake_resp.status_code = 400
    err = requests.HTTPError(response=fake_resp)
    fake_resp.raise_for_status.side_effect = err
    scraper.session.post.return_value = fake_resp
    with patch.object(scraper, "_rate_limit"), patch(
        "apps.scraper.federal.sinec_scraper.time.sleep"
    ):
        assert scraper._post("https://x.com", data={}) is None


def test_post_returns_none_on_timeout(scraper):
    scraper.session.post.side_effect = requests.Timeout
    with patch.object(scraper, "_rate_limit"), patch(
        "apps.scraper.federal.sinec_scraper.time.sleep"
    ):
        assert scraper._post("https://x.com", data={}) is None


# ---------------------------------------------------------------------------
# _extract_view_state
# ---------------------------------------------------------------------------


def test_extract_view_state_from_input_element(scraper):
    html = '<input name="javax.faces.ViewState" value="abc123"/>'
    out = scraper._extract_view_state(html)
    assert out == "abc123"
    assert scraper._view_state == "abc123"


def test_extract_view_state_via_regex_fallback(scraper):
    """Some pages embed ViewState in a script literal — regex catches it."""
    html = '<script>var x = {javax.faces.ViewState"value="regex_token"};</script>'
    out = scraper._extract_view_state(html)
    assert out == "regex_token"


def test_extract_view_state_returns_none_when_missing(scraper):
    assert scraper._extract_view_state("<html></html>") is None
    assert scraper._view_state is None


def test_extract_view_state_skips_input_with_empty_value(scraper):
    html = '<input name="javax.faces.ViewState" value=""/>'
    assert scraper._extract_view_state(html) is None


# ---------------------------------------------------------------------------
# _initialize_search_page
# ---------------------------------------------------------------------------


def test_initialize_search_page_returns_false_on_get_failure(scraper):
    with patch.object(scraper, "_get", return_value=None):
        assert scraper._initialize_search_page() is False


def test_initialize_search_page_with_view_state(scraper):
    fake_resp = MagicMock()
    fake_resp.text = '<input name="javax.faces.ViewState" value="vs1"/>'
    with patch.object(scraper, "_get", return_value=fake_resp):
        assert scraper._initialize_search_page() is True
    assert scraper._view_state == "vs1"


def test_initialize_search_page_without_view_state_still_succeeds(scraper):
    """When no ViewState is found, return True (page is plain HTML)."""
    fake_resp = MagicMock()
    fake_resp.text = "<html><body>no JSF</body></html>"
    with patch.object(scraper, "_get", return_value=fake_resp):
        assert scraper._initialize_search_page() is True


# ---------------------------------------------------------------------------
# _parse_sinec_results / _parse_sinec_plain_html / _parse_result_row
# ---------------------------------------------------------------------------


def test_parse_result_row_extracts_full_record(scraper):
    html = """
    <table><tbody>
      <tr>
        <td>NOM-001-SSA1-2010</td>
        <td>Norma de equipo médico</td>
        <td>SSA1</td>
        <td>15/03/2010</td>
        <td>Vigente</td>
      </tr>
    </tbody></table>
    """
    row = BeautifulSoup(html, "html.parser").find("tr")
    out = scraper._parse_result_row(row)
    assert out is not None
    assert out["nom_id"] == "NOM-001-SSA1-2010"
    assert "equipo" in out["title"]
    assert out["status"] == "vigente"
    assert out["date_published"] == "2010-03-15"


def test_parse_result_row_returns_none_when_no_nom_pattern(scraper):
    html = "<tr><td>Not a NOM</td><td>Junk</td></tr>"
    row = BeautifulSoup(html, "html.parser").find("tr")
    assert scraper._parse_result_row(row) is None


def test_parse_result_row_detects_cancelada_in_text(scraper):
    html = """
    <tr>
      <td>NOM-002-SSA1-2015 (cancelada)</td>
      <td>Old norm</td>
    </tr>
    """
    row = BeautifulSoup(html, "html.parser").find("tr")
    out = scraper._parse_result_row(row)
    assert out["status"] == "cancelada"


def test_parse_result_row_extracts_dof_reference(scraper):
    html = """
    <tr>
      <td>NOM-003-SE-2020 DOF: 15/03/2020</td>
      <td>Title</td>
    </tr>
    """
    row = BeautifulSoup(html, "html.parser").find("tr")
    out = scraper._parse_result_row(row)
    assert "DOF" in out["dof_reference"]


def test_parse_result_row_resolves_relative_url(scraper):
    html = """
    <tr>
      <td><a href="/detalle/123">NOM-001-SSA1-2010</a></td>
      <td>Title</td>
    </tr>
    """
    row = BeautifulSoup(html, "html.parser").find("tr")
    out = scraper._parse_result_row(row)
    assert out["url"].startswith("https://sinec.gob.mx/")


def test_parse_sinec_results_handles_jsf_cdata(scraper):
    """JSF AJAX responses wrap HTML in <update><![CDATA[...]]>."""
    html = """
    <partial-response>
      <changes>
        <update><![CDATA[
          <table><tbody>
            <tr>
              <td>NOM-007-SSA1-2010</td>
              <td>Body of norm</td>
            </tr>
          </tbody></table>
        ]]></update>
      </changes>
    </partial-response>
    """
    out = scraper._parse_sinec_results(html)
    assert len(out) == 1
    assert out[0]["nom_id"] == "NOM-007-SSA1-2010"


def test_parse_sinec_results_handles_plain_html(scraper):
    """When CDATA absent, parse the html directly."""
    html = "<table><tbody><tr><td>NOM-008-SSA1-2015</td><td>X</td></tr></tbody></table>"
    out = scraper._parse_sinec_results(html)
    assert len(out) == 1


def test_parse_sinec_plain_html_extracts_via_text_pattern(scraper):
    html = """
    <html><body>
      <div class="result">NOM-009-SSA1-2020 — Some norm description (vigente) DOF 01/01/2020</div>
    </body></html>
    """
    out = scraper._parse_sinec_plain_html(html)
    assert len(out) >= 1
    # Find the entry that matches our NOM
    matching = [n for n in out if n["nom_id"] == "NOM-009-SSA1-2020"]
    assert len(matching) >= 1
    assert matching[0]["status"] == "vigente"


def test_parse_sinec_plain_html_detects_cancelada(scraper):
    html = '<div class="result">NOM-010-SSA1-2020 cancelada</div>'
    out = scraper._parse_sinec_plain_html(html)
    matching = [n for n in out if n["nom_id"] == "NOM-010-SSA1-2020"]
    assert matching and matching[0]["status"] == "cancelada"


def test_parse_sinec_plain_html_detects_proyecto(scraper):
    html = '<div class="result">PROY-NOM-011-SSA1-2025 proyecto</div>'
    out = scraper._parse_sinec_plain_html(html)
    matching = [n for n in out if "011" in n["nom_id"]]
    assert matching and matching[0]["status"] == "en_proyecto"


# ---------------------------------------------------------------------------
# Checkpoint / save_results
# ---------------------------------------------------------------------------


def test_save_and_load_checkpoint_round_trip(scraper, tmp_path):
    noms = [
        {"nom_id": "NOM-001-SSA1-2010", "title": "X"},
        {"nom_id": "NOM-002-SSA1-2010", "title": "Y"},
    ]
    scraper.save_checkpoint(noms, tmp_path)
    loaded = scraper.load_checkpoint(tmp_path)
    assert loaded == noms


def test_load_checkpoint_returns_empty_when_missing(scraper, tmp_path):
    assert scraper.load_checkpoint(tmp_path / "nope") == []


def test_load_checkpoint_returns_empty_on_invalid_json(scraper, tmp_path):
    # Write a checkpoint file at the path the loader expects.
    from apps.scraper.federal.sinec_scraper import _CHECKPOINT_FILENAME

    (tmp_path / _CHECKPOINT_FILENAME).write_text("not json", encoding="utf-8")
    assert scraper.load_checkpoint(tmp_path) == []


def test_save_results_writes_json(tmp_path):
    out = tmp_path / "out" / "result.json"
    SinecScraper.save_results([{"nom_id": "NOM-001"}], out)
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8")) == [{"nom_id": "NOM-001"}]
