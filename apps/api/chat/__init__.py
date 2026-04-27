"""
First-party AI assistant ("Pregunta a Tezca") — Track 2 of
FEATURE_PARITY_PLAN_2026-04-27 §3.1.

Architecture (per the plan's strict constraint contract):
- Tezca never holds an OpenAI/Anthropic API key.
- Every LLM call routes through Selva (`agents-api.madfam.io/v1`,
  OpenAI-compatible) per the MADFAM ECOSYSTEM convention.
- LLM costs are billed via Dhanam metered agent-hours, not per Tezca tier.

Tezca-side responsibilities:
1. Retrieve relevant article snippets via ES + cross-references.
2. Build the system prompt with the corpus snippets.
3. Forward to Selva and stream/return the response.
4. Enforce per-tier daily message budgets via APIUsageLog accounting.

Components:
- ``selva_client`` — HTTP client wrapper. Real + mock implementations.
- ``retriever``    — RAG retrieval over the existing ES index.
- ``views``        — DRF view at POST /api/v1/chat/preguntar/
"""

from .selva_client import MockSelvaClient, SelvaClient, get_selva_client

__all__ = ["MockSelvaClient", "SelvaClient", "get_selva_client"]
