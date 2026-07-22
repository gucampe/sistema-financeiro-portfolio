"""E2E Playwright — Transferências entre contas (QA adversarial)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from playwright.sync_api import expect

from contas.models import Conta
from e2e.factories.personas import E2E_PASSWORD
from e2e.fixtures.pages.login_page import LoginPage
from e2e.fixtures.pages.transacoes_page import HistoricoPage, TransacaoModalPage
from financial_contracts.saldo_contracts import assert_patrimonio_contas, assert_saldo_conta
from transacoes.models import Transacao
from transacoes.services import criar_transferencia


def _hoje() -> date:
    return timezone.localdate()


def _assert_par(user, transfer_id) -> None:
    qs = Transacao.objects.filter(usuario=user, transfer_id=transfer_id, tipo="transferencia")
    assert qs.count() == 2
    papeis = set(qs.values_list("papel_transferencia", flat=True))
    assert papeis == {"origem", "destino"}


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_transf_e2e_01_criar_atualiza_saldos(logged_in_page, app_base_url, persona_basic):
    page = logged_in_page
    conta_a = persona_basic["conta"]
    conta_b = persona_basic["conta_b"]
    user = persona_basic["user"]
    patrimonio_antes = sum(
        c.saldo_atual_calc for c in Conta.objects.filter(usuario=user, ativa=True)
    )
    saldo_a = conta_a.saldo_atual_calc
    saldo_b = conta_b.saldo_atual_calc
    valor = Decimal("120.50")

    hist = HistoricoPage(page, app_base_url)
    modal = hist.open_nova_transferencia()
    modal.criar_transferencia(
        conta_origem_id=conta_a.id,
        conta_destino_id=conta_b.id,
        valor=valor,
        descricao="E2E transferência feliz",
        data=_hoje(),
    )

    conta_a.refresh_from_db()
    conta_b.refresh_from_db()
    assert_saldo_conta(conta_a, saldo_a - valor)
    assert_saldo_conta(conta_b, saldo_b + valor)
    assert_patrimonio_contas(user, patrimonio_antes)

    txs = Transacao.objects.filter(
        usuario=user, tipo="transferencia", descricao="E2E transferência feliz"
    )
    assert txs.count() == 2
    tid = txs.first().transfer_id
    _assert_par(user, tid)
    expect(page.locator("text=Transferência para").first).to_be_visible()


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_transf_e2e_02_origem_igual_destino_mostra_erro(
    logged_in_page, app_base_url, persona_basic
):
    page = logged_in_page
    conta_a = persona_basic["conta"]
    antes = Transacao.objects.filter(
        usuario=persona_basic["user"], tipo="transferencia"
    ).count()

    hist = HistoricoPage(page, app_base_url)
    modal = hist.open_nova_transferencia()
    modal.select_conta_origem(conta_a.id)
    modal.select_conta_destino(conta_a.id)
    modal.fill_valor(Decimal("10.00"))
    modal.fill_descricao("igual")
    modal.fill_data(_hoje())
    modal.salvar(wait_reload=False)
    modal.expect_erro_formulario()

    assert (
        Transacao.objects.filter(
            usuario=persona_basic["user"], tipo="transferencia"
        ).count()
        == antes
    )


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_transf_e2e_03_valor_zero_erro(logged_in_page, app_base_url, persona_basic):
    page = logged_in_page
    hist = HistoricoPage(page, app_base_url)
    modal = hist.open_nova_transferencia()
    modal.select_conta_origem(persona_basic["conta"].id)
    modal.select_conta_destino(persona_basic["conta_b"].id)
    modal.fill_valor(Decimal("0.00"))
    modal.fill_descricao("zero")
    modal.fill_data(_hoje())
    modal.salvar(wait_reload=False)
    modal.expect_erro_formulario()


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_transf_e2e_04_esc_fecha_modal(logged_in_page, app_base_url, persona_basic):
    page = logged_in_page
    hist = HistoricoPage(page, app_base_url)
    hist.open_nova_transferencia()
    expect(page.locator("#overlay-adicionar")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#overlay-adicionar")).to_be_hidden()


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_transf_e2e_05_duplo_clique_salvar_nao_cria_orfao(
    logged_in_page, app_base_url, persona_basic
):
    page = logged_in_page
    user = persona_basic["user"]
    hist = HistoricoPage(page, app_base_url)
    modal = hist.open_nova_transferencia()
    modal.select_conta_origem(persona_basic["conta"].id)
    modal.select_conta_destino(persona_basic["conta_b"].id)
    modal.fill_valor(Decimal("15.00"))
    modal.fill_descricao("E2E duplo clique")
    modal.fill_data(_hoje())

    with page.expect_navigation(timeout=45000, wait_until="load"):
        modal.salvar_double_click()

    txs = Transacao.objects.filter(
        usuario=user, tipo="transferencia", descricao="E2E duplo clique"
    )
    # Flag salvando + disable: idealmente 1 par (2 txs). Aceita no máx. 2 pares se race vencer.
    assert txs.count() in (2, 4)
    assert txs.count() % 2 == 0
    for tid in set(txs.values_list("transfer_id", flat=True)):
        _assert_par(user, tid)


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_transf_e2e_06_editar_e_excluir_par(logged_in_page, app_base_url, persona_basic):
    page = logged_in_page
    user = persona_basic["user"]
    conta_a = persona_basic["conta"]
    conta_b = persona_basic["conta_b"]
    o, _d = criar_transferencia(
        user,
        conta_origem=conta_a,
        conta_destino=conta_b,
        valor=Decimal("40.00"),
        data=_hoje(),
        descricao="E2E editar alvo transf",
    )
    tid = o.transfer_id
    saldo_a_antes = conta_a.saldo_atual_calc

    hist = HistoricoPage(page, app_base_url)
    hist.open(_hoje().year, _hoje().month)
    hist.editar_por_id(o.id)

    modal = TransacaoModalPage(page, app_base_url)
    expect(page.locator("#bloco-transferencia")).to_be_visible()
    modal.fill_valor(Decimal("55.00"))
    modal.salvar()

    o.refresh_from_db()
    assert o.valor == Decimal("55.00")
    _assert_par(user, tid)

    hist.open(_hoje().year, _hoje().month)
    hist.excluir_por_id(o.id)
    assert Transacao.objects.filter(usuario=user, transfer_id=tid).count() == 0
    conta_a.refresh_from_db()
    # Após excluir, saldo deve voltar ao estado pré-transferência editada
    # (saldo_a_antes era pós-criação de 40; edição para 55 mudou; exclusão restaura base).
    assert conta_a.saldo_atual_calc == saldo_a_antes + Decimal("40.00")


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_transf_e2e_07_refresh_durante_modal_nao_persiste(
    logged_in_page, app_base_url, persona_basic
):
    page = logged_in_page
    user = persona_basic["user"]
    antes = Transacao.objects.filter(usuario=user, tipo="transferencia").count()
    hist = HistoricoPage(page, app_base_url)
    modal = hist.open_nova_transferencia()
    modal.select_conta_origem(persona_basic["conta"].id)
    modal.select_conta_destino(persona_basic["conta_b"].id)
    modal.fill_valor(Decimal("99.00"))
    modal.fill_descricao("abortada refresh")
    page.reload()
    page.wait_for_load_state("load")
    assert Transacao.objects.filter(usuario=user, tipo="transferencia").count() == antes


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_transf_e2e_08_duas_abas_excluir_simultaneo(
    browser, app_base_url, persona_basic, django_db_blocker
):
    django_db_blocker.unblock()
    user = persona_basic["user"]
    o, d = criar_transferencia(
        user,
        conta_origem=persona_basic["conta"],
        conta_destino=persona_basic["conta_b"],
        valor=Decimal("22.00"),
        data=_hoje(),
        descricao="E2E race excluir",
    )
    tid = o.transfer_id

    ctx1 = browser.new_context(timezone_id="America/Sao_Paulo", locale="pt-BR")
    ctx2 = browser.new_context(timezone_id="America/Sao_Paulo", locale="pt-BR")
    p1 = ctx1.new_page()
    p2 = ctx2.new_page()
    LoginPage(p1, app_base_url).login(user.email, E2E_PASSWORD)
    LoginPage(p2, app_base_url).login(user.email, E2E_PASSWORD)

    h1 = HistoricoPage(p1, app_base_url)
    h2 = HistoricoPage(p2, app_base_url)
    hoje = _hoje()
    h1.open(hoje.year, hoje.month)
    h2.open(hoje.year, hoje.month)

    # Dispara exclusão pelas duas pernas; uma deve vencer, a outra ser idempotente.
    errors = []
    try:
        h1.excluir_por_id(o.id)
    except Exception as exc:
        errors.append(exc)
    try:
        h2.excluir_por_id(d.id)
    except Exception as exc:
        errors.append(exc)

    assert Transacao.objects.filter(usuario=user, transfer_id=tid).count() == 0
    # No máximo uma das abas pode falhar na UI (navegação já sem a linha).
    assert len(errors) <= 1
    ctx1.close()
    ctx2.close()


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_transf_e2e_09_regressao_receita_ainda_funciona(
    logged_in_page, app_base_url, persona_basic
):
    """Garantir que o fluxo de receita não quebrou após transferências."""
    page = logged_in_page
    conta = persona_basic["conta"]
    saldo_antes = conta.saldo_atual_calc
    from e2e.fixtures.pages.dashboard_page import DashboardPage

    dash = DashboardPage(page, app_base_url)
    dash.open()
    dash.open_nova_receita()
    modal = TransacaoModalPage(page, app_base_url)
    modal.criar_transacao(
        tipo="receita",
        conta_id=conta.id,
        cartao_id=None,
        categoria_id=persona_basic["cat_receita"].id,
        valor=Decimal("10.00"),
        descricao="E2E regressão receita pós-transf",
        data=_hoje(),
    )
    conta.refresh_from_db()
    assert_saldo_conta(conta, saldo_antes + Decimal("10.00"))
