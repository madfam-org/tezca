"""Comprehensive tests for ``apps.scraper.federal.conamer_scraper``.

Targets pure helpers + HTML parsing + dedup logic. The HTTP-coupled
methods are exercised via mocked sessions.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.scraper.federal.conamer_scraper import (
    ConamerScraper,
    _normalise_title,
    _strip_accents,
)

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def test_strip_accents_removes_diacritics():
    assert _strip_accents("regulación") == "regulacion"
    assert _strip_accents("Tratado") == "Tratado"
    assert _strip_accents("ÁéÍóÚñ") == "AeIoUn"


def test_normalise_title_lowers_and_strips_punctuation():
    out = _normalise_title("Reglamento Federal de Cosas: Importantes!")
    assert "reglamento" in out
    assert "cosas" in out
    assert ":" not in out
    assert "!" not in out


def test_normalise_title_handles_empty_string():
    assert _normalise_title("") == ""


# ---------------------------------------------------------------------------
# Scraper instance setup
# ---------------------------------------------------------------------------


@pytest.fixture
def scraper():
    s = ConamerScraper.__new__(ConamerScraper)
    s.session = MagicMock()
    s.last_request_time = 0.0
    s._api_endpoint = None
    return s


def test_init_creates_session():
    scraper = ConamerScraper()
    assert scraper.session is not None
    assert scraper.last_request_time == 0.0
    assert scraper._api_endpoint is None


def test_rate_limit_sleeps_when_too_fast(scraper):
    import time

    scraper.last_request_time = time.time()
    with patch("apps.scraper.federal.conamer_scraper.time.sleep") as msleep:
        scraper._rate_limit()
    msleep.assert_called_once()


# ---------------------------------------------------------------------------
# _get — HTTP error matrix
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


# ---------------------------------------------------------------------------
# _extract_items_from_json
# ---------------------------------------------------------------------------


def test_extract_items_from_list_passthrough():
    items = [{"id": 1}, {"id": 2}]
    assert ConamerScraper._extract_items_from_json(items) == items


def test_extract_items_from_dict_with_results_key():
    data = {"results": [{"id": 1}]}
    assert ConamerScraper._extract_items_from_json(data) == [{"id": 1}]


def test_extract_items_from_dict_with_regulaciones_key():
    data = {"regulaciones": [{"id": 1}]}
    assert ConamerScraper._extract_items_from_json(data) == [{"id": 1}]


def test_extract_items_returns_empty_on_unknown():
    assert ConamerScraper._extract_items_from_json({"unknown": "shape"}) == []
    assert ConamerScraper._extract_items_from_json(None) == []


# ---------------------------------------------------------------------------
# _normalize_item
# ---------------------------------------------------------------------------


def test_normalize_item_canonical_fields():
    raw = {
        "id": 42,
        "nombre": "Reglamento de Aguas",
        "dependencia": "CONAGUA",
        "fecha_publicacion": "2024-03-15",
        "url": "https://conamer.gob.mx/r/42",
        "tipo": "Reglamento",
    }
    out = ConamerScraper._normalize_item(raw)
    assert out is not None
    assert out["id"] == "42"
    assert out["name"] == "Reglamento de Aguas"
    assert out["issuing_body"] == "CONAGUA"
    assert out["date"] == "2024-03-15"
    assert out["url"] == "https://conamer.gob.mx/r/42"
    assert out["regulation_type"] == "Reglamento"
    assert out["source"] == "conamer_cnartys"


def test_normalize_item_alternate_field_names():
    raw = {
        "title": "Alt Title",
        "issuing_body": "Alt Body",
        "date": "2024-01-01",
        "enlace": "https://x.com",
        "regulation_type": "Decreto",
    }
    out = ConamerScraper._normalize_item(raw)
    assert out["name"] == "Alt Title"
    assert out["issuing_body"] == "Alt Body"
    assert out["url"] == "https://x.com"


def test_normalize_item_returns_none_when_no_name():
    assert ConamerScraper._normalize_item({}) is None
    assert ConamerScraper._normalize_item({"id": "x"}) is None


# ---------------------------------------------------------------------------
# _parse_html_catalog
# ---------------------------------------------------------------------------


def test_parse_html_catalog_strategy1_table_rows(scraper):
    html = """
    <table><tbody>
      <tr>
        <td><a href="/r/1">Reglamento de Aguas</a></td>
        <td>CONAGUA</td>
        <td>2024-03-15</td>
        <td>Reglamento</td>
      </tr>
    </tbody></table>
    """
    out = scraper._parse_html_catalog(html)
    assert len(out) == 1
    assert out[0]["name"] == "Reglamento de Aguas"
    assert out[0]["issuing_body"] == "CONAGUA"
    assert out[0]["date"] == "2024-03-15"
    assert out[0]["url"].startswith("https://")


def test_parse_html_catalog_skips_short_names(scraper):
    """Names shorter than 5 chars are dropped."""
    html = """
    <table><tbody>
      <tr><td><a href="/r/1">X</a></td></tr>
    </tbody></table>
    """
    out = scraper._parse_html_catalog(html)
    assert out == []


def test_parse_html_catalog_skips_too_few_cells(scraper):
    """Rows with <2 cells are skipped."""
    html = """
    <table><tbody>
      <tr><td>Solo una celda</td></tr>
    </tbody></table>
    """
    out = scraper._parse_html_catalog(html)
    assert out == []


def test_parse_html_catalog_strategy2_card_layout(scraper):
    """When tables yield nothing, scan card / list-item / article elements."""
    html = """
    <html><body>
      <article>
        <h3>Reglamento Federal Importante</h3>
        <a href="/r/1">link</a>
      </article>
    </body></html>
    """
    out = scraper._parse_html_catalog(html)
    assert len(out) == 1
    assert "Importante" in out[0]["name"]


def test_parse_html_catalog_card_no_title_skipped(scraper):
    html = "<article><p>just text, no h2/h3/a/strong</p></article>"
    out = scraper._parse_html_catalog(html)
    assert out == []


def test_parse_html_catalog_empty_html_returns_empty(scraper):
    assert scraper._parse_html_catalog("<html></html>") == []


# ---------------------------------------------------------------------------
# dedup_against_existing
# ---------------------------------------------------------------------------


def test_dedup_against_existing_drops_matches():
    incoming = [
        {"name": "Reglamento de Aguas"},
        {"name": "Decreto Nuevo"},
    ]
    existing = {"reglamento de aguas"}
    out = ConamerScraper.dedup_against_existing(incoming, existing)
    assert len(out) == 1
    assert out[0]["name"] == "Decreto Nuevo"


def test_dedup_against_existing_normalises_accents():
    """An accent-only difference should still match as duplicate."""
    incoming = [{"name": "Regulación de cosas"}]
    existing = {"regulacion de cosas"}
    out = ConamerScraper.dedup_against_existing(incoming, existing)
    assert out == []


def test_dedup_against_existing_skips_empty_names():
    incoming = [{"name": ""}, {"name": "Real Name"}]
    out = ConamerScraper.dedup_against_existing(incoming, set())
    assert len(out) == 1
    assert out[0]["name"] == "Real Name"


def test_dedup_against_existing_with_no_duplicates():
    incoming = [{"name": "Unique A"}, {"name": "Unique B"}]
    out = ConamerScraper.dedup_against_existing(incoming, {"different"})
    assert len(out) == 2


# ---------------------------------------------------------------------------
# save_batch
# ---------------------------------------------------------------------------


def test_save_batch_writes_numbered_file(tmp_path):
    items = [{"name": "x"}]
    out = ConamerScraper.save_batch(items, tmp_path, batch_number=42)
    assert out.exists()
    assert out.name == "batch_0042.json"
    assert json.loads(out.read_text(encoding="utf-8")) == items


def test_save_batch_creates_missing_dir(tmp_path):
    target = tmp_path / "does" / "not" / "exist"
    out = ConamerScraper.save_batch([{"name": "x"}], target, batch_number=1)
    assert out.parent == target


# ---------------------------------------------------------------------------
# probe_api
# ---------------------------------------------------------------------------


def test_probe_api_finds_list_endpoint(scraper):
    fake_resp = MagicMock()
    fake_resp.headers = {"Content-Type": "application/json"}
    fake_resp.json.return_value = [{"id": 1, "nombre": "X"}]

    with patch.object(scraper, "_get", return_value=fake_resp):
        out = scraper.probe_api()

    assert out["found"] is True
    assert out["endpoint"] is not None
    assert scraper._api_endpoint is not None


def test_probe_api_finds_dict_results_endpoint(scraper):
    fake_resp = MagicMock()
    fake_resp.headers = {"Content-Type": "application/json"}
    fake_resp.json.return_value = {"results": [{"id": 1}]}

    with patch.object(scraper, "_get", return_value=fake_resp):
        out = scraper.probe_api()

    assert out["found"] is True


def test_probe_api_skips_non_json_response(scraper):
    fake_resp = MagicMock()
    fake_resp.headers = {"Content-Type": "text/html"}

    with patch.object(scraper, "_get", return_value=fake_resp):
        out = scraper.probe_api()

    assert out["found"] is False


def test_probe_api_skips_invalid_json(scraper):
    fake_resp = MagicMock()
    fake_resp.headers = {"Content-Type": "application/json"}
    fake_resp.json.side_effect = ValueError

    with patch.object(scraper, "_get", return_value=fake_resp):
        out = scraper.probe_api()

    assert out["found"] is False


def test_probe_api_handles_get_failure(scraper):
    with patch.object(scraper, "_get", return_value=None):
        out = scraper.probe_api()
    assert out["found"] is False


# ---------------------------------------------------------------------------
# scrape_catalog (delegates by api_endpoint presence)
# ---------------------------------------------------------------------------


def test_scrape_catalog_uses_api_when_endpoint_known(scraper):
    scraper._api_endpoint = "https://x.com/api"
    with patch.object(scraper, "_scrape_via_api", return_value=iter([])) as m:
        list(scraper.scrape_catalog())
    m.assert_called_once()


def test_scrape_catalog_uses_html_when_no_endpoint(scraper):
    with patch.object(scraper, "_scrape_via_html", return_value=iter([])) as m:
        list(scraper.scrape_catalog())
    m.assert_called_once()


# ---------------------------------------------------------------------------
# run — high-level orchestration
# ---------------------------------------------------------------------------


def test_run_invokes_probe_then_paginate(scraper, tmp_path):
    fake_batch = [{"name": "Reg X"}]
    with patch.object(scraper, "probe_api", return_value={"found": True}), patch.object(
        scraper, "scrape_catalog", return_value=iter([fake_batch])
    ), patch.object(ConamerScraper, "save_batch") as save_mock:
        summary = scraper.run(output_dir=str(tmp_path))
    save_mock.assert_called_once()
    assert summary["total_items"] == 1


def test_run_skips_empty_batches_after_dedup(scraper, tmp_path):
    """When a batch is fully deduped, save_batch isn't called for it."""
    fake_batch = [{"name": "Existing"}]
    with patch.object(
        scraper, "probe_api", return_value={"found": False}
    ), patch.object(
        scraper, "scrape_catalog", return_value=iter([fake_batch])
    ), patch.object(
        ConamerScraper, "save_batch"
    ) as save_mock:
        summary = scraper.run(output_dir=str(tmp_path), existing_titles={"existing"})
    save_mock.assert_not_called()
    assert summary["total_items"] == 0
