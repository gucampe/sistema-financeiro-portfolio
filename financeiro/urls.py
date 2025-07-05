# financeiro/urls.py
from django.urls import path
from .views import adicionar_transacao, dados_grafico_receitas_despesas


app_name = 'financeiro'

urlpatterns = [
    path('adicionar/', adicionar_transacao, name='adicionar'),
    path('api/grafico/receitas-despesas/', dados_grafico_receitas_despesas, name='grafico_receitas_despesas'),

]
