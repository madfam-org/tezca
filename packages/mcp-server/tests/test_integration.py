"""Integration tests that hit the live Tezca API.

Skipped by default. Run with:
    TEZCA_API_URL=https://tezca.mx/api/v1 uv run pytest tests/test_integration.py -v
"""

from __future__ import annotations

import os

import pytest

from helpers.api_client import fetch_json
from helpers.formatters import (
    format_categories,
    format_coverage,
    format_judicial_results,
    format_law_detail,
    format_search_results,
    format_states,
    format_stats,
    format_suggestions,
)

LIVE = os.getenv("TEZCA_API_URL", "").startswith("https://")
pytestmark = pytest.mark.skipif(not LIVE, reason="Live API tests — set TEZCA_API_URL to https://...")


async def test_live_search():
    data = await fetch_json("/search/", {"q": "amparo", "page_size": 3})
    result = format_search_results(data)
    assert "results" in result.lower() or "found" in result.lower()


async def test_live_suggest():
    data = await fetch_json("/suggest/", {"q": "código civil"})
    result = format_suggestions(data)
    assert "civil" in result.lower()


async def test_live_law_detail():
    data = await fetch_json("/laws/amparo/")
    result = format_law_detail(data)
    assert "Amparo" in result


async def test_live_stats():
    data = await fetch_json("/stats/")
    result = format_stats(data)
    assert "Total laws" in result


async def test_live_categories():
    data = await fetch_json("/categories/")
    result = format_categories(data)
    assert "civil" in result.lower()


async def test_live_states():
    data = await fetch_json("/states/")
    result = format_states(data)
    assert "Jalisco" in result


async def test_live_coverage():
    data = await fetch_json("/coverage/")
    result = format_coverage(data)
    assert "Coverage" in result


async def test_live_judicial_search():
    data = await fetch_json("/judicial/search/", {"q": "amparo", "page_size": 3})
    result = format_judicial_results(data)
    assert len(result) > 0
