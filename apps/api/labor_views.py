"""Feed laboral — Tezca como oráculo de la ley del trabajo.

    GET /api/v1/laws/<official_id>/articles/<article>/vigente/?on=YYYY-MM-DD
    GET /api/v1/labor/rules/?kind=&on=&payer_legal_form=&provider_regime=&service=
    GET /api/v1/labor/catalogos/?catalog=&code=&on=

Contrato C1 del programa «Cobertura laboral del HCM». Como el feed fiscal,
exige una API key (o JWT de Janua) con el scope ``read``, y **la consulta
principal es «qué regía el día X»** (``?on=``), porque ésa es la pregunta que
hace de verdad un cálculo de nómina o una compuerta de cumplimiento.

Fail-closed en serio
--------------------

Cuando no hay fila para lo que se pide, el endpoint devuelve 404 con
``detail`` explicando que Tezca prefiere no responder a responder con otra
vigencia. El consumidor (symbiosis-hcm) traduce eso a ``disclosed: pending``
y muestra la obligación con «ventana por publicar»: nunca inventa el número.

Toda respuesta lleva ``provenance``; el consumidor sólo debe calcular con
filas ``published``. ``seed-unverified`` es orientación, no cumplimiento.
"""

import logging

from django.db.models import Q
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .labor_models import LaborRule, LawArticle, SatCatalogEntry
from .labor_serializers import (
    serialize_labor_rule,
    serialize_law_article,
    serialize_sat_catalog_entry,
)

logger = logging.getLogger(__name__)

REQUIRED_SCOPE = "read"

DISCLAIMER = (
    "Tezca sirve reglas laborales como apoyo a la decisión, con procedencia "
    "explícita. Las filas cuya procedencia no es 'published' NO fueron "
    "verificadas contra una fuente primaria por Tezca y no deben presentarse "
    "como una afirmación de cumplimiento."
)


def _check_scope(request):
    """Devuelve una Response de error si quien llama no trae el scope 'read'."""
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return Response(
            {
                "error": (
                    "Authentication required. Provide an API key with the "
                    "X-API-Key header."
                )
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )
    scopes = getattr(user, "scopes", [])
    if REQUIRED_SCOPE not in scopes:
        return Response(
            {
                "error": f"Insufficient scope. Required: '{REQUIRED_SCOPE}'",
                "your_scopes": list(scopes),
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def _parse_on(request):
    """Lee ``?on=YYYY-MM-DD``. ``(fecha, None)`` | ``(None, Response)`` | ``(None, None)``."""
    raw = request.query_params.get("on")
    if not raw:
        return None, None
    parsed = parse_date(raw)
    if not parsed:
        return None, Response(
            {"error": "Invalid 'on' date. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return parsed, None


def _in_force_on(queryset, when):
    """Filtra a las filas vigentes el día ``when`` (effective_to NULL = vigente)."""
    return queryset.filter(effective_from__lte=when).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=when)
    )


ON_PARAM = OpenApiParameter(
    name="on",
    description=(
        "Devuelve sólo lo vigente en esta fecha (YYYY-MM-DD). Es la consulta "
        "principal del feed."
    ),
    required=False,
    type=str,
)


@extend_schema(
    tags=["Labor"],
    summary="Artículo de ley vigente en una fecha",
    description=(
        "Texto del artículo tal como regía el día pedido, con la reforma del "
        "DOF que lo fijó. Es la respuesta a «qué decía el artículo 59 de la "
        "LFT el 30 de abril de 2026», que el índice de búsqueda no puede dar "
        "porque guarda una sola foto sin vigencia. Sin ``?on=`` devuelve el "
        "texto vigente hoy. Requiere API key con scope 'read'."
    ),
    parameters=[ON_PARAM],
)
@api_view(["GET"])
def law_article_vigente(request, law_id: str, article: str):
    """Devuelve el texto de ``article`` de la ley ``law_id`` vigente en ``?on=``."""
    denied = _check_scope(request)
    if denied is not None:
        return denied

    on_date, err = _parse_on(request)
    if err is not None:
        return err

    from django.utils import timezone

    when = on_date or timezone.localdate()
    # El artículo se normaliza como en el corpus: '39-a' y '39-A' son el mismo.
    qs = LawArticle.objects.filter(official_id=law_id, article__iexact=article.strip())
    row = _in_force_on(qs, when).order_by("-effective_from").first()

    if row is None:
        existe = qs.exists()
        return Response(
            {
                "error": f"No hay texto vigente de {law_id} art. {article} en {when.isoformat()}.",
                "official_id": law_id,
                "article": article,
                "on": when.isoformat(),
                "detail": (
                    "Tezca falla en claro antes que servir el texto de otra "
                    "vigencia. "
                    + (
                        "El artículo está en el corpus pero ninguna versión "
                        "cubre esa fecha."
                        if existe
                        else "El artículo no está publicado todavía en el feed "
                        "laboral; un operador debe publicarlo."
                    )
                ),
                "disclaimer": DISCLAIMER,
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    data = serialize_law_article(row)
    data["on"] = when.isoformat()
    data["disclaimer"] = DISCLAIMER
    return Response(data)


@extend_schema(
    tags=["Labor"],
    summary="Reglas laborales estructuradas",
    description=(
        "Reglas laborales con vigencia y artículo: ventanas legales, topes, "
        "porcentajes de retención por (pagador × régimen del prestador), "
        "tablas y listas. Contrato C1. Filtra con ?kind=, ?on=, "
        "?payer_legal_form=, ?provider_regime= y ?service=. "
        "Requiere API key con scope 'read'."
    ),
    parameters=[
        ON_PARAM,
        OpenApiParameter(
            name="kind",
            description="Tipo de regla, p. ej. 'imss_alta_ventana_dias_habiles'.",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="payer_legal_form",
            description="'persona_moral', 'persona_fisica' o 'any'.",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="provider_regime",
            description="Clave del c_RegimenFiscal del prestador, p. ej. '612', '626'.",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="service",
            description="Tipo de servicio, p. ej. 'servicios_profesionales'.",
            required=False,
            type=str,
        ),
    ],
)
@api_view(["GET"])
def labor_rules_list(request):
    """Lista reglas laborales, filtrables por kind, fecha y dimensiones."""
    denied = _check_scope(request)
    if denied is not None:
        return denied

    on_date, err = _parse_on(request)
    if err is not None:
        return err

    kind = request.query_params.get("kind")
    valid_kinds = {choice.value for choice in LaborRule.Kind}
    if kind and kind not in valid_kinds:
        return Response(
            {"error": f"Invalid 'kind'. Valid: {sorted(valid_kinds)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payer = request.query_params.get("payer_legal_form")
    valid_payers = {choice.value for choice in LaborRule.PayerLegalForm}
    if payer and payer not in valid_payers:
        return Response(
            {"error": f"Invalid 'payer_legal_form'. Valid: {sorted(valid_payers)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    qs = LaborRule.objects.all()
    if on_date is not None:
        qs = _in_force_on(qs, on_date)
    if kind:
        qs = qs.filter(kind=kind)
    if payer:
        # Una regla marcada 'any' aplica a cualquier pagador, así que un
        # filtro por persona moral debe traerla también: si no, un consumidor
        # que filtra correctamente perdería la ventana del alta al IMSS.
        qs = qs.filter(
            Q(payer_legal_form=payer) | Q(payer_legal_form=LaborRule.PayerLegalForm.ANY)
        )
    regime = request.query_params.get("provider_regime")
    if regime:
        qs = qs.filter(Q(provider_regime=regime) | Q(provider_regime=""))
    service = request.query_params.get("service")
    if service:
        qs = qs.filter(Q(service=service) | Q(service=""))

    rows = [
        serialize_labor_rule(row)
        for row in qs.order_by("kind", "-effective_from", "payer_legal_form")
    ]

    payload = {
        "count": len(rows),
        "results": rows,
        "all_published": bool(rows)
        and all(r["provenance"] == "published" for r in rows),
        "disclaimer": DISCLAIMER,
    }
    if on_date is not None:
        payload["on"] = on_date.isoformat()
    return Response(payload)


@extend_schema(
    tags=["Labor"],
    summary="Catálogos del SAT para el CFDI 4.0",
    description=(
        "Claves de c_RegimenFiscal, c_TipoRegimen, c_TipoContrato y "
        "c_TipoJornada con su vigencia, tal como las publica el SAT. Un "
        "timbrado necesita saber que la clave estaba vigente el día del "
        "comprobante. Filtra con ?catalog=, ?code= y ?on=. "
        "Requiere API key con scope 'read'."
    ),
    parameters=[
        ON_PARAM,
        OpenApiParameter(
            name="catalog",
            description=(
                "'c_RegimenFiscal', 'c_TipoRegimen', 'c_TipoContrato' o "
                "'c_TipoJornada'."
            ),
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="code",
            description="Clave exacta, p. ej. '605'.",
            required=False,
            type=str,
        ),
    ],
)
@api_view(["GET"])
def sat_catalogos_list(request):
    """Lista claves de los catálogos del SAT, filtrables por catálogo y fecha."""
    denied = _check_scope(request)
    if denied is not None:
        return denied

    on_date, err = _parse_on(request)
    if err is not None:
        return err

    catalog = request.query_params.get("catalog")
    valid = {choice.value for choice in SatCatalogEntry.Catalog}
    if catalog and catalog not in valid:
        return Response(
            {"error": f"Invalid 'catalog'. Valid: {sorted(valid)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    qs = SatCatalogEntry.objects.all()
    if on_date is not None:
        qs = _in_force_on(qs, on_date)
    if catalog:
        qs = qs.filter(catalog=catalog)
    code = request.query_params.get("code")
    if code:
        qs = qs.filter(code=code.strip())

    rows = [
        serialize_sat_catalog_entry(row)
        for row in qs.order_by("catalog", "code", "-effective_from")
    ]

    payload = {
        "count": len(rows),
        "results": rows,
        "all_published": bool(rows)
        and all(r["provenance"] == "published" for r in rows),
        "disclaimer": DISCLAIMER,
    }
    if on_date is not None:
        payload["on"] = on_date.isoformat()
    return Response(payload)
