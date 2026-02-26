"""Add WebhookSubscription model."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0011_apikey_apiusagelog"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebhookSubscription",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("url", models.URLField(max_length=500)),
                (
                    "events",
                    models.JSONField(
                        default=list,
                        help_text='e.g. ["law.updated", "law.created", "version.created"]',
                    ),
                ),
                (
                    "domain_filter",
                    models.JSONField(
                        default=list,
                        help_text='e.g. ["fiscal"] \u2014 empty list means all domains',
                    ),
                ),
                (
                    "secret",
                    models.CharField(
                        help_text="HMAC-SHA256 signing secret", max_length=64
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_triggered_at", models.DateTimeField(blank=True, null=True)),
                (
                    "failure_count",
                    models.IntegerField(
                        default=0,
                        help_text="Auto-disable after 10 consecutive failures",
                    ),
                ),
                (
                    "api_key",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="webhooks",
                        to="api.apikey",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["api_key", "is_active"],
                        name="api_webhook_key_active_idx",
                    ),
                ],
            },
        ),
    ]
