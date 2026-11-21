"""Views do painel de alertas (PB04). Toda rota exige sessão autenticada (RNF003)."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.views import View

from dashboard.services import consulta

from .dominio import AlertaNaoEncontrado, ErroDeAlerta
from .forms import AlterarSituacaoForm, FiltroAlertasForm
from .models import Alerta
from .services import FILTRO_ABERTOS, alterar_situacao, contadores, listar_alertas, obter_alerta


def _alerta_ou_404(pk) -> Alerta:
    try:
        return obter_alerta(pk)
    except AlertaNaoEncontrado as exc:
        raise Http404(str(exc)) from exc


class PainelView(LoginRequiredMixin, View):
    """Painel de alertas (tela T03)."""

    http_method_names = ["get"]
    por_pagina = 20

    def get(self, request):
        form = FiltroAlertasForm(
            request.GET or None,
            municipios=consulta.listar_municipios(),
            agravos=consulta.listar_agravos(),
        )
        filtros = form.cleaned_data if form.is_valid() else {}
        qs = listar_alertas(
            situacao=filtros.get("situacao") or FILTRO_ABERTOS,
            municipio=filtros.get("municipio", ""),
            agravo=filtros.get("agravo", ""),
            inicio=filtros.get("inicio"),
            fim=filtros.get("fim"),
        )
        pagina = Paginator(qs, self.por_pagina).get_page(request.GET.get("pagina"))
        params = request.GET.copy()
        params.pop("pagina", None)
        return render(request, "alertas/painel.html", {
            "form": form,
            "pagina": pagina,
            "contadores": contadores(),
            "querystring": params.urlencode(),
        })


class DetalheView(LoginRequiredMixin, View):
    http_method_names = ["get"]

    def get(self, request, pk):
        alerta = _alerta_ou_404(pk)
        form = AlterarSituacaoForm(alerta=alerta)
        return render(request, "alertas/detalhe.html", {
            "alerta": alerta,
            "historico": sorted(alerta.historico, key=lambda r: r.em, reverse=True),
            "form": form,
            "pode_alterar": bool(form.fields["nova_situacao"].choices),
        })


class AlterarSituacaoView(LoginRequiredMixin, View):
    """Somente POST. Não existe view de edição do histórico nem de exclusão (RN03)."""

    http_method_names = ["post"]

    def post(self, request, pk):
        alerta = _alerta_ou_404(pk)
        form = AlterarSituacaoForm(request.POST, alerta=alerta)
        if not form.is_valid():
            erros = "; ".join(e for lista in form.errors.values() for e in lista)
            messages.error(request, f"Dados inválidos: {erros}")
            return redirect("alertas:detalhe", pk=pk)
        try:
            novo = alterar_situacao(
                alerta_id=pk,
                nova_situacao=form.cleaned_data["nova_situacao"],
                versao_lida=form.cleaned_data["versao"],
                usuario=request.user,
                observacao=form.cleaned_data["observacao"],
            )
        except ErroDeAlerta as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"Situação atualizada para “{novo.rotulo_situacao}”.")
        return redirect("alertas:detalhe", pk=pk)
