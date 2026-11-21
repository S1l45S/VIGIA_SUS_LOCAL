from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model

from alertas.contratos import AnomaliaDetectada
from alertas.models import Alerta
from deteccao.models import ResultadoDeteccao
from deteccao.services.estatistica import processar_series
from dominio.models import Agravo, Municipio
from ingestao.models import CargaDeDados, RegistroSemanal

SEGUNDA_INICIAL = date(2025, 1, 6)  # segunda-feira


@pytest.fixture
def banco_limpo(db):
    """Zera as coleções usadas pelos testes para o resultado ser determinístico."""
    for modelo in (
        Alerta, ResultadoDeteccao, RegistroSemanal, CargaDeDados, Municipio, Agravo,
    ):
        modelo.objects.all().delete()


@pytest.fixture
def gestor(db):
    return get_user_model().objects.create_user(username="gestor1", password="senha-de-teste-123")


@pytest.fixture
def outro_gestor(db):
    return get_user_model().objects.create_user(username="gestor2", password="senha-de-teste-123")


@pytest.fixture
def cliente_logado(client, gestor):
    client.force_login(gestor)
    return client


@pytest.fixture
def criar_serie(banco_limpo):
    """Catálogo + semanas consecutivas + ResultadoDeteccao (via processar_series real)."""

    def _criar(
        quantidades, *, municipio=("2800308", "Aracaju"), agravo=("A90", "Dengue"),
        inicio=SEGUNDA_INICIAL,
    ):
        Municipio.objects.get_or_create(
            codigo_ibge=municipio[0], defaults={"nome": municipio[1], "uf": "SE"}
        )
        Agravo.objects.get_or_create(codigo=agravo[0], defaults={"nome": agravo[1]})
        registros = [
            RegistroSemanal(
                agravo_codigo=agravo[0], municipio_codigo=municipio[0],
                semana_inicio=inicio + timedelta(weeks=i), semana_ord=i, ano=2025,
                semana_epidemiologica=1, quantidade=q, carga_id="teste",
            )
            for i, q in enumerate(quantidades)
        ]
        RegistroSemanal.objects.bulk_create(registros)
        processar_series(registros)
        return registros

    return _criar


@pytest.fixture
def corrigir_ultima_semana():
    """Simula carga corrigida: troca a quantidade da última semana e reprocessa a série."""

    def _corrigir(agravo, municipio, nova_quantidade):
        serie = RegistroSemanal.objects.filter(
            agravo_codigo=agravo, municipio_codigo=municipio
        ).order_by("semana_inicio")
        ultimo = list(serie)[-1]
        ultimo.quantidade = nova_quantidade
        ultimo.save()
        processar_series(registros=serie)

    return _corrigir


@pytest.fixture
def anomalia():
    def _make(**kw):
        base = {
            "agravo_codigo": "A90", "agravo_nome": "Dengue",
            "municipio_codigo": "2800308", "municipio_nome": "Aracaju",
            "ano_epi": 2025, "semana_epi": 10, "semana_inicio": date(2025, 3, 3),
            "observado": 30, "media": 10.0, "desvio": 0.0, "limite": 10.0,
            "janela_semanas": 8, "fator_desvio": 2, "resultado_id": "r-1",
            "carga_id": "carga-1",
        }
        base.update(kw)
        return AnomaliaDetectada(**base)

    return _make
