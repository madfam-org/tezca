"""Tests for search tools."""

from __future__ import annotations

import httpx

from tests.conftest import SEARCH_RESPONSE, SEARCH_WITHIN_RESPONSE, SUGGEST_RESPONSE
from tools.search import register_search_tools


async def test_search_laws(mock_api):
    mock_api.get("/search/").mock(return_value=httpx.Response(200, json=SEARCH_RESPONSE))

    from helpers.api_client import fetch_json
    from helpers.formatters import format_search_results

    data = await fetch_json("/search/", {"q": "amparo", "page": 1, "page_size": 10})
    result = format_search_results(data)

    assert "Ley de Amparo" in result
    assert "Art. 1" in result
    assert "1 results" in result


async def test_search_laws_empty(mock_api):
    mock_api.get("/search/").mock(
        return_value=httpx.Response(200, json={"results": [], "total": 0, "page": 1, "total_pages": 0})
    )

    from helpers.api_client import fetch_json
    from helpers.formatters import format_search_results

    data = await fetch_json("/search/", {"q": "nonexistent"})
    result = format_search_results(data)

    assert "No results" in result


async def test_search_within_law(mock_api):
    mock_api.get("/laws/amparo/search/").mock(
        return_value=httpx.Response(200, json=SEARCH_WITHIN_RESPONSE)
    )

    from helpers.api_client import fetch_json
    from helpers.formatters import format_search_within_law

    data = await fetch_json("/laws/amparo/search/", {"q": "suspensión"})
    result = format_search_within_law(data)

    assert "Art. 128" in result
    assert "suspensión" in result


async def test_suggest_laws(mock_api):
    mock_api.get("/suggest/").mock(return_value=httpx.Response(200, json=SUGGEST_RESPONSE))

    from helpers.api_client import fetch_json
    from helpers.formatters import format_suggestions

    data = await fetch_json("/suggest/", {"q": "amparo"})
    result = format_suggestions(data)

    assert "Ley de Amparo" in result
    assert "amparo" in result
