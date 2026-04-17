#!/usr/bin/env bash
# Bootstrap the Meta-Harness experiment environment.
#
# 1. Clone the upstream reference repo (pinned by tag/commit) into ./upstream.
# 2. Set up a local venv and install this integration layer in editable mode.
# 3. Leave the user a note about what to do next.
#
# Safe to re-run: clones are skipped if the dir exists; uv sync is idempotent.

set -euo pipefail
cd "$(dirname "$0")/.."

UPSTREAM_REPO="https://github.com/stanford-iris-lab/meta-harness.git"
# Pin a specific commit once we've vetted one. For the spike we track main.
UPSTREAM_REF="${UPSTREAM_REF:-main}"

if [ ! -d upstream ]; then
    echo "[bootstrap] cloning meta-harness into ./upstream ..."
    git clone "$UPSTREAM_REPO" upstream
else
    echo "[bootstrap] upstream/ already exists, skipping clone"
fi

(
    cd upstream
    git fetch origin
    git checkout "$UPSTREAM_REF"
)

if [ ! -d .venv ]; then
    echo "[bootstrap] creating .venv ..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -e '.[dev]'

echo ""
echo "[bootstrap] done."
echo ""
echo "Next steps:"
echo "  1. cp .env.example .env   # then fill SELVA_API_KEY + MADFAM_EXPERIMENT_OWNER"
echo "  2. source .venv/bin/activate"
echo "  3. make estimate           # dry-run worst-case cost with default scenario"
echo "  4. make test               # verify gate tests pass"
echo ""
echo "DO NOT run any upstream script directly. Use 'make run' (gated) instead."
