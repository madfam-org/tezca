"""Prometheus metrics: request instrumentation and the private :9464 listener.

Four layers, cheapest first:

* the request middleware records ``http_requests_total`` and
  ``http_request_duration_seconds`` by method, route pattern and status;
* the public Django app serves NO metrics route, whatever the Host or headers;
* ``apps.api.metrics_server`` answers ``GET /metrics`` and nothing else;
* end to end under real gunicorn with two workers and the repo's config file:
  the master serves the SUM of both workers' samples on the metrics port
  (prometheus_client multiprocess mode) and the API port still has no metrics.
"""

import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from django.test import Client, RequestFactory
from django.urls import resolve
from prometheus_client import REGISTRY, CollectorRegistry, Counter
from prometheus_client.parser import text_string_to_metric_families

from apps.api import metrics_server
from apps.api.middleware.request_metrics import (
    UNMATCHED_ROUTE,
    RequestMetricsMiddleware,
    _method_label,
    _route_label,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
POD_HOST = "10.42.1.2:9464"


def _count(route, code, method="GET"):
    value = REGISTRY.get_sample_value(
        "http_requests_total", {"method": method, "route": route, "code": code}
    )
    return value or 0.0


def _observations(route, method="GET"):
    value = REGISTRY.get_sample_value(
        "http_request_duration_seconds_count", {"method": method, "route": route}
    )
    return value or 0.0


@pytest.fixture
def client(settings):
    # "*" so a 404 below can never be Django's own Host validation (a 400).
    settings.ALLOWED_HOSTS = ["*"]
    return Client()


def _get(url, host=None, method="GET"):
    request = urllib.request.Request(url, method=method)
    if host:
        request.add_header("Host", host)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, dict(response.headers), response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read().decode()


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


# ── Request middleware ──────────────────────────────────────────────────


class TestRequestMetrics:
    def test_counts_and_times_a_request_by_route_and_code(self, client):
        before = _count("health", "200")
        observed = _observations("health")

        response = client.get("/health", HTTP_HOST="api.tezca.mx")

        assert response.status_code == 200
        assert _count("health", "200") == before + 1
        assert _observations("health") == observed + 1

    def test_unrouted_path_is_labelled_unmatched(self, client):
        before = _count(UNMATCHED_ROUTE, "404")
        response = client.get("/no-such-route/12345", HTTP_HOST="api.tezca.mx")
        assert response.status_code == 404
        assert _count(UNMATCHED_ROUTE, "404") == before + 1

    def test_route_is_the_pattern_not_the_raw_path(self):
        request = RequestFactory().get("/api/v1/laws/cpeum/")
        request.resolver_match = resolve("/api/v1/laws/cpeum/")
        assert _route_label(request) == "api/v1/laws/<str:law_id>/"

    def test_unknown_methods_share_one_label(self):
        assert _method_label("get") == "GET"
        assert _method_label("BREW") == "OTHER"
        assert _method_label(None) == "OTHER"

    def test_an_exception_is_counted_as_a_500(self):
        def explode(request):
            raise RuntimeError("boom")

        middleware = RequestMetricsMiddleware(explode)
        before = _count(UNMATCHED_ROUTE, "500", method="POST")
        with pytest.raises(RuntimeError):
            middleware(RequestFactory().post("/api/v1/whatever/"))
        assert _count(UNMATCHED_ROUTE, "500", method="POST") == before + 1


# ── The public app ──────────────────────────────────────────────────────


class TestPublicAppServesNoMetrics:
    @pytest.mark.parametrize("path", ["/metrics", "/metrics/", "/api/v1/metrics"])
    def test_public_host_gets_404(self, client, path):
        response = client.get(path, HTTP_HOST="api.tezca.mx")
        assert response.status_code == 404
        assert b"# TYPE" not in response.content

    def test_cloudflare_request_gets_404(self, client):
        response = client.get(
            "/metrics", HTTP_HOST="api.tezca.mx", HTTP_CF_CONNECTING_IP="203.0.113.7"
        )
        assert response.status_code == 404
        assert b"# TYPE" not in response.content

    def test_even_a_pod_ip_host_gets_404_on_the_api_port(self, client):
        response = client.get("/metrics", HTTP_HOST="10.42.1.2:8000")
        assert response.status_code == 404
        assert b"# TYPE" not in response.content


# ── The metrics listener ────────────────────────────────────────────────


@pytest.fixture
def listener():
    registry = CollectorRegistry()
    counter = Counter("tezca_test_total", "A test counter.", registry=registry)
    counter.inc(3)
    server = metrics_server.start_metrics_server(0, registry, addr="127.0.0.1")
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


class TestMetricsListener:
    def test_scraper_request_gets_exposition(self, listener):
        status, headers, body = _get(listener + "/metrics", host=POD_HOST)
        assert status == 200
        assert headers["Content-Type"].startswith("text/plain")
        assert "# TYPE tezca_test_total counter" in body
        assert "tezca_test_total 3.0" in body

    @pytest.mark.parametrize("path", ["/", "/metrics/", "/metrics/extra", "/health"])
    def test_every_other_path_is_404(self, listener, path):
        status, _, body = _get(listener + path, host=POD_HOST)
        assert status == 404
        assert "# TYPE" not in body

    def test_only_get(self, listener):
        status, headers, _ = _get(listener + "/metrics", host=POD_HOST, method="POST")
        assert status == 405
        assert headers["Allow"] == "GET"


class TestResolveMetricsPort:
    def test_defaults_to_9464(self):
        assert metrics_server.resolve_metrics_port({}) == 9464
        assert metrics_server.DEFAULT_METRICS_PORT == 9464

    def test_reads_env(self):
        assert metrics_server.resolve_metrics_port({"METRICS_PORT": "9100"}) == 9100

    @pytest.mark.parametrize("value", ["abc", "0", "70000", "94.64"])
    def test_rejects_non_ports(self, value):
        with pytest.raises(ValueError, match="METRICS_PORT must be a TCP port"):
            metrics_server.resolve_metrics_port({"METRICS_PORT": value})

    def test_refuses_the_api_port(self):
        with pytest.raises(ValueError, match="must differ from the API port"):
            metrics_server.resolve_metrics_port({"METRICS_PORT": "8000"})


def test_reset_multiproc_dir_removes_only_db_files(tmp_path):
    (tmp_path / "counter_123.db").write_bytes(b"x")
    (tmp_path / "keep.txt").write_text("x")
    metrics_server.reset_multiproc_dir(str(tmp_path))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["keep.txt"]


# ── End to end under gunicorn ───────────────────────────────────────────


def _wait_for(url, deadline):
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except urllib.error.HTTPError:
            return
        except OSError:
            time.sleep(0.2)
    raise AssertionError(f"{url} did not come up")


def _samples(body, name):
    for family in text_string_to_metric_families(body):
        for sample in family.samples:
            if sample.name == name:
                yield sample


@pytest.fixture(scope="module")
def gunicorn_api(tmp_path_factory):
    api_port, metrics_port = _free_port(), _free_port()
    env = {
        **os.environ,
        "METRICS_PORT": str(metrics_port),
        "PROMETHEUS_MULTIPROC_DIR": str(tmp_path_factory.mktemp("multiproc")),
        "DEBUG": "True",
        "ALLOWED_HOSTS": "*",
        "DB_ENGINE": "django.db.backends.sqlite3",
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "gunicorn",
            "apps.indigo.wsgi:application",
            "--config",
            "apps/indigo/gunicorn.conf.py",
            "--bind",
            f"127.0.0.1:{api_port}",
            "--workers",
            "2",
            "--worker-class",
            "gthread",
            "--threads",
            "2",
        ],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.monotonic() + 60
        _wait_for(f"http://127.0.0.1:{api_port}/health", deadline)
        _wait_for(f"http://127.0.0.1:{metrics_port}/metrics", deadline)
        yield f"http://127.0.0.1:{api_port}", f"http://127.0.0.1:{metrics_port}"
    finally:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


class TestUnderGunicorn:
    @staticmethod
    def _health_series(metrics):
        status, _, body = _get(metrics + "/metrics", host=POD_HOST)
        assert status == 200
        served = [
            s
            for s in _samples(body, "http_requests_total")
            if s.labels == {"method": "GET", "route": "health", "code": "200"}
        ]
        return served, body

    def test_master_serves_the_sum_of_all_workers(self, gunicorn_api):
        api, metrics = gunicorn_api
        # The readiness wait already sent at least one /health request.
        before, _ = self._health_series(metrics)
        assert len(before) == 1

        requests = 20
        for _ in range(requests):
            status, _, _ = _get(api + "/health", host="api.tezca.mx")
            assert status == 200

        after, body = self._health_series(metrics)
        # One aggregated series, not one per worker, and it counts every
        # request whichever worker served it.
        assert len(after) == 1
        assert after[0].value - before[0].value == requests
        assert any(_samples(body, "http_request_duration_seconds_bucket"))
        assert any(_samples(body, "python_info"))

    def test_api_port_still_serves_no_metrics(self, gunicorn_api):
        api, _ = gunicorn_api
        for path in ("/metrics", "/metrics/"):
            status, _, body = _get(api + path, host="api.tezca.mx")
            assert status == 404
            assert "# TYPE" not in body
