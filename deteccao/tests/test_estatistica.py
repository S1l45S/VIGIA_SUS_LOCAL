from datetime import date, timedelta
from math import isclose

import pytest

from deteccao.services.estatistica import calcular_referencias, processar_series


def test_calcula_media_desvio_populacional_e_limite():
    referencias = calcular_referencias([1, 2, 3, 4, 5, 6, 7, 8])

    assert referencias["media_movel"] == 4.5
    assert isclose(referencias["desvio_padrao"], 2.29128784747792)
    assert isclose(referencias["limite_superior"], 9.08257569495584)


def test_rejeita_janela_incompleta_e_parametro_invalido():
    with pytest.raises(ValueError, match="exatamente 8"):
        calcular_referencias([1, 2])
    with pytest.raises(ValueError, match="inteiro positivo"):
        calcular_referencias([1], janela=0)


def test_rejeita_valores_nao_finitos():
    with pytest.raises(ValueError, match="números finitos"):
        calcular_referencias([1, 2, 3, 4, 5, 6, 7, float("nan")])


def _registro(indice, quantidade, agravo="AGR001", municipio="2800308"):
    return {
        "agravo_codigo": agravo,
        "municipio_codigo": municipio,
        "semana_inicio": date(2025, 1, 6) + timedelta(weeks=indice),
        "quantidade": quantidade,
    }


def test_processa_semana_com_oito_semanas_de_historico_e_classifica_anomalia():
    registros = (
        [_registro(i, 10) for i in range(8)]
        + [_registro(8, 10)]
        + [_registro(9, 30)]
    )

    resultados = processar_series(registros, persistir=False)

    assert len(resultados) == 2
    assert resultados[0]["anomalia"] is False
    assert resultados[0]["media_movel"] == 10
    assert resultados[0]["desvio_padrao"] == 0
    assert resultados[0]["limite_superior"] == 10
    assert resultados[1]["anomalia"] is True
    assert resultados[1]["quantidade_observada"] == 30


def test_series_com_menos_de_oito_semanas_nao_gera_resultados():
    assert processar_series([_registro(i, i) for i in range(8)], persistir=False) == []


def test_nao_avalia_janela_com_semana_ausente_e_retoma_apos_oito_semanas_contiguas():
    registros = [_registro(i, 10) for i in range(8)]
    registros += [_registro(i, 10 if i < 17 else 30) for i in range(9, 18)]

    resultados = processar_series(registros, persistir=False)

    assert len(resultados) == 1
    assert resultados[0]["semana_inicio"] == _registro(17, 30)["semana_inicio"]
    assert resultados[0]["anomalia"] is True


def test_rejeita_semanas_duplicadas_na_mesma_serie():
    registros = [_registro(i, 10) for i in range(8)]
    registros += [_registro(7, 10), _registro(8, 30)]

    with pytest.raises(ValueError, match="semanas duplicadas"):
        processar_series(registros, persistir=False)


def test_processa_series_separadamente_por_municipio_e_agravo():
    registros = [_registro(i, 10) for i in range(8)] + [_registro(8, 30)]
    registros += [_registro(i, 2, municipio="2800407") for i in range(9)]

    resultados = processar_series(registros, persistir=False)

    assert len(resultados) == 2
    assert {r["municipio_codigo"] for r in resultados} == {"2800308", "2800407"}
    assert {r["anomalia"] for r in resultados} == {False, True}
