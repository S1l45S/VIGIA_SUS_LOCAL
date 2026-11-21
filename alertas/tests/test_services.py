"""Serviços do alerta, com MongoDB real em replica set (como no resto do projeto)."""
from datetime import date

import pytest
from django.contrib.auth.models import AnonymousUser

from alertas.dominio import (AlertaSubstituido, AnomaliaInvalida, ConflitoDeVersao,
                             TransicaoInvalida, UsuarioNaoAutenticado)
from alertas.models import Alerta
from alertas.services import alterar_situacao, emitir_alerta, emitir_alertas, listar_alertas

pytestmark = pytest.mark.django_db


# ---- emissão sem duplicidade (US03) ------------------------------------------------
def test_emite_alerta_novo_com_historico_inicial(banco_limpo, anomalia):
    alerta, status = emitir_alerta(anomalia())
    assert status == "criado"
    assert alerta.situacao == "novo" and alerta.versao == 1 and not alerta.substituido
    assert len(alerta.historico) == 1 and alerta.historico[0].origem == "sistema"


def test_reprocesso_identico_nao_duplica(banco_limpo, anomalia):
    emitir_alerta(anomalia())
    _, status = emitir_alerta(anomalia())
    assert status == "inalterado"
    assert Alerta.objects.count() == 1


def test_reprocesso_com_insumos_novos_substitui_e_preserva_historico(banco_limpo, anomalia, gestor):
    antigo, _ = emitir_alerta(anomalia())
    alterar_situacao(alerta_id=antigo.pk, nova_situacao="em_investigacao",
                     versao_lida=1, usuario=gestor)
    novo, status = emitir_alerta(anomalia(observado=45, resultado_id="r-2"))
    assert status == "substituido"
    antigo.refresh_from_db()
    assert antigo.substituido and antigo.situacao == "em_investigacao"  # mantém situação
    assert len(antigo.historico) == 2                                    # mantém histórico
    assert novo.situacao == "novo" and novo.substitui == antigo.pk       # QA-03/DP06
    assert Alerta.objects.filter(substituido=False).count() == 1         # sem duplicidade


def test_so_anomalia_gera_alerta(banco_limpo, anomalia):
    with pytest.raises(AnomaliaInvalida):
        emitir_alerta(anomalia(observado=10, limite=10.0))   # RN02: estritamente maior
    assert Alerta.objects.count() == 0


def test_emitir_alertas_em_lote(banco_limpo, anomalia):
    res = emitir_alertas([anomalia(), anomalia(semana_inicio=date(2025, 3, 10), semana_epi=11), anomalia()])
    assert res.total_criados == 2 and len(res.inalterados) == 1


# ---- atualização de situação (US04, RN03) -------------------------------------------
def test_altera_situacao_registra_data_hora_e_usuario(banco_limpo, anomalia, gestor):
    a, _ = emitir_alerta(anomalia())
    a = alterar_situacao(alerta_id=a.pk, nova_situacao="em_investigacao", versao_lida=1,
                         usuario=gestor, observacao="Equipe enviada ao bairro")
    ultimo = a.historico[-1]
    assert a.situacao == "em_investigacao" and a.versao == 2 and len(a.historico) == 2
    assert ultimo.usuario_nome == "gestor1" and ultimo.usuario_id == str(gestor.pk)
    assert ultimo.em is not None and ultimo.situacao_anterior == "novo"


def test_historico_e_de_acrescimo(banco_limpo, anomalia, gestor):
    a, _ = emitir_alerta(anomalia())
    a.refresh_from_db()  # o MongoDB guarda datetime em milissegundos
    primeiro = a.historico[0].em
    a = alterar_situacao(alerta_id=a.pk, nova_situacao="encerrado", versao_lida=1, usuario=gestor)
    assert a.historico[0].em == primeiro and a.historico[0].origem == "sistema"


def test_recusa_sem_usuario_autenticado(banco_limpo, anomalia):
    a, _ = emitir_alerta(anomalia())
    for u in (None, AnonymousUser()):
        with pytest.raises(UsuarioNaoAutenticado):
            alterar_situacao(alerta_id=a.pk, nova_situacao="encerrado", versao_lida=1, usuario=u)
    a.refresh_from_db()
    assert a.situacao == "novo" and len(a.historico) == 1


def test_recusa_transicao_invalida_sem_gravar(banco_limpo, anomalia, gestor):
    a, _ = emitir_alerta(anomalia())
    a = alterar_situacao(alerta_id=a.pk, nova_situacao="encerrado", versao_lida=1, usuario=gestor)
    with pytest.raises(TransicaoInvalida):   # encerrado não reabre
        alterar_situacao(alerta_id=a.pk, nova_situacao="novo", versao_lida=a.versao, usuario=gestor)
    a.refresh_from_db()
    assert a.situacao == "encerrado" and a.versao == 2 and len(a.historico) == 2


def test_conflito_de_versao_nao_sobrescreve(banco_limpo, anomalia, gestor, outro_gestor):
    a, _ = emitir_alerta(anomalia())
    alterar_situacao(alerta_id=a.pk, nova_situacao="em_investigacao", versao_lida=1,
                     usuario=gestor)
    with pytest.raises(ConflitoDeVersao):    # segundo gestor ainda tem a versão 1
        alterar_situacao(alerta_id=a.pk, nova_situacao="encerrado", versao_lida=1,
                         usuario=outro_gestor)
    a.refresh_from_db()
    assert a.situacao == "em_investigacao" and len(a.historico) == 2


def test_alerta_substituido_recusa_alteracao(banco_limpo, anomalia, gestor):
    antigo, _ = emitir_alerta(anomalia())
    emitir_alerta(anomalia(observado=45, resultado_id="r-2"))
    with pytest.raises(AlertaSubstituido):
        alterar_situacao(alerta_id=antigo.pk, nova_situacao="encerrado",
                         versao_lida=1, usuario=gestor)


def test_alerta_nunca_e_excluido(banco_limpo, anomalia):
    a, _ = emitir_alerta(anomalia())
    with pytest.raises(PermissionError):
        a.delete()
    assert Alerta.objects.count() == 1


# ---- consulta (UC-08) ----------------------------------------------------------------
def test_painel_ordenado_e_encerrado_sai_dos_abertos(banco_limpo, anomalia, gestor):
    a1, _ = emitir_alerta(anomalia(semana_inicio=date(2025, 3, 3), semana_epi=10))
    emitir_alerta(anomalia(semana_inicio=date(2025, 3, 17), semana_epi=12))
    emitir_alerta(anomalia(semana_inicio=date(2025, 3, 10), semana_epi=11))
    alterar_situacao(alerta_id=a1.pk, nova_situacao="encerrado", versao_lida=1, usuario=gestor)
    abertos = list(listar_alertas())
    assert [x.semana_epi for x in abertos] == [12, 11]            # mais recente primeiro
    assert listar_alertas(situacao="todos").count() == 3          # encerrado permanece no histórico
    assert listar_alertas(agravo="Z99", situacao="todos").count() == 0
