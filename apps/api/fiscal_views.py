"""Fiscal-value feed — Tezca as the ecosystem's source of fiscal values.

    GET /api/v1/fiscal/uma/                  UMA rows (filterable by year / ?on=)
    GET /api/v1/fiscal/uma/current/          the UMA in force today
    GET /api/v1/fiscal/minimos/              salario mínimo general + ZLFN
    GET /api/v1/fiscal/tipo-cambio/          DOF exchange rates (?from=/?to=/?on=)
    GET /api/v1/fiscal/tipo-cambio/current/  the DOF rate in force today
    GET /api/v1/fiscal/tables/               ISR / subsidio / IMSS / ISN tables
    GET /api/v1/fiscal/tables/<year>/        all tables for one fiscal year

Requires an API key (or Janua JWT) carrying the 'read' scope — the same key
scheme the changelog and bulk feeds use, so usage lands in APIUsageLog via
the global UsageLoggingMiddleware with no per-view work.

**The primary query shape is "value in force on a date"** (``?on=YYYY-MM-DD``),
not "value for a year", because that is the question a payroll or offer
calculation actually asks.

Every response carries provenance. A consumer must not present a value whose
provenance is not ``published`` as a compliance assertion: Tezca states what
it knows and how well it knows it, and the caller decides.
"""

import logging

from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .fiscal_models import FiscalTable, MinimumWage, Provenance, TipoDeCambio, UMAValue
from .fiscal_serializers import (
    serialize_fiscal_table,
    serialize_minimum_wage,
    serialize_tipo_cambio,
    serialize_uma,
)

logger = logging.getLogger(__name__)

REQUIRED_SCOPE = "read"

# Stated on every response so a consumer never has to infer the posture.
DISCLAIMER = (
    "Tezca serves fiscal values as decision-support with explicit provenance. "
    "Rows whose provenance is not 'published' are NOT DOF-verified by Tezca "
    "and must not be presented as a compliance assertion."
)


def _check_scope(request):
    """Return an error Response if the caller lacks the 'read' scope."""
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
    """Parse ``?on=YYYY-MM-DD``.

    Returns ``(date, None)`` on success, ``(None, Response)`` on a bad value,
    and ``(None, None)`` when the caller did not ask for a point in time.
    """
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


def _parse_year(request):
    """Parse ``?year=YYYY``. Returns ``(year, None)`` or ``(None, Response)``."""
    raw = request.query_params.get("year")
    if not raw:
        return None, None
    try:
        year = int(raw)
    except (TypeError, ValueError):
        return None, Response(
            {"error": "Invalid 'year'. Use a four-digit year, e.g. 2026."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return year, None


def _in_force_on(queryset, when):
    """Narrow to rows in force on ``when`` (vigencia_to NULL = still in force)."""
    from django.db.models import Q

    return queryset.filter(vigencia_from__lte=when).filter(
        Q(vigencia_to__isnull=True) | Q(vigencia_to__gte=when)
    )


ON_PARAM = OpenApiParameter(
    name="on",
    description=(
        "Return only the value(s) in force on this date (YYYY-MM-DD). "
        "This is the primary query shape."
    ),
    required=False,
    type=str,
)
YEAR_PARAM = OpenApiParameter(
    name="year",
    description="Filter to a single fiscal year, e.g. 2026.",
    required=False,
    type=int,
)


@extend_schema(
    tags=["Fiscal"],
    summary="UMA values",
    description=(
        "Unidad de Medida y Actualización (daily/monthly/annual) per year. "
        "Set by INEGI, DOF-published each January, in force from 1 February. "
        "UMA is NOT the minimum wage (LFVUMA Art. 4): obligations, fines and "
        "caps are denominated in UMA; wages in salario mínimo. "
        "Requires an API key with 'read' scope."
    ),
    parameters=[ON_PARAM, YEAR_PARAM],
)
@api_view(["GET"])
def uma_list(request):
    """List UMA values, newest first, optionally filtered by date or year."""
    denied = _check_scope(request)
    if denied is not None:
        return denied

    on_date, err = _parse_on(request)
    if err is not None:
        return err
    year, err = _parse_year(request)
    if err is not None:
        return err

    qs = UMAValue.objects.all()
    if on_date is not None:
        qs = _in_force_on(qs, on_date)
    if year is not None:
        qs = qs.filter(year=year)

    rows = [serialize_uma(row) for row in qs.order_by("-vigencia_from")]

    payload = {
        "count": len(rows),
        "results": rows,
        "disclaimer": DISCLAIMER,
    }
    if on_date is not None:
        payload["on"] = on_date.isoformat()
        # Convenience for the single-value question the consumer really asks.
        # symbiosis-hcm's TezcaFiscalClient.get_uma_for_date() reads the flat
        # top-level "value"/"year"/"effective_date" keys.
        if rows:
            payload.update(
                {
                    "value": rows[0]["value"],
                    "year": rows[0]["year"],
                    "effective_date": rows[0]["vigencia_from"],
                    "provenance": rows[0]["provenance"],
                }
            )
    return Response(payload)


@extend_schema(
    tags=["Fiscal"],
    summary="Current UMA",
    description=(
        "The UMA in force today. Returns 404 when no row covers today — a "
        "deliberate fail-closed: a consumer must never silently fall back to "
        "a stale hardcoded UMA. Requires an API key with 'read' scope."
    ),
)
@api_view(["GET"])
def uma_current(request):
    """Return the single UMA row in force today."""
    denied = _check_scope(request)
    if denied is not None:
        return denied

    today = timezone.localdate()
    row = _in_force_on(UMAValue.objects.all(), today).order_by("-vigencia_from").first()
    if row is None:
        return Response(
            {
                "error": "No UMA value on file for today.",
                "on": today.isoformat(),
                "detail": (
                    "Tezca fails closed rather than serving a stale value. "
                    "An operator must publish the current UMA."
                ),
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    data = serialize_uma(row)
    # Flat keys match symbiosis-hcm's TezcaFiscalClient.get_current_uma().
    data["on"] = today.isoformat()
    data["effective_date"] = data["vigencia_from"]
    data["disclaimer"] = DISCLAIMER
    return Response(data)


def _parse_pair(request):
    """Read ?from=/?to= currency filters (default USD/MXN, the DOF daily pair)."""
    frm = (request.query_params.get("from") or "USD").strip().upper()
    to = (request.query_params.get("to") or "MXN").strip().upper()
    return frm, to


FROM_PARAM = OpenApiParameter(
    name="from",
    description="Base currency ISO 4217 (default USD — the DOF daily pair).",
    required=False,
    type=str,
)
TO_PARAM = OpenApiParameter(
    name="to",
    description="Quote currency ISO 4217 (default MXN).",
    required=False,
    type=str,
)


@extend_schema(
    tags=["Fiscal"],
    summary="Tipo de cambio (DOF)",
    description=(
        "DOF reference exchange rate — *tipo de cambio para solventar "
        "obligaciones denominadas en moneda extranjera*, published by Banco "
        "de México in the DOF each business day. This is the SAT-defensible "
        "rate for converting foreign-currency fiscal obligations (LIVA Art. "
        "20, CFF Art. 20), NOT a market/spot quote. Filter by ?from=/?to= "
        "and ?on=. Requires an API key with 'read' scope."
    ),
    parameters=[ON_PARAM, FROM_PARAM, TO_PARAM],
)
@api_view(["GET"])
def tipo_cambio_list(request):
    """List DOF exchange rates, newest first, optionally filtered by date/pair."""
    denied = _check_scope(request)
    if denied is not None:
        return denied

    on_date, err = _parse_on(request)
    if err is not None:
        return err
    frm, to = _parse_pair(request)

    qs = TipoDeCambio.objects.filter(from_currency=frm, to_currency=to)
    if on_date is not None:
        qs = _in_force_on(qs, on_date)

    rows = [serialize_tipo_cambio(row) for row in qs.order_by("-vigencia_from")]

    payload = {
        "count": len(rows),
        "results": rows,
        "disclaimer": DISCLAIMER,
    }
    if on_date is not None:
        payload["on"] = on_date.isoformat()
        if rows:
            payload.update(
                {
                    "value": rows[0]["value"],
                    "rate": rows[0]["value"],
                    "pair": rows[0]["pair"],
                    "effective_date": rows[0]["vigencia_from"],
                    "provenance": rows[0]["provenance"],
                }
            )
    return Response(payload)


@extend_schema(
    tags=["Fiscal"],
    summary="Current tipo de cambio (DOF)",
    description=(
        "The DOF reference exchange rate in force today for the given pair "
        "(default USD/MXN). Returns 404 when no row covers today — a "
        "deliberate fail-closed: a consumer must never silently substitute a "
        "stale or market rate on a fiscal document. Requires 'read' scope."
    ),
    parameters=[FROM_PARAM, TO_PARAM],
)
@api_view(["GET"])
def tipo_cambio_current(request):
    """Return the single DOF exchange rate in force today for the pair."""
    denied = _check_scope(request)
    if denied is not None:
        return denied

    frm, to = _parse_pair(request)
    today = timezone.localdate()
    row = (
        _in_force_on(
            TipoDeCambio.objects.filter(from_currency=frm, to_currency=to), today
        )
        .order_by("-vigencia_from")
        .first()
    )
    if row is None:
        return Response(
            {
                "error": f"No DOF exchange rate on file for {frm}/{to} today.",
                "on": today.isoformat(),
                "pair": f"{frm}/{to}",
                "detail": (
                    "Tezca fails closed rather than serving a stale or market "
                    "rate. An operator must publish the current DOF rate."
                ),
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    data = serialize_tipo_cambio(row)
    # Flat keys mirror uma_current for an FX client's get_current_dof_rate().
    data["on"] = today.isoformat()
    data["effective_date"] = data["vigencia_from"]
    data["disclaimer"] = DISCLAIMER
    return Response(data)


@extend_schema(
    tags=["Fiscal"],
    summary="Salario mínimo",
    description=(
        "Salario mínimo general and Zona Libre de la Frontera Norte (ZLFN), "
        "per CONASAMI resolutions published in the DOF, in force each "
        "1 January. Filter with ?zone=general|zlfn. "
        "Requires an API key with 'read' scope."
    ),
    parameters=[
        ON_PARAM,
        YEAR_PARAM,
        OpenApiParameter(
            name="zone",
            description="'general' (resto del país) or 'zlfn'.",
            required=False,
            type=str,
        ),
    ],
)
@api_view(["GET"])
def minimos_list(request):
    """List minimum-wage values, optionally filtered by date, year or zone."""
    denied = _check_scope(request)
    if denied is not None:
        return denied

    on_date, err = _parse_on(request)
    if err is not None:
        return err
    year, err = _parse_year(request)
    if err is not None:
        return err

    zone = request.query_params.get("zone")
    valid_zones = {choice.value for choice in MinimumWage.Zone}
    if zone and zone not in valid_zones:
        return Response(
            {
                "error": f"Invalid 'zone'. Valid: {sorted(valid_zones)}",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    qs = MinimumWage.objects.all()
    if on_date is not None:
        qs = _in_force_on(qs, on_date)
    if year is not None:
        qs = qs.filter(year=year)
    if zone:
        qs = qs.filter(zone=zone)

    rows = [
        serialize_minimum_wage(row) for row in qs.order_by("-vigencia_from", "zone")
    ]

    payload = {
        "count": len(rows),
        "results": rows,
        "disclaimer": DISCLAIMER,
    }
    if on_date is not None:
        payload["on"] = on_date.isoformat()
    return Response(payload)


@extend_schema(
    tags=["Fiscal"],
    summary="Fiscal tables",
    description=(
        "Structured fiscal tables keyed by fiscal year: ISR retention "
        "brackets (LISR Art. 96), subsidio al empleo, IMSS cuotas, and ISN "
        "rates by state. Filter with ?kind= and ?year= or ?on=. "
        "Requires an API key with 'read' scope."
    ),
    parameters=[
        ON_PARAM,
        YEAR_PARAM,
        OpenApiParameter(
            name="kind",
            description=(
                "One of: isr_monthly, isr_annual, subsidio_monthly, "
                "imss_rates, isn_rates."
            ),
            required=False,
            type=str,
        ),
    ],
)
@api_view(["GET"])
def tables_list(request):
    """List fiscal tables, optionally filtered by kind, year or date."""
    denied = _check_scope(request)
    if denied is not None:
        return denied

    on_date, err = _parse_on(request)
    if err is not None:
        return err
    year, err = _parse_year(request)
    if err is not None:
        return err

    kind = request.query_params.get("kind")
    valid_kinds = {choice.value for choice in FiscalTable.Kind}
    if kind and kind not in valid_kinds:
        return Response(
            {"error": f"Invalid 'kind'. Valid: {sorted(valid_kinds)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    qs = FiscalTable.objects.all()
    if on_date is not None:
        qs = _in_force_on(qs, on_date)
    if year is not None:
        qs = qs.filter(year=year)
    if kind:
        qs = qs.filter(kind=kind)

    rows = [serialize_fiscal_table(row) for row in qs.order_by("-year", "kind")]

    payload = {
        "count": len(rows),
        "results": rows,
        "disclaimer": DISCLAIMER,
    }
    if on_date is not None:
        payload["on"] = on_date.isoformat()
    return Response(payload)


@extend_schema(
    tags=["Fiscal"],
    summary="Fiscal tables for a year",
    description=(
        "All fiscal tables for one fiscal year, grouped by kind. This is the "
        "shape symbiosis-hcm's TezcaFiscalClient.get_fiscal_tables(year) "
        "consumes: isr_brackets, subsidio, imss_rates, isn_rates. "
        "Requires an API key with 'read' scope."
    ),
)
@api_view(["GET"])
def tables_by_year(request, year: int):
    """Return every table for ``year``, keyed by the consumer's field names."""
    denied = _check_scope(request)
    if denied is not None:
        return denied

    rows = list(FiscalTable.objects.filter(year=year).order_by("kind"))
    if not rows:
        return Response(
            {
                "error": f"No fiscal tables on file for {year}.",
                "year": year,
                "detail": (
                    "Tezca fails closed rather than serving another year's "
                    "tables. An operator must publish this year's tables."
                ),
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    by_kind = {row.kind: serialize_fiscal_table(row) for row in rows}

    def _rows_for(kind):
        entry = by_kind.get(kind)
        return entry["rows"] if entry else None

    return Response(
        {
            "year": year,
            # Consumer-facing names (symbiosis TezcaFiscalClient).
            "isr_brackets": _rows_for(FiscalTable.Kind.ISR_MONTHLY),
            "subsidio": _rows_for(FiscalTable.Kind.SUBSIDIO_MONTHLY),
            "imss_rates": _rows_for(FiscalTable.Kind.IMSS_RATES),
            "isn_rates": _rows_for(FiscalTable.Kind.ISN_RATES),
            # Full rows with per-table provenance, so a caller can check
            # whether the numbers it just took are DOF-verified.
            "tables": by_kind,
            "provenance_summary": {
                kind: entry["provenance"] for kind, entry in by_kind.items()
            },
            "all_published": all(
                entry["provenance"] == Provenance.PUBLISHED
                for entry in by_kind.values()
            ),
            "disclaimer": DISCLAIMER,
        }
    )
