"""Gunicorn hooks for the Tezca API: Prometheus multiprocess metrics.

Loaded by the Dockerfile CMD (``--config apps/indigo/gunicorn.conf.py``). The
bind address, worker count and timeouts stay on that command line.

The API runs several gunicorn workers, each its own process with its own
prometheus_client values. prometheus_client's multiprocess mode makes them add
up: every worker writes its samples to files under ``PROMETHEUS_MULTIPROC_DIR``,
and the master serves the sum on the private metrics port (9464) through
``MultiProcessCollector``. See apps/api/metrics_server.py.

Order matters. prometheus_client picks its value backend when it is FIRST
imported, and workers inherit the master's modules and environment when they
fork, so ``PROMETHEUS_MULTIPROC_DIR`` is set here, at config load in the
master, before anything imports prometheus_client.
"""

import os
import sys
from pathlib import Path

# The repo root (/app in the image). Gunicorn runs from it, but the console
# script does not guarantee it is on sys.path when this file is loaded.
_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", "/tmp/tezca-prometheus-multiproc")

from apps.api import metrics_server  # noqa: E402  (needs the env var above)

metrics_server.reset_multiproc_dir(os.environ["PROMETHEUS_MULTIPROC_DIR"])


def when_ready(server):
    """Start the metrics listener in the master once it is ready to fork.

    A bad ``METRICS_PORT`` or a port that cannot be bound raises here and
    gunicorn exits: better a pod that fails to start than an API that serves
    traffic while Prometheus reports it down.
    """
    port = metrics_server.resolve_metrics_port()
    metrics_server.start_metrics_server(port, metrics_server.multiprocess_registry())
    server.log.info(
        "Prometheus metrics (in-cluster only) on :%d%s",
        port,
        metrics_server.METRICS_PATH,
    )


def child_exit(server, worker):
    metrics_server.mark_worker_dead(worker.pid)
