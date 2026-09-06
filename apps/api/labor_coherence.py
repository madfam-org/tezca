"""Compuertas de coherencia del feed laboral.

Del mismo linaje que ``fiscal_coherence``: reglas **falsables sin volver al
DOF**, que atrapan el error de transcripción que ninguna prueba de "existe la
fila" detecta.

Dos invariantes, cada una con su motivo:

``vigencias_traslapadas``
    Dos filas del mismo ``kind`` y las mismas dimensiones vigentes el mismo
    día hacen la consulta ambigua: el endpoint devolvería la que ordenara
    primero, y esa elección no la respalda ninguna ley. Es exactamente el
    riesgo que corre un feed escalonado como el de la jornada, donde hay
    cinco vigencias contiguas del mismo ``kind``.

``huecos_en_la_serie``
    Cuando un ``kind`` se publica como serie cerrada (cada fila con
    ``effective_to``), un hueco entre el fin de una y el inicio de la
    siguiente deja días sin respuesta. Un consumidor que preguntara por el
    1 de enero de 2028 recibiría 'no hay regla' y HCM diría 'ventana por
    publicar' cuando la ley sí dice algo. Es un error de transcripción, no
    una laguna legal.
"""

from datetime import timedelta


def _dimensiones(fila):
    """La clave natural de una regla: kind más las dimensiones que la parten."""
    return (
        fila["kind"],
        fila.get("payer_legal_form", "any"),
        fila.get("provider_regime", ""),
        fila.get("service", ""),
    )


def _fecha(valor):
    """Acepta date o 'YYYY-MM-DD'."""
    if valor is None:
        return None
    if isinstance(valor, str):
        from datetime import date

        return date.fromisoformat(valor)
    return valor


def vigencias_traslapadas(filas) -> list[dict]:
    """Devuelve los pares de filas que rigen a la vez lo mismo.

    Una lista vacía significa que, para cada combinación de kind y
    dimensiones, cualquier fecha tiene a lo sumo una respuesta.
    """
    por_clave: dict[tuple, list] = {}
    for fila in filas:
        por_clave.setdefault(_dimensiones(fila), []).append(fila)

    problemas = []
    for clave, grupo in por_clave.items():
        ordenado = sorted(grupo, key=lambda f: _fecha(f["effective_from"]))
        for previa, siguiente in zip(ordenado, ordenado[1:]):
            fin = _fecha(previa.get("effective_to"))
            inicio = _fecha(siguiente["effective_from"])
            # Sin fin, la previa sigue vigente y cualquier sucesora la traslapa.
            if fin is None or fin >= inicio:
                problemas.append(
                    {
                        "kind": clave[0],
                        "dimensiones": clave[1:],
                        "previa_desde": str(previa["effective_from"]),
                        "previa_hasta": str(previa.get("effective_to")),
                        "siguiente_desde": str(siguiente["effective_from"]),
                    }
                )
    return problemas


def huecos_en_la_serie(filas) -> list[dict]:
    """Devuelve los días sin cobertura dentro de una serie cerrada."""
    por_clave: dict[tuple, list] = {}
    for fila in filas:
        por_clave.setdefault(_dimensiones(fila), []).append(fila)

    problemas = []
    for clave, grupo in por_clave.items():
        if len(grupo) < 2:
            continue
        ordenado = sorted(grupo, key=lambda f: _fecha(f["effective_from"]))
        for previa, siguiente in zip(ordenado, ordenado[1:]):
            fin = _fecha(previa.get("effective_to"))
            inicio = _fecha(siguiente["effective_from"])
            if fin is not None and fin + timedelta(days=1) < inicio:
                problemas.append(
                    {
                        "kind": clave[0],
                        "dimensiones": clave[1:],
                        "hueco_desde": str(fin + timedelta(days=1)),
                        "hueco_hasta": str(inicio - timedelta(days=1)),
                    }
                )
    return problemas


def describe(problemas) -> str:
    """Un mensaje de falla legible para el reporte de pytest."""
    return "; ".join(
        " ".join(f"{campo}={valor}" for campo, valor in problema.items())
        for problema in problemas
    )
