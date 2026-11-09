import django_mongodb_backend.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ResultadoDeteccao",
            fields=[
                ("id", django_mongodb_backend.fields.ObjectIdAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name="ID",
                )),
                ("agravo_codigo", models.CharField(max_length=30)),
                ("municipio_codigo", models.CharField(max_length=7)),
                ("semana_inicio", models.DateField()),
                ("quantidade_observada", models.PositiveIntegerField()),
                ("media_movel", models.FloatField()),
                ("desvio_padrao", models.FloatField()),
                ("limite_superior", models.FloatField()),
                ("anomalia", models.BooleanField(default=False)),
                ("janela_semanas", models.PositiveSmallIntegerField(default=8)),
                ("calculado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "resultados_deteccao",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("agravo_codigo", "municipio_codigo", "semana_inicio"),
                        name="uq_deteccao_agravo_municipio_semana",
                    )
                ],
                "indexes": [
                    models.Index(
                        fields=("municipio_codigo", "semana_inicio"),
                        name="idx_deteccao_mun_semana",
                    )
                ],
            },
        ),
    ]
