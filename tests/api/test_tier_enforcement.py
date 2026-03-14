"""Tests for RequireTier / RequireFeature wired to actual endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.api.middleware.tier_permissions import (
    RequireFeature,
    RequireTier,
    check_feature,
)


class TestBulkArticlesTierGate:
    """bulk_articles uses RequireFeature.of('bulk_download')."""

    def test_essentials_blocked_by_feature(self):
        perm = RequireFeature.of("bulk_download")()
        factory = APIRequestFactory()
        request = factory.get("/api/v1/bulk/articles/")
        user = MagicMock()
        user.tier = "essentials"
        request.user = user
        assert perm.has_permission(request, None) is False

    def test_community_passes_feature_gate(self):
        perm = RequireFeature.of("bulk_download")()
        factory = APIRequestFactory()
        request = factory.get("/api/v1/bulk/articles/")
        user = MagicMock()
        user.tier = "community"
        request.user = user
        assert perm.has_permission(request, None) is True

    def test_academic_passes_feature_gate(self):
        perm = RequireFeature.of("bulk_download")()
        factory = APIRequestFactory()
        request = factory.get("/api/v1/bulk/articles/")
        user = MagicMock()
        user.tier = "academic"
        request.user = user
        assert perm.has_permission(request, None) is True


class TestCreateWebhookTierGate:
    """create_webhook uses RequireFeature.of('webhooks')."""

    def test_essentials_blocked_by_feature(self):
        perm = RequireFeature.of("webhooks")()
        factory = APIRequestFactory()
        request = factory.post("/api/v1/webhooks/")
        user = MagicMock()
        user.tier = "essentials"
        request.user = user
        assert perm.has_permission(request, None) is False

    def test_community_blocked_by_feature(self):
        """Community does NOT have webhooks (only institutional+)."""
        perm = RequireFeature.of("webhooks")()
        factory = APIRequestFactory()
        request = factory.post("/api/v1/webhooks/")
        user = MagicMock()
        user.tier = "community"
        request.user = user
        assert perm.has_permission(request, None) is False

    def test_institutional_passes_feature_gate(self):
        perm = RequireFeature.of("webhooks")()
        factory = APIRequestFactory()
        request = factory.post("/api/v1/webhooks/")
        user = MagicMock()
        user.tier = "institutional"
        request.user = user
        assert perm.has_permission(request, None) is True


class TestSearchAnalyticsFeatureGate:
    """search_analytics feature check blocks essentials and community tiers."""

    def test_essentials_no_search_analytics(self):
        assert check_feature("essentials", "search_analytics") is False

    def test_community_no_search_analytics(self):
        assert check_feature("community", "search_analytics") is False

    def test_academic_has_search_analytics(self):
        assert check_feature("academic", "search_analytics") is True

    def test_anon_no_search_analytics(self):
        assert check_feature("anon", "search_analytics") is False
