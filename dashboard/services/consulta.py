from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Sum

from deteccao.models import ResultadoDeteccao
from dominio.models import Agravo, Municipio
from ingestao.models import CargaDeDados, RegistroSemanal
from ingestao.services.calendario import semana_da_data

SEMANAS_PERIODO_PADRAO = 52
JANELA_MINIMA = 8


def formatar_decimal(valor):
    """Formata com uma casa decimal e vírgula (padrão brasileiro)."""
    if valor is None:
        return "—"
    return f"{valor:.1f}".replace(".", ",")


def rotulo_semana(semana_inicio):
    """Rótulo 'SE nn/aaaa' calculado a partir da segunda-feira armazenada.

    ``semana_inicio`` é a segunda-feira da semana; a SE começa no domingo
    anterior. Calcular a partir da data evita depender do par ano/semana ISO
    gravado, que pode divergir da SE real em alguns anos.
    """
    ano, semana = semana_da_data(semana_inicio - timedelta(days=1))
    return f"SE {semana:02d}/{ano}"


@dataclass(frozen=True)
class PontoSerie:
    semana_inicio: date
    rotulo: str
    observado: int
    media_movel: float | None
    limite_superior: float | None
    anomalia: bool

    @property
    def media_formatada(self):
        return formatar_decimal(self.media_movel)

    @property
    def limite_formatado(self):
        return formatar_decimal(self.limite_superior)


@dataclass(frozen=True)
class SerieTemporal:
    municipio_codigo: str
    agravo_codigo: str
    inicio: date | None
    fim: date | None
    pontos: tuple

    @property
    def vazia(self):
        """Sem linhas ou só com zeros: não há o que desenhar (RF002)."""
        return not any(ponto.observado for ponto in self.pontos)

    @property
    def total_notificacoes(self):
        return sum(ponto.observado for ponto in self.pontos)

    @property
    def semanas_em_anomalia(self):
        return sum(1 for ponto in self.pontos if ponto.anomalia)

    @property
    def semanas_sem_referencia(self):
        return sum(1 for ponto in self.pontos if ponto.limite_superior is None)

    @property
    def sem_banda(self):
        """Nenhuma semana do período tem média e limite (histórico curto)."""
        return bool(self.pontos) and self.semanas_sem_referencia == len(self.pontos)

    def para_grafico(self):
        """Estrutura serializável consumida por ``static/.../grafico.js``."""
        return {
            "rotulos": [p.rotulo for p in self.pontos],
            "observado": [p.observado for p in self.pontos],
            "media_movel": [
                None if p.media_movel is None else round(p.media_movel, 2)
                for p in self.pontos
            ],
            "limite_superior": [
                None if p.limite_superior is None else round(p.limite_superior, 2)
                for p in self.pontos
            ],
            "anomalia": [p.anomalia for p in self.pontos],
        }


def listar_municipios():
    """Municípios ativos do catálogo: [(codigo_ibge, nome)]."""
    return list(
        Municipio.objects.filter(ativo=True)
        .order_by("nome")
        .values_list("codigo_ibge", "nome")
    )


def listar_agravos():
    """Agravos ativos do catálogo: [(codigo, nome)]."""
    return list(
        Agravo.objects.filter(ativo=True).order_by("nome").values_list("codigo", "nome")
    )


def _maior_total(queryset, campo):
    """Código com maior soma de notificações (empate: menor código)."""
    linha = (
        queryset.values(campo)
        .annotate(total=Sum("quantidade"))
        .order_by("-total", campo)
        .first()
    )
    return linha[campo] if linha else None


def selecao_inicial():
    """Seleção inicial do RF002: (município, agravo) de maior volume.

    Primeiro o município com mais notificações no período carregado; depois,
    dentro dele, o agravo com mais notificações. Devolve ``None`` quando não
    há nenhum registro carregado.
    """
    municipio = _maior_total(RegistroSemanal.objects.all(), "municipio_codigo")
    if municipio is None:
        return None
    agravo = _maior_total(
        RegistroSemanal.objects.filter(municipio_codigo=municipio),
        "agravo_codigo",
    )
    return municipio, agravo


def resolver_periodo(municipio, agravo, inicio=None, fim=None):
    """Completa o período informado com o padrão: últimas 52 semanas.

    O padrão termina na semana mais recente carregada para a série. Se a
    série não tem registros, devolve o período como veio (pode ser None).
    """
    if inicio is not None and fim is not None:
        return inicio, fim

    mais_recente = (
        RegistroSemanal.objects.filter(municipio_codigo=municipio, agravo_codigo=agravo)
        .order_by("-semana_inicio")
        .values_list("semana_inicio", flat=True)
        .first()
    )
    if mais_recente is None:
        return inicio, fim

    fim = fim or mais_recente
    inicio = inicio or fim - timedelta(weeks=SEMANAS_PERIODO_PADRAO - 1)
    return inicio, fim


def montar_serie(municipio, agravo, inicio, fim):
    """Monta a série semanal com observado, média móvel e limite."""
    filtro = {"municipio_codigo": municipio, "agravo_codigo": agravo}
    if inicio is not None:
        filtro["semana_inicio__gte"] = inicio
    if fim is not None:
        filtro["semana_inicio__lte"] = fim

    registros = list(
        RegistroSemanal.objects.filter(**filtro)
        .order_by("semana_inicio")
        .values_list("semana_inicio", "quantidade")
    )
    referencias = {
        r["semana_inicio"]: r
        for r in ResultadoDeteccao.objects.filter(**filtro).values(
            "semana_inicio", "media_movel", "limite_superior", "anomalia"
        )
    }

    pontos = []
    for semana_inicio, quantidade in registros:
        ref = referencias.get(semana_inicio)
        pontos.append(
            PontoSerie(
                semana_inicio=semana_inicio,
                rotulo=rotulo_semana(semana_inicio),
                observado=quantidade,
                media_movel=ref["media_movel"] if ref else None,
                limite_superior=ref["limite_superior"] if ref else None,
                anomalia=bool(ref and ref["anomalia"]),
            )
        )

    return SerieTemporal(
        municipio_codigo=municipio,
        agravo_codigo=agravo,
        inicio=inicio,
        fim=fim,
        pontos=tuple(pontos),
    )


def ultima_carga_aceita():
    """Última carga aceita (para informar a atualidade dos dados)."""
    return CargaDeDados.objects.filter(status="ACEITA").order_by("-criada_em").first()
