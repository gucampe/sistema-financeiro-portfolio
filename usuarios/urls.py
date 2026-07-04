from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import (
    GranaGoPasswordResetCompleteView,
    GranaGoPasswordResetConfirmView,
    GranaGoPasswordResetDoneView,
    GranaGoPasswordResetView,
    configuracoes,
    configuracoes_alterar_senha,
    excluir_conta,
    login_view,
    primeiros_passos,
    primeiros_passos_status,
    privacidade_view,
    termos_view,
)

app_name = "usuarios"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("privacidade/", privacidade_view, name="privacidade"),
    path("termos/", termos_view, name="termos"),
    path("senha/redefinir/", GranaGoPasswordResetView.as_view(), name="password_reset"),
    path("senha/redefinir/enviado/", GranaGoPasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "senha/redefinir/confirmar/<uidb64>/<token>/",
        GranaGoPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "senha/redefinir/concluido/",
        GranaGoPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("configuracoes/", configuracoes, name="configuracoes"),
    path("configuracoes/senha/", configuracoes_alterar_senha, name="configuracoes_senha"),
    path("configuracoes/excluir-conta/", excluir_conta, name="excluir_conta"),
    path("primeiros-passos/", primeiros_passos, name="primeiros_passos"),
    path("primeiros-passos/status/", primeiros_passos_status, name="primeiros_passos_status"),
]
