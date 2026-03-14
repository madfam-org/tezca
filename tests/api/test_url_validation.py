"""Tests for SSRF protection in webhook URL validation."""

from unittest.mock import patch

import pytest

from apps.api.utils.url_validation import UnsafeURLError, validate_webhook_url


def _fake_resolve(hostname, port, family, socktype):
    """Simulate DNS resolution returning a controlled IP."""
    ip_map = {
        "public.example.com": "93.184.216.34",
        "localhost": "127.0.0.1",
        "internal.local": "10.0.0.1",
        "link-local.test": "169.254.1.1",
        "private-172.test": "172.16.0.1",
        "private-192.test": "192.168.1.1",
    }
    ip = ip_map.get(hostname)
    if ip is None:
        import socket

        raise socket.gaierror("Name resolution failed")
    import socket

    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]


@patch("apps.api.utils.url_validation.socket.getaddrinfo", side_effect=_fake_resolve)
class TestValidateWebhookUrl:
    def test_allows_public_https_url(self, mock_dns):
        """Public HTTPS URLs pass validation."""
        validate_webhook_url("https://public.example.com/webhook")

    def test_rejects_http_scheme(self, mock_dns):
        with pytest.raises(UnsafeURLError, match="HTTPS"):
            validate_webhook_url("http://public.example.com/webhook")

    def test_rejects_ftp_scheme(self, mock_dns):
        with pytest.raises(UnsafeURLError, match="HTTPS"):
            validate_webhook_url("ftp://public.example.com/file")

    def test_rejects_empty_scheme(self, mock_dns):
        with pytest.raises(UnsafeURLError):
            validate_webhook_url("//public.example.com/webhook")

    def test_rejects_localhost(self, mock_dns):
        with pytest.raises(UnsafeURLError, match="private"):
            validate_webhook_url("https://localhost/hook")

    def test_rejects_private_10x(self, mock_dns):
        with pytest.raises(UnsafeURLError, match="private"):
            validate_webhook_url("https://internal.local/hook")

    def test_rejects_private_172x(self, mock_dns):
        with pytest.raises(UnsafeURLError, match="private"):
            validate_webhook_url("https://private-172.test/hook")

    def test_rejects_private_192x(self, mock_dns):
        with pytest.raises(UnsafeURLError, match="private"):
            validate_webhook_url("https://private-192.test/hook")

    def test_rejects_link_local(self, mock_dns):
        with pytest.raises(UnsafeURLError, match="private"):
            validate_webhook_url("https://link-local.test/hook")

    def test_rejects_unresolvable_hostname(self, mock_dns):
        with pytest.raises(UnsafeURLError, match="Cannot resolve"):
            validate_webhook_url("https://nonexistent.invalid/hook")

    def test_rejects_no_hostname(self, mock_dns):
        with pytest.raises(UnsafeURLError):
            validate_webhook_url("https:///path-only")

    def test_rejects_file_scheme(self, mock_dns):
        with pytest.raises(UnsafeURLError, match="HTTPS"):
            validate_webhook_url("file:///etc/passwd")
