from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0016_contribution"),
    ]

    operations = [
        migrations.CreateModel(
            name="JudicialRecord",
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
                    "registro",
                    models.CharField(
                        help_text="SCJN registry key",
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    "epoca",
                    models.CharField(
                        db_index=True,
                        help_text="Epoch (e.g. 11a)",
                        max_length=50,
                    ),
                ),
                (
                    "instancia",
                    models.CharField(
                        help_text="Issuing body (Pleno, Primera Sala, TCC, etc.)",
                        max_length=200,
                    ),
                ),
                (
                    "materia",
                    models.CharField(
                        choices=[
                            ("civil", "Civil"),
                            ("penal", "Penal"),
                            ("administrativa", "Administrativa"),
                            ("laboral", "Laboral"),
                            ("constitucional", "Constitucional"),
                            ("comun", "Común"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("jurisprudencia", "Jurisprudencia"),
                            ("tesis_aislada", "Tesis Aislada"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                (
                    "rubro",
                    models.TextField(help_text="Subject heading / title"),
                ),
                (
                    "texto",
                    models.TextField(help_text="Full text of the thesis"),
                ),
                (
                    "precedentes",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Precedent cases",
                    ),
                ),
                (
                    "votos",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Dissenting/concurring votes",
                    ),
                ),
                (
                    "ponente",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Reporting justice",
                        max_length=200,
                    ),
                ),
                (
                    "fuente",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Source publication (Semanario Judicial, Gaceta)",
                        max_length=300,
                    ),
                ),
                ("fecha_publicacion", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-fecha_publicacion"],
                "indexes": [
                    models.Index(
                        fields=["tipo", "materia"],
                        name="api_judicial_tipo_ma_idx",
                    ),
                    models.Index(
                        fields=["epoca", "instancia"],
                        name="api_judicial_epoca_i_idx",
                    ),
                ],
            },
        ),
    ]
