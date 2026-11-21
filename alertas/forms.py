from django import forms

from .dominio import ROTULOS, Situacao, transicoes_permitidas
from .services import FILTRO_ABERTOS, FILTRO_TODOS

DATA_ISO = ["%Y-%m-%d"]
_SITUACOES = (
    [(FILTRO_ABERTOS, "Abertos (novos e em investigação)")]
    + [(s.value, ROTULOS[s]) for s in Situacao]
    + [(FILTRO_TODOS, "Todos")]
)


class FiltroAlertasForm(forms.Form):
    """Filtros do painel. ``municipios``/``agravos`` vêm do catálogo: [(código, nome)]."""

    situacao = forms.ChoiceField(choices=_SITUACOES, required=False, label="Situação")
    municipio = forms.ChoiceField(required=False, label="Município")
    agravo = forms.ChoiceField(required=False, label="Agravo")
    inicio = forms.DateField(
        required=False, label="De", input_formats=DATA_ISO,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    fim = forms.DateField(
        required=False, label="Até", input_formats=DATA_ISO,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    def __init__(self, *args, municipios=(), agravos=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["municipio"].choices = [("", "Todos")] + list(municipios)
        self.fields["agravo"].choices = [("", "Todos")] + list(agravos)

    def clean(self):
        dados = super().clean()
        if dados.get("inicio") and dados.get("fim") and dados["inicio"] > dados["fim"]:
            self.add_error("fim", "A data final deve ser igual ou posterior à inicial.")
        return dados


class AlterarSituacaoForm(forms.Form):
    nova_situacao = forms.ChoiceField(label="Nova situação")
    versao = forms.IntegerField(widget=forms.HiddenInput, min_value=1)
    observacao = forms.CharField(
        label="Observação (opcional)", required=False, max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, alerta, **kwargs):
        super().__init__(*args, **kwargs)
        permitidas = transicoes_permitidas(alerta.situacao, substituido=alerta.substituido)
        self.fields["nova_situacao"].choices = [
            (s.value, ROTULOS[s]) for s in Situacao if s in permitidas
        ]
        self.initial.setdefault("versao", alerta.versao)
