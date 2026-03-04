"""Tezca MCP Server — Mexican law for AI agents.

Exposes 35K+ Mexican laws and 3.5M+ articles via the Model Context Protocol.
Proxies the Tezca REST API (tezca.mx/api/v1) through 16 tools, 3 resources,
and 3 prompt templates.
"""

from __future__ import annotations

import logging

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from helpers.config import LOG_LEVEL, MCP_HOST, MCP_PORT
from prompts import register_prompts
from resources import register_resources
from tools import register_all

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger("tezca-mcp")

mcp = FastMCP(
    "Tezca — Mexican Law",
    instructions=(
        "Tezca provides access to 35,000+ Mexican laws and 3.5M+ indexed articles "
        "covering federal, state, and municipal legislation, plus judicial records "
        "(jurisprudencia and tesis aisladas from the SCJN). "
        "All law content is in Spanish. Search queries work best in Spanish. "
        "Use suggest_laws to find a law's ID, then get_law_detail/get_law_articles "
        "for content. Use search_laws for full-text search across all articles."
    ),
)

register_all(mcp)
register_resources(mcp)
register_prompts(mcp)

app = mcp.streamable_http_app()


@app.route("/health")
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "tezca-mcp"})


def main():
    logger.info("Starting Tezca MCP server on %s:%s", MCP_HOST, MCP_PORT)
    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    main()
