"""Unit tests for the provider-picking logic in SelvaClient.

We don't exercise the network here — the OpenAI SDK's HTTP is mocked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from madfam_budget_gate import new_tracker, require_approval
from madfam_budget_gate.gate import _challenge_string
from meta_harness_madfam.selva_client import (
    PROVIDER_ENDPOINTS,
    SelvaClient,
    _pick_provider_from_env,
)


def _fresh_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in (
        "MADFAM_INFERENCE_PROVIDER",
        "SELVA_API_BASE",
        "SELVA_API_KEY",
        "DEEPINFRA_API_KEY",
        "DEEPINFRA_API_BASE",
    ):
        monkeypatch.delenv(k, raising=False)


def test_pick_provider_raises_without_config(monkeypatch: pytest.MonkeyPatch):
    _fresh_env(monkeypatch)
    with pytest.raises(RuntimeError, match="No inference provider"):
        _pick_provider_from_env()


def test_pick_provider_respects_explicit(monkeypatch: pytest.MonkeyPatch):
    _fresh_env(monkeypatch)
    monkeypatch.setenv("MADFAM_INFERENCE_PROVIDER", "deepinfra")
    assert _pick_provider_from_env() == "deepinfra"
    monkeypatch.setenv("MADFAM_INFERENCE_PROVIDER", "selva")
    assert _pick_provider_from_env() == "selva"


def test_pick_provider_prefers_selva(monkeypatch: pytest.MonkeyPatch):
    _fresh_env(monkeypatch)
    monkeypatch.setenv("SELVA_API_BASE", "https://selva.example/v1")
    monkeypatch.setenv("SELVA_API_KEY", "k1")
    monkeypatch.setenv("DEEPINFRA_API_KEY", "k2")
    assert _pick_provider_from_env() == "selva"


def test_pick_provider_falls_back_to_deepinfra(monkeypatch: pytest.MonkeyPatch):
    _fresh_env(monkeypatch)
    monkeypatch.setenv("DEEPINFRA_API_KEY", "k2")
    assert _pick_provider_from_env() == "deepinfra"


def test_provider_endpoints_cover_both(monkeypatch: pytest.MonkeyPatch):
    assert "selva" in PROVIDER_ENDPOINTS
    assert "deepinfra" in PROVIDER_ENDPOINTS
    # DeepInfra has a default base URL so a bare API key is enough.
    assert PROVIDER_ENDPOINTS["deepinfra"]["default_base_url"]


def _make_client(
    monkeypatch: pytest.MonkeyPatch,
    gate_cfg,
    cheap_estimate,
    provider_env: dict[str, str],
):
    _fresh_env(monkeypatch)
    for k, v in provider_env.items():
        monkeypatch.setenv(k, v)
    challenge = _challenge_string(cheap_estimate, gate_cfg.experiment_id)
    import io

    record = require_approval(
        cheap_estimate,
        gate_cfg,
        input_stream=io.StringIO(challenge + "\n"),
        output_stream=io.StringIO(),
    )
    tracker = new_tracker(record, gate_cfg)

    with patch("meta_harness_madfam.selva_client.OpenAI") as mock_openai_cls:
        client = SelvaClient(
            tracker=tracker,
            pricing=gate_cfg_pricing(),
            experiment_id=gate_cfg.experiment_id,
        )
        return client, mock_openai_cls, tracker


def gate_cfg_pricing():
    # Reload the default pricing table for these end-to-end constructor tests.
    from madfam_budget_gate.cost_model import PricingTable
    return PricingTable.load()


def test_client_constructs_for_deepinfra(monkeypatch, gate_cfg, cheap_estimate):
    client, mock_openai_cls, _ = _make_client(
        monkeypatch,
        gate_cfg,
        cheap_estimate,
        {"DEEPINFRA_API_KEY": "dk-test"},
    )
    assert client.provider == "deepinfra"
    # SDK was constructed with DeepInfra base URL
    args, kwargs = mock_openai_cls.call_args
    assert kwargs["base_url"] == "https://api.deepinfra.com/v1/openai"
    assert kwargs["api_key"] == "dk-test"


def test_client_constructs_for_selva(monkeypatch, gate_cfg, cheap_estimate):
    client, mock_openai_cls, _ = _make_client(
        monkeypatch,
        gate_cfg,
        cheap_estimate,
        {"SELVA_API_BASE": "https://selva.example/v1", "SELVA_API_KEY": "sk-test"},
    )
    assert client.provider == "selva"
    args, kwargs = mock_openai_cls.call_args
    assert kwargs["base_url"] == "https://selva.example/v1"
    assert kwargs["api_key"] == "sk-test"


def test_client_raises_when_nothing_configured(monkeypatch, gate_cfg, cheap_estimate):
    _fresh_env(monkeypatch)
    with pytest.raises(RuntimeError, match="No inference provider"):
        SelvaClient(
            tracker=MagicMock(),
            pricing=gate_cfg_pricing(),
            experiment_id=gate_cfg.experiment_id,
        )
