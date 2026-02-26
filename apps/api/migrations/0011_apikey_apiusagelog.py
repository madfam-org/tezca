"""Add APIKey and APIUsageLog models."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0010_add_db_indexes_and_fix_exportlog"),
    ]

    operations = [
        migrations.CreateModel(
            name="APIKey",
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
                ("prefix", models.CharField(db_index=True, max_length=8, unique=True)),
                ("hashed_key", models.CharField(max_length=128)),
                ("name", models.CharField(max_length=200)),
                ("owner_email", models.EmailField(max_length=254)),
                (
                    "organization",
                    models.CharField(blank=True, default="", max_length=200),
                ),
                (
                    "janua_user_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        help_text="Links key to Janua account for tier sync",
                        max_length=255,
                    ),
                ),
                (
                    "tier",
                    models.CharField(
                        choices=[
                            ("internal", "Internal (MADFAM)"),
                            ("free", "Free"),
                            ("pro", "Pro"),
                            ("enterprise", "Enterprise"),
                        ],
                        db_index=True,
                        default="free",
                        max_length=20,
                    ),
                ),
                (
                    "scopes",
                    models.JSONField(
                        default=list,
                        help_text='e.g. ["read", "search", "export", "bulk"]',
                    ),
                ),
                (
                    "allowed_domains",
                    models.JSONField(
                        default=list,
                        help_text='e.g. ["fiscal", "mercantil"] \u2014 empty list means all domains',
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "rate_limit_per_hour",
                    models.IntegerField(
                        blank=True,
                        help_text="Override tier default rate limit",
                        null=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "API Key",
                "verbose_name_plural": "API Keys",
                "indexes": [
                    models.Index(
                        fields=["prefix", "is_active"],
                        name="api_apikey_prefix_is_active_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="APIUsageLog",
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
                (
                    "api_key_prefix",
                    models.CharField(
                        blank=True, db_index=True, default="", max_length=8
                    ),
                ),
                ("ip_address", models.GenericIPAddressField()),
                ("endpoint", models.CharField(max_length=200)),
                ("method", models.CharField(default="GET", max_length=10)),
                ("status_code", models.IntegerField(default=200)),
                ("response_time_ms", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["api_key_prefix", "created_at"],
                        name="api_apiusagelog_prefix_created_idx",
                    ),
                    models.Index(
                        fields=["ip_address", "created_at"],
                        name="api_apiusagelog_ip_created_idx",
                    ),
                ],
            },
        ),
    ]
