"""Compuerta de coherencia de las cuotas IMSS y de las tasas estatales del ISN.

Misma idea que :mod:`apps.api.fiscal_coherence` para las tarifas del ISR: una
transcripción equivocada rompe identidades que el propio texto legal impone, y
eso se puede comprobar sin volver a abrir el DOF. No sustituye la lectura de la
fuente: la abarata.

Identidades que se vigilan (cada una sale de un artículo, no de una costumbre):

* **Arts. 25 y 107 LSS** reparten su cuota 70 % patrón / 25 % trabajador /
  5 % Estado. En ambos renglones, ``patron x 25 == trabajador x 70``.
* **Transitorio DÉCIMO NOVENO (1995)** — diez ajustes anuales de 1998 a 2007:
  cuota fija ``0.139 + 10 x 0.0065``; excedente ``0.06 - 10 x 0.0049``
  (patrón) y ``0.02 - 10 x 0.0016`` (trabajador).
* **Tabla del transitorio SEGUNDO (DOF 16-12-2020)** — la primera banda se mide
  en salarios mínimos y llega hasta 1.00; las demás en UMA con límites
  superiores crecientes; la última es abierta; las tasas crecen banda a banda
  (así es la tabla en cada una de sus ocho columnas, 2023-2030).
* **Tope del SBC** — el renglón ``tope_sbc`` repite el multiplicador de la regla
  laboral ``sbc_tope_veces_uma`` vigente; si discrepan, una de las dos está mal.
* **ISN** — tasa positiva y menor a 10 %; dentro de una entidad, ninguna
  vigencia se superpone con otra.

Y la regla de procedencia: una tabla ``published`` no puede tener un renglón
que no lo sea.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

CONCEPTOS_REQUERIDOS = (
    "em_cuota_fija",
    "em_excedente",
    "em_prestaciones_dinero",
    "em_gastos_medicos_pensionados",
    "invalidez_vida",
    "retiro",
    "cesantia_vejez",
    "guarderias_prestaciones_sociales",
    "infonavit",
    "tope_sbc",
)

UNIDADES = ("uma", "salario_minimo")


def _dec(raw):
    if raw is None:
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return None


def incoherencias_imss(rows, *, provenance="published", tope_regla_laboral=None):
    """Devuelve la lista de problemas de una tabla ``imss_rates``; vacía si cuadra.

    ``tope_regla_laboral`` es el ``value`` de la regla ``sbc_tope_veces_uma``
    vigente (``{"veces": 25, "unidad": "uma", ...}``), cuando el llamador la
    tiene; sin ella esa identidad no se comprueba.
    """
    problemas = []
    por_concepto = {}
    for row in rows:
        concepto = row.get("concepto")
        if concepto in por_concepto:
            problemas.append(f"concepto repetido: {concepto}")
        por_concepto[concepto] = row
        if provenance == "published" and row.get("provenance") != "published":
            problemas.append(
                f"{concepto}: la tabla es published y el renglón es "
                f"{row.get('provenance')!r}"
            )
        for parte in ("patron", "trabajador"):
            raw = row.get(parte)
            if raw is None:
                continue
            tasa = _dec(raw)
            if tasa is None or not (Decimal("0") <= tasa < Decimal("1")):
                problemas.append(f"{concepto}.{parte}: tasa fuera de [0, 1): {raw!r}")

    faltan = [c for c in CONCEPTOS_REQUERIDOS if c not in por_concepto]
    if faltan:
        problemas.append(f"faltan conceptos: {', '.join(faltan)}")

    for concepto in ("em_prestaciones_dinero", "em_gastos_medicos_pensionados"):
        row = por_concepto.get(concepto)
        if row is None:
            continue
        patron, trabajador = _dec(row.get("patron")), _dec(row.get("trabajador"))
        if patron is None or trabajador is None or patron * 25 != trabajador * 70:
            problemas.append(
                f"{concepto}: patrón {row.get('patron')} y trabajador "
                f"{row.get('trabajador')} no reparten 70/25"
            )

    fija = por_concepto.get("em_cuota_fija")
    if fija is not None and _dec(fija.get("patron")) != Decimal("0.139") + 10 * Decimal(
        "0.0065"
    ):
        problemas.append(
            f"em_cuota_fija: {fija.get('patron')} no es 13.9 % + 10 x 0.65 puntos"
        )
    excedente = por_concepto.get("em_excedente")
    if excedente is not None:
        if _dec(excedente.get("patron")) != Decimal("0.06") - 10 * Decimal("0.0049"):
            problemas.append(
                f"em_excedente.patron: {excedente.get('patron')} no es 6 % - 10 x 0.49"
            )
        if _dec(excedente.get("trabajador")) != Decimal("0.02") - 10 * Decimal(
            "0.0016"
        ):
            problemas.append(
                f"em_excedente.trabajador: {excedente.get('trabajador')} no es "
                "2 % - 10 x 0.16"
            )
        umbral = excedente.get("umbral") or {}
        if umbral.get("unidad") != "uma" or _dec(umbral.get("veces")) != Decimal("3"):
            problemas.append(f"em_excedente.umbral: {umbral!r} no es 3 UMA")

    cev = por_concepto.get("cesantia_vejez")
    if cev is not None:
        problemas.extend(incoherencias_bandas_cev(cev.get("bandas_patron") or []))

    tope = por_concepto.get("tope_sbc")
    if tope is not None and tope_regla_laboral is not None:
        de_tabla = tope.get("tope") or {}
        if _dec(de_tabla.get("veces")) != _dec(
            tope_regla_laboral.get("veces")
        ) or de_tabla.get("unidad") != tope_regla_laboral.get("unidad"):
            problemas.append(
                f"tope_sbc: la tabla dice {de_tabla!r} y la regla laboral "
                f"sbc_tope_veces_uma dice {tope_regla_laboral.get('veces')} "
                f"{tope_regla_laboral.get('unidad')}"
            )
    return problemas


def incoherencias_bandas_cev(bandas):
    """Problemas de forma de la tabla de cesantía y vejez patronal."""
    problemas = []
    if len(bandas) < 2:
        return ["cesantia_vejez: la tabla patronal necesita al menos dos bandas"]
    primera = bandas[0]
    hasta = primera.get("hasta") or {}
    if (
        primera.get("desde") is not None
        or hasta.get("unidad") != "salario_minimo"
        or _dec(hasta.get("veces")) != Decimal("1.00")
    ):
        problemas.append("cesantia_vejez: la primera banda debe ser «1.0 SM»")
    if bandas[-1].get("hasta") is not None:
        problemas.append("cesantia_vejez: la última banda debe ser abierta")

    tasas = [_dec(b.get("tasa_patron")) for b in bandas]
    if any(t is None or not (Decimal("0") < t < Decimal("1")) for t in tasas):
        problemas.append(f"cesantia_vejez: tasas fuera de (0, 1): {tasas!r}")
    elif any(b <= a for a, b in zip(tasas, tasas[1:])):
        problemas.append(f"cesantia_vejez: las tasas no crecen banda a banda: {tasas}")

    limites_uma = []
    for banda in bandas[1:-1]:
        limite = banda.get("hasta") or {}
        if limite.get("unidad") not in UNIDADES:
            problemas.append(f"cesantia_vejez {banda.get('texto')}: unidad desconocida")
        if limite.get("unidad") == "uma":
            limites_uma.append(_dec(limite.get("veces")))
    if any(v is None for v in limites_uma) or any(
        b <= a for a, b in zip(limites_uma, limites_uma[1:])
    ):
        problemas.append(
            f"cesantia_vejez: los límites en UMA no crecen: {limites_uma!r}"
        )
    return problemas


def incoherencias_isn(filas):
    """Problemas de un conjunto de tasas estatales (dicts con la forma del seed).

    Cada fila trae ``entidad``, ``value`` (porcentaje), ``vigencia_from`` y
    ``vigencia_to`` (ISO o ``None``).
    """
    problemas = []
    por_entidad = {}
    for fila in filas:
        tasa = _dec(fila.get("value"))
        if tasa is None or not (Decimal("0") < tasa < Decimal("10")):
            problemas.append(
                f"ISN {fila.get('entidad')}: tasa {fila.get('value')!r} fuera de (0, 10) %"
            )
        por_entidad.setdefault(fila.get("entidad"), []).append(fila)
    for entidad, propias in por_entidad.items():
        tramos = sorted(
            (
                date.fromisoformat(str(f["vigencia_from"])),
                (
                    date.fromisoformat(str(f["vigencia_to"]))
                    if f.get("vigencia_to")
                    else None
                ),
            )
            for f in propias
        )
        for (inicio_a, fin_a), (inicio_b, _fin_b) in zip(tramos, tramos[1:]):
            if fin_a is None or fin_a >= inicio_b:
                problemas.append(
                    f"ISN {entidad}: la vigencia que empieza {inicio_a} se superpone "
                    f"con la que empieza {inicio_b}"
                )
    return problemas


def describe(problemas) -> str:
    """Un mensaje de falla legible para el reporte de pytest."""
    return "; ".join(problemas)
