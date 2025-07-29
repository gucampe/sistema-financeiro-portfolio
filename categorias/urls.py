from django.urls import path
from .views import categorias_view, adicionar_categoria

app_name = 'categorias'

urlpatterns = [
    path('categorias/', categorias_view, name='home'),
    path('categorias/adicionar/', adicionar_categoria, name='adicionar'),
] 