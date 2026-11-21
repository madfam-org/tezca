"""UDI y tasa de retención sobre intereses, **leídas del texto del DOF**.

Mismas reglas que :mod:`apps.api.fiscal_dof_2026`: nada aquí es inferencia,
cada constante lleva el ``codigo`` de ``nota_detalle`` y su fecha, y una fila
publicada no se sobrescribe.

    https://dof.gob.mx/nota_detalle.php?codigo=<codigo>&fecha=<dd/mm/aaaa>

Leído el **2026-11-20** y el **2026-11-21** de ``nota_detalle``, de forma
directa y sin fuentes secundarias.

Lo que NO está aquí
-------------------
* Los avisos de la UDI anteriores o posteriores al del 10-11-2026. Cada aviso
  cubre unos quince días; publicar el siguiente es un paso de operación, con
  su propio ``codigo``.
* Tasas de retención de ejercicios anteriores a 2026: nadie en este repo leyó
  esas Leyes de Ingresos.
"""

VERIFIED_NOTE = (
    "Verificado el 2026-11-21 contra el texto del DOF (lectura directa de "
    "nota_detalle), sin fuentes secundarias. Provenance='published': la cita "
    "y el codigo identifican el documento exacto."
)


def _dof_url(codigo: str, fecha: str) -> str:
    """``fecha`` en ISO (aaaa-mm-dd); el DOF la quiere dd/mm/aaaa."""
    year, month, day = fecha.split("-")
    return f"https://dof.gob.mx/nota_detalle.php?codigo={codigo}&fecha={day}/{month}/{year}"


# ── UDI ────────────────────────────────────────────────────────────────────
# Banco de México, «Valor de la unidad de inversión», DOF 10-11-2026: «da a
# conocer el valor en pesos de la Unidad de Inversión, para los días del 11 al
# 25 de noviembre de 2026». Quince días, quince valores, tal como vienen.
UDI_AVISO_2026_11_10 = {
    "dof_date": "2026-11-10",
    "dof_codigo": "5803350",
    "source_citation": (
        "Banco de México, Valor de la unidad de inversión, DOF 10-11-2026 "
        "(días del 11 al 25 de noviembre de 2026)"
    ),
    "values": [
        ("2026-11-11", "8.899987"),
        ("2026-11-12", "8.902304"),
        ("2026-11-13", "8.904621"),
        ("2026-11-14", "8.906939"),
        ("2026-11-15", "8.909257"),
        ("2026-11-16", "8.911577"),
        ("2026-11-17", "8.913896"),
        ("2026-11-18", "8.916217"),
        ("2026-11-19", "8.918538"),
        ("2026-11-20", "8.920859"),
        ("2026-11-21", "8.923181"),
        ("2026-11-22", "8.925504"),
        ("2026-11-23", "8.927827"),
        ("2026-11-24", "8.930151"),
        ("2026-11-25", "8.932476"),
    ],
}

UDI_AVISOS = [UDI_AVISO_2026_11_10]


def udi_rows():
    """Una fila por día de cada aviso, lista para ``UDIValue``."""
    rows = []
    for aviso in UDI_AVISOS:
        for day, value in aviso["values"]:
            rows.append(
                {
                    "value": value,
                    "unit": "MXN/UDI",
                    "vigencia_from": day,
                    "vigencia_to": day,
                    "dof_date": aviso["dof_date"],
                    "dof_codigo": aviso["dof_codigo"],
                    "source_url": _dof_url(aviso["dof_codigo"], aviso["dof_date"]),
                    "source_citation": aviso["source_citation"],
                    "notes": VERIFIED_NOTE,
                }
            )
    return rows


# ── Retención sobre intereses ──────────────────────────────────────────────
# Ley de Ingresos de la Federación, artículo 24: «Durante el ejercicio fiscal
# de <año> la tasa de retención anual a que se refieren los artículos 54 y 135
# de la Ley del Impuesto sobre la Renta será del <tasa> por ciento.»
RETENCION_INTERESES = [
    {
        "year": 2026,
        "value": "0.90",
        "legal_basis": "LIF 2026 Art. 24; LISR Arts. 54 y 135",
        "vigencia_from": "2026-01-01",
        "vigencia_to": "2026-12-31",
        "dof_date": "2025-11-07",
        "dof_codigo": "5772357",
        "source_citation": (
            "Ley de Ingresos de la Federación para el Ejercicio Fiscal de 2026, "
            "artículo 24, DOF 07-11-2025"
        ),
    },
    {
        "year": 2027,
        "value": "0.68",
        "legal_basis": "LIF 2027 Art. 24; LISR Arts. 54 y 135",
        "vigencia_from": "2027-01-01",
        "vigencia_to": "2027-12-31",
        "dof_date": "2026-11-13",
        "dof_codigo": "5803757",
        "source_citation": (
            "Ley de Ingresos de la Federación para el Ejercicio Fiscal de 2027, "
            "artículo 24, DOF 13-11-2026"
        ),
    },
]


def retencion_rows():
    """Una fila por ejercicio, lista para ``RetencionIntereses``."""
    return [
        {
            **spec,
            "unit": "percent",
            "source_url": _dof_url(spec["dof_codigo"], spec["dof_date"]),
            "notes": VERIFIED_NOTE,
        }
        for spec in RETENCION_INTERESES
    ]
