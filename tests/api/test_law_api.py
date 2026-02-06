import json
import os
import tempfile
import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import CrossReference, Law, LawVersion


@pytest.mark.django_db
class TestLawApi:
    def setup_method(self):
        self.client = APIClient()

        # Create unique IDs for isolation
        self.fed_id = f"federal_law_{uuid.uuid4().hex[:8]}"
        self.state_id = f"colima_civil_{uuid.uuid4().hex[:8]}"

        # Create test laws
        self.law_federal = Law.objects.create(
            official_id=self.fed_id, name="Ley Federal", tier="federal", category="ley"
        )
        LawVersion.objects.create(
            law=self.law_federal,
            publication_date=date(2024, 1, 1),
            dof_url="http://dof.gob.mx/nota_detalle.php?codigo=123",
        )

        self.law_state = Law.objects.create(
            official_id=self.state_id,
            name="Codigo Civil de Colima",
            tier="state",
            category="codigo",
        )

    def test_law_detail(self):
        """Test retrieving law detail metadata."""
        url = reverse("law-detail", args=[self.law_federal.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.data["id"] == self.fed_id
        assert (
            response.data["versions"][0]["dof_url"]
            == "http://dof.gob.mx/nota_detalle.php?codigo=123"
        )

    def test_law_detail_not_found(self):
        """Test 404 for non-existent law."""
        url = reverse("law-detail", args=["nonexistent"])
        response = self.client.get(url)
        assert response.status_code == 404

    def test_law_detail_state_extraction(self):
        """Test that state name is extracted from official_id."""
        url = reverse("law-detail", args=[self.law_state.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.data["state"] == "Colima"

    @patch("apps.api.law_views.Elasticsearch")
    def test_law_articles(self, mock_es_class):
        """Test retrieving law articles."""
        # Mock Elasticsearch response
        mock_es = mock_es_class.return_value
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"article": "1", "text": "Articulo 1..."}},
                    {"_source": {"article": "2", "text": "Articulo 2..."}},
                ]
            }
        }

        url = reverse("law-articles", args=[self.law_federal.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.data["total"] == 2
        assert response.data["articles"][0]["article_id"] == "1"
        assert len(response.data["articles"]) == 2

        # Verify ES call
        mock_es_class.assert_called_once()

    def test_states_list(self):
        """Test verifying state list generation."""
        # ensure we have at least one state law from setup
        url = reverse("states-list")
        response = self.client.get(url)

        assert response.status_code == 200
        assert "states" in response.data
        assert "Colima" in response.data["states"]

    # ---------------------------------------------------------------
    # New tests: Ingestion, Search, Structure, LawList, CrossReferences
    # ---------------------------------------------------------------

    @patch("apps.api.ingestion_manager.IngestionManager.start_ingestion")
    def test_ingestion_start(self, mock_start):
        """Test POST /ingest/ starts ingestion and returns 202."""
        mock_start.return_value = (True, "Job started")

        url = reverse("ingest")
        response = self.client.post(url, {}, format="json")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "started"
        assert data["message"] == "Job started"
        mock_start.assert_called_once()

    @patch("apps.api.ingestion_manager.IngestionManager.start_ingestion")
    def test_ingestion_conflict(self, mock_start):
        """Test POST /ingest/ returns 409 when ingestion is already running."""
        mock_start.return_value = (False, "Already running")

        url = reverse("ingest")
        response = self.client.post(url, {}, format="json")

        assert response.status_code == 409
        data = response.json()
        assert data["status"] == "error"
        assert data["message"] == "Already running"

    def test_search_empty_query(self):
        """Test GET /search/ with no q param returns empty results."""
        url = reverse("search")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["total"] == 0

    @patch("apps.api.search_views.Elasticsearch")
    def test_search_with_results(self, mock_es_class):
        """Test GET /search/?q=articulo returns paginated results."""
        mock_es = mock_es_class.return_value
        mock_es.ping.return_value = True
        mock_es.search.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_id": "doc-1",
                        "_score": 5.2,
                        "_source": {
                            "law_id": self.fed_id,
                            "law_name": "Ley Federal",
                            "article": "1",
                            "text": "Articulo primero sobre derechos.",
                            "publication_date": "2024-01-01",
                            "state": None,
                            "municipality": None,
                            "hierarchy": ["Titulo Primero"],
                            "book": None,
                            "title": "Titulo Primero",
                            "chapter": None,
                        },
                        "highlight": {
                            "text": ["<em>Articulo</em> primero sobre derechos."]
                        },
                    },
                    {
                        "_id": "doc-2",
                        "_score": 3.1,
                        "_source": {
                            "law_id": self.fed_id,
                            "law_name": "Ley Federal",
                            "article": "2",
                            "text": "Articulo segundo sobre obligaciones.",
                            "publication_date": "2024-01-01",
                            "state": None,
                            "municipality": None,
                            "hierarchy": ["Titulo Primero"],
                            "book": None,
                            "title": "Titulo Primero",
                            "chapter": None,
                        },
                        "highlight": {
                            "text": ["<em>Articulo</em> segundo sobre obligaciones."]
                        },
                    },
                ],
            }
        }

        url = reverse("search")
        response = self.client.get(url, {"q": "articulo"})

        assert response.status_code == 200
        data = response.json()

        # Verify pagination structure
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total_pages"] == 1
        assert len(data["results"]) == 2

        # Verify result item structure
        first = data["results"][0]
        assert first["id"] == "doc-1"
        assert first["law_id"] == self.fed_id
        assert first["law_name"] == "Ley Federal"
        assert first["article"] == "Art. 1"
        assert "snippet" in first
        assert first["score"] == 5.2

        # Verify ES was queried
        mock_es_class.assert_called_once()
        mock_es.ping.assert_called_once()
        mock_es.search.assert_called_once()

    @patch("apps.api.law_views.Elasticsearch")
    def test_law_structure_natural_sort(self, mock_es_class):
        """Test GET /laws/{id}/structure/ builds sorted tree from hierarchy."""
        mock_es = mock_es_class.return_value
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "hierarchy": ["Titulo Primero", "Capitulo II"],
                            "article": "3",
                            "text": "Art 3...",
                        }
                    },
                    {
                        "_source": {
                            "hierarchy": ["Titulo Primero", "Capitulo I"],
                            "article": "1",
                            "text": "Art 1...",
                        }
                    },
                    {
                        "_source": {
                            "hierarchy": ["Titulo Primero", "Capitulo I"],
                            "article": "2",
                            "text": "Art 2...",
                        }
                    },
                    {
                        "_source": {
                            "hierarchy": ["Titulo Segundo", "Capitulo I"],
                            "article": "10",
                            "text": "Art 10...",
                        }
                    },
                    {
                        "_source": {
                            "hierarchy": ["Titulo Primero", "Capitulo X"],
                            "article": "9",
                            "text": "Art 9...",
                        }
                    },
                ]
            }
        }

        url = reverse("law-structure", args=[self.law_federal.official_id])
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["law_id"] == self.law_federal.official_id

        structure = data["structure"]
        assert len(structure) == 2

        # Natural sort: Titulo Primero before Titulo Segundo
        assert structure[0]["label"] == "Titulo Primero"
        assert structure[1]["label"] == "Titulo Segundo"

        # Children of Titulo Primero should be naturally sorted
        children = structure[0]["children"]
        assert len(children) == 3
        assert children[0]["label"] == "Capitulo I"
        assert children[1]["label"] == "Capitulo II"
        assert children[2]["label"] == "Capitulo X"

        # Titulo Segundo has one child
        assert len(structure[1]["children"]) == 1
        assert structure[1]["children"][0]["label"] == "Capitulo I"

    def test_law_list(self):
        """Test GET /laws/ returns all laws sorted by official_id."""
        # Create additional law for testing sort order
        law_alpha = Law.objects.create(
            official_id="alpha_law",
            name="Alpha Law",
            tier="federal",
            category="ley",
        )
        LawVersion.objects.create(
            law=law_alpha,
            publication_date=date(2024, 6, 15),
        )

        url = reverse("law-list")
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()

        # Should contain all laws (2 from setup + 1 new)
        assert len(data) == 3

        # Verify sorted by official_id
        ids = [item["id"] for item in data]
        assert ids == sorted(ids)

        # Verify item structure
        first = data[0]
        assert "id" in first
        assert "name" in first
        assert "versions" in first

        # Verify alpha_law has 1 version
        alpha_item = next(item for item in data if item["id"] == "alpha_law")
        assert alpha_item["versions"] == 1

    def test_article_cross_references(self):
        """Test GET /laws/{id}/articles/{art}/references/ returns outgoing and incoming."""
        # NOTE: The URL pattern uses <str:law_id> but the view function parameter
        # is named law_slug. If this test fails with a 500, it indicates the
        # parameter name mismatch needs to be resolved in urls.py or the view.

        law_slug = "amparo"
        Law.objects.create(
            official_id=law_slug,
            name="Ley de Amparo",
            tier="federal",
            category="ley",
        )

        # Create outgoing reference: amparo art 107 -> cpeum art 103
        CrossReference.objects.create(
            source_law_slug="amparo",
            source_article_id="107",
            target_law_slug="cpeum",
            target_article_num="103",
            reference_text="conforme al articulo 103 de la Constitucion",
            confidence=0.95,
            start_position=10,
            end_position=55,
        )

        # Create incoming reference: cpeum art 103 -> amparo art 107
        CrossReference.objects.create(
            source_law_slug="cpeum",
            source_article_id="103",
            target_law_slug="amparo",
            target_article_num="107",
            reference_text="en los terminos de la Ley de Amparo articulo 107",
            confidence=0.90,
            start_position=20,
            end_position=70,
        )

        url = reverse("article-references", args=["amparo", "107"])
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()

        # Verify outgoing references
        assert data["total_outgoing"] == 1
        outgoing = data["outgoing"]
        assert len(outgoing) == 1
        assert outgoing[0]["targetLawSlug"] == "cpeum"
        assert outgoing[0]["targetArticle"] == "103"
        assert outgoing[0]["confidence"] == 0.95
        assert "targetUrl" in outgoing[0]

        # Verify incoming references
        assert data["total_incoming"] == 1
        incoming = data["incoming"]
        assert len(incoming) == 1
        assert incoming[0]["sourceLawSlug"] == "cpeum"
        assert incoming[0]["sourceArticle"] == "103"
        assert incoming[0]["confidence"] == 0.90

    @patch("apps.api.law_views.Elasticsearch")
    @patch("apps.api.law_views.REGISTRY_PATH")
    def test_stats_coverage_field(self, mock_registry_path, mock_es_class):
        """Test that /stats/ returns the coverage breakdown from universe registry."""
        # Create a temp registry file
        registry = {
            "version": "1.0",
            "sources": {
                "federal_leyes_vigentes": {
                    "known_count": 336,
                    "source_name": "Camara de Diputados",
                    "last_verified": "2026-02-03",
                },
                "state_legislativo": {
                    "known_count": 12120,
                    "source_name": "OJN - Poder Legislativo",
                    "permanent_gaps": 782,
                },
                "state_non_legislativo": {"known_count": 23660},
                "municipal": {
                    "known_count": None,
                    "cities_covered": 5,
                    "total_municipalities": 2468,
                },
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(registry, f)
            tmp_path = f.name

        try:
            # Patch the registry path and clear cache
            mock_registry_path.__str__ = lambda self: tmp_path
            import apps.api.law_views as lv

            original_path = lv.REGISTRY_PATH
            lv.REGISTRY_PATH = tmp_path
            lv._registry_cache["data"] = None
            lv._registry_cache["mtime"] = 0

            mock_es = mock_es_class.return_value
            mock_es.ping.return_value = True
            mock_es.count.return_value = {"count": 500000}

            url = reverse("law-stats")
            response = self.client.get(url)

            assert response.status_code == 200
            data = response.json()

            # Legacy fields still present
            assert "total_laws" in data
            assert "federal_coverage" in data

            # New coverage field present
            assert "coverage" in data
            cov = data["coverage"]
            assert "leyes_vigentes" in cov
            assert "federal" in cov
            assert "state" in cov
            assert "municipal" in cov

            # Federal coverage
            assert cov["federal"]["universe"] == 336
            assert cov["federal"]["source"] == "Camara de Diputados"

            # State coverage
            assert cov["state"]["universe"] == 12120
            assert cov["state"]["permanent_gaps"] == 782

            # Municipal has no universe
            assert cov["municipal"]["universe"] is None
            assert cov["municipal"]["percentage"] is None
            assert cov["municipal"]["cities_covered"] == 5

            # Leyes vigentes = federal + state
            assert cov["leyes_vigentes"]["universe"] == 336 + 12120
        finally:
            lv.REGISTRY_PATH = original_path
            lv._registry_cache["data"] = None
            os.unlink(tmp_path)

    def test_law_cross_references(self):
        """Test GET /laws/{id}/references/ returns aggregated statistics."""
        # NOTE: Same URL parameter name mismatch caveat as article_cross_references.

        law_slug = "amparo_stats"
        Law.objects.create(
            official_id=law_slug,
            name="Ley de Amparo Stats",
            tier="federal",
            category="ley",
        )

        # Create outgoing references from amparo_stats to multiple laws
        CrossReference.objects.create(
            source_law_slug="amparo_stats",
            source_article_id="1",
            target_law_slug="cpeum",
            target_article_num="103",
            reference_text="ref to cpeum art 103",
            confidence=0.9,
            start_position=0,
            end_position=20,
        )
        CrossReference.objects.create(
            source_law_slug="amparo_stats",
            source_article_id="2",
            target_law_slug="cpeum",
            target_article_num="107",
            reference_text="ref to cpeum art 107",
            confidence=0.85,
            start_position=0,
            end_position=20,
        )
        CrossReference.objects.create(
            source_law_slug="amparo_stats",
            source_article_id="3",
            target_law_slug="ley_organica",
            target_article_num="10",
            reference_text="ref to ley organica art 10",
            confidence=0.80,
            start_position=0,
            end_position=26,
        )

        # Create incoming reference to amparo_stats from another law
        CrossReference.objects.create(
            source_law_slug="codigo_penal",
            source_article_id="50",
            target_law_slug="amparo_stats",
            target_article_num="1",
            reference_text="segun la Ley de Amparo",
            confidence=0.75,
            start_position=0,
            end_position=22,
        )

        url = reverse("law-references", args=["amparo_stats"])
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()

        stats = data["statistics"]
        assert stats["total_outgoing"] == 3
        assert stats["total_incoming"] == 1

        # Verify top referenced laws (outgoing targets)
        most_referenced = stats["most_referenced_laws"]
        assert len(most_referenced) >= 1
        # cpeum should be the most referenced with 2 references
        cpeum_entry = next(
            (item for item in most_referenced if item["slug"] == "cpeum"), None
        )
        assert cpeum_entry is not None
        assert cpeum_entry["count"] == 2

        # Verify citing laws (incoming sources)
        most_citing = stats["most_citing_laws"]
        assert len(most_citing) == 1
        assert most_citing[0]["slug"] == "codigo_penal"
        assert most_citing[0]["count"] == 1


@pytest.mark.django_db
class TestMunicipalitiesList:
    def setup_method(self):
        self.client = APIClient()

    def test_empty_when_no_municipal_laws(self):
        """Returns empty list when no laws have municipality set."""
        Law.objects.create(
            official_id="fed_test", name="Federal Test", tier="federal", category="ley"
        )
        url = reverse("municipalities-list")
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_municipalities_with_counts(self):
        """Returns distinct municipalities with correct counts."""
        Law.objects.create(
            official_id="muni_1",
            name="Reglamento 1",
            tier="municipal",
            category="reglamento",
            municipality="Guadalajara",
            state="Jalisco",
        )
        Law.objects.create(
            official_id="muni_2",
            name="Reglamento 2",
            tier="municipal",
            category="reglamento",
            municipality="Guadalajara",
            state="Jalisco",
        )
        Law.objects.create(
            official_id="muni_3",
            name="Reglamento 3",
            tier="municipal",
            category="reglamento",
            municipality="Monterrey",
            state="Nuevo León",
        )

        url = reverse("municipalities-list")
        response = self.client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        gdl = next(m for m in data if m["municipality"] == "Guadalajara")
        assert gdl["count"] == 2
        assert gdl["state"] == "Jalisco"

        mty = next(m for m in data if m["municipality"] == "Monterrey")
        assert mty["count"] == 1

    def test_state_filter(self):
        """?state= filter narrows results to a single state."""
        Law.objects.create(
            official_id="muni_a",
            name="Reg A",
            tier="municipal",
            category="reglamento",
            municipality="Guadalajara",
            state="Jalisco",
        )
        Law.objects.create(
            official_id="muni_b",
            name="Reg B",
            tier="municipal",
            category="reglamento",
            municipality="Monterrey",
            state="Nuevo León",
        )

        url = reverse("municipalities-list")
        response = self.client.get(url, {"state": "Jalisco"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["municipality"] == "Guadalajara"
