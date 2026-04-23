FROM python:3.12-slim

# Audit 2026-04-23 (cross-cutting I.1): create an unprivileged runtime user
# so Kyverno pod-security policies don't need an exception and any escape
# from the MCP server process can't write outside /app.
RUN groupadd -r mcp --gid 10001 && useradd -r -g mcp --uid 10001 -m -d /home/mcp mcp

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
RUN uv sync --no-dev

COPY . .
RUN chown -R mcp:mcp /app

USER mcp

EXPOSE 8000

CMD ["uv", "run", "main.py"]
