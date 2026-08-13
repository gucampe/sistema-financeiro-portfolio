"""Testes de segurança — mídia protegida."""

from __future__ import annotations

from importlib import reload

import pytest
from django.test import Client
from django.urls import clear_url_caches, reverse, set_urlconf

from relatorios.models import ExportJob
from usuarios.models import Perfil
from usuarios.tests.helpers.seguranca_fixtures import par_usuarios


@pytest.fixture
def enable_protected_media(settings):
    """Recarrega as URLs com a rota de mídia protegida (só existe fora de DEBUG)."""
    import config.urls as urls_mod

    settings.DEBUG = False
    settings.PROTECT_MEDIA = True
    settings.ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
    clear_url_caches()
    reload(urls_mod)
    set_urlconf(urls_mod)
    yield
    settings.DEBUG = True
    settings.PROTECT_MEDIA = False
    clear_url_caches()
    reload(urls_mod)
    set_urlconf(urls_mod)


@pytest.mark.seguranca
@pytest.mark.django_db
def test_protected_media_cross_user_404(enable_protected_media, settings, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_ROOT", tmp_path)
    par = par_usuarios()
    foto_rel = "perfis/fotos/user_b.jpg"
    foto_path = tmp_path / "perfis" / "fotos"
    foto_path.mkdir(parents=True)
    (foto_path / "user_b.jpg").write_bytes(b"fake")

    Perfil.objects.filter(usuario=par.user_b).update(foto=foto_rel)

    url = reverse("protected_media", kwargs={"path": foto_rel})
    resp = par.client_a.get(url)
    assert resp.status_code == 404


@pytest.mark.seguranca
@pytest.mark.django_db
def test_protected_media_path_traversal_404(enable_protected_media, settings, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_ROOT", tmp_path)
    par = par_usuarios()
    url = reverse("protected_media", kwargs={"path": "../.env"})
    resp = par.client_a.get(url)
    assert resp.status_code == 404


@pytest.mark.seguranca
@pytest.mark.django_db
def test_protected_media_owner_ok(enable_protected_media, settings, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_ROOT", tmp_path)
    par = par_usuarios()
    foto_rel = "perfis/fotos/user_a.jpg"
    foto_path = tmp_path / "perfis" / "fotos"
    foto_path.mkdir(parents=True)
    (foto_path / "user_a.jpg").write_bytes(b"fake-image")

    perfil = par.perfil_a
    perfil.foto = foto_rel
    perfil.save(update_fields=["foto"])

    url = reverse("protected_media", kwargs={"path": foto_rel})
    resp = par.client_a.get(url)
    assert resp.status_code == 200


@pytest.mark.seguranca
@pytest.mark.django_db
def test_protected_media_export_owner(enable_protected_media, settings, tmp_path, monkeypatch):
    from django.core.files.uploadedfile import SimpleUploadedFile

    monkeypatch.setattr(settings, "MEDIA_ROOT", tmp_path)
    par = par_usuarios()
    job = ExportJob.objects.create(
        usuario=par.user_a,
        status=ExportJob.STATUS_READY,
        dominio=ExportJob.DOMINIO_TITULAR_LGPD,
        formato=ExportJob.FORMATO_ZIP,
    )
    job.arquivo.save(
        "job_a.zip",
        SimpleUploadedFile("job_a.zip", b"zip-content"),
        save=True,
    )
    export_rel = job.arquivo.name
    url = reverse("protected_media", kwargs={"path": export_rel})
    resp = par.client_a.get(url)
    assert resp.status_code == 200


@pytest.mark.seguranca
@pytest.mark.django_db
def test_protected_media_anon_redirect_login(enable_protected_media, settings, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_ROOT", tmp_path)
    url = reverse("protected_media", kwargs={"path": "exports/x.zip"})
    resp = Client().get(url)
    assert resp.status_code == 302
    assert "/login/" in resp.url
