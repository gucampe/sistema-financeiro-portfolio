"""
Smoke contínuo — reutilizável em staging/produção com conta demo.

Executar: pytest e2e/specs/synthetic -m synthetic
Ou cron: python -m pytest e2e/specs/synthetic/test_monitor.py -m synthetic
"""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from playwright.sync_api import expect

from e2e.factories.personas import E2E_PASSWORD
from e2e.fixtures.pages.dashboard_page import DashboardPage
from e2e.fixtures.pages.login_page import LoginPage
from e2e.fixtures.pages.transacoes_page import TransacaoModalPage
from financial_contracts.saldo_contracts import assert_saldo_conta
from transacoes.models import Transacao


@pytest.mark.synthetic
@pytest.mark.django_db(transaction=True)
def test_synthetic_smoke_completo(logged_in_page, app_base_url, persona_basic):
    """Login → dashboard KPIs → criar/excluir transação synthetic."""
    page = logged_in_page
    user = persona_basic["user"]
    conta = persona_basic["conta"]
    saldo_antes = conta.saldo_atual_calc
    stamp = timezone.now().strftime("%H%M%S")

    dash = DashboardPage(page, app_base_url)
    dash.open()
    dash.kpi_receitas()
    dash.open_nova_despesa()

    modal = TransacaoModalPage(page, app_base_url)
    desc = f"synthetic-check-{stamp}"
    modal.criar_transacao(
        tipo="despesa",
        conta_id=conta.id,
        cartao_id=None,
        categoria_id=persona_basic["cat_despesa"].id,
        valor=Decimal("0.01"),
        descricao=desc,
        data=timezone.localdate(),
    )

    conta.refresh_from_db()
    assert_saldo_conta(conta, saldo_antes - Decimal("0.01"))

    tx = Transacao.objects.get(usuario=user, descricao=desc)
    page.request.post(
        f"{app_base_url}/transacoes/{tx.id}/excluir/",
        headers={"X-CSRFToken": page.locator("[name=csrfmiddlewaretoken]").first.input_value()},
    )

    conta.refresh_from_db()
    assert_saldo_conta(conta, saldo_antes)

    api = page.request.get(f"{app_base_url}/relatorios/api/serie-tendencia/")
    assert api.status == 200


@pytest.mark.synthetic
@pytest.mark.django_db(transaction=True)
def test_synthetic_apis(logged_in_page, app_base_url):
    page = logged_in_page
    r1 = page.request.get(f"{app_base_url}/relatorios/api/top-categorias/?tipo=despesa")
    assert r1.status == 200
