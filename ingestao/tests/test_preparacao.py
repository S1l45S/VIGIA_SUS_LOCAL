import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from ingestao.fontes.base import ErroContratoFonte, Notificacoes
from ingestao.services.preparacao import preparar_csv
from ingestao.services.saida import caminho_metadados
from ingestao.tests.fontes_falsas import FonteEmMemoria

ARACAJU = "2800308"
MUNICIPIOS = {ARACAJU: "Aracaju"}
AGORA = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


def preparar(tmp_path, fonte, nome="saida.csv", **extra):
    return preparar_csv(
        fonte,
        agravo_codigo="A90",
        agravo_nome="Dengue",
        municipios=MUNICIPIOS,
        anos=[2025],
        inicio=(2025, 1),
        saida=tmp_path / nome,
        agora=AGORA,
        **extra,
    )


def test_grava_csv_no_contrato_e_metadados_da_fonte(tmp_path):
    fonte = FonteEmMemoria(
        [(ARACAJU, 2025, 1), (ARACAJU, 2025, 6)],
        tipo_semana="semana de teste",
        descartes={"campo_nulo": 3},
    )

    resultado, metadados, fim = preparar(tmp_path, fonte, fim=(2025, 4))

    linhas = (tmp_path / "saida.csv").read_text(encoding="utf-8").splitlines()
    assert linhas[0] == (
        "agravo_codigo,agravo_nome,municipio_codigo,municipio_nome,"
        "ano,semana_epidemiologica,contagem"
    )
    assert linhas[1] == "A90,Dengue,2800308,Aracaju,2025,1,1"
    assert len(linhas) == 5
    arquivo = json.loads(caminho_metadados(tmp_path / "saida.csv").read_text(encoding="utf-8"))
    assert arquivo == metadados
    assert metadados["fonte"] == "Fonte em memória"
    assert metadados["tipo_semana"] == "semana de teste"
    assert metadados["periodo"] == {"inicio": "202501", "fim": "202504"}
    assert "semana ISO" in metadados["calendario_do_csv"]
    assert metadados["extraido_em"] == "2026-11-10T12:00:00+00:00"
    assert metadados["descartes"] == {
        "fonte": {"campo_nulo": 3},
        "agregacao": {"municipio_fora_do_recorte": 0, "semana_fora_do_periodo": 1},
    }
    assert metadados["semanas_cortadas"] == 0
    assert fim == (2025, 4)


def test_sem_fim_corta_as_ultimas_semanas_da_fonte(tmp_path):
    fonte = FonteEmMemoria([(ARACAJU, 2025, 1), (ARACAJU, 2025, 10)])

    _, metadados, fim = preparar(tmp_path, fonte, cortar_ultimas=4)

    assert fim == (2025, 6)
    assert metadados["periodo"]["fim"] == "202506"
    assert metadados["semanas_cortadas"] == 4


def test_duas_execucoes_geram_arquivos_identicos(tmp_path):
    fonte = FonteEmMemoria([(ARACAJU, 2025, 1), (ARACAJU, 2025, 3)])

    preparar(tmp_path, fonte, nome="a.csv", fim=(2025, 4))
    preparar(tmp_path, fonte, nome="b.csv", fim=(2025, 4))

    assert (tmp_path / "a.csv").read_bytes() == (tmp_path / "b.csv").read_bytes()


class FonteQueViolaOContrato:
    nome = "Fonte ruim"

    def obter(self, *, agravo_codigo, anos):
        tabela = pd.DataFrame({"municipio": ["x"], "semana": [1]})
        return Notificacoes(
            fonte=self.nome, tipo_semana="t", tabela=tabela, linhas_lidas=1
        )


def test_fonte_fora_do_contrato_e_barrada_antes_de_gravar(tmp_path):
    with pytest.raises(ErroContratoFonte):
        preparar(tmp_path, FonteQueViolaOContrato(), fim=(2025, 4))

    assert not (tmp_path / "saida.csv").exists()


def test_inicio_invalido_e_rejeitado(tmp_path):
    with pytest.raises(ValueError, match="inexistente"):
        preparar_csv(
            FonteEmMemoria([]),
            agravo_codigo="A90", agravo_nome="Dengue", municipios=MUNICIPIOS,
            anos=[2025], inicio=(2024, 53), saida=tmp_path / "x.csv",
        )