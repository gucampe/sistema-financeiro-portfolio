from django.urls import path
from .views import categorias_view, adicionar_categoria, excluir_categoria

urlpatterns = [
    path('categorias/', categorias_view, name='home'),
    path('categorias/adicionar/', adicionar_categoria, name='adicionar'),
    path('categorias/excluir/<int:id>/', excluir_categoria, name='excluir'),  # nova
]
