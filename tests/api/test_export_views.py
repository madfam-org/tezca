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
  - LaTeX tier access (academic+)
  - DOCX tier access (institutional+)
  - EPUB tier access (institutional+)
  - JSON tier access and response structure
  - Error paths: missing deps, ES failures, special characters
"""

import json
import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import ExportLog, Law, LawVersion

# All tests patch CombinedAuthentication.authenticate to control the user tier.
# - anonymous: authenticate returns None → DRF assigns AnonymousUser (is_authenticated=False → tier="anon")
# - free/premium: authenticate returns (JanuaUser_with_tier, "fake-token")
AUTH_PATCH_TARGET = (
    "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"
)


def _make_anon_auth(mock_auth):
    """Configure mock so CombinedAuthentication returns None (anonymous)."""
    mock_auth.return_value = None


def _make_tier_auth(mock_auth, tier, user_id="user-123"):
    """Configure mock so CombinedAuthentication returns an authenticated user with the given tier."""
    from apps.api.middleware.janua_auth import JanuaUser

    user = JanuaUser({"sub": user_id, "tier": tier})
    user.tier = tier  # CombinedAuthentication normally sets this; replicate here
    mock_auth.return_value = (user, "fake-token")


def _mock_es_with_articles(mock_es, articles=None):
    """Configure mock ES to return articles. Defaults to a single article."""
    mock_es.ping.return_value = True
    if articles is None:
        articles = [{"_source": {"article": "1", "text": "Contenido de prueba."}}]
    mock_es.search.return_value = {"hits": {"hits": articles}}


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
    @patch(AUTH_PATCH_TARGET)
    def test_txt_export_anonymous_success(self, mock_auth, mock_es):
        """Anonymous user can download TXT export."""
        _make_anon_auth(mock_auth)

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
    @patch(AUTH_PATCH_TARGET)
    def test_txt_export_logs_export(self, mock_auth, mock_es):
        """TXT export creates an ExportLog record."""
        _make_anon_auth(mock_auth)

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

    @patch(AUTH_PATCH_TARGET)
    def test_pdf_export_anonymous_returns_403(self, mock_auth):
        """Anonymous user cannot access PDF export."""
        _make_anon_auth(mock_auth)

        url = reverse("law-export-pdf", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403
        assert "Authentication required" in response.data["error"]
        assert response.data["required_tier"] == "free_member"


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

    @patch(AUTH_PATCH_TARGET)
    def test_anon_cannot_access_latex(self, mock_auth):
        """Anonymous user cannot access LaTeX (premium format)."""
        _make_anon_auth(mock_auth)

        url = reverse("law-export-latex", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403

    @patch(AUTH_PATCH_TARGET)
    def test_anon_cannot_access_docx(self, mock_auth):
        """Anonymous user cannot access DOCX (premium format)."""
        _make_anon_auth(mock_auth)

        url = reverse("law-export-docx", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403

    @patch(AUTH_PATCH_TARGET)
    def test_anon_cannot_access_epub(self, mock_auth):
        """Anonymous user cannot access EPUB (premium format)."""
        _make_anon_auth(mock_auth)

        url = reverse("law-export-epub", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403

    @patch(AUTH_PATCH_TARGET)
    def test_anon_cannot_access_json(self, mock_auth):
        """Anonymous user cannot access JSON (premium format)."""
        _make_anon_auth(mock_auth)

        url = reverse("law-export-json", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403

    @patch(AUTH_PATCH_TARGET)
    def test_free_cannot_access_premium_format(self, mock_auth):
        """Free-tier user cannot access premium-only formats (latex, docx, epub, json)."""
        _make_tier_auth(mock_auth, "free")

        url = reverse("law-export-latex", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403
        assert response.data["your_tier"] == "essentials"
        assert response.data["required_tier"] == "academic"

    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_free_can_access_txt(self, mock_auth, mock_es):
        """Free-tier user can access TXT."""
        _make_tier_auth(mock_auth, "free")

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
    @patch(AUTH_PATCH_TARGET)
    def test_rate_limit_exceeded_returns_429(self, mock_auth, mock_check):
        """When quota is exhausted, export returns 429 with Retry-After."""
        _make_anon_auth(mock_auth)

        mock_check.return_value = (False, 1800)

        url = reverse("law-export-txt", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 429
        assert "Rate limit exceeded" in response.data["error"]
        assert response.data["retry_after"] == 1800
        assert response["Retry-After"] == "1800"

    @patch("apps.api.export_views.es_client")
    @patch("apps.api.export_views.check_export_quota")
    @patch(AUTH_PATCH_TARGET)
    def test_within_quota_succeeds(self, mock_auth, mock_check, mock_es):
        """When within quota, export proceeds normally."""
        _make_anon_auth(mock_auth)

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

    @patch(AUTH_PATCH_TARGET)
    def test_nonexistent_law_returns_404(self, mock_auth):
        """Requesting export for a law that does not exist returns 404."""
        _make_anon_auth(mock_auth)

        url = reverse("law-export-txt", args=["nonexistent_law_id"])
        response = self.client.get(url)

        assert response.status_code == 404

    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_empty_articles_returns_404(self, mock_auth, mock_es):
        """Law exists but has no articles in ES returns 404."""
        law_id = f"fed_empty_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=law_id,
            name="Ley Sin Articulos",
            tier="federal",
            category="ley",
        )

        _make_anon_auth(mock_auth)

        mock_es.ping.return_value = True
        mock_es.search.return_value = {"hits": {"hits": []}}

        url = reverse("law-export-txt", args=[law_id])
        response = self.client.get(url)

        assert response.status_code == 404
        assert "No articles found" in response.data["error"]

    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_es_unavailable_returns_404(self, mock_auth, mock_es):
        """When ES is unavailable (ping fails), _get_articles returns [] -> 404."""
        law_id = f"fed_esdown_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=law_id,
            name="Ley ES Down",
            tier="federal",
            category="ley",
        )

        _make_anon_auth(mock_auth)

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

    @patch(AUTH_PATCH_TARGET)
    def test_quota_endpoint_anonymous(self, mock_auth):
        """Anonymous user sees anon tier and TXT-only format."""
        _make_anon_auth(mock_auth)

        url = reverse("law-export-quota", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.data["tier"] == "anon"
        assert response.data["limit"] == 10
        assert "txt" in response.data["formats_available"]
        assert "pdf" not in response.data["formats_available"]

    @patch(AUTH_PATCH_TARGET)
    def test_quota_endpoint_premium(self, mock_auth):
        """Premium (normalized to academic) user sees academic-available formats."""
        _make_tier_auth(mock_auth, "premium", user_id="premium-user")

        url = reverse("law-export-quota", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.data["tier"] == "academic"
        assert response.data["limit"] == 60
        assert set(response.data["formats_available"]) == {
            "txt",
            "pdf",
            "json",
            "latex",
        }


# ── New test classes: format-specific tier access, JSON structure, error paths ──


@pytest.mark.django_db
class TestExportLatexAccess:
    """LaTeX export requires 'academic' tier (rank 3). Lower tiers get 403."""

    def setup_method(self):
        self.client = APIClient()
        self.law_id = f"fed_latex_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=self.law_id,
            name="Ley LaTeX Test",
            tier="federal",
            category="ley",
        )

    @patch("apps.api.export_views._has_jinja2", False)
    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_academic_can_access_latex(self, mock_auth, mock_es):
        """Academic user passes the tier gate for LaTeX. With jinja2 absent, returns 501
        (proving the 403 tier check was passed)."""
        _make_tier_auth(mock_auth, "academic")
        _mock_es_with_articles(mock_es)

        url = reverse("law-export-latex", args=[self.law_id])
        response = self.client.get(url)

        # 501 means tier check passed but jinja2 is unavailable
        assert response.status_code == 501
        assert "Jinja2" in response.data["error"]

    @patch(AUTH_PATCH_TARGET)
    def test_essentials_cannot_access_latex(self, mock_auth):
        """Essentials user (rank 2) cannot access LaTeX (requires academic, rank 3)."""
        _make_tier_auth(mock_auth, "essentials")

        url = reverse("law-export-latex", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403
        assert response.data["your_tier"] == "essentials"
        assert response.data["required_tier"] == "academic"

    @patch(AUTH_PATCH_TARGET)
    def test_free_member_cannot_access_latex(self, mock_auth):
        """Free member (rank 1) cannot access LaTeX (requires academic, rank 3)."""
        _make_tier_auth(mock_auth, "free_member")

        url = reverse("law-export-latex", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403
        assert response.data["your_tier"] == "free_member"
        assert response.data["required_tier"] == "academic"


@pytest.mark.django_db
class TestExportDocxAccess:
    """DOCX export requires 'institutional' tier (rank 4). Lower tiers get 403."""

    def setup_method(self):
        self.client = APIClient()
        self.law_id = f"fed_docx_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=self.law_id,
            name="Ley DOCX Test",
            tier="federal",
            category="ley",
        )

    @patch("apps.api.export_views._has_docx", False)
    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_institutional_can_access_docx(self, mock_auth, mock_es):
        """Institutional user passes the tier gate for DOCX. With python-docx absent,
        returns 501 (proving the 403 tier check was passed)."""
        _make_tier_auth(mock_auth, "institutional")
        _mock_es_with_articles(mock_es)

        url = reverse("law-export-docx", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 501
        assert "python-docx" in response.data["error"]

    @patch(AUTH_PATCH_TARGET)
    def test_academic_cannot_access_docx(self, mock_auth):
        """Academic user (rank 3) cannot access DOCX (requires institutional, rank 4)."""
        _make_tier_auth(mock_auth, "academic")

        url = reverse("law-export-docx", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403
        assert response.data["your_tier"] == "academic"
        assert response.data["required_tier"] == "institutional"

    @patch("apps.api.export_views._has_docx", False)
    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_docx_unavailable_returns_501(self, mock_auth, mock_es):
        """Institutional user gets 501 when python-docx is not installed."""
        _make_tier_auth(mock_auth, "institutional")
        _mock_es_with_articles(mock_es)

        url = reverse("law-export-docx", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 501
        assert "python-docx" in response.data["error"]


@pytest.mark.django_db
class TestExportEpubAccess:
    """EPUB export requires 'institutional' tier (rank 4). Lower tiers get 403."""

    def setup_method(self):
        self.client = APIClient()
        self.law_id = f"fed_epub_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=self.law_id,
            name="Ley EPUB Test",
            tier="federal",
            category="ley",
        )

    @patch("apps.api.export_views._has_ebooklib", False)
    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_institutional_can_access_epub(self, mock_auth, mock_es):
        """Institutional user passes the tier gate for EPUB. With ebooklib absent,
        returns 501 (proving the 403 tier check was passed)."""
        _make_tier_auth(mock_auth, "institutional")
        _mock_es_with_articles(mock_es)

        url = reverse("law-export-epub", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 501
        assert "ebooklib" in response.data["error"]

    @patch(AUTH_PATCH_TARGET)
    def test_academic_cannot_access_epub(self, mock_auth):
        """Academic user (rank 3) cannot access EPUB (requires institutional, rank 4)."""
        _make_tier_auth(mock_auth, "academic")

        url = reverse("law-export-epub", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403
        assert response.data["your_tier"] == "academic"
        assert response.data["required_tier"] == "institutional"

    @patch("apps.api.export_views._has_ebooklib", False)
    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_epub_unavailable_returns_501(self, mock_auth, mock_es):
        """Institutional user gets 501 when ebooklib is not installed."""
        _make_tier_auth(mock_auth, "institutional")
        _mock_es_with_articles(mock_es)

        url = reverse("law-export-epub", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 501
        assert "ebooklib" in response.data["error"]


@pytest.mark.django_db
class TestExportJsonAccess:
    """JSON export requires 'free_member' tier (rank 1). Anon users get 403."""

    def setup_method(self):
        self.client = APIClient()
        self.law_id = f"fed_json_{uuid.uuid4().hex[:8]}"
        self.law = Law.objects.create(
            official_id=self.law_id,
            name="Ley JSON Test",
            tier="federal",
            category="ley",
        )

    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_free_member_can_access_json(self, mock_auth, mock_es):
        """Free member (rank 1) can access JSON export."""
        _make_tier_auth(mock_auth, "free_member")
        _mock_es_with_articles(mock_es)

        url = reverse("law-export-json", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert "application/json" in response["Content-Type"]
        assert "attachment" in response["Content-Disposition"]
        assert ".json" in response["Content-Disposition"]

    @patch(AUTH_PATCH_TARGET)
    def test_anon_cannot_access_json(self, mock_auth):
        """Anonymous user cannot access JSON export (requires free_member)."""
        _make_anon_auth(mock_auth)

        url = reverse("law-export-json", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 403
        assert "Authentication required" in response.data["error"]
        assert response.data["required_tier"] == "free_member"

    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_json_response_structure(self, mock_auth, mock_es):
        """JSON export contains 'meta' and 'articles' top-level keys."""
        _make_tier_auth(mock_auth, "academic")
        mock_es.ping.return_value = True
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "article": "1",
                            "text": "Primer articulo.",
                        }
                    },
                    {
                        "_source": {
                            "article": "2",
                            "text": "Segundo articulo.",
                        }
                    },
                ]
            }
        }

        url = reverse("law-export-json", args=[self.law_id])
        response = self.client.get(url)

        assert response.status_code == 200

        data = json.loads(response.content.decode("utf-8"))
        assert "meta" in data
        assert "articles" in data
        assert data["meta"]["official_id"] == self.law_id
        assert data["meta"]["name"] == "Ley JSON Test"
        assert data["meta"]["article_count"] == 2
        assert len(data["articles"]) == 2
        assert data["articles"][0]["article_id"] == "1"
        assert data["articles"][1]["article_id"] == "2"


@pytest.mark.django_db
class TestExportErrorPaths:
    """Error handling paths: special characters, missing deps, ES failures."""

    def setup_method(self):
        self.client = APIClient()

    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_special_chars_in_law_id_filename(self, mock_auth, mock_es):
        """Law IDs with spaces are sanitized in the Content-Disposition filename."""
        law_id = f"fed special {uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=law_id,
            name="Ley con Caracteres Especiales",
            tier="federal",
            category="ley",
        )

        _make_anon_auth(mock_auth)
        _mock_es_with_articles(mock_es)

        url = reverse("law-export-txt", args=[law_id])
        response = self.client.get(url)

        assert response.status_code == 200
        disposition = response["Content-Disposition"]
        # Spaces replaced with underscores by _safe_filename
        assert " " not in disposition.split("filename=")[1]
        assert "_" in disposition

    @patch("apps.api.export_views._has_weasyprint", False)
    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_pdf_without_weasyprint_returns_501(self, mock_auth, mock_es):
        """PDF export returns 501 when WeasyPrint is not installed."""
        law_id = f"fed_nopdf_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=law_id,
            name="Ley No WeasyPrint",
            tier="federal",
            category="ley",
        )

        _make_tier_auth(mock_auth, "free_member")
        _mock_es_with_articles(mock_es)

        url = reverse("law-export-pdf", args=[law_id])
        response = self.client.get(url)

        assert response.status_code == 501
        assert "WeasyPrint" in response.data["error"]

    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_es_connection_error_returns_404(self, mock_auth, mock_es):
        """When ES raises an exception, _get_articles returns [] leading to 404."""
        law_id = f"fed_eserr_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=law_id,
            name="Ley ES Error",
            tier="federal",
            category="ley",
        )

        _make_tier_auth(mock_auth, "free_member")
        mock_es.ping.side_effect = Exception("Connection refused")

        url = reverse("law-export-txt", args=[law_id])
        response = self.client.get(url)

        assert response.status_code == 404

    @patch("apps.api.export_views._has_jinja2", False)
    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_latex_without_jinja2_returns_501(self, mock_auth, mock_es):
        """LaTeX export returns 501 when Jinja2 is not installed."""
        law_id = f"fed_nolatex_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=law_id,
            name="Ley No Jinja2",
            tier="federal",
            category="ley",
        )

        _make_tier_auth(mock_auth, "academic")
        _mock_es_with_articles(mock_es)

        url = reverse("law-export-latex", args=[law_id])
        response = self.client.get(url)

        assert response.status_code == 501
        assert "Jinja2" in response.data["error"]
