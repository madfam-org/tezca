"""Article listings expose ``kind`` so transitorios are distinguishable (#222)."""

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import Law


@pytest.mark.django_db
@patch("apps.api.law_views.es_client")
def test_law_articles_reports_kind_and_orders_transitorios_last(mock_es):
    Law.objects.create(official_id="lfpdppp", name="LFPDPPP", status="vigente")
    mock_es.count.return_value = {"count": 5}
    mock_es.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "article": "T-R2-1",
                        "text": "Reforma",
                        "is_transitorio": True,
                    }
                },
                {
                    "_source": {
                        "article": "T-8",
                        "text": "Octavo",
                        "is_transitorio": True,
                    }
                },
                {
                    "_source": {
                        "article": "8",
                        "text": "Consentimiento expreso",
                        "is_transitorio": False,
                    }
                },
                {"_source": {"article": "10", "text": "Calidad"}},
                # Indexed before the flag existed: kind falls back to the id.
                {"_source": {"article": "T-1", "text": "Vigencia"}},
            ]
        }
    }

    response = APIClient().get(reverse("law-articles", args=["lfpdppp"]))

    assert response.status_code == 200
    articles = response.json()["articles"]
    assert [(a["article_id"], a["kind"]) for a in articles] == [
        ("8", "articulo"),
        ("10", "articulo"),
        ("T-1", "transitorio"),
        ("T-8", "transitorio"),
        ("T-R2-1", "transitorio"),
    ]
