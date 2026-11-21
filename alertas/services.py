"""Casos de uso do alerta: emitir (UC-06), consultar (UC-08/09), atualizar situação (UC-10)."""

import logging
from dataclasses import dataclass, field
from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from django_mongodb_backend.transaction import atomic

from .contratos import AnomaliaDetectada
from .dominio import (
    AlertaNaoEncontrado,
    AnomaliaInvalida,
    ConflitoDeVersao,
    Situacao,
    UsuarioNaoAutenticado,
    validar_transicao,
)
from .models import Alerta, RegistroDeSituacao

log = logging.getLogger(__name__)
FILTRO_ABERTOS = "abertos"
FILTRO_TODOS = "todos"


@dataclass
class ResultadoEmissao:
    criados: list = field(default_factory=list)
    substituidos: list = field(default_factory=list)  # ids dos alertas antigos
    inalterados: list = field(default_factory=list)
    obsoletos: list = field(default_factory=list)  # vigentes cuja semana deixou de ser anomalia

    @property
    def total_criados(self):
        return len(self.criados)


def _registro_sistema(texto: str) -> RegistroDeSituacao:
    return RegistroDeSituacao(
        situacao=Situacao.NOVO.value,
        em=timezone.now(),
        origem="sistema",
        usuario_nome="sistema",
        observacao=texto,
    )


def _novo_alerta(a: AnomaliaDetectada, observacao: str, substitui=None) -> Alerta:
    return Alerta(
        agravo_codigo=a.agravo_codigo,
        agravo_nome=a.agravo_nome,
        municipio_codigo=a.municipio_codigo,
        municipio_nome=a.municipio_nome,
        semana_inicio=a.semana_inicio,
        ano_epi=a.ano_epi,
        semana_epi=a.semana_epi,
        observado=a.observado,
        media=a.media,
        desvio=a.desvio,
        limite=a.limite,
        janela_semanas=a.janela_semanas,
        fator_desvio=a.fator_desvio,
        resultado_id=a.resultado_id,
        carga_id=a.carga_id,
        situacao=Situacao.NOVO.value,
        substitui=substitui,
        criado_em=timezone.now(),
        historico=[_registro_sistema(observacao)],
    )


def _vigente(a: AnomaliaDetectada):
    return Alerta.objects.filter(
        agravo_codigo=a.agravo_codigo,
        municipio_codigo=a.municipio_codigo,
        semana_inicio=a.semana_inicio,
        substituido=False,
    ).first()


def emitir_alerta(a: AnomaliaDetectada) -> tuple[Alerta, str]:
    """Emite o alerta de uma anomalia. Idempotente e sem duplicidade.

    Retorna (alerta_vigente, "criado" | "substituido" | "inalterado"):
      - não existe vigente              -> cria (TR-01);
      - vigente com os mesmos insumos   -> nada muda (reprocesso idêntico, RNF005);
      - vigente com insumos diferentes  -> o antigo vira substituído (TR-05, mantém
        situação e histórico) e o novo nasce em Novo (QA-03/DP06).
    """
    if not a.observado > a.limite:  # RN02: estritamente maior
        raise AnomaliaInvalida(
            f"Observado ({a.observado}) não excede o limite ({a.limite}); não gera alerta."
        )

    existente = _vigente(a)
    if existente and existente.assinatura() == a.assinatura():
        return existente, "inalterado"

    try:
        with atomic():
            substitui = None
            if existente:
                n = Alerta.objects.filter(pk=existente.pk, substituido=False).update(
                    substituido=True
                )
                if n == 0:
                    raise IntegrityError("alerta vigente mudou durante a emissão")
                substitui = existente.pk
            if existente:
                obs = (
                    f"Reprocessamento: substitui o alerta {existente.pk} "
                    f"(janela {a.janela_semanas} semanas, limite μ+{a.fator_desvio}σ)."
                )
            else:
                obs = (
                    f"Alerta emitido pela detecção "
                    f"(janela {a.janela_semanas} semanas, limite μ+{a.fator_desvio}σ)."
                )
            novo = _novo_alerta(a, obs, substitui)
            novo.save()
            if existente:
                Alerta.objects.filter(pk=existente.pk).update(substituido_por=novo.pk)
    except IntegrityError:
        # Corrida fora de transação externa: o índice único parcial barrou a duplicata.
        # Dentro da transação da carga, o erro aborta a carga inteira (comportamento desejado).
        vencedor = _vigente(a)
        if vencedor is None:
            raise
        return vencedor, "inalterado"
    return novo, ("substituido" if existente else "criado")


def emitir_alertas(anomalias) -> ResultadoEmissao:
    res = ResultadoEmissao()
    for a in anomalias:
        alerta, status = emitir_alerta(a)
        if status == "criado":
            res.criados.append(alerta)
        elif status == "substituido":
            res.criados.append(alerta)
            res.substituidos.append(alerta.substitui)
        else:
            res.inalterados.append(alerta)
    return res


# ------------------------------------------------------------------ consulta
def obter_alerta(pk) -> Alerta:
    try:
        return Alerta.objects.get(pk=pk)
    except (Alerta.DoesNotExist, ValidationError, ValueError, TypeError) as exc:
        raise AlertaNaoEncontrado("Alerta não encontrado.") from exc


def listar_alertas(
    *,
    situacao: str = FILTRO_ABERTOS,
    municipio: str = "",
    agravo: str = "",
    inicio: date | None = None,
    fim: date | None = None,
):
    """Painel: semana mais recente primeiro. Padrão: só abertos e vigentes.

    "Todos" e uma situação específica incluem os substituídos, que continuam
    listados com marca (P2 UC-08 4a). ``municipio``/``agravo`` são códigos.
    """
    qs = Alerta.objects.all()
    if situacao == FILTRO_ABERTOS or not situacao:
        qs = qs.filter(substituido=False).exclude(situacao=Situacao.ENCERRADO.value)
    elif situacao != FILTRO_TODOS:
        qs = qs.filter(situacao=situacao)
    if municipio:
        qs = qs.filter(municipio_codigo=municipio)
    if agravo:
        qs = qs.filter(agravo_codigo=agravo)
    if inicio:
        qs = qs.filter(semana_inicio__gte=inicio)
    if fim:
        qs = qs.filter(semana_inicio__lte=fim)
    return qs.order_by("-semana_inicio", "-criado_em")


def contadores() -> dict:
    vig = Alerta.objects.filter(substituido=False)
    return {s.value: vig.filter(situacao=s.value).count() for s in Situacao}


# ----------------------------------------------------- situação (RF005, UC-10)
_MSG_CONFLITO = "Este alerta foi alterado por outra pessoa. Recarregue a página e tente de novo."


def alterar_situacao(
    *, alerta_id, nova_situacao: str, versao_lida: int, usuario, observacao: str = ""
) -> Alerta:
    """Muda a situação (SEQ-07). Ordem: sessão -> existe -> vigente/transição -> versão.

    O histórico é de acréscimo: a gravação só vale se a versão no banco ainda for
    ``versao_lida`` (atualização atômica de um documento). Em recusa, nada é gravado.
    """
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        raise UsuarioNaoAutenticado("Sessão autenticada obrigatória.")

    alerta = obter_alerta(alerta_id)
    destino = validar_transicao(alerta.situacao, nova_situacao, substituido=alerta.substituido)
    if alerta.versao != versao_lida:
        raise ConflitoDeVersao(_MSG_CONFLITO)

    registro = RegistroDeSituacao(
        situacao=destino.value,
        situacao_anterior=alerta.situacao,
        em=timezone.now(),
        origem="gestor",
        usuario_id=str(usuario.pk),
        usuario_nome=usuario.get_username(),
        observacao=(observacao or "").strip()[:500],
    )
    atualizados = Alerta.objects.filter(
        pk=alerta.pk, versao=versao_lida, substituido=False
    ).update(
        situacao=destino.value,
        versao=versao_lida + 1,
        historico=[*alerta.historico, registro],
    )
    if atualizados != 1:
        raise ConflitoDeVersao(_MSG_CONFLITO)
    alerta.refresh_from_db()
    return alerta
