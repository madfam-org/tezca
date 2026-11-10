"""
Parse the Resolución Miscelánea Fiscal rule by rule and register each dated
text as a LawVersion of ``rmf_2026``.

``ingest_rmf`` (catalog) only registers that SAT published an RMF document;
its LawVersion has no text, so ``/laws/rmf_2026/articles/`` is empty. This
command fills that gap from **pinned official documents only**:

1. reads the manifest (``apps/parsers/rmf/manifests/rmf_2026.json``): one
   entry per text — the DOF publication of 28-dic-2025 and each SAT
   compiled edition after a resolución de modificaciones — with its URL,
   DOF date, validity and SHA-256;
2. refuses any PDF whose SHA-256 differs from the manifest (SAT re-uploads
   files in place; an unreviewed document never reaches the corpus);
3. segments it by rule (``apps.parsers.rmf``), validates the result, and
   writes Akoma Ntoso to ``--output-dir`` (one file per version) and, when
   ``STORAGE_BACKEND=r2``, uploads it under the key ``read_data_content``
   reads (production pods keep nothing under ``data/`` across restarts);
4. upserts the Law and one LawVersion per manifest entry, keyed by
   publication date, with ``valid_from``/``valid_to`` and the AKN path.

Afterwards ``index_laws --law-id rmf_2026`` indexes the newest version; each
rule becomes article ``3.13.7``, transitorios ``T-1`` / ``T-R2-1``.

Anexos are out of scope (separate DOF publications).

This is a legal-data ingestion job: anything beyond a ``--dry-run`` over
local files requires ``LOCAL_LEGAL_DATA_OPS=yes`` (see AGENTS.md).

Usage::

    python manage.py ingest_rmf_rules --dry-run --source-dir ~/rmf-pdfs
    LOCAL_LEGAL_DATA_OPS=yes python manage.py ingest_rmf_rules --download
    LOCAL_LEGAL_DATA_OPS=yes python manage.py ingest_rmf_rules --only compilada-3a-rm
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.api.models import Law, LawVersion
from apps.parsers.rmf.akn import build_akn
from apps.parsers.rmf.lines import extract_lines
from apps.parsers.rmf.segmenter import segment, validate
from apps.scraper.federal.rmf_scraper import RMF_CATEGORY, RMF_DOMAINS

DEFAULT_MANIFEST = Path("apps") / "parsers" / "rmf" / "manifests" / "rmf_2026.json"
DEFAULT_SOURCE_DIR = Path("data") / "rmf" / "sources"
DEFAULT_OUTPUT_DIR = Path("data") / "rmf"
GUARD_VARIABLE = "LOCAL_LEGAL_DATA_OPS"
_DOWNLOAD_TIMEOUT = 120
_MAX_WARNINGS_SHOWN = 15


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _lower_priority() -> None:
    try:
        os.nice(19 - os.nice(0))
    except (AttributeError, OSError):  # not POSIX, or already lowest
        pass


def load_manifest(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        manifest = json.load(fh)
    for key in ("official_id", "name", "work_date", "versions"):
        if key not in manifest:
            raise CommandError(f"Manifest {path} lacks '{key}'")
    for version in manifest["versions"]:
        for key in (
            "key",
            "publication_date",
            "valid_from",
            "document_url",
            "filename",
            "sha256",
        ):
            if not version.get(key):
                raise CommandError(
                    f"Manifest version {version.get('key', '?')} lacks '{key}'"
                )
    return manifest


class Command(BaseCommand):
    help = (
        "Parse the RMF rule by rule from pinned official PDFs and register "
        "dated LawVersions (AKN) for index_laws"
    )

    def add_arguments(self, parser):
        parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
        parser.add_argument(
            "--source-dir",
            default=str(DEFAULT_SOURCE_DIR),
            help=f"Where the manifest's PDFs live (default {DEFAULT_SOURCE_DIR})",
        )
        parser.add_argument(
            "--output-dir",
            default=str(DEFAULT_OUTPUT_DIR),
            help=f"Where AKN files are written (default {DEFAULT_OUTPUT_DIR})",
        )
        parser.add_argument(
            "--download",
            action="store_true",
            help="Fetch missing PDFs from the manifest URLs (hash-verified)",
        )
        parser.add_argument(
            "--only",
            action="append",
            default=[],
            metavar="KEY",
            help="Process only this manifest version key (repeatable)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate; write no files and no DB rows",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if (not dry_run or options["download"]) and os.environ.get(
            GUARD_VARIABLE
        ) != "yes":
            raise CommandError(
                f"Refusing to run RMF ingestion: set {GUARD_VARIABLE}=yes only "
                f"for an explicit operator-requested run (or use --dry-run "
                f"over local files)."
            )

        # Parsing an 860-page PDF is minutes of CPU. In production this runs
        # inside the shared worker container next to Celery, whose liveness
        # probe (a 5 s ping) failed and restarted the container when the parse
        # ran at normal priority (2026-11-10). Yield the CPU to everything else.
        _lower_priority()

        manifest = load_manifest(Path(options["manifest"]))
        versions = manifest["versions"]
        if options["only"]:
            wanted = set(options["only"])
            unknown = wanted - {v["key"] for v in versions}
            if unknown:
                raise CommandError(
                    f"Unknown version key(s): {', '.join(sorted(unknown))}"
                )
            versions = [v for v in versions if v["key"] in wanted]

        source_dir = Path(options["source_dir"]).expanduser()
        output_dir = Path(options["output_dir"])
        prefix = "[DRY-RUN] " if dry_run else ""

        parsed = []
        failures = 0
        for version in versions:
            try:
                pdf = self._source_pdf(version, source_dir, options["download"])
                xml, stats = self._parse(manifest, version, pdf)
            except CommandError as exc:
                failures += 1
                self.stderr.write(self.style.ERROR(f"{version['key']}: {exc}"))
                continue
            parsed.append((version, xml, stats))
            self.stdout.write(
                f"{prefix}{version['key']}: {stats['rules']} reglas "
                f"({stats['derogadas']} derogadas), {stats['transitorios']} "
                f"transitorios, {stats['warnings']} warnings"
            )

        if failures:
            raise CommandError(
                f"{failures} version(s) failed; nothing was written for them. "
                f"Fix the source or the parser before ingesting."
            )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"{prefix}{len(parsed)} version(s) parse cleanly")
            )
            return

        # Files first (and to R2 when that is the backend), rows second: a
        # LawVersion must never point at an AKN file that is not stored.
        output_dir.mkdir(parents=True, exist_ok=True)
        written = []
        for version, xml, _stats in parsed:
            path = output_dir / f"{manifest['official_id']}-{version['key']}.xml"
            path.write_text(xml, encoding="utf-8")
            key = self._sync_to_storage(path)
            written.append((version, path))
            self.stdout.write(
                f"Wrote {version['key']} → {path}" + (f" (R2 key {key})" if key else "")
            )

        with transaction.atomic():
            law = self._upsert_law(manifest)
            for version, path in written:
                self._upsert_version(law, version, path)
                self.stdout.write(f"Linked {version['key']} → {path}")

        self._report_stray_versions(manifest)
        for pending in manifest.get("pending", []):
            self.stdout.write(
                self.style.WARNING(
                    f"Not reflected in any version: {pending['instrument']} "
                    f"(DOF {pending['dof_date']}). {pending.get('reason', '')}"
                )
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"RMF rules ingested for {manifest['official_id']}. Make them "
                f"searchable with: python manage.py index_laws --law-id "
                f"{manifest['official_id']}"
            )
        )

    # ------------------------------------------------------------------

    def _source_pdf(self, version: dict, source_dir: Path, download: bool) -> Path:
        path = source_dir / version["filename"]
        if not path.exists():
            if not download:
                raise CommandError(
                    f"{path} not found (re-run with --download to fetch "
                    f"{version['document_url']})"
                )
            self._download(version["document_url"], path)
        actual = sha256_of(path)
        if actual != version["sha256"]:
            raise CommandError(
                f"SHA-256 mismatch for {path}: expected {version['sha256']}, "
                f"got {actual}. The official document changed; review it and "
                f"update the manifest before ingesting."
            )
        return path

    @staticmethod
    def storage_key(path: Path) -> str:
        """R2 key for a data path, normalised exactly as ``read_data_content``
        does on its R2 fallback (keys mirror ``data/``)."""
        key = str(path).lstrip("/")
        return key[5:] if key.startswith("data/") else key

    def _sync_to_storage(self, path: Path):
        """Upload the AKN to R2 when that is the storage backend.

        Production pods have no volume under ``data/``: a file written by
        ``enclii exec`` lives until the pod restarts, after which
        ``read_data_content`` falls back to R2. Locally the file already sits
        where the reader looks, so nothing is copied.
        """
        if os.environ.get("STORAGE_BACKEND") != "r2":
            return None
        if path.is_absolute():
            raise CommandError(
                f"--output-dir must be relative under data/ when STORAGE_BACKEND=r2 "
                f"(got {path}); the R2 key is derived from it."
            )
        from apps.api.storage import get_storage_backend

        key = self.storage_key(path)
        get_storage_backend().put_file(key, path)
        return key

    def _download(self, url: str, path: Path) -> None:
        import requests

        from apps.scraper.http import DEFAULT_USER_AGENT

        path.parent.mkdir(parents=True, exist_ok=True)
        self.stdout.write(f"Downloading {url}")
        response = requests.get(
            url, headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=_DOWNLOAD_TIMEOUT
        )
        if response.status_code != 200 or not response.content:
            raise CommandError(f"Download failed ({response.status_code}): {url}")
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
            tmp.write(response.content)
        Path(tmp.name).replace(path)

    def _parse(self, manifest: dict, version: dict, pdf: Path):
        doc = segment(extract_lines(pdf))
        problems = validate(doc)
        for warning in doc.warnings[:_MAX_WARNINGS_SHOWN]:
            self.stdout.write(f"  warning: {warning}")
        if len(doc.warnings) > _MAX_WARNINGS_SHOWN:
            self.stdout.write(
                f"  … {len(doc.warnings) - _MAX_WARNINGS_SHOWN} more warnings"
            )
        if problems:
            raise CommandError("validation failed: " + "; ".join(problems[:10]))
        xml = build_akn(
            doc,
            {
                "official_id": manifest["official_id"],
                "work_date": manifest["work_date"],
                "expression_date": version["publication_date"],
            },
        )
        rules = doc.rules()
        stats = {
            "rules": len(rules),
            "derogadas": sum(1 for r in rules if r.derogada),
            "transitorios": len(doc.transitorios),
            "warnings": len(doc.warnings),
        }
        return xml, stats

    def _upsert_law(self, manifest: dict) -> Law:
        first = manifest["versions"][0]
        law, _created = Law.objects.update_or_create(
            official_id=manifest["official_id"],
            defaults={
                "name": manifest["name"],
                "short_name": manifest.get("short_name") or manifest["name"][:200],
                "tier": "federal",
                "category": RMF_CATEGORY,
                "domains": list(RMF_DOMAINS),
                "law_type": Law.LawType.NON_LEGISLATIVE,
                "source_url": (first.get("dof_url") or first["document_url"])[:500],
            },
        )
        return law

    def _upsert_version(self, law: Law, version: dict, path: Path) -> None:
        LawVersion.objects.update_or_create(
            law=law,
            publication_date=parse_date(version["publication_date"]),
            defaults={
                "valid_from": parse_date(version["valid_from"]),
                "valid_to": (
                    parse_date(version["valid_to"]) if version.get("valid_to") else None
                ),
                "dof_url": (version.get("dof_url") or version["document_url"])[:500],
                "xml_file_path": str(path),
                "change_summary": version.get("change_summary") or None,
            },
        )

    def _report_stray_versions(self, manifest: dict) -> None:
        """Point at versions this command does not own (never deletes them).

        The catalog feed (``ingest_rmf``) registers a text-less version dated
        1 January when SAT shows no publication date; it is harmless for
        indexing (the newest version wins) but an operator may remove it.
        """
        known = {v["publication_date"] for v in manifest["versions"]}
        stray = LawVersion.objects.filter(
            law__official_id=manifest["official_id"]
        ).exclude(publication_date__in=known)
        for version in stray:
            self.stdout.write(
                self.style.WARNING(
                    f"Version {version.publication_date} of "
                    f"{manifest['official_id']} is not in the manifest "
                    f"(xml_file_path={version.xml_file_path or 'none'}); left as is."
                )
            )
