from django.db import models


class Municipio(models.Model):

    codigo_ibge = models.CharField(
        max_length=7,
        unique=True
    )

    nome = models.CharField(
        max_length=150
    )

    uf = models.CharField(
        max_length=2
    )

    ativo = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "municipios"

    def __str__(self):
        return self.nome

class Agravo(models.Model):

    codigo = models.CharField(
        max_length=30,
        unique=True
    )

    nome = models.CharField(
        max_length=150
    )

    ativo = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "agravos"

    def __str__(self):
        return self.nome
