"""Tests for annotation CRUD endpoints."""

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.middleware.janua_auth import JanuaUser
from apps.api.models import Annotation

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"


def _make_user(user_id="test-user-1", tier="academic"):
    user = JanuaUser({"sub": user_id, "email": f"{user_id}@test.com", "tier": tier})
    user.tier = tier
    user.scopes = ["read", "search"]
    user.allowed_domains = []
    user.api_key_prefix = ""
    return user


@pytest.mark.django_db
class TestAnnotationList:
    """Tests for GET/POST /user/annotations/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("annotation-list")
        self.user = _make_user()

    @patch(AUTH_PATCH)
    def test_list_empty(self, mock_auth):
        """GET returns empty list when user has no annotations."""
        mock_auth.return_value = (self.user, "fake-token")
        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["annotations"] == []
        assert data["page"] == 1

    @patch(AUTH_PATCH)
    def test_list_with_data(self, mock_auth):
        """GET returns annotations belonging to the authenticated user."""
        mock_auth.return_value = (self.user, "fake-token")
        Annotation.objects.create(
            janua_user_id="test-user-1",
            law_id="cpeum",
            article_id="art-1",
            text="Important note",
            color="yellow",
        )
        Annotation.objects.create(
            janua_user_id="test-user-1",
            law_id="cpeum",
            article_id="art-2",
            text="Second note",
            color="blue",
        )
        # Annotation by another user (should not appear)
        Annotation.objects.create(
            janua_user_id="other-user",
            law_id="cpeum",
            article_id="art-1",
            text="Other user note",
        )

        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["annotations"]) == 2
        assert data["annotations"][0]["text"] == "Important note"

    @patch(AUTH_PATCH)
    def test_list_filter_by_law_id(self, mock_auth):
        """GET ?law_id=X filters annotations to that law."""
        mock_auth.return_value = (self.user, "fake-token")
        Annotation.objects.create(
            janua_user_id="test-user-1",
            law_id="cpeum",
            article_id="art-1",
            text="Constitution note",
        )
        Annotation.objects.create(
            janua_user_id="test-user-1",
            law_id="lft",
            article_id="art-5",
            text="Labor note",
        )

        response = self.client.get(self.url, {"law_id": "cpeum"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["annotations"][0]["law_id"] == "cpeum"

    @patch(AUTH_PATCH)
    def test_list_pagination(self, mock_auth):
        """GET respects page and page_size parameters."""
        mock_auth.return_value = (self.user, "fake-token")
        for i in range(5):
            Annotation.objects.create(
                janua_user_id="test-user-1",
                law_id="cpeum",
                article_id=f"art-{i}",
                text=f"Note {i}",
            )

        response = self.client.get(self.url, {"page": 1, "page_size": 2})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["annotations"]) == 2
        assert data["page"] == 1

    @patch(AUTH_PATCH)
    def test_create_success(self, mock_auth):
        """POST creates a new annotation and returns 201."""
        mock_auth.return_value = (self.user, "fake-token")
        payload = {
            "law_id": "cpeum",
            "article_id": "art-27",
            "text": "Property rights annotation",
            "highlight_start": 10,
            "highlight_end": 50,
            "color": "green",
        }

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == 201
        data = response.json()
        assert data["law_id"] == "cpeum"
        assert data["article_id"] == "art-27"
        assert data["text"] == "Property rights annotation"
        assert data["color"] == "green"
        assert data["highlight_start"] == 10
        assert data["highlight_end"] == 50
        assert Annotation.objects.count() == 1

    @patch(AUTH_PATCH)
    def test_create_missing_fields(self, mock_auth):
        """POST with missing required fields returns 400."""
        mock_auth.return_value = (self.user, "fake-token")
        # Missing text
        payload = {"law_id": "cpeum", "article_id": "art-1"}

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == 400
        assert "required" in response.json()["error"].lower()

    def test_list_unauthenticated(self):
        """GET without auth returns 401."""
        response = self.client.get(self.url)
        assert response.status_code == 401

    def test_create_unauthenticated(self):
        """POST without auth returns 401."""
        payload = {"law_id": "cpeum", "article_id": "art-1", "text": "Note"}
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == 401


@pytest.mark.django_db
class TestAnnotationDetail:
    """Tests for PUT/DELETE /user/annotations/<id>/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = _make_user()

    @patch(AUTH_PATCH)
    def test_update_success(self, mock_auth):
        """PUT updates annotation text and color."""
        mock_auth.return_value = (self.user, "fake-token")
        annotation = Annotation.objects.create(
            janua_user_id="test-user-1",
            law_id="cpeum",
            article_id="art-1",
            text="Original",
            color="yellow",
        )
        url = reverse("annotation-detail", args=[annotation.id])

        response = self.client.put(
            url, {"text": "Updated", "color": "blue"}, format="json"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Updated"
        assert data["color"] == "blue"

    @patch(AUTH_PATCH)
    def test_update_not_found(self, mock_auth):
        """PUT on non-existent annotation returns 404."""
        mock_auth.return_value = (self.user, "fake-token")
        url = reverse("annotation-detail", args=[99999])

        response = self.client.put(url, {"text": "Updated"}, format="json")

        assert response.status_code == 404

    @patch(AUTH_PATCH)
    def test_update_wrong_user(self, mock_auth):
        """PUT on annotation belonging to another user returns 404."""
        mock_auth.return_value = (self.user, "fake-token")
        annotation = Annotation.objects.create(
            janua_user_id="other-user",
            law_id="cpeum",
            article_id="art-1",
            text="Other user note",
        )
        url = reverse("annotation-detail", args=[annotation.id])

        response = self.client.put(url, {"text": "Hacked"}, format="json")

        assert response.status_code == 404

    @patch(AUTH_PATCH)
    def test_delete_success(self, mock_auth):
        """DELETE removes annotation and returns 204."""
        mock_auth.return_value = (self.user, "fake-token")
        annotation = Annotation.objects.create(
            janua_user_id="test-user-1",
            law_id="cpeum",
            article_id="art-1",
            text="To delete",
        )
        url = reverse("annotation-detail", args=[annotation.id])

        response = self.client.delete(url)

        assert response.status_code == 204
        assert Annotation.objects.count() == 0

    @patch(AUTH_PATCH)
    def test_delete_not_found(self, mock_auth):
        """DELETE on non-existent annotation returns 404."""
        mock_auth.return_value = (self.user, "fake-token")
        url = reverse("annotation-detail", args=[99999])

        response = self.client.delete(url)

        assert response.status_code == 404

    def test_update_unauthenticated(self):
        """PUT without auth returns 401."""
        url = reverse("annotation-detail", args=[1])
        response = self.client.put(url, {"text": "Updated"}, format="json")
        assert response.status_code == 401
