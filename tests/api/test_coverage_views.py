"""Tests for the public coverage API endpoint."""

import uuid
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import Law

REGISTRY_PATCH = "apps.api.coverage_views._load_universe_registry"


def _fake_registry():
    """Minimal universe registry for testing."""
    return {
        "version": "2026-03-01",
        "last_updated": "2026-03-01T00:00:00Z",
        "sources": {
            "federal_leyes_vigentes": {"known_count": 336},
            "federal_reglamentos": {"known_count": 150},
            "federal_noms": {"known_count": 4000, "scraped_count": 413},
            "state_legislativo": {"known_count": 12120, "scraped_count": 12468},
            "state_non_legislativo": {"known_count": 23660, "scraped_count": 18439},
            "international_treaties": {"known_count": 1500, "scraped_count": 1170},
            "conamer_cnartys": {"known_count": 113373, "scraped_count": 0},
            "judicial_jurisprudencia": {"known_count": 60000},
            "judicial_tesis_aisladas": {"known_count": 440000},
        },
    }


@pytest.mark.django_db
class TestPublicCoverage:
    """Tests for GET /coverage/"""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("public-coverage")

    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_returns_200(self, mock_registry):
        response = self.client.get(self.url)
        assert response.status_code == 200

    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_response_structure(self, mock_registry):
        response = self.client.get(self.url)
        data = response.json()

        expected_keys = {
            "total_laws",
            "total_items",
            "total_universe",
            "overall_pct",
            "tiers",
            "last_updated",
            "version",
        }
        assert set(data.keys()) == expected_keys

    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_tier_structure(self, mock_registry):
        response = self.client.get(self.url)
        data = response.json()

        assert isinstance(data["tiers"], list)
        assert len(data["tiers"]) > 0

        required_fields = {"id", "name", "have", "universe", "pct", "color"}
        for tier in data["tiers"]:
            # Every tier must have at least these fields
            assert required_fields.issubset(set(tier.keys())), (
                f"Tier '{tier.get('id', '?')}' missing fields: "
                f"{required_fields - set(tier.keys())}"
            )

    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_tier_ids(self, mock_registry):
        """All expected tier IDs are present in the response."""
        response = self.client.get(self.url)
        data = response.json()
        tier_ids = {t["id"] for t in data["tiers"]}

        expected_ids = {
            "federal_laws",
            "federal_reglamentos",
            "noms",
            "state_legislative",
            "state_non_legislative",
            "municipal",
            "treaties",
            "conamer",
            "judicial",
        }
        assert tier_ids == expected_ids

    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_with_laws(self, mock_registry):
        """total_laws reflects actual DB law count."""
        uid = uuid.uuid4().hex[:6]
        for i in range(5):
            Law.objects.create(
                official_id=f"cov-test-{uid}-{i}",
                name=f"Ley de Cobertura {i}",
                tier="federal",
                status="vigente",
            )

        response = self.client.get(self.url)
        data = response.json()
        assert data["total_laws"] == 5

    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_version_and_last_updated(self, mock_registry):
        response = self.client.get(self.url)
        data = response.json()

        assert data["version"] == "2026-03-01"
        assert data["last_updated"] == "2026-03-01T00:00:00Z"

    @patch(REGISTRY_PATCH, return_value=None)
    def test_coverage_without_registry(self, mock_registry):
        """Endpoint still returns 200 even when universe_registry.json is missing."""
        response = self.client.get(self.url)
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == ""
        assert data["last_updated"] == ""

    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_overall_pct_is_number(self, mock_registry):
        response = self.client.get(self.url)
        data = response.json()
        assert isinstance(data["overall_pct"], (int, float))
        assert 0 <= data["overall_pct"] <= 100

    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_municipal_has_null_universe(self, mock_registry):
        """Municipal tier has unknown universe (null pct and universe)."""
        response = self.client.get(self.url)
        data = response.json()
        municipal = next(t for t in data["tiers"] if t["id"] == "municipal")
        assert municipal["universe"] is None
        assert municipal["pct"] is None
