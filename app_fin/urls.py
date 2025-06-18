from django.urls import path
from . import views

urlpatterns = [
    # Adicione suas rotas aqui
    path('', views.cadastro, name='cadastro'),
]