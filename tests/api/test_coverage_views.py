"""Tests for the public coverage API endpoint."""

import uuid
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import Law

REGISTRY_PATCH = "apps.api.coverage_views._load_universe_registry"
ES_PATCH = "apps.api.coverage_views._get_total_articles"


def _fake_registry():
    """Minimal universe registry for testing."""
    return {
        "version": "2026-03-01",
        "last_updated": "2026-03-01T00:00:00Z",
        "sources": {
            "federal_leyes_vigentes": {
                "known_count": 336,
                "scraped_count": 336,
                "confidence": "high",
            },
            "federal_reglamentos": {
                "known_count": 150,
                "scraped_count": 150,
                "confidence": "high",
            },
            "federal_noms": {
                "known_count": None,
                "scraped_count": 428,
                "confidence": "low",
            },
            "state_legislativo": {
                "known_count": 12120,
                "scraped_count": 12468,
                "confidence": "high",
            },
            "state_non_legislativo": {
                "known_count": 23660,
                "scraped_count": 19042,
                "confidence": "high",
            },
            "municipal": {
                "known_count": None,
                "scraped_count": 2439,
                "confidence": "low",
            },
            "international_treaties": {
                "known_count": 1500,
                "scraped_count": 1510,
                "confidence": "medium",
            },
            "conamer_cnartys": {
                "known_count": 113373,
                "scraped_count": 0,
                "confidence": "medium",
            },
            "judicial_jurisprudencia": {
                "known_count": 60000,
                "scraped_count": 0,
                "confidence": "high",
            },
            "judicial_tesis_aisladas": {
                "known_count": 440000,
                "scraped_count": 0,
                "confidence": "medium",
            },
        },
        "coverage_views": {
            "leyes_vigentes": {
                "label": "Leyes Legislativas Vigentes",
                "universe": 12804,
                "components": [
                    {"key": "federal_leyes_vigentes", "count_field": "scraped_count"},
                    {"key": "state_legislativo", "count_field": "scraped_count"},
                ],
            },
            "marco_juridico_completo": {
                "label": "Marco Jurídico Completo",
                "universe": 36719,
                "components": [
                    {"key": "federal_leyes_vigentes", "count_field": "scraped_count"},
                    {"key": "state_legislativo", "count_field": "scraped_count"},
                    {"key": "state_non_legislativo", "count_field": "scraped_count"},
                ],
            },
            "normatividad_primaria": {
                "label": "Normatividad Primaria (Tiers 1-4)",
                "universe": 36719,
                "components": [
                    {"key": "federal_leyes_vigentes", "count_field": "scraped_count"},
                    {"key": "state_legislativo", "count_field": "scraped_count"},
                    {"key": "state_non_legislativo", "count_field": "scraped_count"},
                    {"key": "municipal", "count_field": "scraped_count"},
                ],
            },
            "marco_juridico_total": {
                "label": "Marco Jurídico Total (All Tiers)",
                "universe": 652136,
                "components": [
                    {"key": "federal_leyes_vigentes", "count_field": "scraped_count"},
                    {"key": "state_legislativo", "count_field": "scraped_count"},
                    {"key": "state_non_legislativo", "count_field": "scraped_count"},
                    {"key": "municipal", "count_field": "scraped_count"},
                    {"key": "federal_reglamentos", "count_field": "scraped_count"},
                    {"key": "conamer_cnartys", "count_field": "scraped_count"},
                    {"key": "judicial_jurisprudencia", "count_field": "scraped_count"},
                    {"key": "judicial_tesis_aisladas", "count_field": "scraped_count"},
                    {"key": "international_treaties", "count_field": "scraped_count"},
                ],
            },
        },
    }


@pytest.mark.django_db
class TestPublicCoverage:
    """Tests for GET /coverage/"""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("public-coverage")

    @patch(ES_PATCH, return_value=3500000)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_returns_200(self, mock_registry, mock_es):
        response = self.client.get(self.url)
        assert response.status_code == 200

    @patch(ES_PATCH, return_value=3500000)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_response_structure(self, mock_registry, mock_es):
        response = self.client.get(self.url)
        data = response.json()

        expected_keys = {
            "total_laws",
            "total_items",
            "total_universe",
            "overall_pct",
            "tiers",
            "total_articles",
            "coverage_views",
            "state_coverage",
            "last_updated",
            "version",
        }
        assert set(data.keys()) == expected_keys

    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_tier_structure(self, mock_registry, mock_es):
        response = self.client.get(self.url)
        data = response.json()

        assert isinstance(data["tiers"], list)
        assert len(data["tiers"]) > 0

        required_fields = {
            "id",
            "name",
            "have",
            "universe",
            "pct",
            "color",
            "confidence",
        }
        for tier in data["tiers"]:
            assert required_fields.issubset(set(tier.keys())), (
                f"Tier '{tier.get('id', '?')}' missing fields: "
                f"{required_fields - set(tier.keys())}"
            )

    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_tier_ids(self, mock_registry, mock_es):
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

    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_with_laws(self, mock_registry, mock_es):
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

    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_version_and_last_updated(self, mock_registry, mock_es):
        response = self.client.get(self.url)
        data = response.json()

        assert data["version"] == "2026-03-01"
        assert data["last_updated"] == "2026-03-01T00:00:00Z"

    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=None)
    def test_coverage_without_registry(self, mock_registry, mock_es):
        """Endpoint still returns 200 even when universe_registry.json is missing."""
        response = self.client.get(self.url)
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == ""
        assert data["last_updated"] == ""

    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_overall_pct_is_number(self, mock_registry, mock_es):
        response = self.client.get(self.url)
        data = response.json()
        assert isinstance(data["overall_pct"], (int, float))
        assert 0 <= data["overall_pct"] <= 100

    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_municipal_has_null_universe(self, mock_registry, mock_es):
        """Municipal tier has unknown universe (null pct and universe)."""
        response = self.client.get(self.url)
        data = response.json()
        municipal = next(t for t in data["tiers"] if t["id"] == "municipal")
        assert municipal["universe"] is None
        assert municipal["pct"] is None

    # ---------------------------------------------------------------
    # NOMs fix: null universe when no census
    # ---------------------------------------------------------------
    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_noms_null_universe(self, mock_registry, mock_es):
        """NOMs tier has null universe/pct when known_count is None."""
        response = self.client.get(self.url)
        data = response.json()
        noms = next(t for t in data["tiers"] if t["id"] == "noms")
        assert noms["universe"] is None
        assert noms["pct"] is None
        assert noms["note"] is not None
        assert "censo" in noms["note"]["es"].lower()

    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_overall_pct_excludes_null_universe(self, mock_registry, mock_es):
        """overall_pct does not include NOMs or municipal (null universe)."""
        response = self.client.get(self.url)
        data = response.json()
        # Verify NOMs and municipal are excluded from total_universe
        tiers_with_universe = [t for t in data["tiers"] if t["universe"] is not None]
        expected_universe = sum(t["universe"] for t in tiers_with_universe)
        assert data["total_universe"] == expected_universe
        # NOMs and municipal should NOT be in tiers_with_universe
        null_ids = {t["id"] for t in data["tiers"] if t["universe"] is None}
        assert "noms" in null_ids
        assert "municipal" in null_ids

    # ---------------------------------------------------------------
    # Coverage views
    # ---------------------------------------------------------------
    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_views_present(self, mock_registry, mock_es):
        """Response has 4 coverage view entries."""
        response = self.client.get(self.url)
        data = response.json()
        assert "coverage_views" in data
        assert len(data["coverage_views"]) == 4
        expected_keys = {
            "leyes_vigentes",
            "marco_juridico_completo",
            "normatividad_primaria",
            "marco_juridico_total",
        }
        assert set(data["coverage_views"].keys()) == expected_keys

    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_views_pct_capped(self, mock_registry, mock_es):
        """No coverage view pct exceeds 100."""
        response = self.client.get(self.url)
        data = response.json()
        for view_key, view in data["coverage_views"].items():
            if view["pct"] is not None:
                assert (
                    view["pct"] <= 100
                ), f"View '{view_key}' has pct {view['pct']} > 100"

    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_coverage_views_have_labels(self, mock_registry, mock_es):
        """Each view has trilingual labels."""
        response = self.client.get(self.url)
        data = response.json()
        for view_key, view in data["coverage_views"].items():
            assert "label" in view
            assert "es" in view["label"]
            assert "en" in view["label"]
            assert "nah" in view["label"]

    # ---------------------------------------------------------------
    # State coverage
    # ---------------------------------------------------------------
    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_state_coverage_present(self, mock_registry, mock_es):
        """Response has state_coverage list."""
        response = self.client.get(self.url)
        data = response.json()
        assert "state_coverage" in data
        assert isinstance(data["state_coverage"], list)

    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_state_coverage_no_anomaly(self, mock_registry, mock_es):
        """No state row has anomaly key (admin-only data)."""
        response = self.client.get(self.url)
        data = response.json()
        for row in data["state_coverage"]:
            assert "anomaly" not in row

    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_state_coverage_with_laws(self, mock_registry, mock_es):
        """State laws appear in state_coverage."""
        uid = uuid.uuid4().hex[:6]
        for i in range(3):
            Law.objects.create(
                official_id=f"sc-test-{uid}-{i}",
                name=f"Ley Estatal {i}",
                tier="state",
                state="jalisco",
                status="vigente",
            )
        response = self.client.get(self.url)
        data = response.json()
        jalisco = next(
            (s for s in data["state_coverage"] if s["state"] == "Jalisco"), None
        )
        assert jalisco is not None
        assert jalisco["total"] == 3

    # ---------------------------------------------------------------
    # Confidence
    # ---------------------------------------------------------------
    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_tier_confidence_present(self, mock_registry, mock_es):
        """Each tier has a confidence key."""
        response = self.client.get(self.url)
        data = response.json()
        for tier in data["tiers"]:
            assert "confidence" in tier, f"Tier '{tier['id']}' missing confidence"

    # ---------------------------------------------------------------
    # Total articles
    # ---------------------------------------------------------------
    @patch(ES_PATCH, return_value=3500000)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_total_articles_present(self, mock_registry, mock_es):
        response = self.client.get(self.url)
        data = response.json()
        assert data["total_articles"] == 3500000

    @patch(ES_PATCH, return_value=None)
    @patch(REGISTRY_PATCH, return_value=_fake_registry())
    def test_total_articles_null_on_failure(self, mock_registry, mock_es):
        response = self.client.get(self.url)
        data = response.json()
        assert data["total_articles"] is None
