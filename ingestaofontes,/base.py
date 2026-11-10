"""Contrato comum a toda fonte de notificações

O resto da ingestão conhece só este módulo. Cada fonte traduz o seu formato para a tabela abaixo.
"""

from dataclasses import dataclass, field
from typing import Protocol, Sequence

import pandas as pd
from pandas.api.types import is_integer_dtype, is_string_dtype

from ingestao.services.calendario import semanas_no_ano
from ingestao.services.ibge import com_dv

# Uma linha por notificação, ou sea, município com 7 dígitos, ano e semana epidemiológica.
COLUNAS_NOTIFICACOES = ["municipio_codigo", "ano", "semana"]


class ErroContratoFonte(Exception):
    """A fonte devolveu dados fora do contrato."""


@dataclass
class Notificacoes:
    fonte: str
    tipo_semana: str
    tabela: pd.DataFrame
    linhas_lidas: int
    descartes: dict = field(default_factory=dict)
    arquivos_brutos: list = field(default_factory=list)


class FonteDeNotificacoes(Protocol):
    """aualquer objeto com este método pode alimentar a ingestão"""

    def obter(
        self, *, agravo_codigo: str, anos: Sequence[int]
    ) -> Notificacoes: ...


def verificar_notificacoes(notificacoes):
    """confere as pos condições que toda fonte promete cumprir"""
    if not notificacoes.fonte or not notificacoes.tipo_semana:
        raise ErroContratoFonte("A fonte deve informar nome e tipo de semana.")

    tabela = notificacoes.tabela
    if list(tabela.columns) != COLUNAS_NOTIFICACOES:
        raise ErroContratoFonte(
            f"Colunas esperadas {COLUNAS_NOTIFICACOES}, recebidas {list(tabela.columns)}."
        )
    if not is_string_dtype(tabela["municipio_codigo"]):
        raise ErroContratoFonte("municipio_codigo deve ser texto.")
    for coluna in ("ano", "semana"):
        if not is_integer_dtype(tabela[coluna]):
            raise ErroContratoFonte(f"{coluna} deve ser inteiro.")
    if notificacoes.linhas_lidas < len(tabela):
        raise ErroContratoFonte("Há mais notificações aceitas do que linhas lidas.")

    for codigo in tabela["municipio_codigo"].unique():
        if len(str(codigo)) != 7:
            raise ErroContratoFonte(f"Código de município sem 7 dígitos: {codigo}.")
        try:
            com_dv(codigo)
        except ValueError as erro:
            raise ErroContratoFonte(str(erro)) from erro

    for ano, semana in tabela[["ano", "semana"]].drop_duplicates().itertuples(index=False):
        try:
            existe = 1 <= semana <= semanas_no_ano(int(ano))
        except (ValueError, OverflowError):
            existe = False
        if not existe:
            raise ErroContratoFonte(f"Semana inexistente: {ano}/{semana}.")