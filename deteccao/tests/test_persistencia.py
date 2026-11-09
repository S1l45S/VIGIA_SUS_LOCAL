import csv
from datetime import date, timedelta
from uuid import uuid4

import pytest

from deteccao.models import ResultadoDeteccao
from deteccao.services.estatistica import processar_series
from dominio.models import Agravo, Municipio
from ingestao.models import RegistroSemanal
from ingestao.services.carga import importar_csv


@pytest.mark.django_db
def test_persiste_resultados_e_atualiza_sem_duplicar():
    codigo_agravo = f"AGR-{uuid4().hex[:12]}"
    codigo_municipio = uuid4().hex[:7]
    inicio = date(2025, 1, 6)
    for indice in range(9):
        RegistroSemanal.objects.create(
            agravo_codigo=codigo_agravo,
            municipio_codigo=codigo_municipio,
            semana_inicio=inicio + timedelta(weeks=indice),
            semana_ord=indice,
            ano=2025,
            semana_epidemiologica=indice + 2,
            quantidade=10 if indice < 8 else 30,
            carga_id="teste-persistencia",
        )

    processar_series()
    processar_series()

    resultados = ResultadoDeteccao.objects.filter(
        agravo_codigo=codigo_agravo,
        municipio_codigo=codigo_municipio,
    )
    assert resultados.count() == 1
    resultado = resultados.get()
    assert resultado.quantidade_observada == 30
    assert resultado.media_movel == 10
    assert resultado.desvio_padrao == 0
    assert resultado.limite_superior == 10
    assert resultado.anomalia is True


@pytest.mark.django_db
def test_importacao_aceita_processa_e_persiste_a_serie(tmp_path):
    codigo_agravo = f"AGR-{uuid4().hex[:12]}"
    codigo_municipio = uuid4().hex[:7]
    nome_agravo = "Agravo de teste"
    nome_municipio = "Municipio de teste"
    Agravo.objects.create(codigo=codigo_agravo, nome=nome_agravo)
    Municipio.objects.create(
        codigo_ibge=codigo_municipio,
        nome=nome_municipio,
        uf="SE",
    )

    caminho = tmp_path / "serie.csv"
    colunas = [
        "agravo_codigo",
        "agravo_nome",
        "municipio_codigo",
        "municipio_nome",
        "ano",
        "semana_epidemiologica",
        "contagem",
    ]
    inicio = date(2025, 1, 6)
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas)
        escritor.writeheader()
        for indice in range(9):
            semana = inicio + timedelta(weeks=indice)
            escritor.writerow({
                "agravo_codigo": codigo_agravo,
                "agravo_nome": nome_agravo,
                "municipio_codigo": codigo_municipio,
                "municipio_nome": nome_municipio,
                "ano": semana.isocalendar().year,
                "semana_epidemiologica": semana.isocalendar().week,
                "contagem": 10 if indice < 8 else 30,
            })

    carga = importar_csv(caminho)

    assert carga.status == "ACEITA"
    resultado = ResultadoDeteccao.objects.get(
        agravo_codigo=codigo_agravo,
        municipio_codigo=codigo_municipio,
        semana_inicio=inicio + timedelta(weeks=8),
    )
    assert resultado.quantidade_observada == 30
    assert resultado.anomalia is True
