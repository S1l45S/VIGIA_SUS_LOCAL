"""O CSV gerado a partir do DATASUS passa pelas regras que já existiam

Prova que a saída da nova ingestão é aceita por elas
"""

import csv
from datetime import timedelta

from deteccao.services.estatistica import processar_series
from ingestao.services.preparacao import preparar_csv
from ingestao.services.validacao import validar_estrutura, validar_registro
from ingestao.tests.fontes_falsas import FonteEmMemoria

ARACAJU = "2800308"


def gerar(tmp_path, linhas, inicio, fim):
    caminho = tmp_path / "carga.csv"
    preparar_csv(
        FonteEmMemoria(linhas),
        agravo_codigo="A90",
        agravo_nome="Dengue",
        municipios={ARACAJU: "Aracaju"},
        anos=[inicio[0]],
        inicio=inicio,
        fim=fim,
        saida=caminho,
    )
    return caminho


def validar(caminho):
    registros = []
    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = validar_estrutura(arquivo)
        for linha in leitor:
            registros.append(validar_registro(linha))
    return registros


def test_todas_as_linhas_sao_aceitas_pela_validacao_existente(tmp_path):
    # atravessa as viradas de 2020 (53 SE), 2025 (53 SE) e 2026.
    caminho = gerar(tmp_path, [(ARACAJU, 2020, 10)], inicio=(2019, 40), fim=(2026, 40))

    with caminho.open(encoding="utf-8") as arquivo:
        total = sum(1 for _ in csv.DictReader(arquivo))
    assert len(validar(caminho)) == total


def test_semanas_ficam_consecutivas_em_toda_a_serie(tmp_path):
    caminho = gerar(tmp_path, [(ARACAJU, 2025, 53)], inicio=(2019, 40), fim=(2026, 40))

    datas = [registro["semana_inicio"] for registro in validar(caminho)]

    assert all(b - a == timedelta(days=7) for a, b in zip(datas, datas[1:]))


def test_a_contagem_da_se_53_nao_se_perde(tmp_path):
    caminho = gerar(
        tmp_path,
        [(ARACAJU, 2025, 53), (ARACAJU, 2025, 53), (ARACAJU, 2025, 52)],
        inicio=(2025, 50), fim=(2026, 3),
    )

    quantidades = [registro["quantidade"] for registro in validar(caminho)]

    # SE 50, 51, 52, 53 de 2025 e SE 1, 2, 3 de 2026.
    assert quantidades == [0, 0, 1, 2, 0, 0, 0]


def test_a_deteccao_existente_avalia_a_serie_inteira_sem_lacunas(tmp_path):
    linhas = [(ARACAJU, 2025, semana) for semana in range(1, 54) for _ in range(10)]
    linhas += [(ARACAJU, 2026, semana) for semana in range(1, 6) for _ in range(10)]
    linhas += [(ARACAJU, 2026, 6) for _ in range(40)]
    caminho = gerar(tmp_path, linhas, inicio=(2025, 1), fim=(2026, 6))

    registros = validar(caminho)
    resultados = processar_series(registros=registros, persistir=False)

    # 59 semanas na série, 8 de histórico logo, 51 semanas avaliadas, sem lacuna.
    assert len(registros) == 59
    assert len(resultados) == 51
    assert resultados[-1]["anomalia"] is True
    assert not any(r["anomalia"] for r in resultados[:-1])