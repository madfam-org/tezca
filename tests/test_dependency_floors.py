"""Security floors for locked dependencies (see SECURITY.md, "Security baseline").

On 2026-09-30 two fixes landed together: next 16.3.8 for GHSA-vcvr-r3jv-pc5j
(a critical RCE in ``next/og`` ImageResponse; ``/leyes/[id]/opengraph-image``
is a dynamic ``next/og`` route) in #258, and axios 1.20.0, PyJWT 2.15.1 and
urllib3 2.8.0 in #259.

``pip-audit`` and ``npm audit`` already run in CI, but as separate "Security
audit" steps, and #258 had to merge with exactly those steps red. This test
puts the floors inside the backend test job itself, so a lockfile regeneration
that drifts any of them back below the patched version fails as an ordinary
test, independent of the advisory databases.

Raise a floor here in the same change that raises it in pyproject.toml or the
lockfile. Never lower one to make this pass.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest
from packaging.version import Version

ROOT = Path(__file__).resolve().parent.parent

PYTHON_FLOORS = {
    "pyjwt": "2.15.1",
    "urllib3": "2.8.0",
}

NODE_FLOORS = {
    "next": "16.3.8",
    "axios": "1.20.0",
}


def _poetry_locked() -> dict[str, str]:
    data = tomllib.loads((ROOT / "poetry.lock").read_text())
    return {pkg["name"].lower(): pkg["version"] for pkg in data["package"]}


def _npm_locked(name: str) -> list[tuple[str, str]]:
    """Every resolved copy of ``name`` in package-lock.json (hoisted or nested)."""
    packages = json.loads((ROOT / "package-lock.json").read_text())["packages"]
    suffix = f"node_modules/{name}"
    return [
        (path, meta["version"])
        for path, meta in packages.items()
        if (path == suffix or path.endswith("/" + suffix)) and "version" in meta
    ]


@pytest.mark.parametrize("name,floor", sorted(PYTHON_FLOORS.items()))
def test_poetry_lock_meets_security_floor(name, floor):
    locked = _poetry_locked()
    assert name in locked, f"{name} is no longer in poetry.lock; update this test"
    assert Version(locked[name]) >= Version(
        floor
    ), f"poetry.lock resolves {name} {locked[name]}, below the security floor {floor}"


@pytest.mark.parametrize("name,floor", sorted(PYTHON_FLOORS.items()))
def test_pyproject_declares_the_floor(name, floor):
    """The floor lives in pyproject.toml too, so a fresh lock cannot undercut it."""
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["poetry"][
        "dependencies"
    ]
    spec = next(v for k, v in deps.items() if k.lower() == name)
    if isinstance(spec, dict):
        spec = spec["version"]
    match = re.search(r"(?:\^|>=)\s*([0-9][0-9.]*)", spec)
    assert match, f"{name} constraint {spec!r} has no lower bound"
    assert Version(match.group(1)) >= Version(
        floor
    ), f"pyproject.toml lets {name} resolve below {floor} ({spec!r})"


@pytest.mark.parametrize("name,floor", sorted(NODE_FLOORS.items()))
def test_package_lock_meets_security_floor(name, floor):
    copies = _npm_locked(name)
    assert copies, f"{name} is no longer in package-lock.json; update this test"
    below = [(path, ver) for path, ver in copies if Version(ver) < Version(floor)]
    assert not below, f"package-lock.json resolves {name} below {floor}: {below}"
