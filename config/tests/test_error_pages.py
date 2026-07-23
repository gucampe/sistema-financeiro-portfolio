"""Testes das páginas de erro brandadas do GranaGo."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse

from config.axes_lockout import lockout_response
from config.error_handlers import handler403, handler404, handler500


User = get_user_model()


def _assert_branded_error(resp, *, status: int, heading_fragment: str):
    assert resp.status_code == status
    content = resp.content.decode("utf-8")
    assert "GranaGo" in content
    assert heading_fragment in content
    assert "Traceback" not in content
    assert "<main" in content
    assert 'lang="pt-BR"' in content
    assert resp.get("Cache-Control") == "no-store"
    assert "noindex" in (resp.get("X-Robots-Tag") or "")


@override_settings(DEBUG=False, APP_HOST="", LANDING_HOSTS="", MAINTENANCE_MODE=False)
@pytest.mark.django_db
def test_404_branded_page():
    client = Client()
    resp = client.get("/rota-inexistente-erro-pages-xyz/")
    _assert_branded_error(resp, status=404, heading_fragment="Página não encontrada")
    assert "não existe ou não está mais disponível" in resp.content.decode("utf-8")


@override_settings(DEBUG=False, APP_HOST="", LANDING_HOSTS="", MAINTENANCE_MODE=False)
@pytest.mark.django_db
def test_403_handler_branded():
    rf = RequestFactory()
    request = rf.get("/qualquer/")
    request.user = type("U", (), {"is_authenticated": False})()
    resp = handler403(request, exception=Exception("forbidden"))
    _assert_branded_error(resp, status=403, heading_fragment="Acesso negado")


@override_settings(DEBUG=False, APP_HOST="", LANDING_HOSTS="", MAINTENANCE_MODE=False)
@pytest.mark.django_db
def test_csrf_failure_uses_403_page():
    client = Client(enforce_csrf_checks=True)
    resp = client.post(reverse("usuarios:login"), {"email": "a@b.com", "password": "x"})
    _assert_branded_error(resp, status=403, heading_fragment="Acesso negado")


@override_settings(DEBUG=False, APP_HOST="", LANDING_HOSTS="", MAINTENANCE_MODE=False)
@pytest.mark.django_db
def test_429_lockout_branded():
    rf = RequestFactory()
    request = rf.get("/login/")
    request.user = type("U", (), {"is_authenticated": False})()
    resp = lockout_response(request, credentials={"username": "a@b.com"})
    _assert_branded_error(resp, status=429, heading_fragment="Muitas tentativas")
    assert resp.get("Retry-After") is not None


@override_settings(DEBUG=False, APP_HOST="", LANDING_HOSTS="", MAINTENANCE_MODE=False)
@pytest.mark.django_db
def test_500_handler_branded_no_traceback():
    rf = RequestFactory()
    request = rf.get("/qualquer/")
    request.user = type("U", (), {"is_authenticated": False})()
    resp = handler500(request)
    _assert_branded_error(resp, status=500, heading_fragment="Algo deu errado")
    assert "OperationalError" not in resp.content.decode("utf-8")


@override_settings(
    DEBUG=False,
    APP_HOST="",
    LANDING_HOSTS="",
    MAINTENANCE_MODE=True,
)
@pytest.mark.django_db
def test_maintenance_mode_503_allows_health():
    client = Client()
    resp = client.get(reverse("usuarios:login"))
    _assert_branded_error(resp, status=503, heading_fragment="Estamos em manutenção")
    assert resp.get("Retry-After") is not None

    health = client.get(reverse("health"))
    assert health.status_code == 200
    assert health.json()["status"] in ("ok", "degraded")


@override_settings(
    DEBUG=False,
    APP_HOST="app.granago.com.br",
    LANDING_HOSTS="granago.com.br",
    APP_LOGIN_URL="https://app.granago.com.br/login/",
    MAINTENANCE_MODE=False,
)
@pytest.mark.django_db
def test_404_cta_on_landing_host():
    rf = RequestFactory()
    request = rf.get("/pagina-fantasma/", HTTP_HOST="granago.com.br")
    request.user = type("U", (), {"is_authenticated": False})()
    resp = handler404(request, exception=None)
    content = resp.content.decode("utf-8")
    assert resp.status_code == 404
    assert "Ir para o início" in content
    assert "Entrar" in content


@override_settings(DEBUG=False, APP_HOST="", LANDING_HOSTS="", MAINTENANCE_MODE=False)
@pytest.mark.django_db
def test_404_cta_authenticated_dashboard():
    user = User.objects.create_user(
        email="erro-pages@example.com",
        password="SenhaForte123!",
        nome="Erro Pages",
    )
    rf = RequestFactory()
    request = rf.get("/pagina-fantasma/")
    request.user = user
    resp = handler404(request, exception=None)
    content = resp.content.decode("utf-8")
    assert "Ir para o Dashboard" in content


@override_settings(DEBUG=False, APP_HOST="", LANDING_HOSTS="", MAINTENANCE_MODE=False)
@pytest.mark.django_db
def test_anon_protected_redirects_login_not_401():
    client = Client()
    resp = client.get(reverse("relatorios:home"))
    assert resp.status_code in (302, 301)
    assert resp.status_code != 401
    assert "/login/" in resp["Location"]
