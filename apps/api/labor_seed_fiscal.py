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
        "source": DOF,
        "source_url": URL["nom035"],
        "dof_date": "2018-10-23",
        "dof_codigo": "5541828",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Numeral 4 (campo de aplicación) de la NOM-035-STPS-2018. Las "
            "disposiciones del primer bloque entraron en vigor al año de la "
            "publicación (23-10-2019) y las de identificación, evaluación del "
            "entorno y exámenes médicos a los dos años (23-10-2020); esta fila "
            "se fecha en la primera. El texto íntegro de la NOM no está en el "
            "corpus: se cita por numeral, no por artículo (hueco declarado)."
        ),
    },
    # -- Recaracterización: lo único que NO se pudo verificar --------------
    {
        "kind": K.RECARACTERIZACION_INDICIOS,
        "value": {
            "elementos_de_ley": [
                "Prestación de un trabajo personal.",
                "Subordinación a otra persona.",
                "Pago de un salario.",
            ],
            "fuente_de_los_elementos": "LFT art. 20, primer párrafo",
            "indicios_orientativos": [
                "Horario fijo impuesto por quien paga.",
                "Instrucciones sobre cómo y cuándo ejecutar el trabajo.",
                "Herramientas, equipo y lugar provistos por quien paga.",
                "Exclusividad de hecho o de derecho.",
                "Pagos periódicos de monto uniforme, no por entregable.",
                "Integración a la estructura y a los procesos del centro.",
                "Supervisión y régimen disciplinario aplicables a la persona.",
            ],
            "advertencia": (
                "Los tres elementos son de ley; la lista de indicios NO está "
                "en la LFT ni se pudo citar con registro de jurisprudencia en "
                "este carril. Es orientación para levantar un aviso, nunca "
                "base para recaracterizar: sólo un dictamen legal firmado "
                "cambia la lectura de un vínculo."
            ),
        },
        "unit": "lista",
        "label": "Indicios de relación laboral (aviso, no dictamen)",
        "official_id": "lft",
        "article": "20",
        "effective_from": "1970-04-01",
        "source": CAMARA,
        "source_url": URL["lft"],
        # Deliberadamente seed-unverified: los tres elementos sí son del art.
        # 20, pero la lista de indicios es doctrina y jurisprudencia que este
        # carril no pudo citar con registro. El consumidor la descarta para
        # calcular, que es exactamente lo correcto: un aviso se levanta con
        # criterio humano, no con una lista que Tezca no puede defender.
        "provenance": Provenance.SEED_UNVERIFIED,
        "notes": (
            "HUECO DECLARADO. El art. 20 define la relación de trabajo por "
            "tres elementos y no enumera indicios; la lista proviene de "
            "criterios jurisprudenciales que no se localizaron con registro "
            "verificable de la SCJN en este carril. Se publica como "
            "seed-unverified para que HCM pueda mostrarla al humano que "
            "decide, y para que ningún cálculo la use."
        ),
    },
]
