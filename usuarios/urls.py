from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import (
    configuracoes,
    configuracoes_alterar_senha,
    login_view,
)

app_name = "usuarios"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("configuracoes/", configuracoes, name="configuracoes"),
    path("configuracoes/senha/", configuracoes_alterar_senha, name="configuracoes_senha"),
]
