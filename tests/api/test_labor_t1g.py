"""Lo que los carriles HP-2, HP-3, HP-5 y HP-0d piden a Tezca (T-1g).

La compuerta central es ``test_todo_lo_que_los_carriles_piden_existe``: fija,
por nombre, cada ``kind`` y cada catálogo del SAT que un carril HP-* pidió río
arriba, y falla si alguno no está publicado **ni** declarado como hueco con
motivo. Entra con ``HUECOS_DECLARADOS`` vacío.

**Está roja sobre ``main``** y por tres razones distintas, todas verificadas en
el carril:

* ``sbc_tope_veces_uma`` y ``seguro_facultativo_estudiantes_incorporacion`` no
  existen ni siquiera como ``kind`` del modelo;
* ``c_TipoPercepcion``, ``c_TipoDeduccion`` y ``c_TipoOtroPago`` no están en
  ``SatCatalogEntry.Catalog`` ni en ``data/labor/sat_catalogos.json``;
* la fila del JCF cita el DOF 5746424 (Reglas **2025**, abrogadas) con
  ``official_id`` vacío.

Las tres correcciones de cita que este carril publica —el art. 28 se lee en
UMA por un transitorio y no por una reforma, el seguro de estudiantes no se
funda ni en LSS 13 fr. V ni en LSS 240, y las Reglas del JCF de 2026 ya no
obligan al Centro de Trabajo a verificar la evaluación— tienen cada una su
prueba, para que nadie las revierta al fundamento cómodo sin que se note.
"""

import io
import json
from datetime import date
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.api.fiscal_models import Provenance
from apps.api.labor_coherence import huecos_en_la_serie, vigencias_traslapadas
from apps.api.labor_models import LaborRule, SatCatalogEntry
from apps.api.labor_seed_data import REGLAS
from apps.api.labor_seed_hcm import REGLAS_HCM
from apps.api.labor_seed_t1g import REGLAS_T1G

#: El mismo archivo que lee `publish_labor_rules`, anclado a la raíz del repo
#: y no al cwd — igual que en `test_labor_rules`.
CATALOGOS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "labor" / "sat_catalogos.json"
)

#: Lo que los carriles HP-* piden a Tezca, leído de los cuerpos de sus PR y de
#: sus ``docs/hardening/hp*-*.md`` el 2026-09-06. Nombre del carril → petición.
PEDIDOS_KIND = {
    "sbc_tope_veces_uma": "HP-2 (#97): el tope del art. 28 de la LSS como número",
    "seguro_facultativo_estudiantes_incorporacion": (
        "HP-5 (#99): el seguro de estudiantes para prácticas y servicio social"
    ),
    "jcf_validacion_periodicidad_dias": (
        "HP-0d (#103): la misma regla, citando las Reglas de Operación 2026"
    ),
}

#: Catálogos del SAT que HP-3 (#100) pide para poder timbrar asimilados sin
#: llevar la clave 046 escrita a mano en el código del HCM.
PEDIDOS_CATALOGO = {
    "c_TipoPercepcion": "HP-3 (#100): la clave 046 'Ingresos asimilados a salarios'",
    "c_TipoDeduccion": "HP-3 (#100): la clave 001 'Seguridad social'",
    "c_TipoOtroPago": "HP-3 (#100): la clave 002 'Subsidio para el empleo'",
}

#: Las claves concretas que los carriles nombran. Que el catálogo exista no
#: basta: si la clave que el consumidor va a escribir en el CFDI no está, el
#: timbrado falla igual.
CLAVES_QUE_LOS_CARRILES_USAN = [
    ("c_TipoPercepcion", "001", "Sueldos"),
    ("c_TipoPercepcion", "002", "Gratificación Anual"),
    ("c_TipoPercepcion", "046", "Ingresos asimilados a salarios"),
    ("c_TipoDeduccion", "001", "Seguridad social"),
    ("c_TipoDeduccion", "002", "ISR"),
    ("c_TipoOtroPago", "002", "Subsidio para el empleo"),
]

#: Lo que un carril pidió y Tezca NO publica, con su motivo. Vacío hoy: los
#: tres kind y los tres catálogos se responden. Existe para que un hueco
#: futuro se declare aquí, a la vista, y no como una prueba que alguien borró.
HUECOS_DECLARADOS: dict[str, str] = {}


@pytest.fixture(scope="module")
def kinds_publicados():
    return {r["kind"] for r in REGLAS if r["provenance"] == Provenance.PUBLISHED}


@pytest.fixture(scope="module")
def catalogo():
    return json.loads(CATALOGOS_PATH.read_text(encoding="utf-8"))


class TestLoQueLosCarrilesPiden:
    """La compuerta: nada pedido queda sin respuesta ni sin motivo."""

    def test_todo_lo_que_los_carriles_piden_existe(self, kinds_publicados, catalogo):
        publicados = kinds_publicados | {f["catalog"] for f in catalogo}
        pedidos = set(PEDIDOS_KIND) | set(PEDIDOS_CATALOGO)
        sin_responder = pedidos - publicados - set(HUECOS_DECLARADOS)
        assert not sin_responder, (
            "Carriles HP-* piden a Tezca cosas que no publica y que tampoco "
            f"están en HUECOS_DECLARADOS: {sorted(sin_responder)}. Publícalas "
            "con lectura primaria o decláralas como hueco con su motivo."
        )

    def test_los_huecos_declarados_lo_estan_de_verdad(self, kinds_publicados, catalogo):
        """Un hueco que ya se publicó debe salir de la lista, o es folclore."""
        publicados = kinds_publicados | {f["catalog"] for f in catalogo}
        for nombre, motivo in HUECOS_DECLARADOS.items():
            assert nombre not in publicados, (
                f"'{nombre}' está declarado como hueco ('{motivo}') pero ya se "
                "publica. Quítalo de HUECOS_DECLARADOS."
            )
            assert motivo.strip(), f"El hueco '{nombre}' no dice por qué lo es."

    def test_los_kind_pedidos_existen_en_el_modelo(self):
        del_modelo = {k.value for k in LaborRule.Kind}
        assert not set(PEDIDOS_KIND) - del_modelo

    def test_los_catalogos_pedidos_existen_en_el_modelo(self):
        del_modelo = {c.value for c in SatCatalogEntry.Catalog}
        assert not set(PEDIDOS_CATALOGO) - del_modelo


class TestTopeDelSbc:
    """HP-2: el art. 28 de la LSS, con la unidad correcta en cada época."""

    @staticmethod
    @pytest.fixture(scope="class")
    def filas():
        return sorted(
            (r for r in REGLAS_T1G if r["kind"] == "sbc_tope_veces_uma"),
            key=lambda r: r["effective_from"],
        )

    def test_son_dos_vigencias_contiguas(self, filas):
        """Una por unidad de cuenta: salario mínimo hasta 2016, UMA después."""
        assert len(filas) == 2
        assert filas[0]["effective_to"] == "2016-01-27"
        assert filas[1]["effective_from"] == "2016-01-28"
        # La fila vigente omite `effective_to`, como el resto del seed: la
        # clave ausente y `None` significan lo mismo para `publish_labor_rules`
        # (`regla.get("effective_to")`), y el seed prefiere no escribirla.
        assert filas[1].get("effective_to") is None

    def test_el_multiplicador_es_veinticinco_en_las_dos(self, filas):
        """La desindexación cambió la unidad, no el número."""
        assert [f["value"]["veces"] for f in filas] == [25, 25]

    def test_la_unidad_cambia_con_el_decreto(self, filas):
        assert filas[0]["value"]["unidad"] == "salario_minimo"
        assert filas[1]["value"]["unidad"] == "uma"

    def test_el_piso_no_se_desindexa(self, filas):
        """El límite INFERIOR sigue en salario mínimo, en las dos filas.

        Es el error más fácil de cometer: convertir el artículo entero a UMA.
        El transitorio TERCERO sólo alcanza a las menciones que usan el
        salario mínimo como unidad de cuenta; el piso del SBC lo usa como
        salario, que es su naturaleza propia y lo que el art. 123 A fr. VI
        reformado protege expresamente.
        """
        for fila in filas:
            assert fila["value"]["limite_inferior"]["unidad"] == "salario_minimo"

    def test_la_fila_en_uma_se_funda_en_el_decreto_no_en_una_reforma(self, filas):
        """El art. 28 nunca se reformó: citar una reforma sería inventarla."""
        uma = filas[1]
        assert uma["dof_codigo"] == "5423663"
        assert uma["dof_date"] == "2016-01-27"
        assert uma["article"] == "28"
        assert "transitorio" in uma["notes"].lower()

    def test_las_dos_filas_citan_el_mismo_articulo(self, filas):
        """Porque es el mismo artículo, con el mismo texto, leído distinto."""
        assert {f["article"] for f in filas} == {"28"}
        assert {f["official_id"] for f in filas} == {"lss"}


class TestSeguroDeEstudiantes:
    """HP-5: ni LSS 13 fr. V ni LSS 240, y sin ventana."""

    @staticmethod
    @pytest.fixture(scope="class")
    def fila():
        (unica,) = [
            r
            for r in REGLAS_T1G
            if r["kind"] == "seguro_facultativo_estudiantes_incorporacion"
        ]
        return unica

    def test_no_se_atribuye_al_articulo_13(self, fila):
        """LSS 13 fr. V son los trabajadores de las administraciones públicas.

        La fracción que el plan cita no habla de estudiantes, y las fracciones
        III y IV —las que en su día cubrían otros colectivos— están derogadas
        desde 2019 y 2023.
        """
        assert not fila["article"].startswith("13")

    def test_no_se_atribuye_al_articulo_240(self, fila):
        """LSS 240 es el seguro de salud para la FAMILIA, no para estudiantes."""
        assert fila["article"] != "240"

    def test_se_funda_en_el_12_fraccion_iii_y_en_el_decreto(self, fila):
        """El artículo que faculta al Ejecutivo, más el decreto que lo ejerce."""
        assert fila["official_id"] == "lss"
        assert fila["article"] == "12-III"
        assert fila["dof_codigo"] == "4892913"
        assert fila["dof_date"] == "1998-09-14"

    def test_no_inventa_ventana(self, fila):
        """El decreto no fija plazo. Declararlo es la respuesta correcta.

        HP-5 pidió el kind como ``seguro_facultativo_ventana_dias``. Publicar
        un número de días para que el nombre cuadre habría sido exactamente lo
        que este feed existe para impedir.
        """
        assert fila["value"]["hay_ventana"] is False
        assert fila["value"]["motivo_sin_ventana"].strip()
        assert fila["unit"] == "regla"

    def test_dice_que_no_es_facultativo(self, fila):
        """La LSS de 1997 suprimió esa figura; es régimen OBLIGATORIO."""
        assert fila["value"]["es_seguro_facultativo"] is False
        assert fila["value"]["regimen"] == "obligatorio"

    def test_dice_que_no_la_cumple_el_centro_de_trabajo(self, fila):
        """La cobertura deriva de ser estudiante, no del vínculo formativo.

        Sin esto, HP-5 podría pintarla como una obligación del inquilino que
        recibe a la persona en prácticas, y no lo es.
        """
        assert fila["value"]["para_practicas_y_servicio_social"].strip()
        assert "institución educativa" in fila["value"]["quien_inscribe"]


class TestJcfReglas2026:
    """HP-0d: la cita nueva y —lo que importa más— el fondo que cambió."""

    @staticmethod
    @pytest.fixture(scope="class")
    def vieja():
        (unica,) = [
            r for r in REGLAS_HCM if r["kind"] == "jcf_validacion_periodicidad_dias"
        ]
        return unica

    @staticmethod
    @pytest.fixture(scope="class")
    def nueva():
        (unica,) = [
            r for r in REGLAS_T1G if r["kind"] == "jcf_validacion_periodicidad_dias"
        ]
        return unica

    def test_la_vieja_se_cierra_en_vez_de_editarse(self, vieja):
        """Append-only: su cita de 2024 sigue siendo la que Tezca dio en 2025."""
        assert vieja["dof_codigo"] == "5746424"
        assert vieja["official_id"] == ""
        assert vieja["effective_to"] == "2025-12-31"

    def test_la_nueva_cita_las_reglas_de_2026(self, nueva):
        assert nueva["official_id"] == "jcf-reglas-2026"
        assert nueva["dof_codigo"] == "5777674"
        assert nueva["dof_date"] == "2025-12-31"
        assert nueva["effective_from"] == "2026-01-01"

    def test_la_nueva_no_arrastra_el_codigo_abrogado(self, nueva):
        """Es la corrección que HP-0d pide: 5746424 son las Reglas de 2025."""
        assert nueva["dof_codigo"] != "5746424"

    def test_las_reglas_2026_ya_no_obligan_al_centro_de_trabajo(self, nueva):
        """El fondo, no la cita.

        Las Reglas 2024 obligaban al Centro de Trabajo a «verificar que cada
        Tutora o Tutor designado evalúe mensualmente» (fr. X de sus
        obligaciones). Las XXIV fracciones del apartado D) de la regla Décima
        Segunda de 2026 **no traen esa obligación**: evaluar es un derecho de
        la Tutora o Tutor y de la persona aprendiz. Copiar la nota de 2024
        sobre la cita de 2026 habría dejado a HCM exigiendo una obligación que
        las Reglas vigentes ya no imponen.
        """
        assert nueva["value"]["es_obligacion_del_centro_de_trabajo"] is False
        assert nueva["value"]["cambio_frente_a_2024"].strip()

    def test_la_nueva_no_promete_afirmativa_ficta(self, nueva, vieja):
        """La fila de 2024 prometía afirmativa ficta; la de 2026 la niega.

        Se comprueba por contraste y no por ausencia de la cadena: la nota de
        2026 **nombra** la figura para decir que no existe, y una prueba que
        sólo buscara la frase se pondría roja por decir la verdad. Lo que no
        puede volver es la promesa: que no validar deje pasar el pago «por
        afirmativa ficta», que era el efecto de las Reglas 2024.
        """
        assert "afirmativa ficta" in vieja["value"]["efecto_de_no_validar"].lower()
        efecto_2026 = nueva["value"]["efecto_de_no_validar"].lower()
        assert "no existe" in efecto_2026
        assert "no aparece en el documento" in efecto_2026

    def test_sigue_siendo_un_ciclo_y_no_un_plazo_en_dias(self, nueva):
        """El nombre del kind dice 'dias' por C1; la fuente dice un ciclo."""
        assert nueva["unit"] == "ciclo_mensual"
        assert nueva["value"]["periodicidad"] == "mensual"
        assert nueva["value"]["ventana"] == "ultima_semana_del_mes"


class TestCatalogosDeNomina:
    """HP-3: los tres catálogos del complemento, fila por fila con procedencia."""

    @staticmethod
    @pytest.fixture(scope="class")
    def nuevos():
        filas = json.loads(CATALOGOS_PATH.read_text(encoding="utf-8"))
        return [f for f in filas if f["catalog"] in PEDIDOS_CATALOGO]

    def test_hay_filas_de_los_tres(self, nuevos):
        assert {f["catalog"] for f in nuevos} == set(PEDIDOS_CATALOGO)

    @pytest.mark.parametrize("catalog,code,fragmento", CLAVES_QUE_LOS_CARRILES_USAN)
    def test_la_clave_que_el_carril_usa_existe(self, nuevos, catalog, code, fragmento):
        """No basta el catálogo: la clave concreta tiene que estar."""
        coincidencias = [
            f for f in nuevos if f["catalog"] == catalog and f["code"] == code
        ]
        assert len(coincidencias) == 1, f"{catalog} {code} no está exactamente una vez"
        assert fragmento.lower() in coincidencias[0]["label"].lower()

    def test_toda_fila_declara_su_procedencia(self, nuevos):
        """Fila por fila: archivo de origen, versión del .xls y URL."""
        for fila in nuevos:
            assert fila["catalogo_origen"] == "sat_cat_nomina", fila["code"]
            assert fila["source_url"].endswith("catNomina.xls"), fila["code"]
            assert fila["catalogo_version"].strip(), fila["code"]
            assert fila["effective_from"], fila["code"]

    def test_las_claves_no_se_repiten_dentro_de_una_vigencia(self, nuevos):
        """La clave natural de SatCatalogEntry es (catálogo, clave, vigencia)."""
        identidades = {(f["catalog"], f["code"], f["effective_from"]) for f in nuevos}
        assert len(identidades) == len(nuevos)

    def test_la_baja_de_una_clave_se_conserva(self, nuevos):
        """El SAT da de baja claves y el .xls lo imprime; no se descarta.

        La deducción 072 tiene fin de vigencia el 2018-10-14. Un consumidor
        que timbre un CFDI de 2018 necesita saber que existía; uno que timbre
        hoy, que ya no. Descartar las claves con baja habría perdido esa
        respuesta.
        """
        bajas = [f for f in nuevos if f["effective_to"]]
        assert bajas, "ninguna clave con baja: ¿se filtraron al transcribir?"
        assert any(
            f["catalog"] == "c_TipoDeduccion" and f["code"] == "072" for f in bajas
        )


class TestCoherenciaConElSeedCompleto:
    """Las filas nuevas no rompen las compuertas que ya existían."""

    def test_no_introducen_traslapes(self):
        assert vigencias_traslapadas(REGLAS) == []

    def test_no_introducen_huecos(self):
        assert huecos_en_la_serie(REGLAS) == []

    def test_las_filas_de_este_carril_son_todas_published(self):
        """Ninguna entra sin verificar: las cuatro se leyeron de la fuente."""
        assert [
            r["kind"] for r in REGLAS_T1G if r["provenance"] != Provenance.PUBLISHED
        ] == []

    def test_toda_fila_de_este_carril_trae_procedencia_completa(self):
        for regla in REGLAS_T1G:
            assert regla["source"], regla["kind"]
            assert regla["source_url"].startswith("https://"), regla["kind"]
            assert len(regla["notes"].strip()) > 40, regla["kind"]


@pytest.mark.django_db
class TestElConsumidorPuedeLeerlas:
    """De extremo a extremo: publicar y consultar como lo hace el HCM."""

    @pytest.fixture(autouse=True)
    def _publicado(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_labor_rules", stdout=io.StringIO())

    def test_el_tope_del_sbc_responde_uma_hoy_y_minimo_en_2010(self):
        """La misma pregunta, dos respuestas, según la fecha del cálculo."""
        hoy = LaborRule.objects.get(
            kind="sbc_tope_veces_uma",
            effective_from__lte=date(2026, 9, 6),
            effective_to__isnull=True,
        )
        assert hoy.value["unidad"] == "uma"
        assert hoy.value["veces"] == 25

        antes = LaborRule.objects.get(
            kind="sbc_tope_veces_uma",
            effective_from__lte=date(2010, 6, 30),
            effective_to__gte=date(2010, 6, 30),
        )
        assert antes.value["unidad"] == "salario_minimo"

    def test_el_dia_del_corte_no_es_ambiguo(self):
        """27 y 28 de enero de 2016 devuelven, cada uno, exactamente una fila."""
        for dia, unidad in (
            (date(2016, 1, 27), "salario_minimo"),
            (date(2016, 1, 28), "uma"),
        ):
            filas = LaborRule.objects.filter(kind="sbc_tope_veces_uma").filter(
                effective_from__lte=dia
            )
            vigentes = [
                f for f in filas if f.effective_to is None or f.effective_to >= dia
            ]
            assert len(vigentes) == 1, f"{dia} tiene {len(vigentes)} filas vigentes"
            assert vigentes[0].value["unidad"] == unidad

    def test_el_jcf_responde_las_reglas_2026_este_anio(self):
        """Preguntar por hoy debe traer 5777674, no el código abrogado."""
        fila = LaborRule.objects.get(
            kind="jcf_validacion_periodicidad_dias",
            effective_from__lte=date(2026, 9, 6),
            effective_to__isnull=True,
        )
        assert fila.official_id == "jcf-reglas-2026"
        assert fila.dof_codigo == "5777674"

    def test_el_jcf_de_2025_sigue_respondiendo_las_reglas_2024(self):
        """Append-only: la historia no se reescribe."""
        fila = LaborRule.objects.get(
            kind="jcf_validacion_periodicidad_dias",
            effective_from__lte=date(2025, 6, 30),
            effective_to__gte=date(2025, 6, 30),
        )
        assert fila.dof_codigo == "5746424"

    def test_el_seguro_de_estudiantes_llega_como_published(self):
        fila = LaborRule.objects.get(
            kind="seguro_facultativo_estudiantes_incorporacion"
        )
        assert fila.is_verified
        assert fila.article == "12-III"

    @pytest.mark.parametrize("catalog,code,_frag", CLAVES_QUE_LOS_CARRILES_USAN)
    def test_cada_clave_del_carril_es_consultable(self, catalog, code, _frag):
        """El camino completo: comando → modelo → consulta por vigencia."""
        filas = SatCatalogEntry.objects.filter(
            catalog=catalog, code=code, provenance=Provenance.PUBLISHED
        )
        assert filas.count() == 1


class TestFalsabilidadDeLaCompuerta:
    """La compuerta se pone roja ante lo que dice atrapar."""

    def test_un_pedido_sin_publicar_se_detecta(self, kinds_publicados, catalogo):
        publicados = kinds_publicados | {f["catalog"] for f in catalogo}
        pedidos = set(PEDIDOS_KIND) | {"kind_que_ningun_carril_publica"}
        assert pedidos - publicados - set(HUECOS_DECLARADOS) == {
            "kind_que_ningun_carril_publica"
        }

    def test_borrar_el_tope_del_sbc_se_detecta(self):
        """Si alguien quita la fila que HP-2 pide, la compuerta lo ve."""
        publicados = {
            r["kind"]
            for r in REGLAS
            if r["provenance"] == Provenance.PUBLISHED
            and r["kind"] != "sbc_tope_veces_uma"
        }
        assert "sbc_tope_veces_uma" in set(PEDIDOS_KIND) - publicados

    def test_quitar_un_catalogo_se_detecta(self, catalogo):
        """Si una reimportación pierde c_TipoPercepcion, la compuerta lo ve."""
        publicados = {
            f["catalog"] for f in catalogo if f["catalog"] != "c_TipoPercepcion"
        }
        assert "c_TipoPercepcion" in set(PEDIDOS_CATALOGO) - publicados
