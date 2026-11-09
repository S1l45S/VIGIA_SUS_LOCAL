from django.db import models


class CargaDeDados(models.Model):

    STATUS_CHOICES = [
        ("PROCESSANDO", "Processando"),
        ("ACEITA", "Aceita"),
        ("REJEITADA", "Rejeitada"),
    ]

    origem = models.CharField(
        max_length=255
    )

    data_extracao = models.DateTimeField(
        null=True,
        blank=True
    )

    periodo_inicio = models.DateField(
        null=True,
        blank=True
    )

    periodo_fim = models.DateField(
        null=True,
        blank=True
    )

    registros_lidos = models.PositiveIntegerField(
        default=0
    )

    registros_validos = models.PositiveIntegerField(
        default=0
    )

    registros_rejeitados = models.PositiveIntegerField(
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PROCESSANDO"
    )

    motivo_rejeicao = models.TextField(
        blank=True
    )

    criada_em = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "cargas"

    def __str__(self):
        return f"Carga {self.pk} - {self.status}"

class RegistroSemanal(models.Model):

    agravo_codigo = models.CharField(
        max_length=30
    )

    municipio_codigo = models.CharField(
        max_length=7
    )

    semana_inicio = models.DateField()

    semana_ord = models.IntegerField()

    ano = models.PositiveIntegerField()

    semana_epidemiologica = models.PositiveSmallIntegerField()

    quantidade = models.PositiveIntegerField()

    carga_id = models.CharField(
        max_length=100
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "registros_semanais"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "agravo_codigo",
                    "municipio_codigo",
                    "semana_inicio",
                ],
                name="uq_registro_agravo_municipio_semana",
            )
        ]

    def __str__(self):
        return (
            f"{self.agravo_codigo} - "
            f"{self.municipio_codigo} - "
            f"{self.semana_inicio}"
        )

# Create your models here.
