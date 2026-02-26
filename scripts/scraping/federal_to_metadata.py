#!/usr/bin/env python3
"""
Convert federal scraper batch JSON output to ingestible metadata format.

Federal scrapers (CONAMER, NOM, Treaty) save paginated batch_NNNN.json files.
This script reads all batches, deduplicates, and produces a single metadata
JSON compatible with ingest_from_metadata.py.

Usage:
    python scripts/scraping/federal_to_metadata.py --source conamer --input data/federal/conamer/
    python scripts/scraping/federal_to_metadata.py --source noms --input data/federal/noms/
    python scripts/scraping/federal_to_metadata.py --source treaties --input data/federal/treaties/
    python scripts/scraping/federal_to_metadata.py --source all
"""

import argparse
import hashlib
import json
import logging
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Source configs
# ---------------------------------------------------------------------------

SOURCES = {
    "conamer": {
        "default_input": "data/federal/conamer",
        "tier": "federal",
        "category": "Reglamento",
        "law_type": "reglamento",
        "id_prefix": "conamer",
    },
    "noms": {
        "default_input": "data/federal/noms",
        "tier": "federal",
        "category": "NOM",
        "law_type": "nom",
        "id_prefix": "nom",
    },
    "treaties": {
        "default_input": "data/federal/treaties",
        "tier": "federal",
        "category": "Tratado",
        "law_type": "tratado",
        "id_prefix": "treaty",
    },
}


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _make_official_id(prefix: str, name: str, index: int) -> str:
    """Generate a stable official_id from source prefix + name hash."""
    name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
    return f"{prefix}_{name_hash}_{index:05d}"


def _extract_date(item: Dict[str, Any]) -> str:
    """Extract publication date from various field names."""
    for key in ("date", "fecha_publicacion", "publication_date", "year"):
        val = item.get(key)
        if val:
            val_str = str(val).strip()
            # If just a year, make it a date
            if re.match(r"^\d{4}$", val_str):
                return f"{val_str}-01-01"
            # If already ISO-like, return as-is
            if re.match(r"^\d{4}-\d{2}-\d{2}", val_str):
                return val_str[:10]
            return val_str
    return ""


def load_batches(input_dir: Path) -> List[Dict[str, Any]]:
    """Load all batch JSON files from a directory."""
    items = []
    batch_files = sorted(input_dir.glob("batch_*.json"))

    if not batch_files:
        # Also check for single-file outputs
        for f in sorted(input_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    items.extend(data)
                elif isinstance(data, dict):
                    # Look for items under known keys
                    for key in (
                        "items",
                        "regulations",
                        "noms",
                        "treaties",
                        "results",
                        "data",
                    ):
                        if key in data and isinstance(data[key], list):
                            items.extend(data[key])
                            break
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Could not read %s: %s", f, e)
        return items

    for batch_file in batch_files:
        try:
            data = json.loads(batch_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                items.extend(data)
            elif isinstance(data, dict) and "items" in data:
                items.extend(data["items"])
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not read %s: %s", batch_file, e)

    logger.info(
        "Loaded %d items from %d batch files in %s",
        len(items),
        len(batch_files),
        input_dir,
    )
    return items


def dedup_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate items by normalised title."""
    seen: Set[str] = set()
    unique = []
    for item in items:
        name = item.get("name", "") or item.get("nombre", "") or item.get("title", "")
        norm = _strip_accents(name.lower().strip())
        norm = re.sub(r"\s+", " ", norm)
        if norm and norm not in seen:
            seen.add(norm)
            unique.append(item)
    logger.info("Dedup: %d → %d unique items", len(items), len(unique))
    return unique


def convert_to_metadata(
    items: List[Dict[str, Any]],
    source_config: Dict[str, str],
) -> Dict[str, Any]:
    """Convert raw scraper items to ingest-compatible metadata format."""
    laws = []
    prefix = source_config["id_prefix"]
    tier = source_config["tier"]
    default_category = source_config["category"]
    default_law_type = source_config["law_type"]

    for i, item in enumerate(items):
        name = (
            item.get("name", "")
            or item.get("nombre", "")
            or item.get("title", "")
            or item.get("treaty_name", "")
        ).strip()
        if not name:
            continue

        url = (item.get("url", "") or item.get("enlace", "") or "").strip()

        official_id = _make_official_id(prefix, name, i)
        pub_date = _extract_date(item)

        # Determine category from name if possible
        category = (
            item.get("regulation_type") or item.get("category") or default_category
        )

        laws.append(
            {
                "official_id": official_id,
                "law_name": name[:500],
                "category": category[:100],
                "tier": tier,
                "state": "",
                "publication_date": pub_date,
                "text_file": "",
                "url": url[:500],
                "file_id": official_id,
                "format": "",
                "law_type": default_law_type,
            }
        )

    metadata = {
        "source": prefix,
        "total_laws": len(laws),
        "laws": laws,
    }
    return metadata


def process_source(source_key: str, input_dir: str = None):
    """Process a single federal source."""
    if source_key not in SOURCES:
        logger.error("Unknown source: %s (available: %s)", source_key, list(SOURCES))
        return None

    config = SOURCES[source_key]
    in_dir = Path(input_dir) if input_dir else PROJECT_ROOT / config["default_input"]

    if not in_dir.exists():
        logger.warning("Input directory does not exist: %s", in_dir)
        return None

    logger.info("Processing %s from %s", source_key, in_dir)

    items = load_batches(in_dir)
    if not items:
        logger.warning("No items found for %s", source_key)
        return None

    unique_items = dedup_items(items)
    metadata = convert_to_metadata(unique_items, config)

    # Write output
    output_path = PROJECT_ROOT / "data" / f"federal_{source_key}_metadata.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info("Wrote %d laws to %s", len(metadata["laws"]), output_path)
    return {
        "source": source_key,
        "raw_items": len(items),
        "unique_items": len(unique_items),
        "output": str(output_path),
    }


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Convert federal scraper batch JSON to ingest metadata format",
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        choices=list(SOURCES) + ["all"],
        help="Federal source to convert (or 'all')",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Input directory with batch JSON files (default: data/federal/{source}/)",
    )
    args = parser.parse_args()

    sources_to_run = list(SOURCES) if args.source == "all" else [args.source]
    results = []

    for key in sources_to_run:
        result = process_source(key, args.input if args.source != "all" else None)
        if result:
            results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("FEDERAL METADATA CONVERSION SUMMARY")
    print("=" * 60)
    for r in results:
        print(
            f"  {r['source']}: {r['raw_items']} raw → {r['unique_items']} unique → {r['output']}"
        )
    print("=" * 60)


if __name__ == "__main__":
    main()
