"""
Judicial record API views.

Search and browse SCJN jurisprudencia and tesis aisladas.
Public endpoints — no authentication required.
"""

import logging

from django.db.models import Q
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import JudicialRecord

logger = logging.getLogger(__name__)


class JudicialRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = JudicialRecord
        fields = [
            "id",
            "registro",
            "epoca",
            "instancia",
            "materia",
            "tipo",
            "rubro",
            "texto",
            "precedentes",
            "votos",
            "ponente",
            "fuente",
            "fecha_publicacion",
        ]


class JudicialRecordListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views (no full text)."""

    class Meta:
        model = JudicialRecord
        fields = [
            "id",
            "registro",
            "epoca",
            "instancia",
            "materia",
            "tipo",
            "rubro",
            "ponente",
            "fecha_publicacion",
        ]


@api_view(["GET"])
def judicial_list(request):
    """
    List judicial records with filtering.

    Query params:
        tipo: jurisprudencia | tesis_aislada
        materia: civil | penal | administrativa | laboral | constitucional | comun
        epoca: e.g. "11a"
        instancia: e.g. "Pleno"
        page: page number (default 1)
        page_size: results per page (default 20, max 100)
    """
    qs = JudicialRecord.objects.all()

    tipo = request.query_params.get("tipo")
    if tipo:
        qs = qs.filter(tipo=tipo)

    materia = request.query_params.get("materia")
    if materia:
        qs = qs.filter(materia=materia)

    epoca = request.query_params.get("epoca")
    if epoca:
        qs = qs.filter(epoca=epoca)

    instancia = request.query_params.get("instancia")
    if instancia:
        qs = qs.filter(instancia__icontains=instancia)

    # Pagination
    page = max(1, int(request.query_params.get("page", 1)))
    page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
    start = (page - 1) * page_size

    total = qs.count()
    records = qs[start : start + page_size]

    return Response(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": JudicialRecordListSerializer(records, many=True).data,
        }
    )


@api_view(["GET"])
def judicial_detail(request, registro):
    """Get a single judicial record by registro."""
    try:
        record = JudicialRecord.objects.get(registro=registro)
    except JudicialRecord.DoesNotExist:
        return Response({"error": "Record not found"}, status=status.HTTP_404_NOT_FOUND)

    return Response(JudicialRecordSerializer(record).data)


@api_view(["GET"])
def judicial_search(request):
    """
    Full-text search across judicial records.

    Query params:
        q: search query (searches rubro + texto)
        tipo, materia, epoca: optional filters
        page, page_size: pagination
    """
    query = request.query_params.get("q", "").strip()
    if not query:
        return Response(
            {"error": "Query parameter 'q' is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    qs = JudicialRecord.objects.filter(
        Q(rubro__icontains=query) | Q(texto__icontains=query)
    )

    tipo = request.query_params.get("tipo")
    if tipo:
        qs = qs.filter(tipo=tipo)

    materia = request.query_params.get("materia")
    if materia:
        qs = qs.filter(materia=materia)

    epoca = request.query_params.get("epoca")
    if epoca:
        qs = qs.filter(epoca=epoca)

    page = max(1, int(request.query_params.get("page", 1)))
    page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
    start = (page - 1) * page_size

    total = qs.count()
    records = qs[start : start + page_size]

    return Response(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "query": query,
            "results": JudicialRecordListSerializer(records, many=True).data,
        }
    )


@api_view(["GET"])
def judicial_stats(request):
    """Summary statistics for the judicial corpus."""
    from django.db.models import Count

    total = JudicialRecord.objects.count()

    by_tipo = dict(
        JudicialRecord.objects.values_list("tipo")
        .annotate(c=Count("id"))
        .values_list("tipo", "c")
    )

    by_materia = dict(
        JudicialRecord.objects.values_list("materia")
        .annotate(c=Count("id"))
        .values_list("materia", "c")
    )

    by_epoca = dict(
        JudicialRecord.objects.values_list("epoca")
        .annotate(c=Count("id"))
        .values_list("epoca", "c")
    )

    return Response(
        {
            "total": total,
            "by_tipo": by_tipo,
            "by_materia": by_materia,
            "by_epoca": by_epoca,
        }
    )
