"""Cuotas obrero-patronales IMSS 2026 e impuesto sobre nóminas por entidad.

Leídos de fuente primaria el **2026-11-03** (ratificación de Tezca,
internal-devops ``audits/2026-11-03-ratificacion-tezca/``, hallazgos F1 y F2).
Mismas reglas que :mod:`apps.api.fiscal_dof_2026`:

1. **Nada aquí es inferencia.** Cada cifra se transcribe del texto que la fija.
   Donde la cifra vigente sale de una aritmética que el propio texto ordena
   (los incrementos anuales del transitorio de 1995), la aritmética se escribe
   completa en ``notas`` y la prueba la vuelve a hacer.
2. **Procedencia por renglón.** Cada renglón lleva su artículo, su fuente y su
   ``provenance``. La tabla sólo se sella ``published`` si todos sus
   renglones lo son (``cuotas_coherence``).
3. **Publicación protegida.** ``publish_fiscal_values_2026`` nunca toca una
   fila que ya esté ``published``.

FUENTES LEÍDAS
==============

* **Cámara de Diputados, LeyesBiblio — Ley del Seguro Social, texto vigente,
  última reforma DOF 15-01-2026** (PDF de 181 páginas): arts. 25, 28, 106, 107,
  147, 168, 211, 212 y el transitorio DÉCIMO NOVENO de la Ley publicada en el
  DOF el 21-12-1995. Es la lectura primaria que el feed laboral ya admite
  (``labor_models``: «el texto vigente que publica la Cámara de Diputados»).
* **DOF 16-12-2020, codigo 5607729** — decreto de reforma a la LSS y a la LSAR,
  transitorio SEGUNDO. La tabla de la cuota patronal de cesantía y vejez
  2023-2030 es una IMAGEN en ``nota_detalle`` (``shcp11_Cimg_858340.png``); se
  leyó la imagen, columna 2026.
* **DOF 27-01-2016, codigo 5423663** — decreto de desindexación del salario
  mínimo, transitorio TERCERO. Ya publicado por Tezca para el tope del SBC
  (``labor_seed_t1g``); aquí convierte en UMA la misma unidad de cuenta de los
  arts. 106 fr. I y II.
* **Ley del INFONAVIT, art. 29 fr. II** — el ``LawArticle`` ``lifnvt/29`` de
  Tezca (Cámara, última reforma DOF 21-02-2025).
* **Morelos**: Periódico Oficial «Tierra y Libertad» 6382 Extraordinaria del
  31-12-2024 (Decreto Número Veinticuatro) y 6506 Extraordinaria del
  22-12-2025 (Decreto Novecientos Noventa y Siete), ambos de
  ``periodico.morelos.gob.mx``.
* **Ciudad de México**: Código Fiscal de la Ciudad de México, texto vigente que
  publica la Consejería Jurídica y de Servicios Legales (última reforma G.O.
  CDMX 19-12-2025), art. 158 y los transitorios del decreto publicado en la
  Gaceta Oficial el 27-12-2024. El certificado TLS del portal verificó el
  2026-11-03 (la ratificación del mismo día no pudo leerlo; esta lectura sí).

LO QUE NO ESTÁ, A PROPÓSITO
===========================

* **Riesgo de trabajo.** No es una constante de la ley: es la prima de CADA
  patrón (LSS 71-74). La prima media por clase del art. 73 sólo rige al
  inscribirse o al cambiar de actividad; después manda la prima que el patrón
  determina con su siniestralidad. Publicarla como tasa del ejercicio sería
  afirmar la prima de un patrón que Tezca no conoce.
* **Las otras 30 entidades.** El modelo ``ImpuestoNominaEstatal`` las admite;
  nadie leyó su ley todavía, así que no se escriben.
"""

VERIFIED_ON = "2026-11-03"

CAMARA_LSS = (
    "Cámara de Diputados, LeyesBiblio: Ley del Seguro Social, texto vigente, "
    "última reforma DOF 15-01-2026"
)
CAMARA_LSS_URL = "https://www.diputados.gob.mx/LeyesBiblio/pdf/LSS.pdf"

CEV_DOF = {
    "dof_date": "2020-12-16",
    "dof_codigo": "5607729",
    "source_url": "https://dof.gob.mx/nota_detalle.php?codigo=5607729&fecha=16/12/2020",
}

DESINDEXACION = (
    "Decreto de desindexación del salario mínimo, DOF 27-01-2016 (codigo "
    "5423663), transitorio TERCERO: las menciones al salario mínimo como unidad "
    "de cuenta, índice, base o referencia se entienden referidas a la UMA"
)

# ---------------------------------------------------------------------------
# Cuota patronal de cesantía en edad avanzada y vejez, 2026.
#
# LSS 168 fr. II a) trae en su texto la tabla de 2030 (3.150 % … 11.875 %);
# el transitorio SEGUNDO del decreto DOF 16-12-2020 la aplica «de manera
# gradual, a partir del 1 de enero de 2023, de conformidad con la siguiente
# tabla», con una columna por año. Ésta es la columna 2026, leída de la imagen.
#
# Forma de cada banda: ``hasta`` es el límite SUPERIOR tal como lo imprime el
# DOF (dos decimales) en su unidad; ``desde`` el inferior, igual. ``None`` en
# ``hasta`` = «en adelante». La primera banda se mide en SALARIOS MÍNIMOS y no
# en UMA: el texto dice «1.0 SM» y la desindexación no la alcanza (ahí el
# salario mínimo es salario, no unidad de cuenta — el mismo criterio que deja
# el piso del SBC en salarios mínimos en ``labor_seed_t1g``).
#
# LO QUE EL TEXTO NO DICE: cómo tratar un salario base de cotización que cae
# ENTRE dos límites impresos (p. ej. 1.505 UMA, o 1.005 SM). Tezca no lo
# resuelve; el consumidor declara su regla. Tampoco dice en qué zona de
# salario mínimo se mide la primera banda: la tabla dice «Salario Mínimo».
# ---------------------------------------------------------------------------
CEV_PATRON_BANDAS_2026 = [
    {
        "texto": "1.0 SM",
        "desde": None,
        "hasta": {"veces": "1.00", "unidad": "salario_minimo"},
        "tasa_patron": "0.0315",
    },
    {
        "texto": "1.01 SM a 1.50 UMA",
        "desde": {"veces": "1.01", "unidad": "salario_minimo"},
        "hasta": {"veces": "1.50", "unidad": "uma"},
        "tasa_patron": "0.03676",
    },
    {
        "texto": "1.51 a 2.00 UMA",
        "desde": {"veces": "1.51", "unidad": "uma"},
        "hasta": {"veces": "2.00", "unidad": "uma"},
        "tasa_patron": "0.04851",
    },
    {
        "texto": "2.01 a 2.50 UMA",
        "desde": {"veces": "2.01", "unidad": "uma"},
        "hasta": {"veces": "2.50", "unidad": "uma"},
        "tasa_patron": "0.05556",
    },
    {
        "texto": "2.51 a 3.00 UMA",
        "desde": {"veces": "2.51", "unidad": "uma"},
        "hasta": {"veces": "3.00", "unidad": "uma"},
        "tasa_patron": "0.06026",
    },
    {
        "texto": "3.01 a 3.50 UMA",
        "desde": {"veces": "3.01", "unidad": "uma"},
        "hasta": {"veces": "3.50", "unidad": "uma"},
        "tasa_patron": "0.06361",
    },
    {
        "texto": "3.51 a 4.00 UMA",
        "desde": {"veces": "3.51", "unidad": "uma"},
        "hasta": {"veces": "4.00", "unidad": "uma"},
        "tasa_patron": "0.06613",
    },
    {
        "texto": "4.01 UMA en adelante",
        "desde": {"veces": "4.01", "unidad": "uma"},
        "hasta": None,
        "tasa_patron": "0.07513",
    },
]


def _renglon(concepto, label, *, patron, trabajador, base, articulo, notas, **extra):
    """Un renglón de cuotas con su cita completa. Las tasas en FRACCIÓN decimal."""
    row = {
        "concepto": concepto,
        "label": label,
        "patron": patron,
        "trabajador": trabajador,
        "base": base,
        "official_id": extra.pop("official_id", "lss"),
        "articulo": articulo,
        "fuente": extra.pop("fuente", CAMARA_LSS),
        "source_url": extra.pop("source_url", CAMARA_LSS_URL),
        "dof_date": extra.pop("dof_date", None),
        "dof_codigo": extra.pop("dof_codigo", ""),
        "provenance": "published",
        "notas": notas,
    }
    row.update(extra)
    return row


# ---------------------------------------------------------------------------
# La tabla imss_rates 2026. ``patron`` / ``trabajador`` en fracción decimal
# del ``base`` (``None`` = esa parte no cotiza el ramo). Bases:
#   * ``uma_diaria``      — la UMA diaria, por día cotizado (cuota fija).
#   * ``sbc``             — el salario base de cotización diario, ya topado.
#   * ``sbc_excedente``   — la parte del SBC que excede ``umbral``.
# ---------------------------------------------------------------------------
IMSS_RATES_2026 = [
    _renglon(
        "em_cuota_fija",
        "Enfermedades y maternidad, prestaciones en especie: cuota fija",
        patron="0.204",
        trabajador=None,
        base="uma_diaria",
        articulo="106 fr. I y transitorio DÉCIMO NOVENO (LSS, DOF 21-12-1995)",
        notas=(
            "Art. 106 fr. I: «trece punto nueve por ciento de un salario mínimo "
            "general diario para el Distrito Federal». Transitorio DÉCIMO "
            "NOVENO: esa tasa «se incrementará el primero de julio de cada año "
            "en sesenta y cinco centésimas de punto porcentual», de 1998 a "
            "2007: diez incrementos, 13.9 + 10 x 0.65 = 20.40 %. La base pasa "
            "a la UMA diaria por el " + DESINDEXACION + "."
        ),
    ),
    _renglon(
        "em_excedente",
        "Enfermedades y maternidad, prestaciones en especie: excedente de 3 UMA",
        patron="0.011",
        trabajador="0.004",
        base="sbc_excedente",
        umbral={"veces": "3", "unidad": "uma"},
        articulo="106 fr. II y transitorio DÉCIMO NOVENO (LSS, DOF 21-12-1995)",
        notas=(
            "Art. 106 fr. II: sobre la diferencia entre el SBC y «tres veces el "
            "salario mínimo general diario para el Distrito Federal», seis por "
            "ciento patronal y dos por ciento obrero. Transitorio DÉCIMO "
            "NOVENO: se reducen el 1 de julio de cada año, de 1998 a 2007, "
            "cuarenta y nueve centésimas (patrón) y dieciséis centésimas "
            "(trabajador): 6 - 10 x 0.49 = 1.10 % y 2 - 10 x 0.16 = 0.40 %. El "
            "umbral pasa a 3 UMA por el " + DESINDEXACION + "."
        ),
    ),
    _renglon(
        "em_prestaciones_dinero",
        "Enfermedades y maternidad, prestaciones en dinero",
        patron="0.007",
        trabajador="0.0025",
        base="sbc",
        articulo="107",
        notas=(
            "Art. 107: cuota del uno por ciento sobre el SBC; setenta por ciento "
            "al patrón (0.70 %), veinticinco por ciento al trabajador (0.25 %) y "
            "cinco por ciento al Gobierno Federal."
        ),
    ),
    _renglon(
        "em_gastos_medicos_pensionados",
        "Enfermedades y maternidad: gastos médicos de pensionados",
        patron="0.0105",
        trabajador="0.00375",
        base="sbc",
        articulo="25 párrafo segundo",
        notas=(
            "Art. 25 párr. segundo: cuota de uno punto cinco por ciento sobre el "
            "SBC; al patrón «el uno punto cero cinco por ciento», a los "
            "trabajadores «el cero punto trescientos setenta y cinco por ciento» "
            "y al Estado el cero punto cero setenta y cinco por ciento."
        ),
    ),
    _renglon(
        "invalidez_vida",
        "Invalidez y vida",
        patron="0.0175",
        trabajador="0.00625",
        base="sbc",
        articulo="147",
        notas=(
            "Art. 147: «el uno punto setenta y cinco por ciento y el cero punto "
            "seiscientos veinticinco por ciento sobre el salario base de "
            "cotización», a patrones y trabajadores respectivamente."
        ),
    ),
    _renglon(
        "retiro",
        "Retiro",
        patron="0.02",
        trabajador=None,
        base="sbc",
        articulo="168 fr. I",
        notas="Art. 168 fr. I: «el dos por ciento del salario base de cotización».",
    ),
    _renglon(
        "cesantia_vejez",
        "Cesantía en edad avanzada y vejez",
        patron=None,
        trabajador="0.01125",
        base="sbc",
        bandas_patron=CEV_PATRON_BANDAS_2026,
        articulo=(
            "168 fr. II a) y b); transitorio SEGUNDO del decreto DOF 16-12-2020 "
            "(columna 2026)"
        ),
        fuente=(
            "DOF 16-12-2020, «DECRETO por el que se reforman, adicionan y derogan "
            "diversas disposiciones de la Ley del Seguro Social y de la Ley de los "
            "Sistemas de Ahorro para el Retiro» (codigo 5607729), transitorio "
            "SEGUNDO; " + CAMARA_LSS + ", art. 168 fr. II"
        ),
        source_url=CEV_DOF["source_url"],
        dof_date=CEV_DOF["dof_date"],
        dof_codigo=CEV_DOF["dof_codigo"],
        notas=(
            "La cuota PATRONAL es una tabla por salario base de cotización "
            "(``bandas_patron``): la columna 2026 del transitorio SEGUNDO, leída "
            "de la imagen de la tabla en nota_detalle (shcp11_Cimg_858340.png). "
            "El art. 168 fr. II a) trae la columna de 2030. La cuota OBRERA es "
            "fija: fr. II b), «uno punto ciento veinticinco por ciento». El "
            "texto no dice cómo tratar un SBC entre dos límites impresos ni en "
            "qué zona se mide «1.0 SM»; Tezca no lo resuelve."
        ),
    ),
    _renglon(
        "guarderias_prestaciones_sociales",
        "Guarderías y prestaciones sociales",
        patron="0.01",
        trabajador=None,
        base="sbc",
        articulo="211 y 212",
        notas=(
            "Art. 211: «el uno por ciento sobre el salario base de cotización». "
            "Art. 212: «Los patrones cubrirán íntegramente la prima»."
        ),
    ),
    _renglon(
        "infonavit",
        "Aportación al INFONAVIT",
        patron="0.05",
        trabajador=None,
        base="sbc",
        official_id="lifnvt",
        articulo="29 fr. II",
        fuente=(
            "Cámara de Diputados, LeyesBiblio: Ley del INFONAVIT, texto vigente, "
            "última reforma DOF 21-02-2025 (LawArticle lifnvt/29 de Tezca)"
        ),
        source_url="https://www.diputados.gob.mx/LeyesBiblio/doc/LIFNVT.doc",
        notas=(
            "Art. 29 fr. II: «aportaciones del cinco por ciento sobre el salario "
            "de los trabajadores»; para la base y su límite superior «se aplicará "
            "lo contenido en la Ley del Seguro Social» (el SBC con el tope del "
            "art. 28). No es cuota del IMSS: viaja en esta tabla porque se "
            "calcula sobre la misma base."
        ),
    ),
    _renglon(
        "tope_sbc",
        "Tope del salario base de cotización",
        patron=None,
        trabajador=None,
        base="sbc",
        tope={"veces": "25", "unidad": "uma"},
        articulo="28",
        notas=(
            "Art. 28: «veinticinco veces el salario mínimo general que rija en el "
            "Distrito Federal», leído en UMA por el " + DESINDEXACION + ". Es el "
            "mismo valor que publica /labor/rules/?kind=sbc_tope_veces_uma desde "
            "el 2016-01-28, con su serie histórica; aquél es la fuente con "
            "vigencias, éste lo repite para que la tabla del ejercicio esté "
            "completa. La coherencia entre ambos la vigila cuotas_coherence."
        ),
    ),
]

IMSS_RATES_2026_TABLE = {
    "year": 2026,
    "period": "daily",
    "legal_basis": "LSS arts. 25, 28, 106, 107, 147, 168, 211 y 212; LINFONAVIT art. 29 fr. II",
    "vigencia_from": "2026-01-01",
    "vigencia_to": "2026-12-31",
    "dof_date": CEV_DOF["dof_date"],
    "dof_codigo": CEV_DOF["dof_codigo"],
    "source_url": CEV_DOF["source_url"],
    "source_citation": (
        "Cuota patronal de cesantía y vejez 2026: DOF 16-12-2020 (codigo "
        "5607729), transitorio SEGUNDO. Las demás tasas: " + CAMARA_LSS + " "
        "(arts. 25, 28, 106 y transitorio DÉCIMO NOVENO de 1995, 107, 147, 168, "
        "211, 212) y Ley del INFONAVIT art. 29 fr. II; unidad de cuenta: DOF "
        "27-01-2016 (codigo 5423663). Cada renglón lleva su propia cita."
    ),
    "notes": (
        f"Leído de fuente primaria el {VERIFIED_ON} (ratificación de Tezca, F1). "
        "La vigencia es el año calendario 2026 porque la tabla del transitorio "
        "SEGUNDO publica una columna por año; las demás tasas no cambiaron. "
        "Tasas en fracción decimal. RIESGO DE TRABAJO NO ESTÁ: es la prima de "
        "cada patrón (LSS 71-74), no una constante del ejercicio; la prima media "
        "por clase del art. 73 sólo rige al inscribirse o cambiar de actividad."
    ),
}

# ---------------------------------------------------------------------------
# Impuesto sobre nóminas por entidad. ``value`` en PORCENTAJE.
#
# Morelos lo llama «impuesto sobre erogaciones por remuneraciones al trabajo
# personal» (Ley General de Hacienda del Estado de Morelos, LGHEM). La CDMX,
# «Impuesto sobre Nóminas» (Código Fiscal de la Ciudad de México, CFCDMX).
# ---------------------------------------------------------------------------
POE_MORELOS = "https://periodico.morelos.gob.mx/obtenerPDF/{anio}/{numero}.pdf"
CFCDMX_URL = (
    "https://data.consejeria.cdmx.gob.mx/images/leyes/2025/2026/210126/"
    "CODIGO_FISCAL_DE_LA_CDMX_26.1.pdf"
)

ISN_TASAS = [
    {
        "entidad": "MOR",
        "value": "2.5",
        "vigencia_from": "2025-01-01",
        # El fin NO es inferencia: el Decreto 997 reforma el mismo artículo y
        # entra en vigor el 01-01-2026 (transitoria SEGUNDA). La tasa de 2.5 %
        # dejó de regir el día anterior.
        "vigencia_to": "2025-12-31",
        "legal_basis": "LGHEM Art. 58 BIS-4",
        "publicacion_fecha": "2024-12-31",
        "source_url": POE_MORELOS.format(anio=2024, numero=6382),
        "source_citation": (
            "Periódico Oficial «Tierra y Libertad» 6382 Extraordinaria, "
            "31-12-2024, Decreto Número Veinticuatro (reforma, entre otros, el "
            "artículo 58 BIS-4 de la Ley General de Hacienda del Estado de "
            "Morelos), Artículo Primero; disposición transitoria SEGUNDA: en "
            "vigor a partir del 1 de enero de 2025"
        ),
        "notes": (
            f"Leído el {VERIFIED_ON} del PDF oficial del Periódico Oficial. Texto: "
            "«El impuesto sobre erogaciones por remuneraciones al trabajo personal "
            "se determinará aplicando la tasa del 2.5% sobre el monto total de las "
            "erogaciones…». El dictamen bajó la tasa propuesta (3 %) a 2.5 %. Fin "
            "de vigencia 31-12-2025: el Decreto 997 (POE 6506 Ext.) reforma el "
            "mismo artículo desde el 01-01-2026."
        ),
    },
    {
        "entidad": "MOR",
        "value": "3.0",
        "vigencia_from": "2026-01-01",
        "vigencia_to": None,
        "legal_basis": "LGHEM Art. 58 BIS-4",
        "publicacion_fecha": "2025-12-22",
        "source_url": POE_MORELOS.format(anio=2025, numero=6506),
        "source_citation": (
            "Periódico Oficial «Tierra y Libertad» 6506 Extraordinaria, "
            "22-12-2025, Decreto Novecientos Noventa y Siete (reforma, entre "
            "otros, el artículo 58 BIS-4 de la Ley General de Hacienda del Estado "
            "de Morelos), Artículo Segundo; disposición transitoria SEGUNDA: en "
            "vigor a partir del 01 de enero de 2026"
        ),
        "notes": (
            f"Leído el {VERIFIED_ON} del PDF oficial del Periódico Oficial. Texto: "
            "«…se determinará aplicando la tasa del 3.0% sobre el monto total de "
            "las erogaciones efectuadas por concepto de remuneraciones al trabajo "
            "personal». El dictamen bajó la tasa propuesta (4.25 %) a 3.0 %. "
            "Vigencia abierta: ningún texto posterior leído la cierra."
        ),
    },
    {
        "entidad": "CMX",
        "value": "4.0",
        "vigencia_from": "2025-01-01",
        "vigencia_to": None,
        "legal_basis": "CFCDMX Art. 158",
        "publicacion_fecha": "2024-12-27",
        "source_url": CFCDMX_URL,
        "source_citation": (
            "Código Fiscal de la Ciudad de México, texto vigente (Consejería "
            "Jurídica y de Servicios Legales; última reforma G.O. CDMX "
            "19-12-2025), art. 158 «Artículo Reformado G.O.CDMX. 27/12/24»; "
            "decreto publicado en la Gaceta Oficial de la Ciudad de México el "
            "27-12-2024, transitorio PRIMERO: en vigor el 1º de enero de 2025"
        ),
        "notes": (
            f"Leído el {VERIFIED_ON} del texto vigente que publica la Consejería "
            "(CODIGO_FISCAL_DE_LA_CDMX_26.1.pdf, con certificado TLS verificado). "
            "Texto: «El Impuesto sobre Nóminas se determinará, aplicando la tasa "
            "del 4% sobre el monto total de las erogaciones realizadas por "
            "concepto de remuneraciones al trabajo personal subordinado». La "
            "reforma del 19-12-2025 no tocó el art. 158. Tezca publica la tasa "
            "del Código; reducciones o estímulos que se otorguen por resolución de "
            "carácter general no están en esta fila."
        ),
    },
]
