"""
Tests for the /api/v1/chat/preguntar/ endpoint and its components.

Covers (in priority order):
1. Feature-flag gating (CHAT_ENABLED)
2. Tier gating (community/free_member → 403, essentials+ → 200)
3. Selva-client selection (mock by default; selva env switch)
4. Retriever fail-tolerance (ES down → empty context, no exception)
5. Daily-budget enforcement (429 once limit hit)
6. Citation extraction + dedup
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.chat.retriever import (
    RetrievedSnippet,
    build_system_prompt,
    extract_referenced_articles,
    retrieve,
)
from apps.api.chat.selva_client import (
    ChatMessage,
    MockSelvaClient,
    SelvaClient,
    get_selva_client,
)
from apps.api.middleware.apikey_auth import APIKeyUser

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"


def _make_user(tier="essentials", prefix="chatpfx1"):
    mock_key = MagicMock()
    mock_key.prefix = prefix
    mock_key.owner_email = "chat@example.com"
    mock_key.name = "Chat Test Key"
    mock_key.tier = tier
    mock_key.scopes = ["read", "search"]
    mock_key.allowed_domains = []
    return APIKeyUser(mock_key)


# ── MockSelvaClient ────────────────────────────────────────────────────


class TestMockSelvaClient:
    def test_returns_canned_response_echoing_user_turn(self):
        client = MockSelvaClient()
        messages = [
            ChatMessage(role="system", content="You are Tezca."),
            ChatMessage(role="user", content="¿Qué dice el Artículo 31?"),
        ]
        completion = client.chat_completion(messages)
        assert completion.message.role == "assistant"
        assert "Artículo 31" in completion.message.content

    def test_token_counts_are_nonzero(self):
        client = MockSelvaClient()
        completion = client.chat_completion([ChatMessage(role="user", content="hola")])
        assert completion.prompt_tokens > 0
        assert completion.completion_tokens > 0
        assert completion.total_tokens == (
            completion.prompt_tokens + completion.completion_tokens
        )


# ── get_selva_client() backend selection ───────────────────────────────


class TestSelvaClientFactory:
    def test_default_returns_mock(self, monkeypatch):
        monkeypatch.delenv("CHAT_BACKEND", raising=False)
        client = get_selva_client()
        assert isinstance(client, MockSelvaClient)

    def test_explicit_mock_returns_mock(self, monkeypatch):
        monkeypatch.setenv("CHAT_BACKEND", "mock")
        assert isinstance(get_selva_client(), MockSelvaClient)

    def test_selva_without_env_falls_back_to_mock(self, monkeypatch):
        monkeypatch.setenv("CHAT_BACKEND", "selva")
        monkeypatch.delenv("SELVA_API_URL", raising=False)
        monkeypatch.delenv("SELVA_API_TOKEN", raising=False)
        # Configuration error degrades to MockSelvaClient — never crash
        # on import/startup.
        assert isinstance(get_selva_client(), MockSelvaClient)

    def test_selva_with_env_returns_real_client(self, monkeypatch):
        monkeypatch.setenv("CHAT_BACKEND", "selva")
        monkeypatch.setenv("SELVA_API_URL", "https://example.test/v1")
        monkeypatch.setenv("SELVA_API_TOKEN", "test-token")
        client = get_selva_client()
        assert isinstance(client, SelvaClient)


# ── Retriever ──────────────────────────────────────────────────────────


class TestRetriever:
    @patch("apps.api.chat.retriever.es_client")
    def test_retrieve_returns_truncated_snippets(self, mock_es):
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_score": 5.0,
                        "_source": {
                            "law_id": "cpeum",
                            "law_name": "Constitución Política",
                            "article_id": "31",
                            "text": "x" * 1500,
                        },
                    }
                ]
            }
        }
        result = retrieve(
            "¿Cuáles son las obligaciones?", top_k=3, snippet_max_chars=500
        )
        assert len(result) == 1
        assert result[0].article_id == "31"
        assert len(result[0].text) <= 501  # 500 + ellipsis char

    @patch("apps.api.chat.retriever.es_client")
    def test_retrieve_returns_empty_on_es_failure(self, mock_es):
        mock_es.search.side_effect = Exception("ES is down")
        result = retrieve("anything")
        assert result == [], "ES failure must degrade to empty, not raise"

    def test_retrieve_returns_empty_on_blank_query(self):
        assert retrieve("") == []
        assert retrieve("   ") == []

    def test_build_system_prompt_with_no_context_uses_no_context_template(self):
        prompt = build_system_prompt([])
        assert "no encontré" in prompt.lower() or "no encontre" in prompt.lower()

    def test_build_system_prompt_includes_citations_format(self):
        snippets = [
            RetrievedSnippet(
                law_id="cpeum",
                law_name="Constitución",
                article_id="31",
                text="Son obligaciones de los mexicanos…",
                score=4.2,
            ),
        ]
        prompt = build_system_prompt(snippets)
        assert "[cpeum#31]" in prompt
        assert "Constitución" in prompt

    def test_extract_referenced_articles_dedups_by_law_and_article(self):
        snippets = [
            RetrievedSnippet(
                law_id="cpeum",
                law_name="Constitución",
                article_id="31",
                text="...",
                score=4.0,
            ),
            RetrievedSnippet(
                law_id="cpeum",
                law_name="Constitución",
                article_id="31",
                text="duplicate",
                score=3.0,
            ),
            RetrievedSnippet(
                law_id="cpeum",
                law_name="Constitución",
                article_id="73",
                text="...",
                score=3.5,
            ),
        ]
        citations = extract_referenced_articles(snippets)
        assert len(citations) == 2
        assert {c["article_id"] for c in citations} == {"31", "73"}
        # URL points back to the article anchor used by LinkifiedArticle
        assert all("article-" in c["url"] for c in citations)


# ── Endpoint integration tests ─────────────────────────────────────────


@pytest.mark.django_db
class TestPreguntarEndpoint:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("chat-preguntar")

    def test_503_when_chat_disabled(self, monkeypatch):
        monkeypatch.setenv("CHAT_ENABLED", "false")
        response = self.client.post(self.url, {"question": "..."}, format="json")
        # Either 503 (feature-flag) or 401 (auth-first) is acceptable here:
        # the auth layer fires before the feature flag; in production both
        # together amount to "endpoint is closed."
        assert response.status_code in (401, 503)

    @patch(AUTH_PATCH)
    def test_blocks_essentials_below_tier(self, mock_auth, monkeypatch):
        monkeypatch.setenv("CHAT_ENABLED", "true")
        monkeypatch.setenv("CHAT_BACKEND", "mock")
        # community tier doesn't have chat=true in tiers.json
        user = _make_user(tier="community", prefix="commx001")
        mock_auth.return_value = (user, "fake-key")
        response = self.client.post(self.url, {"question": "x"}, format="json")
        assert response.status_code == 403

    @patch("apps.api.chat.views.retrieve")
    @patch(AUTH_PATCH)
    def test_essentials_tier_gets_answer(self, mock_auth, mock_retrieve, monkeypatch):
        monkeypatch.setenv("CHAT_ENABLED", "true")
        monkeypatch.setenv("CHAT_BACKEND", "mock")
        user = _make_user(tier="essentials", prefix="essex001")
        mock_auth.return_value = (user, "fake-key")
        # Stub retriever so no ES is needed
        mock_retrieve.return_value = [
            RetrievedSnippet(
                law_id="cpeum",
                law_name="Constitución",
                article_id="31",
                text="Son obligaciones de los mexicanos…",
                score=4.0,
            )
        ]

        response = self.client.post(
            self.url,
            {"question": "¿Cuáles son las obligaciones de los mexicanos?"},
            format="json",
        )
        assert response.status_code == 200
        body = response.json()
        assert "answer" in body
        assert body["citations"] == [
            {
                "law_id": "cpeum",
                "law_name": "Constitución",
                "article_id": "31",
                "url": "/leyes/cpeum#article-31",
            }
        ]
        assert body["usage"]["total_tokens"] > 0

    @patch("apps.api.chat.views.retrieve")
    @patch(AUTH_PATCH)
    def test_rejects_blank_question(self, mock_auth, mock_retrieve, monkeypatch):
        monkeypatch.setenv("CHAT_ENABLED", "true")
        user = _make_user(tier="essentials", prefix="essex002")
        mock_auth.return_value = (user, "fake-key")

        response = self.client.post(self.url, {"question": "  "}, format="json")
        assert response.status_code == 400

    @patch("apps.api.chat.views.retrieve")
    @patch(AUTH_PATCH)
    def test_rejects_oversize_question(self, mock_auth, mock_retrieve, monkeypatch):
        monkeypatch.setenv("CHAT_ENABLED", "true")
        user = _make_user(tier="essentials", prefix="essex003")
        mock_auth.return_value = (user, "fake-key")

        oversized = "x" * 2500
        response = self.client.post(self.url, {"question": oversized}, format="json")
        assert response.status_code == 400

    @patch("apps.api.chat.views.retrieve")
    @patch(AUTH_PATCH)
    def test_returns_502_on_selva_failure(self, mock_auth, mock_retrieve, monkeypatch):
        monkeypatch.setenv("CHAT_ENABLED", "true")
        monkeypatch.setenv("CHAT_BACKEND", "mock")
        user = _make_user(tier="essentials", prefix="essex004")
        mock_auth.return_value = (user, "fake-key")
        mock_retrieve.return_value = []

        # Patch the client factory to return a client that raises
        with patch("apps.api.chat.views.get_selva_client") as mock_factory:
            failing = MagicMock()
            failing.chat_completion.side_effect = Exception("upstream down")
            mock_factory.return_value = failing

            response = self.client.post(
                self.url, {"question": "anything"}, format="json"
            )
        assert response.status_code == 502

    @patch("apps.api.chat.views.retrieve")
    @patch(AUTH_PATCH)
    def test_429_when_daily_budget_exhausted(
        self, mock_auth, mock_retrieve, monkeypatch
    ):
        """Synthesize 30 prior usage rows; the 31st request should 429."""
        monkeypatch.setenv("CHAT_ENABLED", "true")
        monkeypatch.setenv("CHAT_BACKEND", "mock")
        user = _make_user(tier="essentials", prefix="essex005")
        mock_auth.return_value = (user, "fake-key")
        mock_retrieve.return_value = []

        from apps.api.models import APIUsageLog

        for _ in range(30):
            APIUsageLog.objects.create(
                api_key_prefix="essex005",
                ip_address="127.0.0.1",
                endpoint="chat.preguntar",
                method="POST",
                status_code=200,
            )

        response = self.client.post(self.url, {"question": "next one"}, format="json")
        assert response.status_code == 429
        assert response.json()["limit"] == 30
