"""Reglas laborales estructuradas — el seed leído de fuente primaria (T-1b).

Cada regla trae la lectura del artículo de la que salió. Los textos íntegros
de esos artículos están en ``data/labor/articulos_vigentes.json`` y se sirven
por ``/api/v1/laws/<id>/articles/<art>/vigente/``, así que un consumidor que
dude de un número puede leer la prosa que lo sostiene sin salir de Tezca.

Regla del carril: sin lectura primaria no se publica. Lo que no se pudo leer
de un documento oficial queda ``seed-unverified`` (el consumidor lo descarta)
y se lista como hueco en ``docs/labor/reglas.md``.

Fuentes usadas, todas verificadas en este carril:

* Cámara de Diputados, LeyesBiblio, texto vigente (.doc): LFT 14-05-2026,
  LSS 15-01-2026, LISR 01-04-2024, LIVA 12-11-2021, RLIVA 25-09-2014,
  CFF 09-04-2026, LIF 2026 (DOF 07-11-2025).
* DOF ``nota_to_doc.php``: decreto de reducción de la jornada laboral
  (``codigo`` 5786537, 01-05-2026), NOM-035-STPS-2018 (``codigo`` 5541828,
  23-10-2018), Acuerdo REPSE (``codigo`` 5619148, 24-05-2021).

Este módulo cubre la mitad **laboral** del seed (LFT y LSS: jornada, prueba,
prestaciones, alta al IMSS). La mitad **fiscal y de normas oficiales** —
retenciones, RESICO, recargos, actualización, REPSE, teletrabajo, NOM-035 y la
lista de recaracterización — vive en ``labor_seed_fiscal``, separada por la
compuerta de tamaño del repo. ``REGLAS`` las une: es la única lista que un
consumidor importa.
"""

from apps.api.fiscal_models import Provenance
from apps.api.labor_models import LaborRule
from apps.api.labor_seed_fiscal import REGLAS_FISCALES

# Fuentes, para no repetir la cadena en cada fila.
CAMARA = "Cámara de Diputados, LeyesBiblio (texto vigente)"
DOF = "Diario Oficial de la Federación"

URL = {
    "lft": "https://www.diputados.gob.mx/LeyesBiblio/doc/LFT.doc",
    "lss": "https://www.diputados.gob.mx/LeyesBiblio/doc/LSS.doc",
    "jornada2026": "https://dof.gob.mx/nota_detalle.php?codigo=5786537&fecha=01/05/2026",
}

K = LaborRule.Kind
PF = LaborRule.PayerLegalForm

# ---------------------------------------------------------------------------
# La jornada, escalón por escalón.
#
# El artículo 59 reformado dice "cuarenta horas semanales", pero el
# transitorio SEGUNDO del mismo decreto escalona la reducción a partir del
# 1 de enero de cada año, y el CUARTO hace lo propio con el tiempo
# extraordinario del artículo 66. Publicar el 40 como un valor único haría
# que HCM calculara hoy con ocho horas de menos: por eso una fila por año.
#
# Antes del decreto la jornada eran 48 horas (art. 59 en su texto de 1970) y
# el tiempo extra tres horas diarias sin exceder tres veces por semana
# (art. 66 anterior); esa vigencia se cierra el 31-12-2025 porque el
# transitorio segundo fija 48 para 2026 y el decreto entró en vigor el
# 1 de mayo de 2026 — el escalón de 2026 coincide con el texto anterior, así
# que la serie no tiene hueco.
# ---------------------------------------------------------------------------
JORNADA_SEMANAL = [
    # (año, horas)
    (2026, 48),
    (2027, 46),
    (2028, 44),
    (2029, 42),
    (2030, 40),
]

TIEMPO_EXTRA_SEMANAL = [
    (2026, 9),
    (2027, 9),
    (2028, 10),
    (2029, 11),
    (2030, 12),
]


def _jornada_rows():
    """Las vigencias escalonadas de la jornada y del tiempo extraordinario."""
    filas = []
    for indice, (anio, horas) in enumerate(JORNADA_SEMANAL):
        siguiente = (
            JORNADA_SEMANAL[indice + 1][0]
            if indice + 1 < len(JORNADA_SEMANAL)
            else None
        )
        filas.append(
            {
                "kind": K.JORNADA_SEMANAL_HORAS_MAX,
                "value": horas,
                "unit": "horas/semana",
                "label": f"Jornada ordinaria semanal máxima en {anio}",
                "official_id": "lft",
                "article": "59",
                "effective_from": f"{anio}-01-01",
                # El último escalón (2030) ya no se cierra: es el régimen final.
                "effective_to": f"{siguiente - 1}-12-31" if siguiente else None,
                "source": DOF,
                "source_url": URL["jornada2026"],
                "dof_date": "2026-05-01",
                "dof_codigo": "5786537",
                "provenance": Provenance.PUBLISHED,
                "notes": (
                    "Transitorio segundo del decreto: la jornada del art. 59 "
                    "se alcanza de manera gradual, a partir del 1 de enero de "
                    "cada año. El texto del artículo dice 'cuarenta horas' "
                    "desde el 01-05-2026, pero ese número no rige hasta 2030."
                ),
            }
        )
    for indice, (anio, horas) in enumerate(TIEMPO_EXTRA_SEMANAL):
        siguiente = (
            TIEMPO_EXTRA_SEMANAL[indice + 1][0]
            if indice + 1 < len(TIEMPO_EXTRA_SEMANAL)
            else None
        )
        filas.append(
            {
                "kind": K.TIEMPO_EXTRA_SEMANAL_HORAS_MAX,
                "value": horas,
                "unit": "horas/semana",
                "label": f"Tiempo extraordinario semanal máximo en {anio}",
                "official_id": "lft",
                "article": "66",
                "effective_from": f"{anio}-01-01",
                "effective_to": f"{siguiente - 1}-12-31" if siguiente else None,
                "source": DOF,
                "source_url": URL["jornada2026"],
                "dof_date": "2026-05-01",
                "dof_codigo": "5786537",
                "provenance": Provenance.PUBLISHED,
                "notes": (
                    "Transitorio cuarto del decreto. El art. 66 reformado fija "
                    "doce horas repartidas en hasta cuatro diarias por un "
                    "máximo de cuatro días; el tope anual es el del "
                    "transitorio. El art. 68 añade que la prolongación que "
                    "exceda el art. 66 no puede pasar de cuatro horas "
                    "semanales, se paga al 200 %, y ordinaria más "
                    "extraordinaria nunca supera doce horas diarias."
                ),
            }
        )
    return filas


_REGLAS_LABORALES = _jornada_rows() + [
    # -- Alta al IMSS y contrato ------------------------------------------
    {
        "kind": K.IMSS_ALTA_VENTANA,
        "value": 5,
        "unit": "dias_habiles",
        "label": "Plazo para inscribir a la persona trabajadora en el IMSS",
        "official_id": "lss",
        "article": "15",
        "effective_from": "2001-12-20",
        "source": CAMARA,
        "source_url": URL["lss"],
        "dof_date": "2001-12-20",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 15 fr. I: registrarse e inscribir a sus trabajadores, "
            "comunicar altas y bajas y las modificaciones de salario 'dentro "
            "de plazos no mayores de cinco días hábiles'. La fracción se "
            "reformó el 20-12-2001."
        ),
    },
    {
        "kind": K.CONTRATO_ESCRITO,
        "value": True,
        "unit": "boolean",
        "label": "Las condiciones de trabajo deben constar por escrito",
        "official_id": "lft",
        "article": "24",
        "effective_from": "1970-04-01",
        "source": CAMARA,
        "source_url": URL["lft"],
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 24: por escrito cuando no haya contrato colectivo aplicable, "
            "en dos ejemplares. La LFT no fija un plazo en días para "
            "firmarlo; el art. 25 enumera lo que debe contener y el art. 26 "
            "carga al patrón la falta de la formalidad. Por eso esta regla es "
            "booleana y no una ventana: HCM no debe inventar un plazo."
        ),
    },
    # -- Prueba y capacitación inicial -------------------------------------
    {
        "kind": K.PRUEBA_DIAS_MAX,
        "value": 30,
        "unit": "dias",
        "label": "Periodo de prueba (general)",
        "official_id": "lft",
        "article": "39-A",
        "effective_from": "2012-11-30",
        "source": CAMARA,
        "source_url": URL["lft"],
        "dof_date": "2012-11-30",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 39-A: sólo en relaciones por tiempo indeterminado o que "
            "excedan de ciento ochenta días; no podrá exceder de treinta días."
        ),
    },
    {
        "kind": K.PRUEBA_DIAS_MAX_DIRECCION,
        "value": 180,
        "unit": "dias",
        "label": "Periodo de prueba, puestos de dirección o técnicos especializados",
        "official_id": "lft",
        "article": "39-A",
        "effective_from": "2012-11-30",
        "source": CAMARA,
        "source_url": URL["lft"],
        "dof_date": "2012-11-30",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 39-A, segundo párrafo: hasta ciento ochenta días sólo para "
            "puestos de dirección, gerenciales, de administración general o "
            "labores técnicas o profesionales especializadas."
        ),
    },
    {
        "kind": K.CAPACITACION_MESES_MAX,
        "value": 3,
        "unit": "meses",
        "label": "Capacitación inicial (general)",
        "official_id": "lft",
        "article": "39-B",
        "effective_from": "2012-11-30",
        "source": CAMARA,
        "source_url": URL["lft"],
        "dof_date": "2012-11-30",
        "provenance": Provenance.PUBLISHED,
        "notes": "Art. 39-B, segundo párrafo: duración máxima de tres meses.",
    },
    {
        "kind": K.CAPACITACION_MESES_MAX_DIRECCION,
        "value": 6,
        "unit": "meses",
        "label": "Capacitación inicial, puestos de dirección o especializados",
        "official_id": "lft",
        "article": "39-B",
        "effective_from": "2012-11-30",
        "source": CAMARA,
        "source_url": URL["lft"],
        "dof_date": "2012-11-30",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 39-B: hasta seis meses sólo para puestos de dirección, "
            "gerenciales o que requieran conocimientos profesionales "
            "especializados. El art. 39-C exige que prueba y capacitación "
            "inicial consten por escrito con seguridad social garantizada; si "
            "no, la relación se entiende por tiempo indeterminado."
        ),
    },
    # -- Jornada diaria ----------------------------------------------------
    {
        "kind": K.JORNADA_DIURNA_HORAS_MAX,
        "value": 8,
        "unit": "horas/dia",
        "label": "Jornada diurna diaria máxima",
        "official_id": "lft",
        "article": "61",
        "effective_from": "2026-05-01",
        "source": DOF,
        "source_url": URL["jornada2026"],
        "dof_date": "2026-05-01",
        "dof_codigo": "5786537",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 61 reformado. El art. 60 define la jornada diurna entre las "
            "seis y las veinte horas. A diferencia de la semanal, la diaria "
            "no se escalona: rige desde la entrada en vigor del decreto."
        ),
    },
    {
        "kind": K.JORNADA_NOCTURNA_HORAS_MAX,
        "value": 7,
        "unit": "horas/dia",
        "label": "Jornada nocturna diaria máxima",
        "official_id": "lft",
        "article": "61",
        "effective_from": "2026-05-01",
        "source": DOF,
        "source_url": URL["jornada2026"],
        "dof_date": "2026-05-01",
        "dof_codigo": "5786537",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 61 reformado. El art. 60 define la nocturna entre las "
            "veinte y las seis horas."
        ),
    },
    {
        "kind": K.JORNADA_MIXTA_HORAS_MAX,
        "value": 7.5,
        "unit": "horas/dia",
        "label": "Jornada mixta diaria máxima",
        "official_id": "lft",
        "article": "61",
        "effective_from": "2026-05-01",
        "source": DOF,
        "source_url": URL["jornada2026"],
        "dof_date": "2026-05-01",
        "dof_codigo": "5786537",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 61 reformado: siete horas y media. El art. 60 advierte que "
            "si el periodo nocturno alcanza tres horas y media o más, la "
            "jornada se reputa nocturna."
        ),
    },
    # -- Semana reducida ---------------------------------------------------
    {
        "kind": K.SEMANA_REDUCIDA_PRORRATEO,
        "value": {
            "regla": "piso_salario_minimo",
            "descripcion": (
                "Con jornada o semana reducida la cotización se determina por "
                "unidad de tiempo, pero en ningún caso se reciben cuotas sobre "
                "un salario inferior al mínimo."
            ),
            "salario_diario": {
                "semanal": "remuneracion / 7",
                "quincenal": "remuneracion / 15",
                "mensual": "remuneracion / 30",
            },
            "piso": "salario_minimo_general_del_area",
        },
        "unit": "regla",
        "label": "Cotización con jornada o semana reducida",
        "official_id": "lss",
        "article": "29",
        "effective_from": "1997-07-01",
        "source": CAMARA,
        "source_url": URL["lss"],
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 29 fr. II (salario diario según el periodo de pago) y fr. "
            "III (jornadas reducidas: nunca por debajo del mínimo). NO es el "
            "art. 62, que trata recaídas por riesgos de trabajo. El art. 28 "
            "fija además el tope superior en veinticinco veces el salario "
            "mínimo. La LSS entró en vigor el 1 de julio de 1997."
        ),
    },
    # -- PTU ---------------------------------------------------------------
    {
        "kind": K.PTU_EVENTUALES_DIAS_MIN,
        "value": 60,
        "unit": "dias",
        "label": "Días mínimos trabajados para que un eventual reciba PTU",
        "official_id": "lft",
        "article": "127",
        "effective_from": "1970-04-01",
        "source": CAMARA,
        "source_url": URL["lft"],
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 127 fr. VII: los trabajadores eventuales participan cuando "
            "hayan trabajado sesenta días durante el año, por lo menos. La "
            "fracción no registra reformas."
        ),
    },
    {
        "kind": K.PTU_FECHA_LIMITE_DIAS,
        "value": 60,
        "unit": "dias",
        "label": "Días para repartir la PTU tras la fecha de pago del impuesto anual",
        "official_id": "lft",
        "article": "122",
        "effective_from": "1976-07-02",
        "source": CAMARA,
        "source_url": URL["lft"],
        "dof_date": "1976-07-02",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 122: dentro de los sesenta días siguientes a la fecha en que "
            "deba pagarse el impuesto anual, aun cuando esté en trámite "
            "objeción de los trabajadores."
        ),
    },
    # -- Aguinaldo, vacaciones, prima --------------------------------------
    {
        "kind": K.AGUINALDO_DIAS_MIN,
        "value": 15,
        "unit": "dias_de_salario",
        "label": "Aguinaldo mínimo",
        "official_id": "lft",
        "article": "87",
        "effective_from": "1970-04-01",
        "source": CAMARA,
        "source_url": URL["lft"],
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 87: equivalente a quince días de salario, por lo menos. "
            "Quien no cumplió el año recibe la parte proporcional (párrafo "
            "reformado el 31-12-1975)."
        ),
    },
    {
        "kind": K.AGUINALDO_FECHA_LIMITE,
        "value": {"mes": 12, "dia": 20, "criterio": "antes_de"},
        "unit": "fecha",
        "label": "Fecha límite para pagar el aguinaldo",
        "official_id": "lft",
        "article": "87",
        "effective_from": "1970-04-01",
        "source": CAMARA,
        "source_url": URL["lft"],
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 87: 'deberá pagarse antes del día veinte de diciembre'. "
            "Antes del 20, no el 20: el criterio es estricto."
        ),
    },
    {
        "kind": K.VACACIONES_DIAS_POR_ANIO,
        "value": {
            "tabla": [
                {"anio_servicio": 1, "dias": 12},
                {"anio_servicio": 2, "dias": 14},
                {"anio_servicio": 3, "dias": 16},
                {"anio_servicio": 4, "dias": 18},
                {"anio_servicio": 5, "dias": 20},
            ],
            "despues_del_quinto": {
                "regla": "dos_dias_por_cada_cinco_anios",
                "descripcion": (
                    "A partir del sexto año el periodo aumenta en dos días por "
                    "cada cinco de servicios."
                ),
            },
            "continuos_minimos": 12,
            "proporcional_discontinuos": True,
        },
        "unit": "tabla",
        "label": "Vacaciones por año de servicio",
        "official_id": "lft",
        "article": "76",
        "effective_from": "2023-01-01",
        "source": CAMARA,
        "source_url": URL["lft"],
        "dof_date": "2022-12-27",
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 76 reformado el 27-12-2022 ('vacaciones dignas'): doce días "
            "al primer año, más dos por cada año subsecuente hasta veinte; "
            "desde el sexto, dos por cada cinco de servicios. El art. 78 "
            "garantiza doce días continuos por lo menos. El art. 77 da "
            "proporción a discontinuos y de temporada, el 79 al que no cumple "
            "el año, y el 81 obliga a concederlas dentro de los seis meses "
            "siguientes al aniversario. La reforma entró en vigor el "
            "1 de enero de 2023."
        ),
    },
    {
        "kind": K.PRIMA_VACACIONAL_PCT_MIN,
        "value": 25,
        "unit": "percent",
        "label": "Prima vacacional mínima",
        "official_id": "lft",
        "article": "80",
        "effective_from": "1970-04-01",
        "source": CAMARA,
        "source_url": URL["lft"],
        "provenance": Provenance.PUBLISHED,
        "notes": (
            "Art. 80: prima no menor de veinticinco por ciento sobre los "
            "salarios del periodo de vacaciones. Sin reformas."
        ),
    },
]

REGLAS = _REGLAS_LABORALES + REGLAS_FISCALES
