"""Feature interest capture endpoints (public, rate-limited)."""

import logging

from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import FeatureInterest

logger = logging.getLogger(__name__)


class InterestThrottle(AnonRateThrottle):
    rate = "10/hour"


@api_view(["POST"])
@throttle_classes([InterestThrottle])
def register_interest(request):
    """Register interest in a gated feature."""
    email = (request.data.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return Response(
            {"error": "A valid email is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    feature_key = (request.data.get("feature_key") or "").strip()
    if feature_key not in FeatureInterest.ALLOWED_FEATURES:
        return Response(
            {
                "error": f"Invalid feature_key. Must be one of: {', '.join(FeatureInterest.ALLOWED_FEATURES)}"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    use_case = (request.data.get("use_case") or "").strip()
    janua_user_id = (request.data.get("janua_user_id") or "").strip()
    source_page = (request.data.get("source_page") or "").strip()

    interest, created = FeatureInterest.objects.get_or_create(
        email=email,
        feature_key=feature_key,
        defaults={
            "use_case": use_case,
            "janua_user_id": janua_user_id,
            "source_page": source_page,
        },
    )

    if not created:
        # Update supplementary fields if provided on re-registration
        updated = False
        if use_case and not interest.use_case:
            interest.use_case = use_case
            updated = True
        if janua_user_id and not interest.janua_user_id:
            interest.janua_user_id = janua_user_id
            updated = True
        if source_page and not interest.source_page:
            interest.source_page = source_page
            updated = True
        if updated:
            interest.save()
        return Response({"status": "already_registered"})

    return Response({"status": "registered"}, status=status.HTTP_201_CREATED)
