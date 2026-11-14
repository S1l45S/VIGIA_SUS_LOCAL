"""Download do SINAN pelo PySUS.

É a única parte da ingestão que usa rede. Devolve só as colunas permitidas,
para que o dado completo não circule pelo sistem. Isolamos ela pois a API muda

"""

from pathlib import Path

import pandas as pd

from ingestao.fontes.sinan import COLUNAS_PERMITIDAS, selecionar_colunas
from ingestao.services.saida import sha256_arquivo


def _como_lista(resultado):
    if isinstance(resultado, (str, Path)):
        return [resultado]
    if hasattr(resultado, "paths"):
        return list(resultado.paths)
    return list(resultado)


def _ler_parquet(caminho):
    import pyarrow.parquet as pq

    nomes = pq.read_schema(caminho).names
    mapa = {nome.upper(): nome for nome in nomes}
    faltantes = [c for c in COLUNAS_PERMITIDAS if c not in mapa]
    if faltantes:
        raise ValueError(f"Colunas ausentes em {caminho}: {faltantes}")
    return pd.read_parquet(
        caminho, columns=[mapa[coluna] for coluna in COLUNAS_PERMITIDAS]
    )


def baixar_sinan_pysus(doenca, ano):
    """baixa um ano e devolve (DataFrame, lista de arquivos brutos)"""
    from pysus import ftp

    # pysus.sinan (obsoleta) baixou dois arquivos com o mesmo nome e a leitura
    # falhou. A origem FTP devolve um arquivo por ano.
    resultado = ftp.sinan(disease=doenca, year=ano)
    if isinstance(resultado, pd.DataFrame):
        return selecionar_colunas(resultado), []

    quadros = []
    brutos = []
    for caminho in _como_lista(resultado):
        quadros.append(selecionar_colunas(_ler_parquet(caminho)))
        if Path(caminho).is_file():
            brutos.append({
                "arquivo": Path(caminho).name,
                "ano": ano,
                "sha256": sha256_arquivo(caminho),
            })
    if not quadros:
        raise ValueError(f"Nenhum arquivo baixado para {doenca} em {ano}.")
    return pd.concat(quadros, ignore_index=True), brutos