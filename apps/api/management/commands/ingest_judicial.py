"""
Management command to ingest SCJN judicial records into database.

Reads from scraped JSON files (jurisprudencia + tesis aisladas) and creates
JudicialRecord entries with dedup by registro.

Usage:
    # Ingest all judicial records
    python apps/manage.py ingest_judicial --file data/judicial/scjn_records.json

    # Ingest specific type
    python apps/manage.py ingest_judicial --file data/judicial/scjn_records.json --tipo jurisprudencia

    # Dry run
    python apps/manage.py ingest_judicial --file data/judicial/scjn_records.json --dry-run

    # Merge multiple batch files
    python apps/manage.py ingest_judicial --dir data/judicial/batches/
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.api.models import JudicialRecord


class Command(BaseCommand):
    help = "Ingest SCJN judicial records (jurisprudencia + tesis aisladas)"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--file", type=str, help="Path to JSON file with records")
        group.add_argument(
            "--dir", type=str, help="Directory with batch JSON files to merge"
        )

        parser.add_argument(
            "--tipo",
            choices=["jurisprudencia", "tesis_aislada"],
            help="Filter by record type",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Dry run (no database writes)"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Batch size for transactions (default: 500)",
        )
        parser.add_argument(
            "--limit", type=int, help="Limit number of records to process"
        )

    def _load_records(self, options):
        """Load records from file or directory."""
        if options["file"]:
            path = Path(options["file"])
            if not path.exists():
                self.stderr.write(f"File not found: {path}")
                return []
            with open(path) as f:
                data = json.load(f)
            return data if isinstance(data, list) else data.get("records", [])

        # Directory mode: merge batch files
        dir_path = Path(options["dir"])
        if not dir_path.exists():
            self.stderr.write(f"Directory not found: {dir_path}")
            return []

        records = []
        for f in sorted(dir_path.glob("*.json")):
            with open(f) as fh:
                data = json.load(fh)
                batch = data if isinstance(data, list) else data.get("records", [])
                records.extend(batch)
                self.stdout.write(f"  Loaded {len(batch)} records from {f.name}")

        return records

    def _normalize_materia(self, raw):
        """Map raw materia string to model choices."""
        raw_lower = raw.lower().strip()
        materia_map = {
            "civil": "civil",
            "penal": "penal",
            "administrativa": "administrativa",
            "administrativo": "administrativa",
            "laboral": "laboral",
            "constitucional": "constitucional",
            "común": "comun",
            "comun": "comun",
            "common": "comun",
        }
        return materia_map.get(raw_lower, "comun")

    def _normalize_tipo(self, raw):
        """Map raw tipo string to model choices."""
        raw_lower = raw.lower().strip()
        if "jurisprudencia" in raw_lower:
            return "jurisprudencia"
        return "tesis_aislada"

    def handle(self, *args, **options):
        records = self._load_records(options)
        if not records:
            self.stdout.write(self.style.ERROR("No records found"))
            return

        if options["tipo"]:
            records = [
                r
                for r in records
                if self._normalize_tipo(r.get("tipo", "")) == options["tipo"]
            ]

        if options["limit"]:
            records = records[: options["limit"]]

        self.stdout.write("=" * 70)
        self.stdout.write("JUDICIAL RECORD INGESTION")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Records to process: {len(records):,}")
        self.stdout.write(f"Batch size: {options['batch_size']}")
        self.stdout.write(f"Dry run: {options['dry_run']}")
        self.stdout.write("=" * 70)

        created = 0
        updated = 0
        skipped = 0
        errors = 0

        for i in range(0, len(records), options["batch_size"]):
            batch = records[i : i + options["batch_size"]]

            if options["dry_run"]:
                for rec in batch:
                    registro = rec.get("registro", "")
                    if not registro:
                        skipped += 1
                        continue
                    exists = JudicialRecord.objects.filter(registro=registro).exists()
                    if exists:
                        updated += 1
                    else:
                        created += 1
            else:
                with transaction.atomic():
                    for rec in batch:
                        try:
                            registro = rec.get("registro", "")
                            if not registro:
                                skipped += 1
                                continue

                            defaults = {
                                "epoca": rec.get("epoca", ""),
                                "instancia": rec.get("instancia", ""),
                                "materia": self._normalize_materia(
                                    rec.get("materia", "")
                                ),
                                "tipo": self._normalize_tipo(rec.get("tipo", "")),
                                "rubro": rec.get("rubro", ""),
                                "texto": rec.get("texto", ""),
                                "precedentes": rec.get("precedentes", ""),
                                "votos": rec.get("votos", ""),
                                "ponente": rec.get("ponente", ""),
                                "fuente": rec.get("fuente", ""),
                                "fecha_publicacion": rec.get("fecha_publicacion"),
                            }

                            _, was_created = JudicialRecord.objects.update_or_create(
                                registro=registro, defaults=defaults
                            )
                            if was_created:
                                created += 1
                            else:
                                updated += 1

                        except Exception as e:
                            errors += 1
                            if errors <= 10:
                                self.stderr.write(
                                    f"  Error: {rec.get('registro', '?')}: {e}"
                                )

            processed = i + len(batch)
            self.stdout.write(
                f"  Progress: {processed:,}/{len(records):,} "
                f"(created={created}, updated={updated}, skipped={skipped})"
            )

        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write("INGESTION SUMMARY")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Created:  {created:,}")
        self.stdout.write(f"Updated:  {updated:,}")
        self.stdout.write(f"Skipped:  {skipped:,}")
        self.stdout.write(f"Errors:   {errors:,}")
        self.stdout.write("=" * 70)

        if not options["dry_run"]:
            total = JudicialRecord.objects.count()
            self.stdout.write(
                self.style.SUCCESS(f"\nTotal judicial records in DB: {total:,}")
            )
