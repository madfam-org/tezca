"""
Redesign tier system: community→essentials→academic→institutional.

- Rename pro → academic
- Add academic, institutional choices
- Remove pro choice
"""

from django.db import migrations, models


def migrate_pro_to_academic(apps, schema_editor):
    APIKey = apps.get_model("api", "APIKey")
    APIKey.objects.filter(tier="pro").update(tier="academic")


def migrate_academic_to_pro(apps, schema_editor):
    APIKey = apps.get_model("api", "APIKey")
    APIKey.objects.filter(tier="academic").update(tier="pro")


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0020_add_rate_limit_validators"),
    ]

    operations = [
        # Data migration first: pro → academic
        migrations.RunPython(migrate_pro_to_academic, migrate_academic_to_pro),
        # Update choices
        migrations.AlterField(
            model_name="apikey",
            name="tier",
            field=models.CharField(
                choices=[
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
    ]
