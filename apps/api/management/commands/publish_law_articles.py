"""Publica los textos de artículos con vigencia leídos de fuente primaria.

    python manage.py publish_law_articles --dry-run
    LOCAL_DB=yes python manage.py publish_law_articles

El insumo es ``data/labor/articulos_vigentes.json``, generado transcribiendo
el **texto vigente** que publica la Cámara de Diputados (el .doc, no el PDF:
el PDF intercala espacios dentro de las palabras y repite el encabezado de
página). Cada fila trae la edición de la que se transcribió, la URL de la que
se bajó y las fechas DOF de las reformas que la propia Cámara imprime bajo el
artículo.

``effective_from`` es la fecha de la reforma más reciente que tocó al
artículo, no la de la última reforma de la ley entera: el artículo 20 de la
LFT conserva su texto de 1970 aunque la ley se haya reformado en 2026, y
fecharlo en 2026 sería mentir sobre desde cuándo dice lo que dice. Los
artículos sin nota de reforma se fechan en la publicación original de la ley.

Append-only, igual que el feed fiscal: una fila ``published`` no se toca. Una
fila ``seed-unverified`` de la misma vigencia se promueve en su lugar.
"""

import json
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.api.fiscal_models import Provenance
from apps.api.labor_models import LawArticle

# Anclado a la raíz del repo/imagen, NO al cwd. Con `Path("data")/...` el
# comando sólo funcionaba si se le invocaba parado exactamente en la raíz;
# desde cualquier otro directorio abortaba con «No existe el seed», que es
# indistinguible del seed genuinamente ausente. En el pod el cwd es /app y
# BASE_DIR es /app, así que el valor por omisión es el mismo: lo que cambia
# es que ahora lo sigue siendo desde cualquier cwd. Ver
# `docs/labor/README.md`, «Qué ocurre si el seed no está en la imagen».
DEFAULT_SEED = Path(settings.BASE_DIR) / "data" / "labor" / "articulos_vigentes.json"

# Fuente primaria de todos los textos de este seed.
SOURCE = "Cámara de Diputados, LeyesBiblio (texto vigente)"


class Command(BaseCommand):
    help = "Publica los textos de artículos con vigencia (feed laboral, T-1)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Reporta lo que escribiría sin tocar la base de datos",
        )
        parser.add_argument(
            "--seed",
            default=str(DEFAULT_SEED),
            help=f"Ruta del JSON de artículos (por omisión {DEFAULT_SEED})",
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

        seed_path = Path(options["seed"])
        if not seed_path.exists():
            self.stderr.write(self.style.ERROR(f"No existe el seed: {seed_path}"))
            return

        filas = json.loads(seed_path.read_text(encoding="utf-8"))
        counts = {"created": 0, "promoted": 0, "kept": 0}

        with transaction.atomic():
            for fila in filas:
                self._publish(fila, counts, dry_run)
            if dry_run:
                transaction.set_rollback(True)

        verbo = "Publicaría" if dry_run else "Publicó"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verbo}: {counts['created']} artículos nuevos, "
                f"{counts['promoted']} promovidos desde seed-unverified. "
                f"Intactos (ya published): {counts['kept']}."
            )
        )

    def _publish(self, fila, counts, dry_run):
        official_id = fila["official_id"]
        article = fila["article"]
        effective_from = parse_date(fila["effective_from"])
        etiqueta = f"{official_id} art. {article} ({fila['effective_from']})"

        existing = LawArticle.objects.filter(
            official_id=official_id, article=article, effective_from=effective_from
        ).first()
        if existing is not None and existing.provenance == Provenance.PUBLISHED:
            counts["kept"] += 1
            return

        # La última reforma del artículo es también la publicación del DOF que
        # fija su texto; se guarda como dof_date para que el consumidor pueda
        # citarla. Los artículos que nunca se reformaron no tienen una.
        reformas = fila.get("reformas_dof") or []
        dof_date = parse_date(reformas[-1]) if reformas else None

        campos = {
            "text": fila["text"],
            "edition": fila.get("edition", ""),
            "derogado": fila.get("derogado", False),
            "reformas_dof": reformas,
            "effective_to": None,
            "source": SOURCE,
            "source_url": fila.get("source_url", ""),
            "dof_date": dof_date,
            "provenance": Provenance.PUBLISHED,
            "notes": (
                "Fechado por la nota de reforma que imprime la Cámara bajo el "
                "artículo."
                if fila.get("fechado_por") == "reforma"
                else "Sin nota de reforma: conserva el texto de la publicación "
                "original de la ley, y por eso se fecha ahí."
            ),
        }

        if dry_run:
            counts["created" if existing is None else "promoted"] += 1
            return

        if existing is None:
            LawArticle.objects.create(
                official_id=official_id,
                article=article,
                effective_from=effective_from,
                **campos,
            )
            counts["created"] += 1
        else:
            for campo, valor in campos.items():
                setattr(existing, campo, valor)
            existing.save()
            counts["promoted"] += 1
