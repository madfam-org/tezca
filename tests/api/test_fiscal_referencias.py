"""UDI and interest-withholding feed: the DOF transcription, the publisher and the endpoints."""

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.fiscal_dof_referencias import (
    RETENCION_INTERESES,
    UDI_AVISO_2026_11_10,
    UDI_AVISO_2026_11_25,
    UDI_AVISOS,
    retencion_rows,
    udi_rows,
)
from apps.api.fiscal_models import Provenance, RetencionIntereses, UDIValue
from apps.api.middleware.janua_auth import JanuaUser

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"


def _make_user(scopes=None):
    user = JanuaUser(
        {"sub": "fiscal-test", "email": "fiscal@test.com", "tier": "essentials"}
    )
    user.tier = "essentials"
    user.scopes = ["read", "search"] if scopes is None else scopes
    user.allowed_domains = []
    user.api_key_prefix = ""
    return user


def _udi_days():
    return [date.fromisoformat(row["vigencia_from"]) for row in udi_rows()]


def _publish(monkeypatch, *args):
    monkeypatch.setenv("LOCAL_DB", "yes")
    out = StringIO()
    call_command("publish_fiscal_referencias", *args, stdout=out)
    return out.getvalue()


class TestTranscripcion:
    """Lo que el módulo afirma haber leído del DOF."""

    @pytest.mark.parametrize(
        "aviso, first, last",
        [
            (UDI_AVISO_2026_11_10, date(2026, 11, 11), date(2026, 11, 25)),
            (UDI_AVISO_2026_11_25, date(2026, 11, 26), date(2026, 12, 10)),
        ],
    )
    def test_el_aviso_cubre_quince_dias_seguidos(self, aviso, first, last):
        days = [date.fromisoformat(day) for day, _ in aviso["values"]]
        assert len(days) == 15
        assert days[0] == first and days[-1] == last
        assert all(b - a == timedelta(days=1) for a, b in zip(days, days[1:]))

    def test_los_avisos_se_encadenan_sin_hueco_ni_repeticion(self):
        days = _udi_days()
        assert len(days) == sum(len(aviso["values"]) for aviso in UDI_AVISOS)
        assert len(set(days)) == len(days)
        assert all(b - a == timedelta(days=1) for a, b in zip(days, days[1:]))

    def test_la_udi_sube_cada_dia_y_trae_seis_decimales(self):
        values = [row["value"] for row in udi_rows()]
        assert all(len(value.split(".")[1]) == 6 for value in values)
        decimals = [Decimal(v) for v in values]
        assert all(a < b <= a + Decimal("0.01") for a, b in zip(decimals, decimals[1:]))
        assert dict(UDI_AVISO_2026_11_10["values"])["2026-11-20"] == "8.920859"
        assert dict(UDI_AVISO_2026_11_25["values"])["2026-12-01"] == "8.951775"

    def test_cada_fila_cita_su_aviso(self):
        avisos = {
            "2026-11-10": "5803350",
            "2026-11-25": "5805263",
        }
        assert {a["dof_date"]: a["dof_codigo"] for a in UDI_AVISOS} == avisos
        rows = udi_rows()
        assert {row["dof_date"] for row in rows} == set(avisos)
        for aviso in UDI_AVISOS:
            own_days = {day for day, _ in aviso["values"]}
            year, month, day = aviso["dof_date"].split("-")
            for row in rows:
                if row["vigencia_from"] not in own_days:
                    continue
                assert row["dof_codigo"] == aviso["dof_codigo"]
                assert row["dof_date"] == aviso["dof_date"]
                assert row["source_url"].endswith(
                    f"codigo={aviso['dof_codigo']}&fecha={day}/{month}/{year}"
                )
                assert row["source_citation"] == aviso["source_citation"]
        for row in rows:
            assert row["vigencia_from"] == row["vigencia_to"]
            assert row["unit"] == "MXN/UDI"

    def test_la_retencion_es_una_fila_por_ejercicio(self):
        assert [spec["year"] for spec in RETENCION_INTERESES] == [2026, 2027]
        by_year = {row["year"]: row for row in retencion_rows()}
        assert (
            by_year[2026]["value"] == "0.90"
            and by_year[2026]["dof_codigo"] == "5772357"
        )
        assert (
            by_year[2027]["value"] == "0.68"
            and by_year[2027]["dof_codigo"] == "5803757"
        )
        for row in by_year.values():
            assert row["unit"] == "percent"
            assert row["vigencia_from"] == f"{row['year']}-01-01"
            assert row["vigencia_to"] == f"{row['year']}-12-31"
            assert date.fromisoformat(row["dof_date"]).year == row["year"] - 1


@pytest.mark.django_db
class TestPublicacion:
    def test_se_niega_a_escribir_sin_confirmacion(self, monkeypatch):
        monkeypatch.delenv("LOCAL_DB", raising=False)
        with pytest.raises(CommandError):
            call_command("publish_fiscal_referencias", stdout=StringIO())
        assert UDIValue.objects.count() == 0

    def test_dry_run_no_escribe(self, monkeypatch):
        monkeypatch.delenv("LOCAL_DB", raising=False)
        out = StringIO()
        call_command("publish_fiscal_referencias", "--dry-run", stdout=out)
        expected = len(udi_rows()) + len(retencion_rows())
        assert f"Would publish: {expected} filas nuevas" in out.getvalue()
        assert UDIValue.objects.count() == 0 and RetencionIntereses.objects.count() == 0

    def test_publica_y_es_idempotente(self, monkeypatch):
        udi_count, retencion_count = len(udi_rows()), len(retencion_rows())
        assert udi_count == 30 and retencion_count == 2
        expected = udi_count + retencion_count
        assert f"Published: {expected} filas nuevas" in _publish(monkeypatch)
        assert (
            UDIValue.objects.count() == udi_count
            and RetencionIntereses.objects.count() == retencion_count
        )
        row = UDIValue.objects.get(vigencia_from=date(2026, 11, 20))
        assert (
            row.value == Decimal("8.920859") and row.provenance == Provenance.PUBLISHED
        )
        assert "0 filas nuevas" in _publish(monkeypatch)
        assert (
            UDIValue.objects.count() == udi_count
            and RetencionIntereses.objects.count() == retencion_count
        )

    def test_una_diferencia_detiene_todo_sin_escribir(self, monkeypatch):
        UDIValue.objects.create(
            value="8.000000",
            unit="MXN/UDI",
            vigencia_from=date(2026, 11, 20),
            vigencia_to=date(2026, 11, 20),
            provenance=Provenance.OPERATOR,
        )
        with pytest.raises(CommandError, match="UDI 2026-11-20"):
            _publish(monkeypatch)
        assert UDIValue.objects.count() == 1
        assert RetencionIntereses.objects.count() == 0


@pytest.mark.django_db
class TestUdiEndpoints:
    def setup_method(self):
        self.client = APIClient()
        self.user = _make_user()
        for row in udi_rows():
            UDIValue.objects.create(**row, provenance=Provenance.PUBLISHED)

    def test_requires_authentication_and_scope(self):
        for name in (
            "fiscal-udi-list",
            "fiscal-udi-current",
            "fiscal-retencion-intereses-list",
        ):
            assert self.client.get(reverse(name)).status_code == 401
            with patch(AUTH_PATCH, return_value=(_make_user(scopes=["search"]), "k")):
                assert self.client.get(reverse(name)).status_code == 403

    def test_un_dia(self):
        with patch(AUTH_PATCH, return_value=(self.user, "k")):
            data = self.client.get(
                reverse("fiscal-udi-list"), {"on": "2026-11-20"}
            ).json()
        assert data["count"] == 1 and data["value"] == "8.920859"
        assert data["provenance"] == "published"
        row = data["results"][0]
        assert row["date"] == "2026-11-20" and row["is_verified"] is True
        assert row["dof_codigo"] == "5803350" and "in_force" not in row

    def test_un_dia_sin_fila_no_se_rellena(self):
        day_after = (max(_udi_days()) + timedelta(days=1)).isoformat()
        with patch(AUTH_PATCH, return_value=(self.user, "k")):
            data = self.client.get(reverse("fiscal-udi-list"), {"on": day_after}).json()
        assert data["count"] == 0 and "value" not in data

    def test_un_rango(self):
        with patch(AUTH_PATCH, return_value=(self.user, "k")):
            data = self.client.get(
                reverse("fiscal-udi-list"), {"from": "2026-11-18", "to": "2026-11-20"}
            ).json()
        assert [row["date"] for row in data["results"]] == [
            "2026-11-20",
            "2026-11-19",
            "2026-11-18",
        ]
        assert data["from"] == "2026-11-18" and data["to"] == "2026-11-20"

    @pytest.mark.parametrize(
        "params",
        [
            {"on": "20-11-2026"},
            {"from": "2026-11-18"},
            {"to": "2026-11-18"},
            {"from": "2026-11-20", "to": "2026-11-18"},
            {"from": "2025-01-01", "to": "2026-11-18"},
            {"from": "ayer", "to": "hoy"},
            {"on": "2026-11-20", "from": "2026-11-18", "to": "2026-11-20"},
        ],
    )
    def test_filtros_invalidos_son_400(self, params):
        with patch(AUTH_PATCH, return_value=(self.user, "k")):
            assert (
                self.client.get(reverse("fiscal-udi-list"), params).status_code == 400
            )

    def test_hoy_falla_cerrado_si_no_hay_fila(self):
        last = max(_udi_days())
        assert last == date(2026, 12, 10)
        with patch(AUTH_PATCH, return_value=(self.user, "k")), patch(
            "apps.api.fiscal_reference_views.timezone.localdate",
            return_value=last + timedelta(days=1),
        ):
            response = self.client.get(reverse("fiscal-udi-current"))
        assert response.status_code == 404
        assert response.json()["latest_on_file"] == last.isoformat()

    def test_hoy(self):
        with patch(AUTH_PATCH, return_value=(self.user, "k")), patch(
            "apps.api.fiscal_reference_views.timezone.localdate",
            return_value=date(2026, 11, 21),
        ):
            data = self.client.get(reverse("fiscal-udi-current")).json()
        assert data["value"] == "8.923181" and data["on"] == "2026-11-21"


@pytest.mark.django_db
class TestRetencionEndpoint:
    def setup_method(self):
        self.client = APIClient()
        self.user = _make_user()
        for row in retencion_rows():
            RetencionIntereses.objects.create(**row, provenance=Provenance.PUBLISHED)

    def test_lista_el_ejercicio_mas_reciente_primero(self):
        with patch(AUTH_PATCH, return_value=(self.user, "k")):
            data = self.client.get(reverse("fiscal-retencion-intereses-list")).json()
        assert [row["year"] for row in data["results"]] == [2027, 2026]

    def test_un_ejercicio(self):
        with patch(AUTH_PATCH, return_value=(self.user, "k")):
            data = self.client.get(
                reverse("fiscal-retencion-intereses-list"), {"year": "2026"}
            ).json()
        assert data["value"] == "0.9000" and data["tasa"] == "0.009000"
        assert (
            data["results"][0]["legal_basis"] == "LIF 2026 Art. 24; LISR Arts. 54 y 135"
        )

    def test_un_ejercicio_sin_ley_publicada_no_tiene_fila(self):
        with patch(AUTH_PATCH, return_value=(self.user, "k")):
            data = self.client.get(
                reverse("fiscal-retencion-intereses-list"), {"year": "2028"}
            ).json()
        assert data["count"] == 0 and "value" not in data

    def test_ano_invalido_es_400(self):
        with patch(AUTH_PATCH, return_value=(self.user, "k")):
            response = self.client.get(
                reverse("fiscal-retencion-intereses-list"), {"year": "dos mil"}
            )
        assert response.status_code == 400
