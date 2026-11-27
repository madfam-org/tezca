"""Guards for tezca-web's in-cluster API URL (``INTERNAL_API_URL``).

``/sitemap.xml`` reads the whole law list server-side through
``INTERNAL_API_URL`` (``apps/web/lib/config.ts``). Without it the web pod read
the public host, through the edge and back; 2026-11-27 that read answered 429
and ``/sitemap.xml`` answered 500 on every request. These tests keep the URL
pointed at a target that actually answers:

- it names the ``tezca-api`` Service, in the namespace the kustomization
  deploys to, on a port that Service exposes;
- its host is in tezca-api's ``ALLOWED_HOSTS`` (otherwise Django answers 400
  DisallowedHost);
- web → api inside the namespace stays admitted by ``allow-intra-namespace``
  (both directions are isolated by the other policies in the file);
- the Enclii spec mirrors the value.

Pure YAML reads: no Django, no cluster.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
K8S = ROOT / "k8s" / "production"
ENCLII = ROOT / "deployment" / "enclii"


def _docs(path: Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _env(path: Path) -> dict[str, str | None]:
    manifest = _docs(path)[0]
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    return {e["name"]: e.get("value") for e in container["env"]}


def _internal_api_url() -> str:
    url = _env(K8S / "tezca-web-deployment.yaml").get("INTERNAL_API_URL")
    assert url, "tezca-web must set INTERNAL_API_URL to the in-cluster API"
    return url


def test_internal_api_url_targets_the_api_service() -> None:
    parts = urlsplit(_internal_api_url())
    namespace = yaml.safe_load((K8S / "kustomization.yaml").read_text())["namespace"]
    service = _docs(K8S / "tezca-api-service.yaml")[0]

    assert parts.scheme == "http"
    assert (
        parts.hostname == f"{service['metadata']['name']}.{namespace}.svc.cluster.local"
    )
    assert parts.port in {p["port"] for p in service["spec"]["ports"]}
    assert parts.path.rstrip("/") == "/api/v1"


def test_internal_api_host_is_allowed_by_the_api() -> None:
    host = urlsplit(_internal_api_url()).hostname
    allowed = _env(K8S / "tezca-api-deployment.yaml")["ALLOWED_HOSTS"] or ""
    assert host in allowed.split(","), f"{host} missing from tezca-api ALLOWED_HOSTS"


def test_web_to_api_traffic_stays_admitted() -> None:
    policies = {d["metadata"]["name"]: d for d in _docs(K8S / "network-policies.yaml")}
    intra = policies["allow-intra-namespace"]["spec"]
    assert intra["podSelector"]["matchLabels"] == {"app.kubernetes.io/part-of": "tezca"}
    assert {"from": [{"podSelector": {}}]} in intra["ingress"]
    assert {"to": [{"podSelector": {}}]} in intra["egress"]

    for name in ("tezca-web-deployment.yaml", "tezca-api-deployment.yaml"):
        labels = _docs(K8S / name)[0]["spec"]["template"]["metadata"]["labels"]
        assert labels.get("app.kubernetes.io/part-of") == "tezca", name


def test_enclii_spec_mirrors_internal_api_url() -> None:
    spec = yaml.safe_load((ENCLII / "tezca-web.yaml").read_text())
    env = {e["name"]: e.get("value") for e in spec["env"]}
    assert env.get("INTERNAL_API_URL") == _internal_api_url()
