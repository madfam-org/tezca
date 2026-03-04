"""Tests for the API client helper."""

from __future__ import annotations

import httpx
import pytest
import respx

from helpers.api_client import fetch_json
from helpers.config import TEZCA_API_URL


@pytest.fixture()
def mock_api():
    with respx.mock(base_url=TEZCA_API_URL, assert_all_called=False) as router:
        yield router


async def test_fetch_json_success(mock_api):
    mock_api.get("/stats/").mock(return_value=httpx.Response(200, json={"total_laws": 100}))

    result = await fetch_json("/stats/")
    assert result == {"total_laws": 100}


async def test_fetch_json_strips_none_params(mock_api):
    route = mock_api.get("/search/").mock(
        return_value=httpx.Response(200, json={"results": [], "total": 0})
    )

    await fetch_json("/search/", {"q": "test", "state": None, "category": None})

    request = route.calls[0].request
    assert "state" not in str(request.url)
    assert "category" not in str(request.url)
    assert "q=test" in str(request.url)


async def test_fetch_json_raises_on_error(mock_api):
    mock_api.get("/laws/nonexistent/").mock(return_value=httpx.Response(404, json={"detail": "Not found"}))

    with pytest.raises(httpx.HTTPStatusError):
        await fetch_json("/laws/nonexistent/")
