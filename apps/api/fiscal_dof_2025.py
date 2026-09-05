"""Valores fiscales 2025 **verificados contra el texto del DOF** — errata.

Este módulo es el gemelo de :mod:`apps.api.fiscal_dof_2026` para el ejercicio
2025, y existe por una razón distinta: no completa un hueco, **corrige un
error**.

Lo que estaba mal
-----------------

``apps.api.fiscal_seed_data`` transcribió la tarifa mensual del Art. 96 desde
``symbiosis-hcm/packages/mx-payroll/mx_payroll/isr.py`` y declaró honestamente
que nadie la había cotejado con el DOF (``seed-unverified``). Al cotejarla el
**2026-09-05** resultó que **6 de sus 11 cuotas fijas son incorrectas**, con un
patrón de dígito de millar perdido (−1,000.00 exactos en tres tramos). El
efecto es que la tarifa sembrada **subestima el ISR retenido** en los tramos 6
a 11, hasta ≈$1,022 mensuales por trabajador.

Además:

* ``SUBSIDIO_MONTHLY_2025`` es la **tabla derogada** de montos por tramos —
  literalmente la que el considerando del decreto vigente cita como el defecto
  que vino a corregir. Desde el decreto DOF 01-05-2024 el subsidio es una
  cuota fija derivada de la UMA, no una tabla.
* La **tarifa anual del Art. 152** nunca se sembró, aunque el modelo define
  el ``kind`` ``isr_annual`` desde el principio.

El diseño fail-closed funcionó: el seed nunca afirmó estar verificado, así que
esto es un hallazgo, no un incidente. Lo que falló es la fuente aguas arriba.

Cómo se leyó el DOF (receta para fechas viejas)
-----------------------------------------------

``nota_detalle.php`` devuelve un **cascarón vacío** (3,325 bytes idénticos)
para publicaciones de diciembre de 2024: sólo sirve meses recientes. Los dos
endpoints que sí responden para fechas antiguas son::

    https://dof.gob.mx/index_111.php?year=2024&month=12&day=30   # índice del día
    https://dof.gob.mx/nota_to_doc.php?codnota=5746354           # texto íntegro

Con el índice del día se identifica la nota por su título y se extrae el
``codigo``; con ``nota_to_doc`` se obtiene el documento completo, cuyas tablas
vienen delimitadas por tabuladores. Por eso las URL de este módulo apuntan a
``nota_to_doc.php`` y no a ``nota_detalle.php``: es el enlace que de verdad
resuelve al texto citado.

**Trampa del apartado C.** La tarifa anual viene dos veces: la fracción I es la
del ejercicio **2024** y la fracción II la de **2025**, en ese orden. En la RMF
2025 ambas son numéricamente idénticas, así que quien extraiga «la primera
tabla anual que aparece» acierta por accidente este año y fallará el año en que
difieran. Las cifras de abajo son de la **fracción II**.

Reglas que gobiernan este módulo
--------------------------------

1. **Nada aquí es inferencia.** Cada cifra se leyó en el texto citado.
2. **Append-only**, igual que 2026: la corrección de una fila ``published`` es
   una fila nueva; una fila ``seed-unverified`` del mismo periodo se promueve
   en su lugar (ver ``publish_fiscal_values_2025``).
3. **No se reutiliza una tarifa de un año para otro.** La verificación dejó
   probado que las tarifas 2025 y 2026 **difieren** (los importes 2026 tienen
   cero ocurrencias en el texto de la RMF 2025), de modo que la equivalencia
   «2025 ≡ 2026» que se llegó a suponer es falsa.

Fuente de la verificación: ``claudedocs/hcm-hardening/dof-2025-isr-verificacion.md``
(labspace), levantado leyendo el texto del DOF de forma directa, sin fuentes
secundarias.
"""

VERIFIED_ON = "2026-09-05"

VERIFIED_NOTE = (
    "Verificado el 2026-09-05 contra el texto del DOF (index_111 para "
    "localizar la nota del día, nota_to_doc para el texto íntegro), sin "
    "fuentes secundarias. Provenance='published': la cita identifica el "
    "documento exacto."
)

# ---------------------------------------------------------------------------
# ISR 2025 — Anexo 8 de la RMF 2025, DOF 30/12/2024, codigo 5746354.
#
# Instrumento: «Resolución Miscelánea Fiscal para 2025, y sus Anexos 1, 5, 6,
# 8, 15, 19 y 27» (SHCP/SAT).
# ---------------------------------------------------------------------------
ISR_2025_DOF = {
    "dof_date": "2024-12-30",
    "dof_codigo": "5746354",
    "source_url": "https://dof.gob.mx/nota_to_doc.php?codnota=5746354",
    "source_citation": (
        "DOF 30-12-2024, SHCP/SAT, «Resolución Miscelánea Fiscal para 2025, y "
        "sus Anexos 1, 5, 6, 8, 15, 19 y 27» (codigo 5746354), Anexo 8 "
        "apartado A fracción V; LISR Art. 96"
    ),
}

# Tarifa mensual del Art. 96 — Anexo 8, apartado A, fracción V: «Tarifa
# aplicable durante 2025 para el cálculo de los pagos provisionales mensuales
# a que se refieren los artículos 96 de la Ley del ISR y 175 de su Reglamento,
# así como la regla 3.12.2.»
#
# Los ONCE límites y los ONCE porcentajes coinciden con los que el seed ya
# traía. Las seis correcciones están todas en la cuota fija, marcadas abajo
# con el valor que el seed afirmaba.
ISR_MONTHLY_2025 = [
    {"lower": "0.01", "upper": "746.04", "fixed_fee": "0.00", "rate": "0.0192"},
    {"lower": "746.05", "upper": "6332.05", "fixed_fee": "14.32", "rate": "0.0640"},
    {"lower": "6332.06", "upper": "11128.01", "fixed_fee": "371.83", "rate": "0.1088"},
    {
        "lower": "11128.02",
        "upper": "12935.82",
        "fixed_fee": "893.63",
        "rate": "0.1600",
    },
    {
        "lower": "12935.83",
        "upper": "15487.71",
        "fixed_fee": "1182.88",
        "rate": "0.1792",
    },
    {
        # seed: 1639.32 (−0.86)
        "lower": "15487.72",
        "upper": "31236.49",
        "fixed_fee": "1640.18",
        "rate": "0.2136",
    },
    {
        # seed: 4005.47 (−998.65)
        "lower": "31236.50",
        "upper": "49233.00",
        "fixed_fee": "5004.12",
        "rate": "0.2352",
    },
    {
        # seed: 8236.89 (−1000.00 exactos)
        "lower": "49233.01",
        "upper": "93993.90",
        "fixed_fee": "9236.89",
        "rate": "0.3000",
    },
    {
        # seed: 21665.17 (−1000.00 exactos)
        "lower": "93993.91",
        "upper": "125325.20",
        "fixed_fee": "22665.17",
        "rate": "0.3200",
    },
    {
        # seed: 31691.18 (−1000.00 exactos)
        "lower": "125325.21",
        "upper": "375975.61",
        "fixed_fee": "32691.18",
        "rate": "0.3400",
    },
    {
        # seed: 116890.10 (−1022.22)
        "lower": "375975.62",
        "upper": None,
        "fixed_fee": "117912.32",
        "rate": "0.3500",
    },
]

ISR_MONTHLY_2025_NOTES = (
    VERIFIED_NOTE + " Corrige seis cuotas fijas que el seed transcribió mal "
    "desde symbiosis-hcm (tramos 6 a 11: 1639.32→1640.18, 4005.47→5004.12, "
    "8236.89→9236.89, 21665.17→22665.17, 31691.18→32691.18, "
    "116890.10→117912.32). Los once límites y las once tasas ya eran "
    "correctos. La tarifa errónea subestimaba el ISR retenido."
)

# Tarifa anual del Art. 152 — Anexo 8, apartado C, **fracción II** («Tarifa
# para el cálculo del impuesto correspondiente al ejercicio de 2025 a que se
# refieren los artículos 97 y 152 de la Ley del ISR, así como la regla
# 3.17.1»). La fracción I, que aparece ANTES, es la del ejercicio 2024.
ISR_ANNUAL_2025 = [
    {"lower": "0.01", "upper": "8952.49", "fixed_fee": "0.00", "rate": "0.0192"},
    {"lower": "8952.50", "upper": "75984.55", "fixed_fee": "171.88", "rate": "0.0640"},
    {
        "lower": "75984.56",
        "upper": "133536.07",
        "fixed_fee": "4461.94",
        "rate": "0.1088",
    },
    {
        "lower": "133536.08",
        "upper": "155229.80",
        "fixed_fee": "10723.55",
        "rate": "0.1600",
    },
    {
        "lower": "155229.81",
        "upper": "185852.57",
        "fixed_fee": "14194.54",
        "rate": "0.1792",
    },
    {
        "lower": "185852.58",
        "upper": "374837.88",
        "fixed_fee": "19682.13",
        "rate": "0.2136",
    },
    {
        "lower": "374837.89",
        "upper": "590795.99",
        "fixed_fee": "60049.40",
        "rate": "0.2352",
    },
    {
        "lower": "590796.00",
        "upper": "1127926.84",
        "fixed_fee": "110842.74",
        "rate": "0.3000",
    },
    {
        "lower": "1127926.85",
        "upper": "1503902.46",
        "fixed_fee": "271981.99",
        "rate": "0.3200",
    },
    {
        "lower": "1503902.47",
        "upper": "4511707.37",
        "fixed_fee": "392294.17",
        "rate": "0.3400",
    },
    {
        "lower": "4511707.38",
        "upper": None,
        "fixed_fee": "1414947.85",
        "rate": "0.3500",
    },
]

ISR_ANNUAL_2025_DOF = {
    "dof_date": "2024-12-30",
    "dof_codigo": "5746354",
    "source_url": "https://dof.gob.mx/nota_to_doc.php?codnota=5746354",
    "source_citation": (
        "DOF 30-12-2024, SHCP/SAT, «Resolución Miscelánea Fiscal para 2025, y "
        "sus Anexos 1, 5, 6, 8, 15, 19 y 27» (codigo 5746354), Anexo 8 "
        "apartado C fracción II; LISR Art. 152"
    ),
    "notes": (
        VERIFIED_NOTE + " Tomada de la fracción II del apartado C. La fracción "
        "I, que aparece antes en el mismo apartado, es la del ejercicio 2024: "
        "en la RMF 2025 ambas son numéricamente idénticas, así que leer «la "
        "primera tabla anual» acierta por accidente y fallará el año en que "
        "difieran."
    ),
}

# ---------------------------------------------------------------------------
# Subsidio al empleo 2025 — regla derivada, no tabla
#
# Instrumento: «Decreto que otorga el subsidio para el empleo», DOF
# 01/05/2024, modificado por el DOF 31/12/2024 (codigo 5746529, firmado por
# la Presidenta Claudia Sheinbaum Pardo).
#
# Texto verificado:
#   · Artículo Segundo: subsidio mensual = UMA mensual x 13.8 %, para
#     trabajadores cuyo ingreso base no exceda de $10,171.00.
#   · Periodos menores a un mes: (UMA mensual x 13.8 %) / 30.4 x días.
#   · TRANSITORIO PRIMERO: en vigor el 1 de enero de 2025.
#   · TRANSITORIO SEGUNDO: para enero de 2025 el porcentaje es 14.39 %
#     «en sustitución del porcentaje de 13.8 %», y el considerando precisa
#     que se aplica sobre «la Unidad de Medida y Actualización vigente en
#     2024» — porque la UMA 2025 no entra en vigor hasta el 1 de febrero.
#
# Ese transitorio es la razón de que 2025 tenga DOS vigencias, igual que 2026
# pero por un motivo distinto: en 2026 cambia la UMA, en 2025 cambian LA UMA
# Y EL PORCENTAJE a la vez. El diseño deja el subsidio casi plano
# (474.95 → 474.65), lo que corrobora la lectura del empalme.
#
# Se reutiliza el mismo ``kind`` ``subsidio_rule`` y la misma forma de fila
# que introdujo el carril 2026: un consumidor no distingue de qué año viene.
# ---------------------------------------------------------------------------
SUBSIDIO_2025_DOF = {
    "dof_date": "2024-12-31",
    "dof_codigo": "5746529",
    "source_url": "https://dof.gob.mx/nota_to_doc.php?codnota=5746529",
    "source_citation": (
        "«DECRETO por el que se modifica el diverso que otorga el subsidio "
        "para el empleo», DOF 31-12-2024 (codigo 5746529), que reforma el "
        "«Decreto que otorga el subsidio para el empleo», DOF 01-05-2024; "
        "Artículo Segundo y TRANSITORIOS PRIMERO y SEGUNDO"
    ),
    "notes": (
        VERIFIED_NOTE + " Sustituye la tabla de montos por tramos, derogada: "
        "el considerando del propio decreto cita esa tabla (límite superior "
        "7,382.33) como el defecto que vino a corregir."
    ),
}

# El porcentaje de enero de 2025 es el del TRANSITORIO SEGUNDO; no se arrastra
# a ningún otro mes ni a ningún otro ejercicio.
SUBSIDIO_2025_ENERO_RATE_OF_UMA = "0.1439"

# (vigencia_from, vigencia_to, UMA mensual base, % de UMA, monto mensual, nota)
SUBSIDIO_2025_PERIODS = [
    (
        "2025-01-01",
        "2025-01-31",
        "3300.53",
        SUBSIDIO_2025_ENERO_RATE_OF_UMA,
        "474.95",
        "Enero de 2025: el TRANSITORIO SEGUNDO del decreto sustituye el 13.8 % "
        "por 14.39 % «de la Unidad de Medida y Actualización vigente en 2024» "
        "(3,300.53), porque la UMA 2025 no entra en vigor hasta el 1 de "
        "febrero (LFVUMA Art. 5). Aplica sólo a ese mes.",
    ),
    (
        "2025-02-01",
        "2025-12-31",
        "3439.46",
        "0.138",
        "474.65",
        "Desde el 01-02-2025 rige el 13.8 % del Artículo Segundo sobre la UMA "
        "2025 (3,439.46).",
    ),
]

# La tabla derogada que el seed traía. Se conserva **sólo como registro de lo
# que se retiró**, para que la prueba que verifica el retiro pueda nombrarla
# sin resucitarla; NO se siembra ni se publica en ninguna fila.
SUBSIDIO_2025_TABLA_DEROGADA_TOPE = "7382.33"

SUBSIDIO_2025_RETIRO_RAZON = (
    "La tabla de montos por tramos del subsidio al empleo (11 renglones de "
    "407.02 a 0.00, con límite superior 7,382.33) quedó DEROGADA por el "
    "«Decreto que otorga el subsidio para el empleo» (DOF 01-05-2024), "
    "modificado el 31-12-2024 (codigo 5746529), que la sustituyó por una "
    "cuota fija derivada de la UMA. No se conserva «por compatibilidad»: un "
    "consumidor que aplique tramos derogados a 2025 calcula mal, y recibir "
    "null en `subsidio` es exactamente el fallo en claro que el feed busca."
)
