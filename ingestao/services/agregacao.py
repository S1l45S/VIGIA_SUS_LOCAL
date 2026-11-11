"""Agregação semanal de notificações, independente da fonte """

from dataclasses import dataclass

import pandas as pd

from ingestao.services.calendario import listar_semanas, semana_iso_equivalente

COLUNAS_CSV = [
    "agravo_codigo",
    "agravo_nome",
    "municipio_codigo",
    "municipio_nome",
    "ano",
    "semana_epidemiologica",
    "contagem",
]


CALENDARIO_DO_CSV = (
    "ano e semana_epidemiologica do CSV seguem a semana ISO da segunda-feira "
    "seguinte ao domingo de início da SE"
)


@dataclass
class ResultadoAgregacao:
    tabela: pd.DataFrame
    notificacoes_contadas: int
    descartes: dict


def agregar_semanal(
    notificacoes, *, agravo_codigo, agravo_nome, municipios, inicio, fim
):
    """Conta notificações por município e semana e completa com zeros

    notificacoes é a tabela canônica, em semana epidemiológica, municipios
    é {codigo_ibge: nome}. A tabela devolvida já usa a semana no formato que o
    CSV de ingestão espera

    Todo município do recorte recebe todas as semanas do período, mesmo sem
    caso, porque o detector não avalia janelas com semana ausente
    """
    semanas = listar_semanas(inicio, fim)
    chaves_validas = [ano * 100 + semana for ano, semana in semanas]

    no_recorte = notificacoes["municipio_codigo"].isin(list(municipios))
    dados = notificacoes[no_recorte]
    descartes = {"municipio_fora_do_recorte": int((~no_recorte).sum())}

    chaves = dados["ano"] * 100 + dados["semana"]
    no_periodo = chaves.isin(chaves_validas)
    descartes["semana_fora_do_periodo"] = int((~no_periodo).sum())
    dados = dados[no_periodo]
    chaves = chaves[no_periodo]

    indice = pd.MultiIndex.from_product(
        [sorted(municipios), chaves_validas],
        names=["municipio_codigo", "chave"],
    )
    if len(dados) == 0:
        completo = pd.Series(0, index=indice, dtype="int64")
    else:
        contagem = (
            pd.DataFrame({"municipio_codigo": dados["municipio_codigo"], "chave": chaves})
            .groupby(["municipio_codigo", "chave"])
            .size()
        )
        completo = contagem.reindex(indice, fill_value=0)

    # A validação do CSV já existente lê ano e semana como semana ISO. O dado
    # do DATASUS é adaptado aqui sem alterar essa regra
    rotulos = {
        ano * 100 + semana: semana_iso_equivalente(ano, semana)
        for ano, semana in semanas
    }
    tabela = completo.rename("contagem").reset_index()
    tabela["ano"] = tabela["chave"].map(lambda chave: rotulos[chave][0]).astype("int64")
    tabela["semana_epidemiologica"] = (
        tabela["chave"].map(lambda chave: rotulos[chave][1]).astype("int64")
    )
    tabela["agravo_codigo"] = agravo_codigo
    tabela["agravo_nome"] = agravo_nome
    tabela["municipio_nome"] = tabela["municipio_codigo"].map(municipios)
    tabela = tabela[COLUNAS_CSV]

    return ResultadoAgregacao(
        tabela=tabela,
        notificacoes_contadas=int(tabela["contagem"].sum()),
        descartes=descartes,
    )


def ultima_semana(notificacoes):
    """Devolve a maior (ano, semana) da tabela canônica."""
    if len(notificacoes) == 0:
        raise ValueError("Nenhuma notificação para definir a última semana.")
    ordenada = notificacoes.sort_values(["ano", "semana"])
    ultima = ordenada.iloc[-1]
    return int(ultima["ano"]), int(ultima["semana"])