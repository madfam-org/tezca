"""Metadata tools: get_categories, get_states, get_platform_stats, get_coverage."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from helpers.api_client import fetch_json
from helpers.formatters import format_categories, format_coverage, format_states, format_stats


def register_metadata_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_categories() -> str:
        """Get all legal categories with law counts.

        Returns:
            List of categories (civil, penal, fiscal, laboral, etc.) with counts.
        """
        data = await fetch_json("/categories/")
        return format_categories(data)

    @mcp.tool()
    async def get_states() -> str:
        """Get all 32 Mexican states that have indexed laws.

        Returns:
            List of state names (use these exact names when filtering by state).
        """
        data = await fetch_json("/states/")
        return format_states(data)

    @mcp.tool()
    async def get_platform_stats() -> str:
        """Get dashboard-level platform statistics.

        Returns:
            Total laws, articles, coverage percentages, and recent additions.
        """
        data = await fetch_json("/stats/")
        return format_stats(data)

    @mcp.tool()
    async def get_coverage() -> str:
        """Get detailed coverage statistics by legal tier.

        Returns:
            Per-tier breakdown: federal laws, reglamentos, NOMs, state legislative,
            state non-legislative, municipal, treaties, judicial.
        """
        data = await fetch_json("/coverage/")
        return format_coverage(data)
