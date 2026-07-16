"""Tests for ``apps.scraper.judicial.sjf_api`` (fix for issue #142).

Covers the SJF tesis microservice client: list-body construction, HTML
stripping, API-document-to-record mapping, and the requests-based client
itself. No network calls — ``SjfApiClient`` is always constructed with a
``MagicMock`` session, and ``session.post``/``session.get`` return
``MagicMock`` responses with ``.status_code``/``.json()``/``.text`` stubbed.

The client rate-limits via ``time.monotonic()`` (up to ~1s sleep per call);
the ``apps.scraper.judicial.sjf_api.time`` module is patched throughout so
tests run instantly.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.scraper.judicial.sjf_api import (
    EPOCA_API_LABELS,
    SJF_API_TESIS,
    SJF_PUBLIC_DETAIL_URL,
    TIPO_API_LABELS,
    SjfApiClient,
    SjfApiError,
    build_list_body,
    doc_to_record,
    strip_html,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_time():
    """Neutralize the module's rate-limit sleeping across every test."""
    with patch("apps.scraper.judicial.sjf_api.time") as mock_time:
        mock_time.monotonic.return_value = 0.0
        yield mock_time


def _response(status_code: int = 200, json_body=None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    if json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.json.side_effect = ValueError("no JSON object could be decoded")
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# EPOCAS / TIPO label maps
# ---------------------------------------------------------------------------


def test_epoca_api_labels_cover_1_through_12():
    assert set(EPOCA_API_LABELS.keys()) == set(range(1, 13))
    assert EPOCA_API_LABELS[12] == "Duodécima Época"
    assert EPOCA_API_LABELS[1] == "Primera Época"


def test_tipo_api_labels_cover_jurisprudencia_and_tesis_aislada():
    assert TIPO_API_LABELS["jurisprudencia"] == "Jurisprudencia"
    assert TIPO_API_LABELS["tesis_aislada"] == "Aislada"


# ---------------------------------------------------------------------------
# build_list_body
# ---------------------------------------------------------------------------


def test_build_list_body_happy_path_jurisprudencia():
    body = build_list_body(11, "jurisprudencia")
    assert body["idApp"] == "SJFAPP2020"
    assert body["searchTerms"] == []
    assert body["bFacet"] is False
    assert body["ius"] == []
    assert body["filterExpression"] == ""

    classifiers = {c["name"]: c["value"] for c in body["classifiers"]}
    assert classifiers["epoca"] == ["Undécima Época"]
    assert classifiers["tipoTesis"] == ["Jurisprudencia"]
    assert classifiers["tipoDocumento"] == ["1"]


def test_build_list_body_happy_path_tesis_aislada():
    body = build_list_body(10, "tesis_aislada")
    classifiers = {c["name"]: c["value"] for c in body["classifiers"]}
    assert classifiers["epoca"] == ["Décima Época"]
    assert classifiers["tipoTesis"] == ["Aislada"]


@pytest.mark.parametrize("epoca", [0, 13, -1, 100])
def test_build_list_body_unknown_epoca_raises(epoca):
    with pytest.raises(SjfApiError, match="Unknown época"):
        build_list_body(epoca, "jurisprudencia")


def test_build_list_body_unknown_tipo_raises():
    with pytest.raises(SjfApiError, match="Unknown tipo"):
        build_list_body(11, "not_a_real_tipo")


def test_build_list_body_all_epocas_produce_a_body():
    for epoca in EPOCA_API_LABELS:
        body = build_list_body(epoca, "jurisprudencia")
        classifiers = {c["name"]: c["value"] for c in body["classifiers"]}
        assert classifiers["epoca"] == [EPOCA_API_LABELS[epoca]]


# ---------------------------------------------------------------------------
# strip_html
# ---------------------------------------------------------------------------


def test_strip_html_removes_tags():
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_unescapes_entities():
    assert strip_html("Tom &amp; Jerry &lt;3") == "Tom & Jerry <3"


def test_strip_html_strips_surrounding_whitespace():
    assert strip_html("  <div> padded </div>  ") == "padded"


def test_strip_html_none_is_safe():
    assert strip_html(None) == ""


def test_strip_html_empty_string_is_safe():
    assert strip_html("") == ""


def test_strip_html_plain_text_passthrough():
    assert strip_html("No tags here") == "No tags here"


# ---------------------------------------------------------------------------
# doc_to_record
# ---------------------------------------------------------------------------


def test_doc_to_record_maps_full_document():
    doc = {
        "ius": "2031846",
        "rubro": "<b>RUBRO TEXT</b>",
        "texto": "<p>Body &amp; text</p>",
        "precedentes": "<i>Precedente</i>",
        "claveTesis": "P./J. 1/2024",
        "materias": "Civil",
        "instanciaAbr": "Pleno",
        "fuente": "Semanario Judicial",
        "fechaPublicacion": "2024-05-01T00:00:00.000Z",
        "semanal": True,
    }
    rec = doc_to_record(doc, 11, "Undecima Epoca", "jurisprudencia")

    assert rec["registro"] == "2031846"
    assert rec["tipo"] == "jurisprudencia"
    assert rec["epoca"] == 11
    assert rec["epoca_nombre"] == "Undecima Epoca"
    assert rec["instancia"] == "Pleno"
    assert rec["materia"] == "Civil"
    assert rec["tesis_num"] == "P./J. 1/2024"
    assert rec["rubro"] == "RUBRO TEXT"
    assert rec["texto"] == "Body & text"
    assert rec["precedentes"] == "Precedente"
    assert rec["url"] == f"{SJF_PUBLIC_DETAIL_URL}/2031846"
    assert rec["source"] == "sjf_scjn_api"
    assert rec["fuente"] == "Semanario Judicial"
    assert rec["fecha_publicacion"] == "2024-05-01"
    assert rec["semanal"] is True


def test_doc_to_record_falls_back_to_id_when_ius_missing():
    doc = {"id": "999", "rubro": "X"}
    rec = doc_to_record(doc, 10, "Decima Epoca", "jurisprudencia")
    assert rec["registro"] == "999"
    assert rec["url"] == f"{SJF_PUBLIC_DETAIL_URL}/999"


def test_doc_to_record_falls_back_to_sala_for_instancia():
    doc = {"ius": "1", "sala": "Primera Sala"}
    rec = doc_to_record(doc, 10, "Decima Epoca", "jurisprudencia")
    assert rec["instancia"] == "Primera Sala"


def test_doc_to_record_empty_registro_yields_empty_url():
    doc = {}
    rec = doc_to_record(doc, 10, "Decima Epoca", "jurisprudencia")
    assert rec["registro"] == ""
    assert rec["url"] == ""


def test_doc_to_record_missing_fecha_publicacion_is_none():
    doc = {"ius": "1"}
    rec = doc_to_record(doc, 10, "Decima Epoca", "jurisprudencia")
    assert rec["fecha_publicacion"] is None


def test_doc_to_record_blank_fecha_publicacion_is_none():
    doc = {"ius": "1", "fechaPublicacion": ""}
    rec = doc_to_record(doc, 10, "Decima Epoca", "jurisprudencia")
    assert rec["fecha_publicacion"] is None


def test_doc_to_record_fecha_publicacion_truncated_to_date_part():
    doc = {"ius": "1", "fechaPublicacion": "2023-11-30T12:34:56.000Z"}
    rec = doc_to_record(doc, 10, "Decima Epoca", "jurisprudencia")
    assert rec["fecha_publicacion"] == "2023-11-30"


def test_doc_to_record_semanal_defaults_false():
    doc = {"ius": "1"}
    rec = doc_to_record(doc, 10, "Decima Epoca", "jurisprudencia")
    assert rec["semanal"] is False


def test_doc_to_record_tesis_aislada_tipo_preserved():
    doc = {"ius": "1"}
    rec = doc_to_record(doc, 10, "Decima Epoca", "tesis_aislada")
    assert rec["tipo"] == "tesis_aislada"


# ---------------------------------------------------------------------------
# SjfApiClient.list_tesis
# ---------------------------------------------------------------------------


def test_list_tesis_happy_path_returns_documents_total_and_pages():
    session = MagicMock()
    session.post.return_value = _response(
        200,
        json_body={
            "documents": [{"ius": "1"}, {"ius": "2"}],
            "total": 45,
            "totalPage": 5,
        },
    )
    client = SjfApiClient(session=session)

    docs, total, total_pages = client.list_tesis(11, "jurisprudencia", page=0, size=10)

    assert docs == [{"ius": "1"}, {"ius": "2"}]
    assert total == 45
    assert total_pages == 5
    session.post.assert_called_once()
    call_kwargs = session.post.call_args
    assert call_kwargs.args[0] == SJF_API_TESIS
    assert call_kwargs.kwargs["params"] == {"page": 0, "size": 10}
    assert "classifiers" in call_kwargs.kwargs["json"]


def test_list_tesis_defaults_to_jurisprudencia_page0_size50():
    session = MagicMock()
    session.post.return_value = _response(
        200, json_body={"documents": [], "total": 0, "totalPage": 0}
    )
    client = SjfApiClient(session=session)
    client.list_tesis(11)
    call_kwargs = session.post.call_args
    assert call_kwargs.kwargs["params"] == {"page": 0, "size": 50}


def test_list_tesis_missing_documents_key_returns_empty_list():
    session = MagicMock()
    session.post.return_value = _response(200, json_body={"total": 0, "totalPage": 0})
    client = SjfApiClient(session=session)
    docs, total, total_pages = client.list_tesis(11)
    assert docs == []
    assert total == 0
    assert total_pages == 0


def test_list_tesis_non_200_raises_sjf_api_error():
    session = MagicMock()
    session.post.return_value = _response(500, text="Internal Server Error")
    client = SjfApiClient(session=session)
    with pytest.raises(SjfApiError, match="HTTP 500"):
        client.list_tesis(11)


def test_list_tesis_non_json_body_raises_sjf_api_error():
    session = MagicMock()
    session.post.return_value = _response(200, json_body=None, text="not json")
    client = SjfApiClient(session=session)
    with pytest.raises(SjfApiError, match="non-JSON body"):
        client.list_tesis(11)


def test_list_tesis_unknown_epoca_raises_before_any_request():
    session = MagicMock()
    client = SjfApiClient(session=session)
    with pytest.raises(SjfApiError, match="Unknown época"):
        client.list_tesis(999)
    session.post.assert_not_called()


# ---------------------------------------------------------------------------
# SjfApiClient.fetch_detail
# ---------------------------------------------------------------------------


def test_fetch_detail_happy_path_gets_with_is_semanal_true():
    session = MagicMock()
    session.get.return_value = _response(
        200, json_body={"ius": "2031846", "texto": "Full text"}
    )
    client = SjfApiClient(session=session)

    detail = client.fetch_detail("2031846", semanal=True)

    assert detail == {"ius": "2031846", "texto": "Full text"}
    session.get.assert_called_once()
    call_kwargs = session.get.call_args
    assert call_kwargs.args[0] == f"{SJF_API_TESIS}/2031846"
    assert call_kwargs.kwargs["params"]["isSemanal"] == "true"


def test_fetch_detail_semanal_false_sets_is_semanal_false():
    session = MagicMock()
    session.get.return_value = _response(200, json_body={})
    client = SjfApiClient(session=session)
    client.fetch_detail("1", semanal=False)
    call_kwargs = session.get.call_args
    assert call_kwargs.kwargs["params"]["isSemanal"] == "false"


def test_fetch_detail_includes_hostname_param():
    session = MagicMock()
    session.get.return_value = _response(200, json_body={})
    client = SjfApiClient(session=session)
    client.fetch_detail("1")
    call_kwargs = session.get.call_args
    assert "hostName" in call_kwargs.kwargs["params"]


def test_fetch_detail_non_200_raises_sjf_api_error():
    session = MagicMock()
    session.get.return_value = _response(404, text="Not Found")
    client = SjfApiClient(session=session)
    with pytest.raises(SjfApiError, match="HTTP 404"):
        client.fetch_detail("1")


def test_fetch_detail_non_json_body_raises_sjf_api_error():
    session = MagicMock()
    session.get.return_value = _response(200, json_body=None, text="oops")
    client = SjfApiClient(session=session)
    with pytest.raises(SjfApiError, match="non-JSON body"):
        client.fetch_detail("1")


# ---------------------------------------------------------------------------
# SjfApiClient — session setup / rate limiting
# ---------------------------------------------------------------------------


def test_client_sets_browser_shaped_headers_on_session():
    session = MagicMock()
    SjfApiClient(session=session)
    session.headers.update.assert_called_once()
    headers = session.headers.update.call_args.args[0]
    assert "User-Agent" in headers
    assert headers["Origin"] == "https://sjf2.scjn.gob.mx"
    assert "Referer" in headers


def test_client_defaults_to_new_requests_session_when_none_given():
    client = SjfApiClient()
    assert client._session is not None


def test_rate_limit_sleeps_when_called_in_quick_succession(_patch_time):
    session = MagicMock()
    session.post.return_value = _response(
        200, json_body={"documents": [], "total": 0, "totalPage": 0}
    )
    client = SjfApiClient(session=session)

    # _rate_limit() calls time.monotonic() twice per request: once to
    # compute elapsed-since-last-call, once to stamp _last_request_ts after
    # the (possible) sleep. First call: elapsed vs the initial 0.0 timestamp
    # is 0.0 (< the 1s floor) so it sleeps; second call: elapsed since the
    # first call's post-sleep stamp is still 0.0, so it sleeps again too.
    _patch_time.monotonic.side_effect = [0.0, 0.0, 0.1, 0.1]
    client.list_tesis(11)
    client.list_tesis(11)

    assert _patch_time.sleep.called


def test_rate_limit_does_not_sleep_when_interval_elapsed(_patch_time):
    session = MagicMock()
    session.post.return_value = _response(
        200, json_body={"documents": [], "total": 0, "totalPage": 0}
    )
    client = SjfApiClient(session=session)

    # First call: elapsed since init (ts=0.0) is 0.0 → sleeps once and
    # stamps _last_request_ts at 5.0. Second call: elapsed since 5.0 is
    # also >= the 1s floor (10.0 - 5.0), so no further sleep.
    _patch_time.monotonic.side_effect = [0.0, 5.0, 10.0, 10.0]
    client.list_tesis(11)
    client.list_tesis(11)

    _patch_time.sleep.assert_called_once()
