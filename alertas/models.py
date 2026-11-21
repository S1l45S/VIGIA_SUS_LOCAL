from django.db import models
from django.db.models import Q
from django_mongodb_backend.fields import EmbeddedModelArrayField, ObjectIdField
from django_mongodb_backend.models import EmbeddedModel

from .dominio import ROTULOS, Situacao

SITUACAO_CHOICES = [(s.value, ROTULOS[s]) for s in Situacao]


class RegistroDeSituacao(EmbeddedModel):
    """Entrada do histórico (RN03). Só é acrescentada pelo serviço; nunca editada."""

    situacao = models.CharField(max_length=20, choices=SITUACAO_CHOICES)
    situacao_anterior = models.CharField(max_length=20, blank=True, default="")
    em = models.DateTimeField()
    origem = models.CharField(max_length=10, default="gestor")  # "sistema" | "gestor"
    usuario_id = models.CharField(max_length=40, blank=True, default="")
    usuario_nome = models.CharField(max_length=150, blank=True, default="")
    observacao = models.CharField(max_length=500, blank=True, default="")

    @property
    def rotulo(self) -> str:
        return ROTULOS[Situacao(self.situacao)]

    @property
    def rotulo_anterior(self) -> str:
        return ROTULOS[Situacao(self.situacao_anterior)] if self.situacao_anterior else ""


class Alerta(models.Model):
    # Série e semana (chave natural igual à de ResultadoDeteccao)
    agravo_codigo = models.CharField(max_length=30)
    agravo_nome = models.CharField(max_length=150)
    municipio_codigo = models.CharField(max_length=7)
    municipio_nome = models.CharField(max_length=150)
    semana_inicio = models.DateField()
    ano_epi = models.PositiveSmallIntegerField()
    semana_epi = models.PositiveSmallIntegerField()

    # Fotografia do cálculo no momento da emissão (imutável)
    observado = models.PositiveIntegerField()
    media = models.FloatField()
    desvio = models.FloatField()
    limite = models.FloatField()
    janela_semanas = models.PositiveSmallIntegerField()
    fator_desvio = models.PositiveSmallIntegerField()
    resultado_id = models.CharField(max_length=40)
    carga_id = models.CharField(max_length=100, blank=True, default="")

    # Estado (EST-01: situação e vigência)
    situacao = models.CharField(
        max_length=20, choices=SITUACAO_CHOICES, default=Situacao.NOVO.value
    )
    substituido = models.BooleanField(default=False)
    substituido_por = ObjectIdField(null=True, blank=True)
    substitui = ObjectIdField(null=True, blank=True)

    # Controle otimista de concorrência (R08, ADR-007)
    versao = models.PositiveIntegerField(default=1)
    criado_em = models.DateTimeField()
    historico = EmbeddedModelArrayField(RegistroDeSituacao, default=list)

    class Meta:
        db_table = "alertas"
        constraints = [
            # Sem duplicidade: no máximo um alerta NÃO substituído por série/semana.
            models.UniqueConstraint(
                fields=["agravo_codigo", "municipio_codigo", "semana_inicio"],
                condition=Q(substituido=False),
                name="uq_alerta_vigente_serie_semana",
            ),
        ]
        indexes = [
            models.Index(fields=["situacao", "-semana_inicio"], name="idx_alerta_sit_semana"),
            models.Index(fields=["municipio_codigo", "agravo_codigo"], name="idx_alerta_serie"),
        ]
        ordering = ["-semana_inicio", "-criado_em"]

    def __str__(self):
        return f"{self.rotulo_semana} {self.agravo_nome} - {self.municipio_nome}"

    @property
    def rotulo_semana(self) -> str:
        return f"SE {self.semana_epi:02d}/{self.ano_epi}"

    @property
    def rotulo_situacao(self) -> str:
        return ROTULOS[Situacao(self.situacao)]

    @property
    def excedente(self) -> float:
        return self.observado - self.limite

    def assinatura(self) -> tuple:
        return (
            self.observado,
            round(self.media, 6),
            round(self.desvio, 6),
            round(self.limite, 6),
            self.janela_semanas,
            self.fator_desvio,
        )

    def delete(self, *args, **kwargs):
        # RN03: o alerta nunca é excluído. QuerySet.delete() não passa por aqui; a
        # proteção contra ele é a ausência de rota/admin de exclusão.
        raise PermissionError("Alertas não podem ser excluídos (RN03).")
