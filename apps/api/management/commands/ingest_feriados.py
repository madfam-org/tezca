"""
Ingest the CNBV días-inhábiles-bancarios corpus into Law + LawVersion rows.

Each year the CNBV fixes the días inhábiles bancarios and publishes them in the
DOF as a «Disposiciones … que señalan los días … en que las instituciones de
crédito deberán cerrar sus puertas». Exactly like the SEP calendario acuerdo
(``ingest_sep_calendario``), each disposición lands as
``law_type="non_legislative"`` with ``category="dias_inhabiles_bancarios"`` and
``domains=["banking"]`` — so the bank dates the feriados artifact emits are
traceable to the ingested legal source they were READ FROM, not floating
constants.

The bank DATES live in ``apps.scraper.federal.feriados_legales``
(``_CNBV_ADICIONALES``, read from each disposición's Artículo 1); this command
registers the SOURCE document, so ``GET /api/v1/laws/<official_id>/`` resolves
and the artifact can cite ``corpus <official_id>``. The registry
(``FERIADOS_DOCUMENTS``) is a small enumerated set of pinned DOF ``codigo``
values, one per year — the registry IS the source of truth, as with SEP.

Usage::

    python manage.py ingest_feriados
    python manage.py ingest_feriados --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.api.models import Law, LawVersion
from apps.scraper.federal.feriados_legales import (
    FERIADOS_CATEGORY,
    FERIADOS_DOCUMENTS,
    FERIADOS_DOMAINS,
    FeriadosDocument,
)

_STATUS_MAP = {
    "vigente": Law.Status.VIGENTE,
    "abrogada": Law.Status.ABROGADA,
    "derogada": Law.Status.DEROGADA,
    "unknown": Law.Status.UNKNOWN,
}


class Command(BaseCommand):
    help = (
        "Ingest the CNBV días-inhábiles-bancarios corpus (DOF disposiciones, "
        "one per year) into Law records"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created/updated without writing to the DB",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        self.stdout.write(
            f"Using pinned feriados-bancarios registry "
            f"({len(FERIADOS_DOCUMENTS)} documents)"
        )

        created = 0
        updated = 0
        errors = 0
        for doc in FERIADOS_DOCUMENTS:
            try:
                with transaction.atomic():
                    action = self._upsert(doc, dry_run=dry_run)
                if action == "created":
                    created += 1
                elif action == "updated":
                    updated += 1
            except Exception as exc:  # noqa: BLE001 — report per-doc, keep going
                errors += 1
                self.stderr.write(self.style.ERROR(f"Failed {doc.official_id}: {exc}"))

        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Feriados bancarios ingest complete: {created} created, "
                f"{updated} updated, {errors} errors"
            )
        )

    def _upsert(self, doc: FeriadosDocument, dry_run: bool) -> str:
        """Upsert one FeriadosDocument into Law + LawVersion; return the action."""
        if dry_run:
            action = (
                "updated"
                if Law.objects.filter(official_id=doc.official_id).exists()
                else "created"
            )
            self.stdout.write(f"[DRY-RUN] {action}: {doc.official_id} ({doc.status})")
            return action

        defaults = {
            "name": doc.name[:2000],
            "short_name": doc.short_name[:200],
            "category": doc.category or FERIADOS_CATEGORY,
            "domains": list(doc.domains or FERIADOS_DOMAINS),
            "tier": "federal",
            "law_type": Law.LawType.NON_LEGISLATIVE,
            "source_url": doc.dof_url[:500],
            "status": _STATUS_MAP.get(doc.status, Law.Status.UNKNOWN),
        }
        law, created = Law.objects.update_or_create(
            official_id=doc.official_id,
            defaults=defaults,
        )

        LawVersion.objects.update_or_create(
            law=law,
            publication_date=parse_date(doc.publication_date),
            defaults={
                "dof_url": doc.dof_url[:500],
                "valid_from": parse_date(doc.valid_from) if doc.valid_from else None,
                "change_summary": doc.vigencia_note or None,
            },
        )

        return "created" if created else "updated"
