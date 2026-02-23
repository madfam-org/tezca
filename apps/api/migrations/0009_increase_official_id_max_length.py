from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0008_exportlog"),
    ]

    operations = [
        migrations.AlterField(
            model_name="law",
            name="official_id",
            field=models.CharField(
                help_text="Slug identifier (e.g., 'cpeum')",
                max_length=200,
                unique=True,
            ),
        ),
    ]
