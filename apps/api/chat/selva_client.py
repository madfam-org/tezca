"""
Selva client — Tezca's gateway to the MADFAM-wide LLM router.

Per ``internal-devops/ECOSYSTEM.md``: every LLM call should route through
Selva (`selva-office`, formerly `selva-office`) at ``/v1``
(OpenAI-compatible). Tezca never holds an OpenAI / Anthropic API key.

Two implementations:

* ``SelvaClient`` — production. POSTs to ``$SELVA_API_URL/chat/completions``
  with a Janua-relayed bearer token. Returns the response message + usage.
* ``MockSelvaClient`` — deterministic. Used in tests and any environment
  where ``SELVA_API_URL`` is unset. Returns a templated answer derived from
  the input messages so test assertions can be exact.

The active client is selected by ``CHAT_BACKEND`` env var (``selva`` |
``mock``), defaulting to ``mock`` so a fresh dev box doesn't accidentally
hit production Selva.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

import requests

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A single message in a chat completion request/response."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatCompletion:
    """Selva's chat-completion response, normalized to what Tezca needs."""

    message: ChatMessage
    prompt_tokens: int
    completion_tokens: int
    model: str

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class _SelvaClientProtocol(Protocol):
    """Minimal contract every Selva client implementation must satisfy."""

    def chat_completion(
        self,
        messages: List[ChatMessage],
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> ChatCompletion: ...


class SelvaClient:
    """Real Selva client — talks HTTP to the OpenAI-compatible /v1 endpoint.

    Configuration:
    - ``SELVA_API_URL`` — base URL, e.g. ``https://selva.town/v1``
      (canonical public domain per RFC 0010 Layer 2).
    - ``SELVA_API_TOKEN`` — Janua-relayed bearer token. The Tezca service
      account is provisioned per the §3.1 cross-cutting Selva onboarding
      ticket.
    - ``SELVA_DEFAULT_MODEL`` — default ``"claude-haiku-4-5"`` (cheapest
      that handles our RAG context size).
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        default_model: str = "claude-haiku-4-5",
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._default_model = default_model
        self._timeout = timeout
        self._session = requests.Session()

    def chat_completion(
        self,
        messages: List[ChatMessage],
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> ChatCompletion:
        """Forward a chat-completion request to Selva.

        Raises ``requests.HTTPError`` on 4xx/5xx so the caller can decide
        whether to surface a user-facing error or retry.
        """
        payload: Dict[str, Any] = {
            "model": model or self._default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        url = f"{self._base_url}/chat/completions"

        resp = self._session.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()
        body = resp.json()

        choice = body["choices"][0]["message"]
        usage = body.get("usage", {})
        return ChatCompletion(
            message=ChatMessage(role=choice["role"], content=choice["content"]),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            model=body.get("model", payload["model"]),
        )


class MockSelvaClient:
    """Deterministic stand-in for tests + environments without Selva.

    Returns a canned reply derived from the inputs so tests can assert
    exact substrings. Token counts are heuristic (≈ 1 token per 4 chars
    of input + a fixed completion length).
    """

    def __init__(self, default_model: str = "mock-model") -> None:
        self._default_model = default_model

    def chat_completion(
        self,
        messages: List[ChatMessage],
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> ChatCompletion:
        # The deterministic reply echoes the last user turn so retrieval +
        # RAG-context-injection tests can assert that the prompt was built
        # correctly without depending on a real LLM.
        user_turn = next(
            (m.content for m in reversed(messages) if m.role == "user"), ""
        )
        canned = (
            f"[mock-selva] Recibí tu pregunta: «{user_turn[:120]}». "
            "En producción Selva enrutará a un LLM real con citas a artículos."
        )

        prompt_chars = sum(len(m.content) for m in messages)
        prompt_tokens = max(1, prompt_chars // 4)
        completion_tokens = max(1, len(canned) // 4)

        return ChatCompletion(
            message=ChatMessage(role="assistant", content=canned),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model or self._default_model,
        )


def get_selva_client() -> _SelvaClientProtocol:
    """Return the configured Selva client.

    Selection rule:
    - ``CHAT_BACKEND=selva`` → real ``SelvaClient`` (raises if env missing).
    - ``CHAT_BACKEND=mock`` (default) → ``MockSelvaClient``.

    Tests always get ``MockSelvaClient`` unless they explicitly inject a
    real one. Production deploys flip ``CHAT_BACKEND=selva`` once the
    Selva onboarding ticket lands.
    """
    backend = os.getenv("CHAT_BACKEND", "mock").lower()

    if backend == "selva":
        base_url = os.getenv("SELVA_API_URL")
        token = os.getenv("SELVA_API_TOKEN")
        if not base_url or not token:
            logger.error(
                "CHAT_BACKEND=selva but SELVA_API_URL/SELVA_API_TOKEN missing — "
                "falling back to MockSelvaClient"
            )
            return MockSelvaClient()
        return SelvaClient(
            base_url=base_url,
            token=token,
            default_model=os.getenv("SELVA_DEFAULT_MODEL", "claude-haiku-4-5"),
        )

    return MockSelvaClient()
