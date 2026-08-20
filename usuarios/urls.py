from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import RedirectView

from .views import (
    GranaGoPasswordResetCompleteView,
    GranaGoPasswordResetConfirmView,
    GranaGoPasswordResetDoneView,
    GranaGoPasswordResetView,
    captura_lead_view,
    como_funciona_view,
    configuracoes,
    configuracoes_alterar_senha,
    conta_configurar_view,
    excluir_conta,
    faq_view,
    home_view,
    landing_view,
    login_view,
    nossa_historia_view,
    obrigado_view,
    primeiros_passos,
    primeiros_passos_status,
    privacidade_view,
    robots_txt,
    sitemap_xml,
    termos_view,
)

app_name = "usuarios"

urlpatterns = [
    path("", home_view, name="home"),
    path("nossa-historia/", nossa_historia_view, name="nossa_historia"),
    path("como-funciona/", como_funciona_view, name="como_funciona"),
    path("faq/", faq_view, name="faq"),
    path("comece/", landing_view, name="landing"),
    path(
        "primeiros-donos/",
        RedirectView.as_view(pattern_name="usuarios:landing", permanent=True),
        name="landing_legacy",
    ),
    path("captura/", captura_lead_view, name="captura_lead"),
    path("obrigado/", obrigado_view, name="obrigado"),
    path(
        "conta/configurar/<uidb64>/<token>/",
        conta_configurar_view,
        name="conta_configurar",
    ),
    path("login/", login_view, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("politica-de-privacidade/", privacidade_view, name="privacidade"),
    path("termos-de-uso/", termos_view, name="termos"),
    path(
        "privacidade/",
        RedirectView.as_view(pattern_name="usuarios:privacidade", permanent=True),
        name="privacidade_legacy",
    ),
    path(
        "termos/",
        RedirectView.as_view(pattern_name="usuarios:termos", permanent=True),
        name="termos_legacy",
    ),
    path("robots.txt", robots_txt, name="robots"),
    path("sitemap.xml", sitemap_xml, name="sitemap"),
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
