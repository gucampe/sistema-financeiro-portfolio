"""Testes do subsistema de exportação."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from categorias.models import Categoria
from contas.models import Conta
from relatorios.models import ExportJob
from relatorios.services.export.jobs import claim_job, criar_export_job, executar_job
from relatorios.services.export.serializers import payload_from_filtros
from relatorios.services.filtros import RelatorioFiltros
from transacoes.models import Transacao


@pytest.fixture
def export_user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(email="export@test.local", password="x", nome="Export")
    conta = Conta.objects.create(usuario=user, nome="C1", tipo="corrente", ativa=True)
    cat, _ = Categoria.objects.get_or_create(
        usuario=user,
        nome="Cat Export Test",
        tipo="despesa",
        defaults={"cor": "#f00", "ativa": True},
    )
    Transacao.objects.create(
        usuario=user,
        conta=conta,
        categoria=cat,
        tipo="despesa",
        valor=Decimal("50.00"),
        data=date(2026, 6, 1),
        descricao="Teste",
    )
    return user


def _filtros_json():
    f = RelatorioFiltros(
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 6, 30),
        preset="este_mes",
    )
    return json.dumps(payload_from_filtros(f))


@override_settings(EXPORT_JOB_BACKEND="sync")
@pytest.mark.django_db
def test_export_csv_transacoes_sync(export_user):
    job, msg, _ = criar_export_job(
        usuario=export_user,
        dominio=ExportJob.DOMINIO_TRANSACOES,
        formato=ExportJob.FORMATO_CSV,
        filtros_json=_filtros_json(),
    )
    assert job is not None
    executar_job(job.pk)
    job.refresh_from_db()
    assert job.status == ExportJob.STATUS_READY
    assert job.arquivo
    assert job.linhas_count >= 1


@pytest.mark.django_db
def test_claim_job_idempotente(export_user):
    job = ExportJob.objects.create(
        usuario=export_user,
        dominio=ExportJob.DOMINIO_TRANSACOES,
        formato=ExportJob.FORMATO_CSV,
        filtros_json=_filtros_json(),
    )
    first = claim_job(job.pk)
    second = claim_job(job.pk)
    assert first is not None
    assert second is None


@pytest.mark.django_db
def test_api_export_idor(export_user, db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    other = User.objects.create_user(email="other@test.local", password="x", nome="Other")
    job = ExportJob.objects.create(usuario=other, filtros_json="{}")
    client = Client()
    client.force_login(export_user)
    url = reverse("relatorios:api_export_job_detail", kwargs={"pk": job.pk})
    resp = client.get(url)
    assert resp.status_code == 404


@override_settings(EXPORT_JOB_BACKEND="sync")
@pytest.mark.django_db
def test_api_create_export_job(export_user):
    client = Client(enforce_csrf_checks=False)
    client.force_login(export_user)
    url = reverse("relatorios:api_export_jobs_create")
    resp = client.post(f"{url}?preset=este_mes", data={"dominio": "transacoes", "formato": "csv"})
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
