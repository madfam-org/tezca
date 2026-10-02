"""PDF export success path (``GET /api/v1/laws/<id>/export/pdf/``).

``tests/api/test_export_views.py`` covers access control and the 501 answer
when WeasyPrint is missing. Nothing covered the path that actually renders.
WeasyPrint 62.3 with pydyf 0.12 raised ``AttributeError`` inside
``write_pdf()``, and no test noticed. That pairing was fixed by the move to
WeasyPrint 70.0 in #263.

CI does not install the ``pdf``/``export``/``production`` extras, so WeasyPrint
itself is replaced here. The test still renders the real
``export/law_pdf.html`` template, and it checks the exact call the view makes
(``HTML(string=...).write_pdf()`` with no arguments), plus the response and the
``ExportLog`` row that feeds the export quota. The real rendering against Pango is a
manual check, described in ``docs/guides/TESTING_STRATEGY.md``.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import ExportLog, Law

AUTH_PATCH_TARGET = (
    "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"
)
FAKE_PDF = b"%PDF-1.7\n% tezca test\n"


def _free_member(mock_auth, user_id="user-pdf"):
    from apps.api.middleware.janua_auth import JanuaUser

    user = JanuaUser({"sub": user_id, "tier": "free_member"})
    user.tier = "free_member"
    mock_auth.return_value = (user, "fake-token")


@pytest.mark.django_db
class TestExportPdfRender:
    def setup_method(self):
        self.client = APIClient()

    @patch("apps.api.export_views.WeasyHTML", create=True)
    @patch("apps.api.export_views._has_weasyprint", True)
    @patch("apps.api.export_views.es_client")
    @patch(AUTH_PATCH_TARGET)
    def test_renders_template_and_returns_pdf(self, mock_auth, mock_es, mock_weasy):
        law_id = f"fed_pdf_{uuid.uuid4().hex[:8]}"
        Law.objects.create(
            official_id=law_id,
            name="Ley de Prueba PDF",
            tier="federal",
            category="ley",
        )
        _free_member(mock_auth)
        mock_es.ping.return_value = True
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"article": "1", "text": "Primer <artículo>."}},
                    {"_source": {"article": "2", "text": "Segundo artículo."}},
                ]
            }
        }
        document = MagicMock()
        document.write_pdf.return_value = FAKE_PDF
        mock_weasy.return_value = document

        response = self.client.get(reverse("law-export-pdf", args=[law_id]))

        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert response["Content-Disposition"] == f'attachment; filename="{law_id}.pdf"'
        assert response.content == FAKE_PDF

        # The view hands WeasyPrint the rendered template, keyword-only.
        mock_weasy.assert_called_once()
        args, kwargs = mock_weasy.call_args
        assert args == ()
        html = kwargs["string"]
        assert "Ley de Prueba PDF" in html
        assert "Segundo artículo." in html
        # Article text is escaped by the template, never injected as markup.
        assert "<artículo>" not in html
        assert "&lt;artículo&gt;" in html
        document.write_pdf.assert_called_once_with()

        assert ExportLog.objects.filter(law_id=law_id, format="pdf").count() == 1
