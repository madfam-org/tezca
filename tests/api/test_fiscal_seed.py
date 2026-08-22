"""Tests for the fiscal seed command and its data."""

from io import StringIO

import pytest
from django.core.management import call_command

from apps.api.fiscal_models import FiscalTable, MinimumWage, Provenance, UMAValue
from apps.api.fiscal_seed_data import (
    FISCAL_TABLE_SEEDS,
    ISR_MONTHLY_2025,
    MINIMUM_WAGE_SEEDS,
    SUBSIDIO_MONTHLY_2025,
    UMA_SEEDS,
)


class TestSeedDataIntegrity:
    """The seed constants themselves must be internally coherent."""

    def test_uma_covers_2016_to_2026(self):
        years = [row[0] for row in UMA_SEEDS]
        assert years == list(range(2016, 2027))

    def test_uma_vigencia_periods_are_contiguous(self):
        """Each UMA period must start the day after the previous one ends."""
        from datetime import date, timedelta

        for previous, current in zip(UMA_SEEDS, UMA_SEEDS[1:]):
            prev_to = date.fromisoformat(previous[5])
            cur_from = date.fromisoformat(current[4])
            assert cur_from == prev_to + timedelta(
                days=1
            ), f"gap between {previous[0]} and {current[0]}"

    def test_uma_2025_matches_the_symbiosis_hardcoded_value(self):
        """113.14 is the constant hardcoded in symbiosis mx-payroll imss.py.

        It is documented there as the *2025* value. Serving it under year
        2025 is what lets that hardcode be deleted without changing any
        number the consumer computes.
        """
        row = next(r for r in UMA_SEEDS if r[0] == 2025)
        assert row[1] == "113.14"

    def test_uma_values_increase_monotonically(self):
        values = [float(row[1]) for row in UMA_SEEDS]
        assert values == sorted(values)

    def test_zlfn_only_exists_from_2019(self):
        """The Zona Libre de la Frontera Norte was created for 2019."""
        for year, _general, zlfn in MINIMUM_WAGE_SEEDS:
            if year < 2019:
                assert zlfn is None, f"{year} predates the ZLFN"
            else:
                assert zlfn is not None

    def test_zlfn_always_above_general(self):
        for year, general, zlfn in MINIMUM_WAGE_SEEDS:
            if zlfn is not None:
                assert float(zlfn) > float(general), year

    def test_isr_brackets_are_contiguous(self):
        """Each bracket's lower bound must follow the previous upper bound."""
        for previous, current in zip(ISR_MONTHLY_2025, ISR_MONTHLY_2025[1:]):
            assert float(current["lower"]) > float(previous["upper"])

    def test_isr_top_bracket_is_open_ended(self):
        assert ISR_MONTHLY_2025[-1]["upper"] is None
        assert ISR_MONTHLY_2025[-1]["rate"] == "0.3500"

    def test_isr_rates_increase_monotonically(self):
        rates = [float(row["rate"]) for row in ISR_MONTHLY_2025]
        assert rates == sorted(rates)

    def test_subsidio_top_row_is_zero(self):
        assert SUBSIDIO_MONTHLY_2025[-1]["subsidio"] == "0.00"

    def test_no_2026_tables_are_seeded(self):
        """2026 tables were not sourced, so none are claimed — fail closed."""
        assert all(row[1] != 2026 for row in FISCAL_TABLE_SEEDS)


@pytest.mark.django_db
class TestSeedCommand:
    """python manage.py seed_fiscal_values."""

    def test_dry_run_writes_nothing(self):
        out = StringIO()
        call_command("seed_fiscal_values", "--dry-run", stdout=out)

        assert UMAValue.objects.count() == 0
        assert MinimumWage.objects.count() == 0
        assert FiscalTable.objects.count() == 0
        assert "Would create" in out.getvalue()

    def test_refuses_to_write_without_local_db_guard(self, monkeypatch):
        """AGENTS.md: DB-mutating commands need the LOCAL_DB=yes guard."""
        monkeypatch.delenv("LOCAL_DB", raising=False)
        err = StringIO()
        call_command("seed_fiscal_values", stdout=StringIO(), stderr=err)

        assert UMAValue.objects.count() == 0
        assert "LOCAL_DB=yes" in err.getvalue()

    def test_seeds_all_three_datasets(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("seed_fiscal_values", stdout=StringIO())

        assert UMAValue.objects.count() == len(UMA_SEEDS)
        assert MinimumWage.objects.count() == sum(
            1 for _y, _g, z in MINIMUM_WAGE_SEEDS for _ in range(2 if z else 1)
        )
        assert FiscalTable.objects.count() == len(FISCAL_TABLE_SEEDS)

    def test_every_seeded_row_is_marked_unverified(self, monkeypatch):
        """The feed must never claim DOF verification it does not have."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("seed_fiscal_values", stdout=StringIO())

        for model in (UMAValue, MinimumWage, FiscalTable):
            assert not model.objects.exclude(
                provenance=Provenance.SEED_UNVERIFIED
            ).exists(), model.__name__

    def test_is_idempotent(self, monkeypatch):
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("seed_fiscal_values", stdout=StringIO())
        first = UMAValue.objects.count()

        out = StringIO()
        call_command("seed_fiscal_values", stdout=out)

        assert UMAValue.objects.count() == first
        assert "Created: 0 UMA" in out.getvalue()

    def test_seeded_uma_is_queryable_by_date(self, monkeypatch):
        """The seed must actually answer the feed's primary question."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("seed_fiscal_values", stdout=StringIO())

        row = UMAValue.objects.get(
            vigencia_from__lte="2025-06-15", vigencia_to__gte="2025-06-15"
        )
        assert row.year == 2025
        assert str(row.value) == "113.1400"

    def test_current_uma_row_is_open_ended(self, monkeypatch):
        """Exactly one UMA row must be open-ended, or 'current' is ambiguous."""
        monkeypatch.setenv("LOCAL_DB", "yes")
        call_command("seed_fiscal_values", stdout=StringIO())

        assert UMAValue.objects.filter(vigencia_to__isnull=True).count() == 1
