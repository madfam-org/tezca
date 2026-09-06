"""Modelos del feed laboral — Tezca como oráculo de la ley del trabajo.

Dos piezas, por razones distintas:

``LawArticle``
    El texto de un artículo **con vigencia**. El corpus de Tezca ya sirve
    artículos desde Elasticsearch (``law_articles``), pero ese índice guarda
    una sola foto del texto sin periodo de vigencia: no puede responder «qué
    decía el artículo 59 de la LFT el 30 de abril de 2026». Un consumidor que
    calcula nómina o cuotas necesita exactamente esa pregunta, así que el
    texto vigente vive aquí, en la base, versionado y con la reforma del DOF
    que lo tocó. Elasticsearch sigue siendo el índice de búsqueda; esta tabla
    es la fuente citable.

``LaborRule``
    La regla **estructurada** que se desprende del artículo: los días de la
    ventana del alta al IMSS, el tope del periodo de prueba, el porcentaje de
    retención por (forma legal del pagador × régimen del prestador), la tabla
    de vacaciones por año de servicio. HCM no debe leer prosa para calcular;
    lee un número, una tabla o una lista, con su artículo y su vigencia.

Invariantes, los mismos que el feed fiscal (``fiscal_models``):

1. **Append-only.** Una fila publicada no se edita: una corrección es una
   fila nueva con vigencia posterior. Por eso ``LFT 59`` puede convivir con
   sus cinco escalones (48 h en 2026 … 40 h en 2030) sin ambigüedad.
2. **Procedencia obligatoria.** ``published`` sólo con lectura primaria (DOF
   o el texto vigente que publica la Cámara de Diputados / STPS / SAT).
   ``seed-unverified`` es la confesión honesta de que la fila sirve para
   orientar pero no para afirmar cumplimiento — el consumidor la descarta.
3. **La vigencia es del artículo, no de la ley.** La Cámara imprime bajo cada
   artículo la nota «Artículo reformado DOF 01-05-2026»; ese sello, y no la
   fecha de la última reforma de la ley entera, es el que fecha el texto.
"""

from django.core.validators import MinValueValidator
from django.db import models

from .fiscal_models import Provenance


class VigenciaProvenanceBase(models.Model):
    """Vigencia + procedencia comunes al feed laboral.

    Deliberadamente separada de ``FiscalValueBase``: aquélla obliga a un
    ``value`` decimal, y una regla laboral puede ser un texto, una lista de
    indicios o una tabla. Los nombres de los campos sí se comparten, para que
    un consumidor que ya lee el feed fiscal no aprenda un vocabulario nuevo.
    """

    official_id = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Identificador de la ley en el corpus, p. ej. 'lft', 'lss', 'cff'",
    )
    # 200 y no 32 (T-1e). Los 32 originales cabían para un número de artículo
    # y para nada más, pero no todo documento se numera por artículos: las
    # Reglas de Operación del programa JCF se citan por apartado y el Acuerdo
    # REPSE por ordinales en letra. La fila del JCF que publicó T-1c mide 72
    # caracteres, y Postgres —no SQLite, donde corre la suite— la rechazó con
    # `value too long for type character varying(32)`. Truncar la cita no era
    # opción: «Reglas de Operación JCF, apart» no lleva a ningún documento.
    article = models.CharField(
        max_length=200,
        db_index=True,
        help_text=(
            "Artículo normalizado ('59', '39-A', '113-J') o, cuando el "
            "documento no se numera por artículos, su unidad de cita: "
            "'Reglas de Operación JCF, apartado V', 'RMF 2026 regla 2.1.36'"
        ),
    )
    effective_from = models.DateField(
        db_index=True,
        help_text="Primer día en que rige (inclusive)",
    )
    effective_to = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Último día en que rige (inclusive). NULL = sigue vigente.",
    )
    source = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text=(
            "Emisor de la lectura primaria, p. ej. 'Cámara de Diputados, "
            "LeyesBiblio', 'DOF', 'STPS', 'SAT'"
        ),
    )
    source_url = models.URLField(max_length=500, blank=True, default="")
    dof_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de la publicación en el DOF que fija este texto o valor",
    )
    dof_codigo = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_index=True,
        help_text=(
            "'codigo' de nota_detalle del DOF, p. ej. '5786537' para el decreto "
            "de reducción de la jornada laboral. Con dof_date resuelve a un "
            "documento único."
        ),
    )
    provenance = models.CharField(
        max_length=20,
        choices=Provenance.choices,
        default=Provenance.SEED_UNVERIFIED,
        db_index=True,
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    @property
    def is_verified(self) -> bool:
        """True sólo para filas con lectura primaria — la frontera de aserción."""
        return self.provenance == Provenance.PUBLISHED


class LawArticle(VigenciaProvenanceBase):
    """El texto de un artículo tal como rige en un periodo.

    Una fila por (ley, artículo, vigencia). El texto se transcribe del .doc
    que publica la Cámara de Diputados —no del PDF, que intercala espacios
    dentro de las palabras y repite el encabezado de página— y conserva las
    notas de reforma que la propia Cámara imprime.
    """

    text = models.TextField(help_text="Texto íntegro del artículo, tal como se publica")
    edition = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text=(
            "Edición del texto vigente de la que se transcribió, p. ej. "
            "'Última reforma DOF 14-05-2026'"
        ),
    )
    derogado = models.BooleanField(
        default=False,
        help_text=(
            "El artículo dice 'Se deroga'. Se publica igual —un consumidor "
            "necesita saber que su base legal desapareció, no un 404."
        ),
    )
    reformas_dof = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Fechas DOF (dd-mm-aaaa) de las reformas que la Cámara imprime "
            "bajo el artículo, de la más antigua a la más reciente."
        ),
    )

    class Meta:
        verbose_name = "artículo de ley (con vigencia)"
        verbose_name_plural = "artículos de ley (con vigencia)"
        ordering = ["official_id", "article", "-effective_from"]
        indexes = [
            models.Index(fields=["official_id", "article", "effective_from"]),
            models.Index(fields=["effective_from", "effective_to"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["official_id", "article", "effective_from"],
                name="uniq_lawarticle_ley_articulo_vigencia",
            )
        ]

    def __str__(self):
        return f"{self.official_id} art. {self.article} [{self.provenance}]"


class LaborRule(VigenciaProvenanceBase):
    """Una regla laboral estructurada, con su artículo y su vigencia.

    ``value`` es JSON a propósito: un ``kind`` puede ser un número (los 5 días
    hábiles del alta al IMSS), una tabla (vacaciones por año de servicio), una
    lista (los indicios de subordinación del art. 20 LFT) o un objeto (la
    fórmula del factor de actualización del CFF 17-A). El ``unit`` dice cómo
    leerlo y ``docs/labor/README.md`` documenta la forma por ``kind``.

    Las tres dimensiones opcionales existen porque la misma pregunta tiene
    respuestas distintas según quién paga y bajo qué régimen cobra: la
    retención de ISR sobre honorarios es 10 % si el pagador es persona moral
    y el prestador está en el régimen de actividades profesionales, 1.25 % si
    está en RESICO, y **no existe** si el pagador es una persona física. Un
    consumidor que no filtra recibe todas las filas y debe elegir; uno que
    filtra recibe la suya.
    """

    class Kind(models.TextChoices):
        IMSS_ALTA_VENTANA = (
            "imss_alta_ventana_dias_habiles",
            "Ventana para el alta en el IMSS (días hábiles)",
        )
        CONTRATO_ESCRITO = (
            "contrato_escrito_desde_inicio",
            "Contrato escrito desde el inicio",
        )
        PRUEBA_DIAS_MAX = ("prueba_dias_max", "Periodo de prueba (días máximo)")
        PRUEBA_DIAS_MAX_DIRECCION = (
            "prueba_dias_max_direccion",
            "Periodo de prueba, puestos de dirección (días máximo)",
        )
        CAPACITACION_MESES_MAX = (
            "capacitacion_inicial_meses_max",
            "Capacitación inicial (meses máximo)",
        )
        CAPACITACION_MESES_MAX_DIRECCION = (
            "capacitacion_inicial_meses_max_direccion",
            "Capacitación inicial, puestos de dirección (meses máximo)",
        )
        JORNADA_SEMANAL_HORAS_MAX = (
            "jornada_semanal_horas_max",
            "Jornada ordinaria semanal (horas máximo)",
        )
        JORNADA_DIURNA_HORAS_MAX = (
            "jornada_diurna_horas_max",
            "Jornada diurna diaria (horas máximo)",
        )
        JORNADA_NOCTURNA_HORAS_MAX = (
            "jornada_nocturna_horas_max",
            "Jornada nocturna diaria (horas máximo)",
        )
        JORNADA_MIXTA_HORAS_MAX = (
            "jornada_mixta_horas_max",
            "Jornada mixta diaria (horas máximo)",
        )
        TIEMPO_EXTRA_SEMANAL_HORAS_MAX = (
            "tiempo_extra_semanal_horas_max",
            "Tiempo extraordinario semanal (horas máximo)",
        )
        SEMANA_REDUCIDA_PRORRATEO = (
            "semana_reducida_prorrateo",
            "Cotización con jornada o semana reducida",
        )
        PTU_EVENTUALES_DIAS_MIN = (
            "ptu_eventuales_dias_min",
            "PTU de eventuales (días mínimo trabajados)",
        )
        PTU_FECHA_LIMITE_DIAS = (
            "ptu_fecha_limite_dias",
            "PTU: días para repartir tras la declaración anual",
        )
        AGUINALDO_DIAS_MIN = ("aguinaldo_dias_min", "Aguinaldo (días mínimo)")
        AGUINALDO_FECHA_LIMITE = ("aguinaldo_fecha_limite", "Aguinaldo: fecha límite")
        VACACIONES_DIAS_POR_ANIO = (
            "vacaciones_dias_por_anio",
            "Vacaciones por año de servicio (tabla)",
        )
        PRIMA_VACACIONAL_PCT_MIN = (
            "prima_vacacional_pct_min",
            "Prima vacacional (porcentaje mínimo)",
        )
        RETENCION_ISR_HONORARIOS_PCT = (
            "retencion_isr_honorarios_pct",
            "Retención de ISR sobre honorarios (porcentaje)",
        )
        RETENCION_IVA_HONORARIOS_FRACCION = (
            "retencion_iva_honorarios_fraccion",
            "Retención de IVA sobre honorarios (fracción del trasladado)",
        )
        RESICO_TOPE_ANUAL = ("resico_tope_anual", "Tope anual de ingresos RESICO")
        RECARGOS_TASA_MENSUAL = (
            "recargos_tasa_mensual",
            "Tasa mensual de recargos por mora",
        )
        ACTUALIZACION_FACTOR = (
            "actualizacion_factor",
            "Factor de actualización (CFF 17-A)",
        )
        REPSE_OBLIGATORIO_CONDICIONES = (
            "repse_obligatorio_condiciones",
            "REPSE: condiciones que lo hacen obligatorio",
        )
        REPSE_VIGENCIA_ANIOS = ("repse_vigencia_anios", "REPSE: vigencia del registro")
        TELETRABAJO_UMBRAL_PCT = (
            "teletrabajo_umbral_pct",
            "Teletrabajo: umbral del tiempo en domicilio",
        )
        NOM035_UMBRAL_PERSONAS = (
            "nom035_umbral_personas",
            "NOM-035: obligaciones por tamaño del centro de trabajo",
        )
        NOM037_APLICABILIDAD = (
            "nom037_aplicabilidad",
            "NOM-037: cuándo aplica la norma de teletrabajo",
        )
        # Dos kinds y no uno, por la razón que separa la ley de la doctrina
        # (T-1f). El art. 20 LFT enumera **tres elementos** de la relación de
        # trabajo y nada más; los siete indicios que HCM muestra son criterio
        # orientativo que este carril no pudo citar con registro. Servirlos en
        # una sola fila obligaba a que la fila entera fuera `seed-unverified`,
        # y el consumidor descartaba también los tres elementos que sí son
        # ley. Separados, HCM lee la ley como `published` y ve los indicios
        # como lo que son.
        RELACION_TRABAJO_ELEMENTOS = (
            "relacion_trabajo_elementos",
            "Elementos de la relación de trabajo (LFT 20)",
        )
        RECARACTERIZACION_INDICIOS = (
            "recaracterizacion_indicios",
            "Indicios de relación laboral (orientativos, no de ley)",
        )
        SAT_CATALOGO = ("sat_catalogo", "Catálogo del SAT para el CFDI 4.0")
        # -- Los que el catálogo de obligaciones del HCM consulta (T-1c). ----
        OPINION_32D_VIGENCIA_DIAS = (
            "opinion_32d_vigencia_dias",
            "Opinión del cumplimiento (32-D): vigencia en días",
        )
        CFDI_NOMINA_POR_PERIODO = (
            "cfdi_nomina_por_periodo",
            "CFDI de nómina: cuándo debe expedirse",
        )
        COMISIONES_MIXTAS_UMBRAL_PERSONAS = (
            "comisiones_mixtas_umbral_personas",
            "Comisiones mixtas de capacitación: umbral de personas",
        )
        JCF_VALIDACION_PERIODICIDAD_DIAS = (
            "jcf_validacion_periodicidad_dias",
            "Jóvenes Construyendo el Futuro: periodicidad de la validación",
        )
        # -- Los que HP-2 y HP-5 piden (T-1g). ------------------------------
        SBC_TOPE_VECES_UMA = (
            "sbc_tope_veces_uma",
            "Tope superior del salario base de cotización (veces la UMA)",
        )
        # El nombre lo fija HP-5 (`seguro_facultativo_ventana_dias`), pero el
        # decreto que rige a las personas estudiantes **no fija ventana
        # alguna** y —peor— tampoco es un «seguro facultativo»: la LSS de 1997
        # suprimió esa figura, y el decreto las incorpora al régimen
        # OBLIGATORIO. Publicar el nombre pedido con un número de días
        # inventado sería lo contrario de lo que pide este feed, así que el
        # kind se llama por lo que la fuente dice y HP-5 recibe la corrección.
        SEGURO_ESTUDIANTES_INCORPORACION = (
            "seguro_facultativo_estudiantes_incorporacion",
            "Estudiantes: incorporación al régimen obligatorio del IMSS",
        )

    class PayerLegalForm(models.TextChoices):
        """Forma legal de quien paga. ``ANY`` = la regla no distingue."""

        ANY = "any", "Cualquiera"
        PERSONA_MORAL = "persona_moral", "Persona moral"
        PERSONA_FISICA = "persona_fisica", "Persona física"

    kind = models.CharField(max_length=64, choices=Kind.choices, db_index=True)
    value = models.JSONField(
        help_text=(
            "El valor de la regla: número, cadena, lista o tabla. La forma por "
            "kind se documenta en docs/labor/README.md."
        )
    )
    # 64 y no 40 por la misma holgura: 'fraccion_del_iva_trasladado' ya mide
    # 27 y una unidad compuesta nueva llegaría al tope sin avisar.
    unit = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text='p. ej. "dias_habiles", "horas/semana", "percent", "MXN", "tabla"',
    )
    payer_legal_form = models.CharField(
        max_length=20,
        choices=PayerLegalForm.choices,
        default=PayerLegalForm.ANY,
        db_index=True,
        help_text="Forma legal del pagador cuando la regla depende de ella",
    )
    provider_regime = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_index=True,
        help_text=(
            "Régimen fiscal del prestador cuando la regla depende de él, con "
            "la clave del c_RegimenFiscal del SAT: '612', '626', '601'. Vacío "
            "= la regla no distingue."
        ),
    )
    service = models.CharField(
        max_length=60,
        blank=True,
        default="",
        help_text=(
            "Tipo de servicio cuando la regla depende de él, p. ej. "
            "'servicios_profesionales', 'autotransporte_terrestre_bienes'. "
            "Vacío = la regla no distingue."
        ),
    )
    label = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Etiqueta legible para una interfaz, en español",
    )

    class Meta:
        verbose_name = "regla laboral"
        verbose_name_plural = "reglas laborales"
        ordering = ["kind", "-effective_from"]
        indexes = [
            models.Index(fields=["kind", "effective_from"]),
            models.Index(fields=["kind", "payer_legal_form", "provider_regime"]),
            models.Index(fields=["effective_from", "effective_to"]),
        ]
        constraints = [
            # Una regla por (kind × dimensiones × vigencia). Las dimensiones
            # entran en la clave natural porque 'retencion_isr_honorarios_pct'
            # tiene tres filas simultáneas legítimas, una por régimen.
            models.UniqueConstraint(
                fields=[
                    "kind",
                    "payer_legal_form",
                    "provider_regime",
                    "service",
                    "effective_from",
                ],
                name="uniq_laborrule_kind_dims_vigencia",
            )
        ]

    def __str__(self):
        dims = [
            d
            for d in (self.payer_legal_form, self.provider_regime, self.service)
            if d and d != "any"
        ]
        sufijo = f" ({'/'.join(dims)})" if dims else ""
        return f"{self.kind}{sufijo} desde {self.effective_from} [{self.provenance}]"


class SatCatalogEntry(VigenciaProvenanceBase):
    """Una fila de un catálogo del SAT para el CFDI 4.0.

    ``c_RegimenFiscal``, ``c_TipoRegimen``, ``c_TipoContrato`` y
    ``c_TipoJornada`` son catálogos, no reglas: tienen clave, descripción y su
    propia vigencia (el SAT publica altas y bajas de claves). Un consumidor
    que timbra un CFDI de nómina necesita saber que la clave que va a escribir
    estaba vigente el día del comprobante.

    ``official_id`` guarda el catálogo de origen ('sat_cat_nomina' o
    'sat_cat_cfdi') y ``article`` el nombre del catálogo, para reutilizar la
    procedencia común sin inventar campos paralelos.
    """

    class Catalog(models.TextChoices):
        REGIMEN_FISCAL = "c_RegimenFiscal", "c_RegimenFiscal"
        TIPO_REGIMEN = "c_TipoRegimen", "c_TipoRegimen"
        TIPO_CONTRATO = "c_TipoContrato", "c_TipoContrato"
        TIPO_JORNADA = "c_TipoJornada", "c_TipoJornada"
        # Los tres del complemento de nómina que HP-3 pide (T-1g): sin ellos,
        # la clave 046 «Ingresos asimilados a salarios» vivía como constante
        # en el código del HCM, que es justo la transcripción a mano que este
        # feed existe para evitar.
        TIPO_PERCEPCION = "c_TipoPercepcion", "c_TipoPercepcion"
        TIPO_DEDUCCION = "c_TipoDeduccion", "c_TipoDeduccion"
        TIPO_OTRO_PAGO = "c_TipoOtroPago", "c_TipoOtroPago"

    catalog = models.CharField(max_length=32, choices=Catalog.choices, db_index=True)
    code = models.CharField(
        max_length=10, db_index=True, help_text="Clave, p. ej. '605'"
    )
    label = models.TextField(help_text="Descripción tal como la publica el SAT")
    aplica_fisica = models.BooleanField(
        null=True,
        blank=True,
        help_text="Sólo c_RegimenFiscal: la clave aplica a personas físicas",
    )
    aplica_moral = models.BooleanField(
        null=True,
        blank=True,
        help_text="Sólo c_RegimenFiscal: la clave aplica a personas morales",
    )

    class Meta:
        verbose_name = "clave de catálogo SAT"
        verbose_name_plural = "claves de catálogos SAT"
        ordering = ["catalog", "code", "-effective_from"]
        indexes = [
            models.Index(fields=["catalog", "code", "effective_from"]),
            models.Index(fields=["effective_from", "effective_to"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["catalog", "code", "effective_from"],
                name="uniq_satcatalogo_catalogo_clave_vigencia",
            )
        ]

    def __str__(self):
        return f"{self.catalog} {self.code} [{self.provenance}]"
