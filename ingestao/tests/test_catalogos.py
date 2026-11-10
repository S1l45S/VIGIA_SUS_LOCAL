import pytest

from ingestao.services.catalogos import ErroCatalogo, ler_agravos, ler_municipios


def escrever(tmp_path, texto, nome="catalogo.csv"):
    caminho = tmp_path / nome
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def test_ler_municipios_valida_o_codigo_e_normaliza_campos(tmp_path):
    caminho = escrever(tmp_path, "codigo_ibge,nome,uf\n2800308, Aracaju ,se\n")

    assert ler_municipios(caminho) == [
        {"codigo_ibge": "2800308", "nome": "Aracaju", "uf": "SE"}
    ]


def test_ler_municipios_rejeita_digito_verificador_errado(tmp_path):
    caminho = escrever(tmp_path, "codigo_ibge,nome,uf\n2800307,Aracaju,SE\n")

    with pytest.raises(ErroCatalogo, match="Linha 2"):
        ler_municipios(caminho)


def test_ler_municipios_rejeita_codigo_de_seis_digitos(tmp_path):
    caminho = escrever(tmp_path, "codigo_ibge,nome,uf\n280030,Aracaju,SE\n")

    with pytest.raises(ErroCatalogo, match="7 dígitos"):
        ler_municipios(caminho)


def test_ler_municipios_rejeita_codigo_repetido(tmp_path):
    caminho = escrever(
        tmp_path, "codigo_ibge,nome,uf\n2800308,Aracaju,SE\n2800308,Aracaju,SE\n"
    )

    with pytest.raises(ErroCatalogo, match="repetido"):
        ler_municipios(caminho)


def test_ler_municipios_rejeita_coluna_ausente(tmp_path):
    caminho = escrever(tmp_path, "codigo_ibge,nome\n2800308,Aracaju\n")

    with pytest.raises(ErroCatalogo, match="uf"):
        ler_municipios(caminho)


def test_ler_agravos(tmp_path):
    caminho = escrever(tmp_path, "codigo,nome\nA90,Dengue\n")

    assert ler_agravos(caminho) == [{"codigo": "A90", "nome": "Dengue"}]


def test_ler_agravos_rejeita_repetido_e_vazio(tmp_path):
    with pytest.raises(ErroCatalogo, match="repetido"):
        ler_agravos(escrever(tmp_path, "codigo,nome\nA90,Dengue\nA90,Dengue\n"))
    with pytest.raises(ErroCatalogo, match="vazio"):
        ler_agravos(escrever(tmp_path, "codigo,nome\nA90,\n", nome="b.csv"))