"""Valores fiscales 2026 **verificados contra el texto del DOF**.

A diferencia de :mod:`apps.api.fiscal_seed_data` — cuyas filas se declaran
``seed-unverified`` porque nadie en este repo leyó el documento primario —
las cifras se leyeron el **2026-09-05**, con corrección del subsidio el
**2026-10-07** contra el decreto 5777649. Cada dataset conserva su propia cita.

Cada constante lleva el ``codigo`` de ``nota_detalle`` del DOF, que es el
identificador estable de la publicación exacta:

    https://dof.gob.mx/nota_detalle.php?codigo=<codigo>&fecha=<dd/mm/aaaa>

Ese ``codigo`` es la misma disciplina de identidad que ``apps.scraper``
aplica a los documentos anclados del corpus: un código opaco puede resolver
al instrumento equivocado, así que se ancla junto con su fecha.

Reglas que gobiernan este módulo
--------------------------------

1. **Nada aquí es inferencia.** Si el texto del DOF no lo dice, no se
   escribe. Donde hubo que inferir (el fin de vigencia de la UMA), la fila
   deja el campo en ``None`` y lo declara en ``notes``.
2. **Publicación protegida.** El comando ordinario conserva las filas
   publicadas. La errata del subsidio 2026 requiere una opción explícita,
   motivo y archivo íntegro de la fila anterior dentro de la misma
   transacción; una fila desconocida se rechaza. Ver
   ``publish_fiscal_values_2026 --correct-subsidio-2026``.
3. **UMA ≠ salario mínimo** (LFVUMA Art. 4). Son modelos distintos a
   propósito; este módulo no los mezcla.

Fuente de la verificación: ``claudedocs/hcm-hardening/dof-2026-verificacion.md``
(labspace), levantado leyendo ``nota_detalle`` del DOF de forma directa, sin
fuentes secundarias.
"""

VERIFIED_ON = "2026-09-05"

VERIFIED_NOTE = (
    "Verificado el 2026-09-05 contra el texto del DOF (lectura directa de "
    "nota_detalle), sin fuentes secundarias. Provenance='published': la cita "
    "identifica el documento exacto."
)

# ---------------------------------------------------------------------------
# UMA 2026 — INEGI
#
# DOF 09/01/2026, ÚNICA SECCIÓN, INEGI, «UNIDAD de medida y actualización».
# Firmada el 8 de enero de 2026. Vigente a partir del 1 de febrero de 2026
# (LFVUMA Art. 5).
#
# El fin de vigencia (31/01/2027) NO está en el texto: es la consecuencia de
# que la UMA del año siguiente entre en vigor el 1 de febrero. Por eso la
# fila queda abierta (``vigencia_to=None``) y lo dice en notes — el modelo ya
# documenta NULL como "sigue vigente", que es exactamente lo que sabemos.
# ---------------------------------------------------------------------------
UMA_2026 = {
    "year": 2026,
    "daily": "117.31",
    "monthly": "3566.22",
    "annual": "42794.64",
    "vigencia_from": "2026-02-01",
    "vigencia_to": None,
    "dof_date": "2026-01-09",
    "dof_codigo": "5778072",
    "source_url": "https://dof.gob.mx/nota_detalle.php?codigo=5778072&fecha=09/01/2026",
    "source_citation": (
        "DOF 09-01-2026, ÚNICA SECCIÓN, INEGI, «UNIDAD de medida y "
        "actualización» (codigo 5778072); LFVUMA Art. 4 y 5"
    ),
    "notes": (
        VERIFIED_NOTE + " El fin de vigencia (31-01-2027) NO aparece en el "
        "texto: se deriva de que la UMA del ejercicio siguiente entra en vigor "
        "el 1 de febrero, así que la fila se deja abierta en lugar de afirmar "
        "una fecha que el DOF no publicó."
    ),
}

# ---------------------------------------------------------------------------
# Salarios mínimos 2026 — CONASAMI
#
# DOF 09/12/2025, «RESOLUCIÓN … salarios mínimos generales y profesionales …
# a partir del 1º de enero de 2026».
#
# ZSMG (zona de salarios mínimos generales, resto del país) = 315.04/día,
# +13.0 % (MIR de 17.01 más 6.5 %). ZLFN = 440.87/día, +5.0 %, sin MIR.
#
# La resolución trae además una tabla de 61 salarios mínimos PROFESIONALES.
# El documento de verificación registra su existencia pero NO sus 61 valores,
# así que aquí no se escribe ninguno: inventar un profesional sería
# exactamente el fallo que este módulo existe para evitar. Queda pendiente
# (ver docs/fiscal/2026-publicacion-dof.md).
# ---------------------------------------------------------------------------
MINIMUM_WAGE_2026 = {
    "year": 2026,
    "vigencia_from": "2026-01-01",
    "vigencia_to": None,
    "dof_date": "2025-12-09",
    "dof_codigo": "5775534",
    "source_url": "https://dof.gob.mx/nota_detalle.php?codigo=5775534&fecha=09/12/2025",
    "source_citation": (
        "DOF 09-12-2025, CONASAMI, «RESOLUCIÓN del H. Consejo de "
        "Representantes de la CONASAMI que fija los salarios mínimos "
        "generales y profesionales vigentes a partir del 1o. de enero de "
        "2026» (codigo 5775534); LFT Art. 90-97"
    ),
    "zones": [
        # (zone, daily value, incremento as published)
        ("general", "315.04", "+13.0 % (MIR 17.01 más 6.5 %)"),
        ("zlfn", "440.87", "+5.0 %, sin MIR"),
    ],
}

# ---------------------------------------------------------------------------
# ISR 2026 — tarifa mensual del Art. 96 LISR
#
# Anexo 8 de la RMF 2026, apartado B, fracción V («durante 2026»), publicado
# en el DOF 28/12/2025 (codigo 5777219). La RMF 2026 misma es el codigo
# 5777217, vigente del 01-01-2026 al 31-12-2026.
#
# CORRECCIÓN 2026-09-05: aquí se afirmaba que los valores eran IDÉNTICOS a los
# de 2025. No lo son. Al leer el Anexo 8 de la RMF 2025 (codigo 5746354, ver
# apps/api/fiscal_dof_2025.py) resultó que 844.59, 7,168.51, 133,488.54 y
# 425,641.99 tienen CERO ocurrencias en ese texto: el primer tramo mensual de
# 2025 termina en 746.04 y el último arranca en 375,975.62 con cuota
# 117,912.32. Las TASAS sí coinciden entre años; los LÍMITES se actualizaron
# ≈13.2 %, consistente con haber rebasado el umbral de inflación acumulada del
# 10 % del Art. 152 LISR.
#
# Los importes de abajo no cambian —se leyeron del instrumento de 2026— pero
# la conclusión práctica se refuerza: publicar una fila 2026 propia es lo que
# impide que un consumidor reutilice la de 2025, que además es distinta.
#
# Forma de cada renglón: la misma que ISR_MONTHLY_2025 (lower/upper/
# fixed_fee/rate), para que symbiosis-hcm no cambie de parser. ``rate`` va en
# fracción decimal (el DOF publica el porcentaje sobre el excedente).
# ---------------------------------------------------------------------------
ISR_MONTHLY_2026 = [
    {"lower": "0.01", "upper": "844.59", "fixed_fee": "0.00", "rate": "0.0192"},
    {"lower": "844.60", "upper": "7168.51", "fixed_fee": "16.22", "rate": "0.0640"},
    {"lower": "7168.52", "upper": "12598.02", "fixed_fee": "420.95", "rate": "0.1088"},
    {
        "lower": "12598.03",
        "upper": "14644.64",
        "fixed_fee": "1011.68",
        "rate": "0.1600",
    },
    {
        "lower": "14644.65",
        "upper": "17533.64",
        "fixed_fee": "1339.14",
        "rate": "0.1792",
    },
    {
        "lower": "17533.65",
        "upper": "35362.83",
        "fixed_fee": "1856.84",
        "rate": "0.2136",
    },
    {
        "lower": "35362.84",
        "upper": "55736.68",
        "fixed_fee": "5665.16",
        "rate": "0.2352",
    },
    {
        "lower": "55736.69",
        "upper": "106410.50",
        "fixed_fee": "10457.09",
        "rate": "0.3000",
    },
    {
        "lower": "106410.51",
        "upper": "141880.66",
        "fixed_fee": "25659.23",
        "rate": "0.3200",
    },
    {
        "lower": "141880.67",
        "upper": "425641.99",
        "fixed_fee": "37009.69",
        "rate": "0.3400",
    },
    {
        "lower": "425642.00",
        "upper": None,
        "fixed_fee": "133488.54",
        "rate": "0.3500",
    },
]

ISR_2026_DOF = {
    "dof_date": "2025-12-28",
    "dof_codigo": "5777219",
    "source_url": "https://dof.gob.mx/nota_detalle.php?codigo=5777219&fecha=28/12/2025",
    "source_citation": (
        "DOF 28-12-2025, SHCP/SAT, «ANEXOS 4, 5, 6, 8, 15 y 25 de la "
        "Resolución Miscelánea Fiscal para 2026» (codigo 5777219), Anexo 8 "
        "apartado B fracción V; RMF 2026 codigo 5777217, vigente "
        "01-01-2026 a 31-12-2026; LISR Art. 96"
    ),
    "notes": (
        VERIFIED_NOTE + " CORRECCIÓN 2026-09-05: esta nota afirmaba que los "
        "importes coincidían con los de 2025. Es FALSO — la lectura del Anexo "
        "8 de la RMF 2025 (codigo 5746354) encontró cero ocurrencias de "
        "844.59, 7,168.51, 133,488.54 y 425,641.99 en ese texto: el primer "
        "tramo mensual de 2025 termina en 746.04. Las tasas sí coinciden entre "
        "años; los límites se actualizaron ≈13.2 %. Los importes de abajo no "
        "cambian (se leyeron del instrumento de 2026), pero ninguna tabla debe "
        "reutilizarse para el otro año."
    ),
}

# La tarifa ANUAL del Art. 152 también viene en el Anexo 8, pero el documento
# de verificación sólo registró sus extremos (0.01–10,135.11 @ 1.92 % …
# 5,107,703.93+ @ 35 %), no los once renglones completos. Completar a mano los
# renglones intermedios sería inventar cifras, así que NO se publica una fila
# ``isr_annual`` 2026: /fiscal/tables/?kind=isr_annual&year=2026 no devuelve
# nada y el consumidor falla en claro. Queda pendiente de una segunda lectura
# del Anexo 8.
ISR_ANNUAL_2026_PENDING = {
    "reason": (
        "El documento de verificación registra sólo los extremos de la tarifa "
        "anual (Art. 152): 0.01–10,135.11 @ 1.92 % y 5,107,703.93 en adelante "
        "@ 35 %. Faltan los renglones intermedios, y completarlos de memoria "
        "sería inventar cifras. Pendiente de una segunda lectura del Anexo 8 "
        "(DOF 28-12-2025, codigo 5777219)."
    ),
    "known_first_bracket": {"lower": "0.01", "upper": "10135.11", "rate": "0.0192"},
    "known_last_bracket": {"lower": "5107703.93", "upper": None, "rate": "0.3500"},
}

# ---------------------------------------------------------------------------
# Subsidio al empleo 2026 — DOF 31-12-2025, codigo 5777649.
# Artículo Segundo: 15.02 % de UMA mensual, ingreso base <= 11,492.66.
# Transitorio Segundo: únicamente enero usa 15.59 % sobre la UMA 2025.
# Corrección verificada 2026-10-07: la publicación de septiembre aplicaba
# indebidamente el decreto de 2024 a 2026. No cambia el ejercicio 2025.
# ---------------------------------------------------------------------------
SUBSIDIO_RATE_OF_UMA = "0.1502"
SUBSIDIO_ENERO_RATE_OF_UMA = "0.1559"
SUBSIDIO_INCOME_CAP = "11492.66"
SUBSIDIO_DAYS_DIVISOR = "30.4"

SUBSIDIO_2026_DOF = {
    "dof_date": "2025-12-31",
    "dof_codigo": "5777649",
    "source_url": "https://dof.gob.mx/nota_detalle.php?codigo=5777649&fecha=31/12/2025",
    "source_citation": (
        "DOF 31-12-2025, Decreto por el que se modifica el diverso que otorga "
        "el subsidio para el empleo; Artículo Segundo y Transitorios Primero y Segundo."
    ),
    "notes": (
        "Texto oficial verificado 2026-10-07. Sustituye la atribución errónea "
        "del decreto 5746529 a 2026. Enero: 15.59 % de UMA 2025; desde febrero: "
        "15.02 % de UMA 2026. Importes derivados con redondeo a centavos; el "
        "considerando estima 536.22, pero la regla operativa es el porcentaje "
        "de UMA publicada. Cotejo con el facsímil pendiente."
    ),
}

# (vigencia_from, vigencia_to, UMA mensual, monto mensual, nota)
SUBSIDIO_2026_PERIODS = [
    (
        "2026-01-01",
        "2026-01-31",
        "3439.46",
        "536.21",
        "Enero: 15.59 % de la UMA mensual 2025 (Transitorio Segundo).",
    ),
    (
        "2026-02-01",
        None,
        "3566.22",
        "535.65",
        "Desde febrero: 15.02 % de la UMA mensual 2026 (Artículo Segundo).",
    ),
]


def subsidio_rule_rows(
    uma_monthly: str,
    monthly_amount: str,
    rate_of_uma: str = SUBSIDIO_RATE_OF_UMA,
    *,
    income_cap: str = SUBSIDIO_INCOME_CAP,
) -> list[dict]:
    """Regla auto-verificable; cada ejercicio declara porcentaje y tope.

    Los consumidores históricos de 2025 deben pasar su tope explícitamente.
    """
    from decimal import Decimal

    percent = f"{Decimal(rate_of_uma) * 100:f}".rstrip("0").rstrip(".") + " %"
    cap_display = f"{Decimal(income_cap):,.2f}"
    return [
        {
            "rate_of_uma": rate_of_uma,
            "uma_monthly": uma_monthly,
            "monthly_amount": monthly_amount,
            "income_cap": income_cap,
            "days_divisor": SUBSIDIO_DAYS_DIVISOR,
            "formula": (
                f"monto mensual = UMA mensual x {percent}, aplicable cuando el "
                f"ingreso base no excede {cap_display}; para periodos menores a un "
                f"mes: (UMA mensual x {percent}) / 30.4 x dias"
            ),
        }
    ]
