"""
Management command to ingest CONAMER regulations into database.
Creates Law and LawVersion records from discovered_conamer.json or batch files.

Usage:
    python manage.py ingest_conamer --all
    python manage.py ingest_conamer --all --dry-run
    python manage.py ingest_conamer --all --limit 50
    python manage.py ingest_conamer --all --catalog data/conamer/discovered_conamer.json
"""

import json
import re
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.api.models import Law, LawVersion

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_CATALOG = PROJECT_ROOT / "data" / "conamer" / "discovered_conamer.json"
BATCH_DIR = PROJECT_ROOT / "data" / "conamer"

# Category mapping from CONAMER regulation_type to Law.category
_CATEGORY_MAP = {
    "reglamento": "reglamento",
    "acuerdo": "acuerdo",
    "decreto": "decreto",
    "lineamiento": "lineamiento",
    "lineamientos": "lineamiento",
    "norma": "norma",
    "circular": "circular",
    "manual": "manual",
    "aviso": "aviso",
    "reglas": "reglas",
    "reglas de operacion": "reglas",
    "estatuto": "estatuto",
    "convenio": "convenio",
    "criterio": "criterio",
    "resolucion": "resolucion",
}


def _strip_accents(text: str) -> str:
    """Remove diacritical marks from text."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _slugify(text: str) -> str:
    """Create a safe slug from regulation name."""
    text = _strip_accents(text.lower().strip())
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    return text[:150]


def _normalise_for_dedup(name: str) -> str:
    """Normalise a name for dedup comparison (lowercase, no accents, no punctuation)."""
    text = _strip_accents(name.lower().strip())
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def _infer_category(regulation_type: str, name: str) -> str:
    """
    Infer a Law.category from the regulation_type or name.

    Falls back to 'regulacion' if no match is found.
    """
    if regulation_type:
        key = _strip_accents(regulation_type.lower().strip())
        if key in _CATEGORY_MAP:
            return _CATEGORY_MAP[key]

    # Try matching from the name itself
    name_lower = _strip_accents(name.lower())
    for keyword, category in _CATEGORY_MAP.items():
        if keyword in name_lower:
            return category

    return "regulacion"


def _load_catalog(catalog_path: Path) -> list:
    """
    Load regulations from a single JSON file or merge batch files.

    If catalog_path points to an existing file, loads it directly.
    Otherwise, looks for batch_*.json files in the same directory.

    Returns:
        List of regulation dicts.
    """
    if catalog_path.exists():
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []

    # Try merging batch files
    batch_dir = catalog_path.parent
    if not batch_dir.exists():
        return []

    all_items = []
    for batch_file in sorted(batch_dir.glob("batch_*.json")):
        with open(batch_file, "r", encoding="utf-8") as f:
            items = json.load(f)
        if isinstance(items, list):
            all_items.extend(items)

    return all_items


class Command(BaseCommand):
    help = "Ingest CONAMER regulations into database from discovered_conamer.json"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--all", action="store_true", help="Ingest all regulations")

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Dry run (no database writes)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size for transactions (default: 100)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of regulations to process",
        )
        parser.add_argument(
            "--catalog",
            type=str,
            default=str(DEFAULT_CATALOG),
            help=f"Path to discovered_conamer.json (default: {DEFAULT_CATALOG})",
        )

    def create_law_and_version(self, regulation, dry_run=False):
        """Create Law and LawVersion records from a CONAMER regulation entry."""
        try:
            # Build official_id
            reg_id = regulation.get("id", "")
            reg_name = regulation.get("name", "")[:500]

            if not reg_name:
                return {
                    "success": False,
                    "official_id": "",
                    "error": "No regulation name",
                }

            if reg_id:
                official_id = f"conamer_{reg_id}"
            else:
                official_id = f"conamer_{_slugify(reg_name)}"
            official_id = official_id[:200]

            regulation_type = regulation.get("regulation_type", "")
            category = _infer_category(regulation_type, reg_name)
            source_url = (regulation.get("url", "") or "")[:500]
            issuing_body = regulation.get("issuing_body", "")
            date_str = regulation.get("date", "")

            if dry_run:
                return {
                    "success": True,
                    "official_id": official_id,
                    "action": "dry_run",
                    "law_name": reg_name,
                    "category": category,
                }

            # Dedup: check if law already exists by official_id
            existing_law = Law.objects.filter(official_id=official_id).first()

            # Also check by normalized name to catch duplicates with different IDs
            if not existing_law:
                norm_name = _normalise_for_dedup(reg_name)
                for candidate in Law.objects.filter(
                    tier="federal", law_type="non_legislative"
                ).only("id", "name"):
                    if _normalise_for_dedup(candidate.name) == norm_name:
                        existing_law = candidate
                        break

            defaults = {
                "name": reg_name,
                "tier": "federal",
                "law_type": "non_legislative",
                "category": category,
                "source_url": source_url,
                "status": Law.Status.VIGENTE,
            }

            if existing_law:
                # Update existing record
                for key, value in defaults.items():
                    if value:  # Only update non-empty values
                        setattr(existing_law, key, value)
                existing_law.save()
                law = existing_law
                action = "updated"
            else:
                law = Law.objects.create(official_id=official_id, **defaults)
                action = "created"

            # Publication date
            pub_date = None
            if date_str:
                pub_date = parse_date(date_str)
            if not pub_date:
                pub_date = parse_date("2020-01-01")

            version, v_created = LawVersion.objects.get_or_create(
                law=law,
                publication_date=pub_date,
                defaults={
                    "dof_url": source_url,
                    "xml_file_path": "",
                },
            )
            if not v_created:
                version.dof_url = source_url
                version.save()
                action = "updated"

            return {
                "success": True,
                "official_id": official_id,
                "action": action,
                "law_id": law.id,
                "version_id": version.id,
                "version_created": v_created,
                "law_name": reg_name,
                "category": category,
            }

        except Exception as e:
            return {
                "success": False,
                "official_id": regulation.get("id", "unknown"),
                "error": str(e),
            }

    def handle(self, *args, **options):
        catalog_path = Path(options["catalog"])

        self.stdout.write(f"Loading CONAMER catalog from {catalog_path}...")

        all_regulations = _load_catalog(catalog_path)

        if not all_regulations:
            self.stdout.write(
                self.style.ERROR(f"No regulations found at {catalog_path}")
            )
            self.stdout.write(
                "   Run the CONAMER scraper first:\n"
                "   python -m apps.scraper.federal.conamer_playwright"
            )
            return

        if options["limit"]:
            all_regulations = all_regulations[: options["limit"]]

        if not all_regulations:
            self.stdout.write(self.style.ERROR("No regulations to process"))
            return

        self.stdout.write("=" * 70)
        self.stdout.write("CONAMER REGULATION INGESTION PLAN")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Regulations to ingest: {len(all_regulations):,}")
        self.stdout.write(f"Batch size: {options['batch_size']}")
        self.stdout.write(f"Dry run: {options['dry_run']}")
        self.stdout.write("=" * 70)

        self.stdout.write("Starting CONAMER ingestion...\n")

        results = []
        batch_count = 0

        for i in range(0, len(all_regulations), options["batch_size"]):
            batch = all_regulations[i : i + options["batch_size"]]
            batch_count += 1

            if not options["dry_run"]:
                with transaction.atomic():
                    for regulation in batch:
                        result = self.create_law_and_version(
                            regulation, options["dry_run"]
                        )
                        results.append(result)
            else:
                for regulation in batch:
                    result = self.create_law_and_version(regulation, options["dry_run"])
                    results.append(result)

            processed = len(results)
            success_so_far = sum(1 for r in results if r["success"])
            self.stdout.write(
                f"  Batch {batch_count}: {processed:,}/{len(all_regulations):,} "
                f"({success_so_far}/{processed} successful)"
            )

        # Summary
        success_count = sum(1 for r in results if r["success"])
        failed = [r for r in results if not r["success"]]

        action_counts: dict = {}
        category_counts: dict = {}
        for r in results:
            if r["success"]:
                action = r.get("action", "unknown")
                action_counts[action] = action_counts.get(action, 0) + 1
                cat = r.get("category", "unknown")
                category_counts[cat] = category_counts.get(cat, 0) + 1

        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write("CONAMER INGESTION SUMMARY")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Total regulations:  {len(results):,}")
        self.stdout.write(
            f"Success:            {success_count:,} "
            f"({success_count / len(results) * 100:.1f}%)"
            if results
            else ""
        )
        self.stdout.write(f"Failed:             {len(failed):,}")

        if action_counts:
            self.stdout.write("\nActions:")
            for action, count in sorted(action_counts.items()):
                self.stdout.write(f"  {action:15} {count:5,}")

        if category_counts:
            self.stdout.write("\nCategories:")
            for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
                self.stdout.write(f"  {cat:20} {count:5,}")

        if failed and len(failed) <= 20:
            self.stdout.write(f"\nFailed regulations ({len(failed)}):")
            for result in failed[:20]:
                self.stdout.write(f"  - {result['official_id']}: {result['error']}")
        elif failed:
            self.stdout.write(f"\n{len(failed)} regulations failed")

        self.stdout.write("=" * 70)

        if not options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(f"\nIngested {success_count:,} CONAMER regulations!")
            )
