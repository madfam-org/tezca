"""Async HTTP client for the Tezca REST API."""

from __future__ import annotations

import httpx

from helpers.config import TEZCA_API_URL

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Get or create the shared httpx async client."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=TEZCA_API_URL,
            timeout=30.0,
            headers={"Accept": "application/json"},
        )
    return _client


async def close_client() -> None:
    """Close the shared client."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        _client = None


async def fetch_json(path: str, params: dict | None = None) -> dict | list:
    """Fetch JSON from a Tezca API endpoint.

    Args:
        path: API path (e.g. "/search/").
        params: Query parameters. None values are stripped.

    Returns:
        Parsed JSON response.

    Raises:
        httpx.HTTPStatusError: On 4xx/5xx responses.
    """
    client = get_client()
    cleaned = {k: v for k, v in (params or {}).items() if v is not None}
    resp = await client.get(path, params=cleaned)
    resp.raise_for_status()
    return resp.json()
