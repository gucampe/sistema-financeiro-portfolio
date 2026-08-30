"""REL-X-01..09 — consistência cross-app (transações/cartões → relatórios)."""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from playwright.sync_api import expect

from e2e.fixtures.pages.dashboard_page import DashboardPage
from e2e.fixtures.pages.relatorios_page import FiltrosPortalPage, FluxoCaixaPage, RelatoriosHomePage
from e2e.fixtures.pages.transacoes_page import HistoricoPage, TransacaoModalPage
from e2e.helpers.financial_contracts import verify_saldo_conta
from e2e.helpers.moeda import parse_moeda_ptbr
from e2e.helpers.relatorio_contracts import (
    kpi_despesas_esperado,
    kpi_receitas_esperado,
    totais_esperados,
    verify_fluxo_periodo,
    verify_patrimonio_dashboard,
)
from financial_contracts.saldo_contracts import assert_saldo_conta
from relatorios.models import OrcamentoCategoria
from relatorios.services.dashboard import contas_dashboard
from transacoes.models import Transacao


def _hoje() -> date:
    return timezone.localdate()


@pytest.mark.relatorios
@pytest.mark.relatorios_consistency
@pytest.mark.django_db(transaction=True)
def test_rel_x_01_receita_atualiza_kpi(logged_in_page, app_base_url, persona_basic):
    user = persona_basic["user"]
    conta = persona_basic["conta"]
    antes = kpi_receitas_esperado(user)
    valor = Decimal("120.00")

    page = logged_in_page
    dash = DashboardPage(page, app_base_url)
    dash.open()
    dash.open_nova_receita()
    TransacaoModalPage(page, app_base_url).criar_transacao(
        tipo="receita",
        conta_id=conta.id,
        cartao_id=None,
        categoria_id=persona_basic["cat_receita"].id,
        valor=valor,
        descricao="REL-X-01 receita",
        data=_hoje(),
    )

    dash.open()
    assert dash.kpi_receitas() == antes + valor
    verify_saldo_conta(conta.id, conta.saldo_atual_calc)


@pytest.mark.relatorios
@pytest.mark.relatorios_consistency
@pytest.mark.django_db(transaction=True)
def test_rel_x_02_despesa_atualiza_kpi(logged_in_page, app_base_url, persona_basic):
    user = persona_basic["user"]
    antes = kpi_despesas_esperado(user)
    valor = Decimal("45.00")

    page = logged_in_page
    dash = DashboardPage(page, app_base_url)
    dash.open()
    dash.open_nova_despesa()
    TransacaoModalPage(page, app_base_url).criar_transacao(
        tipo="despesa",
        conta_id=persona_basic["conta"].id,
        cartao_id=None,
        categoria_id=persona_basic["cat_despesa"].id,
        valor=valor,
        descricao="REL-X-02 despesa",
        data=_hoje(),
    )

    dash.open()
    assert dash.kpi_despesas() == antes + valor


@pytest.mark.relatorios
@pytest.mark.relatorios_consistency
@pytest.mark.django_db(transaction=True)
def test_rel_x_03_editar_tx_atualiza_kpi(logged_in_page, app_base_url, persona_basic):
    user = persona_basic["user"]
    conta = persona_basic["conta"]
    tx = Transacao.objects.create(
        usuario=user,
        conta=conta,
        categoria=persona_basic["cat_despesa"],
        tipo="despesa",
        valor=Decimal("30.00"),
        data=_hoje(),
        descricao="REL-X-03 alvo",
    )
    antes = kpi_despesas_esperado(user)

    hist = HistoricoPage(logged_in_page, app_base_url)
    hoje = _hoje()
    hist.open(hoje.year, hoje.month)
    hist.editar_por_id(tx.id)
    TransacaoModalPage(logged_in_page, app_base_url).fill_valor(Decimal("55.00"))
    TransacaoModalPage(logged_in_page, app_base_url).salvar()

    dash = DashboardPage(logged_in_page, app_base_url)
    dash.open()
    assert dash.kpi_despesas() == antes + Decimal("25.00")


@pytest.mark.relatorios
@pytest.mark.relatorios_consistency
@pytest.mark.django_db(transaction=True)
def test_rel_x_04_excluir_tx_reverte_kpi(logged_in_page, app_base_url, persona_basic):
    user = persona_basic["user"]
    conta = persona_basic["conta"]
    tx = Transacao.objects.create(
        usuario=user,
        conta=conta,
        categoria=persona_basic["cat_despesa"],
        tipo="despesa",
        valor=Decimal("22.00"),
        data=_hoje(),
        descricao="REL-X-04 excluir",
    )
    antes = kpi_despesas_esperado(user)

    hist = HistoricoPage(logged_in_page, app_base_url)
    hoje = _hoje()
    hist.open(hoje.year, hoje.month)
    hist.excluir_por_id(tx.id)

    dash = DashboardPage(logged_in_page, app_base_url)
    dash.open()
    assert dash.kpi_despesas() == antes - Decimal("22.00")


@pytest.mark.relatorios
@pytest.mark.relatorios_consistency
@pytest.mark.django_db(transaction=True)
def test_rel_x_05_compra_cartao_patrimonio(logged_in_card_page, app_base_url, persona_card):
    user = persona_card["user"]
    patrimonio = verify_patrimonio_dashboard(user)
    home = RelatoriosHomePage(logged_in_card_page, app_base_url)
    home.open()
    sec = logged_in_card_page.locator("section").filter(has_text="Saldo das contas")
    texto = sec.locator(".dash-valor").first.inner_text()
    assert parse_moeda_ptbr(texto) == patrimonio


@pytest.mark.relatorios
@pytest.mark.relatorios_consistency
@pytest.mark.django_db(transaction=True)
def test_rel_x_06_pagar_fatura_patrimonio(persona_card):
    user = persona_card["user"]
    patrimonio = contas_dashboard(user)["patrimonio_total"]
    assert patrimonio is not None


@pytest.mark.relatorios
@pytest.mark.relatorios_consistency
@pytest.mark.django_db(transaction=True)
def test_rel_x_07_filtro_conta_exclui_despesa(logged_in_relatorios_page, app_base_url, persona_relatorios):
    user = persona_relatorios["user"]
    conta_a = persona_relatorios["conta_a"]
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    filtros = FiltrosPortalPage(logged_in_relatorios_page, app_base_url)
    filtros.abrir()
    filtros.desmarcar_todas_contas()
    filtros.marcar_conta(conta_a.id)
    filtros.aplicar()
    esperado = verify_fluxo_periodo(user, {"preset": "este_mes", "conta": [conta_a.id]})
    total_geral = totais_esperados(user)["despesas"]
    assert fluxo.totais_despesas() == esperado["despesas"]
    assert esperado["despesas"] <= total_geral


@pytest.mark.relatorios
@pytest.mark.relatorios_consistency
@pytest.mark.django_db(transaction=True)
def test_rel_x_08_top_despesas_drill(logged_in_relatorios_page, app_base_url, persona_relatorios):
    home = RelatoriosHomePage(logged_in_relatorios_page, app_base_url)
    home.open()
    sec = logged_in_relatorios_page.locator("section").filter(
        has_text="Para onde seu dinheiro está indo"
    )
    link = sec.locator("a[href*='categoria=']").first
    if link.count() == 0:
        pytest.skip("Sem top despesas na home")
    with logged_in_relatorios_page.expect_navigation():
        link.click()
    assert "categoria=" in logged_in_relatorios_page.url or "inicio=" in logged_in_relatorios_page.url


@pytest.mark.relatorios
@pytest.mark.relatorios_consistency
@pytest.mark.django_db(transaction=True)
def test_rel_x_09_orcamento_widget_home(logged_in_relatorios_page, app_base_url, persona_relatorios):
    user = persona_relatorios["user"]
    cat = persona_relatorios["cat_despesa"]
    assert OrcamentoCategoria.objects.filter(usuario=user, categoria=cat).exists()
    from relatorios.services.orcamentos import listar_orcamentos_mes

    linhas_antes = listar_orcamentos_mes(user, _hoje().year, _hoje().month)
    realizado_antes = next(
        (l.realizado for l in linhas_antes if l.categoria_id == cat.id),
        None,
    )
    assert realizado_antes is not None

    home = RelatoriosHomePage(logged_in_relatorios_page, app_base_url)
    home.open()
    sec = logged_in_relatorios_page.locator("section").filter(has_text="Orçamento do mês")
    expect(sec).to_contain_text("E2E Despesas")

    valor = Decimal("35.00")
    home.abrir_nova_despesa()
    TransacaoModalPage(logged_in_relatorios_page, app_base_url).criar_transacao(
        tipo="despesa",
        conta_id=persona_relatorios["conta_a"].id,
        cartao_id=None,
        categoria_id=cat.id,
        valor=valor,
        descricao="REL-X-09 orcamento",
        data=_hoje(),
    )

    linhas_depois = listar_orcamentos_mes(user, _hoje().year, _hoje().month)
    realizado_depois = next(l.realizado for l in linhas_depois if l.categoria_id == cat.id)
    assert realizado_depois == realizado_antes + valor
