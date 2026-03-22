"""User-scoped API key management (self-serve create, list, rename, revoke)."""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import posthog_analytics
from .apikeys import generate_api_key
from .models import APIKey
from .preference_views import _get_user_id
from .tier_permissions import check_feature

MAX_ACTIVE_KEYS_PER_USER = 5


def _serialize_key(key, include_full_key=False, full_key=None):
    data = {
        "prefix": key.prefix,
        "name": key.name,
        "tier": key.tier,
        "scopes": key.scopes,
        "is_active": key.is_active,
        "created_at": key.created_at,
        "last_used_at": key.last_used_at,
    }
    if include_full_key and full_key:
        data["key"] = full_key
    return data


@api_view(["GET", "POST"])
def user_apikey_list_create(request):
    """
    GET: List the authenticated user's API keys.
    POST: Create a new API key for the authenticated user.
    """
    user_id = _get_user_id(request)
    if not user_id:
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    if request.method == "GET":
        qs = APIKey.objects.filter(janua_user_id=user_id).order_by("-created_at")
        keys = list(qs)
        return Response({"keys": [_serialize_key(k) for k in keys], "total": len(keys)})

    # POST — create a new key
    user_tier = getattr(request.user, "tier", "free_member")

    if user_tier == "anon":
        return Response(
            {"error": "Anonymous users cannot create API keys."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not check_feature(user_tier, "api_key_access"):
        return Response(
            {"error": "Your tier does not have API key access."},
            status=status.HTTP_403_FORBIDDEN,
        )

    name = (request.data.get("name") or "").strip()
    if not name:
        return Response(
            {"error": "name is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    active_count = APIKey.objects.filter(janua_user_id=user_id, is_active=True).count()
    if active_count >= MAX_ACTIVE_KEYS_PER_USER:
        return Response(
            {
                "error": f"Maximum {MAX_ACTIVE_KEYS_PER_USER} active keys allowed. "
                "Revoke an existing key first."
            },
            status=status.HTTP_409_CONFLICT,
        )

    # Build scopes based on tier features
    scopes = ["read", "search"]
    if check_feature(user_tier, "pdf_export"):
        scopes.append("export")
    if check_feature(user_tier, "bulk_download"):
        scopes.append("bulk")

    full_key, prefix, hashed_key = generate_api_key()

    key = APIKey.objects.create(
        prefix=prefix,
        hashed_key=hashed_key,
        name=name[:200],
        owner_email=getattr(request.user, "email", ""),
        janua_user_id=user_id,
        tier=user_tier,
        scopes=scopes,
    )

    posthog_analytics.track(
        posthog_analytics.get_distinct_id(request),
        "api_key.self_serve_created",
        {"prefix": prefix, "tier": user_tier},
    )

    return Response(
        _serialize_key(key, include_full_key=True, full_key=full_key),
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
def user_apikey_update(request, prefix):
    """PATCH: Rename an API key (only the name field)."""
    user_id = _get_user_id(request)
    if not user_id:
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        key = APIKey.objects.get(prefix=prefix, janua_user_id=user_id)
    except APIKey.DoesNotExist:
        return Response(
            {"error": "API key not found."}, status=status.HTTP_404_NOT_FOUND
        )

    name = (request.data.get("name") or "").strip()
    if not name:
        return Response(
            {"error": "name is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    key.name = name[:200]
    key.save(update_fields=["name"])
    return Response(_serialize_key(key))


@api_view(["DELETE"])
def user_apikey_revoke(request, prefix):
    """DELETE: Soft-revoke an API key (set is_active=False)."""
    user_id = _get_user_id(request)
    if not user_id:
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        key = APIKey.objects.get(prefix=prefix, janua_user_id=user_id, is_active=True)
    except APIKey.DoesNotExist:
        return Response(
            {"error": "API key not found."}, status=status.HTTP_404_NOT_FOUND
        )

    key.is_active = False
    key.save(update_fields=["is_active"])

    posthog_analytics.track(
        posthog_analytics.get_distinct_id(request),
        "api_key.self_serve_revoked",
        {"prefix": prefix},
    )
    return Response(status=status.HTTP_204_NO_CONTENT)
