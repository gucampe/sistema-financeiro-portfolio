"""
EXT-01..05 — Observabilidade de performance real (tempo + carga).

Não bloqueante. Não usa CaptureQueriesContext como assert principal.
"""

from __future__ import annotations

import time

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from transacoes.ofx_duplicatas import avaliar_duplicatas_importacao
from transacoes.ofx_parse import parse_ofx_bytes
from transacoes.tests.helpers.import_fixtures import build_ofx_bytes
from transacoes.tests.helpers.import_pipeline import importar_ofx_completo, ofx_upload
from transacoes.views import _MAX_LINHAS_IMPORT_OFX
from tests.performance.helpers.seed import seed_perf_user, seed_transacoes_volume

User = get_user_model()

pytestmark = pytest.mark.performance_extended


def _build_n_tx(n: int, *, prefix: str) -> bytes:
    txs = []
    for i in range(n):
        txs.append(
            {
                "fitid": f"{prefix}-{i:05d}",
                "trnamt": f"-{(i % 50) + 1}.00",
                "name": f"Ext {prefix} {i}",
                "dtposted": f"2024{(i % 12) + 1:02d}15120000",
            }
        )
    return build_ofx_bytes(txs)


@pytest.fixture
def ext_client(db):
    data = seed_perf_user("perf-ext@test.local")
    client = Client(enforce_csrf_checks=False)
    client.force_login(data["user"])
    data["client"] = client
    return data


@pytest.mark.django_db
def test_ext_01_import_2000_linhas_elapsed(ext_client):
    """EXT-01: import 2000 linhas → elapsed <= 60s."""
    raw = _build_n_tx(_MAX_LINHAS_IMPORT_OFX, prefix="ext2k")
    t0 = time.monotonic()
    st, body, linhas = importar_ofx_completo(
        ext_client["client"],
        ext_client["conta"],
        raw,
        categoria_despesa_id=ext_client["cat_desp"].id,
        categoria_receita_id=ext_client["cat_rec"].id,
    )
    elapsed = time.monotonic() - t0
    assert st == 200, body
    assert len(linhas) == _MAX_LINHAS_IMPORT_OFX
    assert elapsed <= 60.0, f"import 2000 linhas lento: {elapsed:.2f}s"


@pytest.mark.django_db
def test_ext_02_duplicatas_5k_lote_2k_elapsed(ext_client):
    """EXT-02: duplicatas 5k + lote 2k → elapsed <= 30s."""
    raw_dup = _build_n_tx(5_000, prefix="extdup5k")
    linhas = parse_ofx_bytes(raw_dup)
    t0 = time.monotonic()
    dups = avaliar_duplicatas_importacao(ext_client["user"], ext_client["conta"], linhas)
    elapsed_dup = time.monotonic() - t0
    assert len(dups) == 5_000
    assert elapsed_dup <= 30.0, f"dup 5k lento: {elapsed_dup:.2f}s"

    raw_2k = _build_n_tx(2_000, prefix="extbatch2k")
    t1 = time.monotonic()
    st, body, _ = importar_ofx_completo(
        ext_client["client"],
        ext_client["conta"],
        raw_2k,
        categoria_despesa_id=ext_client["cat_desp"].id,
        categoria_receita_id=ext_client["cat_rec"].id,
    )
    elapsed_batch = time.monotonic() - t1
    assert st == 200, body
    assert elapsed_batch <= 30.0, f"lote 2k lento: {elapsed_batch:.2f}s"


@pytest.mark.django_db
def test_ext_03_relatorios_500_tx_elapsed(ext_client):
    """EXT-03: GET /relatorios/ com 500 tx → elapsed <= 15s."""
    seed_transacoes_volume(
        ext_client["user"],
        ext_client["conta"],
        ext_client["cat_desp"],
        ext_client["cat_rec"],
        n=500,
    )
    url = reverse("relatorios:home")
    t0 = time.monotonic()
    response = ext_client["client"].get(url)
    elapsed = time.monotonic() - t0
    assert response.status_code == 200
    assert elapsed <= 15.0, f"/relatorios/ 500 tx lento: {elapsed:.2f}s"


@pytest.mark.django_db
def test_ext_04_transacoes_500_tx_elapsed(ext_client):
    """EXT-04: GET /transacoes/ com 500 tx → elapsed <= 20s."""
    seed_transacoes_volume(
        ext_client["user"],
        ext_client["conta"],
        ext_client["cat_desp"],
        ext_client["cat_rec"],
        n=500,
    )
    url = reverse("transacoes:historico")
    t0 = time.monotonic()
    response = ext_client["client"].get(url)
    elapsed = time.monotonic() - t0
    assert response.status_code == 200
    assert elapsed <= 20.0, f"/transacoes/ 500 tx lento: {elapsed:.2f}s"


@pytest.mark.django_db
def test_ext_05_import_preview_2000_linhas_elapsed(ext_client):
    """EXT-05: import preview 2000 linhas → elapsed <= 20s."""
    raw = _build_n_tx(_MAX_LINHAS_IMPORT_OFX, prefix="extprev2k")
    upload = ofx_upload(raw, name="ext-preview.ofx")
    url = reverse("transacoes:importar_ofx_preview")
    t0 = time.monotonic()
    response = ext_client["client"].post(
        url,
        {"conta_id": ext_client["conta"].id, "arquivo": upload},
    )
    elapsed = time.monotonic() - t0
    assert response.status_code == 200, response.content[:500]
    payload = response.json()
    assert payload.get("status") == "ok"
    assert len(payload.get("linhas", [])) == _MAX_LINHAS_IMPORT_OFX
    assert elapsed <= 20.0, f"preview 2000 linhas lento: {elapsed:.2f}s"
