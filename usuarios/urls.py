from django.urls import path
from .views import cadastro_usuario, login

app_name = 'usuarios'

urlpatterns = [
    path('cadastro/', cadastro_usuario, name='cadastro_usuario'),
    path('login/', login, name='login'),
] 