"""Tests for IsTezcaAdmin permission class."""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.middleware.admin_permission import IsTezcaAdmin
from apps.api.middleware.janua_auth import JanuaUser


class TestIsTezcaAdminUnit:
    """Unit tests for IsTezcaAdmin.has_permission."""

    def setup_method(self):
        self.permission = IsTezcaAdmin()

    def _make_request(self, user=None):
        request = MagicMock()
        request.user = user
        return request

    def test_unauthenticated_denied(self):
        user = MagicMock()
        user.is_authenticated = False
        request = self._make_request(user)
        assert self.permission.has_permission(request, None) is False

    def test_no_user_denied(self):
        request = MagicMock(spec=[])
        request.user = None
        assert self.permission.has_permission(request, None) is False

    def test_platform_admin_claim_allowed(self):
        user = JanuaUser({"sub": "user-1", "is_admin": True})
        request = self._make_request(user)
        assert self.permission.has_permission(request, None) is True

    @pytest.mark.parametrize("value", [False, None, "true", 1, "True"])
    def test_platform_admin_claim_must_be_exactly_true(self, value):
        user = JanuaUser({"sub": "user-1", "is_admin": value})
        request = self._make_request(user)
        assert self.permission.has_permission(request, None) is False

    def test_organization_admin_in_roles_denied(self):
        """A bare ``admin`` in ``roles`` is an organization role, not platform admin."""
        user = JanuaUser({"sub": "user-1", "roles": ["admin"], "is_admin": False})
        request = self._make_request(user)
        assert self.permission.has_permission(request, None) is False

    def test_organization_admin_without_is_admin_claim_denied(self):
        user = JanuaUser({"sub": "user-1", "roles": ["owner", "admin", "member"]})
        request = self._make_request(user)
        assert self.permission.has_permission(request, None) is False

    def test_singular_role_admin_denied(self):
        user = JanuaUser({"sub": "user-1", "role": "admin"})
        request = self._make_request(user)
        assert self.permission.has_permission(request, None) is False

    @pytest.mark.parametrize(
        "roles",
        [
            ["superadmin"],
            ["platform_admin"],
            ["platform-admin"],
            ["Admin"],
            ["tezca:admin"],
        ],
    )
    def test_custom_organization_role_named_like_admin_denied(self, roles):
        user = JanuaUser({"sub": "user-1", "roles": roles})
        request = self._make_request(user)
        assert self.permission.has_permission(request, None) is False

    def test_non_admin_role_denied(self):
        user = JanuaUser({"sub": "user-2", "role": "member"})
        request = self._make_request(user)
        assert self.permission.has_permission(request, None) is False

    def test_no_role_claim_denied(self):
        user = JanuaUser({"sub": "user-3", "email": "test@example.com"})
        request = self._make_request(user)
        assert self.permission.has_permission(request, None) is False

    @override_settings(TEZCA_ADMIN_USER_IDS={"admin-user-99"})
    def test_allowlisted_user_id_allowed(self):
        user = JanuaUser({"sub": "admin-user-99"})
        request = self._make_request(user)
        assert self.permission.has_permission(request, None) is True

    @override_settings(TEZCA_ADMIN_USER_IDS={"admin-user-99"})
    def test_allowlisted_user_id_allowed_without_any_role(self):
        user = JanuaUser(
            {"sub": "admin-user-99", "roles": ["member"], "is_admin": False}
        )
        request = self._make_request(user)
        assert self.permission.has_permission(request, None) is True

    @override_settings(TEZCA_ADMIN_USER_IDS={"admin-user-99"})
    def test_non_allowlisted_user_denied(self):
        user = JanuaUser({"sub": "regular-user-1"})
        request = self._make_request(user)
        assert self.permission.has_permission(request, None) is False

    @override_settings(TEZCA_ADMIN_USER_IDS=set())
    def test_empty_allowlist_platform_admin_claim_still_works(self):
        user = JanuaUser({"sub": "user-1", "is_admin": True})
        request = self._make_request(user)
        assert self.permission.has_permission(request, None) is True


@pytest.mark.django_db
class TestAdminEndpointAccess:
    """Integration tests verifying admin endpoints reject non-admin users.

    _protected() sets authentication_classes to [JanuaJWTAuthentication]
    on the view class, so we patch that authenticator (not CombinedAuthentication).
    """

    def setup_method(self):
        self.client = APIClient()

    @patch("apps.api.middleware.janua_auth.JanuaJWTAuthentication.authenticate")
    def test_non_admin_gets_403_on_metrics(self, mock_auth):
        """A regular authenticated user cannot access admin endpoints."""
        user = JanuaUser({"sub": "regular-user", "email": "user@example.com"})
        user.tier = "academic"
        user.scopes = ["read", "search"]
        user.allowed_domains = []
        user.api_key_prefix = ""
        mock_auth.return_value = (user, "fake-token")

        url = reverse("admin-metrics")
        response = self.client.get(url)
        assert response.status_code == 403

    @patch("apps.api.middleware.janua_auth.JanuaJWTAuthentication.authenticate")
    def test_platform_admin_gets_200_on_metrics(self, mock_auth):
        """A user with the platform-admin claim can access admin endpoints."""
        from apps.api.models import Law

        Law.objects.create(official_id="test-law", name="Test", tier="federal")

        user = JanuaUser(
            {"sub": "admin-1", "email": "admin@example.com", "is_admin": True}
        )
        user.tier = "madfam"
        user.scopes = ["read", "search"]
        user.allowed_domains = []
        user.api_key_prefix = ""
        mock_auth.return_value = (user, "fake-token")

        url = reverse("admin-metrics")
        response = self.client.get(url)
        assert response.status_code == 200

    @patch("apps.api.middleware.janua_auth.JanuaJWTAuthentication.authenticate")
    def test_organization_admin_gets_403_on_metrics(self, mock_auth):
        """An organization admin without the platform-admin claim is refused."""
        user = JanuaUser(
            {
                "sub": "org-admin",
                "email": "org-admin@example.com",
                "roles": ["admin"],
                "is_admin": False,
            }
        )
        user.tier = "academic"
        user.scopes = ["read", "search"]
        user.allowed_domains = []
        user.api_key_prefix = ""
        mock_auth.return_value = (user, "fake-token")

        url = reverse("admin-metrics")
        response = self.client.get(url)
        assert response.status_code == 403

    def test_unauthenticated_gets_401_on_metrics(self):
        """Unauthenticated requests to admin endpoints get 401."""
        url = reverse("admin-metrics")
        response = self.client.get(url)
        assert response.status_code == 401

    def test_health_check_stays_open(self):
        """Health check endpoint is not protected by admin permission."""
        url = reverse("admin-health")
        response = self.client.get(url)
        assert response.status_code == 200
