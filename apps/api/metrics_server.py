"""Prometheus metrics on a dedicated listener, apart from the public API.

The Cloudflare tunnel routes all of ``api.tezca.mx`` to the API port 8000, so a
metrics route on the Django app would be a public route. This listener binds
its own port (``METRICS_PORT``, default 9464), which only the Service's
``metrics`` port and the ``allow-monitoring-ingress`` NetworkPolicy expose, to
the ``monitoring`` namespace. The tunnel never reaches it.

It answers ``GET /metrics`` and nothing else: every other path is a 404 and
every other method on ``/metrics`` a 405.

Under gunicorn (``apps/indigo/gunicorn.conf.py``) the listener runs in the
master process, started from the ``when_ready`` hook, and serves
:func:`multiprocess_registry`: the workers write their samples to
``PROMETHEUS_MULTIPROC_DIR`` and ``MultiProcessCollector`` sums them at scrape
time. That is the prometheus_client multiprocess mode; a listener inside a
single worker would report a quarter of the traffic, from whichever worker
bound the port.

This module must not import Django or anything under ``apps.indigo``: the
gunicorn master imports it before forking, and ``apps.indigo`` would pull in
Celery. prometheus_client decides multiprocess mode when it is first imported,
so ``PROMETHEUS_MULTIPROC_DIR`` must be set before this module is imported.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from prometheus_client import (
    CollectorRegistry,
    PlatformCollector,
    ProcessCollector,
    make_wsgi_app,
    multiprocess,
)

METRICS_PATH = "/metrics"
DEFAULT_METRICS_PORT = 9464
# The public API port (gunicorn bind in apps/indigo/Dockerfile).
API_PORT = 8000


def resolve_metrics_port(env: dict | None = None) -> int:
    """The port from ``METRICS_PORT``, or :data:`DEFAULT_METRICS_PORT` when unset.

    Raises ``ValueError`` on anything that is not a TCP port, or on the API's
    own port: a metrics listener that silently failed to bind would show the
    API as down in Prometheus while it serves traffic, so the master should
    fail at boot instead.
    """
    env = os.environ if env is None else env
    raw = (env.get("METRICS_PORT") or "").strip()
    try:
        port = int(raw) if raw else DEFAULT_METRICS_PORT
    except ValueError:
        port = -1
    if not 1 <= port <= 65535:
        raise ValueError(
            f"METRICS_PORT must be a TCP port (1-65535), got {env.get('METRICS_PORT')!r}"
        )
    if port == API_PORT:
        raise ValueError(
            f"METRICS_PORT ({port}) must differ from the API port: metrics must "
            "not share the public listener"
        )
    return port


def reset_multiproc_dir(path: str) -> Path:
    """Create ``path`` and delete the ``*.db`` files a previous master left.

    prometheus_client requires the directory to be emptied between runs;
    stale files from a restarted container would otherwise be summed into the
    new process's counters. Only ``*.db`` files are removed, never the
    directory itself or anything else in it.
    """
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    for stale in directory.glob("*.db"):
        stale.unlink()
    return directory


def multiprocess_registry(path: str | None = None) -> CollectorRegistry:
    """A registry that sums every worker's samples, plus the master's own
    process and platform metrics.

    ``process_*`` describes the gunicorn master (the workers' CPU and memory
    are in the container's cAdvisor series); ``python_info`` the interpreter.
    """
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry, path=path)
    ProcessCollector(registry=registry)
    PlatformCollector(registry=registry)
    return registry


def mark_worker_dead(pid: int, path: str | None = None) -> None:
    """Drop a dead worker's live-gauge files (gunicorn ``child_exit`` hook).

    Its counters and histograms stay on disk on purpose: they are the totals
    it served, and the aggregate must not go backwards when it exits.
    """
    multiprocess.mark_process_dead(pid, path)


def make_metrics_app(registry: CollectorRegistry):
    """WSGI app: ``GET /metrics`` from ``registry``; 404 elsewhere, 405 otherwise."""
    exposition = make_wsgi_app(registry)

    def app(environ, start_response):
        if environ.get("PATH_INFO", "") != METRICS_PATH:
            start_response(
                "404 Not Found", [("Content-Type", "text/plain; charset=utf-8")]
            )
            return [b"Not Found\n"]
        if environ.get("REQUEST_METHOD", "GET") != "GET":
            start_response(
                "405 Method Not Allowed",
                [("Content-Type", "text/plain; charset=utf-8"), ("Allow", "GET")],
            )
            return [b"Method Not Allowed\n"]
        return exposition(environ, start_response)

    return app


class _ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        # One access-log line per scrape every 30 s per scraper is noise.
        pass


def start_metrics_server(
    port: int, registry: CollectorRegistry, addr: str = "0.0.0.0"
) -> WSGIServer:
    """Serve :func:`make_metrics_app` on ``addr:port`` from a daemon thread.

    Raises ``OSError`` if the port cannot be bound. Returns the server;
    ``server.server_port`` is the bound port (useful with ``port=0``).
    """
    server = make_server(
        addr,
        port,
        make_metrics_app(registry),
        server_class=_ThreadingWSGIServer,
        handler_class=_QuietHandler,
    )
    thread = threading.Thread(
        target=server.serve_forever, name="prometheus-metrics", daemon=True
    )
    thread.start()
    return server
