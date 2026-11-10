"""Production HTTP→HTTPS redirect: which paths SecurityMiddleware leaves alone.

In production (`DEBUG=False`) `apps/indigo/settings.py` turns on
`SECURE_SSL_REDIRECT` and exempts `PRODUCTION_SECURE_REDIRECT_EXEMPT`. Public
traffic reaches the API through Cloudflare with `X-Forwarded-Proto: https`;
in-cluster callers speak plain HTTP to the Service with no such header. These
tests pin both sides:

- the production settings block really uses the exempt list (a subprocess
  imports the settings module with `DEBUG=False`, since the suite itself runs
  with `DEBUG=True` and the block is skipped);
- SecurityMiddleware, configured exactly like production, does not redirect
  `/api/...` or `/health` over plain HTTP, still redirects every other path,
  and treats `X-Forwarded-Proto: https` requests as secure, as before.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.http import HttpResponse
from django.middleware.security import SecurityMiddleware
from django.test import RequestFactory, override_settings

REPO_ROOT = Path(__file__).resolve().parent.parent

IN_CLUSTER_HOST = "tezca-api.tezca.svc.cluster.local"
PUBLIC_HOST = "api.tezca.mx"


def _production_settings():
    """The redirect settings production runs with, taken from settings.py."""
    return override_settings(
        SECURE_SSL_REDIRECT=True,
        SECURE_REDIRECT_EXEMPT=list(settings.PRODUCTION_SECURE_REDIRECT_EXEMPT),
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
        SECURE_SSL_HOST=None,
        ALLOWED_HOSTS=[PUBLIC_HOST, IN_CLUSTER_HOST],
    )


def _through_security_middleware(path: str, *, host: str, forwarded_proto: str | None):
    """Run one GET through SecurityMiddleware the way production builds it."""
    extra = {"HTTP_HOST": host}
    if forwarded_proto is not None:
        extra["HTTP_X_FORWARDED_PROTO"] = forwarded_proto
    request = RequestFactory().get(path, **extra)
    middleware = SecurityMiddleware(lambda _request: HttpResponse("view ran"))
    return middleware(request)


class TestProductionSettingsBlock:
    """The `if not DEBUG:` block wires the exempt list it claims to."""

    def test_debug_false_settings_use_the_exempt_list(self):
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"DATABASE_URL", "DEBUG", "SECURE_SSL_REDIRECT"}
        }
        env.update({"DEBUG": "False", "DJANGO_SECRET_KEY": "test-only-not-a-secret"})
        probe = (
            "import json, warnings\n"
            "warnings.simplefilter('ignore')\n"
            "import apps.indigo.settings as s\n"
            "print(json.dumps({\n"
            "  'redirect': s.SECURE_SSL_REDIRECT,\n"
            "  'exempt': s.SECURE_REDIRECT_EXEMPT,\n"
            "  'production_exempt': list(s.PRODUCTION_SECURE_REDIRECT_EXEMPT),\n"
            "  'proxy_header': list(s.SECURE_PROXY_SSL_HEADER),\n"
            "  'hsts': s.SECURE_HSTS_SECONDS,\n"
            "  'session_cookie_secure': s.SESSION_COOKIE_SECURE,\n"
            "  'csrf_cookie_secure': s.CSRF_COOKIE_SECURE,\n"
            "}))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        loaded = json.loads(result.stdout.strip().splitlines()[-1])

        assert loaded["redirect"] is True
        assert (
            loaded["exempt"] == loaded["production_exempt"] == [r"^health$", r"^api/"]
        )
        assert loaded["proxy_header"] == ["HTTP_X_FORWARDED_PROTO", "https"]
        # HSTS and secure cookies are untouched by the exemption.
        assert loaded["hsts"] == 31536000
        assert loaded["session_cookie_secure"] is True
        assert loaded["csrf_cookie_secure"] is True


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/laws/?search=codigo&domain=finance",
        "/api/v1/fiscal/tipo-cambio/current",
        "/api/v1/admin/health/",
        "/api/schema/",
    ],
)
def test_in_cluster_plain_http_api_call_is_not_redirected(path):
    with _production_settings():
        response = _through_security_middleware(
            path, host=IN_CLUSTER_HOST, forwarded_proto=None
        )

    assert response.status_code == 200
    assert response.content == b"view ran"


def test_health_is_still_exempt():
    with _production_settings():
        response = _through_security_middleware(
            "/health", host=IN_CLUSTER_HOST, forwarded_proto=None
        )

    assert response.status_code == 200
    assert response.content == b"view ran"


@pytest.mark.parametrize(
    "path",
    [
        "/admin/",
        "/admin/login/",
        # Anchored prefixes: lookalikes outside the API still redirect.
        "/apiv1/laws/",
        "/health/",
        "/healthz",
        "/v1/api/laws/",
    ],
)
def test_non_api_plain_http_still_redirects(path):
    with _production_settings():
        response = _through_security_middleware(
            path, host=IN_CLUSTER_HOST, forwarded_proto=None
        )

    assert response.status_code == 301
    assert response["Location"] == f"https://{IN_CLUSTER_HOST}{path}"


def test_explicit_plain_http_forwarded_proto_on_non_api_path_still_redirects():
    """A request a proxy marked as plain HTTP is redirected exactly as before."""
    with _production_settings():
        response = _through_security_middleware(
            "/admin/", host=PUBLIC_HOST, forwarded_proto="http"
        )

    assert response.status_code == 301
    assert response["Location"] == f"https://{PUBLIC_HOST}/admin/"


@pytest.mark.parametrize(
    "path",
    ["/api/v1/laws/", "/health", "/admin/", "/admin/login/"],
)
def test_forwarded_https_requests_behave_as_before(path):
    """Cloudflare traffic: secure, never redirected, HSTS sent as before."""
    with _production_settings(), override_settings(SECURE_HSTS_SECONDS=31536000):
        response = _through_security_middleware(
            path, host=PUBLIC_HOST, forwarded_proto="https"
        )

    assert response.status_code == 200
    assert response.content == b"view ran"
    assert response["Strict-Transport-Security"].startswith("max-age=31536000")


def test_plain_http_api_response_carries_no_hsts():
    """HSTS is only ever sent on secure requests; the exemption doesn't change that."""
    with _production_settings(), override_settings(SECURE_HSTS_SECONDS=31536000):
        response = _through_security_middleware(
            "/api/v1/laws/", host=IN_CLUSTER_HOST, forwarded_proto=None
        )

    assert response.status_code == 200
    assert "Strict-Transport-Security" not in response


@pytest.mark.django_db
def test_full_stack_health_and_admin_over_plain_http():
    """The real middleware stack and URLconf, not just SecurityMiddleware."""
    from django.test import Client

    client = Client()
    with _production_settings():
        health = client.get("/health", HTTP_HOST=IN_CLUSTER_HOST)
        admin = client.get("/admin/", HTTP_HOST=IN_CLUSTER_HOST)

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert admin.status_code == 301
    assert admin["Location"] == f"https://{IN_CLUSTER_HOST}/admin/"
