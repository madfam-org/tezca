"""Pruebas del endpoint de artículos con vigencia (feed laboral, T-1a).

La compuerta falsable de este carril está en ``test_seed_coherencia``: el
seed que se publica tiene que cumplir invariantes que una transcripción
descuidada rompe (vigencias que se traslapan, filas ``published`` sin fuente,
artículos vacíos). Sobre ``main`` estas pruebas ni siquiera existen porque el
modelo no existe; lo que se declara es que entran con la lista de exenciones
vacía: **cero** filas del seed las incumplen.
"""

import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.fiscal_models import Provenance
from apps.api.labor_models import LawArticle
from apps.api.middleware.janua_auth import JanuaUser

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"

SEED_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "labor" / "articulos_vigentes.json"
)


def _make_user(scopes=None, tier="essentials"):
    user = JanuaUser({"sub": "labor-test", "email": "labor@test.com", "tier": tier})
    user.tier = tier
    user.scopes = ["read", "search"] if scopes is None else scopes
    user.allowed_domains = []
    user.api_key_prefix = ""
    return user


def _make_article(
    official_id="lft",
    article="59",
    text="Artículo 59.- La duración máxima de la jornada ordinaria...",
    effective_from="2026-05-01",
    effective_to=None,
    provenance=Provenance.PUBLISHED,
    derogado=False,
):
    return LawArticle.objects.create(
        official_id=official_id,
        article=article,
        text=text,
        effective_from=effective_from,
        effective_to=effective_to,
        provenance=provenance,
        derogado=derogado,
        source="Cámara de Diputados, LeyesBiblio (texto vigente)",
        source_url="https://www.diputados.gob.mx/LeyesBiblio/doc/LFT.doc",
    )


@pytest.mark.django_db
class TestArticuloVigente:
    """GET /api/v1/laws/<law_id>/articles/<article>/vigente/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = _make_user()

    def _url(self, law_id="lft", article="59"):
        return reverse(
            "law-article-vigente", kwargs={"law_id": law_id, "article": article}
        )

    def _get(self, url, user=None, **params):
        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (user or self.user, "tok")
            return self.client.get(url, params)

    def test_requires_authentication(self):
        """Sin credenciales no hay texto de ley: 401, no datos."""
        assert self.client.get(self._url()).status_code == 401

    def test_requires_read_scope(self):
        """Una llave sin scope 'read' se rechaza."""
        response = self._get(self._url(), user=_make_user(scopes=["search"]))
        assert response.status_code == 403
        assert "read" in response.json()["error"]

    def test_devuelve_el_texto_vigente_hoy(self):
        _make_article()
        response = self._get(self._url())
        assert response.status_code == 200
        data = response.json()
        assert data["official_id"] == "lft"
        assert data["article"] == "59"
        assert "jornada ordinaria" in data["text"]
        assert data["provenance"] == "published"
        assert data["is_verified"] is True

    def test_on_en_la_frontera_devuelve_la_version_de_ese_dia(self):
        """El día del cambio pertenece a la vigencia nueva, no a la vieja.

        Es exactamente la pregunta que el índice de búsqueda no puede
        contestar: qué decía el artículo 59 el 30 de abril de 2026.
        """
        _make_article(
            text="Artículo 59.- ...cuarenta y ocho horas semanales.",
            effective_from="1970-04-01",
            effective_to="2026-04-30",
        )
        _make_article(
            text="Artículo 59.- ...cuarenta horas semanales.",
            effective_from="2026-05-01",
        )

        vieja = self._get(self._url(), on="2026-04-30").json()
        assert "cuarenta y ocho" in vieja["text"]
        assert vieja["effective_to"] == "2026-04-30"

        nueva = self._get(self._url(), on="2026-05-01").json()
        assert "cuarenta horas" in nueva["text"]
        assert nueva["effective_to"] is None
        assert nueva["in_force"] is True

    def test_falla_en_claro_cuando_no_hay_version_para_la_fecha(self):
        """Antes de su primera vigencia, 404 explicado — nunca otra versión."""
        _make_article(effective_from="2026-05-01")
        response = self._get(self._url(), on="2020-01-01")
        assert response.status_code == 404
        cuerpo = response.json()
        assert cuerpo["on"] == "2020-01-01"
        assert "ninguna versión" in cuerpo["detail"]

    def test_falla_en_claro_cuando_el_articulo_no_esta_publicado(self):
        response = self._get(self._url(article="9999"))
        assert response.status_code == 404
        assert "no está publicado" in response.json()["detail"]

    def test_articulo_derogado_se_publica_como_derogado(self):
        """Un consumidor necesita saber que su base legal desapareció.

        Devolver 404 para el art. 15-A de la LFT le diría 'no sé'; lo cierto
        es que el artículo existe y dice 'Se deroga' desde el 23-04-2021.
        """
        _make_article(
            article="15-A",
            text="Artículo 15-A. Se deroga.",
            effective_from="2021-04-23",
            derogado=True,
        )
        data = self._get(self._url(article="15-A")).json()
        assert data["derogado"] is True
        assert "Se deroga" in data["text"]

    def test_fecha_invalida_es_400(self):
        response = self._get(self._url(), on="30-04-2026")
        assert response.status_code == 400

    def test_el_articulo_no_distingue_mayusculas(self):
        """'39-a' y '39-A' son el mismo artículo."""
        _make_article(article="39-A", text="Artículo 39-A. En las relaciones...")
        assert self._get(self._url(article="39-a")).status_code == 200


class TestSeedCoherencia:
    """Compuerta falsable sobre el seed que se publica (sin base de datos).

    Cada aserción falla ruidosamente ante un error de transcripción concreto,
    y todas entran con **cero** exenciones sobre el seed actual.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def filas(cls):
        return json.loads(SEED_PATH.read_text(encoding="utf-8"))

    def test_el_seed_existe_y_no_esta_vacio(self, filas):
        assert len(filas) >= 80

    def test_toda_fila_trae_procedencia_utilizable(self, filas):
        """Sin URL de fuente primaria una fila no puede publicarse."""
        sin_fuente = [
            f"{f['official_id']}/{f['article']}"
            for f in filas
            if not f.get("source_url") or not f.get("edition")
        ]
        assert sin_fuente == []

    def test_ningun_texto_esta_vacio_ni_truncado(self, filas):
        """Un artículo de menos de 60 caracteres es un encabezado, no un texto.

        Es la falla que atrapó los 85 caracteres del 'Artículo 15-A' cuando el
        extractor tomaba la entrada del índice en vez del articulado.
        """
        cortos = [
            (f"{f['official_id']}/{f['article']}", len(f["text"]))
            for f in filas
            if len(f["text"]) < 60 and not f.get("derogado")
        ]
        assert cortos == []

    def test_todo_texto_empieza_por_su_propio_articulo(self, filas):
        """Atrapa el desalineamiento entre el número pedido y el texto traído."""
        import re

        malos = []
        for f in filas:
            # La Cámara imprime el ordinal en los artículos de un dígito
            # ("Artículo 1o.-A" para el que el corpus llama "1-A"), y separa
            # el sufijo con guion o con espacio ("5 A" = "5-A").
            cuerpo, _, sufijo = f["article"].partition("-")
            numero = rf"{cuerpo}(?:o\.?)?"
            if sufijo:
                numero += rf"\s*[-\s.]\s*-?{sufijo}"
            patron = rf"^Art[íi]culo\s+{numero}\b"
            if not re.match(patron, f["text"], re.I):
                malos.append(f"{f['official_id']}/{f['article']}")
        assert malos == []

    def test_las_vigencias_no_se_traslapan_por_articulo(self, filas):
        """Dos textos vigentes el mismo día para el mismo artículo es ambigüedad."""
        from collections import Counter

        claves = Counter(
            (f["official_id"], f["article"], f["effective_from"]) for f in filas
        )
        assert [k for k, n in claves.items() if n > 1] == []

    def test_la_fecha_de_vigencia_es_la_de_su_ultima_reforma(self, filas):
        """El artículo se fecha por SU reforma, no por la de la ley entera.

        Fechar el art. 20 de la LFT en 2026 (última reforma de la ley) diría
        que su texto cambió ese día, y no cambió desde 1970.
        """
        incoherentes = [
            f"{f['official_id']}/{f['article']}"
            for f in filas
            if f.get("reformas_dof") and f["effective_from"] != f["reformas_dof"][-1]
        ]
        assert incoherentes == []

    def test_las_fechas_de_reforma_van_en_orden(self, filas):
        desordenadas = [
            f"{f['official_id']}/{f['article']}"
            for f in filas
            if f.get("reformas_dof") != sorted(f.get("reformas_dof") or [])
        ]
        assert desordenadas == []

    def test_ninguna_reforma_esta_en_el_futuro(self, filas):
        """Una fecha DOF posterior a hoy es un dedazo de transcripción."""
        hoy = date.today().isoformat()
        futuras = [
            (f"{f['official_id']}/{f['article']}", d)
            for f in filas
            for d in (f.get("reformas_dof") or [])
            if d > hoy
        ]
        assert futuras == []

    def test_cubre_los_articulos_que_el_hcm_necesita(self, filas):
        """La lista mínima del §7 del plan, ley por ley."""
        presentes = {(f["official_id"], f["article"]) for f in filas}
        exigidos = [
            ("lft", "20"),
            ("lft", "24"),
            ("lft", "25"),
            ("lft", "35"),
            ("lft", "39-A"),
            ("lft", "39-B"),
            ("lft", "59"),
            ("lft", "61"),
            ("lft", "66"),
            ("lft", "76"),
            ("lft", "80"),
            ("lft", "87"),
            ("lft", "127"),
            ("lft", "132"),
            ("lft", "330-A"),
            ("lft", "422"),
            ("lft", "804"),
            ("lft", "15"),
            ("lss", "5-A"),
            ("lss", "12"),
            ("lss", "15"),
            ("lss", "27"),
            ("lss", "29"),
            ("lifnvt", "29"),
            ("lisr", "28"),
            ("lisr", "94"),
            ("lisr", "96"),
            ("lisr", "106"),
            ("lisr", "113-J"),
            ("liva", "1-A"),
            ("rliva", "3"),
            ("cff", "17-A"),
            ("cff", "21"),
            ("cff", "32-D"),
            ("cff", "15-D"),
        ]
        faltantes = [f"{o}/{a}" for o, a in exigidos if (o, a) not in presentes]
        assert faltantes == []

    def test_la_reforma_de_la_jornada_esta_en_el_texto(self, filas):
        """El art. 59 reformado el 01-05-2026 dice 'cuarenta horas semanales'.

        Es el cambio que un HCM que leyera constantes se perdería entero.
        """
        art59 = next(
            f for f in filas if f["official_id"] == "lft" and f["article"] == "59"
        )
        assert "cuarenta horas semanales" in art59["text"]
        assert art59["effective_from"] == "2026-05-01"

    def test_los_articulos_del_outsourcing_derogado_se_declaran(self, filas):
        """LFT 15-A a 15-D quedaron derogados por la reforma del 23-04-2021.

        El plan del programa los citaba como base del REPSE; la base real es
        el art. 15. Publicarlos marcados 'derogado' evita que un consumidor
        siga citando un artículo que ya no dice nada.
        """
        for numero in ("15-A", "15-B", "15-C", "15-D"):
            fila = next(
                f for f in filas if f["official_id"] == "lft" and f["article"] == numero
            )
            assert fila["derogado"] is True
            assert fila["effective_from"] == "2021-04-23"
