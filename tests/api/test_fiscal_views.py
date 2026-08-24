"""Tests for the fiscal-value feed endpoints."""

from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.api.fiscal_models import (
    FiscalTable,
    MinimumWage,
    Provenance,
    TipoDeCambio,
    UMAValue,
)
from apps.api.middleware.janua_auth import JanuaUser

AUTH_PATCH = "apps.api.middleware.combined_auth.CombinedAuthentication.authenticate"


def _make_user(scopes=None, tier="essentials"):
    user = JanuaUser({"sub": "fiscal-test", "email": "fiscal@test.com", "tier": tier})
    user.tier = tier
    user.scopes = ["read", "search"] if scopes is None else scopes
    user.allowed_domains = []
    user.api_key_prefix = ""
    return user


def _make_uma(year, daily, v_from, v_to=None, provenance=Provenance.SEED_UNVERIFIED):
    return UMAValue.objects.create(
        year=year,
        value=daily,
        monthly_value="3439.46",
        annual_value="41273.52",
        unit="MXN/day",
        vigencia_from=v_from,
        vigencia_to=v_to,
        provenance=provenance,
        source_citation=f"INEGI UMA {year}",
    )


@pytest.mark.django_db
class TestUmaList:
    """GET /api/v1/fiscal/uma/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("fiscal-uma-list")
        self.user = _make_user()

    def test_requires_authentication(self):
        """Anonymous callers get 401, not data."""
        response = self.client.get(self.url)
        assert response.status_code == 401

    def test_requires_read_scope(self):
        """A key without 'read' scope is refused."""

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (_make_user(scopes=["search"]), "tok")
            response = self.client.get(self.url)
        assert response.status_code == 403
        assert "read" in response.json()["error"]

    def test_lists_values_newest_first(self):

        _make_uma(2025, "113.14", "2025-02-01", "2026-01-31")
        _make_uma(2026, "117.31", "2026-02-01", None)

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["results"][0]["year"] == 2026
        # Decimals are strings so consumers avoid a float round-trip.
        assert data["results"][0]["value"] == "117.3100"
        assert "disclaimer" in data

    def test_filter_by_year(self):

        _make_uma(2025, "113.14", "2025-02-01", "2026-01-31")
        _make_uma(2026, "117.31", "2026-02-01", None)

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url, {"year": 2025})

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["year"] == 2025

    def test_on_date_returns_value_in_force(self):
        """?on= is the primary query shape: value in force on a date."""

        _make_uma(2025, "113.14", "2025-02-01", "2026-01-31")
        _make_uma(2026, "117.31", "2026-02-01", None)

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url, {"on": "2025-06-15"})

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["year"] == 2025
        # Flat keys for symbiosis-hcm's TezcaFiscalClient.get_uma_for_date().
        assert data["value"] == "113.1400"
        assert data["year"] == 2025
        assert data["effective_date"] == "2025-02-01"

    def test_on_date_boundary_is_inclusive(self):
        """A value in force from 2026-02-01 covers exactly that day."""

        _make_uma(2025, "113.14", "2025-02-01", "2026-01-31")
        _make_uma(2026, "117.31", "2026-02-01", None)

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            first = self.client.get(self.url, {"on": "2026-02-01"}).json()
            last = self.client.get(self.url, {"on": "2026-01-31"}).json()

        assert first["year"] == 2026
        assert last["year"] == 2025

    def test_open_ended_row_is_in_force(self):
        """vigencia_to=NULL means still in force, however far in the future."""

        _make_uma(2026, "117.31", "2026-02-01", None)

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url, {"on": "2030-01-01"})

        assert response.json()["count"] == 1

    def test_invalid_on_date_returns_400(self):

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url, {"on": "not-a-date"})

        assert response.status_code == 400

    def test_invalid_year_returns_400(self):

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url, {"year": "abc"})

        assert response.status_code == 400

    def test_provenance_is_exposed_honestly(self):
        """Seed rows must not claim to be verified."""

        _make_uma(2026, "117.31", "2026-02-01", None)

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            row = self.client.get(self.url).json()["results"][0]

        assert row["provenance"] == "seed-unverified"
        assert row["is_verified"] is False

    def test_published_row_is_verified(self):

        _make_uma(2026, "117.31", "2026-02-01", None, provenance=Provenance.PUBLISHED)

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            row = self.client.get(self.url).json()["results"][0]

        assert row["is_verified"] is True


@pytest.mark.django_db
class TestUmaCurrent:
    """GET /api/v1/fiscal/uma/current/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("fiscal-uma-current")
        self.user = _make_user()

    def test_returns_value_in_force_today(self):

        today = date.today()
        _make_uma(today.year, "117.31", today.replace(month=1, day=1), None)

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "117.3100"
        assert data["effective_date"]

    def test_fails_closed_when_no_current_value(self):
        """No row for today → 404, never a stale fallback."""

        _make_uma(2016, "73.04", "2016-01-28", "2017-01-31")

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url)

        assert response.status_code == 404
        assert "stale" in response.json()["detail"]

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestMinimos:
    """GET /api/v1/fiscal/minimos/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("fiscal-minimos-list")
        self.user = _make_user()
        MinimumWage.objects.create(
            year=2026,
            zone="general",
            value="315.04",
            unit="MXN/day",
            vigencia_from="2026-01-01",
            provenance=Provenance.SEED_UNVERIFIED,
        )
        MinimumWage.objects.create(
            year=2026,
            zone="zlfn",
            value="440.87",
            unit="MXN/day",
            vigencia_from="2026-01-01",
            provenance=Provenance.SEED_UNVERIFIED,
        )

    def test_lists_both_zones(self):

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url)

        assert response.status_code == 200
        assert response.json()["count"] == 2

    def test_filter_by_zone(self):

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url, {"zone": "zlfn"})

        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["value"] == "440.8700"

    def test_invalid_zone_returns_400(self):

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url, {"zone": "frontera-sur"})

        assert response.status_code == 400

    def test_on_date_filters_in_force(self):

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            in_force = self.client.get(self.url, {"on": "2026-06-01"}).json()
            before = self.client.get(self.url, {"on": "2025-06-01"}).json()

        assert in_force["count"] == 2
        assert before["count"] == 0

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        assert response.status_code == 401


@pytest.mark.django_db
class TestFiscalTables:
    """GET /api/v1/fiscal/tables/ and /fiscal/tables/<year>/."""

    def setup_method(self):
        self.client = APIClient()
        self.list_url = reverse("fiscal-tables-list")
        self.user = _make_user()
        FiscalTable.objects.create(
            kind="isr_monthly",
            year=2025,
            period="monthly",
            rows=[
                {
                    "lower": "0.01",
                    "upper": "746.04",
                    "fixed_fee": "0.00",
                    "rate": "0.0192",
                }
            ],
            legal_basis="LISR Art. 96",
            vigencia_from="2025-01-01",
            vigencia_to="2025-12-31",
            provenance=Provenance.SEED_UNVERIFIED,
        )
        FiscalTable.objects.create(
            kind="subsidio_monthly",
            year=2025,
            period="monthly",
            rows=[{"lower": "0.01", "upper": "1768.96", "subsidio": "407.02"}],
            legal_basis="Decreto de subsidio al empleo",
            vigencia_from="2025-01-01",
            vigencia_to="2025-12-31",
            provenance=Provenance.SEED_UNVERIFIED,
        )

    def test_lists_tables(self):

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.list_url)

        assert response.status_code == 200
        assert response.json()["count"] == 2

    def test_filter_by_kind(self):

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.list_url, {"kind": "isr_monthly"})

        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["legal_basis"] == "LISR Art. 96"
        assert data["results"][0]["row_count"] == 1

    def test_invalid_kind_returns_400(self):

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.list_url, {"kind": "impuesto-inventado"})

        assert response.status_code == 400

    def test_by_year_groups_for_consumer(self):
        """The shape symbiosis-hcm's get_fiscal_tables(year) consumes."""

        url = reverse("fiscal-tables-by-year", kwargs={"year": 2025})
        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2025
        assert len(data["isr_brackets"]) == 1
        assert len(data["subsidio"]) == 1
        # Nothing seeded for these — absent, not silently substituted.
        assert data["imss_rates"] is None
        assert data["isn_rates"] is None
        assert data["all_published"] is False
        assert data["provenance_summary"]["isr_monthly"] == "seed-unverified"

    def test_by_year_fails_closed_for_unknown_year(self):
        """A year with no tables 404s rather than serving another year's."""

        url = reverse("fiscal-tables-by-year", kwargs={"year": 2026})
        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(url)

        assert response.status_code == 404
        assert response.json()["year"] == 2026

    def test_requires_authentication(self):
        response = self.client.get(self.list_url)
        assert response.status_code == 401


def _make_tc(
    value, v_from, v_to=None, frm="USD", to="MXN", provenance=Provenance.PUBLISHED
):
    return TipoDeCambio.objects.create(
        from_currency=frm,
        to_currency=to,
        value=value,
        unit="MXN",
        vigencia_from=v_from,
        vigencia_to=v_to,
        dof_date=v_from,
        provenance=provenance,
        source_citation=f"DOF {v_from}",
    )


@pytest.mark.django_db
class TestTipoCambioList:
    """GET /api/v1/fiscal/tipo-cambio/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("fiscal-tipo-cambio-list")
        self.user = _make_user()

    def test_requires_authentication(self):
        assert self.client.get(self.url).status_code == 401

    def test_requires_read_scope(self):
        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (_make_user(scopes=["search"]), "tok")
            response = self.client.get(self.url)
        assert response.status_code == 403
        assert "read" in response.json()["error"]

    def test_lists_newest_first(self):
        _make_tc("18.4400", "2026-08-20", "2026-08-20")
        _make_tc("18.5100", "2026-08-21", None)

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["results"][0]["value"] == "18.5100"
        assert data["results"][0]["pair"] == "USD/MXN"

    def test_on_date_returns_rate_in_force(self):
        _make_tc("18.4400", "2026-08-20", "2026-08-20")
        _make_tc("18.5100", "2026-08-21", None)

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url, {"on": "2026-08-20"})

        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "18.4400"
        assert data["rate"] == "18.4400"
        assert data["on"] == "2026-08-20"

    def test_pair_filter_isolates_currency(self):
        _make_tc("18.5100", "2026-08-21", None, frm="USD", to="MXN")
        _make_tc("21.7000", "2026-08-21", None, frm="EUR", to="MXN")

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url, {"from": "EUR", "to": "MXN"})

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["value"] == "21.7000"

    def test_decimal_emitted_as_string(self):
        """A rate must never round-trip through float on the wire."""
        _make_tc("18.5137", "2026-08-21", None)

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url, {"on": "2026-08-21"})

        assert response.json()["results"][0]["value"] == "18.5137"

    def test_provenance_exposed_honestly(self):
        _make_tc("18.5100", "2026-08-21", None, provenance=Provenance.SEED_UNVERIFIED)

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url)

        row = response.json()["results"][0]
        assert row["provenance"] == "seed-unverified"
        assert row["is_verified"] is False


@pytest.mark.django_db
class TestTipoCambioCurrent:
    """GET /api/v1/fiscal/tipo-cambio/current/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("fiscal-tipo-cambio-current")
        self.user = _make_user()

    def test_returns_rate_in_force_today(self):
        today = date.today()
        _make_tc("18.5100", today, None)

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "18.5100"
        assert data["pair"] == "USD/MXN"
        assert data["effective_date"]

    def test_fails_closed_when_no_current_rate(self):
        """No DOF rate for today → 404, never a stale or market fallback."""
        _make_tc("17.0000", "2024-01-02", "2024-01-02")

        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            response = self.client.get(self.url)

        assert response.status_code == 404
        assert "stale" in response.json()["detail"]

    def test_pair_defaults_to_usd_mxn_and_isolates(self):
        today = date.today()
        _make_tc("18.5100", today, None, frm="USD", to="MXN")
        # No EUR row today → EUR query fails closed even though USD exists.
        with patch(AUTH_PATCH) as mock_auth:
            mock_auth.return_value = (self.user, "tok")
            eur = self.client.get(self.url, {"from": "EUR", "to": "MXN"})
            usd = self.client.get(self.url)

        assert usd.status_code == 200
        assert eur.status_code == 404

    def test_requires_authentication(self):
        assert self.client.get(self.url).status_code == 401
