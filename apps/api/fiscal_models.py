"""Fiscal-value models — the versioned, DOF-stamped values feed.

Tezca is the ecosystem's Mexican-law oracle.  These models let it serve
*values* (not only law text) so consumers — symbiosis-hcm first, karafiel
second — never re-implement fiscal-value lookup.

Design invariants:

1. **Append-only.**  A value is never edited in place once published; a
   correction is a new row.  ``vigencia_from`` / ``vigencia_to`` carry the
   period a value was in force, so "what was the UMA on 2019-03-04" is
   answerable forever.
2. **Provenance is mandatory and honest.**  Every row states where the
   number came from.  ``SEED_UNVERIFIED`` exists precisely so the feed can
   ship useful values without claiming a DOF citation it does not have.
   A consumer computing an employer cost can therefore refuse to treat an
   unverified value as authoritative.
3. **UMA is not salario mínimo.**  LFVUMA Art. 4 / DOF 27-01-2016 severed
   them: obligations, fines and caps are denominated in UMA; wages in
   salario mínimo.  They are separate models on purpose — never fold them.
"""

from django.core.validators import MinValueValidator
from django.db import models


class Provenance(models.TextChoices):
    """How much this row's value can be trusted.

    ``PUBLISHED`` — transcribed from the cited DOF publication; the citation
    and ``dof_date`` identify the exact source document.
    ``SEED_UNVERIFIED`` — a well-known published figure entered to make the
    feed useful on day one, but NOT verified against a DOF document by this
    repo.  Consumers must treat it as decision-support, never as a
    compliance assertion.
    ``OPERATOR`` — entered by a staff operator through the admin, e.g. the
    hours after a DOF publication and before the ingestion pipeline runs.
    """

    PUBLISHED = "published", "Published (DOF-verified)"
    SEED_UNVERIFIED = "seed-unverified", "Seed (unverified)"
    OPERATOR = "operator", "Operator-entered"


class FiscalValueBase(models.Model):
    """Shared provenance + vigencia fields for every fiscal value row."""

    value = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        validators=[MinValueValidator(0)],
        help_text="The value in force, in MXN unless the unit says otherwise",
    )
    unit = models.CharField(
        max_length=32,
        default="MXN",
        help_text='e.g. "MXN", "MXN/day", "percent"',
    )
    vigencia_from = models.DateField(
        db_index=True,
        help_text="First day this value is in force (inclusive)",
    )
    vigencia_to = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Last day in force (inclusive). NULL = still in force.",
    )
    source_citation = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable citation, e.g. 'DOF 09-01-2026, CONASAMI'",
    )
    source_url = models.URLField(max_length=500, blank=True, default="")
    dof_date = models.DateField(
        null=True,
        blank=True,
        help_text="Publication date in the Diario Oficial de la Federación",
    )
    dof_codigo = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_index=True,
        help_text=(
            "DOF nota_detalle 'codigo' — the stable identifier of the exact "
            "publication, e.g. '5778072'. Together with dof_date it resolves "
            "to one document: "
            "https://dof.gob.mx/nota_detalle.php?codigo=<codigo>&fecha=<dd/mm/yyyy>. "
            "Empty when the row is not tied to a single DOF publication."
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
        """True only for DOF-verified rows — the assert/advisory boundary."""
        return self.provenance == Provenance.PUBLISHED


class UMAValue(FiscalValueBase):
    """Unidad de Medida y Actualización — daily/monthly/annual, per year.

    Set by INEGI, published in the DOF each January, in force from 1
    February (LFVUMA).  ``value`` carries the *daily* figure; the monthly
    and annual figures are stored explicitly rather than derived, because
    INEGI publishes all three and the rounding is theirs, not ours.
    """

    year = models.IntegerField(db_index=True, help_text="Fiscal year, e.g. 2026")
    monthly_value = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        validators=[MinValueValidator(0)],
        help_text="Monthly UMA as published (not daily x 30.4)",
    )
    annual_value = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        validators=[MinValueValidator(0)],
        help_text="Annual UMA as published (not monthly x 12)",
    )

    class Meta:
        verbose_name = "UMA value"
        verbose_name_plural = "UMA values"
        ordering = ["-vigencia_from"]
        indexes = [
            models.Index(fields=["year"]),
            models.Index(fields=["vigencia_from", "vigencia_to"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["year", "vigencia_from"],
                name="uniq_uma_year_vigencia",
            )
        ]

    def __str__(self):
        return f"UMA {self.year}: {self.value}/day [{self.provenance}]"


class MinimumWage(FiscalValueBase):
    """Salario mínimo general — CONASAMI, DOF, effective 1 January.

    Two zones since 2019: the Zona Libre de la Frontera Norte (ZLFN) and
    the rest of the country ("general").  Professional minimums exist too
    (salarios mínimos profesionales) — the ``zone`` field is deliberately
    open so those can land later without a migration of meaning.
    """

    class Zone(models.TextChoices):
        GENERAL = "general", "General (resto del país)"
        ZLFN = "zlfn", "Zona Libre de la Frontera Norte"

    year = models.IntegerField(db_index=True)
    zone = models.CharField(
        max_length=20,
        choices=Zone.choices,
        default=Zone.GENERAL,
        db_index=True,
    )

    class Meta:
        verbose_name = "minimum wage"
        verbose_name_plural = "minimum wages"
        ordering = ["-vigencia_from", "zone"]
        indexes = [
            models.Index(fields=["year", "zone"]),
            models.Index(fields=["vigencia_from", "vigencia_to"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["year", "zone", "vigencia_from"],
                name="uniq_minwage_year_zone_vigencia",
            )
        ]

    def __str__(self):
        return (
            f"Salario mínimo {self.zone} {self.year}: {self.value} [{self.provenance}]"
        )


class TipoDeCambio(FiscalValueBase):
    """DOF reference exchange rate — *tipo de cambio para solventar
    obligaciones denominadas en moneda extranjera*, published by Banco de
    México in the Diario Oficial de la Federación each business day.

    This is the SAT-defensible rate: LIVA Art. 20 and CFF Art. 20 require
    fiscal obligations denominated in foreign currency to be converted at
    the DOF rate in force on the day the obligation arises. It is *not* a
    market/spot rate — consumers who want a live spot quote go direct to a
    market provider; those who need the legally-binding rate for a CFDI or a
    tax figure read it here.

    Append-only like every fiscal value: each business-day publication is a
    new row (``vigencia_from`` = the day it is in force, normally the DOF
    ``dof_date``), never an edit. ``value`` is the units of ``to_currency``
    per one unit of ``from_currency`` (e.g. MXN per 1 USD).
    """

    from_currency = models.CharField(
        max_length=3,
        default="USD",
        db_index=True,
        help_text="ISO 4217 base currency (default USD — the only pair the DOF publishes daily)",
    )
    to_currency = models.CharField(
        max_length=3,
        default="MXN",
        db_index=True,
        help_text="ISO 4217 quote currency (default MXN)",
    )

    class Meta:
        verbose_name = "tipo de cambio (DOF)"
        verbose_name_plural = "tipos de cambio (DOF)"
        ordering = ["-vigencia_from", "from_currency", "to_currency"]
        indexes = [
            models.Index(fields=["from_currency", "to_currency", "vigencia_from"]),
            models.Index(fields=["vigencia_from", "vigencia_to"]),
        ]
        constraints = [
            # One published rate per pair per in-force day. A correction is a
            # later-vigencia row, so the natural key is (pair, vigencia_from).
            models.UniqueConstraint(
                fields=["from_currency", "to_currency", "vigencia_from"],
                name="uniq_tipocambio_pair_vigencia",
            )
        ]

    def __str__(self):
        return (
            f"TC {self.from_currency}/{self.to_currency} "
            f"{self.vigencia_from}: {self.value} [{self.provenance}]"
        )


class FiscalTable(models.Model):
    """A structured, versioned fiscal table keyed by fiscal year.

    Covers the tabular values that do not reduce to a single scalar: the
    Art. 96 LISR retention brackets, the subsidio al empleo table, IMSS
    contribution rates, ISN rates by state.  ``rows`` holds the table as
    published; the shape is documented per ``kind`` in the API docs so
    consumers can parse without guessing.

    Append-only like the scalar models: a corrected table is a new row
    with a later ``vigencia_from``, never an edit.
    """

    class Kind(models.TextChoices):
        ISR_MONTHLY = "isr_monthly", "ISR retención mensual (LISR 96)"
        ISR_ANNUAL = "isr_annual", "ISR tarifa anual (LISR 152)"
        SUBSIDIO_MONTHLY = "subsidio_monthly", "Subsidio al empleo mensual"
        # Since the DOF 01-05-2024 decreto (as modified 31-12-2024), the
        # subsidio is no longer a bracket table: it is a single amount —
        # 13.8 % of the monthly UMA — payable while the ingreso base does not
        # exceed a fixed cap. That is a *rule*, not a table, so it gets its own
        # kind rather than being flattened into fake brackets. The rule's
        # ``rows`` carry the parameters; a consumer that only knows
        # ``subsidio_monthly`` sees no row and fails closed, which is correct:
        # it must not apply pre-2025 brackets to a post-decreto year.
        SUBSIDIO_RULE = "subsidio_rule", "Subsidio al empleo (regla derivada)"
        IMSS_RATES = "imss_rates", "Cuotas obrero-patronales IMSS"
        ISN_RATES = "isn_rates", "Impuesto sobre nóminas por entidad"

    kind = models.CharField(max_length=32, choices=Kind.choices, db_index=True)
    year = models.IntegerField(db_index=True)
    period = models.CharField(
        max_length=20,
        default="monthly",
        help_text='Bracket period: "monthly", "annual", "daily", or "n/a"',
    )
    rows = models.JSONField(
        default=list,
        help_text=(
            "The table as published. For ISR/subsidio: a list of bracket "
            "objects. For imss_rates/isn_rates: a list of rate objects."
        ),
    )
    legal_basis = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text='e.g. "LISR Art. 96"',
    )
    vigencia_from = models.DateField(db_index=True)
    vigencia_to = models.DateField(null=True, blank=True, db_index=True)
    source_citation = models.TextField(blank=True, default="")
    source_url = models.URLField(max_length=500, blank=True, default="")
    dof_date = models.DateField(null=True, blank=True)
    dof_codigo = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_index=True,
        help_text=(
            "DOF nota_detalle 'codigo' of the publication carrying this table "
            "(e.g. '5777219' for the Anexo 8 de la RMF 2026). Empty when the "
            "table is not tied to a single DOF publication."
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
        verbose_name = "fiscal table"
        verbose_name_plural = "fiscal tables"
        ordering = ["-year", "kind"]
        indexes = [
            models.Index(fields=["kind", "year"]),
            models.Index(fields=["vigencia_from", "vigencia_to"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "year", "vigencia_from"],
                name="uniq_fiscaltable_kind_year_vigencia",
            )
        ]

    def __str__(self):
        return f"{self.kind} {self.year} [{self.provenance}]"

    @property
    def is_verified(self) -> bool:
        return self.provenance == Provenance.PUBLISHED
