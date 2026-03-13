"""Tests for user preference endpoints."""

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.middleware.janua_auth import JanuaUser
from apps.api.models import UserPreference

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"


def _make_user(user_id="test-user-1", tier="pro"):
    user = JanuaUser({"sub": user_id, "email": f"{user_id}@test.com", "tier": tier})
    user.tier = tier
    user.scopes = ["read", "search"]
    user.allowed_domains = []
    user.api_key_prefix = ""
    return user


@pytest.mark.django_db
class TestUserPreferences:
    """Tests for GET/PUT /user/preferences/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("user-preferences")
        self.user = _make_user()

    @patch(AUTH_PATCH)
    def test_get_auto_creates(self, mock_auth):
        """GET creates preferences record if missing and returns defaults."""
        mock_auth.return_value = (self.user, "fake-token")
        assert UserPreference.objects.count() == 0

        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["bookmarks"] == []
        assert data["recently_viewed"] == []
        assert data["preferences"] == {}
        assert "updated_at" in data
        assert UserPreference.objects.count() == 1

    @patch(AUTH_PATCH)
    def test_get_returns_existing(self, mock_auth):
        """GET returns existing preferences data."""
        mock_auth.return_value = (self.user, "fake-token")
        UserPreference.objects.create(
            janua_user_id="test-user-1",
            bookmarks=["cpeum", "lft"],
            recently_viewed=["cpeum"],
            preferences={"theme": "dark", "font_size": "large"},
        )

        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["bookmarks"] == ["cpeum", "lft"]
        assert data["recently_viewed"] == ["cpeum"]
        assert data["preferences"]["theme"] == "dark"

    @patch(AUTH_PATCH)
    def test_put_update(self, mock_auth):
        """PUT replaces preferences data."""
        mock_auth.return_value = (self.user, "fake-token")
        UserPreference.objects.create(
            janua_user_id="test-user-1",
            bookmarks=["old"],
            preferences={"theme": "light"},
        )

        response = self.client.put(
            self.url,
            {
                "bookmarks": ["cpeum", "lft"],
                "preferences": {"theme": "dark", "language": "es"},
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.json()["status"] == "updated"

        pref = UserPreference.objects.get(janua_user_id="test-user-1")
        assert pref.bookmarks == ["cpeum", "lft"]
        assert pref.preferences["theme"] == "dark"

    @patch(AUTH_PATCH)
    def test_put_partial_fields(self, mock_auth):
        """PUT with only some fields updates only those fields."""
        mock_auth.return_value = (self.user, "fake-token")
        UserPreference.objects.create(
            janua_user_id="test-user-1",
            bookmarks=["cpeum"],
            recently_viewed=["lft"],
            preferences={"theme": "light"},
        )

        response = self.client.put(self.url, {"bookmarks": ["new"]}, format="json")

        assert response.status_code == 200
        pref = UserPreference.objects.get(janua_user_id="test-user-1")
        assert pref.bookmarks == ["new"]
        # Unchanged fields preserved
        assert pref.recently_viewed == ["lft"]
        assert pref.preferences == {"theme": "light"}

    def test_get_unauthenticated(self):
        """GET without auth returns 401."""
        response = self.client.get(self.url)
        assert response.status_code == 401

    def test_put_unauthenticated(self):
        """PUT without auth returns 401."""
        response = self.client.put(self.url, {"bookmarks": ["cpeum"]}, format="json")
        assert response.status_code == 401


@pytest.mark.django_db
class TestUserBookmarks:
    """Tests for PATCH /user/bookmarks/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("user-bookmarks")
        self.user = _make_user()

    @patch(AUTH_PATCH)
    def test_add_bookmark(self, mock_auth):
        """PATCH action=add adds a bookmark."""
        mock_auth.return_value = (self.user, "fake-token")

        response = self.client.patch(
            self.url, {"action": "add", "law_id": "cpeum"}, format="json"
        )

        assert response.status_code == 200
        assert "cpeum" in response.json()["bookmarks"]

    @patch(AUTH_PATCH)
    def test_add_duplicate_bookmark(self, mock_auth):
        """PATCH action=add with existing bookmark does not duplicate."""
        mock_auth.return_value = (self.user, "fake-token")
        UserPreference.objects.create(janua_user_id="test-user-1", bookmarks=["cpeum"])

        response = self.client.patch(
            self.url, {"action": "add", "law_id": "cpeum"}, format="json"
        )

        assert response.status_code == 200
        assert response.json()["bookmarks"].count("cpeum") == 1

    @patch(AUTH_PATCH)
    def test_remove_bookmark(self, mock_auth):
        """PATCH action=remove removes a bookmark."""
        mock_auth.return_value = (self.user, "fake-token")
        UserPreference.objects.create(
            janua_user_id="test-user-1", bookmarks=["cpeum", "lft"]
        )

        response = self.client.patch(
            self.url, {"action": "remove", "law_id": "cpeum"}, format="json"
        )

        assert response.status_code == 200
        assert response.json()["bookmarks"] == ["lft"]

    @patch(AUTH_PATCH)
    def test_invalid_action(self, mock_auth):
        """PATCH with invalid action returns 400."""
        mock_auth.return_value = (self.user, "fake-token")

        response = self.client.patch(
            self.url, {"action": "toggle", "law_id": "cpeum"}, format="json"
        )

        assert response.status_code == 400

    @patch(AUTH_PATCH)
    def test_missing_law_id(self, mock_auth):
        """PATCH without law_id returns 400."""
        mock_auth.return_value = (self.user, "fake-token")

        response = self.client.patch(self.url, {"action": "add"}, format="json")

        assert response.status_code == 400

    def test_unauthenticated(self):
        """PATCH without auth returns 401."""
        response = self.client.patch(
            self.url, {"action": "add", "law_id": "cpeum"}, format="json"
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestUserRecentlyViewed:
    """Tests for PATCH /user/recently-viewed/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("user-recently-viewed")
        self.user = _make_user()

    @patch(AUTH_PATCH)
    def test_add_recently_viewed(self, mock_auth):
        """PATCH adds a law to the front of recently_viewed."""
        mock_auth.return_value = (self.user, "fake-token")
        UserPreference.objects.create(
            janua_user_id="test-user-1", recently_viewed=["lft"]
        )

        response = self.client.patch(self.url, {"law_id": "cpeum"}, format="json")

        assert response.status_code == 200
        viewed = response.json()["recently_viewed"]
        assert viewed[0] == "cpeum"
        assert viewed[1] == "lft"

    @patch(AUTH_PATCH)
    def test_dedup_moves_to_front(self, mock_auth):
        """PATCH with existing law_id moves it to front (deduplication)."""
        mock_auth.return_value = (self.user, "fake-token")
        UserPreference.objects.create(
            janua_user_id="test-user-1",
            recently_viewed=["lft", "cpeum", "cff"],
        )

        response = self.client.patch(self.url, {"law_id": "cpeum"}, format="json")

        assert response.status_code == 200
        viewed = response.json()["recently_viewed"]
        assert viewed[0] == "cpeum"
        assert viewed.count("cpeum") == 1

    @patch(AUTH_PATCH)
    def test_cap_at_50(self, mock_auth):
        """PATCH caps recently_viewed at 50 entries."""
        mock_auth.return_value = (self.user, "fake-token")
        existing = [f"law-{i}" for i in range(50)]
        UserPreference.objects.create(
            janua_user_id="test-user-1", recently_viewed=existing
        )

        response = self.client.patch(self.url, {"law_id": "new-law"}, format="json")

        assert response.status_code == 200
        viewed = response.json()["recently_viewed"]
        assert len(viewed) == 50
        assert viewed[0] == "new-law"
        # Last one from original list should be dropped
        assert "law-49" not in viewed

    @patch(AUTH_PATCH)
    def test_missing_law_id(self, mock_auth):
        """PATCH without law_id returns 400."""
        mock_auth.return_value = (self.user, "fake-token")

        response = self.client.patch(self.url, {}, format="json")

        assert response.status_code == 400

    def test_unauthenticated(self):
        """PATCH without auth returns 401."""
        response = self.client.patch(self.url, {"law_id": "cpeum"}, format="json")
        assert response.status_code == 401
