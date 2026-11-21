import pytest
from django.urls import reverse

from alertas.services import emitir_alerta

pytestmark = pytest.mark.django_db


def test_rotas_sem_sessao_redirecionam_para_login(client, banco_limpo, anomalia):  # RNF003
    a, _ = emitir_alerta(anomalia())
    for url in (reverse("alertas:painel"), reverse("alertas:detalhe", args=[a.pk])):
        r = client.get(url)
        assert r.status_code == 302 and "login" in r["Location"]
    r = client.post(reverse("alertas:alterar_situacao", args=[a.pk]),
                    {"nova_situacao": "encerrado", "versao": 1})
    assert r.status_code == 302 and "login" in r["Location"]
    a.refresh_from_db()
    assert a.situacao == "novo" and len(a.historico) == 1


def test_painel_exibe_campos_do_alerta(cliente_logado, banco_limpo, anomalia):
    emitir_alerta(anomalia())
    html = cliente_logado.get(reverse("alertas:painel")).content.decode()
    for esperado in ("SE 10/2025", "Dengue", "Aracaju", "30", "10,0", "Novo"):
        assert esperado in html


def test_painel_filtra_por_municipio_e_agravo(cliente_logado, criar_serie, anomalia):
    criar_serie([1] * 3)  # só para criar o catálogo
    emitir_alerta(anomalia())
    emitir_alerta(anomalia(agravo_codigo="B01", agravo_nome="Varicela"))
    r = cliente_logado.get(reverse("alertas:painel"), {"agravo": "B01"})
    assert [a.agravo_codigo for a in r.context["pagina"]] == ["B01"]


def test_periodo_invertido_mostra_erro_sem_quebrar(cliente_logado, banco_limpo):
    r = cliente_logado.get(reverse("alertas:painel"), {"inicio": "2025-03-01", "fim": "2025-02-01"})
    assert r.status_code == 200 and "posterior à inicial" in r.content.decode()


def test_fluxo_completo_pela_interface(cliente_logado, banco_limpo, anomalia):
    a, _ = emitir_alerta(anomalia())
    r = cliente_logado.post(
        reverse("alertas:alterar_situacao", args=[a.pk]),
        {"nova_situacao": "em_investigacao", "versao": 1, "observacao": "visita"}, follow=True,
    )
    assert "Situação atualizada" in r.content.decode()
    a.refresh_from_db()
    assert a.situacao == "em_investigacao" and a.historico[-1].usuario_nome == "gestor1"
    assert "visita" in cliente_logado.get(reverse("alertas:detalhe", args=[a.pk])).content.decode()


def test_transicao_invalida_exibe_erro_e_nao_grava(cliente_logado, banco_limpo, anomalia):
    a, _ = emitir_alerta(anomalia())
    cliente_logado.post(reverse("alertas:alterar_situacao", args=[a.pk]),
                        {"nova_situacao": "encerrado", "versao": 1})
    cliente_logado.post(reverse("alertas:alterar_situacao", args=[a.pk]),
                        {"nova_situacao": "novo", "versao": 2})
    a.refresh_from_db()
    assert a.situacao == "encerrado" and len(a.historico) == 2


def test_nao_existe_rota_de_exclusao_nem_edicao_do_historico(cliente_logado, banco_limpo, anomalia):
    a, _ = emitir_alerta(anomalia())
    for metodo in (cliente_logado.delete, cliente_logado.put, cliente_logado.patch,
                   cliente_logado.post):
        assert metodo(reverse("alertas:detalhe", args=[a.pk])).status_code == 405
    assert cliente_logado.get(reverse("alertas:alterar_situacao", args=[a.pk])).status_code == 405
    assert cliente_logado.post(f"/alertas/{a.pk}/excluir/").status_code == 404


def test_id_invalido_retorna_404(cliente_logado, banco_limpo):
    assert cliente_logado.get(reverse("alertas:detalhe", args=["nao-e-objectid"])).status_code == 404


def test_conteudo_do_banco_nao_vira_html_executavel(cliente_logado, banco_limpo, anomalia):
    emitir_alerta(anomalia(municipio_nome="<script>alert(1)</script>"))
    assert "<script>alert(1)</script>" not in cliente_logado.get(
        reverse("alertas:painel")).content.decode()


def test_dashboard_liga_para_os_alertas_da_serie(cliente_logado, criar_serie):
    from alertas.integracao import sincronizar_alertas

    criar_serie([10] * 8 + [30])
    sincronizar_alertas()
    html = cliente_logado.get(reverse("dashboard:painel")).content.decode()
    assert reverse("alertas:painel") in html and "Ver os alertas desta série" in html
