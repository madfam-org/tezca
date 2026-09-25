"""Prometheus request metrics for the Django API.

Counts every request and times it, by method, route and status code:

* ``http_requests_total{method, route, code}``
* ``http_request_duration_seconds{method, route}`` (histogram)

The names and the ``code`` label match the fleet client-SLO rules in enclii's
``infra/k8s/production/monitoring/prometheus.yaml`` (``ClientServiceErrorRate``
and ``ClientServiceLatencyP95`` select ``http_requests_total`` and
``http_request_duration_seconds_bucket`` in namespace ``tezca``), so the API is
covered by them as soon as Prometheus scrapes it.

``route`` is the URL pattern Django resolved (``api/v1/laws/<str:law_id>/``),
never the raw path, so law ids and query strings cannot explode the series
count. A request that resolved no pattern (a 404, or a request refused before
URL resolution such as a DisallowedHost 400) is labelled ``<unmatched>``.

Nothing here serves the metrics. Under gunicorn the values go to
prometheus_client's multiprocess files (``PROMETHEUS_MULTIPROC_DIR``, set by
``apps/indigo/gunicorn.conf.py``) and the gunicorn master serves them on the
private port 9464 (``apps/api/metrics_server.py``). The public app has no
metrics route.
"""

from __future__ import annotations

import time

from prometheus_client import Counter, Histogram

UNMATCHED_ROUTE = "<unmatched>"

_KNOWN_METHODS = frozenset(
    {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"}
)

# Default prometheus_client buckets stop at 10 s; exports and bulk endpoints run
# up to the 120 s gunicorn timeout, so the tail gets its own buckets.
LATENCY_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
    60.0,
    120.0,
)

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests served by the Tezca API, by method, route pattern and status code.",
    labelnames=("method", "route", "code"),
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Time spent serving a Tezca API request, by method and route pattern.",
    labelnames=("method", "route"),
    buckets=LATENCY_BUCKETS,
)


def _method_label(method: str | None) -> str:
    method = (method or "").upper()
    return method if method in _KNOWN_METHODS else "OTHER"


def _route_label(request) -> str:
    match = getattr(request, "resolver_match", None)
    route = getattr(match, "route", None) if match is not None else None
    return route or UNMATCHED_ROUTE


class RequestMetricsMiddleware:
    """Record ``http_requests_total`` and ``http_request_duration_seconds``.

    Sits FIRST in ``MIDDLEWARE`` so the timing covers the whole stack and the
    responses that other middleware produce (CORS preflights, DisallowedHost
    400s, CSRF 403s) are counted too.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        status = 500
        try:
            response = self.get_response(request)
            status = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - start
            method = _method_label(request.method)
            route = _route_label(request)
            HTTP_REQUESTS.labels(method=method, route=route, code=str(status)).inc()
            HTTP_REQUEST_DURATION.labels(method=method, route=route).observe(elapsed)
