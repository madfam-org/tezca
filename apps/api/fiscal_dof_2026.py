"""Valores fiscales 2026 **verificados contra el texto del DOF**.

A diferencia de :mod:`apps.api.fiscal_seed_data` — cuyas filas se declaran
``seed-unverified`` porque nadie en este repo leyó el documento primario —
cada fila de este módulo se transcribió del texto del DOF el **2026-09-05**,
y por eso se publica con ``provenance='published'``.

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
2. **Append-only.** Publicar no edita una fila existente: la corrección es
   una fila nueva con ``vigencia_from`` posterior, o —cuando corrige el
   mismo periodo de vigencia— una fila nueva que supersede a la anterior
   cerrando su ``vigencia_to``. Ver ``publish_fiscal_values_2026``.
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
# Los valores son IDÉNTICOS a los de 2025 — LISR Art. 152 sólo obliga a
# actualizar cuando la inflación acumulada rebasa 10 % — pero el INSTRUMENTO
# es nuevo. Ésa es precisamente la razón de publicar una fila 2026 en lugar
# de dejar que un consumidor reutilice la de 2025: la cita que defiende el
# cálculo ante el SAT es el Anexo 8 de 2026, no el de 2025.
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
        VERIFIED_NOTE + " Los importes coinciden con los de 2025 (LISR Art. "
        "152: la tarifa se actualiza sólo cuando la inflación acumulada rebasa "
        "10 %), pero el instrumento y la cita son nuevos: quien defienda una "
        "retención de 2026 cita el Anexo 8 de la RMF 2026, no el de 2025."
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
# Subsidio al empleo 2026 — regla derivada, no tabla
#
# Instrumento: «Decreto que otorga el subsidio para el empleo», DOF
# 01/05/2024, modificado por el DOF 31/12/2024 (codigo 5746529). NO hubo
# decreto nuevo para 2026 (se recorrieron los índices del DOF entre el
# 15/12/2025 y el 28/02/2026).
#
# Desde ese decreto el subsidio dejó de ser una tabla de rangos: es un monto
# mensual fijo igual al 13.8 % de la UMA mensual, para quien percibe un
# ingreso base que no exceda $10,171.00. Para periodos menores a un mes:
#     (UMA mensual x 13.8 %) / 30.4 x días
#
# Como el monto se deriva de la UMA mensual y la UMA cambia el 1 de febrero,
# 2026 tiene DOS vigencias — y el modelo append-only las representa como dos
# filas, no como una fila editada:
#     enero 2026        UMA 2025 (3,439.46) x 13.8 % = 474.65
#     desde 01-02-2026  UMA 2026 (3,566.22) x 13.8 % = 492.14
#
# Los importes derivados se publican junto con la fórmula para que un
# consumidor pueda recalcularlos y comprobar la aritmética en lugar de
# confiar en un número opaco.
# ---------------------------------------------------------------------------
SUBSIDIO_RATE_OF_UMA = "0.138"
SUBSIDIO_INCOME_CAP = "10171.00"
SUBSIDIO_DAYS_DIVISOR = "30.4"

SUBSIDIO_2026_DOF = {
    "dof_date": "2024-12-31",
    "dof_codigo": "5746529",
    "source_url": "https://dof.gob.mx/nota_detalle.php?codigo=5746529&fecha=31/12/2024",
    "source_citation": (
        "«DECRETO por el que se otorga el subsidio para el empleo», DOF "
        "01-05-2024, modificado por DOF 31-12-2024 (codigo 5746529). Sin "
        "decreto nuevo para 2026."
    ),
    "notes": (
        VERIFIED_NOTE + " No hubo decreto nuevo para 2026: se recorrieron los "
        "índices del DOF entre el 15-12-2025 y el 28-02-2026 sin encontrarlo, "
        "así que sigue vigente el de 2024. La sustitución del 14.39 % aplicó "
        "sólo a enero de 2025 y NO se arrastra a 2026."
    ),
}

# (vigencia_from, vigencia_to, UMA mensual base, monto mensual derivado, nota)
SUBSIDIO_2026_PERIODS = [
    (
        "2026-01-01",
        "2026-01-31",
        "3439.46",
        "474.65",
        "Enero de 2026 se calcula todavía con la UMA 2025 (3,439.46), "
        "vigente hasta el 31-01-2026.",
    ),
    (
        "2026-02-01",
        None,
        "3566.22",
        "492.14",
        "Desde el 01-02-2026 el subsidio se calcula con la UMA 2026 "
        "(3,566.22), publicada en el DOF 09-01-2026 (codigo 5778072).",
    ),
]


def subsidio_rule_rows(uma_monthly: str, monthly_amount: str) -> list[dict]:
    """La regla del subsidio como la consume un motor de nómina.

    Se devuelve una lista de un solo objeto (y no una tabla de rangos) para
    que la forma del campo ``rows`` siga siendo una lista, igual que en los
    demás ``FiscalTable``, sin fingir que existen tramos que el decreto ya
    no tiene.
    """
    return [
        {
            "rate_of_uma": SUBSIDIO_RATE_OF_UMA,
            "uma_monthly": uma_monthly,
            "monthly_amount": monthly_amount,
            "income_cap": SUBSIDIO_INCOME_CAP,
            "days_divisor": SUBSIDIO_DAYS_DIVISOR,
            "formula": (
                "monto mensual = UMA mensual x 13.8 %, aplicable cuando el "
                "ingreso base no excede 10,171.00; para periodos menores a un "
                "mes: (UMA mensual x 13.8 %) / 30.4 x dias"
            ),
        }
    ]
