"""Fontes de teste servem de semente para a base sintética """

import pandas as pd

from ingestao.fontes.base import COLUNAS_NOTIFICACOES, Notificacoes


class FonteEmMemoria:
    """Devolve notificações montadas na hora, sem rede e sem arquivo."""

    nome = "Fonte em memória"

    def __init__(self, linhas, tipo_semana="semana de teste", descartes=None):
        self._linhas = linhas
        self._tipo_semana = tipo_semana
        self._descartes = descartes or {}

    def obter(self, *, agravo_codigo, anos):
        tabela = pd.DataFrame(self._linhas, columns=COLUNAS_NOTIFICACOES).astype(
            {"municipio_codigo": str, "ano": "int64", "semana": "int64"}
        )
        return Notificacoes(
            fonte=self.nome,
            tipo_semana=self._tipo_semana,
            tabela=tabela,
            linhas_lidas=len(tabela),
            descartes=self._descartes,
        )