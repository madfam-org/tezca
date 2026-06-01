# Meta-Harness MADFAM integration — operator entry points.
#
# The `run` target is the only blessed way to spend tokens. It calls the
# gated CLI, which refuses to start without an explicit typed approval.

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Default smoke-estimate scenario: cheapest practical path.
MODEL ?= openrouter/openai/gpt-oss-120b
ITERATIONS ?= 1
CANDIDATES ?= 5
EVAL_SET_SIZE ?= 100
INPUT_TOK ?= 4000
OUTPUT_TOK ?= 500
ENTRYPOINT ?= meta_harness_madfam.examples.smoke:run

.PHONY: help
help:
	@echo "Targets:"
	@echo "  bootstrap     - clone upstream, create .venv, install deps"
	@echo "  test          - run gate + cost-model tests"
	@echo "  estimate      - print worst-case \$\$ for default scenario (no spend)"
	@echo "  run           - gated run (asks for approval, then executes ENTRYPOINT)"
	@echo "  lint          - ruff"
	@echo "  clean         - remove .venv, upstream/, cached artifacts"

.PHONY: bootstrap
bootstrap:
	bash scripts/bootstrap.sh

.PHONY: test
test: $(PY)
	PYTHONPATH=src $(PY) -m pytest tests/ -q

.PHONY: lint
lint: $(PY)
	$(PY) -m ruff check src tests

.PHONY: estimate
estimate: $(PY)
	PYTHONPATH=src $(PY) -m meta_harness_madfam.runner estimate \
	    --model $(MODEL) \
	    --iterations $(ITERATIONS) \
	    --candidates $(CANDIDATES) \
	    --eval-set-size $(EVAL_SET_SIZE) \
	    --input-tokens-per-eval $(INPUT_TOK) \
	    --output-tokens-per-eval $(OUTPUT_TOK)

.PHONY: run
run: $(PY)
	@set -a; [ -f .env ] && . ./.env; set +a; \
	 PYTHONPATH=src $(PY) -m meta_harness_madfam.runner run \
	    --model $(MODEL) \
	    --iterations $(ITERATIONS) \
	    --candidates $(CANDIDATES) \
	    --eval-set-size $(EVAL_SET_SIZE) \
	    --input-tokens-per-eval $(INPUT_TOK) \
	    --output-tokens-per-eval $(OUTPUT_TOK) \
	    --entrypoint $(ENTRYPOINT)

.PHONY: clean
clean:
	@node ../../scripts/require-local-destructive.mjs
	rm -rf $(VENV) upstream .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -exec rm -rf {} +

$(PY):
	@echo "Run 'make bootstrap' first." >&2
	@exit 1
