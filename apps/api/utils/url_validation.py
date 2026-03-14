"""
Webhook URL validation to prevent SSRF attacks.

Validates that webhook URLs point to public internet hosts,
rejecting private/internal IP ranges, non-HTTPS schemes, and
unresolvable hostnames.
"""

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeURLError(ValueError):
    """Raised when a URL targets a private/internal network address."""

    pass


# Private and reserved IP networks that must not be targeted by webhooks
_BLOCKED_NETWORKS = [
    # IPv4
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("240.0.0.0/4"),
    # IPv6
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP address falls within blocked private/reserved ranges."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # Unparseable = reject
    return any(addr in net for net in _BLOCKED_NETWORKS)


def validate_webhook_url(url: str) -> None:
    """Validate that a webhook URL is safe to deliver to.

    Raises UnsafeURLError if the URL targets a private network,
    uses a non-HTTPS scheme, or cannot be resolved.
    """
    parsed = urlparse(url)

    # Scheme check
    if parsed.scheme != "https":
        raise UnsafeURLError(
            f"Webhook URL must use HTTPS (got {parsed.scheme or 'empty'})"
        )

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("Webhook URL has no hostname")

    # Resolve hostname to IP addresses
    try:
        addrinfo = socket.getaddrinfo(
            hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
        )
    except socket.gaierror:
        raise UnsafeURLError(f"Cannot resolve hostname: {hostname}")

    if not addrinfo:
        raise UnsafeURLError(f"Cannot resolve hostname: {hostname}")

    # Check all resolved IPs against blocked ranges
    for family, _, _, _, sockaddr in addrinfo:
        ip_str = sockaddr[0]
        if _is_private_ip(ip_str):
            raise UnsafeURLError(
                f"Webhook URL resolves to private/reserved IP: {ip_str}"
            )
