"""Leitura e validação dos catálogos de município e agravo."""

import csv

from ingestao.services.ibge import com_dv

COLUNAS_MUNICIPIOS = ("codigo_ibge", "nome", "uf")
COLUNAS_AGRAVOS = ("codigo", "nome")


class ErroCatalogo(Exception):
    pass


def _ler(caminho, colunas):
    with open(caminho, "r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        faltantes = set(colunas) - set(leitor.fieldnames or [])
        if faltantes:
            raise ErroCatalogo(
                f"Colunas ausentes em {caminho}: {sorted(faltantes)}"
            )
        return list(leitor)


def ler_municipios(caminho):
    """Devolve a lista de municípios, com o código IBGE já conferido """
    municipios = []
    vistos = set()
    for numero, linha in enumerate(_ler(caminho, COLUNAS_MUNICIPIOS), start=2):
        try:
            codigo = com_dv(linha["codigo_ibge"])
        except ValueError as erro:
            raise ErroCatalogo(f"Linha {numero}: {erro}") from erro
        if len(linha["codigo_ibge"].strip()) != 7:
            raise ErroCatalogo(f"Linha {numero}: informe o código com 7 dígitos.")
        if codigo in vistos:
            raise ErroCatalogo(f"Linha {numero}: código repetido {codigo}.")
        vistos.add(codigo)
        nome = linha["nome"].strip()
        uf = linha["uf"].strip().upper()
        if not nome or len(uf) != 2:
            raise ErroCatalogo(f"Linha {numero}: nome ou UF inválido.")
        municipios.append({"codigo_ibge": codigo, "nome": nome, "uf": uf})
    return municipios


def ler_agravos(caminho):
    """Devolve a lista de agravos."""
    agravos = []
    vistos = set()
    for numero, linha in enumerate(_ler(caminho, COLUNAS_AGRAVOS), start=2):
        codigo = linha["codigo"].strip()
        nome = linha["nome"].strip()
        if not codigo or not nome:
            raise ErroCatalogo(f"Linha {numero}: código ou nome vazio.")
        if codigo in vistos:
            raise ErroCatalogo(f"Linha {numero}: código repetido {codigo}.")
        vistos.add(codigo)
        agravos.append({"codigo": codigo, "nome": nome})
    return agravos