"""El contrato con el catálogo de obligaciones del HCM (T-1c).

La compuerta central de este carril es ``test_todo_kind_del_hcm_existe``: fija
la lista completa de ``regla_ventana_kind`` que el catálogo del HCM
(``apps/api/cumplimiento/catalogo_seed.py`` en symbiosis-hcm) consulta, y falla
si alguno no está publicado en Tezca **ni** declarado como hueco con motivo.

Es falsable en las dos direcciones y por eso sirve:

* si alguien borra una regla del seed, la prueba se pone en rojo;
* si el HCM añade un ``kind`` nuevo, hay que añadirlo aquí, y entonces la
  prueba obliga a publicarlo o a declararlo hueco — no se puede ignorar.

``KINDS_DEL_CATALOGO_HCM`` se transcribe del catálogo del HCM leído el
2026-09-06 en ``origin/main`` (PR #90, carril HP-0). No es una lista de deseos:
es lo que el consumidor pregunta hoy.
"""

import io
from datetime import date

import pytest
from django.core.management import call_command

from apps.api.fiscal_models import Provenance
from apps.api.labor_coherence import huecos_en_la_serie, vigencias_traslapadas
from apps.api.labor_models import LaborRule
from apps.api.labor_seed_data import REGLAS
from apps.api.labor_seed_hcm import REGLAS_HCM

#: Todo ``regla_ventana_kind`` no vacío del catálogo de obligaciones del HCM.
#: Catorce en total: diez ya publicados por T-1a/T-1b y los cuatro de T-1c.
KINDS_DEL_CATALOGO_HCM = {
    "aguinaldo_fecha_limite",
    "cfdi_nomina_por_periodo",
    "comisiones_mixtas_umbral_personas",
    "contrato_escrito_desde_inicio",
    "imss_alta_ventana_dias_habiles",
    "jcf_validacion_periodicidad_dias",
    "nom035_umbral_personas",
    "opinion_32d_vigencia_dias",
    "prima_vacacional_pct_min",
    "prueba_dias_max",
    "ptu_fecha_limite_dias",
    "repse_obligatorio_condiciones",
    "teletrabajo_umbral_pct",
    "vacaciones_dias_por_anio",
}

#: Los ``kind`` que el HCM consulta y que Tezca NO publica, con su motivo.
#: Vacío hoy. Existe para que un hueco futuro se declare aquí, a la vista, en
#: vez de aparecer como una prueba que alguien silenció.
HUECOS_DECLARADOS: dict[str, str] = {}

#: Los cuatro que abre este carril, con el artículo que los sostiene.
ESPERADO_T1C = {
    "opinion_32d_vigencia_dias": ("rmf", "2.1.36"),
    "cfdi_nomina_por_periodo": ("lisr", "99-III"),
    "comisiones_mixtas_umbral_personas": ("lft", "153-E"),
    "jcf_validacion_periodicidad_dias": ("", "Reglas de Operación JCF"),
}


@pytest.fixture(scope="module")
def kinds_publicados():
    """Los ``kind`` con al menos una fila utilizable por el consumidor."""
    return {
        regla["kind"] for regla in REGLAS if regla["provenance"] == Provenance.PUBLISHED
    }


class TestContratoConElCatalogoDelHcm:
    """La compuerta: nada que el HCM pregunte queda sin respuesta ni sin motivo."""

    def test_todo_kind_del_hcm_existe(self, kinds_publicados):
        """Cada kind del catálogo del HCM está publicado o declarado hueco.

        Entra con ``HUECOS_DECLARADOS`` vacío: hoy los catorce se responden.
        """
        sin_responder = KINDS_DEL_CATALOGO_HCM - kinds_publicados
        no_declarados = sin_responder - set(HUECOS_DECLARADOS)
        assert not no_declarados, (
            "El catálogo del HCM consulta kinds que Tezca no publica y que "
            f"tampoco están en HUECOS_DECLARADOS: {sorted(no_declarados)}. "
            "Publícalos con lectura primaria o decláralos como hueco con su "
            "motivo — el consumidor los pinta como «ventana por publicar»."
        )

    def test_los_huecos_declarados_lo_estan_de_verdad(self, kinds_publicados):
        """Un hueco declarado que ya se publicó debe salir de la lista.

        Si no, la lista se convierte en folclore: nadie la limpia y deja de
        decir la verdad sobre lo que falta.
        """
        for kind, motivo in HUECOS_DECLARADOS.items():
            assert kind not in kinds_publicados, (
                f"'{kind}' está declarado como hueco ('{motivo}') pero ya se "
                "publica. Quítalo de HUECOS_DECLARADOS."
            )
            assert motivo.strip(), f"El hueco '{kind}' no dice por qué lo es."

    def test_todo_kind_del_hcm_es_un_kind_valido_del_modelo(self):
        """Un kind del HCM que no exista en el enum es un contrato roto."""
        del_modelo = {k.value for k in LaborRule.Kind}
        desconocidos = KINDS_DEL_CATALOGO_HCM - del_modelo
        assert not desconocidos, (
            f"El HCM consulta kinds que LaborRule.Kind no define: "
            f"{sorted(desconocidos)}."
        )


class TestReglasDeEsteCarril:
    """Que las cuatro filas nuevas digan lo que dice la fuente que se leyó."""

    @staticmethod
    @pytest.fixture(scope="class")
    def por_kind():
        return {regla["kind"]: regla for regla in REGLAS_HCM}

    def test_son_exactamente_cuatro(self):
        assert len(REGLAS_HCM) == 4
        assert {r["kind"] for r in REGLAS_HCM} == set(ESPERADO_T1C)

    def test_todas_con_lectura_primaria(self):
        """Ninguna entra como seed-unverified: las cuatro se leyeron."""
        sin_verificar = [
            r["kind"] for r in REGLAS_HCM if r["provenance"] != Provenance.PUBLISHED
        ]
        assert sin_verificar == []

    @pytest.mark.parametrize("kind,esperado", sorted(ESPERADO_T1C.items()))
    def test_cada_regla_cita_el_articulo_que_la_sostiene(
        self, por_kind, kind, esperado
    ):
        official_id, article = esperado
        regla = por_kind[kind]
        assert regla["official_id"] == official_id
        assert regla["article"].startswith(article)

    def test_la_opinion_32d_dura_treinta_dias_naturales(self, por_kind):
        """RMF 2026 2.1.36: 'vigencia de treinta días naturales'."""
        regla = por_kind["opinion_32d_vigencia_dias"]
        assert regla["value"] == 30
        assert regla["unit"] == "dias_naturales"
        # La RMF es anual y la fila se cierra con ella: preguntar por 2027 debe
        # devolver 'no hay regla', no la de 2026 extrapolada.
        assert regla["effective_from"] == "2026-01-01"
        assert regla["effective_to"] == "2026-12-31"
        assert regla["dof_codigo"] == "5777217"

    def test_la_opinion_32d_no_se_atribuye_al_cff(self, por_kind):
        """El CFF 32-D no fija plazo: publicarlo ahí sería inventarlo.

        Es la corrección al catálogo del HCM, fijada como prueba para que no
        se revierta sin que alguien lo note.
        """
        assert por_kind["opinion_32d_vigencia_dias"]["official_id"] != "cff"

    def test_el_cfdi_de_nomina_se_ata_a_la_erogacion(self, por_kind):
        """LISR 99 fr. III: 'en la fecha en que se realice la erogación'."""
        valor = por_kind["cfdi_nomina_por_periodo"]["value"]
        assert valor["disparo"] == "erogacion"
        # El nombre del kind dice 'por_periodo' por el contrato C1; el valor no
        # puede repetir esa suposición.
        assert "periodo" not in valor["disparo"]

    def test_las_comisiones_mixtas_son_mas_de_cincuenta(self, por_kind):
        """LFT 153-E: 'más de 50 trabajadores'. Con 50 no hay obligación."""
        valor = por_kind["comisiones_mixtas_umbral_personas"]["value"]
        assert valor["umbral_personas"] == 50
        assert valor["comparador"] == "mayor_que"
        # El umbral es estricto: la fila lo dice dos veces a propósito, porque
        # '50' y 'a partir de 51' se confunden con facilidad.
        assert valor["obligatoria_desde_personas"] == 51

    def test_las_comisiones_mixtas_no_se_atribuyen_al_132(self, por_kind):
        """LFT 132 fr. XXVIII obliga a participar, pero no fija umbral."""
        assert por_kind["comisiones_mixtas_umbral_personas"]["article"] == "153-E"

    def test_la_validacion_jcf_es_un_ciclo_no_un_plazo_en_dias(self, por_kind):
        """Las Reglas fijan un ciclo mensual con ventana, no N días.

        Publicarlo como un número de días invitaría a HCM a restar 30 días a
        una fecha de alta y a mostrar un vencimiento que las Reglas no fijan.
        """
        regla = por_kind["jcf_validacion_periodicidad_dias"]
        assert regla["unit"] == "ciclo_mensual"
        assert regla["value"]["periodicidad"] == "mensual"
        assert regla["value"]["ventana"] == "ultima_semana_del_mes"

    def test_la_regla_jcf_se_cita_por_dof_aunque_no_tenga_official_id(self, por_kind):
        """Sin id en el corpus, la procedencia la sostienen código y fecha."""
        regla = por_kind["jcf_validacion_periodicidad_dias"]
        assert regla["official_id"] == ""
        assert regla["dof_codigo"] == "5746424"
        assert regla["dof_date"] == "2024-12-31"

    def test_toda_fila_trae_procedencia_completa(self):
        """Publicado sin fuente sería una aserción sin respaldo."""
        for regla in REGLAS_HCM:
            assert regla["source"], regla["kind"]
            assert regla["source_url"].startswith("https://"), regla["kind"]
            assert regla["notes"].strip(), regla["kind"]


class TestCoherenciaConElSeedCompleto:
    """Las filas nuevas no rompen las compuertas que ya existían."""

    def test_no_introducen_traslapes(self):
        assert vigencias_traslapadas(REGLAS) == []

    def test_no_introducen_huecos(self):
        assert huecos_en_la_serie(REGLAS) == []


@pytest.mark.django_db
class TestElHcmPuedeLeerlas:
    """De extremo a extremo: publicar y luego consultar como lo hace el HCM.

    Que la fila exista en el seed no prueba que el consumidor la reciba: entre
    una cosa y otra están el comando, el modelo y el serializer. Estas pruebas
    recorren ese camino con la consulta exacta del contrato C1.
    """

    @pytest.fixture(autouse=True)
    def _publicado(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_labor_rules", stdout=io.StringIO())

    @pytest.mark.parametrize("kind", sorted(ESPERADO_T1C))
    def test_cada_kind_nuevo_llega_a_la_base_como_published(self, kind):
        filas = LaborRule.objects.filter(kind=kind, provenance=Provenance.PUBLISHED)
        # El JCF tiene DOS filas desde T-1g: la de las Reglas 2024 (cerrada el
        # 31-12-2025) y la de las Reglas 2026. Es append-only funcionando, no
        # una duplicación: `TestJcfReglas2026` comprueba que sólo una rige
        # cualquier día dado, y `vigencias_traslapadas` lo respalda.
        esperadas = 2 if kind == "jcf_validacion_periodicidad_dias" else 1
        assert filas.count() == esperadas, (
            f"'{kind}' quedó publicado {filas.count()} veces y se esperaban "
            f"{esperadas}"
        )

    def test_la_opinion_32d_responde_dentro_de_su_vigencia_y_calla_fuera(self):
        """La RMF 2026 no puede contestar por 2027: es otra Resolución."""
        dentro = LaborRule.objects.filter(
            kind="opinion_32d_vigencia_dias",
            effective_from__lte=date(2026, 6, 30),
            effective_to__gte=date(2026, 6, 30),
        )
        assert dentro.count() == 1
        assert dentro.first().value == 30

        fuera = LaborRule.objects.filter(
            kind="opinion_32d_vigencia_dias",
            effective_from__lte=date(2027, 6, 30),
            effective_to__gte=date(2027, 6, 30),
        )
        assert not fuera.exists()

    def test_la_regla_del_jcf_es_utilizable_pese_a_no_tener_official_id(self):
        """El consumidor sólo exige provenance='published', no official_id.

        Se comprueba sobre la fila de 2024, que es la que nació sin
        identificador en el corpus. Su sucesora de T-1g sí lo tiene
        (``jcf-reglas-2026``), y eso NO invalida la propiedad que esta prueba
        fija: una fila sin ``official_id`` sigue siendo utilizable, porque la
        procedencia la sostienen ``dof_codigo`` y ``dof_date``.
        """
        fila = LaborRule.objects.get(
            kind="jcf_validacion_periodicidad_dias",
            effective_from=date(2024, 12, 31),
        )
        assert fila.is_verified
        assert fila.official_id == ""
        assert fila.dof_codigo == "5746424"
        # Cerrada por T-1g: las Reglas 2026 la abrogan.
        assert fila.effective_to == date(2025, 12, 31)


class TestFalsabilidadDeLaCompuerta:
    """La compuerta del catálogo se pone en rojo ante lo que dice atrapar."""

    def test_un_kind_del_hcm_sin_publicar_se_detecta(self, kinds_publicados):
        """Simula que el HCM pide un kind que Tezca no tiene."""
        hcm_mutado = KINDS_DEL_CATALOGO_HCM | {"kind_que_nadie_publica"}
        sin_responder = hcm_mutado - kinds_publicados - set(HUECOS_DECLARADOS)
        assert sin_responder == {"kind_que_nadie_publica"}

    def test_borrar_una_regla_publicada_se_detecta(self):
        """Si alguien quita la fila del 32-D, la compuerta lo ve."""
        publicados = {
            r["kind"]
            for r in REGLAS
            if r["provenance"] == Provenance.PUBLISHED
            and r["kind"] != "opinion_32d_vigencia_dias"
        }
        assert "opinion_32d_vigencia_dias" in KINDS_DEL_CATALOGO_HCM - publicados
