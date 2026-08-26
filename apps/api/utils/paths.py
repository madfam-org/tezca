"""
Unified path resolution for Docker and local development.

Resolves relative data paths (from metadata JSON files) to absolute paths,
checking Docker prefix (/app/) first, then project BASE_DIR, then cwd.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Project root: 3 levels up from this file (utils/ -> api/ -> apps/ -> project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Re-export from centralized config for backward compat
from apps.api.config import ES_HOST  # noqa: F401, E402


def _decode_bytes(data: bytes, encoding: str = "utf-8") -> str:
    """Decode raw file bytes to text without silently deleting content.

    The old behaviour here decoded with ``errors="ignore"``, which is a data
    -integrity hazard for the legal corpus: a latin-1 / cp1252 source (SAT,
    some OJN feeds) decoded as UTF-8 does **not** raise and does **not**
    produce the U+FFFD replacement char — ``errors="ignore"`` DELETES every
    high-byte character (á/é/í/ñ/ó/ú, °, §, …) with no trace. The spot-check
    encoding detector only counts U+FFFD, so the corruption was invisible by
    construction and accented articles silently entered Elasticsearch stripped
    of their accents.

    Strategy (in order):
      1. Decode strictly with the requested ``encoding`` — the common,
         correct case (valid UTF-8) is unchanged and fast.
      2. On UnicodeDecodeError, detect the real encoding with
         ``charset_normalizer`` (always installed — it is a hard dependency of
         ``requests``, which is a core direct dependency) and decode with it,
         so latin-1 / cp1252 accents are PRESERVED, not lost. The import is
         defensive: if it were ever absent, the code degrades to step 3 rather
         than crashing.
      3. If detection is unavailable or unusable, fall back to
         ``errors="replace"`` — bad bytes become U+FFFD, which is DETECTABLE
         by the spot-check ``encoding_check`` / ``es_text_sample`` guards.
         Never ``errors="ignore"``: silent deletion is the defect.
    """
    # 1. Fast path: strict decode with the requested encoding.
    try:
        return data.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        pass

    # 2. Detect the true encoding and decode losslessly.
    #
    # The corpus is Mexican Spanish (Western European). charset_normalizer
    # tends to mis-detect a short Spanish latin-1 sample as a Central-European
    # code page (cp1250 / iso8859_2), which decodes 0xF1 as "ń" instead of "ñ"
    # — still lossless but wrong for "niño / señor / año / compañía". Excluding
    # the Eastern-European candidates biases detection back to cp1252 / latin-1,
    # which decode Mexican accents correctly.
    _NON_WESTERN_EXCLUSIONS = [
        "cp1250",
        "cp1251",
        "cp1256",
        "iso8859_2",
        "iso8859_4",
        "iso8859_5",
        "iso8859_13",
    ]
    try:
        from charset_normalizer import from_bytes

        best = from_bytes(data, cp_exclusion=_NON_WESTERN_EXCLUSIONS).best()
        if best is not None:
            # ``str(best)`` yields the decoded text using the detected encoding.
            decoded = str(best)
            logger.warning(
                "read_data_content: %r bytes were not valid %s; decoded as "
                "detected encoding %r (accented content preserved)",
                len(data),
                encoding,
                best.encoding,
            )
            return decoded
    except Exception:  # noqa: BLE001 - detection is best-effort; fall through
        logger.warning(
            "read_data_content: charset detection failed; "
            "falling back to errors='replace'",
        )

    # 3. Detectable fallback: bad bytes become U+FFFD (never silently dropped).
    result = data.decode(encoding, errors="replace")
    if "�" in result:
        logger.warning(
            "read_data_content: undecodable bytes replaced with U+FFFD "
            "(flagged by the encoding spot-check)",
        )
    return result


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
        # Read bytes + decode via _decode_bytes so a mis-encoded (latin-1 /
        # cp1252) source keeps its accents instead of having them silently
        # deleted by errors="ignore". See _decode_bytes for the full rationale.
        return _decode_bytes(local_path.read_bytes(), encoding)

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
            # Same encoding-fidelity strategy as the local path: decode via
            # _decode_bytes so mis-encoded bytes are preserved/flagged, never
            # silently dropped by errors="ignore".
            return _decode_bytes(data, encoding)
        except (FileNotFoundError, Exception):
            return None

    return None
