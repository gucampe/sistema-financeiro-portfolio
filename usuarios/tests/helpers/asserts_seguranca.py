"""Única camada de assert — segurança (HTTP, form, estado)."""

from __future__ import annotations


def assert_http_302_login(resp, *, login_fragment: str = "/login/") -> None:
    assert resp.status_code == 302, resp.status_code
    assert login_fragment in resp.url, resp.url


def assert_http_404(resp) -> None:
    assert resp.status_code == 404, resp.status_code


def assert_http_403(resp) -> None:
    assert resp.status_code == 403, resp.status_code


def assert_http_not_403(resp) -> None:
    assert resp.status_code != 403, resp.status_code


def assert_http_200(resp) -> None:
    assert resp.status_code == 200, resp.status_code


def assert_json_404(resp) -> None:
    assert resp.status_code == 404, resp.status_code
    assert "application/json" in (resp.get("Content-Type") or ""), resp.get("Content-Type")


def assert_form_invalid(form, field: str) -> None:
    assert not form.is_valid(), form.errors
    assert field in form.errors, form.errors


def assert_contagem_inalterada(antes: int, depois: int) -> None:
    assert antes == depois, (antes, depois)


def assert_recurso_ausente_para_usuario(user_a, modelo, pk_b) -> None:
    assert not modelo.objects.filter(usuario=user_a, pk=pk_b).exists()
