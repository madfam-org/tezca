"""Cuotas IMSS 2026 y tasas estatales del ISN (ratificación 2026-11-03, F1 y F2).

Tres capas, como ``test_fiscal_dof_2026``:

* **Las constantes contra la fuente primaria** (``apps.api.fiscal_cuotas_2026``):
  fallan si alguien «corrige» una tasa sin releer la ley.
* **La compuerta de coherencia** (``apps.api.cuotas_coherence``): verde con la
  tabla publicada y roja con cada defecto que dice cazar.
* **La publicación y el feed**: el comando escribe filas ``published``, respeta
  el append-only, y los endpoints que lee symbiosis-hcm devuelven la tasa
  correcta para una fecha y una entidad.
"""

import copy
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from apps.api.cuotas_coherence import (
    CONCEPTOS_REQUERIDOS,
    describe,
    incoherencias_imss,
    incoherencias_isn,
)
from apps.api.fiscal_cuotas_2026 import (
    CEV_PATRON_BANDAS_2026,
    IMSS_RATES_2026,
    IMSS_RATES_2026_TABLE,
    ISN_TASAS,
)
from apps.api.fiscal_models import FiscalTable, ImpuestoNominaEstatal, Provenance
from tests.api.test_fiscal_views import AUTH_PATCH, _make_user


def _concepto(nombre, rows=None):
    return next(r for r in (rows or IMSS_RATES_2026) if r["concepto"] == nombre)


class TestCuotasImssContraLaFuente:
    """LSS (Cámara, última reforma DOF 15-01-2026) y DOF 16-12-2020, leídos 2026-11-03."""

    def test_cev_patronal_2026_es_la_columna_2026_del_transitorio_segundo(self):
        """La tabla es una imagen en el DOF; éstas son sus ocho celdas de 2026."""
        tasas = [banda["tasa_patron"] for banda in CEV_PATRON_BANDAS_2026]
        assert tasas == [
            "0.0315",
            "0.03676",
            "0.04851",
            "0.05556",
            "0.06026",
            "0.06361",
            "0.06613",
            "0.07513",
        ]

    def test_cev_bandas_con_sus_limites_impresos(self):
        textos = [banda["texto"] for banda in CEV_PATRON_BANDAS_2026]
        assert textos == [
            "1.0 SM",
            "1.01 SM a 1.50 UMA",
            "1.51 a 2.00 UMA",
            "2.01 a 2.50 UMA",
            "2.51 a 3.00 UMA",
            "3.01 a 3.50 UMA",
            "3.51 a 4.00 UMA",
            "4.01 UMA en adelante",
        ]
        primera, ultima = CEV_PATRON_BANDAS_2026[0], CEV_PATRON_BANDAS_2026[-1]
        assert primera["hasta"] == {"veces": "1.00", "unidad": "salario_minimo"}
        assert ultima["hasta"] is None, "«en adelante»"
        assert CEV_PATRON_BANDAS_2026[1]["desde"]["unidad"] == "salario_minimo"
        assert CEV_PATRON_BANDAS_2026[1]["hasta"]["unidad"] == "uma"

    def test_cev_ya_no_es_el_3150_plano_salvo_en_la_primera_banda(self):
        """El defecto que la ratificación encontró en symbiosis-hcm (H14)."""
        tasas = {Decimal(b["tasa_patron"]) for b in CEV_PATRON_BANDAS_2026}
        assert Decimal("0.0315") in tasas
        assert len(tasas) == 8

    def test_cev_cita_el_decreto_de_2020_con_su_codigo(self):
        cev = _concepto("cesantia_vejez")
        assert cev["dof_codigo"] == "5607729"
        assert cev["dof_date"] == "2020-12-16"
        assert "5607729" in cev["source_url"]
        assert cev["trabajador"] == "0.01125", "LSS 168 fr. II b)"
        assert cev["patron"] is None, "la patronal es la tabla, no un escalar"

    def test_enfermedades_y_maternidad(self):
        fija = _concepto("em_cuota_fija")
        assert (fija["patron"], fija["trabajador"], fija["base"]) == (
            "0.204",
            None,
            "uma_diaria",
        )
        excedente = _concepto("em_excedente")
        assert (excedente["patron"], excedente["trabajador"]) == ("0.011", "0.004")
        assert excedente["umbral"] == {"veces": "3", "unidad": "uma"}
        dinero = _concepto("em_prestaciones_dinero")
        assert (dinero["patron"], dinero["trabajador"]) == ("0.007", "0.0025")
        pensionados = _concepto("em_gastos_medicos_pensionados")
        assert (pensionados["patron"], pensionados["trabajador"]) == (
            "0.0105",
            "0.00375",
        )

    def test_la_cuota_fija_cita_el_transitorio_de_1995_no_el_de_2001(self):
        """La ratificación citaba «DOF 20-12-2001»; el transitorio es de la Ley de 1995."""
        for nombre in ("em_cuota_fija", "em_excedente"):
            articulo = _concepto(nombre)["articulo"]
            assert "DÉCIMO NOVENO" in articulo
            assert "21-12-1995" in articulo

    def test_invalidez_retiro_guarderias_infonavit(self):
        iv = _concepto("invalidez_vida")
        assert (iv["patron"], iv["trabajador"]) == ("0.0175", "0.00625")
        assert _concepto("retiro")["patron"] == "0.02"
        assert _concepto("guarderias_prestaciones_sociales")["patron"] == "0.01"
        infonavit = _concepto("infonavit")
        assert infonavit["patron"] == "0.05"
        assert infonavit["official_id"] == "lifnvt"

    def test_tope_sbc_es_25_uma(self):
        assert _concepto("tope_sbc")["tope"] == {"veces": "25", "unidad": "uma"}

    def test_riesgo_de_trabajo_no_es_una_constante_del_ejercicio(self):
        """La prima es de cada patrón (LSS 71-74): Tezca no la publica."""
        assert not any("riesgo" in row["concepto"] for row in IMSS_RATES_2026)
        assert "RIESGO DE TRABAJO NO ESTÁ" in IMSS_RATES_2026_TABLE["notes"]

    def test_todo_renglon_es_published_con_articulo_y_fuente(self):
        for row in IMSS_RATES_2026:
            assert row["provenance"] == "published", row["concepto"]
            assert row["articulo"], row["concepto"]
            assert row["fuente"], row["concepto"]
            assert row["source_url"].startswith("https://"), row["concepto"]

    def test_la_tabla_rige_el_anio_calendario_2026(self):
        assert IMSS_RATES_2026_TABLE["vigencia_from"] == "2026-01-01"
        assert IMSS_RATES_2026_TABLE["vigencia_to"] == "2026-12-31"
        assert IMSS_RATES_2026_TABLE["dof_codigo"] == "5607729"


class TestIsnContraLaGaceta:
    """POE Morelos 6382 Ext. y 6506 Ext.; CFCDMX texto vigente de la Consejería."""

    def _fila(self, entidad, desde):
        return next(
            f
            for f in ISN_TASAS
            if f["entidad"] == entidad and f["vigencia_from"] == desde
        )

    def test_morelos_2025_es_2_5_y_termina_al_entrar_el_decreto_997(self):
        fila = self._fila("MOR", "2025-01-01")
        assert fila["value"] == "2.5"
        assert fila["vigencia_to"] == "2025-12-31"
        assert "6382" in fila["source_citation"]
        assert (
            fila["source_url"]
            == "https://periodico.morelos.gob.mx/obtenerPDF/2024/6382.pdf"
        )

    def test_morelos_2026_es_3_0_desde_el_1_de_enero(self):
        fila = self._fila("MOR", "2026-01-01")
        assert fila["value"] == "3.0"
        assert fila["vigencia_to"] is None
        assert "6506" in fila["source_citation"]
        assert "Novecientos Noventa y Siete" in fila["source_citation"]
        assert fila["legal_basis"] == "LGHEM Art. 58 BIS-4"

    def test_cdmx_es_4_desde_2025(self):
        fila = self._fila("CMX", "2025-01-01")
        assert fila["value"] == "4.0"
        assert fila["vigencia_to"] is None
        assert fila["legal_basis"] == "CFCDMX Art. 158"
        assert fila["source_url"].startswith("https://data.consejeria.cdmx.gob.mx/")

    def test_solo_se_publican_las_entidades_leidas(self):
        assert {f["entidad"] for f in ISN_TASAS} == {"MOR", "CMX"}

    def test_toda_entidad_publicada_es_una_clave_valida(self):
        validas = {c.value for c in ImpuestoNominaEstatal.Entidad}
        assert len(validas) == 32
        assert {f["entidad"] for f in ISN_TASAS} <= validas


class TestCompuertaDeCoherencia:
    def test_la_tabla_publicada_cuadra(self):
        problemas = incoherencias_imss(
            IMSS_RATES_2026, tope_regla_laboral={"veces": 25, "unidad": "uma"}
        )
        assert problemas == [], describe(problemas)

    def test_las_tasas_estatales_cuadran(self):
        assert incoherencias_isn(ISN_TASAS) == []

    def test_muerde_dos_bandas_intercambiadas(self):
        rows = copy.deepcopy(IMSS_RATES_2026)
        bandas = _concepto("cesantia_vejez", rows)["bandas_patron"]
        bandas[3]["tasa_patron"], bandas[4]["tasa_patron"] = (
            bandas[4]["tasa_patron"],
            bandas[3]["tasa_patron"],
        )
        assert any("no crecen" in p for p in incoherencias_imss(rows))

    def test_muerde_el_reparto_70_25_roto(self):
        rows = copy.deepcopy(IMSS_RATES_2026)
        _concepto("em_prestaciones_dinero", rows)["trabajador"] = "0.0035"
        assert any("70/25" in p for p in incoherencias_imss(rows))

    def test_muerde_la_cuota_fija_mal_derivada(self):
        rows = copy.deepcopy(IMSS_RATES_2026)
        _concepto("em_cuota_fija", rows)["patron"] = "0.2045"
        assert any("em_cuota_fija" in p for p in incoherencias_imss(rows))

    def test_muerde_un_concepto_faltante(self):
        rows = [r for r in IMSS_RATES_2026 if r["concepto"] != "retiro"]
        assert any("retiro" in p for p in incoherencias_imss(rows))
        assert "retiro" in CONCEPTOS_REQUERIDOS

    def test_una_tabla_published_no_admite_un_renglon_sin_verificar(self):
        rows = copy.deepcopy(IMSS_RATES_2026)
        _concepto("invalidez_vida", rows)["provenance"] = "seed-unverified"
        assert any("invalidez_vida" in p for p in incoherencias_imss(rows))

    def test_muerde_un_tope_distinto_de_la_regla_laboral(self):
        problemas = incoherencias_imss(
            IMSS_RATES_2026, tope_regla_laboral={"veces": 20, "unidad": "uma"}
        )
        assert any("tope_sbc" in p for p in problemas)

    def test_muerde_vigencias_superpuestas_en_una_entidad(self):
        filas = ISN_TASAS + [
            {
                "entidad": "MOR",
                "value": "2.0",
                "vigencia_from": "2025-06-01",
                "vigencia_to": None,
            }
        ]
        assert any("se superpone" in p for p in incoherencias_isn(filas))


@pytest.mark.django_db
class TestPublicacion:
    """python manage.py publish_fiscal_values_2026 — la parte de cuotas e ISN."""

    def test_publica_imss_e_isn(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_fiscal_values_2026", stdout=StringIO())

        tabla = FiscalTable.objects.get(kind=FiscalTable.Kind.IMSS_RATES, year=2026)
        assert tabla.provenance == Provenance.PUBLISHED
        assert tabla.dof_codigo == "5607729"
        assert str(tabla.vigencia_to) == "2026-12-31"
        assert tabla.rows == IMSS_RATES_2026

        isn = {
            (r.entidad, str(r.vigencia_from)): r
            for r in ImpuestoNominaEstatal.objects.all()
        }
        assert set(isn) == {
            ("MOR", "2025-01-01"),
            ("MOR", "2026-01-01"),
            ("CMX", "2025-01-01"),
        }
        assert isn[("MOR", "2026-01-01")].value == Decimal("3.0")
        assert isn[("MOR", "2025-01-01")].vigencia_to.isoformat() == "2025-12-31"
        assert all(r.provenance == Provenance.PUBLISHED for r in isn.values())
        assert all(r.unit == "percent" for r in isn.values())
        assert all(r.dof_codigo == "" for r in isn.values()), "la gaceta no es el DOF"

    def test_es_idempotente(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_fiscal_values_2026", stdout=StringIO())
        antes = (FiscalTable.objects.count(), ImpuestoNominaEstatal.objects.count())
        out = StringIO()
        call_command("publish_fiscal_values_2026", stdout=out)
        assert (
            FiscalTable.objects.count(),
            ImpuestoNominaEstatal.objects.count(),
        ) == antes
        assert "0 filas nuevas" in out.getvalue()

    def test_dry_run_no_escribe(self):
        call_command("publish_fiscal_values_2026", "--dry-run", stdout=StringIO())
        assert ImpuestoNominaEstatal.objects.count() == 0
        assert not FiscalTable.objects.filter(kind=FiscalTable.Kind.IMSS_RATES).exists()

    def test_nunca_toca_una_tasa_ya_publicada(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        ImpuestoNominaEstatal.objects.create(
            entidad="MOR",
            value="3.0",
            unit="percent",
            vigencia_from="2026-01-01",
            provenance=Provenance.PUBLISHED,
            notes="captura de operador verificada",
        )
        call_command("publish_fiscal_values_2026", stdout=StringIO())
        fila = ImpuestoNominaEstatal.objects.get(
            entidad="MOR", vigencia_from="2026-01-01"
        )
        assert fila.notes == "captura de operador verificada"

    def test_promueve_una_tasa_sembrada_sin_verificar(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        sembrada = ImpuestoNominaEstatal.objects.create(
            entidad="CMX",
            value="3.0",
            unit="percent",
            vigencia_from="2025-01-01",
            provenance=Provenance.SEED_UNVERIFIED,
        )
        call_command("publish_fiscal_values_2026", stdout=StringIO())
        sembrada.refresh_from_db()
        assert sembrada.value == Decimal("4.0")
        assert sembrada.provenance == Provenance.PUBLISHED
        assert ImpuestoNominaEstatal.objects.filter(entidad="CMX").count() == 1

    def test_cierra_la_tasa_abierta_anterior_de_la_entidad(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        vieja = ImpuestoNominaEstatal.objects.create(
            entidad="CMX",
            value="3.0",
            unit="percent",
            vigencia_from="2020-01-01",
            provenance=Provenance.SEED_UNVERIFIED,
        )
        call_command("publish_fiscal_values_2026", stdout=StringIO())
        vieja.refresh_from_db()
        assert vieja.vigencia_to.isoformat() == "2024-12-31"

    def test_una_tabla_incoherente_no_se_publica(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        rota = copy.deepcopy(IMSS_RATES_2026)
        _concepto("em_prestaciones_dinero", rota)["patron"] = "0.0071"
        with patch(
            "apps.api.management.commands.publish_fiscal_values_2026.IMSS_RATES_2026",
            rota,
        ):
            with pytest.raises(CommandError, match="incoherentes"):
                call_command("publish_fiscal_values_2026", stdout=StringIO())
        assert not FiscalTable.objects.exists(), "toda la publicación se revierte"


@pytest.mark.django_db
class TestFeedQueLeeElHcm:
    @pytest.fixture(autouse=True)
    def _publicado(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_fiscal_values_2026", stdout=StringIO())

    @pytest.fixture
    def client(self):
        api = APIClient()
        user = _make_user()

        class _Authed:
            @staticmethod
            def get(url, params=None):
                with patch(AUTH_PATCH) as mock_auth:
                    mock_auth.return_value = (user, "tok")
                    return api.get(url, params or {})

        return _Authed()

    def test_isn_requiere_autenticacion(self):
        assert APIClient().get("/api/v1/fiscal/isn/").status_code == 401

    def test_isn_requiere_scope_read(self):
        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (_make_user(scopes=["search"]), "tok")
            resp = APIClient().get("/api/v1/fiscal/isn/")
        assert resp.status_code == 403

    def test_morelos_en_marzo_2026_es_3_por_ciento(self, client):
        resp = client.get("/api/v1/fiscal/isn/", {"entidad": "MOR", "on": "2026-03-15"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["value"] == "3.0000"
        assert body["tasa"] == "0.030000"
        assert body["effective_date"] == "2026-01-01"
        assert body["provenance"] == "published"

    def test_morelos_en_2025_era_2_5(self, client):
        body = client.get(
            "/api/v1/fiscal/isn/", {"entidad": "MOR", "on": "2025-12-31"}
        ).json()
        assert body["value"] == "2.5000"

    def test_cdmx_en_2026_es_4_por_ciento(self, client):
        body = client.get(
            "/api/v1/fiscal/isn/", {"entidad": "cmx", "on": "2026-06-30"}
        ).json()
        assert body["tasa"] == "0.040000"
        assert body["results"][0]["legal_basis"] == "CFCDMX Art. 158"
        assert body["results"][0]["publicacion_fecha"] == "2024-12-27"

    def test_entidad_sin_tasa_publicada_es_count_cero(self, client):
        body = client.get(
            "/api/v1/fiscal/isn/", {"entidad": "JAL", "on": "2026-06-30"}
        ).json()
        assert body["count"] == 0
        assert "value" not in body, "nunca una tasa de otra entidad"

    def test_year_trae_lo_que_rigio_ese_anio(self, client):
        body = client.get("/api/v1/fiscal/isn/", {"year": 2026}).json()
        vigentes = {(r["entidad"], r["vigencia_from"]) for r in body["results"]}
        assert vigentes == {("MOR", "2026-01-01"), ("CMX", "2025-01-01")}

    def test_entidad_invalida_es_400(self, client):
        assert client.get("/api/v1/fiscal/isn/", {"entidad": "XX"}).status_code == 400

    def test_tables_2026_trae_las_cuotas_imss(self, client):
        body = client.get("/api/v1/fiscal/tables/2026/").json()
        assert body["imss_rates"] == IMSS_RATES_2026
        meta = body["tables"]["imss_rates"]
        assert meta["provenance"] == "published"
        assert meta["dof_codigo"] == "5607729"
        assert meta["vigencia_to"] == "2026-12-31"
        assert body["isn_rates"] is None
        assert body["isn_endpoint"] == "/api/v1/fiscal/isn/"

    def test_tables_2027_no_hereda_las_cuotas_2026(self, client):
        body = client.get(
            "/api/v1/fiscal/tables/", {"kind": "imss_rates", "on": "2027-01-15"}
        ).json()
        assert body["count"] == 0
