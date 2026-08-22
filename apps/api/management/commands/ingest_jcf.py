"""
Ingest the JCF (Jóvenes Construyendo el Futuro) normative corpus into
Law + LawVersion rows.

JCF's operative norm is not a ``ley`` but a set of **Reglas de Operación**
re-issued annually by the STPS and published in the DOF. Those are
administrative instruments, so — exactly like the RMF
(``ingest_rmf``) and NOM (``ingest_noms``) feeds — each document lands as
``law_type="non_legislative"`` with ``category="reglas_de_operacion"`` and
``domains=["labor"]`` so labor-domain consumers (symbiosis-hcm's
``legal_basis`` enrichment, the ``domain_filter: ["labor"]`` webhook
subscribers) see them.

Unlike its sister commands this one reads the corpus from
``apps.scraper.federal.jcf_scraper.JCF_DOCUMENTS`` directly when no
catalog file is present. That is deliberate: JCF is a small enumerated set
of pinned DOF ``codigo`` values, not a discovered index, so the registry
*is* the source of truth and requiring a scraper run before ingestion
would add a failure mode for no benefit.

Text ingestion is separate and optional. Running the fetcher with
``--download`` materializes parsed AKN into ``data/jcf/``; this command
links whatever text file exists onto the LawVersion (``xml_file_path``) so
``index_laws`` can pick it up. Without it, metadata still registers and
``GET /api/v1/laws/{official_id}/`` resolves — the article text is simply
not yet searchable, and the command says so rather than pretending.

Usage::

    python manage.py ingest_jcf
    python manage.py ingest_jcf --dry-run
    python manage.py ingest_jcf --catalog data/jcf/catalog.json
    python manage.py ingest_jcf --text-dir data/jcf
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.api.models import Law, LawVersion
from apps.scraper.federal.jcf_scraper import (
    JCF_CATEGORY,
    JCF_DOCUMENTS,
    JCF_DOMAINS,
    JcfDocument,
)

DEFAULT_TEXT_DIR = Path("data") / "jcf"

_STATUS_MAP = {
    "vigente": Law.Status.VIGENTE,
    "abrogada": Law.Status.ABROGADA,
    "derogada": Law.Status.DEROGADA,
    "unknown": Law.Status.UNKNOWN,
}


class Command(BaseCommand):
    help = (
        "Ingest the Jóvenes Construyendo el Futuro normative corpus "
        "(DOF Reglas de Operación + modifications) into Law records"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--catalog",
            type=str,
            default=None,
            help=(
                "Path to catalog.json produced by JcfFetcher. When omitted, "
                "the pinned JCF_DOCUMENTS registry is used directly."
            ),
        )
        parser.add_argument(
            "--text-dir",
            type=str,
            default=str(DEFAULT_TEXT_DIR),
            help=(
                f"Directory holding materialized document text "
                f"(default: {DEFAULT_TEXT_DIR}). Files are linked onto "
                f"LawVersion.xml_file_path when present."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created/updated without writing to the DB",
        )

    def handle(self, *args, **options):
        documents = self._load_documents(options.get("catalog"))
        if documents is None:
            return

        text_dir = Path(options["text_dir"])
        dry_run = options["dry_run"]

        created = 0
        updated = 0
        errors = 0
        with_text = 0

        for doc in documents:
            try:
                with transaction.atomic():
                    result, linked = self._upsert(doc, text_dir, dry_run=dry_run)
                if result == "created":
                    created += 1
                elif result == "updated":
                    updated += 1
                if linked:
                    with_text += 1
            except Exception as exc:
                errors += 1
                self.stderr.write(self.style.ERROR(f"Failed {doc.official_id}: {exc}"))

        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}JCF ingest complete: {created} created, {updated} updated, "
                f"{errors} errors"
            )
        )

        missing_text = len(documents) - with_text
        if missing_text:
            self.stdout.write(
                self.style.WARNING(
                    f"{prefix}{missing_text}/{len(documents)} documents have no "
                    f"text in {text_dir} — metadata resolves via "
                    f"/api/v1/laws/<official_id>/ but article text is NOT "
                    f"searchable yet. Run: python -m "
                    f"apps.scraper.federal.jcf_scraper --download "
                    f"--output-dir {text_dir}  (then: manage.py index_laws)"
                )
            )
        else:
            self.stdout.write(
                f"{prefix}All {with_text} documents have text linked. "
                f"Run `manage.py index_laws` to make articles searchable."
            )

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_documents(self, catalog_arg):
        """Return the documents to ingest, or None when the run should abort."""
        if not catalog_arg:
            self.stdout.write(
                f"Using pinned JCF registry ({len(JCF_DOCUMENTS)} documents)"
            )
            return list(JCF_DOCUMENTS)

        catalog_path = Path(catalog_arg)
        if not catalog_path.exists():
            self.stderr.write(self.style.ERROR(f"Catalog not found: {catalog_path}"))
            return None

        with catalog_path.open(encoding="utf-8") as fh:
            raw = json.load(fh)

        if not raw:
            self.stdout.write(
                self.style.WARNING("Catalog is empty — nothing to ingest")
            )
            return None

        documents = [_document_from_catalog_entry(entry) for entry in raw]
        self.stdout.write(f"Loaded {len(documents)} JCF documents from {catalog_path}")
        return documents

    # ------------------------------------------------------------------
    # Upsert
    # ------------------------------------------------------------------

    def _upsert(self, doc: JcfDocument, text_dir: Path, dry_run: bool):
        """Upsert one JcfDocument into Law + LawVersion.

        Returns ``(action, linked_text)`` where action is "created"/"updated"
        and linked_text says whether a materialized text file was found.
        """
        text_path = _find_text_file(doc, text_dir)

        if dry_run:
            action = (
                "updated"
                if Law.objects.filter(official_id=doc.official_id).exists()
                else "created"
            )
            self.stdout.write(
                f"[DRY-RUN] {action}: {doc.official_id} "
                f"({doc.status}, text={'yes' if text_path else 'no'})"
            )
            return action, bool(text_path)

        defaults = {
            "name": doc.name[:2000],
            "short_name": doc.short_name[:200],
            "category": doc.category or JCF_CATEGORY,
            "domains": list(doc.domains or JCF_DOMAINS),
            "tier": "federal",
            "law_type": Law.LawType.NON_LEGISLATIVE,
            "source_url": doc.dof_url[:500],
            "status": _STATUS_MAP.get(doc.status, Law.Status.UNKNOWN),
        }

        law, created = Law.objects.update_or_create(
            official_id=doc.official_id,
            defaults=defaults,
        )
        action = "created" if created else "updated"

        version_defaults = {
            "dof_url": doc.dof_url[:500],
            "valid_from": parse_date(doc.valid_from) if doc.valid_from else None,
            # vigencia_note carries *why* a document is (or isn't)
            # controlling — the residual 2019 Lineamientos especially.
            # change_summary is the existing LawVersion field for exactly
            # this, so no new column is needed.
            "change_summary": doc.vigencia_note or None,
        }
        if text_path:
            version_defaults["xml_file_path"] = str(text_path)

        LawVersion.objects.update_or_create(
            law=law,
            publication_date=parse_date(doc.publication_date),
            defaults=version_defaults,
        )

        return action, bool(text_path)


def _find_text_file(doc: JcfDocument, text_dir: Path):
    """Return the materialized text file for a document, if one exists.

    Prefers the parsed AKN (per-Regla articles); falls back to the raw-text
    dump the fetcher writes for prose documents like the simplification
    Acuerdo, which index_laws indexes as a single ``full_text`` article.
    """
    for candidate in (
        text_dir / doc.text_filename,
        text_dir / f"{doc.official_id}.txt",
    ):
        if candidate.exists():
            return candidate
    return None


def _document_from_catalog_entry(entry: dict) -> JcfDocument:
    """Rebuild a JcfDocument from a catalog.json entry.

    catalog.json carries derived read-only fields (dof_url, sidof_url,
    text_filename) that are properties on the dataclass, so they are
    dropped rather than passed to the constructor.
    """
    fields = {
        key: value
        for key, value in entry.items()
        if key not in ("dof_url", "sidof_url", "text_filename")
    }
    return JcfDocument(**fields)
