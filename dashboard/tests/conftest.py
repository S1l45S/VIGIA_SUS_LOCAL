from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model

from deteccao.models import ResultadoDeteccao
from deteccao.services.estatistica import processar_series
from dominio.models import Agravo, Municipio
from ingestao.models import CargaDeDados, RegistroSemanal

SEGUNDA_INICIAL = date(2025, 1, 6)  # segunda-feira


@pytest.fixture
def banco_limpo(db):
    """Zera as coleções lidas pelo dashboard para o teste ser determinístico."""
    for modelo in (
        ResultadoDeteccao, RegistroSemanal, CargaDeDados, Municipio, Agravo,
    ):
        modelo.objects.all().delete()


@pytest.fixture
def gestor(db):
    return get_user_model().objects.create_user(
        username="gestor-teste", password="senha-de-teste-123"
    )


@pytest.fixture
def cliente_logado(client, gestor):
    client.force_login(gestor)
    return client


@pytest.fixture
def criar_serie(banco_limpo):
    """Cria catálogo + semanas consecutivas + resultado da detecção."""

    def _criar(
        quantidades,
        *,
        municipio=("2800308", "Aracaju"),
        agravo=("A90", "Dengue"),
        inicio=SEGUNDA_INICIAL,
    ):
        Municipio.objects.get_or_create(
            codigo_ibge=municipio[0],
            defaults={"nome": municipio[1], "uf": "SE"},
        )
        Agravo.objects.get_or_create(
            codigo=agravo[0], defaults={"nome": agravo[1]}
        )
        registros = [
            RegistroSemanal(
                agravo_codigo=agravo[0],
                municipio_codigo=municipio[0],
                semana_inicio=inicio + timedelta(weeks=i),
                semana_ord=i,
                ano=2025,
                semana_epidemiologica=1,
                quantidade=quantidade,
                carga_id="teste",
            )
            for i, quantidade in enumerate(quantidades)
        ]
        RegistroSemanal.objects.bulk_create(registros)
        processar_series(registros)
        return registros

    return _criar