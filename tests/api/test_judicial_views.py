"""Tests for judicial record API endpoints."""

import uuid
from datetime import date

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.models import JudicialRecord


def _create_judicial_records():
    """Create a diverse set of judicial records for testing."""
    uid = uuid.uuid4().hex[:6]
    records = []

    test_data = [
        {
            "registro": f"2025001-{uid}",
            "epoca": "11a",
            "instancia": "Pleno",
            "materia": "civil",
            "tipo": "jurisprudencia",
            "rubro": "DERECHO DE PROPIEDAD. LIMITES CONSTITUCIONALES",
            "texto": "El derecho de propiedad tiene limites constitucionales...",
            "ponente": "Min. Gonzalez Alcantara",
            "fuente": "Semanario Judicial de la Federacion",
            "fecha_publicacion": date(2025, 1, 15),
        },
        {
            "registro": f"2025002-{uid}",
            "epoca": "11a",
            "instancia": "Primera Sala",
            "materia": "penal",
            "tipo": "tesis_aislada",
            "rubro": "PRESUNCION DE INOCENCIA. PRINCIPIO CONSTITUCIONAL",
            "texto": "La presuncion de inocencia es un principio rector...",
            "ponente": "Min. Pardo Rebolledo",
            "fuente": "Gaceta del Semanario",
            "fecha_publicacion": date(2025, 2, 10),
        },
        {
            "registro": f"2025003-{uid}",
            "epoca": "10a",
            "instancia": "Segunda Sala",
            "materia": "administrativa",
            "tipo": "jurisprudencia",
            "rubro": "ACTO ADMINISTRATIVO. FUNDAMENTACION Y MOTIVACION",
            "texto": "Todo acto administrativo debe estar fundado y motivado...",
            "ponente": "Min. Laynez Potisek",
            "fuente": "Semanario Judicial de la Federacion",
            "fecha_publicacion": date(2024, 11, 5),
        },
        {
            "registro": f"2025004-{uid}",
            "epoca": "11a",
            "instancia": "Tribunales Colegiados",
            "materia": "civil",
            "tipo": "tesis_aislada",
            "rubro": "CONTRATO DE ARRENDAMIENTO. CLAUSULAS ABUSIVAS",
            "texto": "Las clausulas abusivas en contratos de arrendamiento...",
            "ponente": "Mag. Torres Lopez",
            "fuente": "Semanario Judicial de la Federacion",
            "fecha_publicacion": date(2025, 3, 1),
        },
        {
            "registro": f"2025005-{uid}",
            "epoca": "10a",
            "instancia": "Pleno",
            "materia": "constitucional",
            "tipo": "jurisprudencia",
            "rubro": "DERECHOS HUMANOS. INTERPRETACION CONFORME",
            "texto": "Los derechos humanos deben interpretarse conforme...",
            "ponente": "Min. Zaldivar Lelo de Larrea",
            "fuente": "Gaceta del Semanario",
            "fecha_publicacion": date(2024, 6, 20),
        },
    ]

    for data in test_data:
        records.append(JudicialRecord.objects.create(**data))

    return records


@pytest.mark.django_db
class TestJudicialList:
    """Tests for GET /judicial/"""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("judicial-list")

    def test_judicial_list_empty(self):
        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_judicial_list_with_data(self):
        records = _create_judicial_records()
        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["results"]) == 5

    def test_judicial_list_filter_tipo(self):
        records = _create_judicial_records()
        response = self.client.get(self.url, {"tipo": "jurisprudencia"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        for item in data["results"]:
            assert item["tipo"] == "jurisprudencia"

    def test_judicial_list_filter_materia(self):
        records = _create_judicial_records()
        response = self.client.get(self.url, {"materia": "civil"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for item in data["results"]:
            assert item["materia"] == "civil"

    def test_judicial_list_filter_epoca(self):
        records = _create_judicial_records()
        response = self.client.get(self.url, {"epoca": "10a"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for item in data["results"]:
            assert item["epoca"] == "10a"

    def test_judicial_list_combined_filters(self):
        records = _create_judicial_records()
        response = self.client.get(
            self.url, {"tipo": "jurisprudencia", "materia": "civil"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["results"][0]["materia"] == "civil"
        assert data["results"][0]["tipo"] == "jurisprudencia"

    def test_judicial_list_pagination(self):
        records = _create_judicial_records()
        response = self.client.get(self.url, {"page": 1, "page_size": 2})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["results"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_judicial_list_result_shape(self):
        """List results use the light serializer (no texto field)."""
        records = _create_judicial_records()
        response = self.client.get(self.url)

        data = response.json()
        item = data["results"][0]
        expected_fields = {
            "id",
            "registro",
            "epoca",
            "instancia",
            "materia",
            "tipo",
            "rubro",
            "ponente",
            "fecha_publicacion",
        }
        assert expected_fields == set(item.keys())
        # texto should NOT be in list results
        assert "texto" not in item


@pytest.mark.django_db
class TestJudicialDetail:
    """Tests for GET /judicial/<registro>/"""

    def setup_method(self):
        self.client = APIClient()
        self.records = _create_judicial_records()

    def test_judicial_detail_found(self):
        record = self.records[0]
        url = reverse("judicial-detail", args=[record.registro])
        response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["registro"] == record.registro
        assert data["rubro"] == record.rubro
        assert data["texto"] == record.texto
        assert data["ponente"] == record.ponente

    def test_judicial_detail_not_found(self):
        url = reverse("judicial-detail", args=["nonexistent-registro-999"])
        response = self.client.get(url)

        assert response.status_code == 404
        assert "error" in response.json()

    def test_judicial_detail_full_shape(self):
        """Detail view returns the full serializer with all fields."""
        record = self.records[0]
        url = reverse("judicial-detail", args=[record.registro])
        response = self.client.get(url)

        data = response.json()
        expected_fields = {
            "id",
            "registro",
            "epoca",
            "instancia",
            "materia",
            "tipo",
            "rubro",
            "texto",
            "precedentes",
            "votos",
            "ponente",
            "fuente",
            "fecha_publicacion",
        }
        assert expected_fields == set(data.keys())


@pytest.mark.django_db
class TestJudicialSearch:
    """Tests for GET /judicial/search/"""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("judicial-search")
        self.records = _create_judicial_records()

    def test_judicial_search_success(self):
        response = self.client.get(self.url, {"q": "propiedad"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["query"] == "propiedad"
        # The word "propiedad" appears in the first record's rubro
        registros = [r["registro"] for r in data["results"]]
        assert self.records[0].registro in registros

    def test_judicial_search_missing_query(self):
        response = self.client.get(self.url)

        assert response.status_code == 400
        assert "error" in response.json()

    def test_judicial_search_empty_query(self):
        response = self.client.get(self.url, {"q": ""})

        assert response.status_code == 400

    def test_judicial_search_no_results(self):
        response = self.client.get(self.url, {"q": "xyznonexistent123"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_judicial_search_with_filters(self):
        response = self.client.get(self.url, {"q": "derecho", "tipo": "jurisprudencia"})

        assert response.status_code == 200
        data = response.json()
        for item in data["results"]:
            assert item["tipo"] == "jurisprudencia"

    def test_judicial_search_matches_texto(self):
        """Search matches text in the texto field, not just rubro."""
        response = self.client.get(self.url, {"q": "principio rector"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        registros = [r["registro"] for r in data["results"]]
        assert self.records[1].registro in registros


@pytest.mark.django_db
class TestJudicialStats:
    """Tests for GET /judicial/stats/"""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("judicial-stats")

    def test_judicial_stats_empty(self):
        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["by_tipo"] == {}
        assert data["by_materia"] == {}
        assert data["by_epoca"] == {}

    def test_judicial_stats(self):
        _create_judicial_records()
        response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5

        # by_tipo: 3 jurisprudencia, 2 tesis_aislada
        assert "by_tipo" in data
        assert data["by_tipo"]["jurisprudencia"] == 3
        assert data["by_tipo"]["tesis_aislada"] == 2

        # by_materia: 2 civil, 1 penal, 1 administrativa, 1 constitucional
        assert "by_materia" in data
        assert data["by_materia"]["civil"] == 2
        assert data["by_materia"]["penal"] == 1
        assert data["by_materia"]["administrativa"] == 1
        assert data["by_materia"]["constitucional"] == 1

        # by_epoca: 3 in 11a, 2 in 10a
        assert "by_epoca" in data
        assert data["by_epoca"]["11a"] == 3
        assert data["by_epoca"]["10a"] == 2

    def test_judicial_stats_response_shape(self):
        response = self.client.get(self.url)
        data = response.json()

        expected_keys = {"total", "by_tipo", "by_materia", "by_epoca"}
        assert set(data.keys()) == expected_keys
