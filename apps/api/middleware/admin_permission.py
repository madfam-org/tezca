"""
Admin permission class for Tezca admin endpoints.

Checks JWT claims for admin role or user ID in allowed list.
"""

import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class IsTezcaAdmin(BasePermission):
    """
    Restricts admin endpoint access to users with admin role claim
    or whose Janua user ID is in TEZCA_ADMIN_USER_IDS.
    """

    message = "Admin access required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False

        # Check JWT role claim
        claims = getattr(user, "claims", {})
        if claims.get("role") == "admin":
            return True

        # Check allow-list by user ID
        user_id = getattr(user, "id", "")
        admin_ids = getattr(settings, "TEZCA_ADMIN_USER_IDS", set())
        if user_id and user_id in admin_ids:
            return True

        return False
