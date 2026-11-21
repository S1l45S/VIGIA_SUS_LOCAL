"""Ponte com a detecção do PB02/PB03: lê ``ResultadoDeteccao`` e emite alertas.

É o único módulo de ``alertas`` que conhece ``deteccao``, ``dominio`` e o calendário
da ingestão; o resto do app só vê ``AnomaliaDetectada``.
"""

import logging
from datetime import timedelta

from django.conf import settings

from deteccao.models import ResultadoDeteccao
from deteccao.services.estatistica import FATOR_DESVIO
from dominio.models import Agravo, Municipio
from ingestao.services.calendario import semana_da_data

from .contratos import AnomaliaDetectada
from .dominio import Situacao
from .models import Alerta
from .services import ResultadoEmissao, emitir_alerta

log = logging.getLogger(__name__)


def montar_anomalia(resultado, agravos: dict, municipios: dict, carga_id: str = "") -> AnomaliaDetectada:
    """Converte um ``ResultadoDeteccao`` (ou objeto equivalente) no contrato do PB04."""
    # semana_inicio é a segunda-feira; a SE real começa no domingo anterior.
    ano, semana = semana_da_data(resultado.semana_inicio - timedelta(days=1))
    return AnomaliaDetectada(
        agravo_codigo=resultado.agravo_codigo,
        agravo_nome=agravos.get(resultado.agravo_codigo, resultado.agravo_codigo),
        municipio_codigo=resultado.municipio_codigo,
        municipio_nome=municipios.get(resultado.municipio_codigo, resultado.municipio_codigo),
        ano_epi=ano,
        semana_epi=semana,
        semana_inicio=resultado.semana_inicio,
        observado=resultado.quantidade_observada,
        media=resultado.media_movel,
        desvio=resultado.desvio_padrao,
        limite=resultado.limite_superior,
        janela_semanas=resultado.janela_semanas,
        fator_desvio=FATOR_DESVIO,
        resultado_id=str(resultado.pk),
        carga_id=carga_id,
    )


def _inicio_emissao(agravo, municipio):
    """Limita a emissão às N semanas mais recentes da série (``ALERTAS_SEMANAS_RECENTES``).

    Padrão None = todas as anomalias (RF004 literal). Evita inundar o painel com
    anomalias históricas na primeira carga.
    """
    n = getattr(settings, "ALERTAS_SEMANAS_RECENTES", None)
    if not n:
        return None
    ultimo = (
        ResultadoDeteccao.objects.filter(agravo_codigo=agravo, municipio_codigo=municipio)
        .order_by("-semana_inicio")
        .first()
    )
    return ultimo.semana_inicio - timedelta(weeks=n - 1) if ultimo else None


def sincronizar_alertas(series=None, *, carga_id: str = "") -> ResultadoEmissao:
    """Emite alertas para as semanas em anomalia das ``series`` [(agravo, município)].

    ``series=None`` processa todas as séries com resultado de detecção. Idempotente:
    chamar de novo sem mudança nos resultados não cria nada. Alertas já emitidos
    cuja semana deixou de ser anomalia NÃO são alterados; são devolvidos em
    ``obsoletos`` para a equipe decidir (nunca se apaga alerta, RN03).
    """
    if series is None:
        series = sorted(
            set(
                ResultadoDeteccao.objects.values_list("agravo_codigo", "municipio_codigo")
            )
        )
    series = list(series)
    agravos = dict(Agravo.objects.values_list("codigo", "nome"))
    municipios = dict(Municipio.objects.values_list("codigo_ibge", "nome"))

    res = ResultadoEmissao()
    for agravo, municipio in series:
        desde = _inicio_emissao(agravo, municipio)
        anomalias = ResultadoDeteccao.objects.filter(
            agravo_codigo=agravo, municipio_codigo=municipio, anomalia=True
        )
        if desde:
            anomalias = anomalias.filter(semana_inicio__gte=desde)
        datas = set()
        for r in anomalias.order_by("semana_inicio"):
            datas.add(r.semana_inicio)
            alerta, status = emitir_alerta(montar_anomalia(r, agravos, municipios, carga_id))
            if status == "criado":
                res.criados.append(alerta)
            elif status == "substituido":
                res.criados.append(alerta)
                res.substituidos.append(alerta.substitui)
            else:
                res.inalterados.append(alerta)

        for vigente in Alerta.objects.filter(
            agravo_codigo=agravo, municipio_codigo=municipio, substituido=False
        ).exclude(situacao=Situacao.ENCERRADO.value):
            if vigente.semana_inicio not in datas and (
                desde is None or vigente.semana_inicio >= desde
            ):
                res.obsoletos.append(vigente)

    log.info(
        "alertas: %d criados, %d substituídos, %d inalterados, %d obsoletos",
        len(res.criados), len(res.substituidos), len(res.inalterados), len(res.obsoletos),
    )
    return res
