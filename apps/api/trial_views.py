"""
Trial management endpoints.

POST /api/v1/trial/start/ — Start a trial for the authenticated user's API key
GET  /api/v1/trial/status/ — Check trial status
"""

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.conf import settings

from .middleware.tier_permissions import check_feature
from .models import APIKey
from .posthog_analytics import get_distinct_id, track

logger = logging.getLogger(__name__)

TRIAL_DURATION_NO_CC = timezone.timedelta(days=settings.TRIAL_DURATION_NO_CC_DAYS)
TRIAL_DURATION_WITH_CC = timezone.timedelta(days=settings.TRIAL_DURATION_WITH_CC_DAYS)
VALID_TRIAL_PLANS = settings.TRIAL_VALID_PLANS


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def trial_start(request):
    """Start a trial for the authenticated user."""
    plan = request.data.get("plan", "")
    if plan not in VALID_TRIAL_PLANS:
        return Response(
            {
                "error": f"Invalid plan. Must be one of: {', '.join(sorted(VALID_TRIAL_PLANS))}"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    user_id = getattr(request.user, "id", None) or ""
    janua_user_id = str(user_id).replace("apikey:", "")

    # Find the user's API key
    api_key = APIKey.objects.filter(janua_user_id=janua_user_id, is_active=True).first()

    if not api_key:
        # If no API key, they need one first
        return Response(
            {"error": "No active API key found. Create an API key first."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Check if user's tier is eligible for a trial
    if not check_feature(api_key.tier, "trial_eligible"):
        return Response(
            {
                "error": f"Your current tier ({api_key.tier}) is not eligible for a trial."
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # Check if user already had a trial
    if api_key.trial_started_at is not None:
        return Response(
            {"error": "Trial already used. Each account gets one trial."},
            status=status.HTTP_409_CONFLICT,
        )

    now = timezone.now()
    api_key.trial_tier = plan
    api_key.trial_started_at = now
    api_key.trial_ends_at = now + TRIAL_DURATION_NO_CC
    api_key.trial_cc_provided = False
    api_key.save(
        update_fields=[
            "trial_tier",
            "trial_started_at",
            "trial_ends_at",
            "trial_cc_provided",
        ]
    )

    track(get_distinct_id(request), "trial.started", {"plan": plan, "duration_days": 3})

    logger.info("Trial started: user=%s plan=%s", janua_user_id, plan)
    return Response(
        {
            "status": "trial_started",
            "trial_tier": plan,
            "trial_ends_at": api_key.trial_ends_at.isoformat(),
            "days_remaining": 3,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trial_status(request):
    """Check trial status for the authenticated user."""
    user_id = getattr(request.user, "id", None) or ""
    janua_user_id = str(user_id).replace("apikey:", "")

    api_key = APIKey.objects.filter(janua_user_id=janua_user_id, is_active=True).first()

    if not api_key:
        return Response({"active": False, "trial_tier": None})

    now = timezone.now()
    active = (
        api_key.trial_tier is not None
        and api_key.trial_ends_at is not None
        and api_key.trial_ends_at > now
    )

    days_remaining = 0
    if active and api_key.trial_ends_at:
        days_remaining = max(0, (api_key.trial_ends_at - now).days)

    return Response(
        {
            "active": active,
            "trial_tier": api_key.trial_tier,
            "trial_ends_at": (
                api_key.trial_ends_at.isoformat() if api_key.trial_ends_at else None
            ),
            "trial_cc_provided": api_key.trial_cc_provided,
            "days_remaining": days_remaining,
            "trial_started_at": (
                api_key.trial_started_at.isoformat()
                if api_key.trial_started_at
                else None
            ),
        }
    )
