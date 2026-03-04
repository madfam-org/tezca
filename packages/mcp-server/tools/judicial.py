"""Judicial tools: search_judicial, get_judicial_detail, get_judicial_stats."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from helpers.api_client import fetch_json
from helpers.formatters import format_judicial_detail, format_judicial_results, format_judicial_stats


def register_judicial_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    async def search_judicial(
        query: str,
        tipo: str | None = None,
        materia: str | None = None,
        epoca: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> str:
        """Search SCJN judicial records (jurisprudencia and tesis aisladas).

        Args:
            query: Search terms in Spanish (searches rubro + full text).
            tipo: "jurisprudencia" (binding precedent) or "tesis_aislada" (isolated thesis).
            materia: Subject — "civil", "penal", "administrativa", "laboral",
                "constitucional", "comun".
            epoca: Judicial epoch (e.g. "11a", "10a").
            page: Page number.
            page_size: Results per page (1-100, default 20).

        Returns:
            Judicial records with registro number, type, subject, and ruling summary.
        """
        params = {
            "q": query,
            "page": page,
            "page_size": min(page_size, 100),
        }
        if tipo:
            params["tipo"] = tipo
        if materia:
            params["materia"] = materia
        if epoca:
            params["epoca"] = epoca

        data = await fetch_json("/judicial/search/", params)
        return format_judicial_results(data)

    @mcp.tool()
    async def get_judicial_detail(registro: str) -> str:
        """Get the full text and metadata of a judicial record.

        Args:
            registro: The registro number (e.g. "2028741"). Found in search results.

        Returns:
            Complete judicial record: rubro, texto, precedentes, ponente, etc.
        """
        data = await fetch_json(f"/judicial/{registro}/")
        return format_judicial_detail(data)

    @mcp.tool()
    async def get_judicial_stats() -> str:
        """Get statistics about the judicial record corpus.

        Returns:
            Total records, breakdown by tipo (jurisprudencia/tesis_aislada),
            by materia (civil/penal/etc.), and by época.
        """
        data = await fetch_json("/judicial/stats/")
        return format_judicial_stats(data)
