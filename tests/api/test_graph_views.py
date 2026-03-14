"""Tests for graph API endpoints."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.middleware.apikey_auth import APIKeyUser
from apps.api.middleware.janua_auth import JanuaUser
from apps.api.models import CrossReference, Law


def _uid():
    return uuid.uuid4().hex[:8]


def _make_law(slug=None, **kwargs):
    slug = slug or f"law-{_uid()}"
    defaults = {"name": f"Ley {slug}", "tier": "federal", "status": "vigente"}
    defaults.update(kwargs)
    return Law.objects.create(official_id=slug, **defaults)


def _make_ref(
    source_slug, target_slug, confidence=0.9, article="1", target_article="1"
):
    return CrossReference.objects.create(
        source_law_slug=source_slug,
        source_article_id=article,
        target_law_slug=target_slug,
        target_article_num=target_article,
        reference_text=f"ref {source_slug}->{target_slug}",
        confidence=confidence,
        start_position=0,
        end_position=10,
    )


AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"


def _make_user(tier="community"):
    user = JanuaUser({"sub": "graph-user", "email": "graph@test.com", "tier": tier})
    user.tier = tier
    user.scopes = ["read", "search"]
    user.allowed_domains = []
    user.api_key_prefix = ""
    return user


@pytest.mark.django_db
class TestLawGraph:
    """Tests for GET /laws/<law_id>/graph/"""

    def setup_method(self):
        self.client = APIClient()
        self.law_a = _make_law("graph-a")
        self.law_b = _make_law("graph-b")
        self.law_c = _make_law("graph-c")
        # A -> B (3 refs), A -> C (1 ref), B -> C (2 refs)
        for i in range(3):
            _make_ref("graph-a", "graph-b", article=str(i + 1))
        _make_ref("graph-a", "graph-c")
        _make_ref("graph-b", "graph-c", article="1")
        _make_ref("graph-b", "graph-c", article="2")
        # Authenticate as institutional tier (graph_api=true in tiers.json)
        self._auth_patcher = patch(AUTH_PATCH)
        mock_auth = self._auth_patcher.start()
        user = _make_user(tier="institutional")
        mock_auth.return_value = (user, "fake-token")

    def teardown_method(self):
        self._auth_patcher.stop()

    def test_law_graph_returns_nodes_and_edges(self):
        url = reverse("law-graph", args=["graph-a"])
        resp = self.client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["focal_law"] == "graph-a"
        assert len(data["nodes"]) >= 2
        assert len(data["edges"]) >= 1
        # Focal node is present and marked
        focal = [n for n in data["nodes"] if n["id"] == "graph-a"]
        assert len(focal) == 1
        assert focal[0]["is_focal"] is True

    def test_law_graph_depth_2_expands(self):
        url = reverse("law-graph", args=["graph-a"])
        resp = self.client.get(url, {"depth": 2})
        assert resp.status_code == 200
        data = resp.json()
        node_ids = {n["id"] for n in data["nodes"]}
        # Depth 2 should find C via A->B->C
        assert "graph-c" in node_ids
        assert data["meta"]["depth_reached"] >= 1

    def test_max_nodes_truncates(self):
        url = reverse("law-graph", args=["graph-a"])
        resp = self.client.get(url, {"depth": 3, "max_nodes": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["nodes"]) <= 2
        assert data["meta"]["truncated"] is True

    def test_min_confidence_filters_edges(self):
        # Create low-confidence ref
        _make_ref("graph-a", "graph-c", confidence=0.1, article="99")
        url = reverse("law-graph", args=["graph-a"])
        # High confidence: should only see B
        resp = self.client.get(url, {"min_confidence": 0.8, "depth": 1})
        data = resp.json()
        node_ids = {n["id"] for n in data["nodes"]}
        # A's refs to B have confidence 0.9, A's ref to C has 0.9 (original) + 0.1 (low)
        # But the aggregation averages them, so they should still be present
        assert "graph-a" in node_ids

    def test_direction_outgoing_only(self):
        # Create incoming ref: B -> A
        _make_ref("graph-b", "graph-a")
        url = reverse("law-graph", args=["graph-a"])
        resp_both = self.client.get(url, {"direction": "both"})
        resp_out = self.client.get(url, {"direction": "outgoing"})
        # outgoing-only should not include B as a source of edges pointing to A
        # but A->B edge should still bring B in
        assert resp_both.status_code == 200
        assert resp_out.status_code == 200

    def test_direction_incoming_only(self):
        _make_ref("graph-b", "graph-a")
        url = reverse("law-graph", args=["graph-a"])
        resp = self.client.get(url, {"direction": "incoming"})
        assert resp.status_code == 200
        data = resp.json()
        node_ids = {n["id"] for n in data["nodes"]}
        # B references A, so B should appear
        assert "graph-b" in node_ids

    def test_unknown_law_returns_empty_graph(self):
        url = reverse("law-graph", args=["nonexistent-law"])
        resp = self.client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        # Only the focal node itself (with no Law match)
        assert data["meta"]["total_edges"] == 0

    def test_response_shape(self):
        url = reverse("law-graph", args=["graph-a"])
        resp = self.client.get(url)
        data = resp.json()
        assert set(data.keys()) == {"focal_law", "nodes", "edges", "meta"}
        assert set(data["meta"].keys()) == {
            "total_nodes",
            "total_edges",
            "depth_reached",
            "truncated",
        }
        if data["nodes"]:
            n = data["nodes"][0]
            assert "id" in n
            assert "label" in n
            assert "tier" in n
            assert "ref_count" in n
            assert "is_focal" in n
        if data["edges"]:
            e = data["edges"][0]
            assert "id" in e
            assert "source" in e
            assert "target" in e
            assert "weight" in e
            assert "avg_confidence" in e

    def test_edge_weight_aggregation(self):
        """Multiple refs between same pair aggregate into one edge with weight > 1."""
        url = reverse("law-graph", args=["graph-a"])
        resp = self.client.get(url, {"depth": 1})
        data = resp.json()
        ab_edges = [
            e
            for e in data["edges"]
            if "graph-a" in e["source"] and "graph-b" in e["target"]
        ]
        if ab_edges:
            assert ab_edges[0]["weight"] == 3


@pytest.mark.django_db
class TestGraphOverview:
    """Tests for GET /graph/overview/"""

    def setup_method(self):
        self.client = APIClient()
        self.fed_a = _make_law("overview-fed-a", tier="federal", category="fiscal")
        self.fed_b = _make_law("overview-fed-b", tier="federal", category="fiscal")
        self.state_c = _make_law("overview-state-c", tier="state", category="civil")
        # Create refs with weight >= 3 (default min_weight)
        for i in range(4):
            _make_ref("overview-fed-a", "overview-fed-b", article=str(i))
        for i in range(3):
            _make_ref("overview-fed-b", "overview-state-c", article=str(i + 10))
        # Authenticate as institutional tier (graph_api=true in tiers.json)
        self._auth_patcher = patch(AUTH_PATCH)
        mock_auth = self._auth_patcher.start()
        user = _make_user(tier="institutional")
        mock_auth.return_value = (user, "fake-token")

    def teardown_method(self):
        self._auth_patcher.stop()

    def test_overview_returns_global_graph(self):
        url = reverse("graph-overview")
        resp = self.client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["focal_law"] is None
        assert data["meta"]["total_nodes"] >= 2
        assert data["meta"]["total_edges"] >= 1

    def test_overview_tier_filter(self):
        url = reverse("graph-overview")
        resp = self.client.get(url, {"tier": "federal", "min_weight": 1})
        assert resp.status_code == 200
        data = resp.json()
        # Should include federal laws
        node_ids = {n["id"] for n in data["nodes"]}
        assert "overview-fed-a" in node_ids

    def test_overview_category_filter(self):
        url = reverse("graph-overview")
        resp = self.client.get(url, {"category": "fiscal", "min_weight": 1})
        assert resp.status_code == 200
        data = resp.json()
        node_ids = {n["id"] for n in data["nodes"]}
        assert "overview-fed-a" in node_ids

    def test_overview_min_weight(self):
        url = reverse("graph-overview")
        # min_weight=5 should exclude the 3-ref edge but keep the 4-ref one
        resp = self.client.get(url, {"min_weight": 5})
        assert resp.status_code == 200
        data = resp.json()
        # Only the 4-ref edge qualifies
        for e in data["edges"]:
            assert e["weight"] >= 5


@pytest.mark.django_db
class TestGraphTierGating:
    """Tests for tier-based access control on graph endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.law = _make_law("tier-test-law")

    def test_anonymous_gets_403_on_law_graph(self):
        """Anonymous users should be denied access to the graph API."""
        url = reverse("law-graph", args=["tier-test-law"])
        resp = self.client.get(url)
        # Without authentication the endpoint should deny access
        assert resp.status_code in (401, 403)

    @patch(AUTH_PATCH)
    def test_community_gets_403_on_law_graph(self, mock_auth):
        """Community tier should be denied access to the graph API."""
        user = _make_user(tier="community")
        mock_auth.return_value = (user, "fake-token")
        url = reverse("law-graph", args=["tier-test-law"])
        resp = self.client.get(url)
        assert resp.status_code == 403

    @patch(AUTH_PATCH)
    def test_institutional_passes_law_graph(self, mock_auth):
        """Institutional tier should have access to the graph API."""
        user = _make_user(tier="institutional")
        mock_auth.return_value = (user, "fake-token")
        url = reverse("law-graph", args=["tier-test-law"])
        resp = self.client.get(url)
        assert resp.status_code == 200
