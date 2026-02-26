"""
Centralized SSL-bypass session factory for government websites.

Many Mexican government portals have expired or misconfigured SSL certificates.
This module provides a single place to manage SSL bypass decisions, keeping an
explicit allowlist of known-problematic hosts instead of scattering
``verify=False`` throughout the codebase.

Usage::

    from apps.scraper.http import government_session

    session = government_session("https://dof.gob.mx/some/path")
    resp = session.get("https://dof.gob.mx/some/path")
"""

import logging
from urllib.parse import urlparse

import requests
import urllib3

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowlist of government hosts with known SSL issues.
# Only these hosts will have certificate verification disabled.
# ---------------------------------------------------------------------------

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
    return urlparse(url).hostname or ""


def government_session(base_url: str) -> requests.Session:
    """Return a :class:`requests.Session` configured for *base_url*.

    If the host portion of *base_url* is in :data:`INSECURE_HOSTS`, SSL
    certificate verification is disabled on the returned session and a
    warning is logged.  Otherwise the session uses normal (verified) TLS.

    The session is pre-configured with a reasonable ``User-Agent`` header
    and a default timeout adapter is **not** injected (callers should pass
    ``timeout=`` on each request or rely on the library default).  The
    ``DEFAULT_TIMEOUT`` constant is exported for convenience.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

    host = _host_from_url(base_url)

    if host in INSECURE_HOSTS:
        session.verify = False
        logger.warning("SSL verification disabled for allowlisted host: %s", host)
    else:
        session.verify = True

    return session
