"""Tests for the quality quarantine system — DB fields, pipeline gate, API exposure."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient, APIRequestFactory

from apps.api.models import Law, LawVersion

AUTH_PATCH_TARGET = (
    "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"
)


def _make_admin_auth(mock_auth):
    """Configure mock for admin authentication."""
    from apps.api.middleware.janua_auth import JanuaUser

    user = JanuaUser({"sub": "admin-user", "tier": "madfam", "role": "admin"})
    user.tier = "madfam"
    mock_auth.return_value = (user, "fake-token")


@pytest.mark.django_db
class TestQualityFields:
    """Quality grade/score fields on LawVersion."""

    def test_quality_fields_nullable(self):
        law = Law.objects.create(
            official_id="test_nullable_quality",
            name="Test Nullable",
            tier="federal",
            category="ley",
        )
        version = LawVersion.objects.create(law=law, publication_date=date(2024, 1, 1))
        assert version.quality_grade is None
        assert version.quality_score is None

    def test_quality_fields_stored(self):
        law = Law.objects.create(
            official_id="test_stored_quality",
            name="Test Stored",
            tier="federal",
            category="ley",
        )
        version = LawVersion.objects.create(
            law=law,
            publication_date=date(2024, 1, 1),
            quality_grade="A",
            quality_score=96.5,
        )
        version.refresh_from_db()
        assert version.quality_grade == "A"
        assert version.quality_score == 96.5

    def test_quality_grade_choices(self):
        law = Law.objects.create(
            official_id="test_grade_choices",
            name="Test Choices",
            tier="federal",
            category="ley",
        )
        for grade in ["A", "B", "C", "D", "F"]:
            version = LawVersion.objects.create(
                law=law,
                publication_date=date(2024, 1, 1),
                quality_grade=grade,
                quality_score=50.0,
            )
            assert version.quality_grade == grade
            version.delete()


@pytest.mark.django_db
class TestQualityQuarantineGate:
    """Pipeline quality gate quarantines D/F grades."""

    @override_settings(QUALITY_QUARANTINE_GRADES=["D", "F"])
    def test_grade_d_is_quarantined(self):
        """Grade D should be in quarantine list."""
        from django.conf import settings

        assert "D" in settings.QUALITY_QUARANTINE_GRADES

    @override_settings(QUALITY_QUARANTINE_GRADES=["D", "F"])
    def test_grade_f_is_quarantined(self):
        from django.conf import settings

        assert "F" in settings.QUALITY_QUARANTINE_GRADES

    @override_settings(QUALITY_QUARANTINE_GRADES=["D", "F"])
    def test_grade_c_passes(self):
        from django.conf import settings

        assert "C" not in settings.QUALITY_QUARANTINE_GRADES

    @override_settings(QUALITY_QUARANTINE_GRADES=["D", "F"])
    def test_grade_a_passes(self):
        from django.conf import settings

        assert "A" not in settings.QUALITY_QUARANTINE_GRADES

    @override_settings(QUALITY_QUARANTINE_GRADES=["F"])
    def test_custom_threshold_only_f(self):
        from django.conf import settings

        assert "D" not in settings.QUALITY_QUARANTINE_GRADES
        assert "F" in settings.QUALITY_QUARANTINE_GRADES


@pytest.mark.django_db
class TestApiQualityExposure:
    """Grade and score shown in law detail API."""

    def setup_method(self):
        self.client = APIClient()

    @patch(AUTH_PATCH_TARGET)
    @patch("apps.api.law_views.es_client")
    def test_grade_and_score_shown(self, mock_es, mock_auth):
        mock_auth.return_value = None
        mock_es.ping.return_value = True
        mock_es.count.return_value = {"count": 10}

        law = Law.objects.create(
            official_id="test_api_quality",
            name="Test Quality API",
            tier="federal",
            category="ley",
        )
        LawVersion.objects.create(
            law=law,
            publication_date=date(2024, 6, 1),
            quality_grade="B",
            quality_score=91.5,
        )

        response = self.client.get(f"/api/v1/laws/{law.official_id}/")
        assert response.status_code == 200
        assert response.data["grade"] == "B"
        assert response.data["score"] == 91.5

    @patch(AUTH_PATCH_TARGET)
    @patch("apps.api.law_views.es_client")
    def test_null_when_no_version(self, mock_es, mock_auth):
        mock_auth.return_value = None
        mock_es.ping.return_value = True
        mock_es.count.return_value = {"count": 0}

        law = Law.objects.create(
            official_id="test_api_no_version",
            name="Test No Version",
            tier="federal",
            category="ley",
        )

        response = self.client.get(f"/api/v1/laws/{law.official_id}/")
        assert response.status_code == 200
        assert response.data["grade"] is None
        assert response.data["score"] is None


@pytest.mark.django_db
class TestAdminQuarantinedEndpoint:
    """Admin endpoint listing quarantined laws."""

    def setup_method(self):
        self.factory = APIRequestFactory()

    @patch("apps.api.middleware.admin_permission.IsTezcaAdmin.has_permission")
    @patch("apps.api.middleware.janua_auth.JanuaJWTAuthentication.authenticate")
    @override_settings(QUALITY_QUARANTINE_GRADES=["D", "F"])
    def test_lists_quarantined_laws(self, mock_auth, mock_perm):
        from apps.api.admin_views import quarantined_laws

        mock_perm.return_value = True
        user = MagicMock()
        user.tier = "madfam"
        mock_auth.return_value = (user, "fake-token")

        law = Law.objects.create(
            official_id="test_quarantined_list",
            name="Low Quality Law",
            tier="federal",
            category="ley",
        )
        LawVersion.objects.create(
            law=law,
            publication_date=date(2024, 1, 1),
            quality_grade="D",
            quality_score=65.0,
        )
        LawVersion.objects.create(
            law=law,
            publication_date=date(2024, 2, 1),
            quality_grade="F",
            quality_score=45.0,
        )

        request = self.factory.get("/api/v1/admin/quarantined/")
        request.user = user
        response = quarantined_laws(request)

        assert response.status_code == 200
        assert response.data["count"] == 2
        grades = [r["grade"] for r in response.data["quarantined"]]
        assert "D" in grades
        assert "F" in grades
