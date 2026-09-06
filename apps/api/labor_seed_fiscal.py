"""Reglas de retención, costos de regularización y umbrales — seed T-1b.

Segunda mitad de ``labor_seed_data``, separada por la compuerta de tamaño del
repo (``scripts/utils/audit_file_sizes.py``, 800 líneas). El corte no es
arbitrario: aquí viven las reglas cuya fuente **no** es la ley laboral sino la
fiscal y las normas oficiales —LISR, LIVA, RLIVA, CFF, LIF, NOM-035, Acuerdo
REPSE—, y son también las que dependen de las dimensiones
(``payer_legal_form`` × ``provider_regime`` × ``service``).

``REGLAS`` sigue siendo una sola lista: se arma en ``labor_seed_data``, que
importa ``REGLAS_FISCALES`` de aquí. Ningún consumidor cambia de import.

Las fuentes y la regla de procedencia son las mismas que documenta
``labor_seed_data``; los huecos, los de ``docs/labor/reglas.md``.
"""

from apps.api.fiscal_models import Provenance
from apps.api.labor_models import LaborRule

CAMARA = "Cámara de Diputados, LeyesBiblio (texto vigente)"
DOF = "Diario Oficial de la Federación"

URL = {
    "lisr": "https://www.diputados.gob.mx/LeyesBiblio/doc/LISR.doc",
    "rliva": "https://www.diputados.gob.mx/LeyesBiblio/regley/Reg_LIVA_250914.doc",
    "cff": "https://www.diputados.gob.mx/LeyesBiblio/doc/CFF.doc",
    "lft": "https://www.diputados.gob.mx/LeyesBiblio/doc/LFT.doc",
    "lif2026": "https://www.diputados.gob.mx/LeyesBiblio/doc/LIF_2026.doc",
    "nom035": "https://dof.gob.mx/nota_detalle.php?codigo=5541828&fecha=23/10/2018",
    "nom037": "https://dof.gob.mx/nota_detalle.php?codigo=5691672&fecha=08/06/2023",
    "repse": "https://dof.gob.mx/nota_detalle.php?codigo=5619148&fecha=24/05/2021",
}

K = LaborRule.Kind
PF = LaborRule.PayerLegalForm

REGLAS_FISCALES = [
    # -- Retenciones sobre honorarios --------------------------------------
    # Tres filas simultáneas del mismo kind, distinguidas por las dimensiones:
    # la respuesta correcta depende de quién paga y bajo qué régimen cobra.
    {
        "kind": K.RETENCION_ISR_HONORARIOS_PCT,
        "value": 10,
        "unit": "percent",
        "label": "Retención de ISR: persona moral a persona física con servicios profesionales",
        "official_id": "lisr",
        "article": "106",
        "effective_from": "2014-01-01",
        "payer_legal_form": PF.PERSONA_MORAL,
        "provider_regime": "612",
        "service": "servicios_profesionales",
        "source": CAMARA,
        "source_url": URL["lisr"],
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 106, penúltimo párrafo: 'la tasa del 10% sobre el monto de "
            "los pagos que les efectúen, sin deducción alguna'. Sólo cuando el "
            "pagador es persona moral. La LISR vigente rige desde el "
            "1 de enero de 2014."
        ),
    },
    {
        "kind": K.RETENCION_ISR_HONORARIOS_PCT,
        "value": 1.25,
        "unit": "percent",
        "label": "Retención de ISR: persona moral a persona física en RESICO",
        "official_id": "lisr",
        "article": "113-J",
        "effective_from": "2022-01-01",
        "payer_legal_form": PF.PERSONA_MORAL,
        "provider_regime": "626",
        "source": CAMARA,
        "source_url": URL["lisr"],
        "dof_date": "2021-11-12",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 113-J: 1.25 % sobre los pagos, sin considerar el IVA, a "
            "enterar a más tardar el día 17 del mes siguiente. Artículo "
            "adicionado el 12-11-2021, en vigor desde el ejercicio 2022."
        ),
    },
    {
        "kind": K.RETENCION_ISR_HONORARIOS_PCT,
        "value": 0,
        "unit": "percent",
        "label": "Retención de ISR: persona física pagadora — no hay obligación de retener",
        "official_id": "lisr",
        "article": "106",
        "effective_from": "2014-01-01",
        "payer_legal_form": PF.PERSONA_FISICA,
        "source": CAMARA,
        "source_url": URL["lisr"],
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "El art. 106 impone la retención a 'las personas morales'. Un "
            "pagador persona física no retiene. Se publica el cero de forma "
            "explícita para que HCM no lo confunda con 'la regla no está' y "
            "retenga 'por si acaso'."
        ),
    },
    {
        "kind": K.RETENCION_IVA_HONORARIOS_FRACCION,
        "value": {"numerador": 2, "denominador": 3, "decimal": "0.6667"},
        "unit": "fraccion_del_iva_trasladado",
        "label": "Retención de IVA: dos terceras partes del impuesto trasladado",
        "official_id": "rliva",
        "article": "3",
        "effective_from": "2006-12-05",
        "payer_legal_form": PF.PERSONA_MORAL,
        "service": "servicios_profesionales",
        "source": CAMARA,
        "source_url": URL["rliva"],
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "RLIVA art. 3 fr. I: la retención se hace por las dos terceras "
            "partes del impuesto trasladado y efectivamente pagado, cuando lo "
            "traslade una persona física por servicios personales "
            "independientes, comisión, o uso o goce temporal de bienes. La "
            "obligación de retener nace del art. 1o.-A fr. II inciso a) de la "
            "LIVA. El Reglamento entró en vigor al día siguiente de su "
            "publicación (DOF 04-12-2006)."
        ),
    },
    {
        "kind": K.RETENCION_IVA_HONORARIOS_FRACCION,
        "value": {"porcentaje": 4, "base": "valor_de_la_contraprestacion"},
        "unit": "percent",
        "label": "Retención de IVA: autotransporte terrestre de bienes",
        "official_id": "rliva",
        "article": "3",
        "effective_from": "2006-12-05",
        "payer_legal_form": PF.PERSONA_MORAL,
        "service": "autotransporte_terrestre_bienes",
        "source": CAMARA,
        "source_url": URL["rliva"],
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "RLIVA art. 3 fr. II: 4 % del valor de la contraprestación "
            "efectivamente pagada. Se distingue por 'service' porque la base "
            "no es el impuesto trasladado sino la contraprestación."
        ),
    },
    {
        "kind": K.RESICO_TOPE_ANUAL,
        "value": 3500000,
        "unit": "MXN",
        "label": "Tope anual de ingresos para el Régimen Simplificado de Confianza",
        "official_id": "lisr",
        "article": "113-E",
        "effective_from": "2022-01-01",
        "source": CAMARA,
        "source_url": URL["lisr"],
        "dof_date": "2021-11-12",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 113-E: 'no hubieran excedido de la cantidad de tres millones "
            "quinientos mil pesos' en el ejercicio inmediato anterior. El "
            "importe está en el texto de la ley y no se actualiza por INPC, "
            "así que no hay una serie anual que seguir."
        ),
    },
    # -- Costos de regularización ------------------------------------------
    {
        "kind": K.RECARGOS_TASA_MENSUAL,
        "value": {
            "tasa_mensual": "2.07",
            "derivacion": "1.38 x 1.5",
            "base_lif": "1.38",
            "tasa_prorroga_mensual": "1.38",
            "parcialidades": {
                "hasta_12_meses": "1.42",
                "de_13_a_24_meses": "1.63",
                "mas_de_24_meses_o_diferido": "1.97",
            },
        },
        "unit": "percent_mensual",
        "label": "Recargos por mora, ejercicio 2026",
        "official_id": "cff",
        "article": "21",
        "effective_from": "2026-01-01",
        "effective_to": "2026-12-31",
        "source": CAMARA,
        "source_url": URL["lif2026"],
        "dof_date": "2025-11-07",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "CFF art. 21: la tasa de recargos por mora es la que fije "
            "anualmente el Congreso 'incrementada en 50%', considerada hasta "
            "la centésima. La LIF 2026 (DOF 07-11-2025) art. 11 fr. I fija "
            "1.38 % mensual de prórroga; 1.38 x 1.5 = 2.07 % mensual de mora. "
            "Las tasas de parcialidades del art. 11 fr. II ya incluyen la "
            "actualización y NO se multiplican por 1.5. La vigencia se cierra "
            "el 31-12-2026 porque la LIF es anual: sin LIF 2027 leída, el "
            "feed falla en claro en lugar de arrastrar la tasa."
        ),
    },
    {
        "kind": K.ACTUALIZACION_FACTOR,
        "value": {
            "formula": "INPC(mes_anterior_al_mas_reciente) / INPC(mes_anterior_al_mas_antiguo)",
            "piso": 1,
            "redondeo": "hasta_diezmilesimo",
            "no_se_actualiza_por_fracciones_de_mes": True,
            "si_no_hay_inpc_publicado": "se_aplica_el_ultimo_indice_mensual_publicado",
        },
        "unit": "formula",
        "label": "Factor de actualización de contribuciones",
        "official_id": "cff",
        "article": "17-A",
        "effective_from": "1982-01-01",
        "source": CAMARA,
        "source_url": URL["cff"],
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 17-A: el factor es el cociente de dos INPC; cuando resulta "
            "menor a 1 se toma 1. Se publica la FÓRMULA, no un número: la "
            "serie mensual del INPC es de INEGI y no se leyó en este carril "
            "(hueco declarado). Un consumidor que necesite el factor debe "
            "traer los dos INPC."
        ),
    },
    # -- REPSE, teletrabajo, NOM-035 ---------------------------------------
    {
        "kind": K.REPSE_OBLIGATORIO_CONDICIONES,
        "value": {
            "prohibido": (
                "La subcontratación de personal —proporcionar o poner a "
                "disposición trabajadores propios en beneficio de otra."
            ),
            "permitido_con_registro": (
                "Servicios especializados u obras especializadas que no formen "
                "parte del objeto social ni de la actividad económica "
                "preponderante de la beneficiaria."
            ),
            "condiciones": [
                "El contratista debe estar registrado en el padrón público de la STPS (LFT 15).",
                "El contrato debe constar por escrito, con el objeto y el número aproximado de trabajadores (LFT 14).",
                "Quien subcontrate con una contratista que incumpla con sus trabajadores es responsable solidario (LFT 14).",
                "Sin el registro, el pago no es deducible ni acreditable (CFF 15-D, al que remite LISR 28 fr. XXXIII).",
            ],
            "articulos_derogados": {
                "lft": ["15-A", "15-B", "15-C", "15-D"],
                "derogados_dof": "2021-04-23",
                "nota": (
                    "La base del REPSE es el art. 15 de la LFT, no los "
                    "derogados 15-A a 15-D."
                ),
            },
        },
        "unit": "texto_estructurado",
        "label": "REPSE: cuándo es obligatorio el registro",
        "official_id": "lft",
        "article": "15",
        "effective_from": "2021-04-24",
        "source": CAMARA,
        "source_url": URL["lft"],
        "dof_date": "2021-04-23",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Arts. 12, 13, 14 y 15 reformados por el decreto del 23-04-2021, "
            "en vigor al día siguiente de su publicación."
        ),
    },
    {
        "kind": K.REPSE_VIGENCIA_ANIOS,
        "value": {
            "vigencia_anios": 3,
            "renovacion_ventana_meses_antes": 3,
        },
        "unit": "anios",
        "label": "REPSE: vigencia del registro y ventana de renovación",
        "official_id": "lft",
        "article": "15",
        "effective_from": "2021-05-25",
        "source": DOF,
        "source_url": URL["repse"],
        "dof_date": "2021-05-24",
        "dof_codigo": "5619148",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "LFT art. 15, segundo párrafo: el registro se renueva cada tres "
            "años. Acuerdo REPSE, artículos DÉCIMO TERCERO (vigencia de tres "
            "años) y DÉCIMO SEXTO (el trámite de renovación se inicia dentro "
            "de los tres meses anteriores a que concluya la vigencia). El "
            "Acuerdo entró en vigor al día siguiente de su publicación."
        ),
    },
    {
        "kind": K.TELETRABAJO_UMBRAL_PCT,
        "value": 40,
        "unit": "percent",
        "label": "Teletrabajo: proporción del tiempo en el domicilio que activa el capítulo",
        "official_id": "lft",
        "article": "330-A",
        "effective_from": "2021-01-12",
        "source": CAMARA,
        "source_url": URL["lft"],
        "dof_date": "2021-01-11",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 330-A, cuarto párrafo: se rigen por el capítulo las "
            "relaciones que se desarrollen 'más del cuarenta por ciento del "
            "tiempo' en el domicilio de la persona trabajadora o en el que "
            "ésta elija. El quinto párrafo excluye lo ocasional o esporádico. "
            "Artículo adicionado el 11-01-2021, en vigor al día siguiente."
        ),
    },
    {
        "kind": K.NOM035_UMBRAL_PERSONAS,
        "value": {
            "tramos": [
                {
                    "hasta": 15,
                    "etiqueta": "Centros de trabajo de hasta 15 personas",
                    "numerales": ["5.1", "5.2", "5.4-5.8", "7.1 inciso a)", "8"],
                    "identificacion_factores": False,
                    "evaluacion_entorno": False,
                },
                {
                    "desde": 16,
                    "hasta": 50,
                    "etiqueta": "Centros de trabajo de 16 a 50 personas",
                    "numerales": [
                        "5.1",
                        "5.2",
                        "5.4-5.8",
                        "7.1 inciso a)",
                        "7.2",
                        "7.4-7.9",
                        "8",
                    ],
                    "identificacion_factores": True,
                    "evaluacion_entorno": False,
                    "alcance": "todas_las_personas_trabajadoras",
                },
                {
                    "desde": 51,
                    "etiqueta": "Centros de trabajo de más de 50 personas",
                    "numerales": [
                        "5.1",
                        "5.3-5.8",
                        "7.1 inciso b)",
                        "7.2-7.9",
                        "8",
                    ],
                    "identificacion_factores": True,
                    "evaluacion_entorno": True,
                    "alcance": "muestra_representativa_guia_III",
                },
            ]
        },
        "unit": "tabla",
        "label": "NOM-035: obligaciones por tamaño del centro de trabajo",
        "official_id": "nom_NOM-035-STPS-2018",
        "article": "4",
        "effective_from": "2019-10-23",
        # Cerrada por T-1f. La fila se queda —append-only: lo publicado no se
        # borra, se sucede— pero deja de ser la respuesta vigente el día en que
        # entra su corrección. Ver la fila siguiente para el porqué.
        "effective_to": "2026-09-05",
        "source": DOF,
        "source_url": URL["nom035"],
        "dof_date": "2018-10-23",
        "dof_codigo": "5541828",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "SUPERADA POR CORRECCIÓN (T-1f). Citaba el campo de aplicación "
            "como «numeral 4» y listaba para el tramo de hasta 15 personas "
            "numerales que la NOM no le impone. La lectura primaria del DOF "
            "5541828 dice numeral 2. Se conserva por append-only y se cierra "
            "el 2026-09-05; la fila vigente es la que sigue."
        ),
    },
    {
        # Corrección de T-1f contra el texto íntegro del DOF 5541828
        # (`nota_to_doc.php?codnota=5541828`, convertido con textutil). Dos
        # errores de transcripción, ninguno detectable por una prueba de
        # «existe la fila»:
        #
        #   1. El campo de aplicación es el **numeral 2**, no el 4. En la
        #      NOM-035 el 4 son las Definiciones. Un consumidor que fuera a
        #      citar el fundamento habría citado el numeral equivocado.
        #   2. El tramo de hasta 15 personas: la NOM le impone «5.1, 5.4, 5.5,
        #      5.7, 8.1 y 8.2», no «5.1, 5.2, 5.4-5.8, 7.1 inciso a), 8». La
        #      fila anterior le exigía de más —el 5.2 y el 7.1 no le tocan— y
        #      HCM habría pedido evidencia que la norma no requiere al centro
        #      de trabajo más pequeño, que es justo el que menos margen tiene.
        #
        # El texto íntegro del numeral 2 se publica además como `LawArticle`
        # (`nom_NOM-035-STPS-2018` art. 2), así que esta tabla ya es
        # verificable contra su propia fuente dentro de Tezca.
        "kind": K.NOM035_UMBRAL_PERSONAS,
        "value": {
            "tramos": [
                {
                    "hasta": 15,
                    "etiqueta": "Centros de trabajo de hasta 15 personas",
                    "numerales": ["5.1", "5.4", "5.5", "5.7", "8.1", "8.2"],
                    "identificacion_factores": False,
                    "evaluacion_entorno": False,
                },
                {
                    "desde": 16,
                    "hasta": 50,
                    "etiqueta": "Centros de trabajo de 16 a 50 personas",
                    "numerales": [
                        "5.1",
                        "5.2",
                        "5.4-5.8",
                        "7.1 inciso a)",
                        "7.2",
                        "7.4-7.9",
                        "8",
                    ],
                    "identificacion_factores": True,
                    "evaluacion_entorno": False,
                    "alcance": "todas_las_personas_trabajadoras",
                },
                {
                    "desde": 51,
                    "etiqueta": "Centros de trabajo de más de 50 personas",
                    "numerales": [
                        "5.1",
                        "5.3-5.8",
                        "7.1 inciso b)",
                        "7.2-7.9",
                        "8",
                    ],
                    "identificacion_factores": True,
                    "evaluacion_entorno": True,
                    "alcance": "muestra_representativa_guia_III",
                },
            ],
            "equivalencia_nmx_r_025": {
                "certificado": "NMX-R-025-SCFI-2015 vigente",
                "da_por_cumplidos": [
                    "5.1 inciso b)",
                    "8.1 inciso b)",
                    "8.2 incisos a) subinciso 2), e) y g)",
                    "5.7 inciso d)",
                ],
            },
        },
        "unit": "tabla",
        "label": "NOM-035: obligaciones por tamaño del centro de trabajo",
        "official_id": "nom_NOM-035-STPS-2018",
        "article": "2",
        "effective_from": "2026-09-06",
        "source": DOF,
        "source_url": URL["nom035"],
        "dof_date": "2018-10-23",
        "dof_codigo": "5541828",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Numeral 2 (campo de aplicación) de la NOM-035-STPS-2018, leído "
            "íntegro del DOF 5541828. La NOM rige desde 2019-10-23 (primer "
            "bloque) y 2020-10-23 (identificación y evaluación del entorno); "
            "esta fila se fecha en 2026-09-06 porque es la fecha de la "
            "CORRECCIÓN, no de la norma: adelantarla a 2019 reescribiría lo "
            "que Tezca respondió entre 2019 y hoy, y el feed es append-only. "
            "El texto del numeral se sirve en "
            "GET /api/v1/laws/nom_NOM-035-STPS-2018/articles/2/vigente/."
        ),
    },
    {
        # El hueco `nom037_si_aplica` del HCM (HP-0c) decía que Tezca no
        # publica los numerales de la NOM-037 «porque `LawArticle` no modela
        # numerales sin forzarlo». Eso era cierto cuando `article` medía 32
        # caracteres; T-1e lo llevó a 200 exactamente para poder citar
        # documentos que no se numeran por artículos. Con esa columna, el
        # numeral 2 de la NOM-037 entra al corpus como cualquier artículo, y
        # esta regla dice —en estructura— lo que ese numeral dice en prosa.
        "kind": K.NOM037_APLICABILIDAD,
        "value": {
            "aplica_si": "existe_al_menos_una_persona_en_teletrabajo",
            "umbral_personas": None,
            "ambito": "toda_la_republica_mexicana",
            "umbral_teletrabajo_en": "teletrabajo_umbral_pct",
            "nota": (
                "La NOM-037 no tiene umbral por tamaño del centro de trabajo: "
                "aplica a todo centro que cuente con al menos una persona "
                "trabajadora bajo la modalidad de teletrabajo. Quién cuenta "
                "como tal lo fija la LFT 330-A (más del 40 % del tiempo), que "
                "se sirve en el kind `teletrabajo_umbral_pct`."
            ),
        },
        "unit": "condicion",
        "label": "NOM-037: cuándo aplica la norma de teletrabajo",
        "official_id": "nom_NOM-037-STPS-2023",
        "article": "2",
        # 180 días naturales tras la publicación (TRANSITORIO PRIMERO):
        # 08-06-2023 + 180 = 05-12-2023.
        "effective_from": "2023-12-05",
        "source": DOF,
        "source_url": URL["nom037"],
        "dof_date": "2023-06-08",
        "dof_codigo": "5691672",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Numeral 2 (campo de aplicación) de la NOM-037-STPS-2023, leído "
            "íntegro del DOF 5691672. Entró en vigor a los 180 días naturales "
            "de su publicación (TRANSITORIO PRIMERO). El texto del numeral se "
            "sirve en "
            "GET /api/v1/laws/nom_NOM-037-STPS-2023/articles/2/vigente/."
        ),
    },
    # -- Recaracterización: la ley por un lado, la doctrina por el otro ----
    #
    # T-1f parte en dos lo que T-1b publicó junto. La fila única era honesta
    # —declaraba en su propio `value` que los indicios no eran de ley— pero
    # tenía un efecto que la honestidad no arreglaba: al ser toda la fila
    # `seed-unverified`, el consumidor fail-closed la descartaba **entera**, y
    # con ella los tres elementos que el art. 20 sí enuncia palabra por
    # palabra. HCM se quedaba sin poder afirmar la definición legal de
    # relación de trabajo, que es justo lo que necesita para avisar.
    {
        "kind": K.RELACION_TRABAJO_ELEMENTOS,
        "value": {
            "elementos": [
                "Prestación de un trabajo personal.",
                "Subordinación a otra persona.",
                "Pago de un salario.",
            ],
            "definicion": (
                "Se entiende por relación de trabajo, cualquiera que sea el "
                "acto que le dé origen, la prestación de un trabajo personal "
                "subordinado a una persona, mediante el pago de un salario."
            ),
            "efecto": (
                "La prestación del trabajo y el contrato celebrado producen "
                "los mismos efectos (art. 20, tercer párrafo): la relación "
                "existe por los hechos, con independencia del nombre del acto."
            ),
        },
        "unit": "lista",
        "label": "Elementos de la relación de trabajo (LFT 20)",
        "official_id": "lft",
        "article": "20",
        "effective_from": "1970-04-01",
        "source": CAMARA,
        "source_url": URL["lft"],
        # `published`: los tres elementos y la frase de los «mismos efectos»
        # se transcribieron del texto vigente del art. 20 que publica la
        # Cámara — el mismo que este repo ya sirve en
        # `GET /api/v1/laws/lft/articles/20/vigente/`.
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 20 LFT, párrafos primero y tercero. El artículo NO enumera "
            "indicios: define la relación por tres elementos. Los indicios "
            "orientativos viven en `recaracterizacion_indicios`, aparte y sin "
            "verificar, precisamente para que esta fila pueda afirmarse."
        ),
    },
    {
        "kind": K.RECARACTERIZACION_INDICIOS,
        "value": {
            "indicios_orientativos": [
                "Horario fijo impuesto por quien paga.",
                "Instrucciones sobre cómo y cuándo ejecutar el trabajo.",
                "Herramientas, equipo y lugar provistos por quien paga.",
                "Exclusividad de hecho o de derecho.",
                "Pagos periódicos de monto uniforme, no por entregable.",
                "Integración a la estructura y a los procesos del centro.",
                "Supervisión y régimen disciplinario aplicables a la persona.",
            ],
            "elementos_de_ley_en": "relacion_trabajo_elementos",
            "advertencia": (
                "Esta lista NO está en la LFT y no se pudo citar con registro "
                "de jurisprudencia. Es orientación para levantar un aviso, "
                "nunca base para recaracterizar: sólo un dictamen legal "
                "firmado cambia la lectura de un vínculo. Los elementos que "
                "sí son de ley se piden con kind "
                "`relacion_trabajo_elementos`, que es `published`."
            ),
        },
        "unit": "lista",
        "label": "Indicios de relación laboral (orientativos, no de ley)",
        "official_id": "lft",
        "article": "20",
        "effective_from": "1970-04-01",
        "source": CAMARA,
        "source_url": URL["lft"],
        # Sigue siendo seed-unverified, y ahora sin arrastrar a la ley con
        # ella: lo que no se puede citar no se afirma, y lo que sí, sí.
        "provenance": Provenance.SEED_UNVERIFIED,
        "notes": (
            "HUECO DECLARADO. Criterios jurisprudenciales que no se "
            "localizaron con registro verificable de la SCJN en este carril. "
            "Se sirve como seed-unverified para que HCM pueda mostrarlos al "
            "humano que decide, y para que ningún cálculo los use. Para "
            "cerrarlo hace falta la tesis o jurisprudencia con número de "
            "registro del Semanario Judicial de la Federación."
        ),
    },
]
