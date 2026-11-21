from django.urls import path

from . import views

app_name = "alertas"

urlpatterns = [
    path("", views.PainelView.as_view(), name="painel"),
    path("<str:pk>/", views.DetalheView.as_view(), name="detalhe"),
    path("<str:pk>/situacao/", views.AlterarSituacaoView.as_view(), name="alterar_situacao"),
]
