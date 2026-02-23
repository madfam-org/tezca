from django.db import models


class Law(models.Model):
    OFFICIAL_ID_MAX_LENGTH = 200

    class Status(models.TextChoices):
        VIGENTE = "vigente", "Vigente"
        ABROGADA = "abrogada", "Abrogada"
        DEROGADA = "derogada", "Derogada"
        UNKNOWN = "unknown", "Unknown"

    class LawType(models.TextChoices):
        LEGISLATIVE = "legislative", "Legislative"
        NON_LEGISLATIVE = "non_legislative", "Non-Legislative"

    official_id = models.CharField(
        max_length=OFFICIAL_ID_MAX_LENGTH,
        unique=True,
        help_text="Slug identifier (e.g., 'cpeum')",
    )
    name = models.CharField(max_length=500, help_text="Full name of the law")
    short_name = models.CharField(max_length=200, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    tier = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    municipality = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Municipality name for municipal laws",
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="State name (e.g., 'Jalisco', 'Ciudad de México')",
    )
    source_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL where this law was obtained",
    )
    last_verified = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this law's source was verified as still available",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNKNOWN,
        db_index=True,
        help_text="Legal status: vigente, abrogada, derogada, unknown",
    )
    law_type = models.CharField(
        max_length=20,
        choices=LawType.choices,
        default=LawType.LEGISLATIVE,
        db_index=True,
        help_text="Legislative (from Congress) or Non-Legislative (executive, judicial, autonomous)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.official_id} - {self.short_name or self.name}"


class LawVersion(models.Model):
    law = models.ForeignKey(Law, on_delete=models.CASCADE, related_name="versions")
    publication_date = models.DateField(help_text="Date of publication in DOF")

    # Validity range
    valid_from = models.DateField(
        null=True, blank=True, help_text="Date this version became effective"
    )
    valid_to = models.DateField(
        null=True,
        blank=True,
        help_text="Date this version was superseded (null if current)",
    )

    # Content
    dof_url = models.URLField(max_length=500, blank=True, null=True)
    xml_file_path = models.CharField(max_length=500, blank=True, null=True)

    # Metadata
    change_summary = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-publication_date"]
        indexes = [
            models.Index(fields=["law", "valid_from", "valid_to"]),
        ]

    def __str__(self):
        return f"{self.law.official_id} ({self.publication_date})"


class CrossReference(models.Model):
    """
    Stores detected cross-references between articles and laws.

    Examples:
    - Article 5 in Law A references Article 107 in Law B
    - Article 27 references "Ley de Amparo" (general reference)
    """

    # Source (where the reference appears)
    source_law_slug = models.CharField(max_length=255, db_index=True)
    source_article_id = models.CharField(max_length=100, db_index=True)

    # Target (what is being referenced)
    target_law_slug = models.CharField(
        max_length=255, db_index=True, null=True, blank=True
    )
    target_article_num = models.CharField(max_length=100, null=True, blank=True)

    # Reference details
    reference_text = models.TextField(help_text="Original text of the reference")
    fraction = models.CharField(
        max_length=20, null=True, blank=True, help_text="Fraction number if specified"
    )
    confidence = models.FloatField(help_text="Detection confidence score (0-1)")

    # Position in source text
    start_position = models.IntegerField(help_text="Start position in article text")
    end_position = models.IntegerField(help_text="End position in article text")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cross_references"
        indexes = [
            models.Index(fields=["source_law_slug", "source_article_id"]),
            models.Index(fields=["target_law_slug", "target_article_num"]),
            models.Index(fields=["confidence"]),
        ]
        ordering = ["start_position"]

    def __str__(self):
        return (
            f"{self.source_law_slug}:{self.source_article_id} -> {self.reference_text}"
        )

    def target_url(self) -> str | None:
        """Generate URL for the target reference."""
        if not self.target_law_slug:
            return None

        url = f"/leyes/{self.target_law_slug}"
        if self.target_article_num:
            url += f"#article-{self.target_article_num}"

        return url


class ExportLog(models.Model):
    """Tracks export requests for quota enforcement."""

    user_id = models.CharField(max_length=255, blank=True, default="")
    ip_address = models.GenericIPAddressField()
    law_id = models.CharField(max_length=50)
    format = models.CharField(max_length=10)
    tier = models.CharField(max_length=20, default="anon")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_id", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
        ]

    def __str__(self):
        return f"{self.tier}:{self.format} {self.law_id} ({self.created_at})"
