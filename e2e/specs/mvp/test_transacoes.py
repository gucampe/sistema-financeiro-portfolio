from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from contas.models import Conta
from e2e.fixtures.pages.dashboard_page import DashboardPage
from e2e.fixtures.pages.transacoes_page import HistoricoPage, TransacaoModalPage
from e2e.helpers.financial_contracts import verify_saldo_conta
from financial_contracts.saldo_contracts import assert_saldo_conta, calcular_saldo_esperado
from transacoes.models import Transacao


def _hoje() -> date:
    return timezone.localdate()


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_trx_01_criar_receita_atualiza_saldo(logged_in_page, app_base_url, persona_basic):
    page = logged_in_page
    conta = persona_basic["conta"]
    saldo_antes = conta.saldo_atual_calc
    valor = Decimal("200.00")

    dash = DashboardPage(page, app_base_url)
    dash.open()
    dash.open_nova_receita()

    modal = TransacaoModalPage(page, app_base_url)
    modal.criar_transacao(
        tipo="receita",
        conta_id=conta.id,
        cartao_id=None,
        categoria_id=persona_basic["cat_receita"].id,
        valor=valor,
        descricao="E2E receita nova",
        data=_hoje(),
    )

    conta.refresh_from_db()
    assert_saldo_conta(conta, saldo_antes + valor)
    verify_saldo_conta(conta.id, saldo_antes + valor)


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_trx_02_criar_despesa(logged_in_page, app_base_url, persona_basic):
    page = logged_in_page
    conta = persona_basic["conta"]
    saldo_antes = conta.saldo_atual_calc
    valor = Decimal("75.50")

    dash = DashboardPage(page, app_base_url)
    dash.open()
    dash.open_nova_despesa()

    modal = TransacaoModalPage(page, app_base_url)
    modal.criar_transacao(
        tipo="despesa",
        conta_id=conta.id,
        cartao_id=None,
        categoria_id=persona_basic["cat_despesa"].id,
        valor=valor,
        descricao="E2E despesa nova",
        data=_hoje(),
    )

    conta.refresh_from_db()
    assert_saldo_conta(conta, saldo_antes - valor)


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_trx_03_editar_transacao(logged_in_page, app_base_url, persona_basic):
    page = logged_in_page
    conta = persona_basic["conta"]
    tx = Transacao.objects.create(
        usuario=persona_basic["user"],
        conta=conta,
        categoria=persona_basic["cat_despesa"],
        tipo="despesa",
        valor=Decimal("40.00"),
        data=_hoje(),
        descricao="E2E editar alvo",
    )
    saldo_com_40 = conta.saldo_atual_calc

    hist = HistoricoPage(page, app_base_url)
    hoje = _hoje()
    hist.open(hoje.year, hoje.month)
    hist.editar_por_id(tx.id)

    modal = TransacaoModalPage(page, app_base_url)
    modal.fill_valor(Decimal("60.00"))
    modal.salvar()

    conta.refresh_from_db()
    assert_saldo_conta(conta, saldo_com_40 - Decimal("20.00"))


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_trx_04_excluir_transacao(logged_in_page, app_base_url, persona_basic):
    page = logged_in_page
    conta = persona_basic["conta"]
    saldo_antes = conta.saldo_atual_calc
    tx = Transacao.objects.create(
        usuario=persona_basic["user"],
        conta=conta,
        categoria=persona_basic["cat_despesa"],
        tipo="despesa",
        valor=Decimal("25.00"),
        data=_hoje(),
        descricao="E2E excluir alvo",
    )
    saldo_apos_criar = conta.saldo_atual_calc

    hist = HistoricoPage(page, app_base_url)
    hoje = _hoje()
    hist.open(hoje.year, hoje.month)
    hist.excluir_por_id(tx.id)

    conta.refresh_from_db()
    assert_saldo_conta(conta, saldo_apos_criar + Decimal("25.00"))
    assert saldo_apos_criar == saldo_antes - Decimal("25.00")


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_trx_06_compra_cartao_nao_altera_saldo_conta(logged_in_card_page, app_base_url, persona_card):
    page = logged_in_card_page
    conta = persona_card["conta"]
    saldo_antes = calcular_saldo_esperado(conta, incluir_compras_cartao=False)

    dash = DashboardPage(page, app_base_url)
    dash.open()
    dash.open_nova_despesa()

    modal = TransacaoModalPage(page, app_base_url)
    modal.criar_transacao(
        tipo="despesa",
        conta_id=None,
        cartao_id=persona_card["cartao"].id,
        categoria_id=persona_card["cat_despesa"].id,
        valor=Decimal("80.00"),
        descricao="E2E compra cartao isolada",
        data=_hoje(),
    )

    conta.refresh_from_db()
    assert_saldo_conta(conta, saldo_antes, incluir_compras_cartao=False)


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_rc_05_double_submit_nao_duplica(logged_in_page, app_base_url, persona_basic):
    page = logged_in_page
    conta = persona_basic["conta"]
    count_antes = Transacao.objects.filter(usuario=persona_basic["user"]).count()

    dash = DashboardPage(page, app_base_url)
    dash.open()
    dash.open_nova_despesa()

    modal = TransacaoModalPage(page, app_base_url)
    modal.wait_modal_open()
    modal.set_tipo("despesa")
    modal.select_conta(conta.id)
    modal.select_categoria(persona_basic["cat_despesa"].id)
    modal.fill_valor(Decimal("10.00"))
    modal.fill_descricao("E2E double submit")
    modal.fill_data(_hoje())
    modal.salvar_double_click()
    page.wait_for_timeout(2000)

    count_depois = Transacao.objects.filter(
        usuario=persona_basic["user"], descricao="E2E double submit"
    ).count()
    assert count_depois == 1
