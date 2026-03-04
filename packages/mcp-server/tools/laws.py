"""Law detail tools: get_law_detail, get_law_articles, get_law_structure, list_laws."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from helpers.api_client import fetch_json
from helpers.formatters import format_articles, format_law_detail, format_law_list, format_structure


def register_law_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_law_detail(law_id: str) -> str:
        """Get full metadata for a specific law including versions and status.

        Args:
            law_id: Law identifier (e.g. "amparo", "codigo_civil_federal",
                "jalisco_codigo_civil"). Use suggest_laws to find IDs.

        Returns:
            Law name, category, tier, status, article count, version history.
        """
        data = await fetch_json(f"/laws/{law_id}/")
        return format_law_detail(data)

    @mcp.tool()
    async def get_law_articles(law_id: str, page: int = 1, page_size: int = 50) -> str:
        """Get the actual text of a law's articles.

        Args:
            law_id: Law identifier. Use suggest_laws to find IDs.
            page: Page number (starts at 1).
            page_size: Articles per page (1-1000, default 50). Use smaller values
                for large laws to avoid overwhelming context.

        Returns:
            Article texts with their identifiers (Art. 1, Art. 2, etc.).
        """
        data = await fetch_json(
            f"/laws/{law_id}/articles/",
            {"page": page, "page_size": min(page_size, 1000)},
        )
        return format_articles(data)

    @mcp.tool()
    async def get_law_structure(law_id: str) -> str:
        """Get the hierarchical table of contents for a law (Book > Title > Chapter).

        Args:
            law_id: Law identifier. Use suggest_laws to find IDs.

        Returns:
            Tree structure showing how the law is organized.
        """
        data = await fetch_json(f"/laws/{law_id}/structure/")
        return format_structure(data)

    @mcp.tool()
    async def list_laws(
        tier: str | None = None,
        state: str | None = None,
        category: str | None = None,
        status: str | None = None,
        law_type: str = "all",
        domain: str | None = None,
        sort: str = "name_asc",
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """Browse and filter the catalog of 35,000+ Mexican laws.

        Args:
            tier: "federal", "state", or "municipal".
            state: State name (e.g. "Jalisco", "Ciudad de México").
            category: Legal category — "civil", "penal", "fiscal", etc.
            status: "vigente" (active) or "abrogado" (repealed).
            law_type: "legislative" or "non_legislative", or "all".
            domain: Shorthand — "finance", "criminal", "labor", "civil",
                "administrative", "constitutional".
            sort: "name_asc", "name_desc", "date_desc", "date_asc", "article_count".
            page: Page number.
            page_size: Results per page (1-200, default 50).

        Returns:
            Paginated list of laws with basic metadata.
        """
        params = {
            "page": page,
            "page_size": min(page_size, 200),
            "sort": sort,
        }
        if tier:
            params["tier"] = tier
        if state:
            params["state"] = state
        if category:
            params["category"] = category
        if status:
            params["status"] = status
        if law_type != "all":
            params["law_type"] = law_type
        if domain:
            params["domain"] = domain

        data = await fetch_json("/laws/", params)
        return format_law_list(data)
