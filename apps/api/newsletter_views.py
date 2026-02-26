"""Newsletter subscription endpoints (public, rate-limited)."""

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import NewsletterSubscription

logger = logging.getLogger(__name__)


class NewsletterThrottle(AnonRateThrottle):
    rate = "5/hour"


@api_view(["POST"])
@throttle_classes([NewsletterThrottle])
def newsletter_subscribe(request):
    """Subscribe to the newsletter."""
    email = (request.data.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return Response(
            {"error": "A valid email is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    topics = request.data.get("topics", [])
    if not isinstance(topics, list):
        topics = []

    sub, created = NewsletterSubscription.objects.get_or_create(
        email=email,
        defaults={"topics": topics, "is_active": True},
    )

    if not created:
        if not sub.is_active:
            sub.is_active = True
            sub.unsubscribed_at = None
            sub.topics = topics or sub.topics
            sub.save()
            return Response({"status": "resubscribed"})
        return Response({"status": "already_subscribed"})

    return Response({"status": "subscribed"}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def newsletter_unsubscribe(request):
    """Unsubscribe from the newsletter."""
    email = (request.data.get("email") or "").strip().lower()
    if not email:
        return Response(
            {"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        sub = NewsletterSubscription.objects.get(email=email)
        sub.is_active = False
        sub.unsubscribed_at = timezone.now()
        sub.save()
        return Response({"status": "unsubscribed"})
    except NewsletterSubscription.DoesNotExist:
        return Response({"status": "not_found"}, status=status.HTTP_404_NOT_FOUND)
