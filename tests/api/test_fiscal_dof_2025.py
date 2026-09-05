"""Pruebas de la errata fiscal 2025 verificada contra el DOF.

Mismas dos capas que ``test_fiscal_dof_2026.py``: las constantes contra el
texto del DOF, y el comportamiento publicado que ve ``symbiosis-hcm``.

La diferencia de fondo es que aquí no se completa un año, se **corrige** uno:
varias de estas pruebas fijan explícitamente el valor que estaba MAL, para que
nadie lo reintroduzca creyendo que corrige una regresión.
"""

from datetime import date
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.api import fiscal_seed_data as seed
from apps.api.fiscal_dof_2025 import (
    ISR_2025_DOF,
    ISR_ANNUAL_2025,
    ISR_ANNUAL_2025_DOF,
    ISR_MONTHLY_2025,
    SUBSIDIO_2025_DOF,
    SUBSIDIO_2025_ENERO_RATE_OF_UMA,
    SUBSIDIO_2025_PERIODS,
)
from apps.api.fiscal_dof_2026 import ISR_MONTHLY_2026, subsidio_rule_rows
from apps.api.fiscal_models import FiscalTable, Provenance
from tests.api.test_fiscal_views import AUTH_PATCH, _make_user

# Las seis cuotas fijas que el seed traía mal, tramo → (mala, buena).
# Anexo 8 de la RMF 2025, apartado A fracción V (DOF 30-12-2024, codigo
# 5746354). Leídas del texto del DOF el 2026-09-05.
ERRATA = {
    6: ("1639.32", "1640.18"),
    7: ("4005.47", "5004.12"),
    8: ("8236.89", "9236.89"),
    9: ("21665.17", "22665.17"),
    10: ("31691.18", "32691.18"),
    11: ("116890.10", "117912.32"),
}


class TestConstantesContraElDOF:
    """Las cifras tal como están en el texto del DOF verificado 2026-09-05."""

    def test_isr_2025_cita_el_anexo_8_de_la_rmf_2025(self):
        assert ISR_2025_DOF["dof_codigo"] == "5746354"
        assert ISR_2025_DOF["dof_date"] == "2024-12-30"
        assert "apartado A fracción V" in ISR_2025_DOF["source_citation"]

    def test_la_url_usa_nota_to_doc_y_no_nota_detalle(self):
        """``nota_detalle`` devuelve un cascarón vacío para diciembre de 2024.

        La cita tiene que apuntar al enlace que de verdad resuelve al texto,
        o no es una cita verificable por quien la lea después.
        """
        for spec in (ISR_2025_DOF, ISR_ANNUAL_2025_DOF, SUBSIDIO_2025_DOF):
            assert "nota_to_doc.php" in spec["source_url"]
            assert "nota_detalle" not in spec["source_url"]

    def test_isr_2025_mensual_tiene_once_tramos(self):
        assert len(ISR_MONTHLY_2025) == 11

    def test_isr_2025_primer_y_ultimo_tramo(self):
        primero, ultimo = ISR_MONTHLY_2025[0], ISR_MONTHLY_2025[-1]
        assert primero["lower"] == "0.01"
        assert primero["upper"] == "746.04"
        assert primero["fixed_fee"] == "0.00"
        assert ultimo["lower"] == "375975.62"
        assert ultimo["upper"] is None
        assert ultimo["fixed_fee"] == "117912.32"
        assert ultimo["rate"] == "0.3500"

    @pytest.mark.parametrize("tramo,valores", sorted(ERRATA.items()))
    def test_cada_cuota_fija_corregida_es_la_del_dof(self, tramo, valores):
        """Una prueba por tramo: el mensaje de falla nombra el tramo exacto."""
        mala, buena = valores
        fila = ISR_MONTHLY_2025[tramo - 1]

        assert fila["fixed_fee"] == buena
        assert fila["fixed_fee"] != mala, "el valor equivocado volvió a entrar"

    def test_los_limites_y_las_tasas_no_se_tocaron(self):
        """El error estaba SÓLO en las cuotas fijas.

        Los once límites inferiores, los once superiores y los once
        porcentajes coincidían con el DOF desde el principio. Fijarlo evita
        que una corrección futura «arregle» de más.
        """
        for corregida, sembrada in zip(ISR_MONTHLY_2025, seed.ISR_MONTHLY_2025):
            assert corregida["lower"] == sembrada["lower"]
            assert corregida["upper"] == sembrada["upper"]
            assert corregida["rate"] == sembrada["rate"]

    def test_el_seed_ya_trae_las_cuotas_corregidas(self):
        """El piso del seed y la fila publicada no pueden discrepar.

        El seed es lo que ve una base que nunca corrió el comando de
        publicación. Si difiere de la lectura del DOF, esa base sirve cifras
        equivocadas sin que nadie lo note.
        """
        assert seed.ISR_MONTHLY_2025 == ISR_MONTHLY_2025

    def test_isr_2025_difiere_de_2026(self):
        """La equivalencia «2025 ≡ 2026» que se llegó a suponer es FALSA.

        Los importes 2026 (844.59, 7,168.51, 133,488.54, 425,641.99) tienen
        cero ocurrencias en el texto de la RMF 2025. Las tasas sí coinciden;
        los límites se actualizaron ≈13.2 %.
        """
        assert ISR_MONTHLY_2025 != ISR_MONTHLY_2026
        assert [r["rate"] for r in ISR_MONTHLY_2025] == [
            r["rate"] for r in ISR_MONTHLY_2026
        ], "las tasas sí son las mismas"
        assert ISR_MONTHLY_2025[0]["upper"] == "746.04"
        assert ISR_MONTHLY_2026[0]["upper"] == "844.59"

    def test_isr_2025_misma_forma_que_2026(self):
        """El consumidor no debe cambiar de parser entre años."""
        assert set(ISR_MONTHLY_2025[0]) == set(ISR_MONTHLY_2026[0])

    # -- tarifa anual --------------------------------------------------------

    def test_isr_anual_2025_tiene_once_tramos(self):
        assert len(ISR_ANNUAL_2025) == 11

    def test_isr_anual_2025_primer_y_ultimo_tramo(self):
        primero, ultimo = ISR_ANNUAL_2025[0], ISR_ANNUAL_2025[-1]
        assert primero["lower"] == "0.01"
        assert primero["upper"] == "8952.49"
        assert primero["rate"] == "0.0192"
        assert ultimo["lower"] == "4511707.38"
        assert ultimo["upper"] is None
        assert ultimo["fixed_fee"] == "1414947.85"

    def test_isr_anual_cita_la_fraccion_II_del_apartado_C(self):
        """La trampa del Anexo 8: la fracción I es la del ejercicio ANTERIOR.

        El apartado C trae primero la tarifa anual de 2024 (fracción I) y
        después la de 2025 (fracción II). En la RMF 2025 ambas son idénticas,
        así que «la primera tabla anual que aparece» acierta por accidente —
        y fallará el año en que difieran. La cita tiene que decir cuál se
        leyó.
        """
        assert "apartado C fracción II" in ISR_ANNUAL_2025_DOF["source_citation"]
        assert "Art. 152" in ISR_ANNUAL_2025_DOF["source_citation"]
        assert "fracción" in ISR_ANNUAL_2025_DOF["notes"]

    def test_la_anual_es_del_mismo_instrumento_que_la_mensual(self):
        assert ISR_ANNUAL_2025_DOF["dof_codigo"] == ISR_2025_DOF["dof_codigo"]

    # -- subsidio ------------------------------------------------------------

    def test_subsidio_2025_cita_el_decreto_modificatorio(self):
        assert SUBSIDIO_2025_DOF["dof_codigo"] == "5746529"
        assert SUBSIDIO_2025_DOF["dof_date"] == "2024-12-31"
        assert "01-05-2024" in SUBSIDIO_2025_DOF["source_citation"]

    def test_subsidio_2025_tiene_dos_vigencias(self):
        """Enero al 14.39 %, el resto del año al 13.8 %."""
        assert len(SUBSIDIO_2025_PERIODS) == 2
        enero, resto = SUBSIDIO_2025_PERIODS
        assert enero[0] == "2025-01-01"
        assert enero[1] == "2025-01-31"
        assert enero[4] == "474.95"
        assert resto[0] == "2025-02-01"
        assert resto[1] == "2025-12-31"
        assert resto[4] == "474.65"

    def test_enero_2025_usa_la_uma_2024_y_el_porcentaje_transitorio(self):
        """Los dos cambios ocurren a la vez, y el DOF lo dice explícitamente.

        El TRANSITORIO SEGUNDO sustituye el 13.8 % por 14.39 %; el
        considerando precisa que es sobre «la Unidad de Medida y
        Actualización vigente en 2024» (3,300.53), porque la UMA 2025 no
        entra en vigor hasta el 1 de febrero (LFVUMA Art. 5).
        """
        enero = SUBSIDIO_2025_PERIODS[0]
        assert enero[2] == "3300.53", "UMA mensual 2024"
        assert enero[3] == SUBSIDIO_2025_ENERO_RATE_OF_UMA == "0.1439"

        resto = SUBSIDIO_2025_PERIODS[1]
        assert resto[2] == "3439.46", "UMA mensual 2025"
        assert resto[3] == "0.138"

    def test_los_importes_del_subsidio_cuadran_con_su_formula(self):
        """Cada fila es recomputable: UMA mensual x porcentaje."""
        for _v_from, _v_to, uma, rate, amount, _note in SUBSIDIO_2025_PERIODS:
            esperado = round(float(uma) * float(rate), 2)
            assert abs(esperado - float(amount)) < 0.01, (uma, rate)

    def test_el_subsidio_queda_casi_plano_entre_enero_y_febrero(self):
        """La corroboración del empalme UMA/porcentaje.

        Que un factor mayor caiga exactamente en el mes en que aún corre la
        UMA vieja no es casualidad: es lo que mantiene el subsidio continuo.
        Si alguien asignara la UMA 2025 a enero, el importe saltaría a 494.94
        y este invariante se rompería.
        """
        enero = float(SUBSIDIO_2025_PERIODS[0][4])
        febrero = float(SUBSIDIO_2025_PERIODS[1][4])

        assert abs(enero - febrero) < 1.00
        assert enero > febrero, "el transitorio deja enero apenas por encima"

    def test_el_subsidio_2025_reutiliza_el_tipo_de_2026(self):
        """No se inventa un tipo nuevo: es el mismo ``subsidio_rule``.

        La forma de la fila tiene que ser idéntica a la de 2026 para que un
        consumidor no distinga de qué año viene.
        """
        de_2025 = subsidio_rule_rows("3300.53", "474.95", "0.1439")[0]
        de_2026 = subsidio_rule_rows("3566.22", "492.14")[0]

        assert set(de_2025) == set(de_2026)
        assert de_2025["income_cap"] == de_2026["income_cap"] == "10171.00"
        assert de_2025["days_divisor"] == de_2026["days_divisor"] == "30.4"
        assert de_2025["rate_of_uma"] == "0.1439"
        assert "14.39 %" in de_2025["formula"], "la fórmula lleva el % efectivo"
        assert "13.8 %" in de_2026["formula"]

    def test_la_tabla_de_tramos_derogada_ya_no_se_siembra(self):
        """No se conserva «por compatibilidad»: se retiró con razón.

        La tabla de montos por tramos (límite superior 7,382.33) es la que el
        considerando del decreto cita como el defecto que vino a corregir.
        """
        assert not hasattr(seed, "SUBSIDIO_MONTHLY_2025")
        assert all(row[0] != "subsidio_monthly" for row in seed.FISCAL_TABLE_SEEDS)

    def test_toda_cita_trae_codigo_del_dof(self):
        for spec in (ISR_2025_DOF, ISR_ANNUAL_2025_DOF, SUBSIDIO_2025_DOF):
            assert spec["dof_codigo"].isdigit()
            assert spec["dof_codigo"] in spec["source_url"]


@pytest.mark.django_db
class TestComandoDePublicacion:
    """python manage.py publish_fiscal_values_2025."""

    def test_dry_run_no_escribe(self):
        out = StringIO()
        call_command("publish_fiscal_values_2025", "--dry-run", stdout=out)

        assert FiscalTable.objects.count() == 0
        assert "Would publish" in out.getvalue()

    def test_exige_el_guard_local_db(self, monkeypatch):
        monkeypatch.delenv("LOCAL_DB", raising=False)
        err = StringIO()
        call_command("publish_fiscal_values_2025", stdout=StringIO(), stderr=err)

        assert FiscalTable.objects.count() == 0
        assert "LOCAL_DB=yes" in err.getvalue()

    def test_publica_cuatro_filas(self, monkeypatch):
        """ISR mensual, ISR anual y dos vigencias del subsidio."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_fiscal_values_2025", stdout=StringIO())

        assert FiscalTable.objects.filter(year=2025).count() == 4
        assert (
            FiscalTable.objects.filter(
                year=2025, provenance=Provenance.PUBLISHED
            ).count()
            == 4
        )

    def test_corrige_la_tarifa_sembrada_al_promoverla(self, monkeypatch):
        """El caso central del carril, de punta a punta.

        Se siembra una base con la tarifa ERRÓNEA (simulando una instalación
        anterior a esta corrección) y se comprueba que el comando la deja con
        las cifras del DOF, sin duplicar la fila.
        """
        monkeypatch.setenv("LOCAL_DB", "yes")
        from tests.api.test_fiscal_coherence import ISR_MONTHLY_2025_CON_ERRATA

        sembrada = FiscalTable.objects.create(
            kind=FiscalTable.Kind.ISR_MONTHLY,
            year=2025,
            period="monthly",
            rows=ISR_MONTHLY_2025_CON_ERRATA,
            vigencia_from="2025-01-01",
            vigencia_to="2025-12-31",
            provenance=Provenance.SEED_UNVERIFIED,
        )

        call_command("publish_fiscal_values_2025", stdout=StringIO())

        assert (
            FiscalTable.objects.filter(
                kind=FiscalTable.Kind.ISR_MONTHLY, year=2025
            ).count()
            == 1
        ), "no se duplica"
        promovida = FiscalTable.objects.get(pk=sembrada.pk)
        assert promovida.provenance == Provenance.PUBLISHED
        assert promovida.dof_codigo == "5746354"
        for tramo, (mala, buena) in ERRATA.items():
            assert promovida.rows[tramo - 1]["fixed_fee"] == buena
            assert promovida.rows[tramo - 1]["fixed_fee"] != mala

    def test_retira_la_tabla_de_subsidio_derogada(self, monkeypatch):
        """Una base ya sembrada conserva la tabla vieja hasta este comando."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        FiscalTable.objects.create(
            kind=FiscalTable.Kind.SUBSIDIO_MONTHLY,
            year=2025,
            period="monthly",
            rows=[{"lower": "0.01", "upper": "1768.96", "subsidio": "407.02"}],
            vigencia_from="2025-01-01",
            vigencia_to="2025-12-31",
            provenance=Provenance.SEED_UNVERIFIED,
        )

        out = StringIO()
        call_command("publish_fiscal_values_2025", stdout=out)

        assert not FiscalTable.objects.filter(
            kind=FiscalTable.Kind.SUBSIDIO_MONTHLY, year=2025
        ).exists()
        assert "retirada" in out.getvalue()

    def test_no_retira_una_tabla_derogada_que_un_operador_publico(self, monkeypatch):
        """Deshacer un acto deliberado de operador no le toca a un comando."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        FiscalTable.objects.create(
            kind=FiscalTable.Kind.SUBSIDIO_MONTHLY,
            year=2025,
            period="monthly",
            rows=[{"lower": "0.01", "upper": "1768.96", "subsidio": "407.02"}],
            vigencia_from="2025-01-01",
            provenance=Provenance.PUBLISHED,
            source_citation="fila de un operador",
        )

        out = StringIO()
        call_command("publish_fiscal_values_2025", stdout=out)

        assert FiscalTable.objects.filter(
            kind=FiscalTable.Kind.SUBSIDIO_MONTHLY, year=2025
        ).exists()
        assert "un operador la selló a mano" in out.getvalue()

    def test_nunca_toca_una_tarifa_ya_publicada(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        FiscalTable.objects.create(
            kind=FiscalTable.Kind.ISR_MONTHLY,
            year=2025,
            period="monthly",
            rows=[
                {"lower": "0.01", "upper": None, "fixed_fee": "1.00", "rate": "0.01"}
            ],
            vigencia_from="2025-01-01",
            provenance=Provenance.PUBLISHED,
            source_citation="fila de un operador",
        )

        out = StringIO()
        call_command("publish_fiscal_values_2025", stdout=out)

        intacta = FiscalTable.objects.get(kind=FiscalTable.Kind.ISR_MONTHLY, year=2025)
        assert intacta.rows[0]["fixed_fee"] == "1.00"
        assert "ya published, intacta" in out.getvalue()

    def test_es_idempotente(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_fiscal_values_2025", stdout=StringIO())
        primero = FiscalTable.objects.count()

        out = StringIO()
        call_command("publish_fiscal_values_2025", stdout=out)

        assert FiscalTable.objects.count() == primero
        assert "0 filas nuevas" in out.getvalue()
        assert "0 promovidas" in out.getvalue()

    def test_toda_fila_publicada_trae_codigo_url_y_fecha(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_fiscal_values_2025", stdout=StringIO())

        for row in FiscalTable.objects.filter(year=2025):
            assert row.dof_codigo, f"{row} sin codigo"
            assert row.dof_date is not None
            assert row.source_url.startswith("https://dof.gob.mx/")
            assert row.dof_codigo in row.source_url

    def test_las_dos_vigencias_del_subsidio_no_se_traslapan(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_fiscal_values_2025", stdout=StringIO())

        filas = list(
            FiscalTable.objects.filter(
                kind=FiscalTable.Kind.SUBSIDIO_RULE, year=2025
            ).order_by("vigencia_from")
        )
        assert len(filas) == 2
        assert filas[0].vigencia_to == date(2025, 1, 31)
        assert filas[1].vigencia_from == date(2025, 2, 1)
        assert filas[1].vigencia_to == date(2025, 12, 31)

    def test_publicar_2025_no_toca_2026(self, monkeypatch):
        """Los dos comandos son independientes y no se pisan."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("publish_fiscal_values_2026", stdout=StringIO())
        antes = {
            (t.kind, t.vigencia_from): t.rows
            for t in FiscalTable.objects.filter(year=2026)
        }

        call_command("publish_fiscal_values_2025", stdout=StringIO())

        despues = {
            (t.kind, t.vigencia_from): t.rows
            for t in FiscalTable.objects.filter(year=2026)
        }
        assert despues == antes


@pytest.mark.django_db
class TestEndpointsConLosValores2025:
    """Lo que symbiosis-hcm verá realmente al llamar al feed."""

    @pytest.fixture(autouse=True)
    def _publicado(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("seed_fiscal_values", stdout=StringIO())
        call_command("publish_fiscal_values_2025", stdout=StringIO())

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

    def test_tables_2025_devuelve_la_tarifa_corregida(self, client):
        resp = client.get("/api/v1/fiscal/tables/2025/")

        assert resp.status_code == 200
        brackets = resp.json()["isr_brackets"]
        assert len(brackets) == 11
        assert brackets[6]["fixed_fee"] == "5004.12", "el tramo del dedazo"
        assert brackets[-1]["fixed_fee"] == "117912.32"

    def test_tables_2025_expone_el_codigo_del_dof(self, client):
        resp = client.get("/api/v1/fiscal/tables/2025/")

        isr = resp.json()["tables"]["isr_monthly"]
        assert isr["provenance"] == "published"
        assert isr["is_verified"]
        assert isr["dof_codigo"] == "5746354"
        assert isr["dof_date"] == "2024-12-30"

    def test_tables_2025_ya_trae_la_tarifa_anual(self, client):
        """El seed nunca la tuvo; ahora existe y está verificada."""
        resp = client.get("/api/v1/fiscal/tables/2025/")

        anual = resp.json()["isr_annual"]
        assert anual is not None
        assert len(anual) == 11
        assert anual[-1]["fixed_fee"] == "1414947.85"
        assert resp.json()["tables"]["isr_annual"]["dof_codigo"] == "5746354"

    def test_tables_2025_no_trae_subsidio_de_tramos(self, client):
        """La tabla derogada desapareció: el campo viejo va en null.

        Un consumidor que sólo sepa leer ``subsidio`` falla en claro en vez de
        aplicar tramos que el decreto de 2024 abolió.
        """
        resp = client.get("/api/v1/fiscal/tables/2025/")

        assert resp.json()["subsidio"] is None
        assert resp.json()["subsidio_rule"] is not None

    def test_subsidio_en_enero_2025_es_el_del_transitorio(self, client):
        """474.95 = UMA 2024 (3,300.53) x 14.39 %."""
        resp = client.get("/api/v1/fiscal/tables/2025/", {"on": "2025-01-20"})

        fila = resp.json()["subsidio_rule"][0]
        assert fila["monthly_amount"] == "474.95"
        assert fila["uma_monthly"] == "3300.53"
        assert fila["rate_of_uma"] == "0.1439"

    def test_subsidio_desde_febrero_2025_vuelve_al_138(self, client):
        """474.65 = UMA 2025 (3,439.46) x 13.8 %."""
        resp = client.get("/api/v1/fiscal/tables/2025/", {"on": "2025-02-01"})

        fila = resp.json()["subsidio_rule"][0]
        assert fila["monthly_amount"] == "474.65"
        assert fila["uma_monthly"] == "3439.46"
        assert fila["rate_of_uma"] == "0.138"

    def test_el_31_de_enero_todavia_es_el_transitorio(self, client):
        """Frontera inclusiva: el último día de vigencia sigue siendo suyo."""
        resp = client.get("/api/v1/fiscal/tables/2025/", {"on": "2025-01-31"})

        assert resp.json()["subsidio_rule"][0]["monthly_amount"] == "474.95"

    def test_sin_on_devuelve_la_vigencia_mas_reciente_y_lista_la_otra(self, client):
        """El mismo contrato que 2026, sin sorpresas de orden de diccionario."""
        resp = client.get("/api/v1/fiscal/tables/2025/")
        cuerpo = resp.json()

        assert cuerpo["subsidio_rule"][0]["monthly_amount"] == "474.65"
        superseded = cuerpo["superseded_within_year"]["subsidio_rule"]
        assert len(superseded) == 1
        assert superseded[0]["rows"][0]["monthly_amount"] == "474.95"

    def test_tables_2025_no_esta_todo_publicado(self, client):
        """IMSS e ISN siguen ausentes: ``all_published`` no puede ser true."""
        cuerpo = client.get("/api/v1/fiscal/tables/2025/").json()

        assert cuerpo["imss_rates"] is None
        assert cuerpo["isn_rates"] is None

    def test_publicar_2025_no_reescribe_la_uma(self, client):
        """Este carril no toca escalares: la UMA 2025 sigue como estaba."""
        resp = client.get("/api/v1/fiscal/uma/", {"on": "2025-06-15"})

        assert resp.json()["value"] == "113.1400"
        assert resp.json()["year"] == 2025
