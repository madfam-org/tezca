"""Tests for the DOF exchange-rate source abstraction + ingestion."""

import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.api.fiscal_fx_sources import (
    BanxicoSieSource,
    DofOpenDataSource,
    OperatorSource,
    TipoDeCambioObservation,
    _to_decimal,
    get_source,
    ingest_tipo_de_cambio,
)
from apps.api.fiscal_models import Provenance, TipoDeCambio

TODAY = datetime.date(2026, 8, 21)


class TestToDecimal:
    def test_parses_plain_number(self):
        assert _to_decimal("18.5137") == Decimal("18.5137")

    def test_strips_thousands_separators(self):
        assert _to_decimal("1,234.56") == Decimal("1234.56")

    def test_rejects_zero_and_negative(self):
        assert _to_decimal("0") is None
        assert _to_decimal("-1.2") is None

    def test_rejects_junk_and_none(self):
        assert _to_decimal("N/E") is None
        assert _to_decimal(None) is None

    def test_no_float_roundtrip(self):
        # A float would introduce 0.1+0.2 style error; Decimal from str is exact.
        assert str(_to_decimal("18.5100")) == "18.5100"


class TestGetSource:
    def test_default_is_operator(self):
        assert isinstance(get_source(), OperatorSource)
        assert isinstance(get_source(""), OperatorSource)

    def test_unknown_falls_back_to_operator(self):
        assert isinstance(get_source("nope"), OperatorSource)

    def test_resolves_named_sources(self):
        assert isinstance(get_source("dof_open_data"), DofOpenDataSource)
        assert isinstance(get_source("banxico_sie", token="t"), BanxicoSieSource)


class TestOperatorSource:
    def test_fetch_always_none(self):
        assert OperatorSource().fetch(TODAY, "USD", "MXN") is None


class TestBanxicoSieSource:
    def test_opts_out_without_token(self):
        assert BanxicoSieSource(token="").fetch(TODAY, "USD", "MXN") is None

    def test_non_usd_mxn_unsupported(self):
        assert BanxicoSieSource(token="t").fetch(TODAY, "EUR", "MXN") is None

    def test_parses_banxico_response(self):
        fake_resp = MagicMock()
        fake_resp.json.return_value = {
            "bmx": {"series": [{"datos": [{"fecha": "21/08/2026", "dato": "18.5100"}]}]}
        }
        fake_resp.raise_for_status.return_value = None
        fake_session = MagicMock()
        fake_session.get.return_value = fake_resp

        with patch("apps.scraper.http.government_session", return_value=fake_session):
            obs = BanxicoSieSource(token="t").fetch(TODAY, "USD", "MXN")

        assert isinstance(obs, TipoDeCambioObservation)
        assert obs.value == Decimal("18.5100")
        assert obs.from_currency == "USD" and obs.to_currency == "MXN"
        assert obs.vigencia_from == TODAY

    def test_returns_none_on_empty_datos(self):
        fake_resp = MagicMock()
        fake_resp.json.return_value = {"bmx": {"series": [{"datos": []}]}}
        fake_resp.raise_for_status.return_value = None
        fake_session = MagicMock()
        fake_session.get.return_value = fake_resp

        with patch("apps.scraper.http.government_session", return_value=fake_session):
            assert BanxicoSieSource(token="t").fetch(TODAY, "USD", "MXN") is None

    def test_never_raises_on_http_error(self):
        fake_session = MagicMock()
        fake_session.get.side_effect = RuntimeError("network down")

        with patch("apps.scraper.http.government_session", return_value=fake_session):
            # Best-effort: swallows and returns None, never propagates.
            assert BanxicoSieSource(token="t").fetch(TODAY, "USD", "MXN") is None


class TestDofOpenDataSource:
    def test_returns_none_on_unfamiliar_shape(self):
        fake_resp = MagicMock()
        fake_resp.json.return_value = {"ListaDiarios": []}  # empty / no notas
        fake_resp.raise_for_status.return_value = None
        fake_session = MagicMock()
        fake_session.get.return_value = fake_resp

        with patch("apps.scraper.http.government_session", return_value=fake_session):
            assert DofOpenDataSource().fetch(TODAY, "USD", "MXN") is None

    def test_never_raises_on_error(self):
        fake_session = MagicMock()
        fake_session.get.side_effect = RuntimeError("boom")
        with patch("apps.scraper.http.government_session", return_value=fake_session):
            assert DofOpenDataSource().fetch(TODAY, "USD", "MXN") is None

    def test_extracts_when_a_cambio_nota_carries_a_numeric_rate(self):
        # A defensive best-effort parse: given a nota that looks like the
        # Banco de México tipo-de-cambio entry with an explicit numeric field.
        fake_resp = MagicMock()
        fake_resp.json.return_value = {
            "ListaDiarios": [
                {
                    "Notas": [
                        {"titulo": "SECRETARÍA DE HACIENDA — algo", "valor": None},
                        {
                            "titulo": "BANCO DE MÉXICO — Tipo de cambio para pagos",
                            "valor": "18.5100",
                        },
                    ]
                }
            ]
        }
        fake_resp.raise_for_status.return_value = None
        fake_session = MagicMock()
        fake_session.get.return_value = fake_resp

        with patch("apps.scraper.http.government_session", return_value=fake_session):
            obs = DofOpenDataSource().fetch(TODAY, "USD", "MXN")

        assert obs is not None
        assert obs.value == Decimal("18.5100")


@pytest.mark.django_db
class TestIngest:
    def test_operator_source_writes_nothing(self):
        row = ingest_tipo_de_cambio(on=TODAY, source_name="operator")
        assert row is None
        assert TipoDeCambio.objects.count() == 0

    def test_ingests_from_a_fetching_source(self):
        fake_resp = MagicMock()
        fake_resp.json.return_value = {
            "bmx": {"series": [{"datos": [{"fecha": "21/08/2026", "dato": "18.5100"}]}]}
        }
        fake_resp.raise_for_status.return_value = None
        fake_session = MagicMock()
        fake_session.get.return_value = fake_resp

        with patch("apps.scraper.http.government_session", return_value=fake_session):
            row = ingest_tipo_de_cambio(on=TODAY, source_name="banxico_sie", token="t")

        assert row is not None
        assert row.value == Decimal("18.5100")
        assert row.provenance == Provenance.PUBLISHED
        assert row.from_currency == "USD" and row.to_currency == "MXN"
        assert TipoDeCambio.objects.count() == 1

    def test_ingest_is_append_only_idempotent(self):
        # Pre-existing published row for the day is never overwritten.
        existing = TipoDeCambio.objects.create(
            from_currency="USD",
            to_currency="MXN",
            value=Decimal("18.4000"),
            unit="MXN",
            vigencia_from=TODAY,
            dof_date=TODAY,
            provenance=Provenance.PUBLISHED,
        )
        fake_resp = MagicMock()
        fake_resp.json.return_value = {
            "bmx": {"series": [{"datos": [{"fecha": "21/08/2026", "dato": "18.9999"}]}]}
        }
        fake_resp.raise_for_status.return_value = None
        fake_session = MagicMock()
        fake_session.get.return_value = fake_resp

        with patch("apps.scraper.http.government_session", return_value=fake_session):
            row = ingest_tipo_de_cambio(on=TODAY, source_name="banxico_sie", token="t")

        assert TipoDeCambio.objects.count() == 1
        assert row.id == existing.id
        assert row.value == Decimal("18.4000")  # unchanged
