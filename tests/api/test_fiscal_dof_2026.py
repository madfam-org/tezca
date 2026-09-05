"""Pruebas de la publicación fiscal 2026 verificada contra el DOF.

Dos capas:

* La **integridad de las constantes** (``apps.api.fiscal_dof_2026``): que las
  cifras sean las del documento de verificación y que la forma de cada tabla
  sea la que el consumidor sabe leer. Estas pruebas no tocan la base de datos
  y son las que fallarían si alguien "corrigiera" una cifra sin releer el DOF.
* El **comportamiento publicado**: que el comando escriba filas ``published``
  con su ``codigo``, que respete el append-only, y —lo que de verdad importa—
  que los endpoints que consume ``symbiosis-hcm`` devuelvan la cifra correcta
  para una fecha dada.
"""

from datetime import date
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.api.fiscal_dof_2026 import (
    ISR_2026_DOF,
    ISR_MONTHLY_2026,
    MINIMUM_WAGE_2026,
    SUBSIDIO_2026_DOF,
    SUBSIDIO_2026_PERIODS,
    SUBSIDIO_INCOME_CAP,
    SUBSIDIO_RATE_OF_UMA,
    UMA_2026,
    subsidio_rule_rows,
)
from apps.api.fiscal_models import FiscalTable, MinimumWage, Provenance, UMAValue
from apps.api.fiscal_seed_data import ISR_MONTHLY_2025
from tests.api.test_fiscal_views import AUTH_PATCH, _make_user


class TestConstantesContraElDOF:
    """Las cifras tal como están en el texto del DOF verificado 2026-09-05."""

    def test_uma_2026_valores_publicados_por_inegi(self):
        """DOF 09-01-2026, codigo 5778072.

        El mensual y el anual son los que publicó el INEGI, NO derivados de
        multiplicar el diario: 117.31 x 30.4 = 3,566.224, y el INEGI redondeó
        a 3,566.22. El seed anterior traía 3,566.28 / 42,795.36, que es lo
        que esta publicación corrige.
        """
        assert UMA_2026["daily"] == "117.31"
        assert UMA_2026["monthly"] == "3566.22"
        assert UMA_2026["annual"] == "42794.64"
        assert UMA_2026["dof_codigo"] == "5778072"
        assert UMA_2026["dof_date"] == "2026-01-09"

    def test_uma_2026_entra_en_vigor_el_1_de_febrero(self):
        """LFVUMA: la UMA rige a partir del 1 de febrero, no del 1 de enero."""
        assert UMA_2026["vigencia_from"] == "2026-02-01"

    def test_uma_2026_no_afirma_un_fin_de_vigencia(self):
        """El 31-01-2027 es inferencia, no texto del DOF: queda en None."""
        assert UMA_2026["vigencia_to"] is None
        assert "no aparece en el texto" in UMA_2026["notes"].lower()

    def test_salarios_minimos_2026(self):
        """DOF 09-12-2025, CONASAMI, codigo 5775534."""
        zones = dict((z, v) for z, v, _inc in MINIMUM_WAGE_2026["zones"])
        assert zones["general"] == "315.04"
        assert zones["zlfn"] == "440.87"
        assert MINIMUM_WAGE_2026["dof_codigo"] == "5775534"
        assert MINIMUM_WAGE_2026["vigencia_from"] == "2026-01-01"

    def test_zlfn_por_encima_del_general(self):
        zones = dict((z, float(v)) for z, v, _inc in MINIMUM_WAGE_2026["zones"])
        assert zones["zlfn"] > zones["general"]

    def test_no_se_publican_salarios_profesionales(self):
        """La resolución trae 61, el documento de verificación ninguno."""
        assert len(MINIMUM_WAGE_2026["zones"]) == 2

    def test_isr_2026_cita_el_anexo_8_de_la_rmf_2026(self):
        assert ISR_2026_DOF["dof_codigo"] == "5777219"
        assert ISR_2026_DOF["dof_date"] == "2025-12-28"
        assert "5777217" in ISR_2026_DOF["source_citation"], "la RMF 2026 misma"

    def test_isr_2026_tiene_once_tramos(self):
        assert len(ISR_MONTHLY_2026) == 11

    def test_isr_2026_primer_y_ultimo_tramo(self):
        primero, ultimo = ISR_MONTHLY_2026[0], ISR_MONTHLY_2026[-1]
        assert primero["lower"] == "0.01"
        assert primero["upper"] == "844.59"
        assert primero["rate"] == "0.0192"
        assert ultimo["lower"] == "425642.00"
        assert ultimo["upper"] is None, "el tramo superior es abierto"
        assert ultimo["fixed_fee"] == "133488.54"
        assert ultimo["rate"] == "0.3500"

    def test_isr_2026_tramos_contiguos(self):
        """Sin huecos: cada límite inferior sigue al superior anterior."""
        for previo, actual in zip(ISR_MONTHLY_2026, ISR_MONTHLY_2026[1:]):
            assert float(actual["lower"]) > float(previo["upper"])

    def test_isr_2026_tasas_monotonas(self):
        rates = [float(row["rate"]) for row in ISR_MONTHLY_2026]
        assert rates == sorted(rates)

    def test_isr_2026_cuotas_fijas_monotonas(self):
        fees = [float(row["fixed_fee"]) for row in ISR_MONTHLY_2026]
        assert fees == sorted(fees)

    def test_isr_2026_difiere_de_2025_pese_a_ser_el_mismo_regimen(self):
        """Mismas tasas, distintos límites: la tarifa de 2025 se actualizó.

        Esta prueba es la que evita el error silencioso de servir la tabla de
        2025 sellada como 2026.
        """
        assert ISR_MONTHLY_2026 != ISR_MONTHLY_2025
        tasas_2026 = [r["rate"] for r in ISR_MONTHLY_2026]
        tasas_2025 = [r["rate"] for r in ISR_MONTHLY_2025]
        assert tasas_2026 == tasas_2025, "las tasas sí son las mismas"
        assert ISR_MONTHLY_2026[0]["upper"] != ISR_MONTHLY_2025[0]["upper"]

    def test_isr_2026_cuotas_fijas_son_aritmeticamente_coherentes(self):
        """La prueba que caza un dígito mal transcrito.

        La cuota fija de cada tramo es el impuesto acumulado hasta el tope del
        tramo anterior:

            cuota_fija[n] = cuota_fija[n-1] + (tope[n-1] - inferior[n-1]) * tasa[n-1]

        Los importes del DOF vienen redondeados a centavos y la cadena acumula
        ese redondeo, así que se toleran 2 centavos: la desviación real máxima
        en esta tarifa es de 0.012 (el tramo que arranca en 141,880.67). Un
        dedazo en cualquier límite, cuota o tasa rompe la cadena por órdenes de
        magnitud más que eso — la tarifa 2025 del seed, por ejemplo, se desvía
        997.79 en un tramo — y ningún test de monotonía lo detectaría.
        """
        from decimal import Decimal

        for previo, actual in zip(ISR_MONTHLY_2026, ISR_MONTHLY_2026[1:]):
            esperada = Decimal(previo["fixed_fee"]) + (
                Decimal(previo["upper"]) - Decimal(previo["lower"])
            ) * Decimal(previo["rate"])
            diferencia = abs(esperada - Decimal(actual["fixed_fee"]))
            assert diferencia <= Decimal("0.02"), (
                f"tramo que arranca en {actual['lower']}: cuota fija "
                f"{actual['fixed_fee']}, esperada ~{esperada:.2f}"
            )

    def test_isr_2026_misma_forma_que_2025(self):
        """El consumidor no debe cambiar de parser."""
        assert set(ISR_MONTHLY_2026[0]) == set(ISR_MONTHLY_2025[0])

    def test_subsidio_2026_es_regla_derivada(self):
        assert SUBSIDIO_RATE_OF_UMA == "0.138"
        assert SUBSIDIO_INCOME_CAP == "10171.00"
        assert SUBSIDIO_2026_DOF["dof_codigo"] == "5746529"

    def test_subsidio_2026_tiene_dos_vigencias(self):
        """La UMA cambia el 1 de febrero, así que el subsidio también."""
        assert len(SUBSIDIO_2026_PERIODS) == 2
        enero, desde_febrero = SUBSIDIO_2026_PERIODS
        assert enero[0] == "2026-01-01"
        assert enero[1] == "2026-01-31"
        assert enero[3] == "474.65"
        assert desde_febrero[0] == "2026-02-01"
        assert desde_febrero[1] is None
        assert desde_febrero[3] == "492.14"

    def test_subsidio_importes_cuadran_con_la_formula(self):
        """13.8 % de la UMA mensual, redondeado a centavos."""
        for _v_from, _v_to, uma_monthly, amount, _note in SUBSIDIO_2026_PERIODS:
            esperado = round(float(uma_monthly) * 0.138, 2)
            assert abs(esperado - float(amount)) < 0.01, uma_monthly

    def test_subsidio_enero_usa_la_uma_2025(self):
        """Enero de 2026 todavía se calcula con la UMA vigente en enero."""
        enero = SUBSIDIO_2026_PERIODS[0]
        assert enero[2] == "3439.46", "UMA mensual 2025"
        febrero = SUBSIDIO_2026_PERIODS[1]
        assert febrero[2] == UMA_2026["monthly"]

    def test_subsidio_rule_rows_lleva_la_formula(self):
        rows = subsidio_rule_rows("3566.22", "492.14")
        assert len(rows) == 1
        row = rows[0]
        assert row["rate_of_uma"] == "0.138"
        assert row["income_cap"] == "10171.00"
        assert row["days_divisor"] == "30.4"
        assert "30.4" in row["formula"]

    def test_toda_cita_trae_codigo_del_dof(self):
        """Sin codigo no hay procedencia verificable."""
        for spec in (UMA_2026, MINIMUM_WAGE_2026, ISR_2026_DOF, SUBSIDIO_2026_DOF):
            assert spec["dof_codigo"].isdigit()
            assert spec["dof_codigo"] in spec["source_url"]


@pytest.mark.django_db
class TestComandoDePublicacion:
    """python manage.py publish_fiscal_values_2026."""

    def test_dry_run_no_escribe(self):
        out = StringIO()
        call_command("publish_fiscal_values_2026", "--dry-run", stdout=out)

        assert UMAValue.objects.count() == 0
        assert MinimumWage.objects.count() == 0
        assert FiscalTable.objects.count() == 0
        assert "Would publish" in out.getvalue()

    def test_exige_el_guard_local_db(self, monkeypatch):
        """AGENTS.md: un comando que muta la base pide LOCAL_DB=yes."""
        monkeypatch.delenv("LOCAL_DB", raising=False)
        err = StringIO()
        call_command("publish_fiscal_values_2026", stdout=StringIO(), stderr=err)

        assert UMAValue.objects.count() == 0
        assert "LOCAL_DB=yes" in err.getvalue()

    def test_publica_todas_las_filas(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_fiscal_values_2026", stdout=StringIO())

        uma = UMAValue.objects.get(year=2026)
        assert str(uma.value) == "117.3100"
        assert str(uma.monthly_value) == "3566.2200"
        assert str(uma.annual_value) == "42794.6400"
        assert uma.provenance == Provenance.PUBLISHED
        assert uma.dof_codigo == "5778072"
        assert uma.is_verified

        assert MinimumWage.objects.filter(year=2026).count() == 2
        assert FiscalTable.objects.filter(year=2026).count() == 3

    def test_toda_fila_publicada_trae_codigo_y_url(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_fiscal_values_2026", stdout=StringIO())

        for model in (UMAValue, MinimumWage, FiscalTable):
            for row in model.objects.filter(provenance=Provenance.PUBLISHED):
                assert row.dof_codigo, f"{model.__name__} sin codigo"
                assert row.dof_date is not None
                assert row.source_url.startswith("https://dof.gob.mx/")
                assert row.dof_codigo in row.source_url

    def test_es_idempotente(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_fiscal_values_2026", stdout=StringIO())
        primero = (
            UMAValue.objects.count(),
            MinimumWage.objects.count(),
            FiscalTable.objects.count(),
        )

        out = StringIO()
        call_command("publish_fiscal_values_2026", stdout=out)

        assert (
            UMAValue.objects.count(),
            MinimumWage.objects.count(),
            FiscalTable.objects.count(),
        ) == primero
        assert "0 filas nuevas" in out.getvalue()
        assert "0 promovidas" in out.getvalue()

    def test_promueve_la_fila_seed_en_lugar_de_duplicarla(self, monkeypatch):
        """El seed dejó una UMA 2026 con mensual/anual mal derivados."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("seed_fiscal_values", stdout=StringIO())

        sembrada = UMAValue.objects.get(year=2026)
        assert sembrada.provenance == Provenance.SEED_UNVERIFIED
        assert str(sembrada.monthly_value) == "3566.2800", "la cifra derivada a mano"

        out = StringIO()
        call_command("publish_fiscal_values_2026", stdout=out)

        assert UMAValue.objects.filter(year=2026).count() == 1, "no se duplica"
        promovida = UMAValue.objects.get(year=2026)
        assert promovida.pk == sembrada.pk
        assert promovida.provenance == Provenance.PUBLISHED
        assert str(promovida.monthly_value) == "3566.2200", "corregida al valor DOF"
        assert "promovidas" in out.getvalue()

    def test_nunca_toca_una_fila_ya_publicada(self, monkeypatch):
        """Un operador que corrigió a mano no debe ser pisado por el comando."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        UMAValue.objects.create(
            year=2026,
            value="999.99",
            monthly_value="1.00",
            annual_value="1.00",
            unit="MXN/day",
            vigencia_from="2026-02-01",
            provenance=Provenance.PUBLISHED,
            source_citation="fila de un operador",
        )

        out = StringIO()
        call_command("publish_fiscal_values_2026", stdout=out)

        intacta = UMAValue.objects.get(year=2026)
        assert str(intacta.value) == "999.9900"
        assert "ya published, intacta" in out.getvalue()

    def test_cierra_la_vigencia_de_la_uma_2025(self, monkeypatch):
        """Enero de 2026 debe seguir resolviendo a la UMA 2025."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("seed_fiscal_values", stdout=StringIO())
        call_command("publish_fiscal_values_2026", stdout=StringIO())

        uma_2025 = UMAValue.objects.get(year=2025)
        assert uma_2025.vigencia_to == date(2026, 1, 31)

    def test_una_sola_uma_abierta(self, monkeypatch):
        """Si hay dos filas abiertas, 'la UMA de hoy' es ambigua."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("seed_fiscal_values", stdout=StringIO())
        call_command("publish_fiscal_values_2026", stdout=StringIO())

        assert UMAValue.objects.filter(vigencia_to__isnull=True).count() == 1

    def test_subsidio_dos_filas_sin_traslape(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_fiscal_values_2026", stdout=StringIO())

        filas = list(
            FiscalTable.objects.filter(
                kind=FiscalTable.Kind.SUBSIDIO_RULE, year=2026
            ).order_by("vigencia_from")
        )
        assert len(filas) == 2
        assert filas[0].vigencia_to == date(2026, 1, 31)
        assert filas[1].vigencia_from == date(2026, 2, 1)
        assert filas[1].vigencia_to is None

    def test_no_publica_la_tarifa_anual(self, monkeypatch):
        """Sólo se conocen sus extremos: no se completa a mano."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_fiscal_values_2026", stdout=StringIO())

        assert not FiscalTable.objects.filter(
            kind=FiscalTable.Kind.ISR_ANNUAL, year=2026
        ).exists()


@pytest.mark.django_db
class TestEndpointsConLosValores2026:
    """Lo que symbiosis-hcm verá realmente al llamar al feed."""

    @pytest.fixture(autouse=True)
    def _publicado(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("seed_fiscal_values", stdout=StringIO())
        call_command("publish_fiscal_values_2026", stdout=StringIO())

    @pytest.fixture
    def client(self):
        """Un cliente autenticado con scope 'read', como los demás tests."""
        api = APIClient()
        user = _make_user()

        class _Authed:
            @staticmethod
            def get(url, params=None):
                with patch(AUTH_PATCH) as mock_auth:
                    mock_auth.return_value = (user, "tok")
                    return api.get(url, params or {})

        return _Authed()

    def test_uma_en_marzo_2026_es_la_nueva(self, client):
        resp = client.get("/api/v1/fiscal/uma/?on=2026-03-01")

        assert resp.status_code == 200
        assert resp.json()["value"] == "117.3100"
        assert resp.json()["year"] == 2026
        assert resp.json()["effective_date"] == "2026-02-01"
        assert resp.json()["provenance"] == "published"

    def test_uma_en_enero_2026_sigue_siendo_la_de_2025(self, client):
        """El caso que un motor de nómina se equivoca sin este feed."""
        resp = client.get("/api/v1/fiscal/uma/?on=2026-01-15")

        assert resp.status_code == 200
        assert resp.json()["value"] == "113.1400"
        assert resp.json()["year"] == 2025
        assert resp.json()["count"] == 1, "una sola UMA vigente ese día"

    def test_uma_el_31_de_enero_todavia_es_la_de_2025(self, client):
        """Frontera inclusiva: el último día de vigencia sigue siendo suyo."""
        resp = client.get("/api/v1/fiscal/uma/?on=2026-01-31")

        assert resp.json()["value"] == "113.1400"

    def test_uma_el_1_de_febrero_ya_es_la_de_2026(self, client):
        resp = client.get("/api/v1/fiscal/uma/?on=2026-02-01")

        assert resp.json()["value"] == "117.3100"

    def test_salario_minimo_2026_por_zona(self, client):
        resp = client.get("/api/v1/fiscal/minimos/?on=2026-06-15")

        assert resp.status_code == 200
        por_zona = {row["zone"]: row for row in resp.json()["results"]}
        assert por_zona["general"]["value"] == "315.0400"
        assert por_zona["zlfn"]["value"] == "440.8700"
        assert all(row["provenance"] == "published" for row in resp.json()["results"])
        assert all(row["is_verified"] for row in resp.json()["results"])

    def test_tables_2026_devuelve_la_tarifa_publicada(self, client):
        resp = client.get("/api/v1/fiscal/tables/2026/")

        assert resp.status_code == 200
        assert resp.json()["year"] == 2026
        brackets = resp.json()["isr_brackets"]
        assert brackets is not None
        assert len(brackets) == 11
        assert brackets[0]["upper"] == "844.59"

    def test_tables_2026_expone_el_codigo_del_dof(self, client):
        resp = client.get("/api/v1/fiscal/tables/2026/")

        isr = resp.json()["tables"]["isr_monthly"]
        assert isr["provenance"] == "published"
        assert isr["is_verified"]
        assert isr["dof_codigo"] == "5777219"
        assert isr["dof_date"] == "2025-12-28"

    def test_tables_2026_ya_no_es_404(self, client):
        """Antes de esta publicación el año 2026 fallaba en claro."""
        assert client.get("/api/v1/fiscal/tables/2026/").status_code == 200

    def test_tables_2026_no_trae_subsidio_de_tramos(self, client):
        """El decreto de 2024 abolió los tramos: el campo viejo va vacío.

        Un consumidor que sólo sepa leer ``subsidio`` (tramos) recibe null y
        falla en claro, en vez de aplicar tramos derogados.
        """
        resp = client.get("/api/v1/fiscal/tables/2026/")

        assert resp.json()["subsidio"] is None
        assert resp.json()["subsidio_rule"] is not None

    def test_subsidio_rule_trae_el_monto_vigente(self, client):
        resp = client.get(
            "/api/v1/fiscal/tables/?kind=subsidio_rule&year=2026&on=2026-06-15"
        )

        assert resp.status_code == 200
        assert resp.json()["count"] == 1
        row = resp.json()["results"][0]["rows"][0]
        assert row["monthly_amount"] == "492.14"
        assert row["income_cap"] == "10171.00"

    def test_subsidio_rule_en_enero_usa_la_uma_anterior(self, client):
        resp = client.get(
            "/api/v1/fiscal/tables/?kind=subsidio_rule&year=2026&on=2026-01-20"
        )

        row = resp.json()["results"][0]["rows"][0]
        assert row["monthly_amount"] == "474.65"
        assert row["uma_monthly"] == "3439.46"

    def test_tables_2026_no_esta_todo_publicado(self, client):
        """all_published sigue siendo False: falta la tarifa anual e IMSS/ISN."""
        resp = client.get("/api/v1/fiscal/tables/2026/")

        assert resp.json()["isr_annual"] is None
        assert resp.json()["imss_rates"] is None
        assert resp.json()["isn_rates"] is None

    def test_2025_sigue_intacto(self, client):
        """Publicar 2026 no reescribe la historia de 2025."""
        resp = client.get("/api/v1/fiscal/uma/?on=2025-06-15")

        assert resp.json()["value"] == "113.1400"
        assert resp.json()["year"] == 2025
