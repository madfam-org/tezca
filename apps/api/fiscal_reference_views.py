"""Fiscal-value feed, reference series: the UDI and the interest withholding rate.

    GET /api/v1/fiscal/udi/                    UDI por día (?on= / ?from=&to=)
    GET /api/v1/fiscal/udi/current/            la UDI de hoy
    GET /api/v1/fiscal/retencion-intereses/    tasa anual de retención (?year=)

Mismas reglas que el resto del feed (:mod:`apps.api.fiscal_views`): scope
``read``, procedencia en cada fila y fallo cerrado. Viven en su propio módulo
para que ``fiscal_views`` siga bajo el techo de tamaño.

Las dos series existen para quien compara instrumentos financieros: los
límites de protección al ahorro y varios umbrales se expresan en UDIS, y el
rendimiento después de impuestos necesita la tasa de retención del ejercicio.
"""

from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .fiscal_models import RetencionIntereses, UDIValue
from .fiscal_serializers import serialize_retencion_intereses, serialize_udi
from .fiscal_views import (
    DISCLAIMER,
    ON_PARAM,
    YEAR_PARAM,
    _check_scope,
    _parse_on,
    _parse_year,
)

# Un aviso del Banco cubre quince o dieciséis días; un año son 366 filas.
MAX_RANGE_DAYS = 366

RANGE_FROM_PARAM = OpenApiParameter(
    name="from",
    description="Primer día del rango (YYYY-MM-DD), inclusive. Va con ?to=.",
    required=False,
    type=str,
)
RANGE_TO_PARAM = OpenApiParameter(
    name="to",
    description="Último día del rango (YYYY-MM-DD), inclusive. Va con ?from=.",
    required=False,
    type=str,
)


def _parse_range(request):
    """Parse ``?from=&to=``. Returns ``(start, end, None)`` or ``(None, None, Response)``.

    Both absent is ``(None, None, None)``. One without the other, an unreadable
    date, an inverted range or one longer than a year is a 400: a silent
    default here would hand back a different series than the caller asked for.
    """
    raw_from = request.query_params.get("from")
    raw_to = request.query_params.get("to")
    if not raw_from and not raw_to:
        return None, None, None

    def bad(message):
        return (
            None,
            None,
            Response({"error": message}, status=status.HTTP_400_BAD_REQUEST),
        )

    if not raw_from or not raw_to:
        return bad("Give both 'from' and 'to' (YYYY-MM-DD), or neither.")
    start, end = parse_date(raw_from), parse_date(raw_to)
    if not start or not end:
        return bad("Invalid 'from' or 'to' date. Use YYYY-MM-DD.")
    if end < start:
        return bad("'to' must not be before 'from'.")
    if (end - start).days >= MAX_RANGE_DAYS:
        return bad(f"Range too long. Ask for at most {MAX_RANGE_DAYS} days.")
    return start, end, None


@extend_schema(
    tags=["Fiscal"],
    summary="UDI (valor diario)",
    description=(
        "Valor en pesos de la Unidad de Inversión por día, como lo publica el "
        "Banco de México en el DOF. Una fila por día. Consulta un día con "
        "?on= o un rango con ?from=&to= (máximo un año); sin filtros devuelve "
        "los 31 días más recientes. Un día sin fila NO se rellena con el "
        "valor anterior. Requiere una API key con scope 'read'."
    ),
    parameters=[ON_PARAM, RANGE_FROM_PARAM, RANGE_TO_PARAM],
)
@api_view(["GET"])
def udi_list(request):
    """List UDI values, newest first, for a day, a range or the latest month."""
    denied = _check_scope(request)
    if denied is not None:
        return denied

    on_date, err = _parse_on(request)
    if err is not None:
        return err
    start, end, err = _parse_range(request)
    if err is not None:
        return err
    if on_date is not None and start is not None:
        return Response(
            {"error": "Use 'on' or 'from'/'to', not both."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    qs = UDIValue.objects.order_by("-vigencia_from")
    if on_date is not None:
        qs = qs.filter(vigencia_from=on_date)
    elif start is not None:
        qs = qs.filter(vigencia_from__gte=start, vigencia_from__lte=end)
    else:
        qs = qs[:31]

    rows = [serialize_udi(row) for row in qs]
    payload = {"count": len(rows), "results": rows, "disclaimer": DISCLAIMER}
    if on_date is not None:
        payload["on"] = on_date.isoformat()
        if rows:
            payload.update(
                {"value": rows[0]["value"], "provenance": rows[0]["provenance"]}
            )
    elif start is not None:
        payload["from"], payload["to"] = start.isoformat(), end.isoformat()
    return Response(payload)


@extend_schema(
    tags=["Fiscal"],
    summary="UDI de hoy",
    description=(
        "El valor de la UDI para hoy. Devuelve 404 si no hay fila para hoy: "
        "fallo cerrado deliberado, para que nadie convierta un límite en UDIS "
        "con un valor de otro día sin saberlo. Requiere scope 'read'."
    ),
)
@api_view(["GET"])
def udi_current(request):
    """Return today's UDI value, or 404 when it has not been published here."""
    denied = _check_scope(request)
    if denied is not None:
        return denied

    today = timezone.localdate()
    row = UDIValue.objects.filter(vigencia_from=today).first()
    if row is None:
        latest = UDIValue.objects.order_by("-vigencia_from").first()
        return Response(
            {
                "error": "No UDI value on file for today.",
                "on": today.isoformat(),
                "latest_on_file": latest.vigencia_from.isoformat() if latest else None,
                "detail": (
                    "Tezca fails closed rather than serving another day's "
                    "value. An operator must publish the current DOF notice."
                ),
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    data = serialize_udi(row)
    data["on"] = today.isoformat()
    data["disclaimer"] = DISCLAIMER
    return Response(data)


@extend_schema(
    tags=["Fiscal"],
    summary="Tasa de retención sobre intereses",
    description=(
        "Tasa anual de retención del ISR sobre el capital que da lugar al "
        "pago de intereses (LISR Arts. 54 y 135), que fija cada año la Ley de "
        "Ingresos de la Federación. Una fila por ejercicio; filtra con ?year=. "
        "Un ejercicio sin Ley de Ingresos publicada no tiene fila: el "
        "consumidor debe negarse a calcularlo. Requiere scope 'read'."
    ),
    parameters=[YEAR_PARAM],
)
@api_view(["GET"])
def retencion_intereses_list(request):
    """List the yearly withholding rate on interest, newest year first."""
    denied = _check_scope(request)
    if denied is not None:
        return denied

    year, err = _parse_year(request)
    if err is not None:
        return err

    qs = RetencionIntereses.objects.order_by("-year")
    if year is not None:
        qs = qs.filter(year=year)

    rows = [serialize_retencion_intereses(row) for row in qs]
    payload = {"count": len(rows), "results": rows, "disclaimer": DISCLAIMER}
    if year is not None:
        payload["year"] = year
        if rows:
            payload.update(
                {
                    "value": rows[0]["value"],
                    "tasa": rows[0]["tasa"],
                    "provenance": rows[0]["provenance"],
                }
            )
    return Response(payload)
