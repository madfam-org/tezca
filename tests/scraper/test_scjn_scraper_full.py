"""Comprehensive tests for ``apps.scraper.judicial.scjn_scraper``.

Targets pure helpers + HTTP-coupled paths via mocked sessions. Coverage
focuses on the parts that are deterministic without a live SCJN portal:

* `_extract_datasets_from_json` — CKAN, list, dict-wrapper variants
* `_extract_download_links` — relative + absolute href handling
* `_looks_like_search_result` — list, dict, count-key, negative cases
* `_detect_pagination` — total/page/size key extraction + None
* `_extract_items_from_json` — wrapper key probing
* `_normalize_tesis` — field-name resilience, URL synthesis, None on empty
* `_extract_labeled_text` — class match, sibling, parent-text fallback
* `_parse_tesis_container/_table_row/_dl` — HTML extraction strategies
* `_parse_tesis_html` — strategy waterfall
* `check_open_data` / `probe_search_api` — full HTTP-mocked flow
* `save_batch` — directory layout + JSON content
* `import_bulk_dump` — JSON + CSV input, NDJSON fallback
* `_load_json_dump` — array + NDJSON
* `_load_csv_dump` — DictReader passthrough
* `_rate_limit` — sleep when requests are too fast
* `_get` — connection/timeout/HTTP/RequestException paths
* `run` — open_data short-circuit + full-pipeline orchestration
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests
from bs4 import BeautifulSoup

from apps.scraper.judicial.scjn_scraper import EPOCAS, ScjnScraper

# ---------------------------------------------------------------------------
# _extract_datasets_from_json
# ---------------------------------------------------------------------------


def test_extract_datasets_from_ckan_string_list():
    data = {"result": ["dataset_a", "dataset_b"]}
    out = ScjnScraper._extract_datasets_from_json(data)
    assert out == [
        {"name": "dataset_a", "type": "ckan_package"},
        {"name": "dataset_b", "type": "ckan_package"},
    ]


def test_extract_datasets_from_ckan_dict_list():
    data = {"result": [{"name": "x", "id": 1}, {"name": "y", "id": 2}]}
    out = ScjnScraper._extract_datasets_from_json(data)
    assert out == [{"name": "x", "id": 1}, {"name": "y", "id": 2}]


def test_extract_datasets_from_plain_list():
    data = [{"a": 1}, {"b": 2}, "skip-me"]
    out = ScjnScraper._extract_datasets_from_json(data)
    assert out == [{"a": 1}, {"b": 2}]


def test_extract_datasets_from_wrapper_dict():
    data = {"datasets": [{"id": 1}, {"id": 2}]}
    out = ScjnScraper._extract_datasets_from_json(data)
    assert len(out) == 2


def test_extract_datasets_returns_empty_on_unknown_shape():
    assert ScjnScraper._extract_datasets_from_json("not a list") == []
    assert ScjnScraper._extract_datasets_from_json({"some_other_key": "value"}) == []


# ---------------------------------------------------------------------------
# _extract_download_links
# ---------------------------------------------------------------------------


def test_extract_download_links_picks_known_extensions():
    html = """
    <html><body>
      <a href="https://example.com/data.csv">CSV</a>
      <a href="/local.json">JSON</a>
      <a href="report.xlsx">XLSX</a>
      <a href="archive.zip">ZIP</a>
      <a href="not-a-data-link">Skip</a>
    </body></html>
    """
    links = ScjnScraper._extract_download_links(html, "https://example.com/api")
    assert "https://example.com/data.csv" in links
    assert any(link.endswith("/local.json") for link in links)
    assert any(link.endswith("report.xlsx") for link in links)
    assert not any("not-a-data-link" in link for link in links)


def test_extract_download_links_returns_empty_on_no_matches():
    assert ScjnScraper._extract_download_links("<html></html>", "https://x.com") == []


# ---------------------------------------------------------------------------
# _looks_like_search_result
# ---------------------------------------------------------------------------


def test_looks_like_search_result_list_with_judicial_keys():
    data = [{"rubro": "x", "texto": "y"}]
    assert ScjnScraper._looks_like_search_result(data) is True


def test_looks_like_search_result_empty_list_is_false():
    assert ScjnScraper._looks_like_search_result([]) is False


def test_looks_like_search_result_list_without_judicial_keys():
    data = [{"foo": "bar"}]
    assert ScjnScraper._looks_like_search_result(data) is False


def test_looks_like_search_result_dict_with_results_key():
    data = {"results": [{"a": 1}]}
    assert ScjnScraper._looks_like_search_result(data) is True


def test_looks_like_search_result_dict_with_total_count():
    assert ScjnScraper._looks_like_search_result({"total": 100}) is True
    assert ScjnScraper._looks_like_search_result({"totalRegistros": 50}) is True


def test_looks_like_search_result_neither_match():
    assert ScjnScraper._looks_like_search_result({"some_other": "thing"}) is False
    assert ScjnScraper._looks_like_search_result("string") is False


# ---------------------------------------------------------------------------
# _detect_pagination
# ---------------------------------------------------------------------------


def test_detect_pagination_extracts_all_keys():
    data = {"total": 100, "page": 1, "pageSize": 50, "extra": "ignored"}
    out = ScjnScraper._detect_pagination(data)
    assert out["total"] == 100
    assert out["current_page"] == 1
    assert out["page_size"] == 50


def test_detect_pagination_returns_none_for_non_dict():
    assert ScjnScraper._detect_pagination([1, 2, 3]) is None
    assert ScjnScraper._detect_pagination("not a dict") is None


def test_detect_pagination_returns_none_when_empty():
    assert ScjnScraper._detect_pagination({"unrelated": "value"}) is None


def test_detect_pagination_alternative_key_names():
    data = {"totalRegistros": 5, "pagina": 2, "limit": 10}
    out = ScjnScraper._detect_pagination(data)
    assert out["total"] == 5
    assert out["current_page"] == 2
    assert out["page_size"] == 10


# ---------------------------------------------------------------------------
# _extract_items_from_json
# ---------------------------------------------------------------------------


def test_extract_items_from_json_list_passthrough():
    items = [{"id": 1}, {"id": 2}]
    assert ScjnScraper._extract_items_from_json(items) == items


def test_extract_items_from_json_dict_with_results_key():
    data = {"results": [{"id": 1}]}
    assert ScjnScraper._extract_items_from_json(data) == [{"id": 1}]


def test_extract_items_from_json_returns_empty_on_unknown():
    assert ScjnScraper._extract_items_from_json({"unknown": "shape"}) == []
    assert ScjnScraper._extract_items_from_json(None) == []


# ---------------------------------------------------------------------------
# _normalize_tesis
# ---------------------------------------------------------------------------


def test_normalize_tesis_canonical_fields():
    raw = {
        "rubro": "Test thesis",
        "texto": "Body text here",
        "registro": "2029001",
        "tesis": "1a/J. 1/2024",
        "instancia": "Primera Sala",
        "materia": "Civil",
        "precedentes": "Some precedents",
        "url": "https://sjf.scjn.gob.mx/detalle/tesis/2029001",
    }
    out = ScjnScraper._normalize_tesis(raw, "jurisprudencia", 10)
    assert out is not None
    assert out["registro"] == "2029001"
    assert out["tipo"] == "jurisprudencia"
    assert out["epoca"] == 10
    assert out["epoca_nombre"] == EPOCAS[10]
    assert out["rubro"] == "Test thesis"
    assert out["texto"] == "Body text here"
    assert out["instancia"] == "Primera Sala"
    assert out["source"] == "sjf_scjn"


def test_normalize_tesis_alternate_field_names():
    raw = {
        "titulo": "Alt rubro",
        "text": "Alt body",
        "id": "9999",
    }
    out = ScjnScraper._normalize_tesis(raw, "tesis_aislada", 11)
    assert out["rubro"] == "Alt rubro"
    assert out["texto"] == "Alt body"
    assert out["registro"] == "9999"
    # URL synthesized from registro
    assert "9999" in out["url"]


def test_normalize_tesis_returns_none_when_no_rubro_or_registro():
    assert ScjnScraper._normalize_tesis({}, "jurisprudencia", 10) is None
    assert (
        ScjnScraper._normalize_tesis({"texto": "only body"}, "jurisprudencia", 10)
        is None
    )


def test_normalize_tesis_handles_unknown_epoca():
    raw = {"rubro": "Test", "registro": "1"}
    out = ScjnScraper._normalize_tesis(raw, "jurisprudencia", 99)
    assert out["epoca"] == 99
    assert "99" in out["epoca_nombre"]


# ---------------------------------------------------------------------------
# _extract_labeled_text
# ---------------------------------------------------------------------------


def test_extract_labeled_text_by_class_name():
    html = '<div><span class="materia-label">Civil</span></div>'
    soup = BeautifulSoup(html, "html.parser")
    result = ScjnScraper._extract_labeled_text(soup.div, "materia")
    assert result == "Civil"


def test_extract_labeled_text_by_label_with_sibling():
    html = "<div><strong>Instancia:</strong><span>Primera Sala</span></div>"
    soup = BeautifulSoup(html, "html.parser")
    result = ScjnScraper._extract_labeled_text(soup.div, "instancia")
    assert result == "Primera Sala"


def test_extract_labeled_text_via_parent_split():
    html = "<div><span>Materia: Civil</span></div>"
    soup = BeautifulSoup(html, "html.parser")
    result = ScjnScraper._extract_labeled_text(soup.div, "materia")
    assert result == "Civil"


def test_extract_labeled_text_returns_empty_on_no_match():
    soup = BeautifulSoup("<div>nothing</div>", "html.parser")
    assert ScjnScraper._extract_labeled_text(soup.div, "xyz") == ""


# ---------------------------------------------------------------------------
# _parse_tesis_container / _table_row / _dl
# ---------------------------------------------------------------------------


@pytest.fixture
def scraper():
    """A scraper with no real session (for pure-function calls)."""
    s = ScjnScraper.__new__(ScjnScraper)
    s.session = MagicMock()
    s.last_request_time = 0.0
    s._search_endpoint = None
    s._open_data_endpoint = None
    return s


def test_parse_tesis_container_extracts_record(scraper):
    html = """
    <article>
      <h3>RUBRO ABOUT JUDICIAL PRECEDENT</h3>
      <p class="texto">Full body of the thesis.</p>
      <a href="/detalle/tesis/2029001">link</a>
    </article>
    """
    soup = BeautifulSoup(html, "html.parser")
    record = scraper._parse_tesis_container(soup.article, "jurisprudencia", 10)
    assert record is not None
    assert "RUBRO" in record["rubro"]
    assert record["registro"] == "2029001"


def test_parse_tesis_container_returns_none_short_rubro(scraper):
    html = "<article><h3>X</h3></article>"
    soup = BeautifulSoup(html, "html.parser")
    assert scraper._parse_tesis_container(soup.article, "jurisprudencia", 10) is None


def test_parse_tesis_table_row_extracts_record(scraper):
    html = """
    <table><tbody>
      <tr>
        <td>RUBRO TEXT HERE</td>
        <td>Primera Sala</td>
        <td>Civil</td>
        <td>1a/J. 1/2024</td>
        <td>Body text</td>
      </tr>
    </tbody></table>
    """
    soup = BeautifulSoup(html, "html.parser")
    row = soup.find("tr")
    record = scraper._parse_tesis_table_row(row, "jurisprudencia", 10)
    assert record is not None
    assert record["instancia"] == "Primera Sala"
    assert record["texto"] == "Body text"


def test_parse_tesis_table_row_returns_none_too_few_cells(scraper):
    html = "<tr><td>only one</td></tr>"
    soup = BeautifulSoup(html, "html.parser")
    assert scraper._parse_tesis_table_row(soup.tr, "jurisprudencia", 10) is None


def test_parse_tesis_dl_extracts_fields(scraper):
    html = """
    <dl>
      <dt>Rubro:</dt><dd>The rubro</dd>
      <dt>Registro:</dt><dd>2029001</dd>
      <dt>Instancia:</dt><dd>Primera Sala</dd>
    </dl>
    """
    soup = BeautifulSoup(html, "html.parser")
    record = scraper._parse_tesis_dl(soup.dl, "jurisprudencia", 10)
    assert record is not None
    assert record["rubro"] == "The rubro"
    assert record["registro"] == "2029001"
    assert "2029001" in record["url"]


def test_parse_tesis_dl_returns_none_when_no_rubro(scraper):
    html = "<dl><dt>Registro:</dt><dd>1</dd></dl>"
    soup = BeautifulSoup(html, "html.parser")
    assert scraper._parse_tesis_dl(soup.dl, "jurisprudencia", 10) is None


def test_parse_tesis_html_uses_strategy_waterfall(scraper):
    """When containers and tables fail, dl should still be tried."""
    html = """
    <html><body>
      <dl>
        <dt>Rubro:</dt><dd>Found via dl</dd>
      </dl>
    </body></html>
    """
    items = scraper._parse_tesis_html(html, "tesis_aislada", 10)
    assert len(items) == 1
    assert items[0]["rubro"] == "Found via dl"


# ---------------------------------------------------------------------------
# _rate_limit / _get
# ---------------------------------------------------------------------------


def test_rate_limit_sleeps_when_too_fast(scraper):
    """If less than _MIN_REQUEST_INTERVAL has passed, the rate limiter sleeps."""
    import time as time_mod

    scraper.last_request_time = time_mod.time()  # just now
    with patch("apps.scraper.judicial.scjn_scraper.time.sleep") as msleep:
        scraper._rate_limit()
    msleep.assert_called_once()
    assert msleep.call_args.args[0] >= 0


def test_get_returns_response_on_success(scraper):
    fake_resp = MagicMock(status_code=200)
    fake_resp.raise_for_status = MagicMock()
    scraper.session.get.return_value = fake_resp
    with patch.object(scraper, "_rate_limit"):
        out = scraper._get("https://example.com")
    assert out is fake_resp


def test_get_returns_none_on_connection_error(scraper):
    scraper.session.get.side_effect = requests.ConnectionError
    with patch.object(scraper, "_rate_limit"):
        assert scraper._get("https://example.com") is None


def test_get_returns_none_on_timeout(scraper):
    scraper.session.get.side_effect = requests.Timeout
    with patch.object(scraper, "_rate_limit"):
        assert scraper._get("https://example.com") is None


def test_get_returns_none_on_http_error(scraper):
    fake_resp = MagicMock()
    fake_resp.status_code = 500
    err = requests.HTTPError(response=fake_resp)
    fake_resp.raise_for_status.side_effect = err
    scraper.session.get.return_value = fake_resp
    with patch.object(scraper, "_rate_limit"):
        assert scraper._get("https://example.com") is None


def test_get_returns_none_on_request_exception(scraper):
    scraper.session.get.side_effect = requests.RequestException("generic")
    with patch.object(scraper, "_rate_limit"):
        assert scraper._get("https://example.com") is None


# ---------------------------------------------------------------------------
# check_open_data — HTTP-mocked
# ---------------------------------------------------------------------------


def test_check_open_data_finds_json_datasets(scraper):
    fake_resp = MagicMock()
    fake_resp.headers = {"Content-Type": "application/json"}
    fake_resp.json.return_value = {"result": ["jurisprudencia_2024"]}

    with patch.object(scraper, "_get", return_value=fake_resp):
        out = scraper.check_open_data()

    assert out["found"] is True
    assert len(out["datasets"]) > 0
    assert "datos.scjn.gob.mx" in out["endpoint"]


def test_check_open_data_finds_html_download_links(scraper):
    html = '<a href="data.csv">Download</a>'
    fake_resp = MagicMock()
    fake_resp.headers = {"Content-Type": "text/html"}
    fake_resp.text = html

    with patch.object(scraper, "_get", return_value=fake_resp):
        out = scraper.check_open_data()

    assert out["found"] is True
    assert any("data.csv" in u for u in out["download_urls"])


def test_check_open_data_handles_invalid_json(scraper):
    fake_resp = MagicMock()
    fake_resp.headers = {"Content-Type": "application/json"}
    fake_resp.json.side_effect = ValueError

    with patch.object(scraper, "_get", return_value=fake_resp):
        out = scraper.check_open_data()
    assert out["found"] is False


def test_check_open_data_skips_when_get_returns_none(scraper):
    with patch.object(scraper, "_get", return_value=None):
        out = scraper.check_open_data()
    assert out["found"] is False


# ---------------------------------------------------------------------------
# probe_search_api
# ---------------------------------------------------------------------------


def test_probe_search_api_finds_endpoint(scraper):
    fake_resp = MagicMock()
    fake_resp.headers = {"Content-Type": "application/json"}
    fake_resp.json.return_value = [{"rubro": "x", "texto": "y"}]

    with patch.object(scraper, "_get", return_value=fake_resp):
        out = scraper.probe_search_api()

    assert out["found"] is True
    assert out["endpoint"] is not None
    assert scraper._search_endpoint is not None


def test_probe_search_api_falls_through_to_form_inspection(scraper):
    """When no JSON endpoint matches, _inspect_search_form is consulted."""
    with patch.object(scraper, "_get", return_value=None), patch.object(
        scraper, "_inspect_search_form", return_value={"action": "/busqueda"}
    ):
        out = scraper.probe_search_api()
    assert out["search_form"] == {"action": "/busqueda"}


def test_inspect_search_form_finds_action(scraper):
    html = """
    <html><body>
      <form action="/busqueda" method="GET">
        <input name="q" type="text" value=""/>
      </form>
    </body></html>
    """
    fake_resp = MagicMock(text=html)
    with patch.object(scraper, "_get", return_value=fake_resp):
        out = scraper._inspect_search_form()
    assert out is not None
    assert "busqueda" in out["action"]
    assert "q" in out["fields"]


def test_inspect_search_form_returns_none_when_no_match(scraper):
    fake_resp = MagicMock(
        text="<html><body><form action='/login'></form></body></html>"
    )
    with patch.object(scraper, "_get", return_value=fake_resp):
        assert scraper._inspect_search_form() is None


def test_inspect_search_form_returns_none_when_get_fails(scraper):
    with patch.object(scraper, "_get", return_value=None):
        assert scraper._inspect_search_form() is None


# ---------------------------------------------------------------------------
# save_batch
# ---------------------------------------------------------------------------


def test_save_batch_writes_correct_path(tmp_path):
    items = [{"registro": "1", "rubro": "x"}]
    out = ScjnScraper.save_batch(items, str(tmp_path), "jurisprudencia", 5)
    assert out.parent == tmp_path / "judicial" / "jurisprudencia"
    assert out.name == "batch_0005.json"
    assert json.loads(out.read_text(encoding="utf-8")) == items


# ---------------------------------------------------------------------------
# import_bulk_dump / _load_json_dump / _load_csv_dump
# ---------------------------------------------------------------------------


def test_load_json_dump_array(tmp_path):
    path = tmp_path / "dump.json"
    path.write_text(json.dumps([{"a": 1}, {"b": 2}]), encoding="utf-8")
    out = ScjnScraper._load_json_dump(path)
    assert out == [{"a": 1}, {"b": 2}]


def test_load_json_dump_ndjson(tmp_path):
    path = tmp_path / "dump.ndjson"
    path.write_text('{"a":1}\n{"b":2}\n', encoding="utf-8")
    out = ScjnScraper._load_json_dump(path)
    assert {"a": 1} in out and {"b": 2} in out


def test_load_json_dump_skips_invalid_lines(tmp_path):
    path = tmp_path / "dump.ndjson"
    path.write_text('{"a":1}\nnot-json\n{"b":2}\n', encoding="utf-8")
    out = ScjnScraper._load_json_dump(path)
    assert len(out) == 2


def test_load_csv_dump_passthrough(tmp_path):
    path = tmp_path / "dump.csv"
    path.write_text("rubro,registro\nA,1\nB,2\n", encoding="utf-8")
    out = ScjnScraper._load_csv_dump(path)
    assert out == [
        {"rubro": "A", "registro": "1"},
        {"rubro": "B", "registro": "2"},
    ]


def test_import_bulk_dump_json(scraper, tmp_path):
    dump = tmp_path / "dump.json"
    dump.write_text(
        json.dumps(
            [
                {"rubro": "X", "registro": "1", "tipo": "jurisprudencia", "epoca": 10},
                {"rubro": "Y", "registro": "2", "tipo": "tesis_aislada", "epoca": 11},
            ]
        ),
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"
    summary = scraper.import_bulk_dump(str(dump), str(out_dir))

    assert summary["total_items"] == 2
    assert summary["total_batches"] >= 1


def test_import_bulk_dump_csv(scraper, tmp_path):
    dump = tmp_path / "dump.csv"
    dump.write_text(
        "rubro,registro,tipo,epoca\nA,1,jurisprudencia,10\nB,2,tesis_aislada,11\n",
        encoding="utf-8",
    )
    summary = scraper.import_bulk_dump(str(dump), str(tmp_path / "out"))
    assert summary["total_items"] == 2


def test_import_bulk_dump_raises_on_missing_file(scraper, tmp_path):
    with pytest.raises(FileNotFoundError):
        scraper.import_bulk_dump(str(tmp_path / "nope.json"), str(tmp_path))


def test_import_bulk_dump_raises_on_unsupported_format(scraper, tmp_path):
    bad = tmp_path / "dump.xml"
    bad.write_text("<xml/>", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported"):
        scraper.import_bulk_dump(str(bad), str(tmp_path))


def test_import_bulk_dump_handles_invalid_epoca(scraper, tmp_path):
    """Records with non-int epoca default to 10."""
    dump = tmp_path / "dump.json"
    dump.write_text(
        json.dumps([{"rubro": "X", "registro": "1", "epoca": "not-an-int"}]),
        encoding="utf-8",
    )
    summary = scraper.import_bulk_dump(str(dump), str(tmp_path / "out"))
    assert summary["total_items"] == 1


# ---------------------------------------------------------------------------
# run — full pipeline orchestration
# ---------------------------------------------------------------------------


def test_run_short_circuits_when_open_data_found(scraper):
    """When open_data discovery succeeds, run() returns without scraping."""
    with patch.object(
        scraper,
        "check_open_data",
        return_value={
            "found": True,
            "endpoint": "https://datos.scjn.gob.mx/api",
            "datasets": [{"name": "x"}],
            "download_urls": ["https://datos.scjn.gob.mx/data.csv"],
            "probed": [],
        },
    ):
        summary = scraper.run(output_dir="/tmp/x")

    assert summary["open_data"]["found"] is True
    # Did not progress past open_data
    assert summary["jurisprudencia"]["total_items"] == 0


def test_run_proceeds_through_full_pipeline(scraper):
    """When open_data not found, run() probes search and tries each tipo."""
    with patch.object(
        scraper,
        "check_open_data",
        return_value={"found": False, "datasets": [], "download_urls": []},
    ), patch.object(
        scraper,
        "probe_search_api",
        return_value={"found": True, "endpoint": "https://x"},
    ), patch.object(
        scraper, "scrape_jurisprudencia", return_value=iter([])
    ), patch.object(
        scraper, "scrape_tesis_aisladas", return_value=iter([])
    ):
        summary = scraper.run(output_dir="/tmp/x", tipo="all", max_items=10)

    assert summary["search_api"]["found"] is True
    assert summary["jurisprudencia"]["total_items"] == 0
    assert summary["tesis_aisladas"]["total_items"] == 0
