"""
Tests for export views: tier access, quota enforcement, format generation.

Covers:
  - TXT export for anonymous users (allowed)
  - PDF export for anonymous users (403 forbidden)
  - Tier checking (anon cannot access premium formats)
  - Rate limit / quota enforcement (429)
  - Non-existent law returns 404
  - Empty articles returns 404
  - Quota info endpoint
"""

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import ExportLog, Law, LawVersion


@pytest.mark.django_db
class TestExportTxtAnonymous:
    """TXT export should be available to anonymous (unauthenticated) users."""

    def setup_method(self):
        self.client = APIClient()
        self.law_id = f"fed_export_{uuid.uuid4().hex[:8]}"
        self.law = Law.objects.create(
            official_id=self.law_id,
            name="Ley de Prueba Export",
            tier="federal",
            category="ley",
            status="vigente",
        )
        LawVersion.objects.create(
            law=self.law,
            publication_date=date(2024, 6, 1),
            dof_url="http://dof.gob.mx/example",
        )

    @patch("apps.api.export_views.es_client")
    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_txt_export_anonymous_success(self, mock_auth_cls, mock_es):
        """Anonymous user can download TXT export."""
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = None
        mock_auth_cls.return_value = mock_auth

        mock_es.ping.return_value = True
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "article": "1",
                            "text": "Primer articulo de la ley.",
                        }
                    },
                    {
                        "_source": {
                            "article": "2",
                            "text": "Segundo articulo de la ley.",
                        }
                    },
                ]
            }
        }

        url = reverse("law-export-txt", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert response["Content-Type"] == "text/plain; charset=utf-8"
        assert "attachment" in response["Content-Disposition"]
        assert ".txt" in response["Content-Disposition"]

        content = response.content.decode("utf-8")
        assert "Ley de Prueba Export" in content
        assert "Primer articulo de la ley." in content
        assert "Segundo articulo de la ley." in content
        assert "Tezca" in content

    @patch("apps.api.export_views.es_client")
    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_txt_export_logs_export(self, mock_auth_cls, mock_es):
        """TXT export creates an ExportLog record."""
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = None
        mock_auth_cls.return_value = mock_auth

        mock_es.ping.return_value = True
        mock_es.search.return_value = {
            "hits": {"hits": [{"_source": {"article": "1", "text": "Contenido."}}]}
        }

        url = reverse("law-export-txt", args=[self.law_id])
        self.client.get(url)

        logs = ExportLog.objects.filter(law_id=self.law_id, format="txt")
        assert logs.count() == 1
        assert logs.first().tier == "anon"


@pytest.mark.django_db
class TestExportPdfAnonymous:
    """PDF export requires at least 'free' tier -- anonymous users get 403."""

    def setup_method(self):
        self.client = APIClient()
        self.law_id = f"fed_pdf_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=self.law_id,
            name="Ley PDF Test",
            tier="federal",
            category="ley",
        )

    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_pdf_export_anonymous_returns_403(self, mock_auth_cls):
        """Anonymous user cannot access PDF export."""
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = None
        mock_auth_cls.return_value = mock_auth

        url = reverse("law-export-pdf", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403
        assert "Authentication required" in response.data["error"]
        assert response.data["required_tier"] == "free"


@pytest.mark.django_db
class TestExportTierAccess:
    """Tier-based access control for all export formats."""

    def setup_method(self):
        self.client = APIClient()
        self.law_id = f"fed_tier_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=self.law_id,
            name="Ley Tier Test",
            tier="federal",
            category="ley",
        )

    def _mock_auth_with_tier(self, mock_auth_cls, tier, user_id="user-123"):
        """Helper to configure auth mock for a specific tier."""
        from apps.api.middleware.janua_auth import JanuaUser

        mock_user = JanuaUser({"sub": user_id, "tier": tier})
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = (mock_user, "fake-token")
        mock_auth_cls.return_value = mock_auth

    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_anon_cannot_access_latex(self, mock_auth_cls):
        """Anonymous user cannot access LaTeX (premium format)."""
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = None
        mock_auth_cls.return_value = mock_auth

        url = reverse("law-export-latex", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403

    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_anon_cannot_access_docx(self, mock_auth_cls):
        """Anonymous user cannot access DOCX (premium format)."""
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = None
        mock_auth_cls.return_value = mock_auth

        url = reverse("law-export-docx", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403

    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_anon_cannot_access_epub(self, mock_auth_cls):
        """Anonymous user cannot access EPUB (premium format)."""
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = None
        mock_auth_cls.return_value = mock_auth

        url = reverse("law-export-epub", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403

    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_anon_cannot_access_json(self, mock_auth_cls):
        """Anonymous user cannot access JSON (premium format)."""
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = None
        mock_auth_cls.return_value = mock_auth

        url = reverse("law-export-json", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403

    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_free_cannot_access_premium_format(self, mock_auth_cls):
        """Free-tier user cannot access premium-only formats (latex, docx, epub, json)."""
        self._mock_auth_with_tier(mock_auth_cls, "free")

        url = reverse("law-export-latex", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403
        assert response.data["your_tier"] == "free"
        assert response.data["required_tier"] == "premium"

    @patch("apps.api.export_views.es_client")
    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_free_can_access_txt(self, mock_auth_cls, mock_es):
        """Free-tier user can access TXT."""
        self._mock_auth_with_tier(mock_auth_cls, "free")

        mock_es.ping.return_value = True
        mock_es.search.return_value = {
            "hits": {"hits": [{"_source": {"article": "1", "text": "Contenido."}}]}
        }

        url = reverse("law-export-txt", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 200


@pytest.mark.django_db
class TestExportQuotaEnforcement:
    """Rate limit / quota enforcement returns 429 when limit exceeded."""

    def setup_method(self):
        self.client = APIClient()
        self.law_id = f"fed_quota_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=self.law_id,
            name="Ley Quota Test",
            tier="federal",
            category="ley",
        )

    @patch("apps.api.export_views.check_export_quota")
    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_rate_limit_exceeded_returns_429(self, mock_auth_cls, mock_check):
        """When quota is exhausted, export returns 429 with Retry-After."""
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = None
        mock_auth_cls.return_value = mock_auth

        mock_check.return_value = (False, 1800)

        url = reverse("law-export-txt", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 429
        assert "Rate limit exceeded" in response.data["error"]
        assert response.data["retry_after"] == 1800
        assert response["Retry-After"] == "1800"

    @patch("apps.api.export_views.es_client")
    @patch("apps.api.export_views.check_export_quota")
    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_within_quota_succeeds(self, mock_auth_cls, mock_check, mock_es):
        """When within quota, export proceeds normally."""
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = None
        mock_auth_cls.return_value = mock_auth

        mock_check.return_value = (True, 0)

        mock_es.ping.return_value = True
        mock_es.search.return_value = {
            "hits": {"hits": [{"_source": {"article": "1", "text": "Contenido."}}]}
        }

        url = reverse("law-export-txt", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 200


@pytest.mark.django_db
class TestExportNotFound:
    """Export views return 404 for non-existent laws and empty articles."""

    def setup_method(self):
        self.client = APIClient()

    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_nonexistent_law_returns_404(self, mock_auth_cls):
        """Requesting export for a law that does not exist returns 404."""
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = None
        mock_auth_cls.return_value = mock_auth

        url = reverse("law-export-txt", args=["nonexistent_law_id"])
        response = self.client.get(url)

        assert response.status_code == 404

    @patch("apps.api.export_views.es_client")
    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_empty_articles_returns_404(self, mock_auth_cls, mock_es):
        """Law exists but has no articles in ES returns 404."""
        law_id = f"fed_empty_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=law_id,
            name="Ley Sin Articulos",
            tier="federal",
            category="ley",
        )

        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = None
        mock_auth_cls.return_value = mock_auth

        mock_es.ping.return_value = True
        mock_es.search.return_value = {"hits": {"hits": []}}

        url = reverse("law-export-txt", args=[law_id])
        response = self.client.get(url)

        assert response.status_code == 404
        assert "No articles found" in response.data["error"]

    @patch("apps.api.export_views.es_client")
    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_es_unavailable_returns_404(self, mock_auth_cls, mock_es):
        """When ES is unavailable (ping fails), _get_articles returns [] -> 404."""
        law_id = f"fed_esdown_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=law_id,
            name="Ley ES Down",
            tier="federal",
            category="ley",
        )

        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = None
        mock_auth_cls.return_value = mock_auth

        mock_es.ping.return_value = False

        url = reverse("law-export-txt", args=[law_id])
        response = self.client.get(url)

        assert response.status_code == 404


@pytest.mark.django_db
class TestExportQuotaEndpoint:
    """Tests for the /laws/{id}/export/quota/ endpoint."""

    def setup_method(self):
        self.client = APIClient()
        self.law_id = f"fed_quotainfo_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=self.law_id,
            name="Ley Quota Info",
            tier="federal",
            category="ley",
        )

    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_quota_endpoint_anonymous(self, mock_auth_cls):
        """Anonymous user sees anon tier and TXT-only format."""
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = None
        mock_auth_cls.return_value = mock_auth

        url = reverse("law-export-quota", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.data["tier"] == "anon"
        assert response.data["limit"] == 10
        assert "txt" in response.data["formats_available"]
        assert "pdf" not in response.data["formats_available"]

    @patch("apps.api.export_views.JanuaJWTAuthentication")
    def test_quota_endpoint_premium(self, mock_auth_cls):
        """Premium user sees all formats available."""
        from apps.api.middleware.janua_auth import JanuaUser

        mock_user = JanuaUser({"sub": "premium-user", "tier": "premium"})
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = (mock_user, "fake-token")
        mock_auth_cls.return_value = mock_auth

        url = reverse("law-export-quota", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.data["tier"] == "premium"
        assert response.data["limit"] == 100
        assert set(response.data["formats_available"]) == {
            "txt",
            "pdf",
            "latex",
            "docx",
            "epub",
            "json",
        }
