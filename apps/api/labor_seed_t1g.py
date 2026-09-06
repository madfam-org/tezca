"""El tope del SBC, el seguro de estudiantes y la regla JCF corregida (T-1g).

Tres cosas distintas que este carril leyó de fuente primaria, y una corrección
append-only sobre una fila que T-1c publicó citando un documento abrogado.

TRES LECTURAS QUE CORRIGEN LO QUE SE PIDIÓ
==========================================

1. **El tope del SBC (HP-2).** El brief pide «25 veces la UMA desde el decreto
   de desindexación». Es correcto en el resultado y engañoso en el camino: el
   **art. 28 de la LSS no se ha reformado nunca** y sigue diciendo, palabra por
   palabra, «veinticinco veces el salario mínimo general que rija en el Distrito
   Federal». Lo que convierte esa mención en UMA es el **transitorio TERCERO**
   del decreto de desindexación (DOF 27-01-2016, ``codigo`` 5423663), que ordena
   que *todas* las menciones al salario mínimo como unidad de cuenta «se
   entenderán referidas a la Unidad de Medida y Actualización». Por eso la fila
   se publica con **dos vigencias**: la de 1997 con `unidad = salario_minimo` y
   la de 2016 con `unidad = uma`. Un consumidor que calcule un SBC de 2015 con
   la UMA se equivoca; uno que calcule el de hoy con el salario mínimo, también.

2. **El seguro de estudiantes (HP-5): las DOS citas del plan están mal.** El
   plan dice LSS 13 fr. V y el catálogo del HCM sembró LSS 240. Lectura primaria
   del texto vigente (LeyesBiblio, LSS última reforma DOF 15-01-2026):

   * **LSS 13 fr. V** son «los trabajadores al servicio de las administraciones
     públicas de la Federación, entidades federativas y municipios». Nada de
     estudiantes. Las fracciones III y IV —que en su día cubrían a otros
     colectivos— **están derogadas** (DOF 01-12-2023 y 02-07-2019).
   * **LSS 240** es el **seguro de salud para la familia**: «Todas las familias
     en México tienen derecho a un seguro de salud para sus miembros». Tampoco.
   * La palabra «estudiante» **no aparece una sola vez** en la LSS vigente, y
     «facultativo» sólo aparece en un transitorio de 1995 que declara extinta
     la figura.

   El fundamento correcto es el **art. 12 fr. III de la LSS** («las personas que
   determine el Ejecutivo Federal a través del Decreto respectivo») **más el
   Decreto de estudiantes** (DOF 14-09-1998, ``codigo`` 4892913), que es el que
   los incorpora. El propio decreto lo dice en su considerando segundo: «la Ley
   del Seguro Social vigente a partir del 1o. de julio de 1997 **no contempla el
   seguro facultativo**». Llamarlo «seguro facultativo» es un nombre heredado
   de 1987; jurídicamente es una incorporación al **régimen obligatorio**.

   **El decreto no fija ventana alguna.** La regla se publica sin plazo y lo
   dice en su `value`, para que el HCM muestre la obligación sin inventar un
   vencimiento. Quien inscribe es la institución educativa, no el patrón.

3. **La regla del JCF citaba las Reglas de 2025, abrogadas (HP-0d).** T-1c la
   publicó con ``dof_codigo`` 5746424 (DOF 31-12-2024) y ``official_id`` vacío.
   Las Reglas de Operación **2026** (DOF 31-12-2025, ``codigo`` 5777674) las
   abrogan expresamente y ya viven en el corpus como ``jcf-reglas-2026``. La
   fila vieja se **cierra** el 31-12-2025 y la nueva rige desde el 01-01-2026.

   Y al leerlas cambió el fondo, no sólo la cita: las Reglas 2026 **suprimieron**
   la obligación del Centro de Trabajo de «verificar que cada Tutora o Tutor
   evalúe mensualmente» (era la fr. X de 2024; el apartado D) de la regla Décima
   Segunda, con sus XXIV fracciones, ya no la trae). En 2026 la evaluación
   mensual es un **derecho** de la Tutora o Tutor (apartado E fr. IV) y de la
   persona aprendiz (apartado A fr. XIII), y la regla Décima A) V la enuncia con
   «**podrá** realizarse mutuamente». Tampoco hay «afirmativa ficta»: la frase
   no aparece en el documento. La fila nueva dice eso, y no lo que decía la
   vieja — copiar la nota de 2024 sobre la cita de 2026 habría dejado a HCM
   exigiendo una obligación que las Reglas vigentes ya no imponen.

Fuentes, todas leídas en este carril:

* Cámara de Diputados, LeyesBiblio, texto vigente (.doc): LSS 15-01-2026
  (arts. 12, 13, 28, 106, 240 y transitorios).
* DOF ``nota_detalle.php``: decreto de desindexación del salario mínimo
  (``codigo`` 5423663, 27-01-2016) y Decreto de estudiantes (``codigo``
  4892913, 14-09-1998).
* Corpus de Tezca: ``data/jcf/jcf-reglas-2026.xml`` (DOF 5777674, 31-12-2025),
  ingerido por ``manage.py ingest_jcf``.
"""

from apps.api.fiscal_models import Provenance
from apps.api.labor_models import LaborRule

CAMARA = "Cámara de Diputados, LeyesBiblio (texto vigente)"
DOF = "Diario Oficial de la Federación"
STPS = "Secretaría del Trabajo y Previsión Social"

URL = {
    "lss": "https://www.diputados.gob.mx/LeyesBiblio/doc/LSS.doc",
    "desindexacion": (
        "https://dof.gob.mx/nota_detalle.php?codigo=5423663&fecha=27/01/2016"
    ),
    "estudiantes": (
        "https://dof.gob.mx/nota_detalle.php?codigo=4892913&fecha=14/09/1998"
    ),
    "jcf2026": "https://dof.gob.mx/nota_detalle.php?codigo=5777674&fecha=31/12/2025",
}

K = LaborRule.Kind

#: El día en que el decreto de desindexación entró en vigor: su transitorio
#: PRIMERO dice «al día siguiente al de su publicación», y se publicó el
#: 27-01-2016. Es la fecha que parte en dos la serie del tope del SBC.
DESINDEXACION_EN_VIGOR = "2016-01-28"

REGLAS_T1G = [
    # -- El tope del SBC, antes de la desindexación ------------------------
    #
    # La LSS vigente desde el 01-07-1997 (art. 28) fija el límite superior en
    # veinticinco veces el salario mínimo del entonces Distrito Federal. Esta
    # fila NO es histórica por gusto: sin ella, `huecos_en_la_serie` tendría
    # razón en quejarse, y un consumidor que reconstruya un SBC de 2010 para
    # una diferencia de cuotas recibiría la UMA, que en 2010 no existía.
    {
        "kind": K.SBC_TOPE_VECES_UMA,
        "value": {
            "veces": 25,
            "unidad": "salario_minimo",
            "unidad_detalle": (
                "Salario mínimo general que rija en el Distrito Federal, "
                "según la letra del art. 28."
            ),
            "limite_inferior": {
                "veces": 1,
                "unidad": "salario_minimo",
                "unidad_detalle": (
                    "Salario mínimo general del área geográfica respectiva."
                ),
            },
        },
        "unit": "veces_salario_minimo",
        "label": "Tope del salario base de cotización (antes de la desindexación)",
        "official_id": "lss",
        "article": "28",
        # La LSS de 1995 entró en vigor el 1 de julio de 1997 (transitorio
        # primero, tras la reforma que corrió la fecha).
        "effective_from": "1997-07-01",
        "effective_to": "2016-01-27",
        "source": CAMARA,
        "source_url": URL["lss"],
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 28: 'Los asegurados se inscribirán con el salario base de "
            "cotización que perciban en el momento de su afiliación, "
            "estableciéndose como límite superior el equivalente a "
            "veinticinco veces el salario mínimo general que rija en el "
            "Distrito Federal y como límite inferior el salario mínimo "
            "general del área geográfica respectiva.' El artículo NO ha sido "
            "reformado: su texto sigue diciendo 'salario mínimo'. Esta fila "
            "cubre el periodo en que esa mención se leía literalmente, y se "
            "cierra el 27-01-2016 porque al día siguiente entró en vigor el "
            "decreto de desindexación."
        ),
    },
    # -- El tope del SBC, ya en UMA ---------------------------------------
    #
    # Misma letra del art. 28, otra unidad de cuenta. El cambio NO lo hizo una
    # reforma a la LSS —que no la ha habido— sino el transitorio TERCERO del
    # decreto constitucional de desindexación, que reescribe la lectura de
    # todas las menciones al salario mínimo como unidad de cuenta a la vez.
    {
        "kind": K.SBC_TOPE_VECES_UMA,
        "value": {
            "veces": 25,
            "unidad": "uma",
            "unidad_detalle": (
                "Unidad de Medida y Actualización diaria. El art. 28 sigue "
                "diciendo 'salario mínimo'; la sustitución la ordena el "
                "transitorio TERCERO del decreto de desindexación, no una "
                "reforma a la LSS."
            ),
            # El piso NO se desindexó, y es el error que un consumidor comete
            # con más facilidad: la Constitución (art. 123 A fr. VI, en el
            # mismo decreto) prohíbe usar el salario mínimo «para fines ajenos
            # a su naturaleza», y el límite inferior del SBC es precisamente
            # su naturaleza — es un salario, no una unidad de cuenta.
            "limite_inferior": {
                "veces": 1,
                "unidad": "salario_minimo",
                "unidad_detalle": (
                    "Salario mínimo general del área geográfica respectiva. "
                    "El piso NO se convierte a UMA: ahí el salario mínimo se "
                    "usa como salario, que es su naturaleza propia, y el "
                    "transitorio TERCERO sólo alcanza a las menciones que lo "
                    "usan como unidad de cuenta, índice, base o referencia."
                ),
            },
            "aplica_a": "salario_base_de_cotizacion",
            "valor_de_la_uma": (
                "Tezca lo sirve en el feed fiscal: GET /api/v1/fiscal/uma/. "
                "Esta regla publica el multiplicador, no el importe."
            ),
        },
        "unit": "veces_uma",
        "label": "Tope del salario base de cotización (25 veces la UMA)",
        "official_id": "lss",
        "article": "28",
        "effective_from": DESINDEXACION_EN_VIGOR,
        "source": DOF,
        "source_url": URL["desindexacion"],
        "dof_date": "2016-01-27",
        "dof_codigo": "5423663",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Decreto de desindexación del salario mínimo, DOF 27-01-2016, "
            "transitorio TERCERO: 'A la fecha de entrada en vigor del "
            "presente Decreto, todas las menciones al salario mínimo como "
            "unidad de cuenta, índice, base, medida o referencia para "
            "determinar la cuantía de las obligaciones y supuestos previstos "
            "en las leyes federales ... se entenderán referidas a la Unidad "
            "de Medida y Actualización.' Transitorio PRIMERO: en vigor al día "
            "siguiente de su publicación, o sea el 28-01-2016. El art. 28 de "
            "la LSS no se reformó y sigue diciendo 'veinticinco veces el "
            "salario mínimo general que rija en el Distrito Federal'; lo que "
            "cambió es cómo se lee esa mención. El transitorio CUARTO dio un "
            "año a los congresos para ajustar la letra de las leyes, plazo "
            "que en la LSS no se ejerció — por eso el texto sigue igual y la "
            "procedencia de esta fila es el decreto, no la ley."
        ),
    },
    # -- Estudiantes: incorporación al régimen obligatorio, SIN ventana ----
    #
    # HP-5 pide 'seguro_facultativo_ventana_dias'. No hay ventana y no es
    # facultativo. Se publica lo que el decreto dice, con el kind nombrado por
    # la fuente, y la corrección se reporta al carril.
    {
        "kind": K.SEGURO_ESTUDIANTES_INCORPORACION,
        "value": {
            "hay_ventana": False,
            "motivo_sin_ventana": (
                "El Decreto no fija plazo alguno para la incorporación: la "
                "realiza el IMSS en términos de los acuerdos de su Consejo "
                "Técnico (art. 1 ¶2) y a través de convenios con las "
                "instituciones educativas (art. 4)."
            ),
            "regimen": "obligatorio",
            "es_seguro_facultativo": False,
            "nota_sobre_el_nombre": (
                "La LSS vigente desde el 01-07-1997 suprimió la figura del "
                "seguro facultativo; el nombre sobrevive del Acuerdo "
                "Presidencial de 1987 que este Decreto abrogó."
            ),
            "prestaciones": [
                "asistencia médico quirúrgica",
                "asistencia farmacéutica",
                "asistencia hospitalaria",
                "asistencia obstétrica",
            ],
            "prestaciones_excluidas": (
                "Sólo las prestaciones EN ESPECIE del Seguro de Enfermedades "
                "y Maternidad. No hay prestaciones en dinero, ni riesgos de "
                "trabajo, ni invalidez y vida, ni retiro."
            ),
            "beneficiarios": (
                "Únicamente la persona estudiante asegurada (art. 2 ¶2): no "
                "se extiende a familiares."
            ),
            "requisitos": {
                "tipo_de_estudios": ["medio_superior", "superior"],
                "tipo_de_institucion": "instituciones educativas del Estado",
                "sin_otra_proteccion": (
                    "No contar con la misma o similar protección por parte "
                    "del propio Instituto o de cualquier otra institución de "
                    "seguridad social."
                ),
            },
            "quien_inscribe": (
                "El IMSS, con la información que la persona estudiante o su "
                "institución educativa le proporcionen (arts. 5 y 6). NO es "
                "una obligación del centro de trabajo que recibe a una "
                "persona en prácticas o servicio social."
            ),
            "quien_paga": (
                "El Gobierno Federal cubre íntegramente las cuotas por "
                "conducto de la SHCP (art. 3). Ni la persona estudiante ni "
                "el centro receptor pagan."
            ),
            "prima": {
                "factor": "1.723%",
                "base": (
                    "Salario mínimo vigente en el Distrito Federal al momento "
                    "de la inscripción, elevado al año."
                ),
                "advertencia": (
                    "El art. 3 del Decreto se escribió en 1998 y no se ha "
                    "reformado; su base se lee hoy en UMA por el transitorio "
                    "TERCERO del decreto de desindexación, igual que el "
                    "art. 28 de la LSS."
                ),
            },
            "para_practicas_y_servicio_social": (
                "Esta cobertura NO deriva del vínculo formativo con el centro "
                "de trabajo: deriva de ser estudiante de una institución "
                "educativa del Estado. Un centro que recibe a una persona en "
                "prácticas o servicio social no la da de alta por este "
                "Decreto ni puede acreditarlo como cumplimiento propio."
            ),
        },
        "unit": "regla",
        "label": ("Estudiantes de media superior y superior: incorporación al IMSS"),
        "official_id": "lss",
        # El decreto se funda en LSS 12 fr. III, que es el artículo que
        # faculta al Ejecutivo a incorporar colectivos por decreto. Citar el
        # decreto solo dejaría la fila sin ancla en el corpus; citar sólo el
        # artículo escondería el instrumento que hace el trabajo.
        "article": "12-III",
        # Transitorio PRIMERO del Decreto: en vigor al día siguiente de su
        # publicación (14-09-1998).
        "effective_from": "1998-09-15",
        "source": DOF,
        "source_url": URL["estudiantes"],
        "dof_date": "1998-09-14",
        "dof_codigo": "4892913",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Decreto por el que se incorporan al régimen obligatorio del "
            "Seguro Social, por lo que corresponde a las prestaciones en "
            "especie del seguro de enfermedades y maternidad, a las personas "
            "que cursen estudios de los tipos medio superior y superior en "
            "instituciones educativas del Estado (DOF 14-09-1998). Art. 1: "
            "'Se incorporan al régimen obligatorio del seguro social ... a "
            "las personas que cursen estudios de los tipos medio superior y "
            "superior en instituciones educativas del Estado y que no cuenten "
            "con la misma o similar protección'. Se funda expresamente en los "
            "arts. 12 fracción III, 91 y 94 fracción I de la LSS. "
            "CORRECCIÓN DE CITA: ni LSS 13 fr. V (que son los trabajadores al "
            "servicio de las administraciones públicas) ni LSS 240 (seguro de "
            "salud para la FAMILIA) tienen que ver con estudiantes; la "
            "palabra 'estudiante' no aparece en la LSS vigente. El decreto no "
            "fija ventana: por eso la regla se publica sin plazo y lo declara."
        ),
    },
    # -- JCF: la regla nueva, citando las Reglas de Operación 2026 ---------
    #
    # La fila de T-1c se cierra el 31-12-2025 (ver labor_seed_hcm) y ésta rige
    # desde el 01-01-2026, que es cuando las Reglas 2026 entran en vigor. La
    # serie queda contigua: ni traslape ni hueco.
    {
        "kind": K.JCF_VALIDACION_PERIODICIDAD_DIAS,
        "value": {
            "periodicidad": "mensual",
            "ventana": "ultima_semana_del_mes",
            "medio": "Plataforma Digital del Programa",
            "quien_evalua": "la Tutora o el Tutor designado por el Centro de Trabajo",
            "mutua": (
                "La evaluación es mutua: la persona aprendiz también evalúa "
                "mensualmente a su Tutora o Tutor (regla Décima Segunda, "
                "apartado A, fracción XIII)."
            ),
            # Lo que cambió de fondo respecto de las Reglas 2024, y que un
            # consumidor fail-closed necesita saber para no exigir de más.
            "es_obligacion_del_centro_de_trabajo": False,
            "cambio_frente_a_2024": (
                "Las Reglas 2024 obligaban al Centro de Trabajo a 'verificar "
                "que cada Tutora o Tutor designado evalúe mensualmente' "
                "(obligaciones del Centro de Trabajo, fr. X). Las Reglas 2026 "
                "NO traen esa fracción: sus XXIV obligaciones del Centro de "
                "Trabajo (regla Décima Segunda, apartado D) no mencionan la "
                "evaluación. En 2026 evaluar mensualmente es un DERECHO de la "
                "Tutora o Tutor (apartado E, fr. IV) y de la persona aprendiz "
                "(apartado A, fr. XIII), y la regla Décima apartado A) "
                "fracción V lo enuncia como 'podrá realizarse'."
            ),
            "efecto_de_no_validar": (
                "Las Reglas 2026 no atan el pago del Apoyo económico a la "
                "evaluación: el art. de Entrega (regla Décima, apartado A, "
                "fracción VI) lo condiciona a que la Capacitación se realice "
                "conforme al Plan de Actividades y al cumplimiento de las "
                "Reglas. No existe cláusula de 'afirmativa ficta' — la frase "
                "no aparece en el documento de 2026."
            ),
        },
        "unit": "ciclo_mensual",
        "label": "JCF: periodicidad de la evaluación de la persona aprendiz",
        # Lo que HP-0d pide y T-1c no pudo dar: la fila ya tiene identificador
        # en el corpus, así que un consumidor puede seguirla hasta el texto.
        "official_id": "jcf-reglas-2026",
        "article": (
            "Reglas de Operación JCF 2026, regla Décima apartado A) fracción V"
        ),
        # Las Reglas 2026 rigen del 1 de enero de 2026 (son del ejercicio
        # fiscal 2026; el catálogo del corpus declara valid_from 2026-01-01).
        "effective_from": "2026-01-01",
        "source": STPS,
        "source_url": URL["jcf2026"],
        "dof_date": "2025-12-31",
        "dof_codigo": "5777674",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "REGLAS de Operación del Programa Jóvenes Construyendo el Futuro "
            "para el ejercicio fiscal 2026, DOF 31-12-2025 (codigo 5777674), "
            "en el corpus de Tezca como official_id 'jcf-reglas-2026'. Regla "
            "Décima, apartado A) 'De las y los Aprendices', fracción V "
            "'Evaluación de Tutora o Tutor y Evaluación de Aprendices': 'La "
            "evaluación tiene como finalidad conocer el desempeño de las y "
            "los Beneficiarios y las y los Tutores. Podrá realizarse "
            "mutuamente entre las y los Beneficiarios y las y los Tutores "
            "durante la última semana de cada mes, a través de la Plataforma "
            "Digital.' Estas Reglas ABROGAN las de 2024 (codigo 5746424) que "
            "T-1c había citado. Al leerlas cambió el fondo: la obligación del "
            "Centro de Trabajo de verificar la evaluación mensual (fr. X de "
            "2024) desapareció, y no hay afirmativa ficta."
        ),
    },
]
