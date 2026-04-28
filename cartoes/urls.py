from django.urls import path

from . import views

app_name = "cartoes"

urlpatterns = [
    path("", views.cartoes_home, name="home"),
    path("salvar/", views.salvar_cartao, name="salvar"),
    path("<int:id>/excluir/", views.excluir_cartao, name="excluir"),
    path("<int:cartao_id>/faturas/", views.faturas_cartao, name="faturas"),
    path("<int:cartao_id>/faturas/<int:fatura_id>/", views.fatura_detalhe, name="fatura_detalhe"),
    path(
        "<int:cartao_id>/faturas/<int:fatura_id>/pagar/",
        views.pagar_fatura_view,
        name="pagar_fatura",
    ),
    path(
        "<int:cartao_id>/faturas/<int:fatura_id>/lancamentos/<int:transacao_id>/mover/",
        views.mover_lancamento_fatura_view,
        name="mover_lancamento_fatura",
    ),
]
