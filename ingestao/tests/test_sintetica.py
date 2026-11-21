"""Base sintética rotulada: determinismo (RNF005), contrato do CSV e rótulos de surto."""
import csv
import io
import itertools
from datetime import date, timedelta

import pytest

from ingestao.services.validacao import validar_registro
from ingestao.sintetica import gerador

PEQUENA = {"semanas": 40}


@pytest.fixture(scope="module")
def base():
    return gerador.gerar_base()


def test_mesma_semente_gera_arquivos_identicos(base):
    outra = gerador.gerar_base()
    assert gerador.serializar(base) == gerador.serializar(outra)


def test_semente_diferente_gera_base_diferente(base):
    assert gerador.serializar(base)["base"] != gerador.serializar(gerador.gerar_base(semente=7))["base"]


def test_tamanho_default_e_20_municipios_x_5_agravos_x_100_semanas(base):
    assert len(base.registros) == 20 * 5 * 100
    assert {r["agravo_nome"] for r in base.registros} == {
        "Dengue", "Zika", "Chikungunya", "Leishmaniose", "Sífilis congênita"}
    assert len({r["municipio_codigo"] for r in base.registros}) == 20


def test_todas_as_linhas_passam_na_validacao_da_ingestao(base):
    texto = gerador.serializar(base)["base"]
    for linha in csv.DictReader(io.StringIO(texto)):
        assert validar_registro(linha) is not None


def test_series_tem_semanas_consecutivas_sem_buracos(base):
    series = {}
    for r in base.registros:
        d = date.fromisocalendar(r["ano"], r["semana_epidemiologica"], 1)
        series.setdefault((r["agravo_codigo"], r["municipio_codigo"]), []).append(d)
    assert len(series) == 100
    for datas in series.values():
        assert all(b - a == timedelta(weeks=1) for a, b in itertools.pairwise(datas))


def test_contagens_sao_inteiros_nao_negativos(base):
    assert all(isinstance(r["contagem"], int) and r["contagem"] >= 0 for r in base.registros)


def test_surtos_rotulados_sao_consistentes(base):
    por_serie = {}
    for s in base.surtos:
        por_serie.setdefault((s["agravo_codigo"], s["municipio_codigo"]), []).append(s)
        semanas = s["semanas_afetadas"].split(";")
        assert len(semanas) == s["duracao_semanas"] and 3 <= s["duracao_semanas"] <= 7
        assert s["incremento_pico_esperado"] >= gerador.PISO_INCREMENTO_PICO * 0.5
    inicio = gerador.INICIO_PADRAO
    for lista in por_serie.values():
        datas = sorted(date.fromisoformat(s["semana_inicio"]) for s in lista)
        assert (datas[0] - inicio).days // 7 >= gerador.HISTORICO_MINIMO  # histórico mínimo
        for a, b in itertools.pairwise(datas):
            assert (b - a).days // 7 >= gerador.INTERVALO_ENTRE_SURTOS     # sem sobreposição


def test_catalogos_passam_na_leitura_do_projeto(tmp_path):
    from ingestao.services.catalogos import ler_agravos, ler_municipios

    textos = gerador.catalogos_texto()
    (tmp_path / "m.csv").write_text(textos["municipios"], encoding="utf-8")
    (tmp_path / "a.csv").write_text(textos["agravos"], encoding="utf-8")
    assert len(ler_municipios(tmp_path / "m.csv")) == 20
    assert len(ler_agravos(tmp_path / "a.csv")) == 5


def test_inicio_deve_ser_segunda_feira():
    with pytest.raises(ValueError):
        gerador.gerar_base(inicio=date(2024, 10, 15))  # terça


def test_poisson_tem_media_proxima_da_esperada():
    rng = gerador._rng(1, "teste")
    for lam in (0.5, 5, 80):
        amostra = [gerador._poisson(rng, lam) for _ in range(4000)]
        assert abs(sum(amostra) / len(amostra) - lam) < 0.1 * lam + 0.1
