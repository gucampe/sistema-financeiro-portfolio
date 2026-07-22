# transacoes/urls.py
from django.urls import path
from .views import (
    adicionar_transacao,
    dados_grafico_receitas_despesas,
    editar_transacao,
    excluir_transacao,
    importar_ofx_confirmar,
    importar_ofx_preview,
    importar_planilha_modelo,
    importar_planilha_preview,
    transferir,
)

app_name = 'transacoes'

urlpatterns = [
    path('', adicionar_transacao, name='historico'),  # ← ESTA É A PÁGINA /transacoes/

    path('adicionar/', adicionar_transacao, name='adicionar'),
    path('transferir/', transferir, name='transferir'),
    path('<int:pk>/editar/', editar_transacao, name='editar'),
    path('<int:pk>/excluir/', excluir_transacao, name='excluir'),
    path('api/grafico/receitas-despesas/', dados_grafico_receitas_despesas, name='grafico_receitas_despesas'),
    path('importar/ofx/preview/', importar_ofx_preview, name='importar_ofx_preview'),
    path('importar/ofx/confirmar/', importar_ofx_confirmar, name='importar_ofx_confirmar'),
    path('importar/planilha/preview/', importar_planilha_preview, name='importar_planilha_preview'),
    path('importar/planilha/confirmar/', importar_ofx_confirmar, name='importar_planilha_confirmar'),
    path('importar/planilha/modelo/', importar_planilha_modelo, name='importar_planilha_modelo'),
]
