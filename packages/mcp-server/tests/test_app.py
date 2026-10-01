"""The ASGI app that `main.py` serves: it must import and route.

No other test imports `main`, so an incompatible Starlette/MCP upgrade (such as
Starlette 1.0 removing `@app.route`) used to pass the suite and only fail at
container start.
"""

from __future__ import annotations

from starlette.testclient import TestClient

import main


def test_health_endpoint():
    client = TestClient(main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "tezca-mcp"}


def test_streamable_http_endpoint_is_mounted():
    paths = {getattr(route, "path", None) for route in main.app.routes}

    assert "/mcp" in paths
    assert "/health" in paths
