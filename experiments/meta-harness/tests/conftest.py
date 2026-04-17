"""Shared fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from madfam_budget_gate import GateConfig
from madfam_budget_gate.cost_model import (
    CostEstimate,
    ModelPrice,
    PricingTable,
    RunShape,
    estimate,
)


@pytest.fixture
def tiny_pricing(tmp_path: Path) -> PricingTable:
    yaml_body = """
models:
  tiny-model:
    input_usd_per_mtok: 1.0
    output_usd_per_mtok: 2.0
    vendor: test
  bigger-model:
    input_usd_per_mtok: 10.0
    output_usd_per_mtok: 30.0
    vendor: test
unknown_model_fallback:
  input_usd_per_mtok: 100.0
  output_usd_per_mtok: 300.0
  vendor: unknown
"""
    path = tmp_path / "pricing.yaml"
    path.write_text(yaml_body)
    return PricingTable.load(path)


@pytest.fixture
def gate_cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GateConfig:
    monkeypatch.setenv("MADFAM_BUDGET_HARD_CAP_USD", "50.00")
    monkeypatch.setenv("MADFAM_BUDGET_GRACE_FACTOR", "1.10")
    monkeypatch.setenv("MADFAM_EXPERIMENT_ID", "test-exp")
    monkeypatch.setenv("MADFAM_EXPERIMENT_OWNER", "test-owner")
    monkeypatch.setenv("MADFAM_APPROVALS_DIR", str(tmp_path / "approvals"))
    monkeypatch.setenv("MADFAM_LOGS_DIR", str(tmp_path / "logs"))
    return GateConfig.from_env()


@pytest.fixture
def cheap_estimate(tiny_pricing: PricingTable) -> CostEstimate:
    """An estimate that's well under the default $50 hard cap."""
    return estimate(
        RunShape(
            model="tiny-model",
            iterations=1,
            candidates_per_iteration=2,
            eval_set_size=5,
            input_tokens_per_eval=1000,
            output_tokens_per_eval=200,
        ),
        tiny_pricing,
    )


@pytest.fixture
def over_cap_estimate(tiny_pricing: PricingTable) -> CostEstimate:
    """An estimate that blows past a $50 hard cap."""
    return estimate(
        RunShape(
            model="bigger-model",
            iterations=10,
            candidates_per_iteration=10,
            eval_set_size=100,
            input_tokens_per_eval=5000,
            output_tokens_per_eval=2000,
        ),
        tiny_pricing,
    )
