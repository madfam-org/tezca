"""Tests for judicial tools."""

from __future__ import annotations

import httpx

from tests.conftest import JUDICIAL_DETAIL_RESPONSE, JUDICIAL_SEARCH_RESPONSE, JUDICIAL_STATS_RESPONSE


async def test_search_judicial(mock_api):
    mock_api.get("/judicial/search/").mock(
        return_value=httpx.Response(200, json=JUDICIAL_SEARCH_RESPONSE)
    )

    from helpers.api_client import fetch_json
    from helpers.formatters import format_judicial_results

    data = await fetch_json("/judicial/search/", {"q": "amparo"})
    result = format_judicial_results(data)

    assert "2028741" in result
    assert "jurisprudencia" in result
    assert "COSA JUZGADA" in result


async def test_get_judicial_detail(mock_api):
    mock_api.get("/judicial/2028741/").mock(
        return_value=httpx.Response(200, json=JUDICIAL_DETAIL_RESPONSE)
    )

    from helpers.api_client import fetch_json
    from helpers.formatters import format_judicial_detail

    data = await fetch_json("/judicial/2028741/")
    result = format_judicial_detail(data)

    assert "COSA JUZGADA" in result
    assert "La cosa juzgada es la autoridad" in result
    assert "Contradicción de tesis" in result
    assert "Primera Sala" in result


async def test_get_judicial_stats(mock_api):
    mock_api.get("/judicial/stats/").mock(
        return_value=httpx.Response(200, json=JUDICIAL_STATS_RESPONSE)
    )

    from helpers.api_client import fetch_json
    from helpers.formatters import format_judicial_stats

    data = await fetch_json("/judicial/stats/")
    result = format_judicial_stats(data)

    assert "5123" in result
    assert "jurisprudencia" in result
    assert "civil" in result
