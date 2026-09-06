"""`article` cabe la cita entera, y `unit` gana holgura (T-1e).

`publish_labor_rules --dry-run` abortaba en el pod con

    django.db.utils.DataError: value too long for type character varying(32)

porque la regla del JCF que publicó T-1c cita «Reglas de Operación JCF,
apartado V y obligaciones del Centro de Trabajo» —72 caracteres— en un
`article` de 32. La suite no podía verlo: corre sobre SQLite, que ignora el
ancho declarado de un VARCHAR.

Aditiva y reversible. Ensanchar un `varchar(n)` en Postgres es un cambio de
catálogo: no reescribe la tabla ni toma un lock largo, y ninguna fila
existente deja de caber. La reversa (200 -> 32) sí truncaría filas, y por eso
sólo puede correrse mientras ninguna las supere — que es exactamente el
estado que la compuerta `desbordes_de_longitud` mantiene.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0034_labor_rule_kinds_hcm"),
    ]

    operations = [
        migrations.AlterField(
            model_name="laborrule",
            name="article",
            field=models.CharField(
                db_index=True,
                help_text="Artículo normalizado ('59', '39-A', '113-J') o, cuando el documento no se numera por artículos, su unidad de cita: 'Reglas de Operación JCF, apartado V', 'RMF 2026 regla 2.1.36'",
                max_length=200,
            ),
        ),
        migrations.AlterField(
            model_name="laborrule",
            name="unit",
            field=models.CharField(
                blank=True,
                default="",
                help_text='p. ej. "dias_habiles", "horas/semana", "percent", "MXN", "tabla"',
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="lawarticle",
            name="article",
            field=models.CharField(
                db_index=True,
                help_text="Artículo normalizado ('59', '39-A', '113-J') o, cuando el documento no se numera por artículos, su unidad de cita: 'Reglas de Operación JCF, apartado V', 'RMF 2026 regla 2.1.36'",
                max_length=200,
            ),
        ),
        migrations.AlterField(
            model_name="satcatalogentry",
            name="article",
            field=models.CharField(
                db_index=True,
                help_text="Artículo normalizado ('59', '39-A', '113-J') o, cuando el documento no se numera por artículos, su unidad de cita: 'Reglas de Operación JCF, apartado V', 'RMF 2026 regla 2.1.36'",
                max_length=200,
            ),
        ),
    ]
