import pandas as pd
import pytest

from ingestao.fontes.base import COLUNAS_NOTIFICACOES, verificar_notificacoes
from ingestao.fontes.sinan import (
    FonteSinan,
    TIPO_SEMANA,
    normalizar_sinan,
    selecionar_colunas,
)


def bruto(*linhas, extras=None):
    """DataFrame no layout do SINAN: (ID_MUNICIP, ID_AGRAVO, SEM_NOT)."""
    dados = {
        "ID_MUNICIP": [linha[0] for linha in linhas],
        "ID_AGRAVO": [linha[1] for linha in linhas],
        "SEM_NOT": [linha[2] for linha in linhas],
    }
    dados.update(extras or {})
    return pd.DataFrame(dados)


def normalizar(df):
    return normalizar_sinan(df, agravo_codigo="A90")


def test_seis_digitos_viram_sete_e_a_tabela_sai_no_formato_canonico():
    tabela, lidas, descartes = normalizar(bruto(("280030", "A90", "202502")))

    assert list(tabela.columns) == COLUNAS_NOTIFICACOES
    assert tabela.iloc[0].tolist() == ["2800308", 2025, 2]
    assert lidas == 1
    assert sum(descartes.values()) == 0


def test_agravo_diferente_e_descartado_e_contado():
    tabela, _, descartes = normalizar(
        bruto(("280030", "A90", "202501"), ("280030", "A92", "202501"))
    )

    assert len(tabela) == 1
    assert descartes["agravo_diferente"] == 1


def test_campos_nulos_sao_descartados_e_contados():
    tabela, _, descartes = normalizar(
        bruto(("280030", "A90", None), (None, "A90", "202501"))
    )

    assert len(tabela) == 0
    assert descartes["campo_nulo"] == 2


@pytest.mark.parametrize("semana", ["2025", "abc123", "2025-1"])
def test_semana_com_formato_invalido_e_descartada(semana):
    tabela, _, descartes = normalizar(bruto(("280030", "A90", semana)))

    assert len(tabela) == 0
    assert descartes["semana_formato_invalido"] == 1


@pytest.mark.parametrize("semana", ["202453", "202500", "202554", "000001"])
def test_semana_inexistente_e_descartada(semana):
    tabela, _, descartes = normalizar(bruto(("280030", "A90", semana)))

    assert len(tabela) == 0
    assert descartes["semana_inexistente"] == 1


def test_codigo_de_municipio_invalido_e_descartado():
    tabela, _, descartes = normalizar(
        bruto(("28003", "A90", "202501"), ("2800307", "A90", "202501"))
    )

    assert len(tabela) == 0
    assert descartes["municipio_invalido"] == 2


def test_coluna_ausente_na_fonte_levanta_erro():
    df = pd.DataFrame({"ID_MUNICIP": ["280030"], "SEM_NOT": ["202501"]})

    with pytest.raises(ValueError, match="ID_AGRAVO"):
        normalizar(df)


def test_colunas_fora_da_lista_permitida_nao_chegam_a_tabela():
    df = bruto(
        ("280030", "A90", "202501"),
        extras={"NM_PACIENT": ["MARIA"], "DT_NASC": ["1990-01-01"]},
    )

    assert list(selecionar_colunas(df).columns) == ["ID_MUNICIP", "ID_AGRAVO", "SEM_NOT"]
    tabela, _, _ = normalizar(df)
    assert list(tabela.columns) == COLUNAS_NOTIFICACOES


def test_nomes_em_minusculas_e_numeros_float_sao_aceitos():
    minusculas = bruto(("280030", "A90", "202501")).rename(columns=str.lower)
    flutuantes = pd.DataFrame(
        {"ID_MUNICIP": [280030.0], "ID_AGRAVO": ["A90"], "SEM_NOT": [202501.0]}
    )

    assert len(normalizar(minusculas)[0]) == 1
    assert len(normalizar(flutuantes)[0]) == 1


def baixador(por_ano, arquivos=None):
    def baixar(doenca, ano):
        return por_ano[ano], (arquivos or {}).get(ano, [])
    return baixar


def test_fonte_junta_anos_soma_linhas_e_descartes_e_repassa_arquivos():
    por_ano = {
        2024: bruto(("280030", "A90", "202401"), ("280030", "A92", "202402")),
        2025: bruto(("280030", "A90", "202501")),
    }
    fonte = FonteSinan("dengue", baixar=baixador(
        por_ano, arquivos={2024: [{"arquivo": "a.parquet", "ano": 2024, "sha256": "x"}]}
    ))

    resultado = fonte.obter(agravo_codigo="A90", anos=[2024, 2025])

    assert len(resultado.tabela) == 2
    assert resultado.linhas_lidas == 3
    assert resultado.descartes["agravo_diferente"] == 1
    assert resultado.arquivos_brutos == [{"arquivo": "a.parquet", "ano": 2024, "sha256": "x"}]
    assert resultado.tipo_semana == TIPO_SEMANA
    verificar_notificacoes(resultado)


def test_fonte_sem_anos_levanta_erro():
    with pytest.raises(ValueError, match="ao menos um ano"):
        FonteSinan("dengue", baixar=baixador({})).obter(agravo_codigo="A90", anos=[])


def test_fonte_com_ano_sem_nenhuma_linha_valida_continua_no_contrato():
    fonte = FonteSinan("dengue", baixar=baixador({2025: bruto(("280030", "A92", "202501"))}))

    resultado = fonte.obter(agravo_codigo="A90", anos=[2025])

    assert len(resultado.tabela) == 0
    verificar_notificacoes(resultado)