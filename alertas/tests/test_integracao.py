"""Ponte PB02/PB03 -> PB04: ResultadoDeteccao vira Alerta."""
from datetime import date
from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.management import call_command

from alertas.integracao import montar_anomalia, sincronizar_alertas
from alertas.models import Alerta


def test_montar_anomalia_usa_se_real_e_nomes_do_catalogo():  # sem banco
    r = SimpleNamespace(
        pk="abc", agravo_codigo="A90", municipio_codigo="2800308",
        semana_inicio=date(2025, 3, 3),  # segunda-feira; a SE começa no domingo 02/03
        quantidade_observada=30, media_movel=10.0, desvio_padrao=0.0,
        limite_superior=10.0, janela_semanas=8,
    )
    a = montar_anomalia(r, {"A90": "Dengue"}, {"2800308": "Aracaju"}, "carga-9")
    assert (a.ano_epi, a.semana_epi) == (2025, 10)
    assert (a.agravo_nome, a.municipio_nome, a.carga_id, a.resultado_id) == (
        "Dengue", "Aracaju", "carga-9", "abc")
    assert a.fator_desvio == 2


def test_montar_anomalia_sem_catalogo_cai_no_codigo():  # sem banco
    r = SimpleNamespace(
        pk=1, agravo_codigo="X", municipio_codigo="Y", semana_inicio=date(2025, 3, 3),
        quantidade_observada=5, media_movel=1.0, desvio_padrao=0.5, limite_superior=2.0,
        janela_semanas=8,
    )
    a = montar_anomalia(r, {}, {})
    assert (a.agravo_nome, a.municipio_nome) == ("X", "Y")


@pytest.mark.django_db
def test_anomalia_detectada_vira_alerta(criar_serie):
    criar_serie([10] * 8 + [30])
    res = sincronizar_alertas()
    assert res.total_criados == 1
    a = Alerta.objects.get()
    assert (a.agravo_codigo, a.municipio_codigo, a.observado) == ("A90", "2800308", 30)
    assert a.agravo_nome == "Dengue" and a.municipio_nome == "Aracaju"
    assert a.limite == 10 and a.janela_semanas == 8 and a.situacao == "novo"


@pytest.mark.django_db
def test_sincronizar_duas_vezes_nao_duplica(criar_serie):
    criar_serie([10] * 8 + [30])
    sincronizar_alertas()
    res = sincronizar_alertas()
    assert res.total_criados == 0 and len(res.inalterados) == 1
    assert Alerta.objects.count() == 1


@pytest.mark.django_db
def test_serie_normal_ou_curta_nao_gera_alerta(criar_serie):
    criar_serie([10, 11, 9, 10, 11, 9, 10, 11, 10])
    criar_serie([5, 6, 7], agravo=("B01", "Varicela"))
    assert sincronizar_alertas().total_criados == 0
    assert Alerta.objects.count() == 0


@pytest.mark.django_db
def test_carga_corrigida_substitui_e_mantem_historico(criar_serie, corrigir_ultima_semana, gestor):
    from alertas.services import alterar_situacao

    criar_serie([10] * 8 + [30])
    sincronizar_alertas()
    antigo = Alerta.objects.get()
    alterar_situacao(alerta_id=antigo.pk, nova_situacao="em_investigacao",
                     versao_lida=1, usuario=gestor)

    corrigir_ultima_semana("A90", "2800308", 40)
    res = sincronizar_alertas()

    assert len(res.substituidos) == 1
    antigo.refresh_from_db()
    assert antigo.substituido and antigo.situacao == "em_investigacao"
    novo = Alerta.objects.get(substituido=False)
    assert novo.observado == 40 and novo.situacao == "novo" and novo.substitui == antigo.pk


@pytest.mark.django_db
def test_semana_que_deixou_de_ser_anomalia_vira_obsoleto_sem_apagar(
    criar_serie, corrigir_ultima_semana
):
    criar_serie([10] * 8 + [30])
    sincronizar_alertas()
    corrigir_ultima_semana("A90", "2800308", 10)
    res = sincronizar_alertas()
    assert len(res.obsoletos) == 1 and Alerta.objects.count() == 1


@pytest.mark.django_db
def test_limite_de_semanas_recentes(criar_serie, settings):
    criar_serie([10] * 8 + [30] + [10] * 8 + [60])  # anomalias nas semanas 9 e 18
    settings.ALERTAS_SEMANAS_RECENTES = None
    assert sincronizar_alertas().total_criados == 2
    Alerta.objects.all().delete()
    settings.ALERTAS_SEMANAS_RECENTES = 3
    assert sincronizar_alertas().total_criados == 1


@pytest.mark.django_db
def test_comando_gerar_alertas(criar_serie):
    criar_serie([10] * 8 + [30])
    saida = StringIO()
    call_command("gerar_alertas", stdout=saida)
    assert "Alertas criados: 1" in saida.getvalue()
    assert Alerta.objects.count() == 1
