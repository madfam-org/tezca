"""
Admin endpoints for API key management.

All endpoints require Janua JWT authentication (admin only).
"""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .apikeys import generate_api_key
from .models import APIKey

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Admin"],
    summary="Create API key",
    description="Create a new API key. Returns the full key once — it cannot be retrieved later.",
    request={
        "application/json": {
            "type": "object",
            "required": ["name", "owner_email"],
            "properties": {
                "name": {"type": "string", "example": "Dhanam Compliance Prod"},
                "owner_email": {"type": "string", "format": "email"},
                "organization": {"type": "string", "default": ""},
                "janua_user_id": {"type": "string", "default": ""},
                "tier": {
                    "type": "string",
                    "enum": ["internal", "free", "pro", "enterprise"],
                    "default": "free",
                },
                "scopes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["read", "search"],
                },
                "allowed_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
                "rate_limit_per_hour": {"type": "integer", "nullable": True},
            },
        }
    },
)
@api_view(["POST"])
def create_api_key(request):
    """Create a new API key. Returns the full key once."""
    data = request.data
    name = data.get("name", "").strip()
    owner_email = data.get("owner_email", "").strip()

    if not name or not owner_email:
        return Response(
            {"error": "name and owner_email are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    tier = data.get("tier", "free")
    if tier not in dict(APIKey.Tier.choices):
        return Response(
            {"error": f"Invalid tier: {tier}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    scopes = data.get("scopes", ["read", "search"])
    allowed_domains = data.get("allowed_domains", [])

    full_key, prefix, hashed = generate_api_key()

    api_key = APIKey.objects.create(
        prefix=prefix,
        hashed_key=hashed,
        name=name,
        owner_email=owner_email,
        organization=data.get("organization", ""),
        janua_user_id=data.get("janua_user_id", ""),
        tier=tier,
        scopes=scopes,
        allowed_domains=allowed_domains,
        rate_limit_per_hour=data.get("rate_limit_per_hour"),
    )

    logger.info("API key created: %s (tier=%s, prefix=%s)", name, tier, prefix)

    return Response(
        {
            "key": full_key,  # Shown once, never stored
            "prefix": api_key.prefix,
            "name": api_key.name,
            "tier": api_key.tier,
            "scopes": api_key.scopes,
            "allowed_domains": api_key.allowed_domains,
            "created_at": api_key.created_at.isoformat(),
        },
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=["Admin"],
    summary="List API keys",
    description="List all API keys (prefix, name, tier, last_used). Never returns the full key.",
)
@api_view(["GET"])
def list_api_keys(request):
    """List all API keys (metadata only, never full key)."""
    keys = APIKey.objects.order_by("-created_at")

    # Optional filters
    tier = request.query_params.get("tier")
    if tier:
        keys = keys.filter(tier=tier)

    is_active = request.query_params.get("is_active")
    if is_active is not None:
        keys = keys.filter(is_active=is_active.lower() in ("true", "1"))

    data = [
        {
            "prefix": k.prefix,
            "name": k.name,
            "owner_email": k.owner_email,
            "organization": k.organization,
            "tier": k.tier,
            "scopes": k.scopes,
            "allowed_domains": k.allowed_domains,
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat(),
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "rate_limit_per_hour": k.rate_limit_per_hour,
        }
        for k in keys
    ]

    return Response({"count": len(data), "keys": data})


@extend_schema(
    tags=["Admin"],
    summary="Update API key",
    description="Update an API key's tier, scopes, active status, or allowed domains.",
)
@api_view(["PATCH"])
def update_api_key(request, prefix):
    """Update an API key by prefix."""
    try:
        api_key = APIKey.objects.get(prefix=prefix)
    except APIKey.DoesNotExist:
        return Response(
            {"error": "API key not found"}, status=status.HTTP_404_NOT_FOUND
        )

    data = request.data
    updatable = [
        "tier",
        "scopes",
        "allowed_domains",
        "is_active",
        "name",
        "organization",
        "rate_limit_per_hour",
        "janua_user_id",
    ]

    for field in updatable:
        if field in data:
            if field == "tier" and data[field] not in dict(APIKey.Tier.choices):
                return Response(
                    {"error": f"Invalid tier: {data[field]}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            setattr(api_key, field, data[field])

    api_key.save()
    logger.info("API key updated: %s (prefix=%s)", api_key.name, prefix)

    return Response(
        {
            "prefix": api_key.prefix,
            "name": api_key.name,
            "tier": api_key.tier,
            "scopes": api_key.scopes,
            "allowed_domains": api_key.allowed_domains,
            "is_active": api_key.is_active,
        }
    )


@extend_schema(
    tags=["Admin"],
    summary="Revoke API key",
    description="Deactivate an API key (soft delete).",
)
@api_view(["DELETE"])
def revoke_api_key(request, prefix):
    """Revoke (deactivate) an API key."""
    try:
        api_key = APIKey.objects.get(prefix=prefix)
    except APIKey.DoesNotExist:
        return Response(
            {"error": "API key not found"}, status=status.HTTP_404_NOT_FOUND
        )

    api_key.is_active = False
    api_key.save(update_fields=["is_active"])
    logger.info("API key revoked: %s (prefix=%s)", api_key.name, prefix)

    return Response({"status": "revoked", "prefix": prefix})
