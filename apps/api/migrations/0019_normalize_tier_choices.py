"""Normalize legacy tier names to canonical values.

Renames: free -> essentials, enterprise -> pro, internal -> madfam.
"""

from django.db import migrations, models


def normalize_tiers_forward(apps, schema_editor):
    APIKey = apps.get_model("api", "APIKey")
    APIKey.objects.filter(tier="free").update(tier="essentials")
    APIKey.objects.filter(tier="enterprise").update(tier="pro")
    APIKey.objects.filter(tier="internal").update(tier="madfam")


def normalize_tiers_reverse(apps, schema_editor):
    APIKey = apps.get_model("api", "APIKey")
    APIKey.objects.filter(tier="essentials").update(tier="free")
    APIKey.objects.filter(tier="madfam").update(tier="internal")
    # Note: enterprise keys were merged into pro — cannot reverse losslessly


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0018_add_community_tier_choice"),
    ]

    operations = [
        migrations.RunPython(normalize_tiers_forward, normalize_tiers_reverse),
        migrations.AlterField(
            model_name="apikey",
            name="tier",
            field=models.CharField(
                choices=[
                    ("essentials", "Essentials"),
                    ("community", "Community"),
                    ("pro", "Pro"),
                    ("madfam", "MADFAM (Internal)"),
                ],
                db_index=True,
                default="essentials",
                max_length=20,
            ),
        ),
    ]
