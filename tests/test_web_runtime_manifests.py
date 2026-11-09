"""Runtime guards for the tezca-web and tezca-admin Deployments.

tezca-web OOM-restarted every 20-46 h in 2026-11 (V8 "Ineffective
mark-compacts near heap limit"). The cause was a per-request leak: the Janua
SDK started a never-cleared 60 s interval for every server render of
``<JanuaProvider>``. That is fixed in ``apps/web/lib/janua-config.ts`` (and the
admin copy). These tests pin the defence-in-depth settings that shipped with
the fix, so they stay coherent with each container's memory limit:

- ``NODE_OPTIONS=--max-old-space-size`` is set, at 55-70% of the limit (the
  rest is native memory: code, new space, buffers, sockets);
- every HTTP probe allows at least 3 s (a 1 s default can fail during a major
  GC pause);
- the Enclii service specs in ``deployment/enclii/`` mirror the same cap.

Pure YAML reads: no Django, no cluster.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
K8S = ROOT / "k8s" / "production"
ENCLII = ROOT / "deployment" / "enclii"

APPS = {
    # app: (k8s manifest, enclii spec)
    "tezca-web": (K8S / "tezca-web-deployment.yaml", ENCLII / "tezca-web.yaml"),
    "tezca-admin": (K8S / "tezca-admin-deployment.yaml", ENCLII / "tezca-admin.yaml"),
}

UNITS_MIB = {"Mi": 1, "Gi": 1024}
MIN_RATIO = 0.55
MAX_RATIO = 0.70
MIN_PROBE_TIMEOUT_S = 3


def _limit_mib(raw: str) -> int:
    m = re.fullmatch(r"(\d+)(Mi|Gi)", str(raw))
    assert m, f"unexpected memory limit format: {raw!r}"
    return int(m.group(1)) * UNITS_MIB[m.group(2)]


def old_space_mib(node_options: str | None) -> int:
    """The --max-old-space-size value in a NODE_OPTIONS string, in MiB."""
    m = re.search(r"--max-old-space-size=(\d+)\b", node_options or "")
    assert m, f"NODE_OPTIONS lacks --max-old-space-size: {node_options!r}"
    return int(m.group(1))


def _container(app: str) -> dict:
    manifest = yaml.safe_load(APPS[app][0].read_text())
    assert manifest["kind"] == "Deployment"
    return manifest["spec"]["template"]["spec"]["containers"][0]


def _env(entries: list[dict]) -> dict[str, str | None]:
    return {e["name"]: e.get("value") for e in entries}


@pytest.mark.parametrize("app", sorted(APPS))
def test_heap_cap_is_set_and_proportionate(app: str) -> None:
    container = _container(app)
    limit = _limit_mib(container["resources"]["limits"]["memory"])
    cap = old_space_mib(_env(container["env"]).get("NODE_OPTIONS"))
    assert MIN_RATIO * limit <= cap <= MAX_RATIO * limit, (
        f"{app}: heap cap {cap} MiB is outside {MIN_RATIO:.0%}-{MAX_RATIO:.0%} "
        f"of the {limit} MiB limit; leave room for native memory"
    )


@pytest.mark.parametrize("app", sorted(APPS))
def test_probes_tolerate_a_gc_pause(app: str) -> None:
    container = _container(app)
    probes = [
        container.get(k) for k in ("livenessProbe", "readinessProbe", "startupProbe")
    ]
    probes = [p for p in probes if p]
    assert probes, f"{app}: no probes"
    for probe in probes:
        # Kubernetes defaults timeoutSeconds to 1 when it is absent.
        assert probe.get("timeoutSeconds", 1) >= MIN_PROBE_TIMEOUT_S, f"{app}: {probe}"


@pytest.mark.parametrize("app", sorted(APPS))
def test_enclii_spec_mirrors_the_heap_cap(app: str) -> None:
    k8s_cap = old_space_mib(_env(_container(app)["env"]).get("NODE_OPTIONS"))
    spec = yaml.safe_load(APPS[app][1].read_text())
    assert spec["service"] == app
    assert _limit_mib(spec["resources"]["limits"]["memory"]) == _limit_mib(
        _container(app)["resources"]["limits"]["memory"]
    ), f"{app}: enclii and k8s memory limits differ"
    assert old_space_mib(_env(spec["env"]).get("NODE_OPTIONS")) == k8s_cap


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("--max-old-space-size=320", 320),
        ("--enable-source-maps --max-old-space-size=160", 160),
    ],
)
def test_old_space_parser(raw: str, expected: int) -> None:
    assert old_space_mib(raw) == expected


@pytest.mark.parametrize(
    "raw", [None, "", "--enable-source-maps", "--max-old-space-size="]
)
def test_old_space_parser_rejects_a_missing_cap(raw: str | None) -> None:
    with pytest.raises(AssertionError):
        old_space_mib(raw)


def test_limit_parser_rejects_unknown_units() -> None:
    assert _limit_mib("1Gi") == 1024
    with pytest.raises(AssertionError):
        _limit_mib("512M")
