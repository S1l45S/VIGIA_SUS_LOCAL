"""Calendário epidemiológico brasileiro

A semana epidemiológica (SE) vai de domingo a sábado. A SE 1 de cada ano é a
primeira semana que tem pelo menos quatro dias em janeiro, o que equivale a
dizer que ela contém o dia 4 de janeiro. Não é a semana ISO, que começa na
segunda-feira.
"""

import re
from datetime import date, timedelta

DIAS_POR_SEMANA = 7
DOMINGO_DE_REFERENCIA = date(1970, 1, 4)


def inicio_se1(ano):
    """devolve o domingo em que começa a SE 1 do ano"""
    quatro_de_janeiro = date(ano, 1, 4)
    dias_desde_domingo = (quatro_de_janeiro.weekday() + 1) % 7
    return quatro_de_janeiro - timedelta(days=dias_desde_domingo)


def semanas_no_ano(ano):
    """devolve quantas semanas epidemiológicas o ano tem, 52 ou 53"""
    return (inicio_se1(ano + 1) - inicio_se1(ano)).days // DIAS_POR_SEMANA


def inicio_semana_epidemiologica(ano, semana):
    """devolve o domingo em que começa a semana epidemiológica informada"""
    if not 1 <= semana <= semanas_no_ano(ano):
        raise ValueError(
            f"Semana epidemiológica inexistente no ano {ano}: {semana}."
        )
    return inicio_se1(ano) + timedelta(weeks=semana - 1)


def ordinal_semana(inicio):
    """Numero sequencial da semana, contado a partir de 04/01/1970"""
    return (inicio - DOMINGO_DE_REFERENCIA).days // DIAS_POR_SEMANA


def semana_da_data(data):
    """devolve  o par (ano, semana) da SE que contem a data"""
    for ano in (data.year + 1, data.year, data.year - 1):
        primeiro_domingo = inicio_se1(ano)
        if primeiro_domingo <= data:
            semana = (data - primeiro_domingo).days // DIAS_POR_SEMANA + 1
            return ano, semana
    raise ValueError(f"Data fora do intervalo suportado: {data}.")


def deslocar_semana(ano, semana, quantidade):
    """anda a quantidade semanas, para frente ou para tras"""
    inicio = inicio_semana_epidemiologica(ano, semana)
    return semana_da_data(inicio + timedelta(weeks=quantidade))


def listar_semanas(inicio, fim):
    """lista as tuplas (ano, semana) de inicio até fim, ambos inclusos"""
    data_inicial = inicio_semana_epidemiologica(*inicio)
    data_final = inicio_semana_epidemiologica(*fim)
    if data_inicial > data_final:
        raise ValueError("O início do período é posterior ao fim.")
    quantidade = (data_final - data_inicial).days // DIAS_POR_SEMANA
    return [
        semana_da_data(data_inicial + timedelta(weeks=indice))
        for indice in range(quantidade + 1)
    ]


def ano_semana_de_texto(texto):
    """Converte AAAASS, tipo '202501', em (ano, semana)"""
    texto = str(texto).strip()
    if not re.fullmatch(r"\d{6}", texto):
        raise ValueError("Informe a semana no formato AAAASS, como 202501.")
    ano, semana = int(texto[:4]), int(texto[4:])
    inicio_semana_epidemiologica(ano, semana)
    return ano, semana