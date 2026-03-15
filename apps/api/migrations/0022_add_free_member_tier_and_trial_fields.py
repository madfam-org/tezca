"""Add free_member tier choice and trial fields to APIKey."""

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0021_redesign_tier_choices"),
    ]

    operations = [
        migrations.AlterField(
            model_name="apikey",
            name="tier",
            field=models.CharField(
                choices=[
                    ("free_member", "Free Member"),
                    ("community", "Community"),
                    ("essentials", "Essentials"),
                    ("academic", "Academic"),
                    ("institutional", "Institutional"),
                    ("madfam", "MADFAM (Internal)"),
                ],
                db_index=True,
                default="essentials",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="apikey",
            name="trial_tier",
            field=models.CharField(
                blank=True,
                choices=[
                    ("free_member", "Free Member"),
                    ("community", "Community"),
                    ("essentials", "Essentials"),
                    ("academic", "Academic"),
                    ("institutional", "Institutional"),
                    ("madfam", "MADFAM (Internal)"),
                ],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="apikey",
            name="trial_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="apikey",
            name="trial_ends_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="apikey",
            name="trial_cc_provided",
            field=models.BooleanField(default=False),
        ),
    ]
