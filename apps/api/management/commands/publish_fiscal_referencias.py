"""Publica la UDI y la tasa de retención sobre intereses leídas del DOF.

    python manage.py publish_fiscal_referencias --dry-run
    LOCAL_DB=yes python manage.py publish_fiscal_referencias

Escribe las filas de :mod:`apps.api.fiscal_dof_referencias` con
``provenance='published'``. Es idempotente: una fila que ya existe con el mismo
valor se deja intacta. Una fila que ya existe con OTRO valor detiene el comando
sin escribir nada: el Banco y el Congreso no corrigen en silencio, así que una
diferencia es un error de transcripción aquí o allá, y lo decide una persona.
"""

import os
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.api.fiscal_dof_referencias import retencion_rows, udi_rows
from apps.api.fiscal_models import Provenance, RetencionIntereses, UDIValue


class Command(BaseCommand):
    help = "Publica la UDI y la tasa de retención sobre intereses verificadas contra el DOF"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Reporta lo que escribiría sin tocar la base de datos",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if not dry_run and os.environ.get("LOCAL_DB") != "yes":
            raise CommandError(
                "Refusing to write: this command mutates the database. "
                "Re-run with --dry-run, or set LOCAL_DB=yes to confirm."
            )

        self.counts = {"created": 0, "kept": 0}
        with transaction.atomic():
            for row in udi_rows():
                existing = UDIValue.objects.filter(
                    vigencia_from=row["vigencia_from"]
                ).first()
                self._publish(
                    UDIValue, existing, row, f"UDI {row['vigencia_from']}", dry_run
                )
            for row in retencion_rows():
                existing = RetencionIntereses.objects.filter(year=row["year"]).first()
                self._publish(
                    RetencionIntereses,
                    existing,
                    row,
                    f"Retención intereses {row['year']}",
                    dry_run,
                )
            if dry_run:
                transaction.set_rollback(True)

        verb = "Would publish" if dry_run else "Published"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb}: {self.counts['created']} filas nuevas. "
                f"Intactas (ya en la base con el mismo valor): {self.counts['kept']}."
            )
        )

    def _publish(self, model, existing, row, label, dry_run):
        if existing is not None:
            if Decimal(str(existing.value)) != Decimal(row["value"]):
                raise CommandError(
                    f"{label}: la base tiene {existing.value} "
                    f"[{existing.provenance}] y el DOF leído dice {row['value']}. "
                    "No se escribió nada. Revisar el aviso antes de corregir."
                )
            self.counts["kept"] += 1
            self.stdout.write(f"  = {label}: ya está, intacta")
            return
        self.counts["created"] += 1
        self.stdout.write(self.style.SUCCESS(f"  + {label}: {row['value']}"))
        if not dry_run:
            model.objects.create(**row, provenance=Provenance.PUBLISHED)
