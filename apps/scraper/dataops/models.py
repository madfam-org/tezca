from django.db import models
from django.utils import timezone


class DataSource(models.Model):
    """Registry of all known data sources for law acquisition."""

    SOURCE_TYPE_CHOICES = [
        ("scraper", "Automated Scraper"),
        ("api", "API Endpoint"),
        ("manual", "Manual Download"),
        ("foia", "FOIA/Transparency Request"),
        ("partnership", "Institutional Partnership"),
    ]

    LEVEL_CHOICES = [
        ("federal", "Federal"),
        ("state", "State"),
        ("municipal", "Municipal"),
    ]

    STATUS_CHOICES = [
        ("healthy", "Healthy"),
        ("degraded", "Degraded"),
        ("down", "Down"),
        ("unknown", "Unknown"),
    ]

    name = models.CharField(max_length=200, unique=True)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    base_url = models.URLField(max_length=500, blank=True)
    state = models.CharField(max_length=100, blank=True)
    municipality = models.CharField(max_length=100, blank=True)

    # Health tracking
    last_check = models.DateTimeField(null=True, blank=True)
    last_success = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unknown")
    response_time_ms = models.IntegerField(null=True, blank=True)

    # Integration
    scraper_class = models.CharField(
        max_length=200,
        blank=True,
        help_text="Python dotted path to scraper class",
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["level", "state", "name"]

    def __str__(self):
        parts = [self.name]
        if self.state:
            parts.append(f"({self.state})")
        return " ".join(parts)

    def mark_healthy(self, response_time_ms=None):
        now = timezone.now()
        self.status = "healthy"
        self.last_check = now
        self.last_success = now
        if response_time_ms is not None:
            self.response_time_ms = response_time_ms
        self.save(
            update_fields=[
                "status",
                "last_check",
                "last_success",
                "response_time_ms",
                "updated_at",
            ]
        )

    def mark_degraded(self, response_time_ms=None):
        self.status = "degraded"
        self.last_check = timezone.now()
        if response_time_ms is not None:
            self.response_time_ms = response_time_ms
        self.save(
            update_fields=[
                "status",
                "last_check",
                "response_time_ms",
                "updated_at",
            ]
        )

    def mark_down(self):
        self.status = "down"
        self.last_check = timezone.now()
        self.save(update_fields=["status", "last_check", "updated_at"])


class GapRecord(models.Model):
    """Tracks every known data gap with escalation history."""

    LEVEL_CHOICES = DataSource.LEVEL_CHOICES

    GAP_TYPE_CHOICES = [
        ("dead_link", "Dead Link (404/410)"),
        ("missing_source", "No Scraper/Source Exists"),
        ("low_count", "Suspiciously Low Count"),
        ("not_scraped", "Source Known but Not Yet Scraped"),
        ("parse_failure", "Downloaded but Failed to Parse"),
        ("site_redesign", "Source Site Changed Structure"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("blocked", "Blocked"),
        ("resolved", "Resolved"),
        ("permanent", "Permanent Gap"),
    ]

    TIER_CHOICES = [
        (0, "Tier 0: Automated Scraping"),
        (1, "Tier 1: Web Search + Alt Source"),
        (2, "Tier 2: Direct Contact"),
        (3, "Tier 3: FOIA/Transparency"),
        (4, "Tier 4: Institutional Partnership"),
    ]

    # What's missing
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    state = models.CharField(max_length=100, blank=True)
    municipality = models.CharField(max_length=100, blank=True)
    law_name = models.CharField(max_length=500, blank=True)
    ojn_file_id = models.CharField(max_length=100, blank=True)
    gap_type = models.CharField(max_length=20, choices=GAP_TYPE_CHOICES)
    description = models.TextField(blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    current_tier = models.IntegerField(choices=TIER_CHOICES, default=0)

    # Attempts (list of {tier, action, date, result})
    attempts = models.JSONField(default=list, blank=True)
    next_action = models.CharField(max_length=500, blank=True)
    next_action_date = models.DateField(null=True, blank=True)

    # Resolution
    resolved_via = models.CharField(max_length=200, blank=True)
    resolved_url = models.URLField(max_length=500, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Priority (1=highest)
    priority = models.IntegerField(default=5)

    # Relations
    source = models.ForeignKey(
        DataSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gaps",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "current_tier", "state"]
        indexes = [
            models.Index(fields=["status", "current_tier"]),
            models.Index(fields=["level", "state"]),
            models.Index(fields=["gap_type"]),
        ]

    def __str__(self):
        label = self.law_name or self.state or self.description[:50]
        return f"[{self.get_status_display()}] {label} (Tier {self.current_tier})"

    def escalate(self, action_taken, result):
        """Record an escalation attempt and move to next tier."""
        self.attempts.append(
            {
                "tier": self.current_tier,
                "action": action_taken,
                "date": timezone.now().isoformat(),
                "result": result,
            }
        )
        if self.current_tier < 4:
            self.current_tier += 1
            self.status = "in_progress"
        else:
            self.status = "blocked"
        self.save()

    def resolve(self, via, url=""):
        """Mark this gap as resolved."""
        self.status = "resolved"
        self.resolved_via = via
        self.resolved_url = url
        self.resolved_at = timezone.now()
        self.attempts.append(
            {
                "tier": self.current_tier,
                "action": f"Resolved via {via}",
                "date": timezone.now().isoformat(),
                "result": "success",
            }
        )
        self.save()

    def mark_permanent(self, reason=""):
        """Mark this gap as permanently unresolvable."""
        self.status = "permanent"
        if reason:
            self.attempts.append(
                {
                    "tier": self.current_tier,
                    "action": "Marked permanent",
                    "date": timezone.now().isoformat(),
                    "result": reason,
                }
            )
        self.save()


class AcquisitionLog(models.Model):
    """Audit trail for all scraping and ingestion operations."""

    operation = models.CharField(max_length=200)
    source = models.ForeignKey(
        DataSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
    )

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # Counts
    found = models.IntegerField(default=0)
    downloaded = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    ingested = models.IntegerField(default=0)

    # Details
    parameters = models.JSONField(default=dict, blank=True)
    error_summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.operation} ({self.started_at:%Y-%m-%d %H:%M})"

    def finish(self, error_summary=""):
        self.finished_at = timezone.now()
        self.error_summary = error_summary
        self.save(update_fields=["finished_at", "error_summary"])

    @property
    def duration_seconds(self):
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self):
        total = self.found or self.downloaded
        if total == 0:
            return None
        return round((self.downloaded - self.failed) / total * 100, 1)
