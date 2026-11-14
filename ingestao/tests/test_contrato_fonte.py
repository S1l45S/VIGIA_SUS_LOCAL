"""Contrato das fontes, ou seja, toda fonte tem de poder ser trocada por outra"""

import pandas as pd
import pytest

from ingestao.fontes.base import (
    ErroContratoFonte,
    Notificacoes,
    verificar_notificacoes,
)
from ingestao.fontes.sinan import FonteSinan
from ingestao.tests.fontes_falsas import FonteEmMemoria


def _sinan():
    df = pd.DataFrame({
        "ID_MUNICIP": ["280030", "280030"],
        "ID_AGRAVO": ["A90", "A90"],
        "SEM_NOT": ["202501", "202502"],
    })
    return FonteSinan("dengue", baixar=lambda doenca, ano: (df, []))


def _memoria():
    return FonteEmMemoria([("2800308", 2025, 1), ("2800308", 2025, 2)])


@pytest.mark.parametrize("criar_fonte", [_sinan, _memoria])
def test_toda_fonte_cumpre_o_contrato(criar_fonte):
    resultado = criar_fonte().obter(agravo_codigo="A90", anos=[2025])

    verificar_notificacoes(resultado)
    assert resultado.linhas_lidas >= len(resultado.tabela)


def _notificacoes(tabela, **extra):
    dados = {"fonte": "x", "tipo_semana": "y", "tabela": tabela, "linhas_lidas": len(tabela)}
    dados.update(extra)
    return Notificacoes(**dados)


def _tabela(**colunas):
    base = {"municipio_codigo": ["2800308"], "ano": [2025], "semana": [1]}
    base.update(colunas)
    return pd.DataFrame(base)


def test_contrato_rejeita_colunas_erradas():
    tabela = _tabela().rename(columns={"semana": "sem"})

    with pytest.raises(ErroContratoFonte, match="Colunas"):
        verificar_notificacoes(_notificacoes(tabela))


def test_contrato_rejeita_tipos_errados():
    with pytest.raises(ErroContratoFonte, match="inteiro"):
        verificar_notificacoes(_notificacoes(_tabela(ano=["2025"])))
    with pytest.raises(ErroContratoFonte, match="texto"):
        verificar_notificacoes(_notificacoes(_tabela(municipio_codigo=[2800308])))


@pytest.mark.parametrize("codigo", ["280030", "2800307"])
def test_contrato_rejeita_municipio_sem_sete_digitos_ou_com_dv_errado(codigo):
    with pytest.raises(ErroContratoFonte):
        verificar_notificacoes(_notificacoes(_tabela(municipio_codigo=[codigo])))


def test_contrato_rejeita_semana_inexistente():
    with pytest.raises(ErroContratoFonte, match="inexistente"):
        verificar_notificacoes(_notificacoes(_tabela(ano=[2024], semana=[53])))


def test_contrato_rejeita_mais_notificacoes_do_que_linhas_lidas():
    with pytest.raises(ErroContratoFonte, match="linhas lidas"):
        verificar_notificacoes(_notificacoes(_tabela(), linhas_lidas=0))


def test_contrato_exige_nome_e_tipo_de_semana():
    with pytest.raises(ErroContratoFonte, match="tipo de semana"):
        verificar_notificacoes(_notificacoes(_tabela(), tipo_semana=""))