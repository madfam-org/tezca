from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0015_user_features"),
    ]

    operations = [
        migrations.CreateModel(
            name="Contribution",
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
                ("submitter_name", models.CharField(max_length=200)),
                ("submitter_email", models.EmailField(max_length=254)),
                (
                    "submitter_institution",
                    models.CharField(blank=True, default="", max_length=300),
                ),
                (
                    "data_type",
                    models.CharField(
                        choices=[
                            ("federal", "Legislación federal"),
                            ("state", "Legislación estatal"),
                            ("municipal", "Reglamentación municipal"),
                            ("nom", "Norma Oficial Mexicana"),
                            ("judicial", "Jurisprudencia"),
                            ("treaty", "Tratado internacional"),
                            ("regulation", "Regulación/reglamento"),
                            ("other", "Otro"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "jurisdiction",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="State, municipality, or 'federal'",
                        max_length=200,
                    ),
                ),
                ("description", models.TextField()),
                (
                    "file_url",
                    models.URLField(blank=True, default="", max_length=500),
                ),
                (
                    "file_format",
                    models.CharField(blank=True, default="", max_length=50),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendiente"),
                            ("reviewing", "En revisión"),
                            ("approved", "Aprobado"),
                            ("rejected", "Rechazado"),
                            ("ingested", "Ingresado"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "reviewer_notes",
                    models.TextField(blank=True, default=""),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["status", "data_type"],
                        name="api_contribut_status_a1b2c3_idx",
                    ),
                ],
            },
        ),
    ]
