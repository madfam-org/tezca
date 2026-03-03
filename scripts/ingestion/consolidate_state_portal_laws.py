#!/usr/bin/env python
"""
Consolidate state congress portal scraped laws into the non-legislative metadata file.

Reads per-state metadata JSONs from data/state_laws/{state}/ and appends entries
to data/state_laws_non_legislative_metadata.json in the format expected by
ingest_non_legislative_laws management command.

Usage:
    # Consolidate BC, DGO, QR into metadata
    python scripts/ingestion/consolidate_state_portal_laws.py --states baja_california durango quintana_roo

    # Dry run (show what would be added)
    python scripts/ingestion/consolidate_state_portal_laws.py --states baja_california --dry-run

    # Consolidate all states with metadata files
    python scripts/ingestion/consolidate_state_portal_laws.py --all
"""

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STATE_LAWS_DIR = DATA_DIR / "state_laws"
METADATA_FILE = DATA_DIR / "state_laws_non_legislative_metadata.json"

STATE_NAME_MAP = {
    "aguascalientes": "Aguascalientes",
    "baja_california": "Baja California",
    "baja_california_sur": "Baja California Sur",
    "campeche": "Campeche",
    "cdmx": "Ciudad de México",
    "ciudad_de_mexico": "Ciudad de México",
    "chiapas": "Chiapas",
    "chihuahua": "Chihuahua",
    "coahuila": "Coahuila",
    "colima": "Colima",
    "durango": "Durango",
    "estado_de_mexico": "Estado de México",
    "guanajuato": "Guanajuato",
    "guerrero": "Guerrero",
    "hidalgo": "Hidalgo",
    "jalisco": "Jalisco",
    "michoacan": "Michoacán",
    "morelos": "Morelos",
    "nayarit": "Nayarit",
    "nuevo_leon": "Nuevo León",
    "oaxaca": "Oaxaca",
    "puebla": "Puebla",
    "queretaro": "Querétaro",
    "quintana_roo": "Quintana Roo",
    "san_luis_potosi": "San Luis Potosí",
    "sinaloa": "Sinaloa",
    "sonora": "Sonora",
    "tabasco": "Tabasco",
    "tamaulipas": "Tamaulipas",
    "tlaxcala": "Tlaxcala",
    "veracruz": "Veracruz",
    "yucatan": "Yucatán",
    "zacatecas": "Zacatecas",
}


def _strip_accents(s):
    """Remove diacritical marks for normalization."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.category(c).startswith("M"))


def _normalize_name(name):
    """Normalize law name for dedup comparison."""
    name = _strip_accents(name.lower())
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _generate_official_id(state_code, law_name, file_id=""):
    """Generate a stable official_id from state + law name."""
    key = f"{state_code}:{_normalize_name(law_name)}"
    h = hashlib.sha256(key.encode()).hexdigest()[:12]
    return f"sp-{state_code}-{h}"


def _extract_date(law_name):
    """Try to extract a date from law name string (e.g. 2023/07/19)."""
    m = re.search(r"(\d{4})/(\d{2})/(\d{2})", law_name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", law_name)
    if m:
        return m.group(0)
    return None


def _clean_law_name(raw_name):
    """Clean up law name: strip dates, status, tomo markers."""
    name = raw_name
    # Remove trailing date patterns like 2023/07/19
    name = re.sub(r"\d{4}/\d{2}/\d{2}", "", name)
    # Remove VIGENTE/ABROGADA/DEROGADA
    name = re.sub(
        r"(VIGENTE|ABROGADA|DEROGADA|REFORMADA)", "", name, flags=re.IGNORECASE
    )
    # Remove TOMO_* markers
    name = re.sub(r"TOMO_[IVX]+", "", name, flags=re.IGNORECASE)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


def find_text_file(state_dir, file_id):
    """Find the .txt file for a given file_id."""
    txt = state_dir / f"{file_id}.txt"
    if txt.exists():
        return str(txt.relative_to(PROJECT_ROOT))
    # Try finding any txt file with the same prefix
    for f in state_dir.glob(f"{file_id}*.txt"):
        return str(f.relative_to(PROJECT_ROOT))
    return None


def _infer_category(law_name):
    """Infer category from law name keywords."""
    name_lower = law_name.lower()
    category_keywords = {
        "Constitucional": ["constituc"],
        "Administrativo": [
            "administrat",
            "burocrát",
            "servidores públicos",
            "gobierno",
        ],
        "Civil": ["civil", "notari", "registro público"],
        "Penal": ["penal", "justicia cívica", "seguridad pública", "polici"],
        "Fiscal": ["fiscal", "hacend", "ingreso", "gasto", "presupuest", "financ"],
        "Laboral": ["trabajo", "laboral", "empleo"],
        "Electoral": ["electoral", "eleccion", "partidos"],
        "Ambiental": ["ambient", "ecolog", "forestal", "agua", "hidráulic"],
        "Educación": ["educac", "universid", "escolar"],
        "Salud": ["salud", "sanitar", "hospital"],
        "Social": [
            "social",
            "asistencia",
            "familia",
            "mujer",
            "joven",
            "niñ",
            "discapacid",
        ],
        "Transparencia": ["transparenc", "acceso a la informac", "datos personal"],
        "Derechos Humanos": ["derechos humanos"],
        "Agrario": ["agrari", "desarroll rural", "ganaderi"],
        "Mercantil": ["comerc", "mercant", "empresa"],
        "Transporte": ["transport", "tránsit", "vialid", "movilid"],
        "Urbano": ["urban", "asentamiento", "ordenamiento territorial", "catastro"],
    }

    for category, keywords in category_keywords.items():
        for kw in keywords:
            if kw in name_lower:
                return category
    return "Otro"


def consolidate_state(state_code, dry_run=False):
    """Read state portal metadata and generate ingest-compatible entries."""
    state_dir = STATE_LAWS_DIR / state_code
    state_name = STATE_NAME_MAP.get(state_code, state_code.replace("_", " ").title())

    # Find metadata file
    meta_files = list(state_dir.glob("*metadata*.json"))
    if not meta_files:
        print(f"  No metadata file found in {state_dir}")
        return []

    with open(meta_files[0]) as f:
        data = json.load(f)

    laws = data.get("laws", [])
    if not laws:
        print(f"  No laws in metadata for {state_code}")
        return []

    entries = []
    skipped = 0

    for law in laws:
        file_id = law.get("file_id", "")
        raw_name = law.get("law_name", "")

        # Find text file
        text_file = find_text_file(state_dir, file_id)
        if not text_file:
            skipped += 1
            continue

        clean_name = _clean_law_name(raw_name)
        pub_date = _extract_date(raw_name)
        official_id = _generate_official_id(state_code, clean_name, file_id)
        category = _infer_category(clean_name)

        entry = {
            "official_id": official_id,
            "law_name": clean_name,
            "state": state_name,
            "tier": "state",
            "category": category,
            "law_type": law.get("law_type", "non_legislative"),
            "publication_date": pub_date or "2023-01-01",
            "text_file": text_file,
            "url": law.get("url", ""),
            "source": "state_congress_portal",
        }
        entries.append(entry)

    print(
        f"  {state_code}: {len(entries)} entries ready, {skipped} skipped (no text file)"
    )
    return entries


def main():
    parser = argparse.ArgumentParser(
        description="Consolidate state portal laws into non-legislative metadata"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--states", nargs="+", help="State codes to consolidate")
    group.add_argument("--all", action="store_true", help="All states with metadata")
    parser.add_argument("--dry-run", action="store_true", help="Show counts only")
    parser.add_argument("--output", type=str, help="Custom output path")
    args = parser.parse_args()

    if args.all:
        state_codes = []
        for d in sorted(STATE_LAWS_DIR.iterdir()):
            if d.is_dir() and list(d.glob("*metadata*.json")):
                state_codes.append(d.name)
    else:
        state_codes = args.states

    print(f"Consolidating {len(state_codes)} state(s): {', '.join(state_codes)}")
    print()

    all_new = []
    for code in state_codes:
        entries = consolidate_state(code, args.dry_run)
        all_new.extend(entries)

    print(f"\nTotal new entries: {len(all_new)}")

    if args.dry_run:
        # Show category distribution
        cats = {}
        for e in all_new:
            cats[e["category"]] = cats.get(e["category"], 0) + 1
        print("\nCategory distribution:")
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")
        return

    # Load existing metadata
    if METADATA_FILE.exists():
        with open(METADATA_FILE) as f:
            metadata = json.load(f)
    else:
        metadata = {
            "source": "consolidated",
            "total_states": 0,
            "total_laws": 0,
            "laws": [],
        }

    # Dedup by normalized name within state
    existing_keys = set()
    for law in metadata.get("laws", []):
        key = f"{law.get('state', '')}:{_normalize_name(law.get('law_name', ''))}"
        existing_keys.add(key)

    added = 0
    for entry in all_new:
        key = f"{entry['state']}:{_normalize_name(entry['law_name'])}"
        if key not in existing_keys:
            metadata["laws"].append(entry)
            existing_keys.add(key)
            added += 1

    metadata["total_laws"] = len(metadata["laws"])

    # Count unique states
    states_in_meta = set(law.get("state", "") for law in metadata["laws"])
    metadata["total_states"] = len(states_in_meta)
    metadata["states_skipped"] = 0

    output_path = Path(args.output) if args.output else METADATA_FILE
    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\nAdded {added} new entries ({len(all_new) - added} duplicates skipped)")
    print(f"Total laws in metadata: {metadata['total_laws']}")
    print(f"Written to: {output_path}")


if __name__ == "__main__":
    main()
