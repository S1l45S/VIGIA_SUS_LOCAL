"""Ponto de integração com a ingestão: carga -> detecção -> alertas na mesma transação."""
import csv
from datetime import date

import pytest

from alertas.models import Alerta
from dominio.models import Agravo, Municipio
from ingestao.services.carga import importar_csv

pytestmark = pytest.mark.django_db


def _csv(tmp_path, quantidades):
    caminho = tmp_path / "carga.csv"
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["agravo_codigo", "agravo_nome", "municipio_codigo", "municipio_nome",
                    "ano", "semana_epidemiologica", "contagem"])
        for i, q in enumerate(quantidades, start=1):  # ISO 2025-W01.. (segunda-feira)
            w.writerow(["A90", "Dengue", "2800308", "Aracaju", 2025, i, q])
    return caminho


@pytest.fixture
def catalogo(banco_limpo):
    Municipio.objects.create(codigo_ibge="2800308", nome="Aracaju", uf="SE")
    Agravo.objects.create(codigo="A90", nome="Dengue")


def test_carga_emite_alerta_da_anomalia(catalogo, tmp_path):
    carga = importar_csv(_csv(tmp_path, [10] * 8 + [30]))
    assert carga.status == "ACEITA"
    a = Alerta.objects.get()
    assert a.observado == 30 and a.carga_id == str(carga.pk)
    assert a.semana_inicio == date(2025, 2, 24)  # segunda-feira da ISO 2025-W09


def test_recarregar_o_mesmo_arquivo_nao_duplica(catalogo, tmp_path):
    arquivo = _csv(tmp_path, [10] * 8 + [30])
    importar_csv(arquivo)
    importar_csv(arquivo)
    assert Alerta.objects.count() == 1


def test_carga_sem_anomalia_nao_emite_alerta(catalogo, tmp_path):
    assert importar_csv(_csv(tmp_path, [10, 11, 9, 10, 11, 9, 10, 11, 10])).status == "ACEITA"
    assert Alerta.objects.count() == 0
