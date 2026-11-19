from datetime import timedelta

import pytest
from django.urls import reverse

from dashboard.tests.conftest import SEGUNDA_INICIAL

pytestmark = pytest.mark.django_db

URL = "dashboard:painel"


def test_rota_sem_sessao_redireciona_para_login(client, banco_limpo):
    resposta = client.get(reverse(URL))

    assert resposta.status_code == 302
    assert "login" in resposta["Location"]


def test_rota_nao_aceita_escrita(cliente_logado, banco_limpo):
    assert cliente_logado.post(reverse(URL)).status_code == 405


def test_painel_abre_na_selecao_de_maior_volume(cliente_logado, criar_serie):
    criar_serie([10] * 8 + [30])

    resposta = cliente_logado.get(reverse(URL))

    assert resposta.status_code == 200
    assert resposta.context["serie"].municipio_codigo == "2800308"
    assert resposta.context["serie"].agravo_codigo == "A90"
    assert b'id="grafico-serie"' in resposta.content
    assert b"dados-grafico" in resposta.content


def test_dados_do_grafico_trazem_observado_media_e_limite(
    cliente_logado, criar_serie
):
    criar_serie([10] * 8 + [30])

    dados = cliente_logado.get(reverse(URL)).context["dados_grafico"]

    assert dados["observado"][-1] == 30
    assert dados["media_movel"][-1] == 10
    assert dados["limite_superior"][-1] == 10


def test_filtros_de_municipio_agravo_e_periodo(cliente_logado, criar_serie):
    criar_serie([1] * 12)
    criar_serie([40] * 12, municipio=("2800100", "Outra cidade"))
    criar_serie([7] * 12, agravo=("B01", "Varicela"))

    resposta = cliente_logado.get(
        reverse(URL),
        {
            "municipio": "2800308",
            "agravo": "B01",
            "inicio": SEGUNDA_INICIAL.isoformat(),
            "fim": (SEGUNDA_INICIAL + timedelta(weeks=3)).isoformat(),
        },
    )

    serie = resposta.context["serie"]
    assert serie.agravo_codigo == "B01"
    assert [p.observado for p in serie.pontos] == [7, 7, 7, 7]


def test_periodo_sem_registros_mostra_mensagem_e_nao_desenha_grafico(
    cliente_logado, criar_serie
):
    criar_serie([5] * 10)

    resposta = cliente_logado.get(
        reverse(URL),
        {
            "municipio": "2800308",
            "agravo": "A90",
            "inicio": "2020-01-06",
            "fim": "2020-03-02",
        },
    )

    assert resposta.status_code == 200
    assert "sem notificações no período" in resposta.content.decode()
    assert b'id="grafico-serie"' not in resposta.content


def test_periodo_invertido_mostra_erro_sem_quebrar(cliente_logado, criar_serie):
    criar_serie([5] * 10)

    resposta = cliente_logado.get(
        reverse(URL),
        {
            "municipio": "2800308",
            "agravo": "A90",
            "inicio": "2025-03-01",
            "fim": "2025-02-01",
        },
    )

    assert resposta.status_code == 200
    assert resposta.context["serie"] is None
    assert "posterior à inicial" in resposta.content.decode()


def test_municipio_desconhecido_e_rejeitado_pelo_formulario(
    cliente_logado, criar_serie
):
    criar_serie([5] * 10)

    resposta = cliente_logado.get(
        reverse(URL), {"municipio": "9999999", "agravo": "A90"}
    )

    assert resposta.status_code == 200
    assert resposta.context["serie"] is None
    assert resposta.context["form"].errors


def test_data_malformada_nao_gera_erro_500(cliente_logado, criar_serie):
    criar_serie([5] * 10)

    resposta = cliente_logado.get(
        reverse(URL),
        {"municipio": "2800308", "agravo": "A90", "inicio": "ontem"},
    )

    assert resposta.status_code == 200
    assert resposta.context["form"].errors


def test_catalogo_vazio_orienta_o_usuario(cliente_logado, banco_limpo):
    resposta = cliente_logado.get(reverse(URL))

    assert resposta.status_code == 200
    assert resposta.context["sem_catalogo"] is True
    assert "Nenhum município ou agravo cadastrado" in resposta.content.decode()


def test_serie_curta_avisa_historico_insuficiente(cliente_logado, criar_serie):
    criar_serie([5, 6, 7])

    resposta = cliente_logado.get(reverse(URL))

    assert "Histórico insuficiente" in resposta.content.decode()


def test_conteudo_do_banco_nao_vira_html_executavel(
    cliente_logado, criar_serie
):
    criar_serie(
        [1] * 10, municipio=("2800308", "<script>alert(1)</script>")
    )

    html = cliente_logado.get(reverse(URL)).content.decode()

    assert "<script>alert(1)</script>" not in html