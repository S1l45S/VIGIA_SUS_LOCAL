import csv

from datetime import date


COLUNAS_OBRIGATORIAS = {
    "agravo_codigo",
    "agravo_nome",
    "municipio_codigo",
    "municipio_nome",
    "ano",
    "semana_epidemiologica",
    "contagem",
}

COLUNAS_PROIBIDAS = {
    "cpf",
    "nome_paciente",
    "nome",
    "cartao_sus",
    "cns",
    "data_nascimento",
}


class ErroEsquemaCSV(Exception):
    pass


def validar_estrutura(arquivo):

    arquivo.seek(0)

    leitor = csv.DictReader(arquivo)

    cabecalho = set(leitor.fieldnames or [])

    proibidas = cabecalho & COLUNAS_PROIBIDAS

    if proibidas:
        raise ErroEsquemaCSV(
            f"Colunas proibidas encontradas: {sorted(proibidas)}"
        )

    faltantes = COLUNAS_OBRIGATORIAS - cabecalho

    if faltantes:
        raise ErroEsquemaCSV(
            f"Colunas obrigatórias ausentes: {sorted(faltantes)}"
        )

    if len(cabecalho) != len(leitor.fieldnames or []):
        raise ErroEsquemaCSV(
            "Cabeçalhos duplicados."
        )

    return leitor


def validar_registro(linha):

    agravo = linha["agravo_codigo"].strip()
    municipio = linha["municipio_codigo"].strip()

    if not agravo or not municipio:
        raise ValueError("Agravo ou município não informado.")

    ano = int(linha["ano"])
    semana = int(linha["semana_epidemiologica"])
    quantidade = int(linha["contagem"])

    if ano < 2000 or ano > 2100:
        raise ValueError("Ano fora do intervalo permitido.")

    if not 1 <= semana <= 53:
        raise ValueError("Semana epidemiológica inválida.")

    if quantidade < 0:
        raise ValueError("Contagem negativa.")

    inicio = date.fromisocalendar(
        ano,
        semana,
        1
    )

    semana_ord = (
        inicio - date(1970, 1, 5)
    ).days // 7

    return {
        "agravo_codigo": agravo,
        "municipio_codigo": municipio,
        "semana_inicio": inicio,
        "semana_ord": semana_ord,
        "ano": ano,
        "semana_epidemiologica": semana,
        "quantidade": quantidade,
    }