"""Search & discovery tools: search_laws, search_within_law, suggest_laws."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from helpers.api_client import fetch_json
from helpers.formatters import format_search_results, format_search_within_law, format_suggestions


def register_search_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    async def search_laws(
        query: str,
        jurisdiction: str = "all",
        category: str | None = None,
        state: str | None = None,
        status: str = "all",
        law_type: str = "all",
        domain: str | None = None,
        date_range: str = "all",
        sort: str = "relevance",
        page: int = 1,
        page_size: int = 10,
    ) -> str:
        """Search across 3.5M+ Mexican law articles. Primary entry point for legal research.

        Args:
            query: Search terms. Use Spanish for best results (e.g. "derecho de amparo").
            jurisdiction: Filter by tier — "federal", "state", "municipal", or "all".
                Comma-separated for multiple (e.g. "federal,state").
            category: Legal category slug — "civil", "penal", "fiscal", "laboral",
                "mercantil", "administrativo", "constitucional". Comma-separated OK.
            state: Mexican state name (e.g. "Jalisco", "Ciudad de México").
            status: Law status — "vigente" (active) or "abrogada" (repealed), or "all".
            law_type: "legislative" or "non_legislative" (reglamentos, NOMs), or "all".
            domain: Shorthand grouping — "finance" (fiscal+mercantil), "criminal" (penal),
                "labor", "civil", "administrative", "constitutional".
            date_range: "this_year", "last_year", "last_5_years", "older", or "all".
            sort: "relevance", "date_desc", "date_asc", or "name".
            page: Page number (starts at 1).
            page_size: Results per page (1-100, default 10).

        Returns:
            Formatted search results with article snippets, law names, and facets.
        """
        params = {
            "q": query,
            "page": page,
            "page_size": min(page_size, 100),
            "sort": sort,
        }
        if jurisdiction != "all":
            params["jurisdiction"] = jurisdiction
        if category:
            params["category"] = category
        if state:
            params["state"] = state
        if status != "all":
            params["status"] = status
        if law_type != "all":
            params["law_type"] = law_type
        if domain:
            params["domain"] = domain
        if date_range != "all":
            params["date_range"] = date_range

        data = await fetch_json("/search/", params)
        return format_search_results(data)

    @mcp.tool()
    async def search_within_law(law_id: str, query: str) -> str:
        """Search within a specific law's articles.

        Args:
            law_id: Law identifier (e.g. "amparo", "codigo_penal_federal",
                "jalisco_codigo_civil"). Use suggest_laws to find IDs.
            query: Search terms in Spanish.

        Returns:
            Matching articles with highlighted snippets.
        """
        data = await fetch_json(f"/laws/{law_id}/search/", {"q": query})
        return format_search_within_law(data)

    @mcp.tool()
    async def suggest_laws(query: str) -> str:
        """Autocomplete law names to find law IDs. Use before get_law_detail.

        Args:
            query: Partial law name (min 2 chars). Spanish works best
                (e.g. "amparo", "código civil", "ley general").

        Returns:
            Up to 8 law name suggestions with their IDs and tiers.
        """
        data = await fetch_json("/suggest/", {"q": query})
        return format_suggestions(data)
