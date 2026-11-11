from datetime import date, timedelta

import pytest

from ingestao.services.calendario import (
    ano_semana_de_texto,
    deslocar_semana,
    inicio_semana_epidemiologica,
    listar_semanas,
    semana_da_data,
    semana_iso_equivalente,
    semanas_no_ano,
)


def test_se1_de_2024_comeca_no_domingo_31_de_dezembro():
    assert inicio_semana_epidemiologica(2024, 1) == date(2023, 12, 31)


def test_se1_de_2025_comeca_no_domingo_29_de_dezembro():
    assert inicio_semana_epidemiologica(2025, 1) == date(2024, 12, 29)


@pytest.mark.parametrize(("ano", "esperado"), [
    (2019, 52), (2020, 53), (2023, 52), (2024, 52), (2025, 53), (2026, 52),
])
def test_quantidade_de_semanas_por_ano(ano, esperado):
    assert semanas_no_ano(ano) == esperado


def test_semana_53_em_ano_de_52_semanas_e_rejeitada():
    with pytest.raises(ValueError, match="inexistente"):
        inicio_semana_epidemiologica(2024, 53)


@pytest.mark.parametrize("semana", [0, 54, -1])
def test_semana_fora_do_intervalo_e_rejeitada(semana):
    with pytest.raises(ValueError, match="inexistente"):
        inicio_semana_epidemiologica(2025, semana)


def test_todo_inicio_de_semana_cai_no_domingo():
    for ano in range(2015, 2031):
        for semana in range(1, semanas_no_ano(ano) + 1):
            assert inicio_semana_epidemiologica(ano, semana).weekday() == 6


def test_semana_da_data_cobre_virada_de_ano():
    assert semana_da_data(date(2024, 12, 30)) == (2025, 1)
    assert semana_da_data(date(2026, 1, 1)) == (2025, 53)
    assert semana_da_data(date(2025, 12, 28)) == (2025, 53)
    assert semana_da_data(date(2026, 1, 4)) == (2026, 1)


def test_semana_da_data_e_inversa_de_inicio_semana():
    for ano in range(2018, 2028):
        for semana in range(1, semanas_no_ano(ano) + 1):
            inicio = inicio_semana_epidemiologica(ano, semana)
            assert semana_da_data(inicio) == (ano, semana)
            assert semana_da_data(inicio + timedelta(days=6)) == (ano, semana)


@pytest.mark.parametrize(("se", "iso"), [
    ((2024, 1), (2024, 1)),
    ((2025, 1), (2025, 1)),
    ((2020, 53), (2020, 53)),
    ((2025, 52), (2025, 52)),
    ((2025, 53), (2026, 1)),   # SE 53 de 2025 cai na ISO 1 de 2026
    ((2026, 1), (2026, 2)),    # 2026 tem 53 semanas ISO e 52 SE
])
def test_semana_iso_equivalente(se, iso):
    assert semana_iso_equivalente(*se) == iso


def test_semanas_iso_equivalentes_sao_consecutivas_na_segunda_feira():
    semanas = listar_semanas((2019, 1), (2027, 10))
    segundas = [
        date.fromisocalendar(*semana_iso_equivalente(ano, semana), 1)
        for ano, semana in semanas
    ]

    assert all(
        proxima - anterior == timedelta(days=7)
        for anterior, proxima in zip(segundas, segundas[1:])
    )
    assert segundas[0] == inicio_semana_epidemiologica(2019, 1) + timedelta(days=1)


def test_csv_usa_a_semana_iso_equivalente_na_virada_de_ano_de_53_semanas():
    tabela = agregar(
        canonica((ARACAJU, 2025, 53), (ARACAJU, 2026, 1)),
        inicio=(2025, 52), fim=(2026, 2),
    ).tabela

    # SE 52 de 2025, SE 53 de 2025, SE 1 de 2026 e SE 2 de 2026 em semana ISO.
    assert list(zip(tabela["ano"], tabela["semana_epidemiologica"], tabela["contagem"])) == [
        (2025, 52, 0), (2026, 1, 1), (2026, 2, 1), (2026, 3, 0),
    ]


def test_listar_semanas_atravessa_ano_de_52_semanas():
    assert listar_semanas((2024, 51), (2025, 1)) == [
        (2024, 51), (2024, 52), (2025, 1),
    ]


def test_listar_semanas_com_uma_semana_so():
    assert listar_semanas((2025, 10), (2025, 10)) == [(2025, 10)]


def test_listar_semanas_rejeita_periodo_invertido():
    with pytest.raises(ValueError, match="posterior"):
        listar_semanas((2025, 10), (2025, 9))


def test_deslocar_semana_para_tras_e_para_frente():
    assert deslocar_semana(2026, 2, -4) == (2025, 51)
    assert deslocar_semana(2025, 52, 2) == (2026, 1)


def test_ano_semana_de_texto():
    assert ano_semana_de_texto("202501") == (2025, 1)
    assert ano_semana_de_texto("202553") == (2025, 53)


@pytest.mark.parametrize("texto", ["2025", "20251", "abcdef", "202400", "202453"])
def test_ano_semana_de_texto_rejeita_formato_ou_semana_invalida(texto):
    with pytest.raises(ValueError):
        ano_semana_de_texto(texto)