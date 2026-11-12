import pandas as pd
import pytest

from ingestao.services.agregacao import COLUNAS_CSV, agregar_semanal, ultima_semana

ARACAJU = "2800308"
MUNICIPIOS = {ARACAJU: "Aracaju"}


def canonica(*linhas):
    """ tabela canônica a partir de (municipio, ano, semana)."""
    return pd.DataFrame(
        linhas, columns=["municipio_codigo", "ano", "semana"]
    ).astype({"municipio_codigo": str, "ano": "int64", "semana": "int64"})


def agregar(tabela, municipios=None, inicio=(2025, 1), fim=(2025, 4)):
    return agregar_semanal(
        tabela,
        agravo_codigo="A90",
        agravo_nome="Dengue",
        municipios=municipios or MUNICIPIOS,
        inicio=inicio,
        fim=fim,
    )


def contagens(resultado):
    return list(resultado.tabela["contagem"])


def test_tres_notificacoes_da_mesma_semana_viram_contagem_tres():
    resultado = agregar(canonica((ARACAJU, 2025, 2), (ARACAJU, 2025, 2), (ARACAJU, 2025, 2)))

    linha = resultado.tabela[resultado.tabela["semana_epidemiologica"] == 2].iloc[0]
    assert linha["contagem"] == 3
    assert resultado.notificacoes_contadas == 3


def test_semana_sem_caso_entre_duas_com_casos_vira_zero():
    resultado = agregar(canonica((ARACAJU, 2025, 1), (ARACAJU, 2025, 3)))

    assert contagens(resultado) == [1, 0, 1, 0]


def test_municipio_do_recorte_sem_nenhum_caso_recebe_serie_de_zeros():
    outro = "2800407"
    resultado = agregar(
        canonica((ARACAJU, 2025, 1)), municipios={ARACAJU: "Aracaju", outro: "Outro"}
    )

    por_municipio = resultado.tabela.groupby("municipio_codigo")["contagem"].apply(list)
    assert por_municipio[ARACAJU] == [1, 0, 0, 0]
    assert por_municipio[outro] == [0, 0, 0, 0]


def test_municipio_fora_do_recorte_e_semana_fora_do_periodo_sao_contados():
    resultado = agregar(canonica(
        ("2800407", 2025, 1),    # outro município
        (ARACAJU, 2024, 10),     # antes do período
        (ARACAJU, 2025, 9),      # depois do período
        (ARACAJU, 2025, 1),
    ))

    assert resultado.notificacoes_contadas == 1
    assert resultado.descartes == {
        "municipio_fora_do_recorte": 1,
        "semana_fora_do_periodo": 2,
    }


def test_tabela_vazia_gera_serie_de_zeros():
    resultado = agregar(canonica())

    assert contagens(resultado) == [0, 0, 0, 0]


def test_tabela_sai_no_formato_do_contrato_ordenada_e_com_inteiros():
    tabela = agregar(canonica((ARACAJU, 2025, 3))).tabela

    assert list(tabela.columns) == COLUNAS_CSV
    assert list(tabela["semana_epidemiologica"]) == [1, 2, 3, 4]
    assert str(tabela["contagem"].dtype) == "int64"
    assert str(tabela["ano"].dtype) == "int64"
    assert set(tabela["municipio_nome"]) == {"Aracaju"}


def test_periodo_atravessa_a_virada_de_ano_de_53_semanas():
    tabela = agregar(
        canonica((ARACAJU, 2025, 53), (ARACAJU, 2026, 1)),
        inicio=(2025, 52), fim=(2026, 2),
    ).tabela

    # O CSV usa semana ISO da segunda-feira seguinte ao domingo de início da SE.
    # Portanto, a SE 53/2025 vira ISO 2026/1 e a SE 1/2026 vira ISO 2026/2.
    assert list(zip(tabela["ano"], tabela["semana_epidemiologica"], tabela["contagem"])) == [
        (2025, 52, 0), (2026, 1, 1), (2026, 2, 1), (2026, 3, 0),
    ]


def test_ultima_semana_usa_ano_e_semana_juntos():
    tabela = canonica((ARACAJU, 2025, 52), (ARACAJU, 2026, 1), (ARACAJU, 2025, 10))

    assert ultima_semana(tabela) == (2026, 1)


def test_ultima_semana_de_tabela_vazia_levanta_erro():
    with pytest.raises(ValueError, match="Nenhuma notificação"):
        ultima_semana(canonica())