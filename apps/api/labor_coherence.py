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


def _limites(modelo) -> dict[str, int]:
    """``{campo: max_length}`` de cada ``CharField`` acotado del modelo.

    Se lee del modelo, no de una lista escrita a mano: un campo nuevo, o un
    ``max_length`` que alguien baje, entra a la compuerta sin tocarla.
    """
    from django.db import models

    return {
        campo.name: campo.max_length
        for campo in modelo._meta.get_fields()
        if isinstance(campo, models.CharField) and campo.max_length
    }


def desbordes_de_longitud(filas, modelo, alias=None) -> list[dict]:
    """Devuelve los valores del seed que no caben en su columna.

    La razón de existir de esta compuerta: la suite corre sobre SQLite, que
    **ignora** el ancho declarado de un ``VARCHAR`` y guarda la cadena entera.
    Postgres no: rechaza la fila con ``value too long for type character
    varying(N)``. Una fila que la prueba daba por buena reventaba en el pod.
    Medir la longitud contra el ``max_length`` del modelo no depende del
    backend y por eso atrapa el error donde sí se corre la suite.

    ``alias`` mapea ``campo del modelo -> clave del seed`` para los seeds que
    no usan el mismo nombre (los catálogos del SAT guardan ``catalog`` en la
    columna ``article``).
    """
    limites = _limites(modelo)
    alias = alias or {}
    problemas = []
    for indice, fila in enumerate(filas):
        for campo, maximo in sorted(limites.items()):
            clave = alias.get(campo, campo)
            valor = fila.get(clave)
            if isinstance(valor, str) and len(valor) > maximo:
                problemas.append(
                    {
                        "fila": indice,
                        "identidad": _identidad(fila),
                        "campo": campo,
                        "clave_seed": clave,
                        "longitud": len(valor),
                        "max_length": maximo,
                        "valor": valor,
                    }
                )
    return problemas


def _identidad(fila) -> str:
    """Cómo nombrar la fila culpable en el mensaje de falla."""
    for clave in ("kind", "catalog", "official_id"):
        if fila.get(clave):
            return f"{clave}={fila[clave]}"
    return "fila sin kind ni catalog"


def describe_desbordes(problemas) -> str:
    """El mensaje del operador: fila, campo, cuántos caracteres y el tope."""
    return "; ".join(
        f"fila {p['fila']} ({p['identidad']}), campo {p['campo']}: "
        f"{p['longitud']} caracteres > max_length {p['max_length']}"
        for p in problemas
    )
