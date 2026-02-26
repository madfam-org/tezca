"""Annotation CRUD for user notes on law articles."""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Annotation
from .preference_views import _get_user_id


def _serialize_annotation(a):
    return {
        "id": a.id,
        "law_id": a.law_id,
        "article_id": a.article_id,
        "text": a.text,
        "highlight_start": a.highlight_start,
        "highlight_end": a.highlight_end,
        "color": a.color,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


@api_view(["GET", "POST"])
def annotation_list(request):
    """
    GET: List annotations. Optional filter: ?law_id=X
    POST: Create a new annotation.
    """
    user_id = _get_user_id(request)
    if not user_id:
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    if request.method == "GET":
        qs = Annotation.objects.filter(janua_user_id=user_id)
        law_id = request.query_params.get("law_id")
        if law_id:
            qs = qs.filter(law_id=law_id)

        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(int(request.query_params.get("page_size", 50)), 200)
        offset = (page - 1) * page_size

        total = qs.count()
        annotations = qs[offset : offset + page_size]
        return Response(
            {
                "total": total,
                "page": page,
                "annotations": [_serialize_annotation(a) for a in annotations],
            }
        )

    # POST
    law_id = request.data.get("law_id")
    article_id = request.data.get("article_id")
    text = request.data.get("text", "").strip()

    if not law_id or not article_id or not text:
        return Response(
            {"error": "law_id, article_id, and text are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    annotation = Annotation.objects.create(
        janua_user_id=user_id,
        law_id=law_id[:200],
        article_id=article_id[:100],
        text=text,
        highlight_start=request.data.get("highlight_start"),
        highlight_end=request.data.get("highlight_end"),
        color=request.data.get("color", "yellow")[:20],
    )
    return Response(_serialize_annotation(annotation), status=status.HTTP_201_CREATED)


@api_view(["PUT", "DELETE"])
def annotation_detail(request, annotation_id):
    """
    PUT: Update an annotation.
    DELETE: Delete an annotation.
    """
    user_id = _get_user_id(request)
    if not user_id:
        return Response(
            {"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        annotation = Annotation.objects.get(id=annotation_id, janua_user_id=user_id)
    except Annotation.DoesNotExist:
        return Response(
            {"error": "Annotation not found."}, status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "DELETE":
        annotation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PUT
    if "text" in request.data:
        annotation.text = request.data["text"].strip()
    if "color" in request.data:
        annotation.color = request.data["color"][:20]
    if "highlight_start" in request.data:
        annotation.highlight_start = request.data["highlight_start"]
    if "highlight_end" in request.data:
        annotation.highlight_end = request.data["highlight_end"]
    annotation.save()
    return Response(_serialize_annotation(annotation))
