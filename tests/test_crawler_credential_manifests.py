"""Guards for tezca's per-caller madfam-crawler key.

The crawler verifies the key tezca's worker sends, so the crawler owns the one
canonical copy (Vault ``secret/madfam-crawler``, property ``api_key_tezca``).
tezca reads that property cross-path into its own Secret,
``tezca-crawler-credentials``, and keeps no copy of its own.

Pure YAML reads: no Django, no cluster.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
K8S = ROOT / "k8s" / "production"
SECRET_NAME = "tezca-crawler-credentials"


def _load(name: str) -> dict:
    doc = yaml.safe_load((K8S / name).read_text())
    assert isinstance(doc, dict), name
    return doc


def test_crawler_credentials_external_secret_is_wired():
    resources = _load("kustomization.yaml")["resources"]
    assert "external-secret-crawler-credentials.yaml" in resources


def test_crawler_credentials_read_the_crawler_owned_per_caller_key():
    doc = _load("external-secret-crawler-credentials.yaml")
    assert doc["kind"] == "ExternalSecret"
    assert doc["metadata"]["name"] == SECRET_NAME
    # Created before the worker rolls (its env reference is read at start).
    assert doc["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "-1"
    spec = doc["spec"]
    assert spec["secretStoreRef"] == {
        "name": "vault-store",
        "kind": "ClusterSecretStore",
    }
    assert spec["target"]["name"] == SECRET_NAME
    assert spec["target"]["creationPolicy"] == "Owner"
    assert "dataFrom" not in spec
    (entry,) = spec["data"]
    assert entry == {
        "secretKey": "MADFAM_CRAWLER_TOKEN",
        "remoteRef": {"key": "secret/madfam-crawler", "property": "api_key_tezca"},
    }


def test_worker_reads_the_token_optionally_from_its_own_secret():
    doc = _load("tezca-worker-deployment.yaml")
    (container,) = doc["spec"]["template"]["spec"]["containers"]
    env = {item["name"]: item for item in container["env"]}
    assert env["MADFAM_CRAWLER_TOKEN"]["valueFrom"]["secretKeyRef"] == {
        "name": SECRET_NAME,
        "key": "MADFAM_CRAWLER_TOKEN",
        "optional": True,
    }


def test_no_other_workload_reads_a_crawler_token_copy():
    for path in sorted(K8S.glob("*.yaml")):
        for doc in yaml.safe_load_all(path.read_text()):
            if not doc or doc.get("kind") not in ("Deployment", "CronJob"):
                continue
            text = yaml.safe_dump(doc)
            if "MADFAM_CRAWLER_TOKEN" in text:
                assert doc["metadata"]["name"] == "tezca-worker", path.name
