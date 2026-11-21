"""Backtest do detector sobre a base sintética (sem banco)."""
import pytest

from deteccao.services.backtest import executar_backtest, relatorio_markdown
from ingestao.sintetica import gerador


@pytest.fixture(scope="module")
def resultado():
    b = gerador.gerar_base()
    return b, executar_backtest(b.registros, b.surtos)


def test_backtest_e_deterministico(resultado):
    b, r = resultado
    assert executar_backtest(b.registros, b.surtos) == r


def test_semanas_avaliadas_descontam_a_janela(resultado):
    _, r = resultado
    assert r["semanas_avaliadas"] == 100 * (100 - 8)


def test_detector_pega_a_maioria_dos_surtos_injetados(resultado):
    _, r = resultado
    assert r["surtos"] > 50 and r["deteccao_qualquer_semana"] >= 0.9


def test_as_duas_definicoes_de_falso_positivo_sao_distintas(resultado):
    _, r = resultado
    g = r["geral"]
    assert g["falsos_positivos"] <= g["alertas"]
    assert g["fp_sobre_alertas"] > g["fp_sobre_semanas_normais"]  # DP04: definições divergem


def test_relatorio_tem_secoes_e_nomes(resultado):
    b, r = resultado
    md = relatorio_markdown(r, b.meta, {p.codigo: p.nome for p in gerador.PERFIS})
    assert "## Resultado geral (OBJ02)" in md and "Leishmaniose" in md and "Por faixa" in md
