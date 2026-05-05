#!/usr/bin/env python3
"""
check-networkpolicy-ports.py — CI lint preventing NetworkPolicy/pod port drift.

THE BUG THIS PREVENTS
=====================
On 2026-05-04, status.enclii.dev had four outages caused by an
`allow-cloudflared-ingress` NetworkPolicy whose `ports:` block listed port 80
while the pods it selected actually exposed containerPort=8000 (karafiel-api)
and containerPort=3050 (karafiel-web). Cloudflared connected to the pod IP on
the right port, but the CNI silently dropped the traffic because the
NetworkPolicy only permitted port 80. Symptom: 100% packet loss with no log
entries. Diagnosis: hours.

The class of bug: **a NetworkPolicy `ports:` clause that does not intersect
the `containerPorts` of the pods selected by `podSelector`**. The fix at the
incident level is to drop the `ports:` field entirely on cloudflared-targeting
policies — cloudflared is the trust boundary, the per-port restriction adds
no security and one more failure mode. This lint enforces that whenever
`ports:` IS present, every listed port must actually exist on the selected
pods.

WHAT IT CHECKS
==============
For each NetworkPolicy in the given roots:
  1. Resolve `spec.podSelector` → matching Deployments/StatefulSets/DaemonSets
     in the same namespace (matchLabels + matchExpressions both supported).
  2. Collect `containerPorts` (numeric and named) from those workloads.
  3. For each *ingress* rule with a `ports:` block, verify at least one
     listed port (numeric or named) intersects the selected pods' container
     ports. Egress is intentionally NOT checked — egress `ports:` describe
     the destination port (DNS=53, HTTPS=443, etc.), which has no
     relationship to the source pod's containerPorts.
  4. FAIL with a precise, file-anchored error if NONE of the listed ports
     intersects the pods' containerPorts (the exact bug class — extras are
     harmless, but a complete miss drops all traffic).

Skipped:
  - NetworkPolicies whose rules omit `ports:` (allow-all from the trust
    boundary — the preferred pattern).
  - NetworkPolicies whose podSelector matches no in-scope workload (warned,
    not failed — could legitimately target external/cross-repo pods).

USAGE
=====
    python3 scripts/check-networkpolicy-ports.py infra/k8s/
    python3 scripts/check-networkpolicy-ports.py infra/k8s/ infra/argocd/

Exit codes:
  0 — all checks passed (or only warnings)
  1 — at least one port mismatch detected
  2 — could not parse manifests (YAML error, missing dir, etc.)

This script is intentionally dependency-light (PyYAML only) so it can be
copied into any ecosystem repo's `scripts/` directory and wired into that
repo's CI verbatim.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

try:
    import yaml
except ImportError:  # pragma: no cover
    print("error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job", "CronJob"}


@dataclass
class Workload:
    """A pod-producing resource (Deployment et al.) we can match against."""

    file: str
    name: str
    namespace: str
    labels: dict[str, str]
    container_ports: set[int] = field(default_factory=set)
    named_ports: set[str] = field(default_factory=set)


@dataclass
class Finding:
    severity: str  # "fail" | "warn"
    file: str
    message: str

    def render(self) -> str:
        prefix = "FAIL" if self.severity == "fail" else "WARN"
        return f"[{prefix}] {self.file}: {self.message}"


def iter_yaml_docs(root: Path) -> Iterator[tuple[Path, dict]]:
    """Yield (path, doc) for every YAML doc under root. Skips non-YAML files."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in {".yaml", ".yml"}:
            continue
        try:
            with path.open("r", encoding="utf-8") as fh:
                for doc in yaml.safe_load_all(fh):
                    if isinstance(doc, dict):
                        yield path, doc
        except yaml.YAMLError as exc:
            print(f"error: cannot parse {path}: {exc}", file=sys.stderr)
            raise


def extract_workload(path: Path, doc: dict) -> Workload | None:
    if doc.get("kind") not in WORKLOAD_KINDS:
        return None
    meta = doc.get("metadata") or {}
    name = meta.get("name", "<unnamed>")
    namespace = meta.get("namespace", "default")

    # CronJob nests one level deeper: spec.jobTemplate.spec.template
    if doc["kind"] == "CronJob":
        template = (
            ((doc.get("spec") or {}).get("jobTemplate") or {})
            .get("spec", {})
            .get("template", {})
        )
    else:
        template = (doc.get("spec") or {}).get("template") or {}

    pod_meta = template.get("metadata") or {}
    labels = pod_meta.get("labels") or {}
    pod_spec = template.get("spec") or {}

    workload = Workload(file=str(path), name=name, namespace=namespace, labels=dict(labels))

    for container in (pod_spec.get("containers") or []):
        for port in (container.get("ports") or []):
            cp = port.get("containerPort")
            if isinstance(cp, int):
                workload.container_ports.add(cp)
            named = port.get("name")
            if isinstance(named, str) and named:
                workload.named_ports.add(named)

    return workload


def selector_matches(selector: dict, labels: dict[str, str]) -> bool:
    """Mimic Kubernetes label-selector semantics for matchLabels + matchExpressions."""
    if not selector:
        # An empty selector matches every pod in the namespace.
        return True

    match_labels = selector.get("matchLabels") or {}
    for key, want in match_labels.items():
        if labels.get(key) != want:
            return False

    for expr in selector.get("matchExpressions") or []:
        key = expr.get("key")
        operator = expr.get("operator")
        values = expr.get("values") or []
        actual = labels.get(key)
        if operator == "In":
            if actual not in values:
                return False
        elif operator == "NotIn":
            if actual in values:
                return False
        elif operator == "Exists":
            if key not in labels:
                return False
        elif operator == "DoesNotExist":
            if key in labels:
                return False
        else:
            # Unknown operator — be conservative and refuse to match.
            return False

    return True


def find_selected_workloads(
    np_namespace: str, pod_selector: dict, workloads: Iterable[Workload]
) -> list[Workload]:
    return [
        w
        for w in workloads
        if w.namespace == np_namespace and selector_matches(pod_selector, w.labels)
    ]


def classify_rule_ports(
    rule_ports: list[dict], allowed_numeric: set[int], allowed_named: set[str]
) -> tuple[list[str], list[str]]:
    """Split rule ports into (matching, non_matching) descriptors.

    Returns:
      matching: human-readable descriptors that DO intersect the pods' container
        ports — at least one of these means the rule is functional.
      non_matching: descriptors that do NOT match — informational only when
        `matching` is non-empty (extras are harmless), but if `matching` is
        empty and `non_matching` is non-empty, every byte gets dropped — that's
        the bug.
    """
    matching: list[str] = []
    non_matching: list[str] = []
    for entry in rule_ports or []:
        port = entry.get("port")
        if isinstance(port, int):
            (matching if port in allowed_numeric else non_matching).append(str(port))
        elif isinstance(port, str):
            # Named port OR stringified integer (yes, k8s allows both).
            if port.isdigit():
                p = int(port)
                (matching if p in allowed_numeric else non_matching).append(port)
            else:
                target = matching if port in allowed_named else non_matching
                target.append(f"'{port}' (named)")
        # Missing/unknown port type: skip — protocol-only entries are fine.
    return matching, non_matching


def check_networkpolicy(np_doc: dict, np_path: Path, workloads: list[Workload]) -> list[Finding]:
    findings: list[Finding] = []
    meta = np_doc.get("metadata") or {}
    np_name = meta.get("name", "<unnamed>")
    np_namespace = meta.get("namespace", "default")

    spec = np_doc.get("spec") or {}
    pod_selector = spec.get("podSelector") or {}

    selected = find_selected_workloads(np_namespace, pod_selector, workloads)
    if not selected:
        # Nothing in scope — surface a hint, but don't fail. The selector
        # might legitimately target a workload defined elsewhere (other repo,
        # operator-managed CRD output, etc.).
        selector_repr = pod_selector.get("matchLabels") or pod_selector.get(
            "matchExpressions"
        ) or "(empty)"
        findings.append(
            Finding(
                severity="warn",
                file=str(np_path),
                message=(
                    f"NetworkPolicy '{np_name}' (ns={np_namespace}) selector "
                    f"{selector_repr} matches no in-scope Deployment/StatefulSet/"
                    "DaemonSet/CronJob — port consistency cannot be verified."
                ),
            )
        )
        return findings

    allowed_numeric: set[int] = set()
    allowed_named: set[str] = set()
    for w in selected:
        allowed_numeric |= w.container_ports
        allowed_named |= w.named_ports

    selector_label = (
        pod_selector.get("matchLabels")
        or pod_selector.get("matchExpressions")
        or "(empty)"
    )

    def check_direction(direction: str, rules: list[dict]) -> None:
        for rule in rules or []:
            ports = rule.get("ports")
            if not ports:
                # Allow-all on this rule from the trust boundary — the preferred
                # pattern. The bug only happens when ports IS specified.
                continue
            matching, non_matching = classify_rule_ports(
                ports, allowed_numeric, allowed_named
            )
            if matching:
                # At least one listed port intersects the pods' container
                # ports — traffic on that port works. Extras are harmless.
                continue
            if not non_matching:
                # Only protocol-only entries; nothing to validate.
                continue
            allowed_repr = sorted(allowed_numeric) + sorted(allowed_named)
            findings.append(
                Finding(
                    severity="fail",
                    file=str(np_path),
                    message=(
                        f"NetworkPolicy '{np_name}' (ns={np_namespace}) "
                        f"{direction} allows port(s) {non_matching} but pods "
                        f"labeled {selector_label} only expose containerPorts "
                        f"{allowed_repr} — NO listed port matches, so all "
                        "traffic via this rule is silently dropped at the CNI. "
                        "Either remove the `ports` restriction (cloudflared is "
                        "the trust boundary) or use a port that matches the pod."
                    ),
                )
            )

    # NOTE: We only check ingress. An ingress rule's `ports:` block restricts
    # which of the *pod's own* listening ports may receive traffic — that's
    # the exact failure mode of the 2026-05-04 outage. An egress rule's
    # `ports:` block restricts the *destination* port the pod connects to
    # (e.g. DNS=53, HTTPS=443) which has no relationship to the pod's
    # containerPorts, so cross-checking egress would produce false positives.
    check_direction("ingress", spec.get("ingress") or [])

    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: check-networkpolicy-ports.py <root> [<root> ...]", file=sys.stderr)
        return 2

    roots = [Path(p) for p in argv[1:]]
    for root in roots:
        if not root.exists():
            print(f"error: root does not exist: {root}", file=sys.stderr)
            return 2

    workloads: list[Workload] = []
    network_policies: list[tuple[Path, dict]] = []

    try:
        for root in roots:
            for path, doc in iter_yaml_docs(root):
                kind = doc.get("kind")
                if kind in WORKLOAD_KINDS:
                    w = extract_workload(path, doc)
                    if w is not None:
                        workloads.append(w)
                elif kind == "NetworkPolicy":
                    network_policies.append((path, doc))
    except yaml.YAMLError:
        return 2

    all_findings: list[Finding] = []
    for path, np in network_policies:
        all_findings.extend(check_networkpolicy(np, path, workloads))

    fails = [f for f in all_findings if f.severity == "fail"]
    warns = [f for f in all_findings if f.severity == "warn"]

    for f in all_findings:
        print(f.render())

    print()
    print(
        f"checked {len(network_policies)} NetworkPolicy doc(s) "
        f"against {len(workloads)} workload(s) in {len(roots)} root(s); "
        f"{len(fails)} failure(s), {len(warns)} warning(s)."
    )

    if fails:
        print(
            "FAIL: NetworkPolicy port consistency check failed. See messages above.",
            file=sys.stderr,
        )
        return 1
    print("OK: NetworkPolicy port consistency check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
