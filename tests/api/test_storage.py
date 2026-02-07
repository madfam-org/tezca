"""Tests for the dual-backend storage abstraction."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.api.storage import (
    LocalStorageBackend,
    R2StorageBackend,
    get_storage_backend,
    reset_storage_backend,
)


# ---------------------------------------------------------------------------
# LocalStorageBackend
# ---------------------------------------------------------------------------


class TestLocalStorageBackend:
    def setup_method(self):
        """Use a temp directory for each test."""
        import tempfile

        self.tmpdir = Path(tempfile.mkdtemp())
        self.backend = LocalStorageBackend(base_dir=self.tmpdir)

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_put_and_get(self):
        data = b"Constitucion Politica de los Estados Unidos Mexicanos"
        self.backend.put("federal/cpeum.xml", data)
        assert self.backend.get("federal/cpeum.xml") == data

    def test_put_creates_parent_dirs(self):
        self.backend.put("deep/nested/path/file.txt", b"content")
        assert (self.tmpdir / "deep" / "nested" / "path" / "file.txt").exists()

    def test_put_file(self):
        # Create a source file
        src = self.tmpdir / "source.pdf"
        src.write_bytes(b"%PDF-1.4 test content")

        self.backend.put_file("raw/pdfs/test.pdf", src)
        assert self.backend.exists("raw/pdfs/test.pdf")
        assert self.backend.get("raw/pdfs/test.pdf") == b"%PDF-1.4 test content"

    def test_put_file_same_location(self):
        """put_file should handle source == destination gracefully."""
        path = self.tmpdir / "already_here.xml"
        path.write_bytes(b"<xml>data</xml>")
        self.backend.put_file("already_here.xml", path)
        assert self.backend.get("already_here.xml") == b"<xml>data</xml>"

    def test_exists(self):
        assert not self.backend.exists("nonexistent.xml")
        self.backend.put("exists.xml", b"data")
        assert self.backend.exists("exists.xml")

    def test_delete(self):
        self.backend.put("to_delete.xml", b"data")
        assert self.backend.delete("to_delete.xml")
        assert not self.backend.exists("to_delete.xml")

    def test_delete_nonexistent(self):
        assert not self.backend.delete("ghost.xml")

    def test_list_keys(self):
        self.backend.put("federal/a.xml", b"a")
        self.backend.put("federal/b.xml", b"b")
        self.backend.put("state/c.xml", b"c")

        all_keys = self.backend.list_keys()
        assert len(all_keys) == 3

        federal_keys = self.backend.list_keys("federal")
        assert len(federal_keys) == 2
        assert all("federal" in k for k in federal_keys)

    def test_list_keys_empty_prefix(self):
        keys = self.backend.list_keys("nonexistent")
        assert keys == []

    def test_url_returns_absolute_path(self):
        self.backend.put("test.xml", b"data")
        url = self.backend.url("test.xml")
        assert str(self.tmpdir) in url

    def test_get_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            self.backend.get("does_not_exist.xml")


# ---------------------------------------------------------------------------
# R2StorageBackend (mocked boto3)
# ---------------------------------------------------------------------------


class TestR2StorageBackend:
    @patch.dict(
        os.environ,
        {
            "R2_ENDPOINT_URL": "https://test.r2.cloudflarestorage.com",
            "R2_ACCESS_KEY_ID": "test-key",
            "R2_SECRET_ACCESS_KEY": "test-secret",
            "R2_BUCKET_NAME": "test-bucket",
        },
    )
    @patch("boto3.client")
    def test_put(self, mock_boto_client):
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        backend = R2StorageBackend()
        backend.put("federal/cpeum.xml", b"<xml>data</xml>")

        mock_s3.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="federal/cpeum.xml",
            Body=b"<xml>data</xml>",
        )

    @patch.dict(
        os.environ,
        {
            "R2_ENDPOINT_URL": "https://test.r2.cloudflarestorage.com",
            "R2_ACCESS_KEY_ID": "test-key",
            "R2_SECRET_ACCESS_KEY": "test-secret",
            "R2_BUCKET_NAME": "test-bucket",
        },
    )
    @patch("boto3.client")
    def test_get(self, mock_boto_client):
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        mock_body = MagicMock()
        mock_body.read.return_value = b"<xml>data</xml>"
        mock_s3.get_object.return_value = {"Body": mock_body}

        backend = R2StorageBackend()
        result = backend.get("federal/cpeum.xml")

        assert result == b"<xml>data</xml>"
        mock_s3.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="federal/cpeum.xml",
        )

    @patch.dict(
        os.environ,
        {
            "R2_ENDPOINT_URL": "https://test.r2.cloudflarestorage.com",
            "R2_ACCESS_KEY_ID": "test-key",
            "R2_SECRET_ACCESS_KEY": "test-secret",
            "R2_BUCKET_NAME": "test-bucket",
        },
    )
    @patch("boto3.client")
    def test_exists_true(self, mock_boto_client):
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_object.return_value = {}

        backend = R2StorageBackend()
        assert backend.exists("federal/cpeum.xml")

    @patch.dict(
        os.environ,
        {
            "R2_ENDPOINT_URL": "https://test.r2.cloudflarestorage.com",
            "R2_ACCESS_KEY_ID": "test-key",
            "R2_SECRET_ACCESS_KEY": "test-secret",
        },
    )
    @patch("boto3.client")
    def test_url(self, mock_boto_client):
        mock_boto_client.return_value = MagicMock()
        backend = R2StorageBackend()
        url = backend.url("federal/cpeum.xml")
        assert "test.r2.cloudflarestorage.com" in url
        assert "federal/cpeum.xml" in url

    def test_missing_endpoint_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("R2_ENDPOINT_URL", None)
            with patch("boto3.client"):
                with pytest.raises(ValueError, match="R2_ENDPOINT_URL"):
                    R2StorageBackend()


# ---------------------------------------------------------------------------
# get_storage_backend() factory
# ---------------------------------------------------------------------------


class TestGetStorageBackend:
    def setup_method(self):
        reset_storage_backend()

    def teardown_method(self):
        reset_storage_backend()

    def test_default_is_local(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("STORAGE_BACKEND", None)
            backend = get_storage_backend()
            assert isinstance(backend, LocalStorageBackend)

    def test_explicit_local(self):
        with patch.dict(os.environ, {"STORAGE_BACKEND": "local"}):
            backend = get_storage_backend()
            assert isinstance(backend, LocalStorageBackend)

    @patch("boto3.client")
    def test_r2_backend(self, mock_boto_client):
        mock_boto_client.return_value = MagicMock()
        with patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "r2",
                "R2_ENDPOINT_URL": "https://test.r2.cloudflarestorage.com",
                "R2_ACCESS_KEY_ID": "key",
                "R2_SECRET_ACCESS_KEY": "secret",
            },
        ):
            backend = get_storage_backend()
            assert isinstance(backend, R2StorageBackend)

    def test_singleton_returns_same_instance(self):
        with patch.dict(os.environ, {"STORAGE_BACKEND": "local"}):
            b1 = get_storage_backend()
            b2 = get_storage_backend()
            assert b1 is b2
