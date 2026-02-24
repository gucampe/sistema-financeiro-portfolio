from django.urls import path
from .views import (
    categorias_view,
    adicionar_categoria,
    arquivar_categoria,
    restaurar_categoria,
    excluir_categoria,
    verificar_exclusao_categoria,
    listar_categorias_ativas,
    excluir_categoria_com_migracao,
)

urlpatterns = [
    path('categorias/', categorias_view, name='home'),
    path('categorias/adicionar/', adicionar_categoria, name='adicionar'),
    path('categorias/arquivar/', arquivar_categoria, name='arquivar'),
    path('categorias/restaurar/', restaurar_categoria, name='restaurar'),
    path('categorias/excluir/<int:id>/', excluir_categoria, name='excluir'),
    path('categorias/verificar-exclusao/<int:id>/', verificar_exclusao_categoria, name='verificar_exclusao'),
    path('categorias/listar-ativas/', listar_categorias_ativas, name='listar_ativas'),
    path('categorias/excluir-com-migracao/', excluir_categoria_com_migracao, name='excluir_com_migracao'),
]
