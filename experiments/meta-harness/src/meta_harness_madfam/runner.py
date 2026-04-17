"""Gated CLI for running Meta-Harness experiments.

Two subcommands:

    estimate  - print the worst-case cost for a run shape, no approval asked.
    run       - ask for approval, then exec a wrapped inner-loop function.

The ``run`` subcommand is the only blessed way to spend tokens in this repo.
It will refuse to proceed until a human types the challenge string, and it
installs a mid-run kill that fires if actual spend exceeds the approved cap
times ``MADFAM_BUDGET_GRACE_FACTOR``.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

from madfam_budget_gate import (
    BudgetDenied,
    CostEstimate,
    GateConfig,
    PricingTable,
    RunShape,
    estimate,
    install_sigusr1_tripwire,
    new_tracker,
    require_approval,
)

from .selva_client import SelvaClient


def _build_run_shape(args: argparse.Namespace) -> RunShape:
    return RunShape(
        model=args.model,
        iterations=args.iterations,
        candidates_per_iteration=args.candidates,
        eval_set_size=args.eval_set_size,
        input_tokens_per_eval=args.input_tokens_per_eval,
        output_tokens_per_eval=args.output_tokens_per_eval,
        proposer_model=args.proposer_model,
        proposer_input_tokens=args.proposer_input_tokens or 0,
        proposer_output_tokens=args.proposer_output_tokens or 0,
    )


def _add_shape_args(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--model", required=True, help="Inner-loop model id as routed by Selva.")
    sp.add_argument("--iterations", type=int, required=True)
    sp.add_argument("--candidates", type=int, required=True, help="Candidates per iteration.")
    sp.add_argument("--eval-set-size", type=int, required=True)
    sp.add_argument(
        "--input-tokens-per-eval",
        type=int,
        required=True,
        help="Worst-case prompt tokens for ONE eval call.",
    )
    sp.add_argument(
        "--output-tokens-per-eval",
        type=int,
        required=True,
        help="Worst-case completion tokens for ONE eval call.",
    )
    sp.add_argument("--proposer-model", default=None)
    sp.add_argument("--proposer-input-tokens", type=int, default=0)
    sp.add_argument("--proposer-output-tokens", type=int, default=0)


def _print_estimate(est: CostEstimate) -> None:
    for line in est.summary_lines():
        print(line)


def cmd_estimate(args: argparse.Namespace) -> int:
    pricing = PricingTable.load(Path(args.pricing) if args.pricing else None)
    shape = _build_run_shape(args)
    est = estimate(shape, pricing)
    if args.json:
        print(json.dumps({"run": asdict(shape), "estimate": asdict(est)}, indent=2))
    else:
        _print_estimate(est)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    cfg = GateConfig.from_env()
    pricing = PricingTable.load(Path(args.pricing) if args.pricing else None)
    shape = _build_run_shape(args)
    est = estimate(shape, pricing)

    try:
        approval = require_approval(est, cfg)
    except BudgetDenied as exc:
        print(f"\n[denied] {exc}", file=sys.stderr)
        return 2

    tracker = new_tracker(approval, cfg)
    install_sigusr1_tripwire(tracker)
    client = SelvaClient(
        tracker=tracker, pricing=pricing, experiment_id=cfg.experiment_id
    )

    # Resolve and call the user-provided inner-loop entrypoint.
    # Convention: a Python callable "module.path:function_name" that accepts
    # (client, tracker, run_shape) and returns a JSON-serializable result dict.
    if ":" not in args.entrypoint:
        print(
            "[denied] --entrypoint must be 'module.path:function_name'",
            file=sys.stderr,
        )
        return 2
    mod_path, func_name = args.entrypoint.split(":", 1)
    try:
        module = importlib.import_module(mod_path)
    except ImportError as exc:
        print(f"[denied] could not import entrypoint module: {exc}", file=sys.stderr)
        return 2
    fn = getattr(module, func_name, None)
    if fn is None or not callable(fn):
        print(
            f"[denied] entrypoint {args.entrypoint} is not callable",
            file=sys.stderr,
        )
        return 2

    print(f"\n[gate] approval recorded, invoking entrypoint: {args.entrypoint}\n")
    try:
        result = fn(client=client, tracker=tracker, run_shape=shape)
    except Exception as exc:  # noqa: BLE001 — user code must not bypass audit
        snap = tracker.snapshot()
        print(
            f"\n[error] entrypoint raised: {type(exc).__name__}: {exc}\n"
            f"[spend] {json.dumps(snap)}",
            file=sys.stderr,
        )
        return 1

    snap = tracker.snapshot()
    print("\n[done] entrypoint returned.")
    print(f"[spend] {json.dumps(snap)}")
    if result is not None:
        print(f"[result] {json.dumps(result, default=str)[:2000]}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="meta-harness-madfam")
    parser.add_argument("--pricing", default=None, help="Path to pricing YAML.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sp_est = sub.add_parser("estimate", help="Print worst-case cost estimate.")
    _add_shape_args(sp_est)
    sp_est.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    sp_est.set_defaults(func=cmd_estimate)

    sp_run = sub.add_parser("run", help="Ask for HITL approval, then run an entrypoint.")
    _add_shape_args(sp_run)
    sp_run.add_argument(
        "--entrypoint",
        required=True,
        help="'module.path:function_name' — called with (client, tracker, run_shape).",
    )
    sp_run.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
