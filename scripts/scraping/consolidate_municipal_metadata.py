#!/usr/bin/env python3
"""
Consolidate municipal metadata into a single municipal_laws_metadata.json.

Reads all metadata files from data/municipal_laws/<state or city>/ and
merges them into data/municipal_laws_metadata.json for the
ingest_municipal_laws management command.

Exit codes: 0 = success, 1 = failure.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _classify_law(name):
    """Simple heuristic classification based on law name."""
    name_lower = name.lower()
    if "constitución" in name_lower or "constitucional" in name_lower:
        return "constitucion"
    if "código" in name_lower or "codigo" in name_lower:
        return "codigo"
    if "ley orgánica" in name_lower or "ley organica" in name_lower:
        return "ley_organica"
    if "ley" in name_lower:
        return "ley"
    if "reglamento" in name_lower:
        return "reglamento"
    if "decreto" in name_lower:
        return "decreto"
    if "acuerdo" in name_lower:
        return "acuerdo"
    return "otros"


def main():
    # Scan both data/municipal/ (scraper downloads) and data/municipal_laws/ (legacy)
    municipal_dirs = [
        PROJECT_ROOT / "data" / "municipal",
        PROJECT_ROOT / "data" / "municipal_laws",
    ]
    output_file = PROJECT_ROOT / "data" / "municipal_laws_metadata.json"

    found_any = False
    for d in municipal_dirs:
        if d.exists():
            found_any = True
    if not found_any:
        print(
            f"ERROR: no municipal directory found in {[str(d) for d in municipal_dirs]}"
        )
        return 1

    all_laws = []
    sources_found = 0
    sources_skipped = 0

    # Find all metadata/catalog files in subdirectories of both dirs
    patterns = ["*/*_metadata.json", "*/*_municipal_metadata.json", "*/*_catalog.json"]
    metadata_files = set()
    for municipal_dir in municipal_dirs:
        if not municipal_dir.exists():
            continue
        for pattern in patterns:
            metadata_files.update(municipal_dir.glob(pattern))

    for metadata_file in sorted(metadata_files):
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  WARNING: Could not read {metadata_file}: {e}")
            sources_skipped += 1
            continue

        # Handle both dict and list formats
        if isinstance(data, list):
            # List format: each item is a law entry directly
            laws = data
            source_name = metadata_file.parent.name
        else:
            source_name = (
                data.get("state_name") or data.get("city") or metadata_file.parent.name
            )
            laws = data.get("laws", [])

        if not laws:
            print(f"  SKIP: {source_name} (no laws)")
            sources_skipped += 1
            continue

        sources_found += 1

        for law in laws:
            # Handle both OJN-format (file_id, law_name) and catalog-format (name, url)
            file_id = law.get("file_id", "")
            law_name = law.get("law_name") or law.get("name", "")
            state = law.get("state", "") or (
                data.get("state_name", "") if isinstance(data, dict) else ""
            )
            municipality = (
                law.get("municipality")
                or law.get("locality")
                or (data.get("city", "") if isinstance(data, dict) else source_name)
            )

            # Generate official_id
            if file_id:
                official_id = f"mun_{file_id}"
            else:
                # Use source + index for catalog entries
                slug = law_name.lower().replace(" ", "-")[:50]
                official_id = f"mun_{source_name.lower().replace(' ', '_')}_{slug}"

            category = _classify_law(law_name)

            consolidated = {
                "official_id": official_id,
                "law_name": law_name,
                "category": category,
                "tier": "municipal",
                "state": state,
                "municipality": municipality,
                "publication_date": law.get("publication_date"),
                "text_file": law.get("local_path", ""),
                "url": law.get("url", ""),
                "file_id": file_id,
                "format": law.get("format", "pdf"),
            }
            all_laws.append(consolidated)

        print(f"  {source_name}: {len(laws)} laws")

    # Write consolidated metadata
    consolidated_data = {
        "total_sources": sources_found,
        "total_laws": len(all_laws),
        "sources_skipped": sources_skipped,
        "laws": all_laws,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(consolidated_data, f, indent=2, ensure_ascii=False)

    print(
        f"\nConsolidated {len(all_laws)} municipal laws from {sources_found} sources."
    )
    print(f"Saved to {output_file}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
