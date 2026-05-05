"""
Centralized SSL session factory for government websites.

Many Mexican government portals have expired or misconfigured SSL certificates.
This module manages two layers of trust:

1. **Fingerprint-pinned hosts** (preferred): the host's leaf certificate is
   compared against a known SHA-256 fingerprint. Even if a CA chain would
   reject the cert, an exact-match fingerprint is treated as authoritative.
   See ``HOST_FINGERPRINTS`` for the pinned hosts and audit dates.

2. **Insecure-allowlisted hosts** (fallback): hosts in ``INSECURE_HOSTS`` get
   ``verify=False`` because their chains are too unstable to pin. Adding to
   this set requires documented justification (see SECURITY.md §"TLS
   verification on government scrapers").

Hosts not in either set get normal CA-verified TLS.

Capture a new fingerprint with::

    poetry run python scripts/utils/capture_tls_fingerprint.py <hostname>

Usage::

    from apps.scraper.http import government_session

    session = government_session("https://dof.gob.mx/some/path")
    resp = session.get("https://dof.gob.mx/some/path")
"""

from __future__ import annotations

import hashlib
import logging
import socket
import ssl
from urllib.parse import urlparse

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fingerprint-pinned hosts: leaf cert SHA-256 (uppercase hex, colon-separated)
# ---------------------------------------------------------------------------
# When a host is here, the leaf certificate is fetched at connection time and
# compared against the known fingerprint. A match is authoritative even if the
# CA chain is broken; a mismatch fails the connection (no fallback). Capture
# new fingerprints with `scripts/utils/capture_tls_fingerprint.py`.
#
# Format: { hostname: (sha256_hex, captured_iso_date, captured_by_url) }
# Review cadence: annually, or whenever a connection failure is reported.

HOST_FINGERPRINTS: dict[str, tuple[str, str, str]] = {
    # No hosts pinned yet — populated as fingerprints are captured.
    # First capture sweep is tracked in SECURITY.md §"TLS verification".
}

# ---------------------------------------------------------------------------
# Allowlist of government hosts with known SSL issues (no pinning available)
# ---------------------------------------------------------------------------
# Only these hosts have certificate verification disabled. Adding to this set
# requires documented justification — see SECURITY.md.

INSECURE_HOSTS: frozenset[str] = frozenset(
    {
        "dof.gob.mx",
        "legislacion.scjn.gob.mx",
        "www.congresobc.gob.mx",
        "congresodurango.gob.mx",
        "www.congresoqroo.gob.mx",
        "compilacion.ordenjuridico.gob.mx",
        "cnartys.conamer.gob.mx",
        "tratados.sre.gob.mx",
        "sjf.scjn.gob.mx",
        # pnt_scraper.py downloads PDFs from the Plataforma Nacional de
        # Transparencia; its certificate chain has been chronically broken.
        "consultapublica.plataformadetransparencia.org.mx",
    }
)

# Suppress the per-request InsecureRequestWarning once at import time so that
# callers no longer need their own ``urllib3.disable_warnings()`` blocks.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_USER_AGENT = "Tezca/1.0 (+https://github.com/madfam-org/tezca)"
DEFAULT_TIMEOUT = 30  # seconds


def _host_from_url(url: str) -> str:
    """Extract the hostname from *url*, lowercased."""
    return (urlparse(url).hostname or "").lower()


def _normalize_fingerprint(raw: str) -> str:
    """Strip colons + uppercase a SHA-256 fingerprint for comparison."""
    return raw.replace(":", "").replace(" ", "").upper()


def fetch_leaf_fingerprint(host: str, port: int = 443, timeout: float = 10.0) -> str:
    """Connect to *host:port* and return the leaf cert SHA-256 fingerprint.

    Returned as uppercase colon-less hex (e.g. ``"AB12...CD"``). Raises any
    socket / SSL exception on failure. Certificate-chain verification is
    *intentionally* disabled — this function exists precisely to capture the
    leaf-cert fingerprint of an untrusted (or self-signed) endpoint, which
    is then pinned via ``HOST_FINGERPRINTS`` so subsequent connections can
    be authenticated against the captured pin.

    Protocol version is still pinned to TLS 1.2+ — disabling chain
    validation does NOT mean accepting insecure transport. Connections that
    can't negotiate TLS 1.2 or higher are rejected at the TLS layer.
    """
    ctx = ssl.create_default_context()
    # Pin minimum protocol to TLS 1.2 — fingerprint capture is for chain-untrust,
    # not protocol-downgrade tolerance. Closes the CodeQL py/insecure-protocol
    # finding (CERT_NONE alone left the door open to TLS<1.2 via system default).
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            der = ssock.getpeercert(binary_form=True)
    if not der:
        raise RuntimeError(f"No leaf certificate returned by {host}:{port}")
    return hashlib.sha256(der).hexdigest().upper()


class _FingerprintPinnedAdapter(HTTPAdapter):
    """HTTPAdapter that validates leaf cert SHA-256 against an expected pin.

    Built on urllib3's ``assert_fingerprint`` — exact-match fingerprint
    overrides CA-chain validation. A mismatch raises ``SSLError`` with no
    fallback; that is the desired behavior (refuse-on-mismatch).
    """

    def __init__(self, *args, fingerprint: str, **kwargs) -> None:
        self._fingerprint = _normalize_fingerprint(fingerprint)
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["assert_fingerprint"] = self._fingerprint
        # When fingerprint-pinning, CA verification is bypassed in favor of the
        # exact-match check. This is by design: gov hosts often have broken
        # chains but stable leaf certs.
        pool_kwargs["cert_reqs"] = "CERT_NONE"
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )


def government_session(base_url: str) -> requests.Session:
    """Return a :class:`requests.Session` configured for *base_url*.

    Trust resolution order:

    1. If the host has a pinned leaf fingerprint in :data:`HOST_FINGERPRINTS`,
       a custom adapter validates the cert against that fingerprint. The
       session is otherwise behaving as if ``verify=True``.
    2. If the host is in :data:`INSECURE_HOSTS`, SSL verification is disabled
       and a warning is logged. (Fallback for hosts whose chains are too
       unstable to pin.)
    3. Otherwise, normal CA-verified TLS.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

    host = _host_from_url(base_url)

    if host in HOST_FINGERPRINTS:
        fingerprint, captured_at, _source = HOST_FINGERPRINTS[host]
        adapter = _FingerprintPinnedAdapter(fingerprint=fingerprint)
        session.mount("https://", adapter)
        session.verify = True
        logger.info(
            "TLS fingerprint-pinning active for %s (captured %s)",
            host,
            captured_at,
        )
    elif host in INSECURE_HOSTS:
        session.verify = False
        logger.warning(
            "SSL verification disabled for allowlisted host: %s "
            "(consider capturing a fingerprint — see scripts/utils/capture_tls_fingerprint.py)",
            host,
        )
    else:
        session.verify = True

    return session
