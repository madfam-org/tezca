"""Serialización del feed laboral.

Funciones planas, como el feed fiscal (``fiscal_serializers``), y con los
mismos nombres de campo donde el significado es el mismo: un consumidor que
ya lee ``provenance`` / ``source_url`` / ``dof_codigo`` en el feed fiscal no
aprende un vocabulario nuevo aquí.

El contrato C1 fija las llaves de ``serialize_labor_rule``: ``kind``,
``value``, ``unit``, ``effective_from``, ``effective_to``, ``official_id``,
``article``, ``source``, ``source_url``, ``dof_codigo`` y ``provenance``. Se
añaden campos, nunca se quitan ni se renombran.
"""


def _provenance_block(row):
    """Los campos de procedencia que lleva toda fila del feed laboral."""
    return {
        "official_id": row.official_id,
        "article": row.article,
        "source": row.source,
        "source_url": row.source_url,
        "dof_date": row.dof_date.isoformat() if row.dof_date else None,
        "dof_codigo": row.dof_codigo,
        "provenance": row.provenance,
        # La frontera aserción/orientación, explícita para que el consumidor
        # no tenga que comparar cadenas.
        "is_verified": row.provenance == "published",
        "notes": row.notes,
    }


def _vigencia_block(row):
    """El periodo en que la fila rige."""
    return {
        "effective_from": row.effective_from.isoformat(),
        "effective_to": row.effective_to.isoformat() if row.effective_to else None,
        "in_force": row.effective_to is None,
    }


def serialize_law_article(row):
    """Serializa un :class:`LawArticle`."""
    data = {
        "text": row.text,
        "edition": row.edition,
        "derogado": row.derogado,
        "reformas_dof": row.reformas_dof,
    }
    data.update(_vigencia_block(row))
    data.update(_provenance_block(row))
    return data


def serialize_labor_rule(row):
    """Serializa un :class:`LaborRule` con la forma del contrato C1."""
    data = {
        "kind": row.kind,
        "kind_label": row.get_kind_display(),
        "label": row.label,
        "value": row.value,
        "unit": row.unit,
        "payer_legal_form": row.payer_legal_form,
        "provider_regime": row.provider_regime,
        "service": row.service,
    }
    data.update(_vigencia_block(row))
    data.update(_provenance_block(row))
    return data


def serialize_sat_catalog_entry(row):
    """Serializa una :class:`SatCatalogEntry`."""
    data = {
        "catalog": row.catalog,
        "code": row.code,
        "label": row.label,
        "aplica_fisica": row.aplica_fisica,
        "aplica_moral": row.aplica_moral,
    }
    data.update(_vigencia_block(row))
    data.update(_provenance_block(row))
    return data
