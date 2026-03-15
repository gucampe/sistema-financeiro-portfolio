# transacoes/urls.py
from django.urls import path
from .views import adicionar_transacao, dados_grafico_receitas_despesas, editar_transacao, excluir_transacao



app_name = 'transacoes'

urlpatterns = [
    path('adicionar/', adicionar_transacao, name='adicionar'),
    path('<int:pk>/editar/', editar_transacao, name='editar'),
    path('<int:pk>/excluir/', excluir_transacao, name='excluir'),
    path('api/grafico/receitas-despesas/', dados_grafico_receitas_despesas, name='grafico_receitas_despesas'),

]
