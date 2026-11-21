from datetime import timedelta
from statistics import quantiles
from time import perf_counter

import pytest
from django.urls import reverse

from dashboard.tests.conftest import SEGUNDA_INICIAL
from deteccao.models import ResultadoDeteccao
from deteccao.services.estatistica import processar_series
from dominio.models import Agravo, Municipio
from ingestao.models import RegistroSemanal

pytestmark = pytest.mark.django_db

MUNICIPIOS = 20
AGRAVOS = 5
SEMANAS = 100  # 20 × 5 × 100 = 10.000 registros
AMOSTRA = 30
LIMITE_SEGUNDOS = 3.0


@pytest.fixture
def base_de_10_mil(banco_limpo):
    municipios = [(f"28{i:05d}", f"Municipio {i}") for i in range(MUNICIPIOS)]
    agravos = [(f"AG{i}", f"Agravo {i}") for i in range(AGRAVOS)]
    Municipio.objects.bulk_create(
        [Municipio(codigo_ibge=c, nome=n, uf="SE") for c, n in municipios]
    )
    Agravo.objects.bulk_create([Agravo(codigo=c, nome=n) for c, n in agravos])

    registros = [
        RegistroSemanal(
            agravo_codigo=agravo,
            municipio_codigo=municipio,
            semana_inicio=SEGUNDA_INICIAL + timedelta(weeks=semana),
            semana_ord=semana,
            ano=2025,
            semana_epidemiologica=1,
            quantidade=(semana * 7 + indice) % 23,
            carga_id="desempenho",
        )
        for indice, (municipio, _) in enumerate(municipios)
        for agravo, _ in agravos
        for semana in range(SEMANAS)
    ]
    RegistroSemanal.objects.bulk_create(registros, batch_size=1000)

    resultados = processar_series(registros, persistir=False)
    ResultadoDeteccao.objects.bulk_create(
        [ResultadoDeteccao(**r) for r in resultados], batch_size=1000
    )
    assert RegistroSemanal.objects.count() == 10_000
    return municipios[0][0], agravos[0][0]


def test_p95_da_consulta_da_serie_abaixo_de_3_segundos(
    cliente_logado, base_de_10_mil
):
    municipio, agravo = base_de_10_mil
    url = reverse("dashboard:painel")
    tempos = []

    for _ in range(AMOSTRA):
        inicio = perf_counter()
        resposta = cliente_logado.get(
            url, {"municipio": municipio, "agravo": agravo}
        )
        tempos.append(perf_counter() - inicio)
        assert resposta.status_code == 200

    p95 = quantiles(tempos, n=20)[-1]
    print(
        f"\n[RNF001] n={AMOSTRA} mediana={sorted(tempos)[AMOSTRA // 2]:.3f}s "
        f"p95={p95:.3f}s máx={max(tempos):.3f}s"
    )
    assert p95 < LIMITE_SEGUNDOS


def test_abertura_sem_filtros_tambem_cabe_no_limite(
    cliente_logado, base_de_10_mil
):
    """Sem parâmetros o painel calcula a seleção inicial (2 agregações)."""
    inicio = perf_counter()
    resposta = cliente_logado.get(reverse("dashboard:painel"))
    duracao = perf_counter() - inicio

    assert resposta.status_code == 200
    print(f"\n[RNF001] abertura sem filtros: {duracao:.3f}s")
    assert duracao < LIMITE_SEGUNDOS