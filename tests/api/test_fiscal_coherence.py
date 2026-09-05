"""La compuerta de coherencia, aplicada a **toda** tarifa ISR del repo.

Dos capas:

* La compuerta contra sí misma: que se ponga en rojo con la errata real que
  este carril corrigió, y en verde con la corrección. Una compuerta que nunca
  se ha visto fallar no es una compuerta.
* La compuerta contra todo lo sembrado y publicado: cualquier tarifa ISR que
  entre al repo —mensual o anual, de cualquier año, por el seed o por un
  módulo ``fiscal_dof_*``— tiene que cumplir la identidad.

Esta segunda capa es la que importa a futuro: se descubre sola. Si alguien
agrega ``fiscal_dof_2027`` con una tarifa mal transcrita, la prueba la
encuentra sin que nadie edite este archivo.
"""

import importlib
import pkgutil

import pytest

from apps.api.fiscal_coherence import TOLERANCIA, describe, incoherencias

# La tarifa mensual 2025 tal como estuvo sembrada hasta el 2026-09-05: seis
# cuotas fijas equivocadas, transcritas de symbiosis-hcm. Se conserva aquí —y
# NO en el código de producción— como el caso de prueba que demuestra que la
# compuerta muerde. Verificada contra el Anexo 8 de la RMF 2025 el 2026-09-05
# (DOF 30-12-2024, codigo 5746354): los importes de abajo son los INCORRECTOS.
ISR_MONTHLY_2025_CON_ERRATA = [
    {"lower": "0.01", "upper": "746.04", "fixed_fee": "0.00", "rate": "0.0192"},
    {"lower": "746.05", "upper": "6332.05", "fixed_fee": "14.32", "rate": "0.0640"},
    {"lower": "6332.06", "upper": "11128.01", "fixed_fee": "371.83", "rate": "0.1088"},
    {"lower": "11128.02", "upper": "12935.82", "fixed_fee": "893.63", "rate": "0.1600"},
    {
        "lower": "12935.83",
        "upper": "15487.71",
        "fixed_fee": "1182.88",
        "rate": "0.1792",
    },
    {
        "lower": "15487.72",
        "upper": "31236.49",
        "fixed_fee": "1639.32",
        "rate": "0.2136",
    },
    {
        "lower": "31236.50",
        "upper": "49233.00",
        "fixed_fee": "4005.47",
        "rate": "0.2352",
    },
    {
        "lower": "49233.01",
        "upper": "93993.90",
        "fixed_fee": "8236.89",
        "rate": "0.3000",
    },
    {
        "lower": "93993.91",
        "upper": "125325.20",
        "fixed_fee": "21665.17",
        "rate": "0.3200",
    },
    {
        "lower": "125325.21",
        "upper": "375975.61",
        "fixed_fee": "31691.18",
        "rate": "0.3400",
    },
    {"lower": "375975.62", "upper": None, "fixed_fee": "116890.10", "rate": "0.3500"},
]


def _tarifas_isr_del_repo():
    """Toda tarifa ISR declarada en ``apps.api``, descubierta por reflexión.

    Recorre los módulos ``fiscal_*`` y recoge cualquier constante cuyo nombre
    empiece por ``ISR_`` y sea una lista de tramos. Descubrirlas así —en vez
    de enumerarlas a mano— es lo que hace que un ``fiscal_dof_2027`` futuro
    quede cubierto el día que se cree, sin que nadie recuerde volver aquí.
    """
    import apps.api as paquete

    encontradas = []
    for info in pkgutil.iter_modules(paquete.__path__):
        if not info.name.startswith("fiscal_"):
            continue
        modulo = importlib.import_module(f"apps.api.{info.name}")
        for nombre in dir(modulo):
            if not nombre.startswith("ISR_"):
                continue
            valor = getattr(modulo, nombre)
            if (
                isinstance(valor, list)
                and valor
                and isinstance(valor[0], dict)
                and {"lower", "fixed_fee", "rate"} <= set(valor[0])
            ):
                encontradas.append((f"{info.name}.{nombre}", valor))
    return encontradas


class TestLaCompuertaMuerde:
    """La compuerta se pone en rojo con el error real que existió."""

    def test_la_errata_2025_rompe_la_identidad(self):
        """Cuatro de los seis tramos equivocados caen sin consultar el DOF."""
        problemas = incoherencias(ISR_MONTHLY_2025_CON_ERRATA)

        assert [p["tramo"] for p in problemas] == [6, 7, 8, 11], describe(problemas)

    def test_el_tramo_peor_se_desvia_casi_mil_pesos(self):
        """El dedazo grande: 4,005.47 donde la identidad exige ~5,003.26."""
        problemas = {p["tramo"]: p for p in incoherencias(ISR_MONTHLY_2025_CON_ERRATA)}

        assert problemas[7]["declarada"] == "4005.47"
        assert problemas[7]["desviacion"] == "997.79"

    def test_dos_tramos_erroneos_SI_pasan_la_compuerta(self):
        """El límite honesto de la compuerta, escrito como prueba.

        Los tramos 9 y 10 traían −1,000.00 exactos, el mismo desfase que su
        predecesor. La identidad es *relativa*, así que un error constante se
        propaga sin romperla: la compuerta habría cazado 4 de 6 errores, no 6
        de 6. Por eso no sustituye la lectura del DOF — la abarata. Si alguien
        endurece la compuerta y esta prueba falla, la compuerta mejoró y hay
        que reescribir esta prueba, no relajarla.
        """
        tramos_en_rojo = {
            p["tramo"] for p in incoherencias(ISR_MONTHLY_2025_CON_ERRATA)
        }

        assert 9 not in tramos_en_rojo
        assert 10 not in tramos_en_rojo

    def test_la_correccion_pone_la_compuerta_en_verde(self):
        from apps.api.fiscal_dof_2025 import ISR_MONTHLY_2025

        assert incoherencias(ISR_MONTHLY_2025) == []

    def test_un_dedazo_de_un_peso_se_detecta(self):
        """Sensibilidad: la tolerancia es de centavos, no de pesos."""
        from apps.api.fiscal_dof_2025 import ISR_MONTHLY_2025

        manipulada = [dict(row) for row in ISR_MONTHLY_2025]
        manipulada[5]["fixed_fee"] = "1641.18"  # +1.00

        assert [p["tramo"] for p in incoherencias(manipulada)] == [6, 7]

    def test_la_tolerancia_es_de_dos_centavos(self):
        from decimal import Decimal

        assert TOLERANCIA == Decimal("0.02")


class TestTodaTarifaSembradaEsCoherente:
    """La compuerta aplicada a todo el repo, presente y futuro."""

    def test_se_descubre_al_menos_una_tarifa_por_ano_conocido(self):
        """Si la reflexión deja de encontrar tarifas, la cobertura es falsa.

        Sin esta prueba, un renombre de módulo convertiría la cobertura de
        abajo en un bucle vacío que pasa siempre.
        """
        nombres = [nombre for nombre, _ in _tarifas_isr_del_repo()]

        assert any("fiscal_dof_2025.ISR_MONTHLY_2025" in n for n in nombres)
        assert any("fiscal_dof_2025.ISR_ANNUAL_2025" in n for n in nombres)
        assert any("fiscal_dof_2026.ISR_MONTHLY_2026" in n for n in nombres)
        assert any("fiscal_seed_data.ISR_MONTHLY_2025" in n for n in nombres)

    @pytest.mark.parametrize(
        "nombre,rows",
        _tarifas_isr_del_repo(),
        ids=lambda v: v if isinstance(v, str) else "",
    )
    def test_toda_tarifa_isr_del_repo_es_coherente(self, nombre, rows):
        """Mensual o anual, sembrada o publicada, de cualquier año."""
        problemas = incoherencias(rows)

        assert not problemas, f"{nombre}: {describe(problemas)}"

    @pytest.mark.parametrize(
        "nombre,rows",
        _tarifas_isr_del_repo(),
        ids=lambda v: v if isinstance(v, str) else "",
    )
    def test_toda_tarifa_isr_del_repo_tiene_forma_valida(self, nombre, rows):
        """Contigüidad, monotonía de tasas y tramo superior abierto."""
        assert rows[-1]["upper"] is None, f"{nombre}: el último tramo debe ser abierto"

        tasas = [float(r["rate"]) for r in rows]
        assert tasas == sorted(tasas), f"{nombre}: tasas no monótonas"

        for previo, actual in zip(rows, rows[1:]):
            assert float(actual["lower"]) > float(
                previo["lower"]
            ), f"{nombre}: tramos desordenados"


@pytest.mark.django_db
class TestLaCompuertaCubreLoQueSeEscribeEnLaBase:
    """Lo sembrado y lo publicado, leído de vuelta desde la base."""

    def test_toda_tarifa_isr_escrita_por_los_comandos_es_coherente(self, monkeypatch):
        from io import StringIO

        from django.core.management import call_command

        from apps.api.fiscal_models import FiscalTable

        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("seed_fiscal_values", stdout=StringIO())
        call_command("publish_fiscal_values_2025", stdout=StringIO())
        call_command("publish_fiscal_values_2026", stdout=StringIO())

        tarifas = FiscalTable.objects.filter(
            kind__in=[FiscalTable.Kind.ISR_MONTHLY, FiscalTable.Kind.ISR_ANNUAL]
        )
        assert tarifas.count() >= 3, "el escenario no sembró nada que probar"

        for tabla in tarifas:
            problemas = incoherencias(tabla.rows)
            assert not problemas, f"{tabla}: {describe(problemas)}"
