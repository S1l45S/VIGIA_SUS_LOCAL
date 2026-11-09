from collections import defaultdict
from datetime import timedelta
from math import isfinite, sqrt

JANELA_SEMANAS = 8
FATOR_DESVIO = 2
DIAS_POR_SEMANA = 7


def calcular_referencias(valores, janela=JANELA_SEMANAS):
    """Calcula média, desvio padrão populacional e limite superior dos valores."""
    if isinstance(janela, bool) or not isinstance(janela, int) or janela < 1:
        raise ValueError("A janela deve ser um inteiro positivo.")

    amostra = list(valores)
    if len(amostra) != janela:
        raise ValueError(f"São necessários exatamente {janela} valores históricos.")
    if any(
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
        or not isfinite(valor)
        for valor in amostra
    ):
        raise ValueError("Os valores históricos devem ser números finitos.")

    media = sum(amostra) / janela
    variancia = sum((valor - media) ** 2 for valor in amostra) / janela
    desvio = sqrt(variancia)
    return {
        "media_movel": media,
        "desvio_padrao": desvio,
        "limite_superior": media + FATOR_DESVIO * desvio,
    }


def _campo(registro, campo):
    if isinstance(registro, dict):
        return registro[campo]
    return getattr(registro, campo)


def processar_series(registros=None, *, janela=JANELA_SEMANAS, persistir=True):
    """Avalia cada semana contra as *oito semanas anteriores* e persiste o resultado.

    ``registros`` permite fornecer registros diretamente (útil para testes). Se omitido,
    consulta os RegistroSemanal armazenados. Retorna apenas semanas que têm histórico
    suficiente, ordenadas por agravo, município e data.
    """
    if registros is None:
        from ingestao.models import RegistroSemanal

        registros = RegistroSemanal.objects.all()
    if isinstance(janela, bool) or not isinstance(janela, int) or janela < 1:
        raise ValueError("A janela deve ser um inteiro positivo.")

    series = defaultdict(list)
    for registro in registros:
        chave = (
            _campo(registro, "agravo_codigo"),
            _campo(registro, "municipio_codigo"),
        )
        series[chave].append(registro)

    resultados = []
    for (agravo, municipio), itens in sorted(series.items()):
        itens.sort(key=lambda item: _campo(item, "semana_inicio"))
        datas = [_campo(item, "semana_inicio") for item in itens]
        if len(set(datas)) != len(datas):
            raise ValueError(
                f"Há semanas duplicadas na série de agravo {agravo}, município {municipio}."
            )

        for posicao in range(janela, len(itens)):
            historico = itens[posicao - janela:posicao]
            atual = itens[posicao]
            if any(
                datas[indice] - datas[indice - 1] != timedelta(days=DIAS_POR_SEMANA)
                for indice in range(posicao - janela + 1, posicao + 1)
            ):
                continue
            refs = calcular_referencias(
                [_campo(item, "quantidade") for item in historico], janela
            )
            quantidade = _campo(atual, "quantidade")
            resultado = {
                "agravo_codigo": agravo,
                "municipio_codigo": municipio,
                "semana_inicio": _campo(atual, "semana_inicio"),
                "quantidade_observada": quantidade,
                **refs,
                "anomalia": quantidade > refs["limite_superior"],
                "janela_semanas": janela,
            }
            resultados.append(resultado)
            if persistir:
                from deteccao.models import ResultadoDeteccao

                ResultadoDeteccao.objects.update_or_create(
                    agravo_codigo=agravo,
                    municipio_codigo=municipio,
                    semana_inicio=resultado["semana_inicio"],
                    defaults={
                        key: value
                        for key, value in resultado.items()
                        if key not in {
                            "agravo_codigo", "municipio_codigo", "semana_inicio"
                        }
                    },
                )
    return resultados
