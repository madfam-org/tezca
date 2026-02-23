"""
Unified path resolution for Docker and local development.

Resolves relative data paths (from metadata JSON files) to absolute paths,
checking Docker prefix (/app/) first, then project BASE_DIR, then cwd.
"""

import json
import os
from pathlib import Path

# Project root: 3 levels up from this file (utils/ -> api/ -> apps/ -> project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Re-export from centralized config for backward compat
from apps.api.config import ES_HOST  # noqa: F401, E402


def _strip_host_prefix(path_str: str) -> str:
    """Strip absolute host project root from paths embedded in metadata JSON.

    Metadata files may contain absolute paths like
    ``/Users/.../tezca/data/state_laws/...``.  Inside Docker the
    project root is ``/app/``, so we extract the relative portion (e.g.
    ``data/state_laws/...``) to allow the normal candidate logic to find them.
    """
    # Common host-side project root markers (support both old and new dir names)
    for marker in ("tezca/", "leyes-como-codigo-mx/"):
        idx = path_str.find(marker)
        if idx != -1:
            return path_str[idx + len(marker) :]
    return path_str


def resolve_data_path(relative_path: str) -> Path:
    """
    Resolve a data path to an absolute path.

    Handles:
    - Absolute paths (returned as-is if they exist)
    - /app/ prefixed paths (Docker)
    - Relative paths (checked against BASE_DIR then cwd)
    - Absolute host paths embedded in metadata (stripped to relative)

    Args:
        relative_path: Path to resolve (absolute or relative)

    Returns:
        Resolved absolute Path (may not exist yet for write destinations)
    """
    # If already an absolute path that exists, return directly
    if relative_path.startswith("/") and not relative_path.startswith("/app/"):
        abs_path = Path(relative_path)
        if abs_path.exists():
            return abs_path
        # Try stripping host project root prefix
        relative_path = _strip_host_prefix(relative_path)

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

    # If already an absolute path that exists, return directly
    if relative_path.startswith("/") and not relative_path.startswith("/app/"):
        abs_path = Path(relative_path)
        if abs_path.exists():
            return abs_path
        # Try stripping host project root prefix
        relative_path = _strip_host_prefix(relative_path)

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


def data_exists(relative_path: str) -> bool:
    """Check if a data file exists locally or in R2 storage.

    Args:
        relative_path: Relative data path (e.g. "state_laws/colima/law.txt")

    Returns:
        True if file exists in local filesystem or R2.
    """
    if not relative_path:
        return False

    # Check local first
    if resolve_data_path_or_none(relative_path) is not None:
        return True

    # Check R2 if configured
    if os.environ.get("STORAGE_BACKEND") == "r2":
        from apps.api.storage import get_storage_backend

        storage = get_storage_backend()
        key = _strip_host_prefix(relative_path)
        key = key.lstrip("/")
        if key.startswith("data/"):
            key = key[5:]
        return storage.exists(key)

    return False


def read_metadata_json(filename: str) -> dict | None:
    """Load a metadata JSON file from local filesystem or R2 storage.

    Tries local resolution first via resolve_metadata_file(). If the file
    doesn't exist locally and STORAGE_BACKEND=r2, falls back to R2.

    Args:
        filename: e.g. "state_laws_metadata.json"

    Returns:
        Parsed JSON dict, or None if not found.
    """
    # Try local first
    local_path = resolve_metadata_file(filename)
    if local_path.exists():
        return json.loads(local_path.read_text(encoding="utf-8"))

    # Fall back to R2
    content = read_data_content(f"data/{filename}")
    if content:
        return json.loads(content)

    return None


def read_data_content(relative_path: str, encoding: str = "utf-8") -> str | None:
    """
    Read file content from local filesystem or R2 storage backend.

    Tries local resolution first (resolve_data_path_or_none). If the file
    is not found locally and STORAGE_BACKEND=r2, falls back to reading
    from R2 using the storage backend.

    Args:
        relative_path: Relative data path (e.g. "federal/mx-fed-103.xml")
        encoding: Text encoding (default utf-8)

    Returns:
        File content as string, or None if not found anywhere.
    """
    if not relative_path:
        return None

    # Try local filesystem first
    local_path = resolve_data_path_or_none(relative_path)
    if local_path:
        return local_path.read_text(encoding=encoding, errors="ignore")

    # Fall back to R2 storage if configured
    if os.environ.get("STORAGE_BACKEND") == "r2":
        from apps.api.storage import get_storage_backend

        storage = get_storage_backend()
        # Normalize the key: strip host prefix and leading data/ prefix,
        # since R2 keys mirror the data/ directory structure
        key = _strip_host_prefix(relative_path)
        key = key.lstrip("/")
        if key.startswith("data/"):
            key = key[5:]

        try:
            data = storage.get(key)
            return data.decode(encoding, errors="ignore")
        except (FileNotFoundError, Exception):
            return None

    return None
