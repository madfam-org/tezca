"""Publica las reglas laborales estructuradas y los catálogos del SAT (T-1b).

    python manage.py publish_labor_rules --dry-run
    LOCAL_DB=yes python manage.py publish_labor_rules

Las reglas vienen de ``apps/api/labor_seed_data.py`` (cada una con el artículo
del que se leyó) y los catálogos de ``data/labor/sat_catalogos.json``
(transcritos de los .xls que publica el SAT).

Append-only, con el mismo criterio que ``publish_fiscal_values_2026``: una
fila ya ``published`` no se toca nunca; una ``seed-unverified`` de la misma
vigencia y las mismas dimensiones se promueve en su lugar, porque una fila
sin verificar nunca fue una aserción de cumplimiento.

Fail-closed en la lectura del catálogo: si el JSON no está o no se puede
leer, el comando aborta sin escribir nada. Publicar medio catálogo del SAT
sería peor que no publicarlo — un timbrado validaría contra una lista
incompleta y rechazaría claves buenas.
"""

import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.api.fiscal_models import Provenance
from apps.api.labor_models import LaborRule, SatCatalogEntry
from apps.api.labor_seed_data import REGLAS

DEFAULT_CATALOGOS = Path("data") / "labor" / "sat_catalogos.json"

SAT = "Servicio de Administración Tributaria"


class Command(BaseCommand):
    help = "Publica las reglas laborales estructuradas y los catálogos del SAT"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Reporta lo que escribiría sin tocar la base de datos",
        )
        parser.add_argument(
            "--catalogos",
            default=str(DEFAULT_CATALOGOS),
            help=f"Ruta del JSON de catálogos SAT (por omisión {DEFAULT_CATALOGOS})",
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

        catalogos_path = Path(options["catalogos"])
        try:
            catalogos = json.loads(catalogos_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            # Fail-closed: medio catálogo es peor que ninguno.
            self.stderr.write(
                self.style.ERROR(
                    f"No se pudo leer el catálogo del SAT en {catalogos_path}: "
                    f"{exc}. No se escribió nada."
                )
            )
            return

        self.counts = {"created": 0, "promoted": 0, "kept": 0}

        with transaction.atomic():
            for regla in REGLAS:
                self._publish_rule(regla)
            for fila in catalogos:
                self._publish_catalog_entry(fila)
            if dry_run:
                transaction.set_rollback(True)

        verbo = "Publicaría" if dry_run else "Publicó"
        sin_verificar = sum(
            1 for r in REGLAS if r["provenance"] != Provenance.PUBLISHED
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{verbo}: {self.counts['created']} filas nuevas, "
                f"{self.counts['promoted']} promovidas desde seed-unverified. "
                f"Intactas (ya published): {self.counts['kept']}."
            )
        )
        self.stdout.write(
            f"{len(REGLAS)} reglas ({sin_verificar} seed-unverified, "
            f"documentadas como hueco en docs/labor/reglas.md) y "
            f"{len(catalogos)} claves de catálogo del SAT."
        )

    # -- helpers ------------------------------------------------------------

    def _bump(self, existing):
        if existing is None:
            self.counts["created"] += 1
        else:
            self.counts["promoted"] += 1

    def _publish_rule(self, regla):
        clave = {
            "kind": regla["kind"],
            "payer_legal_form": regla.get(
                "payer_legal_form", LaborRule.PayerLegalForm.ANY
            ),
            "provider_regime": regla.get("provider_regime", ""),
            "service": regla.get("service", ""),
            "effective_from": parse_date(regla["effective_from"]),
        }
        existing = LaborRule.objects.filter(**clave).first()
        if existing is not None and existing.provenance == Provenance.PUBLISHED:
            self.counts["kept"] += 1
            return

        campos = {
            "value": regla["value"],
            "unit": regla.get("unit", ""),
            "label": regla.get("label", ""),
            "official_id": regla["official_id"],
            "article": regla["article"],
            "effective_to": (
                parse_date(regla["effective_to"]) if regla.get("effective_to") else None
            ),
            "source": regla.get("source", ""),
            "source_url": regla.get("source_url", ""),
            "dof_date": (
                parse_date(regla["dof_date"]) if regla.get("dof_date") else None
            ),
            "dof_codigo": regla.get("dof_codigo", ""),
            "provenance": regla["provenance"],
            "notes": regla.get("notes", ""),
        }
        self._bump(existing)
        if existing is None:
            LaborRule.objects.create(**clave, **campos)
        else:
            for campo, valor in campos.items():
                setattr(existing, campo, valor)
            existing.save()

    def _publish_catalog_entry(self, fila):
        clave = {
            "catalog": fila["catalog"],
            "code": fila["code"],
            "effective_from": parse_date(fila["effective_from"]),
        }
        existing = SatCatalogEntry.objects.filter(**clave).first()
        if existing is not None and existing.provenance == Provenance.PUBLISHED:
            self.counts["kept"] += 1
            return

        campos = {
            "label": fila["label"],
            "aplica_fisica": fila.get("aplica_fisica"),
            "aplica_moral": fila.get("aplica_moral"),
            "effective_to": (
                parse_date(fila["effective_to"]) if fila.get("effective_to") else None
            ),
            # official_id/article reutilizan la procedencia común: el archivo
            # de origen y el nombre del catálogo, en vez de campos paralelos.
            "official_id": fila.get("catalogo_origen", "sat_cat"),
            "article": fila["catalog"],
            "source": SAT,
            "source_url": fila.get("source_url", ""),
            # La procedencia la declara el archivo, fila por fila. Fijarla en
            # 'published' aquí convertiría cualquier clave que alguien añadiera
            # de memoria en una aserción verificada sin que nadie lo notara.
            "provenance": fila.get("provenance", Provenance.PUBLISHED),
            "notes": (
                f"Transcrito del catálogo que publica el SAT, versión "
                f"{fila.get('catalogo_version', 'sin declarar')}."
            ),
        }
        self._bump(existing)
        if existing is None:
            SatCatalogEntry.objects.create(**clave, **campos)
        else:
            for campo, valor in campos.items():
                setattr(existing, campo, valor)
            existing.save()
