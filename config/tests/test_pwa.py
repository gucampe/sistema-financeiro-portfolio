"""Testes da PWA v1 (manifest, SW, host do SaaS, metas no base)."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client, override_settings
from django.urls import reverse


HOSTS = dict(
    APP_HOST="app.granago.com.br",
    LANDING_HOSTS="granago.com.br,www.granago.com.br",
)


def _icons():
    return Path(settings.BASE_DIR) / "static" / "img" / "icons" / "pwa"


@pytest.mark.django_db
def test_icones_pwa_existem_nos_tamanhos_esperados():
    from PIL import Image

    esperado = {
        "icon-192.png": (192, 192),
        "icon-512.png": (512, 512),
        "icon-192-maskable.png": (192, 192),
        "icon-512-maskable.png": (512, 512),
        "apple-touch-icon.png": (180, 180),
    }
    for nome, size in esperado.items():
        path = _icons() / nome
        assert path.is_file(), nome
        with Image.open(path) as img:
            assert img.size == size


@pytest.mark.django_db
def test_manifest_saas_ok():
    client = Client()
    resp = client.get(reverse("web_manifest"))
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("application/manifest+json")
    assert resp["Cache-Control"] == "no-cache"
    data = resp.json()
    assert data["name"] == "GranaGo"
    assert data["short_name"] == "GranaGo"
    assert data["start_url"] == "/"
    assert data["scope"] == "/"
    assert data["display"] == "standalone"
    assert data["theme_color"] == "#f4f5f7"
    assert data["background_color"] == "#f4f5f7"
    sizes = {(i["sizes"], i["purpose"]) for i in data["icons"]}
    assert ("192x192", "any") in sizes
    assert ("512x512", "any") in sizes
    assert ("192x192", "maskable") in sizes
    assert ("512x512", "maskable") in sizes
    assert all("/?" not in i["src"] and "utm_" not in i["src"] for i in data["icons"])


@pytest.mark.django_db
@override_settings(**HOSTS)
def test_manifest_id_producao_e_404_na_landing():
    client = Client()
    app = client.get("/manifest.webmanifest", HTTP_HOST="app.granago.com.br")
    assert app.status_code == 200
    assert app.json()["id"] == "https://app.granago.com.br/"
    landing = client.get("/manifest.webmanifest", HTTP_HOST="granago.com.br")
    assert landing.status_code == 404


@pytest.mark.django_db
def test_service_worker_pass_through_sem_cache():
    client = Client()
    resp = client.get(reverse("service_worker"))
    assert resp.status_code == 200
    assert "javascript" in resp["Content-Type"]
    assert resp["Cache-Control"] == "no-cache"
    body = resp.content.decode("utf-8")
    assert "addEventListener(\"fetch\"" in body
    assert "respondWith(fetch(event.request))" in body
    assert "caches" not in body
    assert "skipWaiting(" not in body
    assert "clients.claim" not in body


@pytest.mark.django_db
@override_settings(**HOSTS)
def test_service_worker_nao_exposto_na_landing():
    client = Client()
    resp = client.get("/sw.js", HTTP_HOST="granago.com.br")
    assert resp.status_code == 404
    app = client.get("/sw.js", HTTP_HOST="app.granago.com.br")
    assert app.status_code == 200


@pytest.mark.django_db
def test_base_saas_tem_metas_pwa():
    client = Client()
    resp = client.get(reverse("usuarios:login"))
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert 'rel="manifest"' in html
    assert "apple-touch-icon" in html
    assert 'name="mobile-web-app-capable"' in html
    assert 'name="apple-mobile-web-app-capable"' in html
    assert 'content="GranaGo"' in html
    assert 'apple-mobile-web-app-status-bar-style' in html
    assert "viewport-fit=cover" in html
    assert "static/js/pwa.js" in html or "/js/pwa.js" in html
    assert "data-pwa-dismiss" not in html
    assert 'data-pwa-auth="1"' not in html


@pytest.mark.django_db
@override_settings(**HOSTS)
def test_landing_nao_tem_manifest():
    client = Client()
    resp = client.get("/", HTTP_HOST="granago.com.br")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert 'rel="manifest"' not in html
    assert "apple-mobile-web-app-capable" not in html
    assert "pwa.js" not in html


@pytest.mark.django_db
def test_configuracoes_tem_secao_aplicativo():
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(email="pwa@test.com", nome="PWA", password="x")
    client = Client()
    client.force_login(user)
    resp = client.get(reverse("usuarios:configuracoes"))
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert 'id="aplicativo"' in html
    assert "Instalar GranaGo" in html
    assert "data-pwa-banner" in html
    assert "data-pwa-auth=\"1\"" in html
