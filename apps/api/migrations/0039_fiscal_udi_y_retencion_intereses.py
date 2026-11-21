# Hand-written to the shape `makemigrations` produces for the two models below;
# CI's `makemigrations --check` is what confirms it matches the model state.

import django.core.validators
from django.db import migrations, models

DOF_CODIGO_HELP = "DOF nota_detalle 'codigo' — the stable identifier of the exact publication, e.g. '5778072'. Together with dof_date it resolves to one document: https://dof.gob.mx/nota_detalle.php?codigo=<codigo>&fecha=<dd/mm/yyyy>. Empty when the row is not tied to a single DOF publication."


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0038_fiscal_isn_estatal"),
    ]

    operations = [
        migrations.CreateModel(
            name="UDIValue",
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
                    "unit",
                    models.CharField(
                        default="MXN",
                        help_text='e.g. "MXN", "MXN/day", "percent"',
                        max_length=32,
                    ),
                ),
                (
                    "vigencia_from",
                    models.DateField(
                        db_index=True,
                        help_text="First day this value is in force (inclusive)",
                    ),
                ),
                (
                    "vigencia_to",
                    models.DateField(
                        blank=True,
                        db_index=True,
                        help_text="Last day in force (inclusive). NULL = still in force.",
                        null=True,
                    ),
                ),
                (
                    "source_citation",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Human-readable citation, e.g. 'DOF 09-01-2026, CONASAMI'",
                    ),
                ),
                ("source_url", models.URLField(blank=True, default="", max_length=500)),
                (
                    "dof_date",
                    models.DateField(
                        blank=True,
                        help_text="Publication date in the Diario Oficial de la Federación",
                        null=True,
                    ),
                ),
                (
                    "dof_codigo",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        help_text=DOF_CODIGO_HELP,
                        max_length=20,
                    ),
                ),
                (
                    "provenance",
                    models.CharField(
                        choices=[
                            ("published", "Published (DOF-verified)"),
                            ("seed-unverified", "Seed (unverified)"),
                            ("operator", "Operator-entered"),
                        ],
                        db_index=True,
                        default="seed-unverified",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "value",
                    models.DecimalField(
                        decimal_places=6,
                        help_text="Pesos por una UDI, con las seis decimales del aviso",
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
            ],
            options={
                "verbose_name": "valor de la UDI",
                "verbose_name_plural": "valores de la UDI",
                "ordering": ["-vigencia_from"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("vigencia_from",),
                        name="uniq_udi_vigencia",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="RetencionIntereses",
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
                    "value",
                    models.DecimalField(
                        decimal_places=4,
                        help_text="The value in force, in MXN unless the unit says otherwise",
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "unit",
                    models.CharField(
                        default="MXN",
                        help_text='e.g. "MXN", "MXN/day", "percent"',
                        max_length=32,
                    ),
                ),
                (
                    "vigencia_from",
                    models.DateField(
                        db_index=True,
                        help_text="First day this value is in force (inclusive)",
                    ),
                ),
                (
                    "vigencia_to",
                    models.DateField(
                        blank=True,
                        db_index=True,
                        help_text="Last day in force (inclusive). NULL = still in force.",
                        null=True,
                    ),
                ),
                (
                    "source_citation",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Human-readable citation, e.g. 'DOF 09-01-2026, CONASAMI'",
                    ),
                ),
                ("source_url", models.URLField(blank=True, default="", max_length=500)),
                (
                    "dof_date",
                    models.DateField(
                        blank=True,
                        help_text="Publication date in the Diario Oficial de la Federación",
                        null=True,
                    ),
                ),
                (
                    "dof_codigo",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        help_text=DOF_CODIGO_HELP,
                        max_length=20,
                    ),
                ),
                (
                    "provenance",
                    models.CharField(
                        choices=[
                            ("published", "Published (DOF-verified)"),
                            ("seed-unverified", "Seed (unverified)"),
                            ("operator", "Operator-entered"),
                        ],
                        db_index=True,
                        default="seed-unverified",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "year",
                    models.IntegerField(db_index=True, help_text="Ejercicio fiscal"),
                ),
                (
                    "legal_basis",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Artículo que fija la tasa, p. ej. 'LIF 2026 Art. 24'",
                        max_length=200,
                    ),
                ),
            ],
            options={
                "verbose_name": "tasa de retención sobre intereses",
                "verbose_name_plural": "tasas de retención sobre intereses",
                "ordering": ["-year"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("year",),
                        name="uniq_retencion_intereses_year",
                    )
                ],
            },
        ),
    ]
