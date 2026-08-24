"""Seed the fiscal-value feed.

    python manage.py seed_fiscal_values --dry-run
    LOCAL_DB=yes python manage.py seed_fiscal_values

Idempotent: rows are matched on their natural key (year + vigencia_from,
plus zone/kind) and skipped if already present. Never overwrites a row an
operator has promoted to ``provenance='published'`` — the seed is a floor,
not an authority.

Writes are DB-mutating, so per AGENTS.md this command requires the
``LOCAL_DB=yes`` guard unless ``--dry-run`` is passed.
"""

import os

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.api.fiscal_models import (
    FiscalTable,
    MinimumWage,
    Provenance,
    TipoDeCambio,
    UMAValue,
)
from apps.api.fiscal_seed_data import (
    FISCAL_TABLE_SEEDS,
    ISR_NOTE,
    MINIMUM_WAGE_SEEDS,
    SEED_NOTE,
    TIPO_CAMBIO_NOTE,
    TIPO_CAMBIO_SEEDS,
    UMA_SEEDS,
)


class Command(BaseCommand):
    help = "Seed UMA, salario mínimo and fiscal tables (provenance=seed-unverified)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be written without touching the database",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if not dry_run and os.environ.get("LOCAL_DB") != "yes":
            self.stderr.write(
                self.style.ERROR(
                    "Refusing to write: this command mutates the database. "
                    "Re-run with --dry-run, or set LOCAL_DB=yes to confirm."
                )
            )
            return

        created = {"uma": 0, "minimos": 0, "tables": 0, "tipo_cambio": 0}
        skipped = {"uma": 0, "minimos": 0, "tables": 0, "tipo_cambio": 0}

        with transaction.atomic():
            self._seed_uma(dry_run, created, skipped)
            self._seed_minimos(dry_run, created, skipped)
            self._seed_tipo_cambio(dry_run, created, skipped)
            self._seed_tables(dry_run, created, skipped)

            if dry_run:
                transaction.set_rollback(True)

        verb = "Would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb}: {created['uma']} UMA, {created['minimos']} salario "
                f"mínimo, {created['tipo_cambio']} tipo de cambio, "
                f"{created['tables']} fiscal tables. "
                f"Skipped (already present): {skipped['uma']} / "
                f"{skipped['minimos']} / {skipped['tipo_cambio']} / "
                f"{skipped['tables']}."
            )
        )
        self.stdout.write(
            "All seeded rows carry provenance='seed-unverified'. Promote to "
            "'published' only after reading the cited DOF publication."
        )

    def _seed_uma(self, dry_run, created, skipped):
        for year, daily, monthly, annual, v_from, v_to in UMA_SEEDS:
            if UMAValue.objects.filter(year=year, vigencia_from=v_from).exists():
                skipped["uma"] += 1
                continue
            created["uma"] += 1
            self.stdout.write(f"  UMA {year}: {daily}/day (from {v_from})")
            if dry_run:
                continue
            UMAValue.objects.create(
                year=year,
                value=daily,
                monthly_value=monthly,
                annual_value=annual,
                unit="MXN/day",
                vigencia_from=v_from,
                vigencia_to=v_to,
                source_citation=(
                    f"INEGI, valor de la UMA {year} (DOF, enero {year}); LFVUMA Art. 4"
                ),
                provenance=Provenance.SEED_UNVERIFIED,
                notes=SEED_NOTE,
            )

    def _seed_minimos(self, dry_run, created, skipped):
        for year, general, zlfn in MINIMUM_WAGE_SEEDS:
            v_from = f"{year}-01-01"
            v_to = (
                f"{year}-12-31"
                if year < max(y for y, _, _ in MINIMUM_WAGE_SEEDS)
                else None
            )
            for zone, amount in (("general", general), ("zlfn", zlfn)):
                if amount is None:
                    continue
                exists = MinimumWage.objects.filter(
                    year=year, zone=zone, vigencia_from=v_from
                ).exists()
                if exists:
                    skipped["minimos"] += 1
                    continue
                created["minimos"] += 1
                self.stdout.write(f"  Salario mínimo {zone} {year}: {amount}")
                if dry_run:
                    continue
                MinimumWage.objects.create(
                    year=year,
                    zone=zone,
                    value=amount,
                    unit="MXN/day",
                    vigencia_from=v_from,
                    vigencia_to=v_to,
                    source_citation=(
                        f"CONASAMI, resolución de salarios mínimos {year} "
                        "(DOF, diciembre del año anterior); LFT Art. 90-97"
                    ),
                    provenance=Provenance.SEED_UNVERIFIED,
                    notes=SEED_NOTE,
                )

    def _seed_tipo_cambio(self, dry_run, created, skipped):
        for frm, to, value, v_from in TIPO_CAMBIO_SEEDS:
            if TipoDeCambio.objects.filter(
                from_currency=frm, to_currency=to, vigencia_from=v_from
            ).exists():
                skipped["tipo_cambio"] += 1
                continue
            created["tipo_cambio"] += 1
            self.stdout.write(f"  Tipo de cambio {frm}/{to} {v_from}: {value}")
            if dry_run:
                continue
            TipoDeCambio.objects.create(
                from_currency=frm,
                to_currency=to,
                value=value,
                unit="MXN",
                vigencia_from=v_from,
                vigencia_to=None,
                dof_date=v_from,
                source_citation=f"DOF {v_from}, Banco de México (tipo de cambio FIX)",
                # OPERATOR, not seed-unverified: a single hand-entered day, meant
                # to be superseded by the automated source — not seed history.
                provenance=Provenance.OPERATOR,
                notes=TIPO_CAMBIO_NOTE,
            )

    def _seed_tables(self, dry_run, created, skipped):
        for kind, year, period, rows, basis, v_from, v_to in FISCAL_TABLE_SEEDS:
            if FiscalTable.objects.filter(
                kind=kind, year=year, vigencia_from=v_from
            ).exists():
                skipped["tables"] += 1
                continue
            created["tables"] += 1
            self.stdout.write(f"  Table {kind} {year}: {len(rows)} rows")
            if dry_run:
                continue
            FiscalTable.objects.create(
                kind=kind,
                year=year,
                period=period,
                rows=rows,
                legal_basis=basis,
                vigencia_from=v_from,
                vigencia_to=v_to,
                source_citation=f"{basis}; tablas SAT {year}",
                provenance=Provenance.SEED_UNVERIFIED,
                notes=ISR_NOTE,
            )
