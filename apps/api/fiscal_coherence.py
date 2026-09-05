"""Compuerta de coherencia aritmética de las tarifas ISR.

En una tarifa progresiva la cuota fija de cada tramo **no es libre**: es el
impuesto acumulado hasta el tope del tramo anterior. De ahí sale una identidad
que toda tarifa legalmente válida cumple, cualquiera que sea el año, el
ejercicio o la periodicidad::

    cuota_fija[n] == cuota_fija[n-1] + tasa[n-1] x (inferior[n] - inferior[n-1])

Escrita sobre los **límites inferiores** (y no sobre el tope del tramo
anterior) porque así no depende de que ``upper[n-1]`` y ``lower[n]`` disten
exactamente un centavo: la identidad es la del impuesto acumulado y ésta es su
forma robusta.

Por qué esto es una compuerta y no una prueba de regresión
----------------------------------------------------------

Es **falsable sin consultar el DOF**. Una tarifa transcrita con un dígito de
más o de menos deja de cumplir la identidad por órdenes de magnitud; ningún
test de monotonía, contigüidad o «once tramos» lo detecta. Aplicada a la
tarifa 2025 que este repo sembró hasta el 2026-09-05, se pone en rojo en
**cuatro** de los seis tramos equivocados (6, 7, 8 y 11) sin más insumo que la
tabla misma. Los tramos 9 y 10 la pasaban sólo porque arrastraban el mismo
desfase de −1,000.00 que su predecesor: la identidad es relativa, así que un
error constante se propaga sin romperla. Por eso la compuerta **no sustituye**
la lectura del DOF — la abarata.

Tolerancia
----------

El DOF publica los importes redondeados a centavos y la cadena acumula ese
redondeo, así que se admiten 2 centavos por tramo. La desviación real máxima
observada en las tarifas verificadas (2025 mensual y anual, 2026 mensual) es
de 0.012. Un dedazo se desvía en pesos, no en centavos.
"""

from decimal import Decimal

# Dos centavos: redondeo del DOF acumulado, nunca un error de transcripción.
TOLERANCIA = Decimal("0.02")


def incoherencias(rows) -> list[dict]:
    """Devuelve los tramos que rompen la identidad de la cuota fija.

    ``rows`` es una tarifa en la forma que usa el feed: una lista de dicts con
    ``lower``, ``upper``, ``fixed_fee`` y ``rate`` (el último ``upper`` puede
    ser ``None``, que es el tramo abierto). Una tarifa coherente devuelve una
    lista vacía.

    Cada incoherencia trae el número de tramo (1-based, como los enumera el
    Anexo 8), lo que la tabla dice y lo que la identidad exige, para que el
    mensaje de falla sea accionable sin abrir el DOF.
    """
    problemas = []
    for indice, (previo, actual) in enumerate(zip(rows, rows[1:]), start=2):
        esperada = Decimal(previo["fixed_fee"]) + Decimal(previo["rate"]) * (
            Decimal(actual["lower"]) - Decimal(previo["lower"])
        )
        declarada = Decimal(actual["fixed_fee"])
        desviacion = abs(esperada - declarada)
        if desviacion > TOLERANCIA:
            problemas.append(
                {
                    "tramo": indice,
                    "lower": actual["lower"],
                    "declarada": str(declarada),
                    "esperada": f"{esperada:.2f}",
                    "desviacion": f"{desviacion:.2f}",
                }
            )
    return problemas


def describe(problemas) -> str:
    """Un mensaje de falla legible para el reporte de pytest."""
    return "; ".join(
        f"tramo {p['tramo']} (desde {p['lower']}): cuota fija {p['declarada']}, "
        f"la identidad exige ~{p['esperada']} (desvía {p['desviacion']})"
        for p in problemas
    )
