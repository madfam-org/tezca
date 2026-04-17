"""Tests for semantic search endpoint: GET /api/v1/search/semantic/.

Covers:
  - Missing query parameter returns 400
  - Successful search returns results in keyword-search-compatible format
  - Missing embedding model (sentence-transformers) returns 503
  - Elasticsearch failure returns 503
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from elasticsearch.exceptions import ApiError
from rest_framework.test import APIClient


def _make_semantic_hit(doc_id, law_id, article, text, score=0.95):
    """Build a single ES kNN hit document."""
    return {
        "_id": doc_id,
        "_score": score,
        "_source": {
            "law_id": law_id,
            "law_name": f"Ley {law_id}",
            "article": article,
            "text": text,
            "publication_date": "2024-01-01",
            "tier": "federal",
            "law_type": "legislative",
            "state": None,
            "municipality": None,
            "hierarchy": [],
            "book": None,
            "title": None,
            "chapter": None,
            "category": "ley",
            "domains": ["fiscal"],
            "status": "vigente",
        },
    }


@pytest.mark.django_db
class TestSemanticSearch:
    """Tests for GET /api/v1/search/semantic/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("semantic-search")

    def test_semantic_search_requires_query(self):
        """GET without q= param returns 400."""
        response = self.client.get(self.url)
        assert response.status_code == 400
        assert "q" in response.json()["error"].lower()

    def test_semantic_search_empty_query_returns_400(self):
        """GET with q= (empty string) returns 400."""
        response = self.client.get(self.url, {"q": ""})
        assert response.status_code == 400

    def test_semantic_search_whitespace_query_returns_400(self):
        """GET with q= (whitespace only) returns 400."""
        response = self.client.get(self.url, {"q": "   "})
        assert response.status_code == 400

    @patch("apps.api.semantic_search_views.es_client")
    def test_semantic_search_returns_results(self, mock_es):
        """Mock EmbeddingGenerator + es_client, verify response format."""
        fake_embedding = [0.1] * 768

        mock_generator = MagicMock()
        mock_generator.generate.return_value = fake_embedding

        # Create a mock module with the mock generator class
        mock_embeddings_module = MagicMock()
        mock_embeddings_module.EmbeddingGenerator.return_value = mock_generator

        hits = [
            _make_semantic_hit(
                "cpeum-1", "cpeum", "1", "La soberania nacional reside en el pueblo."
            ),
            _make_semantic_hit(
                "cff-5", "cff", "5", "Son contribuciones los impuestos.", score=0.88
            ),
        ]
        mock_es.search.return_value = {"hits": {"hits": hits}}

        with patch.dict(
            sys.modules, {"apps.parsers.embeddings": mock_embeddings_module}
        ):
            response = self.client.get(self.url, {"q": "soberania del pueblo"})

        assert response.status_code == 200
        data = response.json()

        # Verify response shape matches keyword search format
        assert "results" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

        assert data["total"] == 2
        assert data["page"] == 1
        assert data["total_pages"] == 1
        assert len(data["results"]) == 2

        # Verify individual result fields
        result = data["results"][0]
        assert result["id"] == "cpeum-1"
        assert result["law_id"] == "cpeum"
        assert result["article"] == "1"
        assert "snippet" in result
        assert "text" in result
        assert "score" in result
        assert result["score"] == 0.95
        assert result["tier"] == "federal"

    @patch("apps.api.semantic_search_views.es_client")
    def test_semantic_search_respects_limit(self, mock_es):
        """Limit parameter controls number of results requested."""
        fake_embedding = [0.1] * 768

        mock_generator = MagicMock()
        mock_generator.generate.return_value = fake_embedding

        mock_embeddings_module = MagicMock()
        mock_embeddings_module.EmbeddingGenerator.return_value = mock_generator

        mock_es.search.return_value = {"hits": {"hits": []}}

        with patch.dict(
            sys.modules, {"apps.parsers.embeddings": mock_embeddings_module}
        ):
            response = self.client.get(self.url, {"q": "test", "limit": "5"})

        assert response.status_code == 200
        # Verify the kNN k parameter was set to 5
        call_kwargs = mock_es.search.call_args
        body = call_kwargs[1].get("body") or call_kwargs[1]
        assert body["knn"]["k"] == 5

    @patch("apps.api.semantic_search_views.es_client")
    def test_semantic_search_caps_limit_at_50(self, mock_es):
        """Limit is capped at 50."""
        fake_embedding = [0.1] * 768

        mock_generator = MagicMock()
        mock_generator.generate.return_value = fake_embedding

        mock_embeddings_module = MagicMock()
        mock_embeddings_module.EmbeddingGenerator.return_value = mock_generator

        mock_es.search.return_value = {"hits": {"hits": []}}

        with patch.dict(
            sys.modules, {"apps.parsers.embeddings": mock_embeddings_module}
        ):
            response = self.client.get(self.url, {"q": "test", "limit": "200"})

        assert response.status_code == 200
        call_kwargs = mock_es.search.call_args
        body = call_kwargs[1].get("body") or call_kwargs[1]
        assert body["knn"]["k"] == 50

    def test_semantic_search_handles_missing_embeddings(self):
        """When sentence-transformers not installed, returns 503."""
        # Remove the module from sys.modules to force ImportError on lazy import
        with patch.dict(sys.modules, {"apps.parsers.embeddings": None}):
            response = self.client.get(self.url, {"q": "amparo"})

        assert response.status_code == 503
        assert "not available" in response.json()["error"].lower()

    @patch("apps.api.semantic_search_views.es_client")
    def test_semantic_search_handles_es_failure(self, mock_es):
        """When ES fails, returns 503."""
        fake_embedding = [0.1] * 768

        mock_generator = MagicMock()
        mock_generator.generate.return_value = fake_embedding

        mock_embeddings_module = MagicMock()
        mock_embeddings_module.EmbeddingGenerator.return_value = mock_generator

        mock_es.search.side_effect = ApiError(
            message="Connection refused", meta=MagicMock(), body=None
        )

        with patch.dict(
            sys.modules, {"apps.parsers.embeddings": mock_embeddings_module}
        ):
            response = self.client.get(self.url, {"q": "impuestos"})

        assert response.status_code == 503
        assert "unavailable" in response.json()["error"].lower()

    @patch("apps.api.semantic_search_views.es_client")
    def test_semantic_search_handles_embedding_generation_failure(self, mock_es):
        """When embedding generation fails unexpectedly, returns 500."""
        mock_generator = MagicMock()
        mock_generator.generate.side_effect = RuntimeError("CUDA out of memory")

        mock_embeddings_module = MagicMock()
        mock_embeddings_module.EmbeddingGenerator.return_value = mock_generator

        with patch.dict(
            sys.modules, {"apps.parsers.embeddings": mock_embeddings_module}
        ):
            response = self.client.get(self.url, {"q": "derechos humanos"})

        assert response.status_code == 500
        assert "embedding" in response.json()["error"].lower()
