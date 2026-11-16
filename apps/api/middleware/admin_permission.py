"""
Admin permission class for Tezca admin endpoints.

Tezca's admin endpoints are platform-level (system metrics, ingestion, API
key management). Access is granted to a platform administrator, identified
by the verified Janua token's ``is_admin`` claim, or to a user whose Janua
ID is listed in ``TEZCA_ADMIN_USER_IDS``.

The ``role`` / ``roles`` claims are not read here: Janua publishes a user's
organization membership roles there as bare strings (``owner``, ``admin``,
``member`` or custom organization roles), so a role name in those claims
describes standing inside some organization, not platform administration.
"""

import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


def is_platform_admin_claims(claims) -> bool:
    """True only when the verified token's ``is_admin`` claim is exactly ``True``."""
    if not isinstance(claims, dict):
        return False
    return claims.get("is_admin") is True


class IsTezcaAdmin(BasePermission):
    """
    Restricts admin endpoint access to platform administrators (``is_admin``
    claim on the verified Janua token) or users whose Janua user ID is in
    TEZCA_ADMIN_USER_IDS.
    """

    message = "Admin access required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False

        # Platform-admin claim from the verified Janua JWT (JanuaUser.claims).
        if is_platform_admin_claims(getattr(user, "claims", None)):
            return True

        # Check allow-list by user ID
        user_id = getattr(user, "id", "")
        admin_ids = getattr(settings, "TEZCA_ADMIN_USER_IDS", set())
        if user_id and user_id in admin_ids:
            return True

        return False
