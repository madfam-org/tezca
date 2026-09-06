"""Las reglas que el catálogo de obligaciones del HCM consulta y faltaban (T-1c).

El catálogo del HCM (``apps/api/cumplimiento/catalogo_seed.py`` en
symbiosis-hcm) declara cada obligación **sin una sola cifra legal dentro**: un
renglón lleva el fundamento (``tezca_official_id`` + ``articulo``) y el nombre
del ``kind`` con el que Tezca contesta la ventana. Cuando Tezca no publica ese
``kind``, el módulo muestra la obligación con «ventana por publicar» — visible,
nunca inventada.

Este módulo cierra los cuatro ``kind`` que quedaban así después de T-1a y T-1b.
Los otros diez que el catálogo consulta ya los publican ``labor_seed_data`` y
``labor_seed_fiscal``; la prueba ``test_labor_seed_hcm`` lo fija para que un
``kind`` nuevo en el HCM no pueda pasar inadvertido.

TRES CORRECCIONES AL CATÁLOGO DEL HCM
=====================================
La lectura primaria contradijo el fundamento que el catálogo del HCM anota. Se
publica lo que dice la fuente, y la discrepancia se reporta para que el HCM
corrija su renglón — no al revés, y sin inventar un número para que cuadre:

1. ``opinion_32d_vigencia_dias`` — el catálogo cita CFF 32-D. El CFF **no fija
   vigencia alguna**: delega el procedimiento en reglas de carácter general.
   Los treinta días naturales están en la **RMF 2026 regla 2.1.36** (no la
   2.1.37, que es la aplicación en línea para quien ejerce recursos públicos).
2. ``comisiones_mixtas_umbral_personas`` — el catálogo cita LFT 132. Esa
   fracción (XXVIII) obliga a «participar en la integración y funcionamiento de
   las Comisiones que deban formarse», pero **no fija umbral**. El umbral está
   en **LFT 153-E**: más de 50 personas.
3. ``cfdi_nomina_por_periodo`` — el nombre del ``kind`` asume un periodo.
   LISR 99 fr. III ata el comprobante a **la fecha de la erogación**, no a un
   periodo de calendario. Se publica esa regla con su forma real; el ``kind``
   conserva el nombre que el contrato C1 ya fijó, porque renombrarlo rompería
   al consumidor sin cambiar la ley.

Fuentes, todas leídas en este carril:

* Cámara de Diputados, LeyesBiblio, texto vigente (.doc): LISR 01-04-2024,
  LFT 14-05-2026, CFF 09-04-2026.
* DOF ``nota_to_doc.php``: Resolución Miscelánea Fiscal para 2026 (``codigo``
  5777217, 28-12-2025) y Reglas de Operación del Programa Jóvenes Construyendo
  el Futuro (``codigo`` 5746424, 31-12-2024, edición matutina).
"""

from apps.api.fiscal_models import Provenance
from apps.api.labor_models import LaborRule

CAMARA = "Cámara de Diputados, LeyesBiblio (texto vigente)"
DOF = "Diario Oficial de la Federación"
STPS = "Secretaría del Trabajo y Previsión Social"

URL = {
    "lisr": "https://www.diputados.gob.mx/LeyesBiblio/doc/LISR.doc",
    "lft": "https://www.diputados.gob.mx/LeyesBiblio/doc/LFT.doc",
    "rmf2026": "https://dof.gob.mx/nota_detalle.php?codigo=5777217&fecha=28/12/2025",
    "jcf": "https://dof.gob.mx/nota_detalle.php?codigo=5746424&fecha=31/12/2024",
}

K = LaborRule.Kind

REGLAS_HCM = [
    # -- Opinión del cumplimiento (32-D): 30 días naturales ----------------
    #
    # La vigencia NO está en el CFF. El art. 32-D delega el procedimiento en
    # "reglas de carácter general" y sólo impone periodicidad propia a las
    # sociedades anónimas bursátiles (opinión mensual). Publicar 30 días con
    # official_id='cff' sería atribuir al Código algo que no dice, y el día que
    # la RMF cambie el plazo nadie sabría dónde buscarlo.
    {
        "kind": K.OPINION_32D_VIGENCIA_DIAS,
        "value": 30,
        "unit": "dias_naturales",
        "label": "Opinión del cumplimiento en sentido positivo: vigencia",
        "official_id": "rmf",
        "article": "2.1.36",
        # La RMF es anual: Transitorio Primero, en vigor el 1 de enero de 2026
        # y vigente hasta el 31 de diciembre de 2026. La fila se cierra en esa
        # fecha a propósito — la RMF 2027 es otra regla, y un consumidor que
        # pregunte por 2027 debe recibir "no hay regla", no una extrapolación.
        "effective_from": "2026-01-01",
        "effective_to": "2026-12-31",
        "source": DOF,
        "source_url": URL["rmf2026"],
        "dof_date": "2025-12-28",
        "dof_codigo": "5777217",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "RMF 2026 regla 2.1.36, párrafo penúltimo: 'La opinión del "
            "cumplimiento de obligaciones fiscales ... que se emita en sentido "
            "positivo, tendrá una vigencia de treinta días naturales a partir "
            "de la fecha de emisión.' El CFF 32-D no fija plazo: remite a "
            "reglas de carácter general. La regla 2.1.37 que cita el catálogo "
            "del HCM es otra cosa — la aplicación en línea para quien ejerce "
            "recursos públicos en contrataciones mayores a $300,000.00. "
            "Sólo la opinión POSITIVA tiene vigencia; una negativa no vence, "
            "se corrige."
        ),
    },
    # -- CFDI de nómina: en la fecha de la erogación -----------------------
    #
    # El kind se llama '..._por_periodo' porque así lo fijó el contrato C1,
    # pero la ley no habla de periodos: habla de la erogación. El valor dice la
    # verdad y el nombre queda; renombrar el kind rompería a HCM sin mover una
    # coma de la LISR.
    {
        "kind": K.CFDI_NOMINA_POR_PERIODO,
        "value": {
            "disparo": "erogacion",
            "regla": (
                "El CFDI se expide y entrega en la fecha en que se realiza la "
                "erogación, no al cierre de un periodo."
            ),
            "aplica_a": "pagos_del_capitulo_i_del_titulo_iv",
            "sirve_como": [
                "constancia o recibo de pago para efectos laborales (LFT 132 "
                "fracciones VII y VIII)",
                "prueba del pago del salario (LFT 804 fracciones II y IV)",
            ],
            "periodicidad_de_pago": (
                "La periodicidad (c_PeriodicidadPago) describe la nómina y va "
                "en el complemento; no es el plazo para timbrar."
            ),
        },
        "unit": "regla",
        "label": "CFDI de nómina: cuándo debe expedirse",
        "official_id": "lisr",
        "article": "99-III",
        # El texto vigente de la fracción III proviene del decreto que sustituyó
        # las constancias por comprobantes fiscales; la LISR vigente rige desde
        # su entrada en vigor el 1 de enero de 2014.
        "effective_from": "2014-01-01",
        "source": CAMARA,
        "source_url": URL["lisr"],
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 99 fr. III: 'Expedir y entregar comprobantes fiscales a las "
            "personas que reciban pagos por los conceptos a que se refiere "
            "este Capítulo, en la fecha en que se realice la erogación "
            "correspondiente, los cuales podrán utilizarse como constancia o "
            "recibo de pago para efectos de la legislación laboral a que se "
            "refieren los artículos 132 fracciones VII y VIII, y 804, primer "
            "párrafo, fracciones II y IV, de la Ley Federal de Trabajo.' "
            "El nombre del kind dice 'por_periodo' por el contrato C1; la ley "
            "ata el comprobante a la erogación. Los plazos de timbrado por "
            "tamaño de patrón viven en la RMF (facilidad del art. 27 fr. V "
            "LISR) y no se leyeron en este carril."
        ),
    },
    # -- Comisiones mixtas de capacitación: más de 50 personas -------------
    #
    # Corrección de artículo: el catálogo del HCM funda esto en LFT 132, que
    # no fija umbral. Es el mismo error que T-1b corrigió con LFT 422-425 para
    # el reglamento interior, y por la misma razón se resuelve igual: se
    # publica el artículo que SÍ dice el número.
    {
        "kind": K.COMISIONES_MIXTAS_UMBRAL_PERSONAS,
        "value": {
            "umbral_personas": 50,
            "comparador": "mayor_que",
            "obligatoria_desde_personas": 51,
            "nombre": (
                "Comisión Mixta de Capacitación, Adiestramiento y Productividad"
            ),
            "integracion": (
                "Por igual número de representantes de las personas "
                "trabajadoras y de la parte patronal."
            ),
            "hasta_50_personas": (
                "No se constituye la comisión. La STPS y la Secretaría de "
                "Economía incentivan su productividad con los programas del "
                "art. 153-J."
            ),
            "funciones": [
                "Vigilar, instrumentar, operar y mejorar los sistemas y los "
                "programas de capacitación y adiestramiento",
                "Proponer cambios en maquinaria, equipos, organización del "
                "trabajo y relaciones laborales",
                "Proponer las medidas acordadas por el Comité Nacional y los "
                "Comités Estatales de Productividad",
                "Vigilar el cumplimiento de los acuerdos de productividad",
                "Resolver las objeciones sobre la distribución de los "
                "beneficios de la productividad",
            ],
        },
        "unit": "personas",
        "label": "Comisión mixta de capacitación: a partir de cuántas personas",
        "official_id": "lft",
        "article": "153-E",
        # Reformado DOF 30-11-2012 (la reforma que le añadió "y Productividad"
        # y el párrafo de micro y pequeñas empresas). En vigor al día siguiente.
        "effective_from": "2012-12-01",
        "source": CAMARA,
        "source_url": URL["lft"],
        "dof_date": "2012-11-30",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 153-E: 'En las empresas que tengan más de 50 trabajadores se "
            "constituirán Comisiones Mixtas de Capacitación, Adiestramiento y "
            "Productividad'. Segundo párrafo: 'las micro y pequeñas empresas, "
            "que son aquellas que cuentan con hasta 50 trabajadores'. El "
            "umbral es ESTRICTO: con 50 personas no hay obligación; con 51 sí. "
            "El catálogo del HCM funda esta obligación en el art. 132, cuya "
            "fracción XXVIII obliga a 'participar en la integración y "
            "funcionamiento de las Comisiones que deban formarse' sin fijar "
            "número alguno. Artículo adicionado DOF 28-04-1978, reformado DOF "
            "30-11-2012."
        ),
    },
    # -- JCF: la validación es mensual -------------------------------------
    #
    # official_id vacío a propósito: las Reglas de Operación del programa no
    # tienen identificador estable en el corpus de Tezca (el catálogo del HCM
    # ya lo declara así). La procedencia se sostiene con dof_codigo + dof_date,
    # que resuelven a un documento único, y el artículo se nombra como texto.
    {
        "kind": K.JCF_VALIDACION_PERIODICIDAD_DIAS,
        "value": {
            "periodicidad": "mensual",
            "ventana": "ultima_semana_del_mes",
            "medio": "Plataforma Digital del Programa",
            "quien_evalua": "la Tutora o el Tutor designado por el Centro de Trabajo",
            "mutua": (
                "La evaluación es mutua: la persona aprendiz también evalúa "
                "mensualmente a su Tutora o Tutor."
            ),
            "efecto_de_no_validar": (
                "El pago a la persona aprendiz verificada procede por "
                "afirmativa ficta salvo que la Tutora o el Tutor dé aviso de "
                "baja: no validar no detiene la beca, pero incumple la "
                "obligación del Centro de Trabajo."
            ),
        },
        # La unidad no es un número de días porque la regla no lo es: es un
        # ciclo de calendario con ventana. Un consumidor que reste 30 días a la
        # fecha de alta calcularía un vencimiento que las Reglas no fijan.
        "unit": "ciclo_mensual",
        "label": "JCF: periodicidad de la validación de la persona aprendiz",
        "official_id": "",
        "article": "Reglas de Operación JCF, apartado V y obligaciones del Centro de Trabajo",
        # Transitorio PRIMERO: en vigor el día de su publicación.
        "effective_from": "2024-12-31",
        "source": STPS,
        "source_url": URL["jcf"],
        "dof_date": "2024-12-31",
        "dof_codigo": "5746424",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Reglas de Operación del Programa Jóvenes Construyendo el Futuro, "
            "DOF 31-12-2024 (edición matutina). Apartado V 'Evaluación de "
            "Tutora o Tutor y Evaluación de Aprendices': 'Podrá realizarse "
            "mutuamente entre las y los Beneficiarios y las y los Tutores "
            "durante la última semana de cada mes, a través de la Plataforma "
            "Digital u otros medios autorizados.' Obligaciones del Centro de "
            "Trabajo, fracción X: 'Verificar que cada Tutora o Tutor designado "
            "evalúe mensualmente el desempeño de las y los Aprendices'. "
            "Transitorio TERCERO: las Reglas 'mantendrán su vigencia en "
            "ejercicios fiscales subsecuentes ... hasta en tanto se emitan "
            "otras Reglas de Operación que las sustituyan', por eso siguen "
            "rigiendo en 2026 sin publicación nueva (se barrió el DOF de "
            "diciembre de 2025 a febrero de 2026 sin encontrar sucesoras). "
            "official_id vacío: el corpus de Tezca no tiene un identificador "
            "estable para las Reglas de Operación del programa; la fila se "
            "cita por dof_codigo y fecha."
        ),
    },
]
