from datetime import date, timedelta

import pytest

from dashboard.services import consulta
from dashboard.tests.conftest import SEGUNDA_INICIAL

pytestmark = pytest.mark.django_db


def test_serie_une_observado_com_referencias_da_deteccao(criar_serie):
    # 8 semanas estáveis em 10 e uma semana em surto (30): média 10, σ 0.
    criar_serie([10] * 8 + [30])

    serie = consulta.montar_serie("2800308", "A90", None, None)

    assert [p.observado for p in serie.pontos] == [10] * 8 + [30]
    # As 8 primeiras semanas não têm histórico suficiente: sem banda.
    assert all(p.media_movel is None for p in serie.pontos[:8])
    ultima = serie.pontos[8]
    assert ultima.media_movel == 10
    assert ultima.limite_superior == 10
    assert ultima.anomalia is True
    assert serie.semanas_em_anomalia == 1
    assert serie.semanas_sem_referencia == 8
    assert serie.total_notificacoes == 110
    assert not serie.vazia


def test_filtra_por_periodo(criar_serie):
    criar_serie(list(range(1, 13)))
    inicio = SEGUNDA_INICIAL + timedelta(weeks=2)
    fim = SEGUNDA_INICIAL + timedelta(weeks=5)

    serie = consulta.montar_serie("2800308", "A90", inicio, fim)

    assert [p.observado for p in serie.pontos] == [3, 4, 5, 6]


def test_filtra_por_municipio_e_agravo_sem_misturar_series(criar_serie):
    criar_serie([1] * 10)
    criar_serie([99] * 10, municipio=("2800100", "Outra cidade"))
    criar_serie([77] * 10, agravo=("B01", "Varicela"))

    serie = consulta.montar_serie("2800308", "A90", None, None)

    assert {p.observado for p in serie.pontos} == {1}


def test_serie_sem_registros_ou_so_com_zeros_e_vazia(criar_serie):
    criar_serie([0] * 10)
    assert consulta.montar_serie("2800308", "A90", None, None).vazia

    sem_dados = consulta.montar_serie("0000000", "ZZZ", None, None)
    assert sem_dados.pontos == ()
    assert sem_dados.vazia


def test_serie_curta_fica_sem_banda(criar_serie):
    criar_serie([5, 6, 7])
    serie = consulta.montar_serie("2800308", "A90", None, None)
    assert serie.sem_banda is True


def test_para_grafico_tem_listas_alinhadas(criar_serie):
    criar_serie([10] * 8 + [30])
    dados = consulta.montar_serie("2800308", "A90", None, None).para_grafico()

    tamanhos = {len(v) for v in dados.values()}
    assert tamanhos == {9}
    assert dados["media_movel"][:8] == [None] * 8
    assert dados["limite_superior"][8] == 10
    assert dados["anomalia"][8] is True


def test_rotulo_usa_semana_epidemiologica_real():
    # Segunda 2025-01-06 abre a SE 02/2025 (SE 1 começou em 2024-12-29).
    assert consulta.rotulo_semana(date(2025, 1, 6)) == "SE 02/2025"
    assert consulta.rotulo_semana(date(2024, 12, 30)) == "SE 01/2025"


def test_selecao_inicial_escolhe_municipio_e_agravo_de_maior_volume(
    criar_serie,
):
    criar_serie([1] * 10)  # Aracaju/Dengue: 10
    criar_serie([50] * 10, municipio=("2800100", "Outra cidade"))  # 500
    criar_serie(
        [5] * 10, municipio=("2800100", "Outra cidade"), agravo=("B01", "Varicela")
    )  # 50

    assert consulta.selecao_inicial() == ("2800100", "A90")


def test_selecao_inicial_sem_dados_devolve_none(banco_limpo):
    assert consulta.selecao_inicial() is None


def test_periodo_padrao_termina_na_semana_mais_recente(criar_serie):
    criar_serie([1] * 80)
    ultima = SEGUNDA_INICIAL + timedelta(weeks=79)

    inicio, fim = consulta.resolver_periodo("2800308", "A90")

    assert fim == ultima
    assert inicio == ultima - timedelta(weeks=51)


def test_periodo_informado_e_preservado(criar_serie):
    criar_serie([1] * 20)
    inicio, fim = date(2025, 2, 3), date(2025, 3, 3)
    assert consulta.resolver_periodo("2800308", "A90", inicio, fim) == (
        inicio,
        fim,
    )