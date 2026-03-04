"""Tests for metadata tools."""

from __future__ import annotations

import httpx

from tests.conftest import CATEGORIES_RESPONSE, COVERAGE_RESPONSE, STATES_RESPONSE, STATS_RESPONSE


async def test_get_categories(mock_api):
    mock_api.get("/categories/").mock(return_value=httpx.Response(200, json=CATEGORIES_RESPONSE))

    from helpers.api_client import fetch_json
    from helpers.formatters import format_categories

    data = await fetch_json("/categories/")
    result = format_categories(data)

    assert "Derecho Civil" in result
    assert "Derecho Penal" in result
    assert "1200" in result


async def test_get_states(mock_api):
    mock_api.get("/states/").mock(return_value=httpx.Response(200, json=STATES_RESPONSE))

    from helpers.api_client import fetch_json
    from helpers.formatters import format_states

    data = await fetch_json("/states/")
    result = format_states(data)

    assert "Aguascalientes" in result
    assert "Jalisco" in result


async def test_get_platform_stats(mock_api):
    mock_api.get("/stats/").mock(return_value=httpx.Response(200, json=STATS_RESPONSE))

    from helpers.api_client import fetch_json
    from helpers.formatters import format_stats

    data = await fetch_json("/stats/")
    result = format_stats(data)

    assert "23,322" in result
    assert "917,443" in result
    assert "98.5%" in result


async def test_get_coverage(mock_api):
    mock_api.get("/coverage/").mock(return_value=httpx.Response(200, json=COVERAGE_RESPONSE))

    from helpers.api_client import fetch_json
    from helpers.formatters import format_coverage

    data = await fetch_json("/coverage/")
    result = format_coverage(data)

    assert "Federal laws" in result
    assert "98.5%" in result
