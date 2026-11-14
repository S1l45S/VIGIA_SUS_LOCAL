"""Layout do SINAN traduzido para a tabela canônica de notificações

Este módulo conhece as colunas do SINAN e MAIS NADA. Quem baixa os arquivos é
injetado, então ele não importa PySUS nem acessa rede
"""

from collections import Counter
from collections.abc import Callable, Sequence

import pandas as pd

from ingestao.fontes.base import COLUNAS_NOTIFICACOES, Notificacoes
from ingestao.services.calendario import semanas_no_ano
from ingestao.services.ibge import com_dv

COLUNAS_PERMITIDAS = ("ID_MUNICIP", "ID_AGRAVO", "SEM_NOT")
TIPO_SEMANA = "SEM_NOT (semana de notificação)"

# recebe (doença, ano) e devolve DataFrame com colunas do SINAN, arquivos brutos
Baixador = Callable[[str, int], "tuple[pd.DataFrame, list]"]


def _texto(serie):
    """Converte para texto sem o '.0' que aparece quando o número vira float."""
    return serie.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)


def selecionar_colunas(df):
    """Mantém só as colunas permitidas, com nomes em maiúsculas."""
    mapa = {str(coluna).upper(): coluna for coluna in df.columns}
    faltantes = [coluna for coluna in COLUNAS_PERMITIDAS if coluna not in mapa]
    if faltantes:
        raise ValueError(f"Colunas ausentes na fonte: {faltantes}")
    recorte = df[[mapa[coluna] for coluna in COLUNAS_PERMITIDAS]].copy()
    recorte.columns = list(COLUNAS_PERMITIDAS)
    return recorte


def _limite_de_semanas(ano):
    try:
        return semanas_no_ano(int(ano))
    except (ValueError, OverflowError):
        return 0


def normalizar_sinan(df, *, agravo_codigo):
    """Converte linhas do SINAN na tabela canônica

    Devolve tabela, linhas_lidas, descartes, linhas inválidas são contadas
    por motivo e não entram na tabela.
    """
    dados = selecionar_colunas(df)
    linhas_lidas = len(dados)
    descartes = Counter()

    nulos = dados.isna().any(axis=1)
    descartes["campo_nulo"] = int(nulos.sum())
    dados = dados[~nulos]

    outro_agravo = _texto(dados["ID_AGRAVO"]) != agravo_codigo
    descartes["agravo_diferente"] = int(outro_agravo.sum())
    dados = dados[~outro_agravo]

    semana_texto = _texto(dados["SEM_NOT"])
    formato_ok = semana_texto.str.fullmatch(r"\d{6}")
    descartes["semana_formato_invalido"] = int((~formato_ok).sum())
    dados = dados[formato_ok]
    semana_texto = semana_texto[formato_ok]

    ano = semana_texto.str[:4].astype("int64")
    semana = semana_texto.str[4:].astype("int64")
    limites = ano.map({valor: _limite_de_semanas(valor) for valor in ano.unique()})
    inexistente = (semana < 1) | (semana > limites)
    descartes["semana_inexistente"] = int(inexistente.sum())
    dados = dados[~inexistente]
    ano = ano[~inexistente]
    semana = semana[~inexistente]

    municipio_texto = _texto(dados["ID_MUNICIP"])
    conversao = {}
    for valor in municipio_texto.unique():
        try:
            conversao[valor] = com_dv(valor)
        except ValueError:
            conversao[valor] = None
    codigos = municipio_texto.map(conversao)
    invalido = codigos.isna()
    descartes["municipio_invalido"] = int(invalido.sum())

    tabela = pd.DataFrame({
        "municipio_codigo": codigos[~invalido].astype(str),
        "ano": ano[~invalido].astype("int64"),
        "semana": semana[~invalido].astype("int64"),
    })[COLUNAS_NOTIFICACOES].reset_index(drop=True)

    return tabela, linhas_lidas, dict(descartes)


class FonteSinan:
    """Fonte de notificações baseada em arquivos do SINAN."""

    nome = "SINAN/DATASUS"

    def __init__(self, doenca, baixar):
        self._doenca = doenca
        self._baixar = baixar

    def obter(self, *, agravo_codigo: str, anos: Sequence[int]) -> Notificacoes:
        tabelas = []
        brutos = []
        linhas_lidas = 0
        descartes = Counter()

        for ano in anos:
            df, arquivos = self._baixar(self._doenca, ano)
            tabela, lidas, motivos = normalizar_sinan(df, agravo_codigo=agravo_codigo)
            tabelas.append(tabela)
            brutos.extend(arquivos)
            linhas_lidas += lidas
            descartes.update(motivos)

        if not tabelas:
            raise ValueError("Informe ao menos um ano.")

        tabela = pd.concat(tabelas, ignore_index=True).astype(
            {"ano": "int64", "semana": "int64"}
        )
        return Notificacoes(
            fonte=self.nome,
            tipo_semana=TIPO_SEMANA,
            tabela=tabela,
            linhas_lidas=linhas_lidas,
            descartes=dict(descartes),
            arquivos_brutos=brutos,
        )