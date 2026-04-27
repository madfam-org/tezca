"""
Tests for ``apps.scraper.http`` — government TLS session factory.
"""

from __future__ import annotations

import hashlib
import logging
from unittest.mock import patch

import pytest

from apps.scraper import http as http_mod


def _fake_der(payload: bytes = b"x") -> bytes:
    return payload


# ---------------------------------------------------------------------------
# _host_from_url
# ---------------------------------------------------------------------------


def test_host_from_url_extracts_hostname_lowercased():
    assert http_mod._host_from_url("https://DOF.gob.mx/some/path") == "dof.gob.mx"


def test_host_from_url_handles_missing_scheme():
    # urlparse returns no hostname for bare strings — function must not crash
    assert http_mod._host_from_url("dof.gob.mx") == ""


# ---------------------------------------------------------------------------
# _normalize_fingerprint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("aa:bb:cc", "AABBCC"),
        ("AA BB CC", "AABBCC"),
        ("aabbcc", "AABBCC"),
    ],
)
def test_normalize_fingerprint(raw, expected):
    assert http_mod._normalize_fingerprint(raw) == expected


# ---------------------------------------------------------------------------
# fetch_leaf_fingerprint
# ---------------------------------------------------------------------------


def test_fetch_leaf_fingerprint_returns_sha256_of_der():
    der = _fake_der(b"hello-world")
    expected = hashlib.sha256(der).hexdigest().upper()

    fake_ssock = type("FakeSSock", (), {"getpeercert": lambda self, binary_form: der})()

    class _CtxMgr:
        def __enter__(self):
            return fake_ssock

        def __exit__(self, *args):
            return False

    class _SocketCtx:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    fake_ctx = type(
        "FakeCtx",
        (),
        {
            "check_hostname": True,
            "verify_mode": None,
            "wrap_socket": lambda self, sock, server_hostname: _CtxMgr(),
        },
    )()

    with patch(
        "apps.scraper.http.ssl.create_default_context", return_value=fake_ctx
    ), patch("apps.scraper.http.socket.create_connection", return_value=_SocketCtx()):
        result = http_mod.fetch_leaf_fingerprint("dof.gob.mx")
    assert result == expected


def test_fetch_leaf_fingerprint_raises_when_no_cert():
    fake_ssock = type(
        "FakeSSock", (), {"getpeercert": lambda self, binary_form: None}
    )()

    class _CtxMgr:
        def __enter__(self):
            return fake_ssock

        def __exit__(self, *args):
            return False

    class _SocketCtx:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    fake_ctx = type(
        "FakeCtx",
        (),
        {
            "check_hostname": True,
            "verify_mode": None,
            "wrap_socket": lambda self, sock, server_hostname: _CtxMgr(),
        },
    )()

    with patch(
        "apps.scraper.http.ssl.create_default_context", return_value=fake_ctx
    ), patch("apps.scraper.http.socket.create_connection", return_value=_SocketCtx()):
        with pytest.raises(RuntimeError, match="No leaf certificate"):
            http_mod.fetch_leaf_fingerprint("dof.gob.mx")


# ---------------------------------------------------------------------------
# government_session — trust-resolution paths
# ---------------------------------------------------------------------------


def test_session_uses_normal_tls_for_unknown_host():
    sess = http_mod.government_session("https://example.com/")
    assert sess.verify is True


def test_session_disables_verify_for_insecure_host(caplog):
    caplog.set_level(logging.WARNING, logger="apps.scraper.http")
    sess = http_mod.government_session("https://dof.gob.mx/some/path")
    assert sess.verify is False
    assert any("dof.gob.mx" in rec.getMessage() for rec in caplog.records)


def test_session_pins_fingerprint_when_known(caplog, monkeypatch):
    fingerprint = "AB" * 32  # 64 hex chars = SHA-256
    monkeypatch.setitem(
        http_mod.HOST_FINGERPRINTS,
        "pinned.example.gob.mx",
        (fingerprint, "2026-04-27", "https://pinned.example.gob.mx/"),
    )

    caplog.set_level(logging.INFO, logger="apps.scraper.http")
    sess = http_mod.government_session("https://pinned.example.gob.mx/")

    assert sess.verify is True
    # An adapter was mounted on https://; verify it's the pinned variant
    adapter = sess.get_adapter("https://pinned.example.gob.mx/")
    assert isinstance(adapter, http_mod._FingerprintPinnedAdapter)
    assert adapter._fingerprint == fingerprint  # already uppercase
    # Log line announces pinning
    assert any("fingerprint-pinning" in rec.getMessage() for rec in caplog.records)


def test_session_fingerprint_takes_precedence_over_insecure_list(monkeypatch):
    """If a host appears in BOTH HOST_FINGERPRINTS and INSECURE_HOSTS, pin wins."""
    fingerprint = "CD" * 32
    monkeypatch.setitem(
        http_mod.HOST_FINGERPRINTS,
        "dof.gob.mx",
        (fingerprint, "2026-04-27", "https://dof.gob.mx/"),
    )

    sess = http_mod.government_session("https://dof.gob.mx/")
    # verify must be True (fingerprint adapter takes over) — not False
    assert sess.verify is True
    adapter = sess.get_adapter("https://dof.gob.mx/")
    assert isinstance(adapter, http_mod._FingerprintPinnedAdapter)


def test_session_user_agent_set():
    sess = http_mod.government_session("https://example.com/")
    assert "Tezca" in sess.headers["User-Agent"]


# ---------------------------------------------------------------------------
# _FingerprintPinnedAdapter — adapter-level checks
# ---------------------------------------------------------------------------


def test_pinned_adapter_initializes_poolmanager_with_fingerprint():
    adapter = http_mod._FingerprintPinnedAdapter(fingerprint="ab:cd:ef")
    assert adapter._fingerprint == "ABCDEF"
    # init_poolmanager was called by HTTPAdapter.__init__; poolmanager exists
    assert adapter.poolmanager is not None
