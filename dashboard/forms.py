from django import forms

DATA_ISO = ["%Y-%m-%d"]


class FiltroSerieForm(forms.Form):
    """Filtros do dashboard: município, agravo e período (RF002, US01)."""

    municipio = forms.ChoiceField(label="Município")
    agravo = forms.ChoiceField(label="Agravo")
    inicio = forms.DateField(
        label="De",
        required=False,
        input_formats=DATA_ISO,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    fim = forms.DateField(
        label="Até",
        required=False,
        input_formats=DATA_ISO,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    def __init__(self, *args, municipios=(), agravos=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["municipio"].choices = list(municipios)
        self.fields["agravo"].choices = list(agravos)

    def clean(self):
        dados = super().clean()
        inicio, fim = dados.get("inicio"), dados.get("fim")
        if inicio and fim and inicio > fim:
            self.add_error("fim", "A data final deve ser igual ou posterior à inicial.")
        return dados
