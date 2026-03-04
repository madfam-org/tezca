# Tezca MCP Server — Mexican Law for AI Agents

MCP (Model Context Protocol) server that gives AI agents direct access to **35,000+ Mexican laws** and **3.5M+ indexed articles** covering federal, state, and municipal legislation, plus SCJN judicial records.

Built on [FastMCP](https://github.com/modelcontextprotocol/python-sdk) with Streamable HTTP transport.

## Quick Start

```bash
# Install and run
cd packages/mcp-server
uv sync
uv run main.py          # Starts on :8000

# Health check
curl http://localhost:8000/health

# Inspect with MCP Inspector
npx @modelcontextprotocol/inspector --http-url http://localhost:8000/mcp
```

### Docker

```bash
cd packages/mcp-server
docker compose up
# Server at http://localhost:8001
```

## 16 Tools

### Search & Discovery
| Tool | Description |
|------|-------------|
| `search_laws` | Full-text search across 3.5M articles. Primary entry point. |
| `search_within_law` | Search within a single law's articles |
| `suggest_laws` | Autocomplete law names to find law IDs |

### Law Detail
| Tool | Description |
|------|-------------|
| `get_law_detail` | Full metadata, versions, status for a law |
| `get_law_articles` | Paginated article text |
| `get_law_structure` | Hierarchical TOC (Book > Title > Chapter) |
| `list_laws` | Browse/filter the 35K+ law catalog |

### Cross-References
| Tool | Description |
|------|-------------|
| `get_related_laws` | Thematically similar laws |
| `get_cross_references` | Citation network (law-level stats or article-level links) |

### Judicial Records (SCJN)
| Tool | Description |
|------|-------------|
| `search_judicial` | Search jurisprudencia + tesis aisladas |
| `get_judicial_detail` | Full text of a judicial record |
| `get_judicial_stats` | Corpus breakdown by tipo/materia/época |

### Metadata
| Tool | Description |
|------|-------------|
| `get_categories` | Legal category taxonomy with counts |
| `get_states` | All 32 Mexican states |
| `get_platform_stats` | Dashboard overview |
| `get_coverage` | Detailed tier-by-tier coverage stats |

## 3 Resources

| URI | Content |
|-----|---------|
| `tezca://taxonomy` | Mexican legal hierarchy: tiers, types, categories |
| `tezca://domains` | Domain→category mapping |
| `tezca://states` | All 32 states with canonical names |

## 3 Prompt Templates

| Prompt | Purpose |
|--------|---------|
| `research_mexican_law` | Step-by-step legal research workflow |
| `compare_state_laws` | Cross-state regulatory comparison |
| `trace_legal_authority` | Citation chain + judicial interpretation |

## Client Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tezca": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.tezca.mx/mcp"]
    }
  }
}
```

### Cursor / VS Code

Add to MCP settings:

```json
{
  "mcpServers": {
    "tezca": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.tezca.mx/mcp"]
    }
  }
}
```

### Local (via uvx)

```bash
pip install tezca-mcp
tezca-mcp
```

Or with uv:

```bash
uvx tezca-mcp
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEZCA_API_URL` | `http://localhost:8000/api/v1` | Tezca REST API base URL |
| `MCP_HOST` | `0.0.0.0` | Server bind host |
| `MCP_PORT` | `8000` | Server bind port |
| `LOG_LEVEL` | `INFO` | Logging level |

## Development

```bash
# Install with dev deps
uv sync --all-extras

# Run tests
uv run pytest tests/ -v

# Run integration tests (against live API)
TEZCA_API_URL=https://tezca.mx/api/v1 uv run pytest tests/test_integration.py -v

# Lint
uv run ruff check .
```

## Architecture

```
Client (Claude/Cursor/etc.)
    ↓ MCP (Streamable HTTP)
Tezca MCP Server (FastMCP + uvicorn)
    ↓ httpx (async)
Tezca REST API (tezca.mx/api/v1)
    ↓
Elasticsearch (3.5M articles) + PostgreSQL (35K laws)
```

The MCP server is a thin proxy — it calls the Tezca REST API via httpx and formats responses for LLM consumption. No direct database access.

## License

AGPL-3.0 — see [LICENSE](LICENSE).
