"""User preference CRUD for cross-device sync."""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import UserPreference


def _get_user_id(request):
    """Extract Janua user ID from the authenticated request."""
    user = getattr(request, "user", None)
    if user and hasattr(user, "janua_user_id"):
        return user.janua_user_id
    # Fallback: check auth header claims
    auth = getattr(request, "auth", None)
    if isinstance(auth, dict):
        return auth.get("sub") or auth.get("user_id")
    return None


@api_view(["GET", "PUT"])
def user_preferences(request):
    """
    GET: Return all user preferences.
    PUT: Replace all preferences.
    """
    user_id = _get_user_id(request)
    if not user_id:
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    if request.method == "GET":
        pref, _ = UserPreference.objects.get_or_create(janua_user_id=user_id)
        return Response(
            {
                "bookmarks": pref.bookmarks,
                "recently_viewed": pref.recently_viewed,
                "preferences": pref.preferences,
                "updated_at": pref.updated_at,
            }
        )

    # PUT
    pref, _ = UserPreference.objects.get_or_create(janua_user_id=user_id)
    data = request.data
    if "bookmarks" in data:
        pref.bookmarks = data["bookmarks"]
    if "recently_viewed" in data:
        pref.recently_viewed = data["recently_viewed"]
    if "preferences" in data:
        pref.preferences = data["preferences"]
    pref.save()
    return Response({"status": "updated"})


@api_view(["PATCH"])
def user_bookmarks(request):
    """Add or remove a bookmark. Body: { action: 'add'|'remove', law_id: '...' }"""
    user_id = _get_user_id(request)
    if not user_id:
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    action = request.data.get("action")
    law_id = request.data.get("law_id")
    if action not in ("add", "remove") or not law_id:
        return Response(
            {"error": "action ('add'/'remove') and law_id required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    pref, _ = UserPreference.objects.get_or_create(janua_user_id=user_id)
    bookmarks = list(pref.bookmarks or [])

    if action == "add" and law_id not in bookmarks:
        bookmarks.append(law_id)
    elif action == "remove":
        bookmarks = [b for b in bookmarks if b != law_id]

    pref.bookmarks = bookmarks
    pref.save()
    return Response({"bookmarks": bookmarks})


@api_view(["PATCH"])
def user_recently_viewed(request):
    """Append to recently viewed. Body: { law_id: '...' }"""
    user_id = _get_user_id(request)
    if not user_id:
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    law_id = request.data.get("law_id")
    if not law_id:
        return Response(
            {"error": "law_id required."}, status=status.HTTP_400_BAD_REQUEST
        )

    pref, _ = UserPreference.objects.get_or_create(janua_user_id=user_id)
    viewed = list(pref.recently_viewed or [])

    # Remove if exists (to re-add at front)
    viewed = [v for v in viewed if v != law_id]
    viewed.insert(0, law_id)
    viewed = viewed[:50]  # Cap at 50 entries

    pref.recently_viewed = viewed
    pref.save()
    return Response({"recently_viewed": viewed})
