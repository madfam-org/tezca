#!/usr/bin/env python3
"""
Capture the leaf TLS certificate SHA-256 fingerprint for a host.

Use this to populate ``apps.scraper.http.HOST_FINGERPRINTS``. The captured
fingerprint pins the leaf cert so a broken CA chain no longer requires a
blanket ``verify=False`` bypass.

Usage:
    poetry run python scripts/utils/capture_tls_fingerprint.py dof.gob.mx
    poetry run python scripts/utils/capture_tls_fingerprint.py dof.gob.mx --port 443

The output prints a ready-to-paste entry. After pasting into
``HOST_FINGERPRINTS``, remove the host from ``INSECURE_HOSTS``.

Verify with::

    poetry run python -c "from apps.scraper.http import government_session; \\
        s = government_session('https://<host>/'); print(s.get('https://<host>/').status_code)"
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.scraper.http import fetch_leaf_fingerprint  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", help="Hostname (e.g. dof.gob.mx)")
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    try:
        fingerprint = fetch_leaf_fingerprint(args.host, args.port, args.timeout)
    except Exception as exc:  # noqa: BLE001 — diagnostic CLI, surface anything
        print(f"FAIL: could not capture fingerprint for {args.host}:{args.port}: {exc}")
        return 1

    today = dt.date.today().isoformat()
    source_url = f"https://{args.host}/"
    fp_pretty = ":".join(fingerprint[i : i + 2] for i in range(0, len(fingerprint), 2))

    print("OK — fingerprint captured.\n")
    print(f"  host         : {args.host}")
    print(f"  fingerprint  : {fp_pretty}")
    print(f"  captured_at  : {today}\n")
    print("Add to apps/scraper/http.py:HOST_FINGERPRINTS:\n")
    print(
        f'    "{args.host}": (\n'
        f'        "{fingerprint}",\n'
        f'        "{today}",\n'
        f'        "{source_url}",\n'
        f"    ),"
    )
    print(
        "\nThen remove the host from INSECURE_HOSTS (if present) so the "
        "fingerprint path takes precedence."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
