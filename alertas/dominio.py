"""Regras de domínio do alerta (PB04): máquina de estados EST-01 e exceções.

Módulo PURO: sem Django, sem banco. Isso permite testar RN03 com tabela de casos
(Definition of Done: "testes de transição de estados aprovados").

Fonte: P2 §6 (EST-01, TR-01..TR-05), UC-10, SEQ-07; P1 RN03, RF005.
Hipóteses do P2 assumidas até validação com gestores (ADR-007):
  QA-01 encerrar direto um alerta Novo é permitido (TR-04);
  QA-02 alerta Encerrado não é reaberto no MVP;
  QA-03 alerta substituto volta a Novo (DP06).
"""
from enum import Enum


class Situacao(str, Enum):
    NOVO = "novo"
    EM_INVESTIGACAO = "em_investigacao"
    ENCERRADO = "encerrado"

    @property
    def rotulo(self) -> str:
        return ROTULOS[self]


ROTULOS = {
    Situacao.NOVO: "Novo",
    Situacao.EM_INVESTIGACAO: "Em investigação",
    Situacao.ENCERRADO: "Encerrado",
}

# TR-02, TR-03, TR-04. Sem retrocesso; Encerrado é estado terminal.
TRANSICOES: dict[Situacao, frozenset[Situacao]] = {
    Situacao.NOVO: frozenset({Situacao.EM_INVESTIGACAO, Situacao.ENCERRADO}),
    Situacao.EM_INVESTIGACAO: frozenset({Situacao.ENCERRADO}),
    Situacao.ENCERRADO: frozenset(),
}


class ErroDeAlerta(Exception):
    """Base das recusas de negócio; a view as converte em mensagem ao gestor."""


class AlertaNaoEncontrado(ErroDeAlerta):
    pass


class UsuarioNaoAutenticado(ErroDeAlerta):
    """RN03/RNF003: nenhuma escrita sem usuário autenticado."""


class AlertaSubstituido(ErroDeAlerta):
    """UC-10 3a: alerta substituído por reprocessamento é somente leitura."""


class TransicaoInvalida(ErroDeAlerta):
    """UC-10 3c."""


class ConflitoDeVersao(ErroDeAlerta):
    """UC-10 3b / R08: outro gestor alterou o alerta depois da leitura."""


class AnomaliaInvalida(ErroDeAlerta):
    """Alerta só existe para observado > limite (RN02, estritamente maior)."""


def transicoes_permitidas(situacao: str, *, substituido: bool = False) -> frozenset[Situacao]:
    if substituido:
        return frozenset()
    return TRANSICOES[Situacao(situacao)]


def validar_transicao(origem: str, destino: str, *, substituido: bool = False) -> Situacao:
    """Valida a mudança de situação e devolve o destino normalizado."""
    if substituido:
        raise AlertaSubstituido("Alerta substituído por reprocessamento é somente leitura.")
    try:
        origem_s, destino_s = Situacao(origem), Situacao(destino)
    except ValueError as exc:
        raise TransicaoInvalida(f"Situação desconhecida: {exc}") from exc
    if origem_s == destino_s:
        raise TransicaoInvalida(f"O alerta já está em “{origem_s.rotulo}”.")
    if destino_s not in TRANSICOES[origem_s]:
        raise TransicaoInvalida(
            f"Transição não permitida: “{origem_s.rotulo}” → “{destino_s.rotulo}”."
        )
    return destino_s
