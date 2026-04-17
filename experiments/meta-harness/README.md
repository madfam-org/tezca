# Meta-Harness — MADFAM integration layer

**Status:** Phase 0 spike (infra only, not yet applied to tezca data).
**Upstream:** [stanford-iris-lab/meta-harness](https://github.com/stanford-iris-lab/meta-harness)
([paper](https://arxiv.org/abs/2603.28052), Apr 2026).
**Location:** `tezca/experiments/meta-harness/` — colocated with Phase 1 pilot, but the library is repo-agnostic and can be lifted out later.

This directory hosts the MADFAM integration layer for Meta-Harness. It does
**not** vendor the upstream code — `scripts/bootstrap.sh` clones it into
`./upstream/`. What lives here is:

- A **HITL budget gate** that blocks any spend-incurring run until a human
  types an explicit per-run approval challenge.
- A **cost model** that computes worst-case USD from a run shape and a
  versioned model-pricing table.
- A **Selva-routed LLM client** so all spend is metered by the centralized
  inference proxy, not billed against per-experiment vendor keys.
- A **gated runner CLI** — the only blessed way to kick off a run.

Everything here is deliberately conservative. If the gate and cost model
disagree, the gate wins; if the estimate and reality diverge, the mid-run
tracker kills the process. These can be relaxed later once we have real
telemetry from live pilots.

---

## Why the gate exists

The Meta-Harness paper's Terminal-Bench-2 reference experiment **costs about
$500 per iteration** on Opus 4.6. Even the cheapest text-classification
setup can rack up double-digit dollars on a runaway loop. Until we have
enough telemetry to trust the framework's cost behavior on our data, every
run is preceded by a one-sentence cost summary and a typed approval
challenge. No silent spending.

The gate enforces three things:

1. **Pre-run cap.** An env-defined `MADFAM_BUDGET_HARD_CAP_USD` is the
   absolute ceiling. Estimates above it are refused outright — the approver
   must consciously raise it to proceed.
2. **Per-run challenge.** The approver types a challenge string that is
   deterministically derived from the estimate. If the estimate changes, the
   challenge changes. No copy-paste habituation.
3. **Mid-run kill.** Every Selva call updates an in-process spend tracker.
   If actual spend exceeds `approved_cap × GRACE_FACTOR` (default 1.10), the
   tracker raises `BudgetExceededError` on the next call and signals the
   main thread.

Approval records are append-only JSON under `./approvals/`. Per-call spend
logs are JSONL under `./logs/`. Both are gitignored.

---

## Quick start

```bash
cd tezca/experiments/meta-harness
bash scripts/bootstrap.sh          # clones upstream, sets up .venv
cp .env.example .env               # fill SELVA_API_KEY, MADFAM_EXPERIMENT_OWNER
source .venv/bin/activate
make test                          # gate + cost-model tests
make estimate                      # show worst-case cost for default scenario
make run                           # GATED. Will ask for typed approval.
```

### What approval looks like

```
=== META-HARNESS BUDGET GATE ===
experiment       : tezca-spike
owner            : aldo
model            : openrouter/openai/gpt-oss-120b
iterations       : 1
candidates/iter  : 5
eval set size    : 100
input tok total  : 2,000,000
output tok total : 250,000
inner-loop cost  : $0.28
WORST-CASE TOTAL : $0.28
hard cap (env)   : $10.00
mid-run kill at  : $0.31 (1.10x approved cost)

To approve, type the following challenge verbatim:
  approve-tezca-spike-0p28usd-a4c91b22
Anything else will cancel.
>
```

The challenge string encodes `experiment_id`, model, iterations, candidates,
eval-set size, and the dollar amount. Changing any of those produces a
different challenge.

---

## Scenarios — quick cost reference

Worst-case cost estimates for common run shapes. Verify against
`config/model_pricing.yaml` before using.

| Scenario | model | iters × cand × items | toks/call in+out | est. USD |
|----------|-------|---------------------|-------------------|----------|
| Smoke text-classification | `openrouter/openai/gpt-oss-120b` | 1×2×5 | 1k+0.2k | ~$0.00 |
| Phase 0 spike | `openrouter/openai/gpt-oss-120b` | 1×5×100 | 4k+0.5k | ~$0.28 |
| Phase 1 tezca pilot (per iter) | `claude-haiku-4-5` | 1×5×100 | 4k+0.5k | ~$3.25 |
| Phase 1 tezca full sweep | `claude-haiku-4-5` | 10×5×100 | 4k+0.5k | ~$32.50 |
| Phase 3 phyne-crm draft eval | `claude-sonnet-4-6` | 1×5×100 | 6k+1k | ~$16.50 |
| Paper TB2 reference (per iter) | `claude-opus-4-7` | 1×2×89 | ~100k+20k | ~$535 |

Regenerate any row with `make estimate MODEL=... ITERATIONS=... CANDIDATES=...`.

---

## How a gated run flows

```
  operator
    │  make run MODEL=... ITERATIONS=...
    ▼
  runner.py (CLI)
    │  1. build RunShape from args
    │  2. load pricing table
    │  3. compute CostEstimate
    │  4. require_approval() — prints summary, reads stdin, writes audit
    │  5. new_tracker() — mid-run kill installed
    │  6. import and call the user's entrypoint(client, tracker, run_shape)
    ▼
  user entrypoint (e.g., wrapped upstream meta_harness.py)
    │  all LLM calls go through SelvaClient
    │  every call records tokens + USD in tracker
    │  tracker raises if cap breached → entrypoint exits cleanly
    ▼
  runner.py prints final snapshot + exits
```

---

## Writing an entrypoint

An entrypoint is any Python callable of the form:

```python
def run(*, client, tracker, run_shape):
    # client : meta_harness_madfam.selva_client.SelvaClient
    # tracker: meta_harness_madfam.budget_gate.SpendTracker
    # run_shape: meta_harness_madfam.cost_model.RunShape
    ...
    return {"held_out_f1": 0.87}  # any JSON-serializable result, or None
```

`client.chat(model=..., messages=...)` will automatically attribute cost to
the tracker. If the cap is breached, the next call raises
`BudgetExceededError`.

For the upstream text-classification reference example, the entrypoint will
be a small adapter that invokes `upstream/reference_examples/text_classification/meta_harness.py`
with monkey-patched LLM calls routed through the Selva client. That adapter
is Phase 1 work and is **not** in this spike.

---

## Tests

```
make test
```

15 tests covering:
- Challenge string stability and per-estimate uniqueness.
- Happy-path approval writes a valid audit record.
- Rejected / empty input cancels and writes nothing.
- Over-hard-cap estimates are refused regardless of input.
- `GateConfig.from_env` rejects missing owner, missing cap, wild grace factor.
- Spend tracker accumulates correctly and writes JSONL.
- Mid-run spend over the kill threshold raises `BudgetExceededError` and
  becomes sticky (next call also raises).
- Cost model: basic math, proposer addition, unknown-model fallback, zero case.

---

## Non-goals for Phase 0

- Not wiring to real tezca data (that's Phase 1).
- Not replacing the upstream repo — we import it.
- Not doing org-level spend tracking across multiple simultaneous
  experiments (single-process tracker for now).
- Not handling streaming completions (the gate sees totals via usage, so
  partial streams would under-attribute cost until Phase 2).
- Not trying to cancel in-flight requests on cap breach — the provider has
  already charged for the current call. The goal is to stop the NEXT call.

---

## Files

```
pyproject.toml                       — uv-compatible, Python 3.11+
Makefile                             — bootstrap / estimate / run / test
scripts/bootstrap.sh                 — clone upstream, create venv
config/model_pricing.yaml            — USD/Mtok table; verify monthly
.env.example                         — SELVA_*, MADFAM_* required vars
src/meta_harness_madfam/
    cost_model.py                    — RunShape, CostEstimate, PricingTable
    budget_gate.py                   — GateConfig, require_approval, SpendTracker
    selva_client.py                  — OpenAI SDK pointed at Selva /v1
    runner.py                        — gated CLI (estimate, run)
tests/
    test_cost_model.py               — 4 tests
    test_budget_gate.py              — 11 tests
    conftest.py                      — pricing + gate fixtures
approvals/                           — audit records (gitignored)
logs/                                — JSONL per-call spend logs (gitignored)
upstream/                            — cloned by bootstrap (gitignored)
```

---

## Phase roadmap (from the adoption plan)

- **Phase 0 (THIS)** — infra + HITL gate + Selva wiring. Verify upstream
  `text_classification` reference runs via our runner.
- **Phase 1** — tezca article categorization. 300 search / 100 val / 100
  held-out split. Success gate: ≥3pp F1 lift, ≤2pp per-label regression.
- **Phase 2** — dhanam transaction auto-categorization. Target ≥20%
  reduction in manual recategorizations.
- **Phase 3** — phyne-crm first-touch email. Offline reply-rate lift ≥15%
  before any live A/B.
- **Phase 4** — autoswarm agent scaffolds. Conditional on 1–3 wins.

Each phase's entrypoint will land under `src/meta_harness_madfam/entrypoints/`.
