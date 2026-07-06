"""Testes do endpoint /health/."""

from __future__ import annotations

import pytest
from django.test import Client, override_settings
from django.urls import reverse


@pytest.mark.seguranca
@pytest.mark.django_db
def test_health_payload_minimo_sem_token():
    client = Client()
    resp = client.get(reverse("health"))
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"status": "ok"}
    assert "checks" not in data


@override_settings(HEALTH_CHECK_TOKEN="secret-token")
@pytest.mark.seguranca
@pytest.mark.django_db
def test_health_detalhado_com_token():
    client = Client()
    url = reverse("health")
    resp_sem = client.get(url)
    assert resp_sem.status_code == 401

    resp_ok = client.get(url, HTTP_X_HEALTH_TOKEN="secret-token")
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert data["status"] == "ok"
    assert "checks" in data
    assert "database" in data["checks"]
