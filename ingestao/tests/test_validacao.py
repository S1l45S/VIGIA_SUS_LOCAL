from datetime import date
from io import StringIO

import pytest

from ingestao.services.validacao import (
    COLUNAS_OBRIGATORIAS,
    ErroEsquemaCSV,
    validar_estrutura,
    validar_registro,
)


CABECALHO = (
    "agravo_codigo,agravo_nome,municipio_codigo,municipio_nome,"
    "ano,semana_epidemiologica,contagem"
)
REGISTRO_VALIDO = {
    "agravo_codigo": " AGR001 ",
    "agravo_nome": "Agravo demonstrativo",
    "municipio_codigo": " 2800308 ",
    "municipio_nome": "Aracaju",
    "ano": "2025",
    "semana_epidemiologica": "1",
    "contagem": "12",
}


def test_validar_estrutura_retorna_leitor_csv():
    leitor = validar_estrutura(StringIO(f"{CABECALHO}\nAGR001,Agravo,2800308,Aracaju,2025,1,12\n"))

    assert next(leitor)["agravo_codigo"] == "AGR001"


def test_validar_estrutura_reposiciona_arquivo_antes_da_leitura():
    arquivo = StringIO(f"{CABECALHO}\nAGR001,Agravo,2800308,Aracaju,2025,1,12\n")
    arquivo.read()

    leitor = validar_estrutura(arquivo)

    assert len(list(leitor)) == 1


def test_validar_estrutura_rejeita_cabecalho_vazio():
    with pytest.raises(ErroEsquemaCSV, match="Colunas obrigatórias ausentes"):
        validar_estrutura(StringIO(""))


def test_validar_estrutura_rejeita_colunas_obrigatorias_ausentes():
    arquivo = StringIO("agravo_codigo,ano\nAGR001,2025\n")

    with pytest.raises(ErroEsquemaCSV, match="Colunas obrigatórias ausentes"):
        validar_estrutura(arquivo)


def test_validar_estrutura_rejeita_coluna_com_dado_pessoal():
    arquivo = StringIO(f"{CABECALHO},cpf\n")

    with pytest.raises(ErroEsquemaCSV, match="Colunas proibidas.*cpf"):
        validar_estrutura(arquivo)


def test_validar_estrutura_rejeita_cabecalho_duplicado():
    cabecalho_duplicado = f"{CABECALHO},ano\n"

    with pytest.raises(ErroEsquemaCSV, match="Cabeçalhos duplicados"):
        validar_estrutura(StringIO(cabecalho_duplicado))


def test_colunas_obrigatorias_estao_cobertas_pelo_cabecalho_de_referencia():
    assert set(CABECALHO.split(",")) == COLUNAS_OBRIGATORIAS


def test_validar_registro_normaliza_campos_e_calcula_semana():
    registro = validar_registro(REGISTRO_VALIDO)

    assert registro == {
        "agravo_codigo": "AGR001",
        "municipio_codigo": "2800308",
        "semana_inicio": date(2024, 12, 30),
        "semana_ord": (date(2024, 12, 30) - date(1970, 1, 5)).days // 7,
        "ano": 2025,
        "semana_epidemiologica": 1,
        "quantidade": 12,
    }


@pytest.mark.parametrize(
    ("campo", "valor", "mensagem"),
    [
        ("agravo_codigo", "   ", "Agravo ou município não informado"),
        ("municipio_codigo", "", "Agravo ou município não informado"),
        ("ano", "abc", "invalid literal"),
        ("ano", "1999", "Ano fora do intervalo"),
        ("ano", "2101", "Ano fora do intervalo"),
        ("semana_epidemiologica", "0", "Semana epidemiológica inválida"),
        ("semana_epidemiologica", "54", "Semana epidemiológica inválida"),
        ("contagem", "-1", "Contagem negativa"),
        ("contagem", "um", "invalid literal"),
    ],
)
def test_validar_registro_rejeita_valores_invalidos(campo, valor, mensagem):
    linha = {**REGISTRO_VALIDO, campo: valor}

    with pytest.raises(ValueError, match=mensagem):
        validar_registro(linha)


def test_validar_registro_rejeita_semana_iso_inexistente():
    linha = {
        **REGISTRO_VALIDO,
        "ano": "2025",
        "semana_epidemiologica": "53",
    }

    with pytest.raises(ValueError, match="Invalid week"):
        validar_registro(linha)
