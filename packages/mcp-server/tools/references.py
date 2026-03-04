"""Cross-reference tools: get_related_laws, get_cross_references."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from helpers.api_client import fetch_json
from helpers.formatters import format_cross_references, format_related_laws


def register_reference_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_related_laws(law_id: str) -> str:
        """Find thematically similar laws using semantic similarity.

        Args:
            law_id: Law identifier (e.g. "amparo"). Use suggest_laws to find IDs.

        Returns:
            Up to 8 related laws with similarity scores.
        """
        data = await fetch_json(f"/laws/{law_id}/related/")
        return format_related_laws(data)

    @mcp.tool()
    async def get_cross_references(law_id: str, article_id: str | None = None) -> str:
        """Get citation network for a law or specific article.

        Without article_id: returns aggregated statistics (total outgoing/incoming,
        most referenced and most citing laws).

        With article_id: returns specific outgoing and incoming cross-references
        with exact article targets and source text.

        Args:
            law_id: Law identifier. Use suggest_laws to find IDs.
            article_id: Optional article number (e.g. "1", "27 Bis"). If provided,
                returns article-level references instead of law-level stats.

        Returns:
            Cross-reference statistics or detailed citation links.
        """
        if article_id:
            path = f"/laws/{law_id}/articles/{article_id}/references/"
        else:
            path = f"/laws/{law_id}/references/"
        data = await fetch_json(path)
        return format_cross_references(data)
