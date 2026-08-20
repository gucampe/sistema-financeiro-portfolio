"""Testes do roteamento por host (landing vs app)."""

from __future__ import annotations

import pytest
from django.test import RequestFactory, override_settings

from config.middleware_hosts import HostRoutingMiddleware


@pytest.fixture
def mw():
    return HostRoutingMiddleware(get_response=lambda r: None)


@override_settings(
    APP_HOST="app.granago.com.br",
    LANDING_HOSTS="granago.com.br,www.granago.com.br",
)
def test_landing_login_redirects_to_app(mw):
    rf = RequestFactory()
    req = rf.get("/login/", HTTP_HOST="granago.com.br")
    resp = mw.process_request(req)
    assert resp is not None
    assert resp.status_code == 302
    assert resp["Location"] == "https://app.granago.com.br/login/"


@override_settings(
    APP_HOST="app.granago.com.br",
    LANDING_HOSTS="granago.com.br,www.granago.com.br",
)
def test_app_root_anon_redirects_login(mw):
    rf = RequestFactory()
    req = rf.get("/", HTTP_HOST="app.granago.com.br")
    req.user = type("U", (), {"is_authenticated": False})()
    resp = mw.process_request(req)
    assert resp is not None
    assert resp["Location"] == "https://app.granago.com.br/login/"


@override_settings(
    APP_HOST="app.granago.com.br",
    LANDING_HOSTS="granago.com.br,www.granago.com.br",
)
def test_landing_home_no_redirect(mw):
    rf = RequestFactory()
    req = rf.get("/", HTTP_HOST="granago.com.br")
    assert mw.process_request(req) is None


@override_settings(
    APP_HOST="app.granago.com.br",
    LANDING_HOSTS="granago.com.br,www.granago.com.br",
)
def test_www_redirects_to_apex(mw):
    rf = RequestFactory()
    req = rf.get("/faq", HTTP_HOST="www.granago.com.br")
    resp = mw.process_request(req)
    assert resp is not None
    assert resp.status_code == 301
    assert resp["Location"] == "https://granago.com.br/faq"


@override_settings(
    APP_HOST="app.granago.com.br",
    LANDING_HOSTS="granago.com.br,www.granago.com.br",
)
def test_landing_conta_e_primeiros_passos_redirecionam_ao_app(mw):
    rf = RequestFactory()
    for path in ("/conta/configurar/abc/tok/", "/primeiros-passos/"):
        req = rf.get(path, HTTP_HOST="granago.com.br")
        resp = mw.process_request(req)
        assert resp is not None
        assert resp.status_code == 302
        assert resp["Location"] == f"https://app.granago.com.br{path}"
