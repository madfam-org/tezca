"""Tests for RequireTier wired to actual endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.api.middleware.tier_permissions import RequireTier, check_feature


class TestBulkArticlesTierGate:
    """bulk_articles requires community tier (+ bulk scope)."""

    def test_essentials_blocked_by_tier(self):
        perm = RequireTier.of("community")()
        factory = APIRequestFactory()
        request = factory.get("/api/v1/bulk/articles/")
        user = MagicMock()
        user.tier = "essentials"
        request.user = user
        assert perm.has_permission(request, None) is False

    def test_community_passes_tier_gate(self):
        perm = RequireTier.of("community")()
        factory = APIRequestFactory()
        request = factory.get("/api/v1/bulk/articles/")
        user = MagicMock()
        user.tier = "community"
        request.user = user
        assert perm.has_permission(request, None) is True

    def test_pro_passes_tier_gate(self):
        perm = RequireTier.of("community")()
        factory = APIRequestFactory()
        request = factory.get("/api/v1/bulk/articles/")
        user = MagicMock()
        user.tier = "pro"
        request.user = user
        assert perm.has_permission(request, None) is True


class TestCreateWebhookTierGate:
    """create_webhook requires community tier."""

    def test_free_user_blocked(self):
        perm = RequireTier.of("community")()
        factory = APIRequestFactory()
        request = factory.post("/api/v1/webhooks/")
        user = MagicMock()
        user.tier = "free"
        request.user = user
        assert perm.has_permission(request, None) is False

    def test_community_user_passes(self):
        perm = RequireTier.of("community")()
        factory = APIRequestFactory()
        request = factory.post("/api/v1/webhooks/")
        user = MagicMock()
        user.tier = "community"
        request.user = user
        assert perm.has_permission(request, None) is True


class TestSearchAnalyticsFeatureGate:
    """search_analytics feature check blocks essentials tier."""

    def test_essentials_no_search_analytics(self):
        assert check_feature("essentials", "search_analytics") is False

    def test_community_has_search_analytics(self):
        assert check_feature("community", "search_analytics") is True

    def test_pro_has_search_analytics(self):
        assert check_feature("pro", "search_analytics") is True

    def test_anon_no_search_analytics(self):
        assert check_feature("anon", "search_analytics") is False
