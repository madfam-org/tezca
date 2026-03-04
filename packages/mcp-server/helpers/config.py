"""Environment configuration for Tezca MCP server."""

import os

TEZCA_API_URL = os.getenv("TEZCA_API_URL", "http://localhost:8000/api/v1").rstrip("/")
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
