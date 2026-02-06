"""
Unified path resolution for Docker and local development.

Resolves relative data paths (from metadata JSON files) to absolute paths,
checking Docker prefix (/app/) first, then project BASE_DIR, then cwd.
"""

import os
from pathlib import Path

# Project root: 3 levels up from this file (utils/ -> api/ -> apps/ -> project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Elasticsearch host: env var with sensible default for local dev
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")


def resolve_data_path(relative_path: str) -> Path:
    """
    Resolve a relative data path to an absolute path.

    Checks in order:
    1. /app/<relative_path>  (Docker container)
    2. BASE_DIR/<relative_path>  (local dev from project root)
    3. cwd/<relative_path>  (fallback)

    Args:
        relative_path: Path relative to project root, e.g. "data/state_laws/colima/text.txt"

    Returns:
        Resolved absolute Path (may not exist yet for write destinations)

    Raises:
        FileNotFoundError: If path doesn't exist in any location
    """
    # Strip leading slashes to normalize
    clean_path = relative_path.lstrip("/")

    # Strip /app/ prefix if someone passed it in already
    if clean_path.startswith("app/"):
        clean_path = clean_path[4:]

    candidates = [
        Path("/app") / clean_path,
        BASE_DIR / clean_path,
        Path.cwd() / clean_path,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # If nothing exists yet, return BASE_DIR-relative path (best default for new files)
    return BASE_DIR / clean_path


def resolve_data_path_or_none(relative_path: str) -> Path | None:
    """
    Like resolve_data_path but returns None if file doesn't exist anywhere.
    """
    if not relative_path:
        return None

    clean_path = relative_path.lstrip("/")
    if clean_path.startswith("app/"):
        clean_path = clean_path[4:]

    candidates = [
        Path("/app") / clean_path,
        BASE_DIR / clean_path,
        Path.cwd() / clean_path,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def resolve_metadata_file(filename: str) -> Path:
    """
    Resolve a metadata JSON file from the data/ directory.

    Args:
        filename: e.g. "state_laws_metadata.json" or "municipal_laws_metadata.json"

    Returns:
        Absolute Path to the metadata file
    """
    return resolve_data_path(f"data/{filename}")
