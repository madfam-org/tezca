"""
Dual-backend document storage: local filesystem (dev) + Cloudflare R2 (production).

The codebase works fully offline with local /data/ — R2 is optional for local dev,
mandatory for tezca.mx production on K8s (pods have no persistent data volumes).

Backend selection via STORAGE_BACKEND env var:
  - unset or "local" → LocalStorageBackend (default, zero config)
  - "r2"             → R2StorageBackend (requires R2_* env vars)
"""

import logging
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Project root: storage.py → api/ → apps/ → project root
_BASE_DIR = Path(__file__).resolve().parent.parent.parent


class StorageBackend(ABC):
    """Abstract interface for document storage."""

    @abstractmethod
    def put(self, key: str, data: bytes) -> str:
        """Store data at key. Returns the key or URL."""

    @abstractmethod
    def put_file(self, key: str, local_path: Path) -> str:
        """Upload a local file to storage. Returns the key or URL."""

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Retrieve data by key."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in storage."""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key from storage. Returns True if deleted."""

    @abstractmethod
    def list_keys(self, prefix: str = "") -> list[str]:
        """List keys matching prefix."""

    @abstractmethod
    def url(self, key: str) -> str:
        """Get a URL or path for the stored object."""


class LocalStorageBackend(StorageBackend):
    """
    Local filesystem storage backend (development default).

    Reads/writes to the project's /data/ directory with zero config.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or (_BASE_DIR / "data")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        resolved = (self.base_dir / key).resolve()
        if not str(resolved).startswith(str(self.base_dir.resolve())):
            raise ValueError(f"Path traversal detected: {key}")
        return resolved

    def put(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def put_file(self, key: str, local_path: Path) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Avoid copying if source and destination are the same
        if path.resolve() != Path(local_path).resolve():
            import shutil

            shutil.copy2(local_path, path)
        return key

    def get(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"Local storage key not found: {key}")
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def delete(self, key: str) -> bool:
        path = self._resolve(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_keys(self, prefix: str = "") -> list[str]:
        search_dir = self._resolve(prefix) if prefix else self.base_dir
        if not search_dir.exists():
            return []
        if search_dir.is_file():
            return [prefix]
        resolved_base = self.base_dir.resolve()
        return [
            str(p.resolve().relative_to(resolved_base))
            for p in search_dir.rglob("*")
            if p.is_file()
        ]

    def url(self, key: str) -> str:
        return str(self._resolve(key))


class R2StorageBackend(StorageBackend):
    """
    Cloudflare R2 storage backend (S3-compatible) for production.

    Uses boto3 with lazy import — only loaded when STORAGE_BACKEND=r2.
    Credentials via env vars: R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
    R2_ENDPOINT_URL, R2_BUCKET_NAME.
    """

    def __init__(self):
        # Lazy import — boto3 is an optional dependency
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for R2 storage. " "Install with: pip install boto3"
            )

        self.bucket_name = os.environ.get("R2_BUCKET_NAME", "tezca-documents")
        endpoint_url = os.environ.get("R2_ENDPOINT_URL")
        access_key = os.environ.get("R2_ACCESS_KEY_ID")
        secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")

        if not endpoint_url:
            raise ValueError("R2_ENDPOINT_URL environment variable is required")

        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )
        logger.info("R2 storage initialized: bucket=%s", self.bucket_name)

    def put(self, key: str, data: bytes) -> str:
        self._client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
        )
        return key

    def put_file(self, key: str, local_path: Path) -> str:
        self._client.upload_file(
            str(local_path),
            self.bucket_name,
            key,
        )
        return key

    def get(self, key: str) -> bytes:
        response = self._client.get_object(
            Bucket=self.bucket_name,
            Key=key,
        )
        return response["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except self._client.exceptions.ClientError:
            return False

    def delete(self, key: str) -> bool:
        try:
            self._client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except self._client.exceptions.ClientError:
            return False

    def list_keys(self, prefix: str = "") -> list[str]:
        keys = []
        paginator = self._client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
        for page in pages:
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys

    def url(self, key: str) -> str:
        endpoint = os.environ.get("R2_ENDPOINT_URL", "")
        return f"{endpoint}/{self.bucket_name}/{key}"


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------

_storage_backend: Optional[StorageBackend] = None
_storage_lock = threading.Lock()


def get_storage_backend() -> StorageBackend:
    """
    Get the configured storage backend (thread-safe singleton).

    Returns LocalStorageBackend by default (zero config for dev).
    Set STORAGE_BACKEND=r2 for Cloudflare R2 in production.
    """
    global _storage_backend
    if _storage_backend is not None:
        return _storage_backend

    with _storage_lock:
        # Double-check after acquiring lock
        if _storage_backend is not None:
            return _storage_backend

        backend_type = os.getenv("STORAGE_BACKEND", "local")

        if backend_type == "r2":
            _storage_backend = R2StorageBackend()
            logger.info("Storage backend: Cloudflare R2")
        else:
            _storage_backend = LocalStorageBackend()
            logger.info("Storage backend: local filesystem")

        return _storage_backend


def reset_storage_backend() -> None:
    """Reset the singleton (for testing)."""
    global _storage_backend
    with _storage_lock:
        _storage_backend = None
