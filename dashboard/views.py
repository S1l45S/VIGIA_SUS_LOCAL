"""Views do dashboard (PB03). Toda rota exige sessão autenticada (RNF003)."""

from time import perf_counter

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .forms import FiltroSerieForm
from .services import consulta


@login_required
@require_GET
def painel(request):
    """Dashboard de tendências temporais (tela T02)."""
    inicio_medicao = perf_counter()

    municipios = consulta.listar_municipios()
    agravos = consulta.listar_agravos()

    # Sem parâmetros, abre na seleção de maior volume (RF002); com
    # parâmetros, o que o usuário escolheu prevalece.
    dados = {
        chave: valor
        for chave, valor in request.GET.items()
        if chave in {"municipio", "agravo", "inicio", "fim"} and valor
    }
    if "municipio" not in dados or "agravo" not in dados:
        inicial = consulta.selecao_inicial()
        if inicial is None and municipios and agravos:
            inicial = (municipios[0][0], agravos[0][0])
        if inicial:
            dados.setdefault("municipio", inicial[0])
            dados.setdefault("agravo", inicial[1])

    form = FiltroSerieForm(dados, municipios=municipios, agravos=agravos)

    contexto = {
        "form": form,
        "ultima_carga": consulta.ultima_carga_aceita(),
        "sem_catalogo": not municipios or not agravos,
        "serie": None,
        "dados_grafico": None,
    }

    if contexto["sem_catalogo"]:
        return render(request, "dashboard/painel.html", contexto)

    if form.is_valid():
        municipio = form.cleaned_data["municipio"]
        agravo = form.cleaned_data["agravo"]
        inicio, fim = consulta.resolver_periodo(
            municipio,
            agravo,
            form.cleaned_data["inicio"],
            form.cleaned_data["fim"],
        )
        serie = consulta.montar_serie(municipio, agravo, inicio, fim)
        contexto.update(
            serie=serie,
            nome_municipio=dict(municipios).get(municipio, municipio),
            nome_agravo=dict(agravos).get(agravo, agravo),
            periodo_inicio=inicio,
            periodo_fim=fim,
            dados_grafico=None if serie.vazia else serie.para_grafico(),
        )

    contexto["tempo_consulta_ms"] = round((perf_counter() - inicio_medicao) * 1000)
    return render(request, "dashboard/painel.html", contexto)
