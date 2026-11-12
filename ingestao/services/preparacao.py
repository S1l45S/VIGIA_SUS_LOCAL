"""Orquestra a preparação do CSV a partir de qualquer fonte"""

from datetime import UTC, datetime

from ingestao.fontes.base import verificar_notificacoes
from ingestao.services.agregacao import (
    CALENDARIO_DO_CSV,
    agregar_semanal,
    ultima_semana,
)
from ingestao.services.calendario import deslocar_semana, inicio_semana_epidemiologica
from ingestao.services.saida import escrever_csv, escrever_metadados, sha256_arquivo


def _semana_texto(ano_semana):
    return f"{ano_semana[0]}{ano_semana[1]:02d}"


def preparar_csv(
    fonte,
    *,
    agravo_codigo,
    agravo_nome,
    municipios,
    anos,
    inicio,
    saida,
    fim=None,
    cortar_ultimas=4,
    agora=None,
):
    """Obtem as notificações da fonte, agrega e grava o CSV com metadados

    Se fim não for informado, usa a última semana da fonte menos
    cortar_ultimas, porque as semanas mais recentes são subnotificadas.
    """
    inicio_semana_epidemiologica(*inicio)

    notificacoes = fonte.obter(agravo_codigo=agravo_codigo, anos=list(anos))
    verificar_notificacoes(notificacoes)

    corte_aplicado = 0
    if fim is None:
        fim = deslocar_semana(*ultima_semana(notificacoes.tabela), -cortar_ultimas)
        corte_aplicado = cortar_ultimas

    resultado = agregar_semanal(
        notificacoes.tabela,
        agravo_codigo=agravo_codigo,
        agravo_nome=agravo_nome,
        municipios=municipios,
        inicio=inicio,
        fim=fim,
    )
    escrever_csv(resultado.tabela, saida)

    agora = agora or datetime.now(UTC)
    metadados = {
        "fonte": notificacoes.fonte,
        "tipo_semana": notificacoes.tipo_semana,
        "agravo": {"codigo": agravo_codigo, "nome": agravo_nome},
        "periodo": {"inicio": _semana_texto(inicio), "fim": _semana_texto(fim)},
        "calendario_do_csv": CALENDARIO_DO_CSV,
        "semanas_cortadas": corte_aplicado,
        "extraido_em": agora.isoformat(),
        "arquivos_brutos": notificacoes.arquivos_brutos,
        "municipios": len(municipios),
        "linhas_lidas": notificacoes.linhas_lidas,
        "notificacoes_contadas": resultado.notificacoes_contadas,
        "descartes": {
            "fonte": notificacoes.descartes,
            "agregacao": resultado.descartes,
        },
        "csv_sha256": sha256_arquivo(saida),
    }
    escrever_metadados(saida, metadados)
    return resultado, metadados, fim