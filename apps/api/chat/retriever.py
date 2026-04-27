"""
RAG retriever for the ``/preguntar`` chat.

Retrieves the top-K most relevant article snippets for a user query by
running a BM25 search against the existing ``articles`` ES index, then
optionally hydrates them with cross-reference metadata so the LLM can
quote outgoing references.

Design notes:
- We deliberately **do not** add a vector-search backend here. Tezca's
  ES index uses BM25 + function-score recency boost (per CLAUDE.md
  "Search relevance"); that's strong enough for the v1 chat. Vector
  retrieval is a separate roadmap item.
- Failure mode: if ES is degraded the retriever returns an empty
  context, the chat view replies politely without citations rather than
  hallucinate. Mirrors the existing graceful-degradation pattern in
  ``law_views``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from apps.api.config import INDEX_NAME, es_client

logger = logging.getLogger(__name__)


@dataclass
class RetrievedSnippet:
    """One article snippet returned from BM25 retrieval."""

    law_id: str
    law_name: str
    article_id: str
    text: str
    score: float

    def citation(self) -> str:
        """Inline citation string used in the LLM system prompt."""
        return f"[{self.law_id}#{self.article_id}]"

    def link(self) -> str:
        """Frontend link for the chat UI."""
        return f"/leyes/{self.law_id}#article-{self.article_id}"


def retrieve(
    query: str,
    *,
    top_k: int = 5,
    snippet_max_chars: int = 800,
) -> List[RetrievedSnippet]:
    """BM25 retrieval against the ``articles`` index.

    Returns up to ``top_k`` snippets, each truncated to
    ``snippet_max_chars`` so the system-prompt context stays bounded.
    On ES failure returns ``[]`` — the caller handles the empty case.
    """
    if not query or not query.strip():
        return []

    body = {
        "size": top_k,
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["text^1", "law_name^2"],
                "type": "best_fields",
            }
        },
        "_source": ["law_id", "law_name", "article_id", "text"],
    }

    try:
        response = es_client.search(index=INDEX_NAME, body=body)
    except Exception:
        logger.exception("ES retrieval failed for chat query")
        return []

    hits = response.get("hits", {}).get("hits", [])
    snippets: List[RetrievedSnippet] = []
    for hit in hits:
        src = hit.get("_source", {})
        text = (src.get("text") or "").strip()
        if not text:
            continue
        snippets.append(
            RetrievedSnippet(
                law_id=src.get("law_id", ""),
                law_name=src.get("law_name", ""),
                article_id=src.get("article_id", ""),
                text=_truncate(text, snippet_max_chars),
                score=float(hit.get("_score", 0.0)),
            )
        )
    return snippets


def build_system_prompt(snippets: List[RetrievedSnippet]) -> str:
    """Compose the system prompt that grounds the LLM in retrieved snippets.

    The prompt is in Spanish because Tezca's primary user is a Spanish
    speaker — but it instructs the model to answer in the user's
    language. The model is told to cite via ``[law_id#article_id]`` so
    the chat UI can convert citations into clickable links via the
    same regex.
    """
    if not snippets:
        return _SYSTEM_PROMPT_NO_CONTEXT

    citations_block = "\n\n".join(
        f"### {s.citation()} — {s.law_name}, Artículo {s.article_id}\n{s.text}"
        for s in snippets
    )
    return _SYSTEM_PROMPT_TEMPLATE.format(citations=citations_block)


_SYSTEM_PROMPT_TEMPLATE = """\
Eres Tezca, un asistente legal mexicano especializado en derecho federal,
estatal y municipal. Respondes preguntas usando ÚNICAMENTE los artículos
citados en CONTEXTO. Si la respuesta no está en CONTEXTO, dilo
claramente; no inventes referencias.

Reglas de citación:
- Cada afirmación legal debe ir acompañada de su cita en formato
  [law_id#article_id].
- No inventes artículos ni cambies sus números.
- Responde en el idioma de la pregunta del usuario.

CONTEXTO (artículos relevantes):

{citations}

Si la pregunta es ambigua, pide aclaración antes de responder.
"""

_SYSTEM_PROMPT_NO_CONTEXT = """\
Eres Tezca, un asistente legal mexicano. No encontré artículos relevantes
en el corpus para esta pregunta. Responde brevemente que necesitas más
contexto o que la consulta podría no estar en el corpus mexicano que
indexamos. No inventes citas.
"""


def _truncate(text: str, max_chars: int) -> str:
    """Truncate ``text`` to ``max_chars``, preserving word boundaries."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut + "…"


def extract_referenced_articles(
    snippets: List[RetrievedSnippet],
) -> List[dict]:
    """Build the citation list the chat UI renders next to the answer.

    Each citation links back to ``/leyes/{law_id}#article-{article_id}``,
    which is the same anchor pattern used by ``LinkifiedArticle`` so the
    user lands on the exact article when they click through.
    """
    seen: set[str] = set()
    citations: List[dict] = []
    for s in snippets:
        key = f"{s.law_id}#{s.article_id}"
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            {
                "law_id": s.law_id,
                "law_name": s.law_name,
                "article_id": s.article_id,
                "url": s.link(),
            }
        )
    return citations


def retrieval_disabled(reason: Optional[str] = None) -> List[RetrievedSnippet]:
    """Sentinel for callers that want to stub retrieval entirely (tests)."""
    if reason:
        logger.info("Chat retrieval disabled: %s", reason)
    return []
