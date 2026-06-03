"""LLM client with per-call cost attribution.

Every Meta-Harness LLM call goes through here. That guarantees two things:
    1. All spend is metered centrally (Selva when available, direct
       vendor metering as a bridge fallback).
    2. All spend is checked against the in-process SpendTracker, so a runaway
       loop trips the kill switch even if upstream metering lags.

Two modes:
    - ``selva`` (default, preferred): routes to Selva's OpenAI-compat /v1
      proxy. Honors org-config, fallbacks, and org-level observability.
      See ``project_inference_centralization`` memory.
    - ``deepinfra``: direct bridge mode used while Anthropic credits are
      paused and Selva's DeepInfra secret isn't yet deployed in prod. Cost
      is still attributed to the in-process tracker and HITL gate still
      applies. See ``selva-office/docs/runbooks/BRIDGE_DEEPINFRA.md``.

Mode is picked by env var (``MADFAM_INFERENCE_PROVIDER``) or the ``provider``
constructor argument. When unset, prefers ``selva`` if ``SELVA_*`` env vars
are present, else falls back to ``deepinfra`` if ``DEEPINFRA_API_KEY`` is set,
else raises.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from openai import OpenAI

from madfam_budget_gate import ModelPrice, PricingTable, SpendTracker

Provider = Literal["selva", "deepinfra"]

PROVIDER_ENDPOINTS: dict[Provider, dict[str, str]] = {
    "selva": {
        "base_url_env": "SELVA_API_BASE",
        "api_key_env": "SELVA_API_KEY",
        "default_base_url": "",  # no default — must be explicit
    },
    "deepinfra": {
        "base_url_env": "DEEPINFRA_API_BASE",
        "api_key_env": "DEEPINFRA_API_KEY",
        "default_base_url": "https://api.deepinfra.com/v1/openai",
    },
}


def _pick_provider_from_env() -> Provider:
    """Choose a provider based on what env vars are populated.

    Explicit override wins; otherwise prefer Selva, fall back to DeepInfra.
    """
    explicit = os.environ.get("MADFAM_INFERENCE_PROVIDER", "").strip().lower()
    if explicit in ("selva", "deepinfra"):
        return explicit  # type: ignore[return-value]
    if os.environ.get("SELVA_API_BASE") and os.environ.get("SELVA_API_KEY"):
        return "selva"
    if os.environ.get("DEEPINFRA_API_KEY"):
        return "deepinfra"
    raise RuntimeError(
        "No inference provider configured. Set MADFAM_INFERENCE_PROVIDER=selva|deepinfra "
        "or populate the matching env vars "
        "(SELVA_API_BASE+SELVA_API_KEY, or DEEPINFRA_API_KEY)."
    )


@dataclass
class ChatResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    usd: float
    raw: Any


class SelvaClient:
    """Thin wrapper around the OpenAI SDK, routed to Selva or DeepInfra.

    Every call:
        - adds ``extra_headers`` tagging the experiment,
        - reads usage from the response,
        - computes USD cost from the local pricing table,
        - records that cost against the tracker (which may raise if over cap).
    """

    def __init__(
        self,
        *,
        tracker: SpendTracker,
        pricing: PricingTable,
        experiment_id: str,
        provider: Provider | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
        timeout_s: float = 120.0,
    ) -> None:
        resolved_provider: Provider = provider or _pick_provider_from_env()
        cfg = PROVIDER_ENDPOINTS[resolved_provider]
        base = api_base or os.environ.get(cfg["base_url_env"]) or cfg["default_base_url"]
        key = api_key or os.environ.get(cfg["api_key_env"])
        if not base:
            raise RuntimeError(
                f"No base URL for provider {resolved_provider!r}: set "
                f"{cfg['base_url_env']} or pass api_base=..."
            )
        if not key:
            raise RuntimeError(
                f"No API key for provider {resolved_provider!r}: set "
                f"{cfg['api_key_env']} or pass api_key=..."
            )
        self._provider: Provider = resolved_provider
        self._client = OpenAI(base_url=base, api_key=key, timeout=timeout_s)
        self._tracker = tracker
        self._pricing = pricing
        self._experiment_id = experiment_id

    @property
    def provider(self) -> Provider:
        return self._provider

    def _price(self, model: str) -> ModelPrice:
        return self._pricing.price_for(model)

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        tag: str | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """One chat completion. Raises BudgetExceededError if over cap."""
        # Fail fast if a prior call already tripped the kill.
        self._tracker.assert_not_killed()

        extra_headers = kwargs.pop("extra_headers", {}) or {}
        extra_headers.setdefault("x-madfam-experiment", self._experiment_id)
        extra_headers.setdefault("x-madfam-provider", self._provider)
        if tag:
            extra_headers.setdefault("x-madfam-tag", tag)

        resp = self._client.chat.completions.create(
            model=model,
            messages=messages,
            extra_headers=extra_headers,
            **kwargs,
        )

        usage = resp.usage
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        price = self._price(model)
        usd = (
            input_tokens * price.input_usd_per_mtok / 1_000_000.0
            + output_tokens * price.output_usd_per_mtok / 1_000_000.0
        )

        # This can raise BudgetExceededError — that's intended. The call
        # already cost what it cost; the point is to block the NEXT call.
        self._tracker.record_usage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            usd=usd,
            tag=tag,
        )

        content = resp.choices[0].message.content or ""
        return ChatResult(
            text=content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            usd=usd,
            raw=resp,
        )
