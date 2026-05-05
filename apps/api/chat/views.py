"""
``POST /api/v1/chat/preguntar/`` — first-party AI assistant endpoint.

Gating layers (in order):

1. ``CHAT_ENABLED`` env feature flag. When ``false`` (default), the
   endpoint returns 503. Lets us merge code without exposing the route.
2. Authenticated user (any tier with ``api_key_access``). Anonymous +
   ``free_member`` get 401/403 from the existing auth stack.
3. ``RequireFeature.of("chat")`` — only ``essentials+`` per
   ``apps/api/tiers.json``.
4. Daily-message budget per tier (``chat_messages_per_day``). Enforced
   via ``APIUsageLog`` rows tagged ``endpoint='chat.preguntar'``.

Body shape::

    POST /api/v1/chat/preguntar/
    Content-Type: application/json
    X-API-Key: tzk_...

    {"question": "..."}

Response::

    {
      "answer": "...",
      "citations": [
        {"law_id": "cpeum", "law_name": "Constitución...", "article_id": "31", "url": "/leyes/cpeum#article-31"},
        ...
      ],
      "usage": {"prompt_tokens": 1234, "completion_tokens": 200, "total_tokens": 1434, "model": "..."}
    }
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import os
from typing import Any, Dict

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from apps.api.middleware.tier_permissions import RequireFeature, get_tier_limits
from apps.api.models import APIUsageLog
from apps.api.tier_permissions import get_effective_tier

from .retriever import build_system_prompt, extract_referenced_articles, retrieve
from .selva_client import ChatMessage, get_selva_client

logger = logging.getLogger(__name__)

# Bound how much corpus context we ship per request — keeps the system
# prompt under typical 8K-token windows even on long-text articles.
_RETRIEVAL_TOP_K = 5
_SNIPPET_MAX_CHARS = 800

# Cap user input length so a malicious caller can't blow our token budget
# in a single request before the daily-budget check runs.
_MAX_QUESTION_CHARS = 2000

# tiers.json key for daily-budget enforcement
_BUDGET_KEY = "chat_messages_per_day"


def _chat_enabled() -> bool:
    return os.getenv("CHAT_ENABLED", "false").lower() in ("true", "1", "yes")


def _today_utc_start() -> datetime.datetime:
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _budget_for_tier(tier: str) -> int:
    """Daily message budget for ``tier``. -1 means unlimited."""
    return int(get_tier_limits(tier).get(_BUDGET_KEY, 0))


def _used_today(api_key_prefix: str) -> int:
    """Count chat.preguntar calls for this api-key prefix since 00:00 UTC."""
    if not api_key_prefix:
        return 0
    return APIUsageLog.objects.filter(
        api_key_prefix=api_key_prefix,
        endpoint="chat.preguntar",
        created_at__gte=_today_utc_start(),
    ).count()


def _record_usage(
    api_key_prefix: str,
    ip_address: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    """Log a chat call to APIUsageLog so the daily-budget check sees it.

    Token counts are intentionally not persisted on the row — APIUsageLog
    has no metadata column today. The endpoint name + count is enough
    for the v1 budget enforcement; richer telemetry goes to logs.
    """
    APIUsageLog.objects.create(
        api_key_prefix=api_key_prefix,
        ip_address=ip_address or "0.0.0.0",
        endpoint="chat.preguntar",
        method="POST",
        status_code=200,
    )
    # Log a SHA-256 hash of the api-key prefix instead of the prefix itself.
    # The prefix alone is low-risk (it's just the public-facing few chars,
    # not the secret), but several compliance regimes (PCI-DSS, SOC 2 CC6.7,
    # MX LFPDPPP) treat any portion of an authentication credential as
    # sensitive in unstructured logs. Hashing yields a stable correlation
    # id without leaking the credential surface.
    api_key_log_id = (
        hashlib.sha256(api_key_prefix.encode("utf-8")).hexdigest()[:16]
        if api_key_prefix
        else "anon"
    )
    logger.info(
        "chat.preguntar usage api_key_id=%s prompt_tokens=%d completion_tokens=%d",
        api_key_log_id,
        prompt_tokens,
        completion_tokens,
    )


@extend_schema(
    tags=["Chat"],
    summary="Ask Tezca a legal question (RAG over the corpus, LLM via Selva)",
    description=(
        "First-party AI assistant. Retrieves relevant articles from the "
        "Tezca corpus and forwards them to Selva for grounded generation. "
        "Gated behind CHAT_ENABLED feature flag and `essentials+` tier."
    ),
)
@api_view(["POST"])
@permission_classes([RequireFeature.of("chat")])
def preguntar(request: Request) -> Response:
    """Handle a single chat question."""
    # Layer 1: global feature flag
    if not _chat_enabled():
        return Response(
            {"error": "Chat is not enabled in this environment."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Layer 2: must have an authenticated user with a Janua user_id.
    # The combined-auth middleware populates request.user; api-key users
    # get a janua_user_id via the APIKey row.
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return Response(
            {"error": "Authentication required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    api_key_prefix = getattr(user, "api_key_prefix", "")

    # Layer 3 already handled by RequireFeature; pull tier for budgeting.
    tier = get_effective_tier(getattr(user, "tier", None) or "anon")
    budget = _budget_for_tier(tier)

    # Layer 4: daily-budget check
    if budget != -1:
        used = _used_today(api_key_prefix)
        if used >= budget:
            return Response(
                {
                    "error": "Daily chat budget exhausted.",
                    "tier": tier,
                    "limit": budget,
                    "resets_at": (
                        _today_utc_start() + datetime.timedelta(days=1)
                    ).isoformat(),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

    # Validate body
    body: Dict[str, Any] = request.data if isinstance(request.data, dict) else {}
    question = (body.get("question") or "").strip()
    if not question:
        return Response(
            {"error": "Body must include a non-empty `question` field."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(question) > _MAX_QUESTION_CHARS:
        return Response(
            {
                "error": (
                    f"Question is too long (max {_MAX_QUESTION_CHARS} characters)."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # RAG retrieval (failure-tolerant — empty context is acceptable)
    snippets = retrieve(
        question, top_k=_RETRIEVAL_TOP_K, snippet_max_chars=_SNIPPET_MAX_CHARS
    )

    system_prompt = build_system_prompt(snippets)
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=question),
    ]

    # Forward to Selva
    client = get_selva_client()
    try:
        completion = client.chat_completion(messages)
    except Exception:
        logger.exception("Selva chat completion failed")
        return Response(
            {"error": "El asistente está temporalmente no disponible."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # Record usage AFTER success so failed calls don't burn budget.
    if api_key_prefix:
        try:
            _record_usage(
                api_key_prefix,
                request.META.get("REMOTE_ADDR", ""),
                completion.prompt_tokens,
                completion.completion_tokens,
            )
        except Exception:
            logger.exception("Failed to record chat usage")

    return Response(
        {
            "answer": completion.message.content,
            "citations": extract_referenced_articles(snippets),
            "usage": {
                "prompt_tokens": completion.prompt_tokens,
                "completion_tokens": completion.completion_tokens,
                "total_tokens": completion.total_tokens,
                "model": completion.model,
            },
        }
    )
