FROM python:3.12-slim

# Audit 2026-04-23 (cross-cutting I.1): create an unprivileged runtime user
# so Kyverno pod-security policies don't need an exception and any escape
# from the MCP server process can't write outside /app.
RUN groupadd -r mcp --gid 10001 && useradd -r -g mcp --uid 10001 -m -d /home/mcp mcp

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Dependencies come from uv.lock, the file tests/test_dependency_floors.py
# checks. `--locked` fails the build if uv.lock is stale against
# pyproject.toml. `--no-install-project` keeps this layer cached across code
# edits; the project itself needs README.md and the sources, copied below.
# (Before 2026-10-01 this step copied only pyproject.toml: it ignored the lock
# and failed with "Readme file does not exist: README.md".)
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
RUN uv sync --locked --no-dev && chown -R mcp:mcp /app

USER mcp

EXPOSE 8000

# --no-sync: run the environment built above; never re-resolve at start.
CMD ["uv", "run", "--no-sync", "main.py"]
