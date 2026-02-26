"""Notification and alert endpoints."""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Notification, UserAlert
from .preference_views import _get_user_id


@api_view(["GET"])
def notification_list(request):
    """List notifications for the authenticated user, unread first."""
    user_id = _get_user_id(request)
    if not user_id:
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    page = max(1, int(request.query_params.get("page", 1)))
    page_size = min(int(request.query_params.get("page_size", 20)), 100)
    offset = (page - 1) * page_size

    qs = Notification.objects.filter(janua_user_id=user_id).order_by(
        "is_read", "-created_at"
    )
    total = qs.count()
    unread = qs.filter(is_read=False).count()

    items = qs[offset : offset + page_size]
    return Response(
        {
            "total": total,
            "unread": unread,
            "page": page,
            "notifications": [
                {
                    "id": n.id,
                    "title": n.title,
                    "body": n.body,
                    "link": n.link,
                    "is_read": n.is_read,
                    "created_at": n.created_at,
                }
                for n in items
            ],
        }
    )


@api_view(["POST"])
def notification_mark_read(request):
    """Mark notifications as read. Body: { ids: [1, 2, 3] } or { all: true }"""
    user_id = _get_user_id(request)
    if not user_id:
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    if request.data.get("all"):
        count = Notification.objects.filter(
            janua_user_id=user_id, is_read=False
        ).update(is_read=True)
    else:
        ids = request.data.get("ids", [])
        if not isinstance(ids, list):
            return Response(
                {"error": "ids must be a list."}, status=status.HTTP_400_BAD_REQUEST
            )
        count = Notification.objects.filter(janua_user_id=user_id, id__in=ids).update(
            is_read=True
        )

    return Response({"marked_read": count})


@api_view(["GET", "POST"])
def alert_list(request):
    """
    GET: List user alert subscriptions.
    POST: Create a new alert.
    """
    user_id = _get_user_id(request)
    if not user_id:
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    if request.method == "GET":
        alerts = UserAlert.objects.filter(janua_user_id=user_id, is_active=True)
        return Response(
            {
                "alerts": [
                    {
                        "id": a.id,
                        "law_id": a.law_id,
                        "category": a.category,
                        "state": a.state,
                        "alert_type": a.alert_type,
                        "delivery": a.delivery,
                        "created_at": a.created_at,
                    }
                    for a in alerts
                ]
            }
        )

    # POST
    alert_type = request.data.get("alert_type", "law_updated")
    if alert_type not in ("law_updated", "new_version", "new_law"):
        return Response(
            {"error": "Invalid alert_type."}, status=status.HTTP_400_BAD_REQUEST
        )

    alert = UserAlert.objects.create(
        janua_user_id=user_id,
        law_id=request.data.get("law_id", "")[:200],
        category=request.data.get("category", "")[:100],
        state=request.data.get("state", "")[:100],
        alert_type=alert_type,
        delivery=request.data.get("delivery", "in_app")[:20],
    )
    return Response(
        {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "law_id": alert.law_id,
            "created_at": alert.created_at,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
def alert_delete(request, alert_id):
    """Deactivate an alert subscription."""
    user_id = _get_user_id(request)
    if not user_id:
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        alert = UserAlert.objects.get(id=alert_id, janua_user_id=user_id)
    except UserAlert.DoesNotExist:
        return Response({"error": "Alert not found."}, status=status.HTTP_404_NOT_FOUND)

    alert.is_active = False
    alert.save()
    return Response(status=status.HTTP_204_NO_CONTENT)
