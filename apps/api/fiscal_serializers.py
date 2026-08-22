"""Serialization for the fiscal-value feed.

Plain functions rather than DRF serializer classes, matching the style of
the other read-only feeds in this app (changelog, coverage, graph).

Decimals are emitted as strings so a consumer can build an exact
``Decimal`` without a float round-trip — a cent lost to binary floating
point in a payroll figure is a real defect, not a cosmetic one.
"""


def _provenance_block(row):
    """The provenance fields every fiscal row carries."""
    return {
        "provenance": row.provenance,
        "is_verified": row.provenance == "published",
        "source_citation": row.source_citation,
        "source_url": row.source_url,
        "dof_date": row.dof_date.isoformat() if row.dof_date else None,
        "notes": row.notes,
    }


def _vigencia_block(row):
    """The period a row is in force."""
    return {
        "vigencia_from": row.vigencia_from.isoformat(),
        "vigencia_to": row.vigencia_to.isoformat() if row.vigencia_to else None,
        "in_force": row.vigencia_to is None,
    }


def serialize_uma(row):
    """Serialize a :class:`UMAValue`."""
    data = {
        "year": row.year,
        "value": str(row.value),
        "daily_value": str(row.value),
        "monthly_value": str(row.monthly_value),
        "annual_value": str(row.annual_value),
        "unit": row.unit,
    }
    data.update(_vigencia_block(row))
    data.update(_provenance_block(row))
    return data


def serialize_minimum_wage(row):
    """Serialize a :class:`MinimumWage`."""
    data = {
        "year": row.year,
        "zone": row.zone,
        "zone_label": row.get_zone_display(),
        "value": str(row.value),
        "unit": row.unit,
    }
    data.update(_vigencia_block(row))
    data.update(_provenance_block(row))
    return data


def serialize_fiscal_table(row):
    """Serialize a :class:`FiscalTable`."""
    data = {
        "kind": row.kind,
        "kind_label": row.get_kind_display(),
        "year": row.year,
        "period": row.period,
        "legal_basis": row.legal_basis,
        "rows": row.rows,
        "row_count": len(row.rows) if isinstance(row.rows, list) else 0,
    }
    data.update(_vigencia_block(row))
    data.update(_provenance_block(row))
    return data
