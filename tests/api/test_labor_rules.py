"""Pruebas de las reglas laborales estructuradas y los catálogos SAT (T-1b).

Tres capas:

* **Coherencia del seed**, sin base de datos: vigencias que no se traslapan ni
  dejan huecos, procedencia utilizable, y que los valores digan lo que dice la
  ley que se leyó. Entra con la lista de exenciones **vacía**.
* **API**, con base: el ``?on=`` en las fronteras de vigencia y el filtrado
  por dimensiones.
* **Falsabilidad de las compuertas**: se demuestra que cada una se pone en
  rojo ante el error que dice atrapar, mutando el seed en memoria.
"""

import copy
import io
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.fiscal_models import Provenance
from apps.api.labor_coherence import huecos_en_la_serie, vigencias_traslapadas
from apps.api.labor_models import LaborRule, SatCatalogEntry
from apps.api.labor_seed_data import REGLAS
from apps.api.middleware.janua_auth import JanuaUser

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"

CATALOGOS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "labor" / "sat_catalogos.json"
)


def _make_user(scopes=None, tier="essentials"):
    user = JanuaUser({"sub": "labor-test", "email": "labor@test.com", "tier": tier})
    user.tier = tier
    user.scopes = ["read", "search"] if scopes is None else scopes
    user.allowed_domains = []
    user.api_key_prefix = ""
    return user


def _regla(kind, **kwargs):
    """Una regla mínima para las pruebas de API."""
    campos = {
        "value": 5,
        "unit": "dias",
        "official_id": "lft",
        "article": "1",
        "effective_from": "2020-01-01",
        "provenance": Provenance.PUBLISHED,
    }
    campos.update(kwargs)
    return LaborRule.objects.create(kind=kind, **campos)


class TestSeedCoherencia:
    """Compuertas sobre el seed publicado. Cero exenciones."""

    def test_ninguna_vigencia_se_traslapa(self):
        """Dos filas del mismo kind vigentes el mismo día son ambigüedad.

        Es el riesgo real del feed de la jornada, que publica cinco vigencias
        contiguas del mismo kind (48 h en 2026 … 40 h en 2030).
        """
        assert vigencias_traslapadas(REGLAS) == []

    def test_ninguna_serie_deja_huecos(self):
        """Un día sin regla dentro de una serie cerrada es un dedazo."""
        assert huecos_en_la_serie(REGLAS) == []

    def test_toda_fila_published_tiene_fuente_primaria(self):
        """`published` sin URL de fuente no puede defenderse ante nadie."""
        sin_fuente = [
            r["kind"]
            for r in REGLAS
            if r["provenance"] == Provenance.PUBLISHED
            and not (r.get("source_url") or r.get("dof_codigo"))
        ]
        assert sin_fuente == []

    def test_toda_fila_cita_su_articulo(self):
        sin_articulo = [
            r["kind"]
            for r in REGLAS
            if not r.get("official_id") or not r.get("article")
        ]
        assert sin_articulo == []

    def test_toda_fila_explica_de_donde_sale_el_numero(self):
        """Sin nota, nadie puede revisar la lectura sin rehacerla."""
        sin_nota = [r["kind"] for r in REGLAS if len(r.get("notes", "")) < 40]
        assert sin_nota == []

    def test_los_kinds_son_del_vocabulario_declarado(self):
        validos = {c.value for c in LaborRule.Kind}
        assert [r["kind"] for r in REGLAS if r["kind"] not in validos] == []

    def test_ninguna_vigencia_empieza_en_el_futuro_sin_razon(self):
        """Salvo el escalonamiento de la jornada, que la ley sí fecha adelante."""
        hoy = date.today().isoformat()
        escalonadas = {
            LaborRule.Kind.JORNADA_SEMANAL_HORAS_MAX.value,
            LaborRule.Kind.TIEMPO_EXTRA_SEMANAL_HORAS_MAX.value,
        }
        futuras = [
            (r["kind"], r["effective_from"])
            for r in REGLAS
            if r["effective_from"] > hoy and r["kind"] not in escalonadas
        ]
        assert futuras == []

    def test_las_reglas_minimas_del_contrato_estan_publicadas(self):
        """La lista de kinds que el contrato C1 exige, sin faltar ninguno."""
        publicados = {
            r["kind"] for r in REGLAS if r["provenance"] == Provenance.PUBLISHED
        }
        exigidos = {
            "imss_alta_ventana_dias_habiles",
            "contrato_escrito_desde_inicio",
            "prueba_dias_max",
            "prueba_dias_max_direccion",
            "capacitacion_inicial_meses_max",
            "capacitacion_inicial_meses_max_direccion",
            "jornada_diurna_horas_max",
            "jornada_nocturna_horas_max",
            "jornada_mixta_horas_max",
            "semana_reducida_prorrateo",
            "ptu_eventuales_dias_min",
            "ptu_fecha_limite_dias",
            "aguinaldo_dias_min",
            "aguinaldo_fecha_limite",
            "vacaciones_dias_por_anio",
            "prima_vacacional_pct_min",
            "retencion_isr_honorarios_pct",
            "retencion_iva_honorarios_fraccion",
            "resico_tope_anual",
            "recargos_tasa_mensual",
            "actualizacion_factor",
            "repse_obligatorio_condiciones",
            "teletrabajo_umbral_pct",
            "nom035_umbral_personas",
        }
        assert sorted(exigidos - publicados) == []


class TestValoresContraLaLectura:
    """Cada número, contra el artículo que se leyó. Un dedazo se ve aquí."""

    def _valor(self, kind, **dims):
        for regla in REGLAS:
            if regla["kind"] != kind:
                continue
            if all(regla.get(k, "") == v for k, v in dims.items()):
                return regla
        raise AssertionError(f"no está la regla {kind} {dims}")

    def test_alta_imss_cinco_dias_habiles(self):
        """LSS 15 fr. I: 'plazos no mayores de cinco días hábiles'."""
        regla = self._valor("imss_alta_ventana_dias_habiles")
        assert regla["value"] == 5
        assert regla["unit"] == "dias_habiles"
        assert (regla["official_id"], regla["article"]) == ("lss", "15")

    def test_prueba_treinta_dias_y_ciento_ochenta_en_direccion(self):
        """LFT 39-A: treinta días; hasta ciento ochenta en puestos de dirección."""
        assert self._valor("prueba_dias_max")["value"] == 30
        assert self._valor("prueba_dias_max_direccion")["value"] == 180

    def test_capacitacion_inicial_tres_y_seis_meses(self):
        """LFT 39-B: tres meses; hasta seis en puestos de dirección."""
        assert self._valor("capacitacion_inicial_meses_max")["value"] == 3
        assert self._valor("capacitacion_inicial_meses_max_direccion")["value"] == 6

    def test_jornada_diaria_ocho_siete_y_siete_y_media(self):
        """LFT 61 reformado: ocho la diurna, siete la nocturna, 7.5 la mixta."""
        assert self._valor("jornada_diurna_horas_max")["value"] == 8
        assert self._valor("jornada_nocturna_horas_max")["value"] == 7
        assert self._valor("jornada_mixta_horas_max")["value"] == 7.5

    def test_aguinaldo_quince_dias_antes_del_veinte_de_diciembre(self):
        """LFT 87: quince días de salario, antes del día veinte de diciembre."""
        assert self._valor("aguinaldo_dias_min")["value"] == 15
        fecha = self._valor("aguinaldo_fecha_limite")["value"]
        assert (fecha["mes"], fecha["dia"], fecha["criterio"]) == (12, 20, "antes_de")

    def test_vacaciones_doce_dias_al_primer_anio(self):
        """LFT 76 reformado el 27-12-2022: doce al primero, veinte al quinto."""
        tabla = self._valor("vacaciones_dias_por_anio")["value"]["tabla"]
        assert tabla[0] == {"anio_servicio": 1, "dias": 12}
        assert tabla[-1] == {"anio_servicio": 5, "dias": 20}
        # Dos días por año subsecuente: la progresión no puede saltarse.
        for previo, actual in zip(tabla, tabla[1:]):
            assert actual["dias"] - previo["dias"] == 2

    def test_prima_vacacional_veinticinco_por_ciento(self):
        """LFT 80: prima no menor de veinticinco por ciento."""
        assert self._valor("prima_vacacional_pct_min")["value"] == 25

    def test_ptu_sesenta_dias_para_eventuales_y_sesenta_para_repartir(self):
        """LFT 127 fr. VII y LFT 122."""
        assert self._valor("ptu_eventuales_dias_min")["value"] == 60
        assert self._valor("ptu_fecha_limite_dias")["value"] == 60

    def test_retenciones_por_pagador_y_regimen(self):
        """La misma pregunta, tres respuestas según quién paga y cómo cobra."""
        moral_612 = self._valor(
            "retencion_isr_honorarios_pct",
            payer_legal_form="persona_moral",
            provider_regime="612",
        )
        assert moral_612["value"] == 10
        assert (moral_612["official_id"], moral_612["article"]) == ("lisr", "106")

        moral_resico = self._valor(
            "retencion_isr_honorarios_pct",
            payer_legal_form="persona_moral",
            provider_regime="626",
        )
        assert moral_resico["value"] == 1.25
        assert moral_resico["article"] == "113-J"

        # El cero explícito importa: 'no hay obligación' NO es 'no hay regla'.
        fisica = self._valor(
            "retencion_isr_honorarios_pct", payer_legal_form="persona_fisica"
        )
        assert fisica["value"] == 0

    def test_iva_dos_tercios_del_trasladado(self):
        """RLIVA 3 fr. I: las dos terceras partes del impuesto trasladado."""
        regla = self._valor(
            "retencion_iva_honorarios_fraccion", service="servicios_profesionales"
        )
        assert regla["value"]["numerador"] == 2
        assert regla["value"]["denominador"] == 3
        assert (regla["official_id"], regla["article"]) == ("rliva", "3")

    def test_resico_tope_tres_millones_quinientos_mil(self):
        """LISR 113-E: 'tres millones quinientos mil pesos'."""
        assert self._valor("resico_tope_anual")["value"] == 3500000

    def test_recargos_son_la_tasa_de_la_lif_incrementada_en_cincuenta(self):
        """CFF 21: la tasa del Congreso 'incrementada en 50%'.

        LIF 2026 art. 11 fr. I fija 1.38 % mensual de prórroga. 1.38 x 1.5 =
        2.07 %. Si alguien copiara el 1.38 como tasa de mora, esta prueba lo
        atrapa: la identidad se verifica, no se transcribe.
        """
        from decimal import Decimal

        regla = self._valor("recargos_tasa_mensual")
        base = Decimal(regla["value"]["base_lif"])
        mora = Decimal(regla["value"]["tasa_mensual"])
        assert mora == (base * Decimal("1.5")).quantize(Decimal("0.01"))
        assert regla["value"]["tasa_mensual"] == "2.07"
        # La LIF es anual: la vigencia tiene que cerrarse con el ejercicio.
        assert regla["effective_to"] == "2026-12-31"

    def test_teletrabajo_cuarenta_por_ciento(self):
        """LFT 330-A: 'más del cuarenta por ciento del tiempo'."""
        assert self._valor("teletrabajo_umbral_pct")["value"] == 40

    def test_nom035_tres_tramos_por_tamano(self):
        """NOM-035 numeral 4: hasta 15, de 16 a 50, y más de 50."""
        tramos = self._valor("nom035_umbral_personas")["value"]["tramos"]
        assert [t.get("hasta") for t in tramos] == [15, 50, None]
        assert tramos[0]["identificacion_factores"] is False
        assert tramos[1]["identificacion_factores"] is True
        assert tramos[2]["evaluacion_entorno"] is True

    def test_repse_tres_anios_con_ventana_de_tres_meses(self):
        """LFT 15 y Acuerdo REPSE arts. DÉCIMO TERCERO y DÉCIMO SEXTO."""
        valor = self._valor("repse_vigencia_anios")["value"]
        assert valor["vigencia_anios"] == 3
        assert valor["renovacion_ventana_meses_antes"] == 3

    def test_la_semana_reducida_es_un_piso_no_un_prorrateo(self):
        """LSS 29 fr. III, no la 62: nunca por debajo del salario mínimo."""
        regla = self._valor("semana_reducida_prorrateo")
        assert regla["value"]["regla"] == "piso_salario_minimo"
        assert (regla["official_id"], regla["article"]) == ("lss", "29")

    def test_los_indicios_de_recaracterizacion_van_sin_verificar(self):
        """Lo que no se pudo citar NO se publica como verdad.

        Los tres elementos son del art. 20; la lista de indicios es doctrina
        que este carril no pudo citar con registro. Va seed-unverified para
        que ningún cálculo la use.
        """
        regla = self._valor("recaracterizacion_indicios")
        assert regla["provenance"] == Provenance.SEED_UNVERIFIED
        assert len(regla["value"]["elementos_de_ley"]) == 3
        assert "advertencia" in regla["value"]


class TestJornadaEscalonada:
    """El escalonamiento de la jornada: el hallazgo central del carril."""

    def _serie(self, kind):
        return sorted(
            (r for r in REGLAS if r["kind"] == kind),
            key=lambda r: r["effective_from"],
        )

    def test_la_jornada_sigue_los_transitorios_del_decreto(self):
        """48 · 46 · 44 · 42 · 40, un escalón por año desde 2026."""
        serie = self._serie("jornada_semanal_horas_max")
        assert [r["value"] for r in serie] == [48, 46, 44, 42, 40]
        assert [r["effective_from"] for r in serie] == [
            f"{a}-01-01" for a in range(2026, 2031)
        ]

    def test_hoy_la_jornada_son_cuarenta_y_ocho_no_cuarenta(self):
        """El texto del art. 59 dice 40; en 2026 rigen 48. La trampa.

        Un HCM que leyera sólo la prosa calcularía con ocho horas de menos.
        """
        en_2026 = [
            r
            for r in self._serie("jornada_semanal_horas_max")
            if r["effective_from"] <= "2026-06-01" <= (r["effective_to"] or "9999")
        ]
        assert len(en_2026) == 1
        assert en_2026[0]["value"] == 48

    def test_el_tiempo_extra_tambien_escalona(self):
        """9 · 9 · 10 · 11 · 12, transitorio cuarto."""
        serie = self._serie("tiempo_extra_semanal_horas_max")
        assert [r["value"] for r in serie] == [9, 9, 10, 11, 12]

    def test_solo_el_ultimo_escalon_queda_abierto(self):
        for kind in (
            "jornada_semanal_horas_max",
            "tiempo_extra_semanal_horas_max",
        ):
            serie = self._serie(kind)
            assert all(r["effective_to"] for r in serie[:-1])
            assert serie[-1]["effective_to"] is None

    def test_todo_escalon_cita_el_decreto(self):
        for kind in (
            "jornada_semanal_horas_max",
            "tiempo_extra_semanal_horas_max",
        ):
            for regla in self._serie(kind):
                assert regla["dof_codigo"] == "5786537"
                assert regla["dof_date"] == "2026-05-01"


class TestCompuertasFalsables:
    """Se demuestra que cada compuerta se pone en rojo ante su error."""

    def test_un_escalon_sin_cerrar_levanta_traslape(self):
        mutado = copy.deepcopy(REGLAS)
        for regla in mutado:
            if (
                regla["kind"] == "jornada_semanal_horas_max"
                and regla["effective_from"] == "2028-01-01"
            ):
                regla["effective_to"] = None
        problemas = vigencias_traslapadas(mutado)
        assert len(problemas) == 1
        assert problemas[0]["kind"] == "jornada_semanal_horas_max"

    def test_un_escalon_cerrado_antes_de_tiempo_levanta_hueco(self):
        mutado = copy.deepcopy(REGLAS)
        for regla in mutado:
            if (
                regla["kind"] == "jornada_semanal_horas_max"
                and regla["effective_from"] == "2028-01-01"
            ):
                regla["effective_to"] = "2028-06-30"
        problemas = huecos_en_la_serie(mutado)
        assert len(problemas) == 1
        assert problemas[0]["hueco_desde"] == "2028-07-01"
        assert problemas[0]["hueco_hasta"] == "2028-12-31"


class TestCatalogosSat:
    """El seed de catálogos, contra lo que publica el SAT."""

    @pytest.fixture(scope="class")
    @classmethod
    def filas(cls):
        return json.loads(CATALOGOS_PATH.read_text(encoding="utf-8"))

    def test_estan_los_cuatro_catalogos(self, filas):
        catalogos = {f["catalog"] for f in filas}
        assert catalogos == {
            "c_RegimenFiscal",
            "c_TipoRegimen",
            "c_TipoContrato",
            "c_TipoJornada",
        }

    def test_toda_clave_trae_vigencia_y_fuente(self, filas):
        malas = [
            f["code"]
            for f in filas
            if not f.get("effective_from") or not f.get("source_url")
        ]
        assert malas == []

    def test_no_hay_claves_repetidas_en_la_misma_vigencia(self, filas):
        from collections import Counter

        repetidas = Counter(
            (f["catalog"], f["code"], f["effective_from"]) for f in filas
        )
        assert [k for k, n in repetidas.items() if n > 1] == []

    def test_los_tipos_de_contrato_cubren_las_modalidades_del_hcm(self, filas):
        """Las claves que el enrutador por vínculo (HP-1) va a necesitar."""
        codigos = {f["code"] for f in filas if f["catalog"] == "c_TipoContrato"}
        # 1 indeterminado · 2 obra · 3 determinado · 4 temporada · 5 prueba ·
        # 6 capacitación inicial · 9 sin relación de trabajo
        assert {"1", "2", "3", "4", "5", "6", "9"} <= codigos

    def test_c_tiporegimen_trae_asimilados_y_sueldos(self, filas):
        """HP-3 (asimilados) necesita distinguirlos del régimen 02 de sueldos."""
        codigos = {f["code"] for f in filas if f["catalog"] == "c_TipoRegimen"}
        assert "2" in codigos  # Sueldos
        assert {"5", "6", "7", "8", "9", "10", "11"} <= codigos  # Asimilados

    def test_c_tipojornada_trae_reducida(self, filas):
        """HP-2 (jornada reducida) necesita la clave 5."""
        reducida = [
            f
            for f in filas
            if f["catalog"] == "c_TipoJornada" and f["label"].lower() == "reducida"
        ]
        assert len(reducida) == 1
        assert reducida[0]["code"] == "5"

    def test_c_regimenfiscal_declara_a_quien_aplica(self, filas):
        """612 es de personas físicas; 601 de morales. HP-4 filtra por eso."""
        por_codigo = {f["code"]: f for f in filas if f["catalog"] == "c_RegimenFiscal"}
        assert por_codigo["612"]["aplica_fisica"] is True
        assert por_codigo["612"]["aplica_moral"] is False
        assert por_codigo["601"]["aplica_moral"] is True
        assert por_codigo["605"]["aplica_fisica"] is True

    def test_cada_catalogo_declara_la_version_que_el_xls_imprime(self, filas):
        """La versión no es decorativa: dice de qué edición salió la clave.

        Los cuatro .xls del SAT imprimen su versión en el encabezado de la
        hoja. Si alguien reimporta de una edición nueva y olvida mover este
        campo, las claves nuevas quedarían atribuidas a la edición vieja y
        nadie podría rastrear de dónde salieron. Los valores se leyeron con
        xlrd del archivo que el SAT sirve en `source_url`.
        """
        esperado = {
            "c_RegimenFiscal": "2.0 (rev. 0, publicado 2020-05-25)",
            "c_TipoRegimen": "2.0 (rev. 1, publicado 2019-12-05)",
            "c_TipoContrato": "1.0 (rev. 0)",
            "c_TipoJornada": "1.0 (rev. A)",
        }
        observado = {(f["catalog"], f["catalogo_version"]) for f in filas}
        assert observado == set(esperado.items())

    def test_cada_catalogo_apunta_al_archivo_del_que_salio(self, filas):
        """c_RegimenFiscal viene de catCFDI.xls; los tres de nómina, de catNomina.xls."""
        for fila in filas:
            archivo = fila["source_url"].rsplit("/", 1)[-1]
            if fila["catalog"] == "c_RegimenFiscal":
                assert archivo == "catCFDI.xls"
                assert fila["catalogo_origen"] == "sat_cat_cfdi"
            else:
                assert archivo == "catNomina.xls"
                assert fila["catalogo_origen"] == "sat_cat_nomina"

    def test_el_hueco_del_626_esta_declarado_y_no_inventado(self, filas):
        """RESICO (626) NO está en el .xls que el SAT sirve en esa ruta.

        La regla de retención del 1.25 % sí cita el régimen 626 por su clave,
        porque el artículo 113-J de la LISR la sostiene sin necesidad del
        catálogo. Lo que NO se hizo fue inventar la fila del catálogo: el
        archivo leído es la versión 2.0 y no la trae. Esta prueba fija el
        hueco para que nadie lo rellene de memoria: si un día se publica desde
        una lectura primaria del catálogo de CFDI 4.0, esta prueba se cae y
        obliga a actualizar la documentación.
        """
        codigos = {f["code"] for f in filas if f["catalog"] == "c_RegimenFiscal"}
        assert "626" not in codigos


@pytest.mark.django_db
class TestReglasApi:
    """GET /api/v1/labor/rules/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = _make_user()
        self.url = reverse("labor-rules-list")

    def _get(self, user=None, **params):
        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (user or self.user, "tok")
            return self.client.get(self.url, params)

    def test_requires_authentication(self):
        assert self.client.get(self.url).status_code == 401

    def test_requires_read_scope(self):
        assert self._get(user=_make_user(scopes=["search"])).status_code == 403

    def test_kind_invalido_es_400(self):
        response = self._get(kind="no_existe_esta_regla")
        assert response.status_code == 400
        assert "Invalid 'kind'" in response.json()["error"]

    def test_on_elige_el_escalon_correcto(self):
        """La consulta que HCM hará de verdad, en la frontera del año."""
        _regla(
            LaborRule.Kind.JORNADA_SEMANAL_HORAS_MAX,
            value=48,
            unit="horas/semana",
            article="59",
            effective_from="2026-01-01",
            effective_to="2026-12-31",
        )
        _regla(
            LaborRule.Kind.JORNADA_SEMANAL_HORAS_MAX,
            value=46,
            unit="horas/semana",
            article="59",
            effective_from="2027-01-01",
            effective_to="2027-12-31",
        )

        fin_2026 = self._get(kind="jornada_semanal_horas_max", on="2026-12-31").json()
        assert fin_2026["count"] == 1
        assert fin_2026["results"][0]["value"] == 48

        inicio_2027 = self._get(
            kind="jornada_semanal_horas_max", on="2027-01-01"
        ).json()
        assert inicio_2027["count"] == 1
        assert inicio_2027["results"][0]["value"] == 46

    def test_filtrar_por_pagador_incluye_las_reglas_sin_dimension(self):
        """Una regla 'any' aplica a cualquier pagador y no debe perderse.

        Si el filtro fuera de igualdad estricta, un consumidor que pregunta
        'soy persona moral' perdería la ventana del alta al IMSS, que no
        distingue por pagador. Ese sería un fallo silencioso.
        """
        _regla(LaborRule.Kind.IMSS_ALTA_VENTANA, value=5, article="15")
        _regla(
            LaborRule.Kind.RETENCION_ISR_HONORARIOS_PCT,
            value=10,
            article="106",
            payer_legal_form=LaborRule.PayerLegalForm.PERSONA_MORAL,
        )
        _regla(
            LaborRule.Kind.RETENCION_ISR_HONORARIOS_PCT,
            value=0,
            article="106",
            payer_legal_form=LaborRule.PayerLegalForm.PERSONA_FISICA,
        )

        moral = self._get(payer_legal_form="persona_moral").json()
        kinds = {r["kind"] for r in moral["results"]}
        assert "imss_alta_ventana_dias_habiles" in kinds
        valores = {
            r["value"]
            for r in moral["results"]
            if r["kind"] == "retencion_isr_honorarios_pct"
        }
        assert valores == {10}

    def test_all_published_es_falso_si_alguna_fila_no_esta_verificada(self):
        """El consumidor puede comprobar de un vistazo si puede calcular."""
        _regla(
            LaborRule.Kind.RECARACTERIZACION_INDICIOS,
            value={"lista": []},
            article="20",
            provenance=Provenance.SEED_UNVERIFIED,
        )
        cuerpo = self._get(kind="recaracterizacion_indicios").json()
        assert cuerpo["all_published"] is False
        assert cuerpo["results"][0]["is_verified"] is False

    def test_la_respuesta_trae_las_llaves_del_contrato_c1(self):
        _regla(LaborRule.Kind.AGUINALDO_DIAS_MIN, value=15, article="87")
        fila = self._get(kind="aguinaldo_dias_min").json()["results"][0]
        for llave in (
            "kind",
            "value",
            "unit",
            "effective_from",
            "effective_to",
            "official_id",
            "article",
            "source",
            "source_url",
            "dof_codigo",
            "provenance",
        ):
            assert llave in fila, f"falta la llave {llave} del contrato C1"


@pytest.mark.django_db
class TestCatalogosApi:
    """GET /api/v1/labor/catalogos/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = _make_user()
        self.url = reverse("labor-catalogos-list")

    def _get(self, **params):
        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            return self.client.get(self.url, params)

    def test_requires_authentication(self):
        assert self.client.get(self.url).status_code == 401

    def test_catalogo_invalido_es_400(self):
        assert self._get(catalog="c_Inventado").status_code == 400

    def test_filtra_por_catalogo_y_clave(self):
        SatCatalogEntry.objects.create(
            catalog=SatCatalogEntry.Catalog.TIPO_JORNADA,
            code="5",
            label="Reducida",
            official_id="sat_cat_nomina",
            article="c_TipoJornada",
            effective_from="2017-01-01",
            provenance=Provenance.PUBLISHED,
        )
        cuerpo = self._get(catalog="c_TipoJornada", code="5").json()
        assert cuerpo["count"] == 1
        assert cuerpo["results"][0]["label"] == "Reducida"

    def test_una_clave_dada_de_baja_no_aparece_despues_de_su_vigencia(self):
        """El 609 (Consolidación) dejó de estar vigente el 2020-01-01.

        Timbrar con una clave dada de baja es un rechazo del PAC; el feed debe
        poder decir que ese día ya no existía.
        """
        SatCatalogEntry.objects.create(
            catalog=SatCatalogEntry.Catalog.REGIMEN_FISCAL,
            code="609",
            label="Consolidación",
            official_id="sat_cat_cfdi",
            article="c_RegimenFiscal",
            effective_from="2016-11-12",
            effective_to="2020-01-01",
            provenance=Provenance.PUBLISHED,
        )
        assert (
            self._get(catalog="c_RegimenFiscal", on="2019-01-01").json()["count"] == 1
        )
        assert (
            self._get(catalog="c_RegimenFiscal", on="2024-01-01").json()["count"] == 0
        )


@pytest.mark.django_db
class TestPublicacion:
    """`publish_labor_rules`: la puerta por la que el seed entra a la base.

    Es el único código de este carril que escribe. Sin estas pruebas nadie
    sabría que respeta la guarda `LOCAL_DB`, que es append-only sobre lo ya
    publicado, ni que aborta sin escribir cuando el catálogo no se puede leer.
    """

    def _run(self, **kwargs):
        salida = io.StringIO()
        error = io.StringIO()
        call_command("publish_labor_rules", stdout=salida, stderr=error, **kwargs)
        return salida.getvalue(), error.getvalue()

    def test_dry_run_no_escribe_nada(self):
        """La opción por omisión: reporta lo que haría, sin tocar la base."""
        salida, _ = self._run(dry_run=True)
        assert "Publicaría" in salida
        assert LaborRule.objects.count() == 0
        assert SatCatalogEntry.objects.count() == 0

    def test_sin_local_db_se_niega_a_escribir(self, monkeypatch):
        """Escribir sin la guarda del repo sería un efecto colateral sorpresa."""
        monkeypatch.delenv("LOCAL_DB", raising=False)
        _, error = self._run()
        assert "Refusing to write" in error
        assert LaborRule.objects.count() == 0

    def test_escribe_con_local_db_y_es_idempotente(self, monkeypatch):
        """Segunda corrida: cero nuevas, todo intacto. Append-only de verdad."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        self._run()
        reglas, catalogos = LaborRule.objects.count(), SatCatalogEntry.objects.count()
        assert reglas == len(REGLAS)
        assert catalogos == len(json.loads(CATALOGOS_PATH.read_text(encoding="utf-8")))

        salida, _ = self._run()
        assert LaborRule.objects.count() == reglas
        assert SatCatalogEntry.objects.count() == catalogos
        assert f"Intactas (ya published): {reglas + catalogos - 1}" in salida

    def test_la_procedencia_del_seed_llega_intacta_a_la_base(self, monkeypatch):
        """El único seed-unverified no se promueve solo al escribirlo."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        self._run()
        indicios = LaborRule.objects.get(kind="recaracterizacion_indicios")
        assert indicios.provenance == Provenance.SEED_UNVERIFIED
        assert indicios.is_verified is False
        assert (
            LaborRule.objects.filter(provenance=Provenance.PUBLISHED).count()
            == len(REGLAS) - 1
        )

    def test_una_fila_sin_verificar_se_promueve_al_publicarla(self, monkeypatch):
        """Lo contrario sí: seed-unverified → published cuando llega la lectura."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        LaborRule.objects.create(
            kind=LaborRule.Kind.AGUINALDO_DIAS_MIN,
            value=0,
            official_id="lft",
            article="87",
            effective_from="1970-04-01",
            provenance=Provenance.SEED_UNVERIFIED,
        )
        salida, _ = self._run()
        promovida = LaborRule.objects.get(kind="aguinaldo_dias_min")
        assert promovida.provenance == Provenance.PUBLISHED
        assert promovida.value == 15
        assert "1 promovidas" in salida

    def test_un_catalogo_ilegible_aborta_sin_escribir_nada(self, monkeypatch, tmp_path):
        """Medio catálogo del SAT rechazaría claves buenas al timbrar."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        roto = tmp_path / "no_existe.json"
        _, error = self._run(catalogos=str(roto))
        assert "No se pudo leer el catálogo del SAT" in error
        # Ni las reglas, que se procesan primero, deben quedar a medias.
        assert LaborRule.objects.count() == 0
