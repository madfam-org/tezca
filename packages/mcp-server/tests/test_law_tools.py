"""Tests for law detail tools."""

from __future__ import annotations

import httpx

from tests.conftest import (
    LAW_ARTICLES_RESPONSE,
    LAW_DETAIL_RESPONSE,
    LAW_LIST_RESPONSE,
    STRUCTURE_RESPONSE,
)


async def test_get_law_detail(mock_api):
    mock_api.get("/laws/amparo/").mock(return_value=httpx.Response(200, json=LAW_DETAIL_RESPONSE))

    from helpers.api_client import fetch_json
    from helpers.formatters import format_law_detail

    data = await fetch_json("/laws/amparo/")
    result = format_law_detail(data)

    assert "Ley de Amparo" in result
    assert "constitucional" in result
    assert "vigente" in result
    assert "271" in result


async def test_get_law_articles(mock_api):
    mock_api.get("/laws/amparo/articles/").mock(
        return_value=httpx.Response(200, json=LAW_ARTICLES_RESPONSE)
    )

    from helpers.api_client import fetch_json
    from helpers.formatters import format_articles

    data = await fetch_json("/laws/amparo/articles/", {"page": 1, "page_size": 500})
    result = format_articles(data)

    assert "Art. 1" in result
    assert "Art. 2" in result
    assert "El juicio de amparo" in result


async def test_get_law_structure(mock_api):
    mock_api.get("/laws/amparo/structure/").mock(
        return_value=httpx.Response(200, json=STRUCTURE_RESPONSE)
    )

    from helpers.api_client import fetch_json
    from helpers.formatters import format_structure

    data = await fetch_json("/laws/amparo/structure/")
    result = format_structure(data)

    assert "Título Primero" in result
    assert "Capítulo I" in result
    assert "Capítulo II" in result


async def test_list_laws(mock_api):
    mock_api.get("/laws/").mock(return_value=httpx.Response(200, json=LAW_LIST_RESPONSE))

    from helpers.api_client import fetch_json
    from helpers.formatters import format_law_list

    data = await fetch_json("/laws/", {"page": 1, "page_size": 50})
    result = format_law_list(data)

    assert "Ley de Amparo" in result
    assert "Código Civil Federal" in result
    assert "2 laws" in result
