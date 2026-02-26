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
    category = models.CharField(max_length=100, blank=True, null=True, db_index=True)
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
        db_index=True,
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
    updated_at = models.DateTimeField(auto_now=True)

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
    law_id = models.CharField(max_length=200)
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


class APIKey(models.Model):
    """API key for programmatic access to Tezca data."""

    class Tier(models.TextChoices):
        INTERNAL = "internal", "Internal (MADFAM)"
        FREE = "free", "Free"
        PRO = "pro", "Pro"
        ENTERPRISE = "enterprise", "Enterprise"

    prefix = models.CharField(max_length=8, unique=True, db_index=True)
    hashed_key = models.CharField(max_length=128)
    name = models.CharField(max_length=200)
    owner_email = models.EmailField()
    organization = models.CharField(max_length=200, blank=True, default="")
    janua_user_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        help_text="Links key to Janua account for tier sync",
    )
    tier = models.CharField(
        max_length=20, choices=Tier.choices, default=Tier.FREE, db_index=True
    )
    scopes = models.JSONField(
        default=list, help_text='e.g. ["read", "search", "export", "bulk"]'
    )
    allowed_domains = models.JSONField(
        default=list,
        help_text='e.g. ["fiscal", "mercantil"] — empty list means all domains',
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    rate_limit_per_hour = models.IntegerField(
        null=True, blank=True, help_text="Override tier default rate limit"
    )

    class Meta:
        indexes = [models.Index(fields=["prefix", "is_active"])]
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"

    def __str__(self):
        return f"{self.name} ({self.prefix}...) [{self.tier}]"


class APIUsageLog(models.Model):
    """Tracks API usage for analytics and rate limiting."""

    api_key_prefix = models.CharField(max_length=8, blank=True, default="", db_index=True)
    ip_address = models.GenericIPAddressField()
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10, default="GET")
    status_code = models.IntegerField(default=200)
    response_time_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["api_key_prefix", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
        ]

    def __str__(self):
        return f"{self.method} {self.endpoint} [{self.status_code}] ({self.api_key_prefix or 'anon'})"


class WebhookSubscription(models.Model):
    """Webhook subscription for push notifications on law changes."""

    api_key = models.ForeignKey(
        APIKey, on_delete=models.CASCADE, related_name="webhooks"
    )
    url = models.URLField(max_length=500)
    events = models.JSONField(
        default=list,
        help_text='e.g. ["law.updated", "law.created", "version.created"]',
    )
    domain_filter = models.JSONField(
        default=list,
        help_text='e.g. ["fiscal"] — empty list means all domains',
    )
    secret = models.CharField(max_length=64, help_text="HMAC-SHA256 signing secret")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    failure_count = models.IntegerField(
        default=0, help_text="Auto-disable after 10 consecutive failures"
    )

    class Meta:
        indexes = [
            models.Index(fields=["api_key", "is_active"]),
        ]

    def __str__(self):
        return f"Webhook {self.url} [{','.join(self.events)}] (key={self.api_key.prefix})"
