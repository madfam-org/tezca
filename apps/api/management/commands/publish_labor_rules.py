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

**Validación previa (T-1e).** Antes de abrir escritura alguna, el comando
mide cada fila contra los ``max_length`` del modelo. Sin ese paso, el
``--dry-run`` escribía dentro de una transacción y la deshacía al final: el
``INSERT`` llegaba a Postgres igual, y una fila demasiado larga abortaba el
modo «no toques nada» con ``DataError: value too long for type character
varying(32)`` y un traceback. Ahora en seco no se abre ninguna transacción de
escritura, y una fila inválida sale con ``CommandError`` diciendo fila, campo
y cifras.
"""

import json
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.api.fiscal_models import Provenance
from apps.api.labor_coherence import desbordes_de_longitud, describe_desbordes
from apps.api.labor_models import LaborRule, SatCatalogEntry
from apps.api.labor_seed_data import REGLAS

# Anclado a la raíz del repo/imagen, NO al cwd — mismo motivo que en
# `publish_law_articles`: el fail-closed de la lectura del catálogo es
# correcto, pero con una ruta relativa se disparaba también por estar
# parado en el directorio equivocado, no sólo por un catálogo ausente.
DEFAULT_CATALOGOS = Path(settings.BASE_DIR) / "data" / "labor" / "sat_catalogos.json"

SAT = "Servicio de Administración Tributaria"

# El catálogo del SAT guarda el nombre del catálogo en la columna `article` y
# el archivo de origen en `official_id`; la validación necesita ese mapeo para
# medir el valor correcto contra el `max_length` correcto.
ALIAS_CATALOGO = {"article": "catalog", "official_id": "catalogo_origen"}


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

        # Antes de abrir escritura alguna. Una fila que no cabe en su columna
        # tiene que salir por aquí, con su fila y su campo, y no como un
        # DataError de Postgres a mitad de la transacción.
        self._validar_longitudes(catalogos)

        self.counts = {"created": 0, "promoted": 0, "kept": 0}

        if dry_run:
            # En seco NO se abre transacción de escritura: sólo se cuenta lo
            # que se haría, con las mismas consultas de lectura. El
            # `set_rollback(True)` de antes deshacía los INSERT pero ya los
            # había mandado a la base, así que el modo «no toques nada» podía
            # reventar por una fila inválida.
            for regla in REGLAS:
                self._count_rule(regla)
            for fila in catalogos:
                self._count_catalog_entry(fila)
        else:
            with transaction.atomic():
                for regla in REGLAS:
                    self._publish_rule(regla)
                for fila in catalogos:
                    self._publish_catalog_entry(fila)

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

    def _validar_longitudes(self, catalogos):
        """Mide cada fila contra los ``max_length`` del modelo, sin tocar la base.

        La aritmética es la misma en SQLite y en Postgres, así que lo que aquí
        pasa cabe también en la columna del pod. Es el paso que faltaba: la
        suite corre sobre SQLite, que **ignora** el ancho de un ``VARCHAR(n)``,
        de modo que ninguna prueba que sólo escriba y lea podía ver el
        desborde. Ver ``docs/labor/README.md``, «Validación previa y límites de
        campo».
        """
        problemas = desbordes_de_longitud(REGLAS, LaborRule)
        problemas += desbordes_de_longitud(
            catalogos, SatCatalogEntry, alias=ALIAS_CATALOGO
        )
        if problemas:
            raise CommandError(
                "No se escribió nada: hay valores que no caben en su columna. "
                + describe_desbordes(problemas)
            )

    def _clave_regla(self, regla):
        return {
            "kind": regla["kind"],
            "payer_legal_form": regla.get(
                "payer_legal_form", LaborRule.PayerLegalForm.ANY
            ),
            "provider_regime": regla.get("provider_regime", ""),
            "service": regla.get("service", ""),
            "effective_from": parse_date(regla["effective_from"]),
        }

    def _clave_catalogo(self, fila):
        return {
            "catalog": fila["catalog"],
            "code": fila["code"],
            "effective_from": parse_date(fila["effective_from"]),
        }

    def _count_rule(self, regla):
        """Lo que el dry-run haría con esta regla. Sólo lee."""
        self._contar(LaborRule.objects.filter(**self._clave_regla(regla)).first())

    def _count_catalog_entry(self, fila):
        """Lo que el dry-run haría con esta clave. Sólo lee."""
        self._contar(
            SatCatalogEntry.objects.filter(**self._clave_catalogo(fila)).first()
        )

    def _contar(self, existing):
        if existing is not None and existing.provenance == Provenance.PUBLISHED:
            self.counts["kept"] += 1
        else:
            self._bump(existing)

    def _bump(self, existing):
        if existing is None:
            self.counts["created"] += 1
        else:
            self.counts["promoted"] += 1

    def _publish_rule(self, regla):
        clave = self._clave_regla(regla)
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
        clave = self._clave_catalogo(fila)
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
