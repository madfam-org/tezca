"""Que cada valor del seed quepa en su columna, y que el dry-run lo diga (T-1e).

Por qué existe este archivo aparte de `test_labor_rules.py`:

`publish_labor_rules --dry-run` reventó en el pod de producción con

    django.db.utils.DataError: value too long for type character varying(32)

y la suite estaba **verde**. No era un descuido de quien escribió la prueba:
la suite corre sobre **SQLite**, que ignora el ancho declarado de un
``VARCHAR(n)`` y guarda la cadena entera; Postgres lo aplica y rechaza la
fila. Ninguna prueba que sólo escriba y lea sobre SQLite puede ver ese error,
por muchas que se añadan.

La salida es medir la longitud contra el ``max_length`` **del modelo**, que es
el mismo dato del que la migración deriva el ``VARCHAR(n)``. Esa comparación
es aritmética pura: no toca la base y por lo tanto da el mismo resultado en
SQLite, en Postgres y en el pod.

La segunda mitad del archivo fija la otra falla, que es de diseño del comando:
`--dry-run` escribía y hacía rollback, así que la validación de la base corría
igual y el modo «no toques nada» podía abortar con un traceback. Ahora valida
en memoria antes de cualquier `save()`.
"""

import io
import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.api.labor_coherence import desbordes_de_longitud, describe_desbordes
from apps.api.labor_models import LaborRule, LawArticle, SatCatalogEntry
from apps.api.labor_seed_data import REGLAS
from apps.api.management.commands.publish_labor_rules import DEFAULT_CATALOGOS
from apps.api.management.commands.publish_law_articles import DEFAULT_SEED

# El catálogo del SAT guarda el nombre del catálogo en la columna `article` y
# el archivo de origen en `official_id`: el mapeo va aquí y no en el helper.
ALIAS_CATALOGO = {"article": "catalog", "official_id": "catalogo_origen"}


def _leer(ruta):
    return json.loads(ruta.read_text(encoding="utf-8"))


class TestLongitudesDelSeed:
    """Cero desbordes. Entra con la lista de exenciones vacía."""

    def test_ninguna_regla_desborda_su_columna(self):
        """La compuerta que faltaba: rojo sobre `main`.

        Sobre `main` esta prueba nombra `jcf_validacion_periodicidad_dias`,
        campo `article`, 72 caracteres contra un `max_length` de 32 — la fila
        que T-1c añadió y que Postgres rechazó en el pod.
        """
        problemas = desbordes_de_longitud(REGLAS, LaborRule)
        assert problemas == [], describe_desbordes(problemas)

    def test_ningun_articulo_desborda_su_columna(self):
        articulos = _leer(DEFAULT_SEED)
        problemas = desbordes_de_longitud(articulos, LawArticle)
        assert problemas == [], describe_desbordes(problemas)

    def test_ninguna_clave_del_catalogo_desborda_su_columna(self):
        catalogos = _leer(DEFAULT_CATALOGOS)
        problemas = desbordes_de_longitud(
            catalogos, SatCatalogEntry, alias=ALIAS_CATALOGO
        )
        assert problemas == [], describe_desbordes(problemas)

    def test_el_articulo_del_jcf_cabe_entero(self):
        """La cita en prosa no se trunca: se le dio columna donde quepa.

        El artículo de esta fila no es un número —las Reglas de Operación del
        programa se citan por apartado— y recortarla a 32 caracteres dejaría
        «Reglas de Operación JCF, apart», que no lleva a ningún lado.
        """
        jcf = next(
            r
            for r in REGLAS
            if r["kind"] == LaborRule.Kind.JCF_VALIDACION_PERIODICIDAD_DIAS
        )
        assert len(jcf["article"]) == 72
        assert jcf["article"].endswith("obligaciones del Centro de Trabajo")
        assert LaborRule._meta.get_field("article").max_length >= len(jcf["article"])


class TestLaCompuertaEsFalsable:
    """Cada aserción de arriba se pone en rojo ante el error que dice atrapar."""

    def test_un_kind_demasiado_largo_se_detecta(self):
        """El `kind` de 33 caracteres que la hipótesis original sospechaba."""
        limite = LaborRule._meta.get_field("kind").max_length
        fila = {"kind": "k" * (limite + 1), "article": "1", "official_id": "lft"}
        problemas = desbordes_de_longitud([fila], LaborRule)
        assert [p["campo"] for p in problemas] == ["kind"]
        assert problemas[0]["longitud"] == limite + 1

    def test_el_mensaje_nombra_la_fila_el_campo_y_las_cifras(self):
        """El operador debe poder arreglarlo sin abrir el traceback."""
        largo = "x" * 500
        problemas = desbordes_de_longitud(
            [{"kind": "aguinaldo_dias_min", "article": largo}], LaborRule
        )
        mensaje = describe_desbordes(problemas)
        assert "fila 0" in mensaje
        assert "kind=aguinaldo_dias_min" in mensaje
        assert "campo article" in mensaje
        assert "500 caracteres" in mensaje
        assert "max_length" in mensaje

    def test_un_campo_nuevo_entra_solo_a_la_compuerta(self):
        """Los límites se leen del modelo, no de una lista escrita a mano."""
        campos = {
            p["campo"]
            for p in desbordes_de_longitud(
                [{"kind": "k" * 999, "unit": "u" * 999, "label": "l" * 999}],
                LaborRule,
            )
        }
        assert {"kind", "unit", "label"} <= campos

    def test_un_valor_que_cabe_justo_no_se_reporta(self):
        """La frontera es `<=`, no `<`: exactamente max_length es válido."""
        limite = LaborRule._meta.get_field("article").max_length
        fila = {"kind": "aguinaldo_dias_min", "article": "a" * limite}
        assert desbordes_de_longitud([fila], LaborRule) == []


@pytest.mark.django_db
class TestDryRunNoEscribe:
    """En seco el comando valida en memoria y no abre escritura alguna."""

    def _run(self, comando, **kwargs):
        salida, error = io.StringIO(), io.StringIO()
        call_command(comando, stdout=salida, stderr=error, **kwargs)
        return salida.getvalue(), error.getvalue()

    def test_dry_run_de_reglas_no_crea_ninguna_fila(self):
        salida, _ = self._run("publish_labor_rules", dry_run=True)
        assert "Publicaría" in salida
        assert LaborRule.objects.count() == 0
        assert SatCatalogEntry.objects.count() == 0

    def test_dry_run_de_articulos_no_crea_ninguna_fila(self):
        salida, _ = self._run("publish_law_articles", dry_run=True)
        assert "Publicaría" in salida
        assert LawArticle.objects.count() == 0

    def test_una_fila_invalida_aborta_sin_traceback_y_sin_escribir(
        self, monkeypatch, tmp_path
    ):
        """El comportamiento que faltaba: mensaje del operador, no DataError.

        Se muta el seed en memoria con la fila exacta que reventó en el pod —
        un `article` más largo que su columna— y se comprueba que el comando
        sale con código != 0 explicando fila, campo y cifras, sin haber
        intentado ni un `INSERT`.
        """
        import apps.api.management.commands.publish_labor_rules as modulo

        roto = [dict(REGLAS[0], article="A" * 400)]
        monkeypatch.setattr(modulo, "REGLAS", roto)

        with pytest.raises(CommandError) as exc:
            self._run("publish_labor_rules", dry_run=True)

        mensaje = str(exc.value)
        assert "campo article" in mensaje
        assert "400 caracteres" in mensaje
        assert "Traceback" not in mensaje
        assert LaborRule.objects.count() == 0

    def test_la_validacion_corre_tambien_al_escribir_de_verdad(
        self, monkeypatch, tmp_path
    ):
        """No sólo en seco: escribir una fila inválida tampoco debe intentarse."""
        import apps.api.management.commands.publish_labor_rules as modulo

        monkeypatch.setenv("LOCAL_DB", "yes")
        monkeypatch.setattr(modulo, "REGLAS", [dict(REGLAS[0], unit="u" * 400)])

        with pytest.raises(CommandError) as exc:
            self._run("publish_labor_rules")

        assert "campo unit" in str(exc.value)
        assert LaborRule.objects.count() == 0
