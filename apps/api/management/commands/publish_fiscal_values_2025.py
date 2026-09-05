"""Publica la errata fiscal 2025 verificada contra el DOF.

    python manage.py publish_fiscal_values_2025 --dry-run
    LOCAL_DB=yes python manage.py publish_fiscal_values_2025

Gemelo de ``publish_fiscal_values_2026``, con una diferencia de fondo: aquel
**completaba** un año sin cifras verificadas; éste **corrige** cifras que ya
estaban sembradas y son incorrectas (ver ``apps.api.fiscal_dof_2025``).

Qué escribe
-----------

1. **ISR mensual 2025** — promueve la fila sembrada, corrigiendo seis cuotas
   fijas mal transcritas, y la sella ``published`` con el Anexo 8 de la RMF
   2025.
2. **ISR anual 2025** — fila nueva; el seed nunca la tuvo.
3. **Subsidio al empleo 2025** — dos filas ``subsidio_rule`` (enero al
   14.39 %, febrero-diciembre al 13.8 %), el mismo ``kind`` que introdujo el
   carril 2026.
4. **Retira la tabla derogada** ``subsidio_monthly`` 2025 que el seed escribió.

Sobre el punto 4: **no se conserva «por compatibilidad»**. Es la tabla de
montos por tramos que el decreto DOF 01-05-2024 sustituyó, y que el propio
considerando de su modificación cita como el defecto que vino a corregir. Un
consumidor que la lea calcula mal. La fila se **borra** en lugar de cerrarle la
vigencia porque nunca fue derecho vigente en 2025: no es historia que preservar
sino una transcripción equivocada, y dejarla con ``vigencia_to`` sólo la
escondería detrás de un ``?on=`` de enero. El append-only protege la historia
de los valores *que estuvieron en vigor*; esta tabla no lo estuvo ni un día del
ejercicio 2025.

Ese borrado toca **sólo** una fila ``subsidio_monthly`` del año 2025 que siga
en ``seed-unverified``. Si un operador la promovió a ``published`` a mano, el
comando se detiene y lo dice: deshacer un acto deliberado de operador no es
decisión de un comando.
"""

import os

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.api.fiscal_dof_2025 import (
    ISR_2025_DOF,
    ISR_ANNUAL_2025,
    ISR_ANNUAL_2025_DOF,
)
from apps.api.fiscal_dof_2025 import ISR_MONTHLY_2025 as ISR_MONTHLY_2025_DOF_ROWS
from apps.api.fiscal_dof_2025 import (
    ISR_MONTHLY_2025_NOTES,
    SUBSIDIO_2025_DOF,
    SUBSIDIO_2025_PERIODS,
    SUBSIDIO_2025_RETIRO_RAZON,
)
from apps.api.fiscal_dof_2026 import subsidio_rule_rows
from apps.api.fiscal_models import FiscalTable, Provenance


class Command(BaseCommand):
    help = "Publica la errata fiscal 2025 (ISR mensual, ISR anual, subsidio)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Reporta lo que escribiría sin tocar la base de datos",
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

        self.counts = {"created": 0, "promoted": 0, "kept": 0, "retired": 0}

        with transaction.atomic():
            self._publish_isr_monthly(dry_run)
            self._publish_isr_annual(dry_run)
            self._publish_subsidio(dry_run)
            self._retire_subsidio_derogado(dry_run)

            if dry_run:
                transaction.set_rollback(True)

        verb = "Would publish" if dry_run else "Published"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb}: {self.counts['created']} filas nuevas, "
                f"{self.counts['promoted']} promovidas desde seed-unverified, "
                f"{self.counts['retired']} retiradas por derogación. "
                f"Intactas (ya published): {self.counts['kept']}."
            )
        )

    # -- helpers ------------------------------------------------------------

    def _skip_if_published(self, row, label) -> bool:
        """Nunca sobrescribimos una fila ya publicada."""
        if row is not None and row.provenance == Provenance.PUBLISHED:
            self.counts["kept"] += 1
            self.stdout.write(f"  = {label}: ya published, intacta")
            return True
        return False

    def _record(self, existing, label):
        if existing is None:
            self.counts["created"] += 1
            self.stdout.write(self.style.SUCCESS(f"  + {label}: fila nueva"))
        else:
            self.counts["promoted"] += 1
            self.stdout.write(
                self.style.WARNING(
                    f"  ^ {label}: promovida seed-unverified → published"
                )
            )

    def _upsert(self, existing, fields):
        if existing is None:
            FiscalTable.objects.create(**fields)
        else:
            for key, value in fields.items():
                setattr(existing, key, value)
            existing.save()

    # -- datasets -----------------------------------------------------------

    def _publish_isr_monthly(self, dry_run):
        existing = FiscalTable.objects.filter(
            kind=FiscalTable.Kind.ISR_MONTHLY, year=2025, vigencia_from="2025-01-01"
        ).first()
        label = f"ISR mensual 2025 ({len(ISR_MONTHLY_2025_DOF_ROWS)} tramos)"
        if self._skip_if_published(existing, label):
            return
        self._record(existing, label)
        if existing is not None:
            self.stdout.write(
                "    · seis cuotas fijas corregidas contra el Anexo 8 "
                "(tramos 6 a 11)"
            )
        if dry_run:
            return

        self._upsert(
            existing,
            {
                "kind": FiscalTable.Kind.ISR_MONTHLY,
                "year": 2025,
                "period": "monthly",
                "rows": ISR_MONTHLY_2025_DOF_ROWS,
                "legal_basis": "LISR Art. 96; Anexo 8 RMF 2025, apartado A fr. V",
                "vigencia_from": "2025-01-01",
                "vigencia_to": "2025-12-31",
                "dof_date": ISR_2025_DOF["dof_date"],
                "dof_codigo": ISR_2025_DOF["dof_codigo"],
                "source_url": ISR_2025_DOF["source_url"],
                "source_citation": ISR_2025_DOF["source_citation"],
                "provenance": Provenance.PUBLISHED,
                "notes": ISR_MONTHLY_2025_NOTES,
            },
        )

    def _publish_isr_annual(self, dry_run):
        existing = FiscalTable.objects.filter(
            kind=FiscalTable.Kind.ISR_ANNUAL, year=2025, vigencia_from="2025-01-01"
        ).first()
        label = f"ISR anual 2025 ({len(ISR_ANNUAL_2025)} tramos)"
        if self._skip_if_published(existing, label):
            return
        self._record(existing, label)
        if dry_run:
            return

        self._upsert(
            existing,
            {
                "kind": FiscalTable.Kind.ISR_ANNUAL,
                "year": 2025,
                "period": "annual",
                "rows": ISR_ANNUAL_2025,
                "legal_basis": "LISR Art. 152; Anexo 8 RMF 2025, apartado C fr. II",
                "vigencia_from": "2025-01-01",
                "vigencia_to": "2025-12-31",
                "dof_date": ISR_ANNUAL_2025_DOF["dof_date"],
                "dof_codigo": ISR_ANNUAL_2025_DOF["dof_codigo"],
                "source_url": ISR_ANNUAL_2025_DOF["source_url"],
                "source_citation": ISR_ANNUAL_2025_DOF["source_citation"],
                "provenance": Provenance.PUBLISHED,
                "notes": ISR_ANNUAL_2025_DOF["notes"],
            },
        )

    def _publish_subsidio(self, dry_run):
        for v_from, v_to, uma_monthly, rate, amount, note in SUBSIDIO_2025_PERIODS:
            existing = FiscalTable.objects.filter(
                kind=FiscalTable.Kind.SUBSIDIO_RULE, year=2025, vigencia_from=v_from
            ).first()
            label = f"Subsidio al empleo 2025 desde {v_from}: {amount}/mes"
            if self._skip_if_published(existing, label):
                continue
            self._record(existing, label)
            if dry_run:
                continue

            self._upsert(
                existing,
                {
                    "kind": FiscalTable.Kind.SUBSIDIO_RULE,
                    "year": 2025,
                    "period": "monthly",
                    "rows": subsidio_rule_rows(uma_monthly, amount, rate),
                    "legal_basis": (
                        "Decreto del subsidio para el empleo (DOF 01-05-2024, "
                        "modificado 31-12-2024)"
                    ),
                    "vigencia_from": v_from,
                    "vigencia_to": v_to,
                    "dof_date": SUBSIDIO_2025_DOF["dof_date"],
                    "dof_codigo": SUBSIDIO_2025_DOF["dof_codigo"],
                    "source_url": SUBSIDIO_2025_DOF["source_url"],
                    "source_citation": SUBSIDIO_2025_DOF["source_citation"],
                    "provenance": Provenance.PUBLISHED,
                    "notes": f"{SUBSIDIO_2025_DOF['notes']} {note}",
                },
            )

    def _retire_subsidio_derogado(self, dry_run):
        """Borra la tabla de tramos derogada que el seed escribió para 2025."""
        derogadas = FiscalTable.objects.filter(
            kind=FiscalTable.Kind.SUBSIDIO_MONTHLY, year=2025
        )
        if not derogadas.exists():
            return

        publicadas = derogadas.filter(provenance=Provenance.PUBLISHED)
        if publicadas.exists():
            self.stdout.write(
                self.style.WARNING(
                    "  ! subsidio_monthly 2025 está 'published': un operador la "
                    "selló a mano y este comando NO la retira. Revísala: la "
                    "tabla de tramos quedó derogada por el decreto DOF "
                    "01-05-2024."
                )
            )
            return

        for row in derogadas:
            self.counts["retired"] += 1
            self.stdout.write(
                self.style.WARNING(
                    f"  - subsidio_monthly {row.year} (tramos derogados): " "retirada"
                )
            )
        self.stdout.write(f"    · razón: {SUBSIDIO_2025_RETIRO_RAZON}")
        if not dry_run:
            derogadas.delete()
