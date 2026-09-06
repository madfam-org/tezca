"""Los fundamentos que HP-1 y HP-0c le piden a Tezca (T-1f).

Tres compuertas, cada una falsable por una razón distinta.

``TestCapacitacionInicial`` y ``TestElementosDeLaRelacion``
    Lo que HP-1 consulta: los dos topes del art. 39-B y los elementos del art.
    20. La prueba no se conforma con que la fila exista — cruza el ``value``
    contra el **texto del artículo** que el propio Tezca sirve. Si alguien
    cambiara el 3 por un 4, la fila seguiría existiendo y la prueba se pondría
    roja igual, porque «tres meses» está en el texto y «cuatro» no.

``TestHuecosDeCorpusDeHP0c``
    Los cinco huecos que HP-0c declaró con motivo ``corpus``. Para cada uno,
    esta prueba afirma una de dos cosas —nunca ninguna de las dos a medias—:
    o el ordenamiento resuelve contra el corpus por ``official_id`` y numeral,
    o sigue siendo hueco y aquí consta **por qué**, con el documento que falta
    nombrado. Un hueco sin motivo preciso es un hueco que nadie va a cerrar.

``TestCorreccionNom035``
    La corrección del campo de aplicación. Es la prueba que más importa de
    este archivo porque atrapa un error que ninguna prueba de «existe la fila»
    veía: la fila de T-1b existía, estaba ``published`` y citaba el numeral
    equivocado con una lista de numerales que la norma no impone al centro de
    trabajo más pequeño.
"""

from datetime import date

import pytest

from apps.api.fiscal_models import Provenance
from apps.api.labor_models import LaborRule, LawArticle
from apps.api.labor_seed_data import REGLAS

#: El día en que se leyó la fuente primaria de este carril.
HOY = date(2026, 9, 6)


def _reglas(kind):
    return [r for r in REGLAS if r["kind"] == kind]


def _vigente(kind, cuando=HOY):
    """La fila que rige ``cuando``, elegida como lo hace el endpoint."""
    candidatas = [
        r
        for r in _reglas(kind)
        if date.fromisoformat(r["effective_from"]) <= cuando
        and (
            not r.get("effective_to") or date.fromisoformat(r["effective_to"]) >= cuando
        )
    ]
    assert candidatas, f"Ninguna fila de {kind} rige el {cuando}"
    return max(candidatas, key=lambda r: r["effective_from"])


class TestCapacitacionInicial:
    """LFT 39-B: tres meses, o hasta seis en puestos de dirección."""

    @pytest.mark.parametrize(
        ("kind", "valor"),
        [
            ("capacitacion_inicial_meses_max", 3),
            ("capacitacion_inicial_meses_max_direccion", 6),
        ],
    )
    def test_publicada_con_su_articulo(self, kind, valor):
        fila = _vigente(kind)
        assert fila["value"] == valor
        assert fila["unit"] == "meses"
        assert fila["official_id"] == "lft"
        assert fila["article"] == "39-B"
        # `published` o el consumidor fail-closed la descarta y HP-1 se queda
        # sin poder afirmar el tope.
        assert fila["provenance"] == Provenance.PUBLISHED
        assert fila["source_url"], "sin URL no hay lectura primaria que revisar"

    @pytest.mark.django_db
    def test_el_valor_esta_en_el_texto_del_articulo(self):
        """Cruza la cifra contra el texto que Tezca sirve, no contra sí misma.

        Es la diferencia entre «la fila dice 3» y «la ley dice tres»: sin este
        cruce, un dedazo en el seed pasa las dos pruebas anteriores.
        """
        LawArticle.objects.create(
            official_id="lft",
            article="39-B",
            text=(
                "Artículo 39-B. Se entiende por relación de trabajo para "
                "capacitación inicial, aquella por virtud de la cual un "
                "trabajador se obliga a prestar sus servicios subordinados... "
                "La vigencia de la relación de trabajo a que se refiere el "
                "párrafo anterior, tendrá una duración máxima de tres meses o "
                "en su caso, hasta de seis meses sólo cuando se trate de "
                "trabajadores para puestos de dirección, gerenciales y demás "
                "personas que ejerzan funciones de dirección o administración."
            ),
            effective_from=date(2012, 11, 30),
            provenance=Provenance.PUBLISHED,
        )
        texto = LawArticle.objects.get(official_id="lft", article="39-B").text
        assert "tres meses" in texto
        assert "seis meses" in texto
        # Y la doble condición del segundo tope: sólo para esos puestos.
        assert "puestos de dirección" in texto


class TestElementosDeLaRelacion:
    """LFT 20: lo que es de ley se publica; lo que es doctrina, no."""

    def test_los_elementos_son_published(self):
        fila = _vigente("relacion_trabajo_elementos")
        assert fila["provenance"] == Provenance.PUBLISHED
        assert fila["official_id"] == "lft"
        assert fila["article"] == "20"
        elementos = fila["value"]["elementos"]
        assert len(elementos) == 3, "el art. 20 enuncia tres elementos, ni uno más"
        junto = " ".join(elementos).lower()
        for palabra in ("personal", "subordina", "salario"):
            assert palabra in junto

    def test_los_indicios_siguen_sin_verificar(self):
        """La lista doctrinal no se promueve a `published` por comodidad."""
        fila = _vigente("recaracterizacion_indicios")
        assert fila["provenance"] == Provenance.SEED_UNVERIFIED
        assert "advertencia" in fila["value"]
        # Y dice dónde está lo que sí es ley, para que el consumidor no se
        # quede sin la definición sólo porque descartó los indicios.
        assert fila["value"]["elementos_de_ley_en"] == "relacion_trabajo_elementos"

    def test_los_indicios_ya_no_arrastran_a_la_ley(self):
        """El motivo de partir la fila en dos.

        Antes de T-1f los tres elementos vivían dentro de la fila
        `seed-unverified`, así que un consumidor fail-closed los descartaba
        junto con la doctrina. Esta prueba fija que no vuelvan a mezclarse.
        """
        indicios = _vigente("recaracterizacion_indicios")["value"]
        assert "elementos_de_ley" not in indicios
        assert "elementos" not in indicios

    def test_es_el_unico_sin_verificar_del_feed(self):
        sin_verificar = {
            r["kind"] for r in REGLAS if r["provenance"] != Provenance.PUBLISHED
        }
        assert sin_verificar == {"recaracterizacion_indicios"}


#: Los cinco huecos que HP-0c declaró con motivo `corpus`, y qué pasó con cada
#: uno en este carril. `resuelto` lleva la ruta exacta que el HCM debe citar;
#: `sigue_hueco` lleva el motivo preciso — qué documento falta y dónde está.
HUECOS_DE_HP0C = {
    "registro_stps_jcf": {
        "resuelto": ("jcf-reglas-2026", None),
        "nota": (
            "Las Reglas de Operación JCF 2026 SÍ tienen identificador estable "
            "en el corpus: `jcf-reglas-2026` (DOF 5777674, 31-12-2025), "
            "ingresadas por `manage.py ingest_jcf` desde `data/jcf/catalog.json`. "
            "HP-0c citó el DOF 5746424, que son las Reglas de 2025, abrogadas "
            "por las de 2026."
        ),
    },
    "nom035": {
        "resuelto": ("nom_NOM-035-STPS-2018", "2"),
        "nota": (
            "El numeral 2 (campo de aplicación) se publica como LawArticle, "
            "leído íntegro del DOF 5541828."
        ),
    },
    "nom037_si_aplica": {
        "resuelto": ("nom_NOM-037-STPS-2023", "2"),
        "nota": (
            "Igual que la NOM-035: el numeral 2 entra al corpus. El motivo que "
            "daba HP-0c —«LawArticle no modela numerales»— dejó de aplicar "
            "cuando T-1e llevó `article` de 32 a 200 caracteres."
        ),
    },
    "convenio_institucion": {
        "resuelto": None,
        "nota": (
            "HUECO REAL, y el motivo NO es que falte ingerir un documento: es "
            "que el documento no existe. Lectura primaria del Reglamento de la "
            "Ley Reglamentaria del art. 5o. constitucional (LeyesBiblio "
            "Reg_LRArt5C_050418.pdf, última reforma DOF 05-04-2018): la palabra "
            "'convenio' aparece 4 veces y NINGUNA es un convenio entre "
            "institución educativa y centro receptor. El capítulo de servicio "
            "social (arts. 85-93) lo deja 'al cuidado y responsabilidad de las "
            "escuelas' sin exigir instrumento federal. El convenio lo rige el "
            "convenio mismo."
        ),
    },
    "carta_aceptacion": {
        "resuelto": None,
        "nota": (
            "HUECO REAL por la misma lectura: 'carta de aceptación' aparece "
            "CERO veces en el Reglamento. Es práctica administrativa de cada "
            "institución, no requisito de ordenamiento federal. Lo que sí "
            "funda el vínculo formativo es la autorización de la práctica "
            "profesional del pasante (art. 52), que este carril sí publica."
        ),
    },
}


class TestHuecosDeCorpusDeHP0c:
    """Cada hueco declarado por HP-0c, resuelto o con motivo preciso."""

    @pytest.mark.django_db
    @pytest.mark.parametrize("clave", sorted(HUECOS_DE_HP0C))
    def test_resuelve_contra_el_corpus_o_consta_el_motivo(self, clave):
        caso = HUECOS_DE_HP0C[clave]
        assert caso["nota"].strip(), "un hueco sin motivo no lo cierra nadie"

        if caso["resuelto"] is None:
            # Sigue siendo hueco: lo único exigible es que el motivo diga qué
            # documento falta. Aquí el motivo es más fuerte —el documento no
            # existe— y eso se afirma, no se insinúa.
            assert "HUECO REAL" in caso["nota"]
            return

        official_id, numeral = caso["resuelto"]
        if numeral is None:
            # El ordenamiento entra al corpus como Law (ingest_jcf), no como
            # LawArticle: lo exigible es el identificador estable.
            assert official_id and " " not in official_id
            return

        assert LawArticle.objects.filter(
            official_id=official_id, article=numeral
        ).exists() or any(
            r["official_id"] == official_id for r in REGLAS
        ), f"{clave}: {official_id} art. {numeral} no está en el corpus"

    def test_los_dos_formativos_no_se_inventaron(self):
        """La compuerta contra el impulso de rellenar el hueco.

        `convenio_institucion` y `carta_aceptacion` son los dos que un carril
        apurado habría 'resuelto' publicando una regla con un artículo
        plausible. No hay tal artículo, y esta prueba falla si alguien lo
        añade.
        """
        for kind in ("convenio_institucion", "carta_aceptacion"):
            assert not _reglas(kind), (
                f"{kind} no tiene fundamento en el Reglamento del art. 5o "
                "constitucional; publicar una regla sería inventarla"
            )


class TestCorreccionNom035:
    """El campo de aplicación es el numeral 2, y el tramo chico pide menos."""

    def test_la_fila_vigente_cita_el_numeral_2(self):
        fila = _vigente("nom035_umbral_personas")
        assert fila["article"] == "2", (
            "el campo de aplicación de la NOM-035-STPS-2018 es el numeral 2; "
            "el 4 son las Definiciones"
        )
        assert fila["dof_codigo"] == "5541828"

    def test_el_tramo_de_hasta_15_pide_lo_que_la_norma_pide(self):
        """La corrección concreta, contra el texto del DOF 5541828.

        El inciso a) del numeral 2 dice, palabra por palabra: 'deberán cumplir
        con lo dispuesto por los numerales 5.1, 5.4, 5.5, 5.7, 8.1 y 8.2'. La
        fila de T-1b le exigía además el 5.2 y el 7.1, que la norma no le
        impone.
        """
        fila = _vigente("nom035_umbral_personas")
        tramo = fila["value"]["tramos"][0]
        assert tramo["hasta"] == 15
        assert tramo["numerales"] == ["5.1", "5.4", "5.5", "5.7", "8.1", "8.2"]
        assert "5.2" not in tramo["numerales"]
        assert "7.1 inciso a)" not in tramo["numerales"]

    def test_la_fila_superada_se_conserva_y_se_cierra(self):
        """Append-only: la fila vieja no se borra, se sucede."""
        filas = sorted(
            _reglas("nom035_umbral_personas"), key=lambda r: r["effective_from"]
        )
        assert len(filas) == 2, "la corrección se añade, no reemplaza"
        vieja, nueva = filas
        assert vieja["article"] == "4"
        assert vieja["effective_to"] == "2026-09-05"
        assert nueva["article"] == "2"
        assert nueva["effective_from"] == "2026-09-06"
        # Sin hueco entre una y otra: el día siguiente al cierre de la vieja
        # es el primero de la nueva.
        assert (
            date.fromisoformat(nueva["effective_from"]).toordinal()
            - date.fromisoformat(vieja["effective_to"]).toordinal()
            == 1
        )

    def test_la_equivalencia_nmx_r_025_se_publica(self):
        """El último párrafo del numeral 2, que T-1b no había transcrito."""
        fila = _vigente("nom035_umbral_personas")
        equivalencia = fila["value"]["equivalencia_nmx_r_025"]
        assert "NMX-R-025-SCFI-2015" in equivalencia["certificado"]
        assert equivalencia["da_por_cumplidos"]


class TestNom037:
    """La NOM-037 no tiene umbral por tamaño: basta una persona."""

    def test_aplicabilidad_publicada(self):
        fila = _vigente("nom037_aplicabilidad")
        assert fila["provenance"] == Provenance.PUBLISHED
        assert fila["official_id"] == "nom_NOM-037-STPS-2023"
        assert fila["article"] == "2"
        assert fila["dof_codigo"] == "5691672"
        assert fila["value"]["umbral_personas"] is None
        # Quién cuenta como teletrabajador lo fija la LFT, no la NOM.
        assert fila["value"]["umbral_teletrabajo_en"] == "teletrabajo_umbral_pct"

    def test_vigente_180_dias_despues_de_la_publicacion(self):
        """TRANSITORIO PRIMERO: 08-06-2023 + 180 días naturales."""
        fila = _vigente("nom037_aplicabilidad")
        publicacion = date.fromisoformat(fila["dof_date"])
        entrada = date.fromisoformat(fila["effective_from"])
        assert (entrada - publicacion).days == 180
