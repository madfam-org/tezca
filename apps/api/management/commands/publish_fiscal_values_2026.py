"""Publica los valores fiscales 2026 verificados contra el DOF.

    python manage.py publish_fiscal_values_2026 --dry-run
    LOCAL_DB=yes python manage.py publish_fiscal_values_2026

A diferencia de ``seed_fiscal_values`` —que escribe cifras conocidas con
``provenance='seed-unverified'`` para que el feed sirva desde el día uno—
este comando escribe filas ``published``: cada una cita el documento del DOF
del que se transcribió, con su ``codigo`` de ``nota_detalle``.

Append-only, en serio
---------------------

El feed es append-only: una fila publicada no se edita. Pero una fila
``seed-unverified`` que cubre el MISMO periodo de vigencia que la que vamos
a publicar no puede simplemente coexistir — ``uniq_uma_year_vigencia`` lo
impide, y aunque no lo impidiera el endpoint devolvería dos filas para la
misma fecha.

Este comando distingue dos casos:

* **Vigencia distinta** — la fila anterior se cierra: su ``vigencia_to`` pasa
  a ser el día previo al inicio de la nueva. Así ocurre con la UMA 2025 (se
  cierra al 31-01-2026) y con los salarios mínimos 2025 (al 31-12-2025).
* **Misma vigencia, fila todavía sin verificar** — se promueve en su lugar.

El caso real aquí es el de la UMA 2026: el seed escribió 3,566.28 / 42,795.36
(mensual/anual derivados a mano) contra los 3,566.22 / 42,794.64 que publicó
el INEGI. Es la misma vigencia y la misma cifra diaria, con dos derivados
equivocados. Una fila seed-unverified nunca fue una aserción de cumplimiento
—el propio modelo lo dice— así que corregirla en su lugar y sellarla como
``published`` es promover la fila, que es exactamente el flujo de operador
que documenta ``docs/FISCAL_VALUES_FEED.md`` («create the row **or edit the
seed-unverified one**, … set provenance to published»). Lo que este comando
nunca hace es tocar una fila que ya está ``published``.
"""

import os

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.api.fiscal_dof_2026 import (
    ISR_2026_DOF,
    ISR_MONTHLY_2026,
    MINIMUM_WAGE_2026,
    SUBSIDIO_2026_DOF,
    SUBSIDIO_2026_PERIODS,
    UMA_2026,
    subsidio_rule_rows,
)
from apps.api.fiscal_models import FiscalTable, MinimumWage, Provenance, UMAValue


class Command(BaseCommand):
    help = "Publica los valores fiscales 2026 verificados contra el DOF"

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

        self.counts = {"created": 0, "promoted": 0, "kept": 0}

        with transaction.atomic():
            self._publish_uma(dry_run)
            self._publish_minimos(dry_run)
            self._publish_isr(dry_run)
            self._publish_subsidio(dry_run)

            if dry_run:
                transaction.set_rollback(True)

        verb = "Would publish" if dry_run else "Published"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb}: {self.counts['created']} filas nuevas, "
                f"{self.counts['promoted']} promovidas desde seed-unverified. "
                f"Intactas (ya published): {self.counts['kept']}."
            )
        )
        self.stdout.write(
            "Todas las filas escritas llevan provenance='published' con su "
            "codigo del DOF. La tarifa anual del Art. 152 NO se publicó: el "
            "documento de verificación sólo trae sus extremos."
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

    # -- datasets -----------------------------------------------------------

    def _publish_uma(self, dry_run):
        spec = UMA_2026
        existing = UMAValue.objects.filter(
            year=spec["year"], vigencia_from=spec["vigencia_from"]
        ).first()
        label = f"UMA {spec['year']} {spec['daily']}/día"
        if self._skip_if_published(existing, label):
            return
        self._record(existing, label)
        if dry_run:
            return

        fields = {
            "year": spec["year"],
            "value": spec["daily"],
            "monthly_value": spec["monthly"],
            "annual_value": spec["annual"],
            "unit": "MXN/day",
            "vigencia_from": spec["vigencia_from"],
            "vigencia_to": spec["vigencia_to"],
            "dof_date": spec["dof_date"],
            "dof_codigo": spec["dof_codigo"],
            "source_url": spec["source_url"],
            "source_citation": spec["source_citation"],
            "provenance": Provenance.PUBLISHED,
            "notes": spec["notes"],
        }
        if existing is None:
            UMAValue.objects.create(**fields)
        else:
            for key, value in fields.items():
                setattr(existing, key, value)
            existing.save()

        # La UMA 2025 debe seguir resolviendo enero de 2026: su vigencia
        # termina el 31-01-2026, el día antes de que entre la de 2026.
        previous = UMAValue.objects.filter(year=2025).order_by("-vigencia_from").first()
        if previous is not None and previous.vigencia_to is None:
            previous.vigencia_to = "2026-01-31"
            previous.save(update_fields=["vigencia_to"])
            self.stdout.write("    · UMA 2025 cerrada al 2026-01-31")

    def _publish_minimos(self, dry_run):
        spec = MINIMUM_WAGE_2026
        for zone, amount, incremento in spec["zones"]:
            existing = MinimumWage.objects.filter(
                year=spec["year"], zone=zone, vigencia_from=spec["vigencia_from"]
            ).first()
            label = f"Salario mínimo {zone} {spec['year']}: {amount}/día"
            if self._skip_if_published(existing, label):
                continue
            self._record(existing, label)
            if dry_run:
                continue

            fields = {
                "year": spec["year"],
                "zone": zone,
                "value": amount,
                "unit": "MXN/day",
                "vigencia_from": spec["vigencia_from"],
                "vigencia_to": spec["vigencia_to"],
                "dof_date": spec["dof_date"],
                "dof_codigo": spec["dof_codigo"],
                "source_url": spec["source_url"],
                "source_citation": spec["source_citation"],
                "provenance": Provenance.PUBLISHED,
                "notes": (
                    f"Incremento publicado: {incremento}. "
                    "La resolución incluye además una tabla de 61 salarios "
                    "mínimos PROFESIONALES que Tezca no publica todavía: sus "
                    "valores no están en el documento de verificación y no se "
                    "inventan."
                ),
            }
            if existing is None:
                MinimumWage.objects.create(**fields)
            else:
                for key, value in fields.items():
                    setattr(existing, key, value)
                existing.save()

            # El salario mínimo del año anterior deja de estar vigente el
            # 31-12-2025; el seed dejó abierta la fila más reciente.
            previous = (
                MinimumWage.objects.filter(year=2025, zone=zone)
                .order_by("-vigencia_from")
                .first()
            )
            if previous is not None and previous.vigencia_to is None:
                previous.vigencia_to = "2025-12-31"
                previous.save(update_fields=["vigencia_to"])
                self.stdout.write(f"    · Salario mínimo {zone} 2025 cerrado")

    def _publish_isr(self, dry_run):
        existing = FiscalTable.objects.filter(
            kind=FiscalTable.Kind.ISR_MONTHLY, year=2026, vigencia_from="2026-01-01"
        ).first()
        label = f"ISR mensual 2026 ({len(ISR_MONTHLY_2026)} tramos)"
        if self._skip_if_published(existing, label):
            return
        self._record(existing, label)
        if dry_run:
            return

        fields = {
            "kind": FiscalTable.Kind.ISR_MONTHLY,
            "year": 2026,
            "period": "monthly",
            "rows": ISR_MONTHLY_2026,
            "legal_basis": "LISR Art. 96; Anexo 8 RMF 2026, apartado B fr. V",
            "vigencia_from": "2026-01-01",
            "vigencia_to": "2026-12-31",
            "dof_date": ISR_2026_DOF["dof_date"],
            "dof_codigo": ISR_2026_DOF["dof_codigo"],
            "source_url": ISR_2026_DOF["source_url"],
            "source_citation": ISR_2026_DOF["source_citation"],
            "provenance": Provenance.PUBLISHED,
            "notes": ISR_2026_DOF["notes"],
        }
        if existing is None:
            FiscalTable.objects.create(**fields)
        else:
            for key, value in fields.items():
                setattr(existing, key, value)
            existing.save()

    def _publish_subsidio(self, dry_run):
        for v_from, v_to, uma_monthly, amount, note in SUBSIDIO_2026_PERIODS:
            existing = FiscalTable.objects.filter(
                kind=FiscalTable.Kind.SUBSIDIO_RULE, year=2026, vigencia_from=v_from
            ).first()
            label = f"Subsidio al empleo 2026 desde {v_from}: {amount}/mes"
            if self._skip_if_published(existing, label):
                continue
            self._record(existing, label)
            if dry_run:
                continue

            fields = {
                "kind": FiscalTable.Kind.SUBSIDIO_RULE,
                "year": 2026,
                "period": "monthly",
                "rows": subsidio_rule_rows(uma_monthly, amount),
                "legal_basis": "Decreto del subsidio para el empleo (DOF 01-05-2024)",
                "vigencia_from": v_from,
                "vigencia_to": v_to,
                "dof_date": SUBSIDIO_2026_DOF["dof_date"],
                "dof_codigo": SUBSIDIO_2026_DOF["dof_codigo"],
                "source_url": SUBSIDIO_2026_DOF["source_url"],
                "source_citation": SUBSIDIO_2026_DOF["source_citation"],
                "provenance": Provenance.PUBLISHED,
                "notes": f"{SUBSIDIO_2026_DOF['notes']} {note}",
            }
            if existing is None:
                FiscalTable.objects.create(**fields)
            else:
                for key, value in fields.items():
                    setattr(existing, key, value)
                existing.save()
