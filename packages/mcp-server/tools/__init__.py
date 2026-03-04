from tools.judicial import register_judicial_tools
from tools.laws import register_law_tools
from tools.metadata import register_metadata_tools
from tools.references import register_reference_tools
from tools.search import register_search_tools


def register_all(mcp):
    """Register all tool groups with the MCP server."""
    register_search_tools(mcp)
    register_law_tools(mcp)
    register_reference_tools(mcp)
    register_judicial_tools(mcp)
    register_metadata_tools(mcp)
