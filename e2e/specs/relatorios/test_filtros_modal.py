"""FIL-01..17 — modal de filtros e presets."""

from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import expect

from e2e.fixtures.pages.relatorios_page import (
    DespesasCategoriaPage,
    FiltrosPortalPage,
    FluxoCaixaPage,
    PorContaPage,
    RelatoriosHomePage,
)
from e2e.helpers.relatorio_contracts import (
    filtros_from_params,
    totais_esperados,
    verify_categoria_total,
    verify_conta_patrimonio,
    verify_fluxo_periodo,
)
from relatorios.services.filtros import RelatorioFiltros


@pytest.fixture
def filtros(logged_in_relatorios_page, app_base_url):
    return FiltrosPortalPage(logged_in_relatorios_page, app_base_url)


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_01_preset_este_mes_fluxo(logged_in_relatorios_page, app_base_url, persona_relatorios):
    user = persona_relatorios["user"]
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    esperado = verify_fluxo_periodo(user, {"preset": "este_mes"})
    assert fluxo.totais_receitas() == esperado["receitas"]
    assert fluxo.totais_despesas() == esperado["despesas"]


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_02_mes_anterior_fluxo(logged_in_relatorios_page, app_base_url, persona_relatorios, filtros):
    user = persona_relatorios["user"]
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    filtros.abrir()
    filtros.selecionar_preset("mes_anterior")
    filtros.aplicar()
    esperado = verify_fluxo_periodo(user, {"preset": "mes_anterior"})
    assert fluxo.totais_receitas() == esperado["receitas"]
    f = filtros_from_params(user, {"preset": "mes_anterior"})
    assert f.data_inicio.strftime("%d/%m") in fluxo.periodo_exibido()


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_03_ultimos_30d_categoria(logged_in_relatorios_page, app_base_url, persona_relatorios, filtros):
    user = persona_relatorios["user"]
    cat = DespesasCategoriaPage(logged_in_relatorios_page, app_base_url)
    cat.open()
    filtros.abrir()
    filtros.selecionar_preset("ultimos_30d")
    filtros.aplicar()
    esperado = verify_categoria_total(user, {"preset": "ultimos_30d"})
    assert cat.total_despesas() == esperado


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_04_ultimos_90d_conta(logged_in_relatorios_page, app_base_url, persona_relatorios, filtros):
    user = persona_relatorios["user"]
    conta = PorContaPage(logged_in_relatorios_page, app_base_url)
    conta.open()
    filtros.abrir()
    filtros.selecionar_preset("ultimos_90d")
    filtros.aplicar()
    esperado = verify_conta_patrimonio(user, {"preset": "ultimos_90d"})
    assert conta.patrimonio_total() == esperado


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_05_este_ano_fluxo(logged_in_relatorios_page, app_base_url, persona_relatorios, filtros):
    user = persona_relatorios["user"]
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    filtros.abrir()
    filtros.selecionar_preset("este_ano")
    filtros.aplicar()
    esperado = verify_fluxo_periodo(user, {"preset": "este_ano"})
    assert fluxo.totais_receitas() == esperado["receitas"]


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_06_custom_intervalo(logged_in_relatorios_page, app_base_url, persona_relatorios, filtros):
    user = persona_relatorios["user"]
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    filtros.abrir()
    f_ref = filtros_from_params(user, {"preset": "este_mes"})
    filtros.preencher_intervalo_custom(
        f_ref.data_inicio.isoformat(),
        f_ref.data_fim.isoformat(),
    )
    expect(logged_in_relatorios_page.locator('[data-filtro-datas]').first).to_be_visible()
    filtros.aplicar()
    assert f_ref.data_inicio.strftime("%d/%m") in fluxo.periodo_exibido()


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_07_filtro_conta(logged_in_relatorios_page, app_base_url, persona_relatorios, filtros):
    user = persona_relatorios["user"]
    conta_b = persona_relatorios["conta_b"]
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    filtros.abrir()
    filtros.desmarcar_todas_contas()
    filtros.marcar_conta(conta_b.id)
    filtros.aplicar()
    esperado = verify_fluxo_periodo(user, {"preset": "este_mes", "conta": [conta_b.id]})
    assert fluxo.totais_despesas() == esperado["despesas"]
    assert fluxo.totais_receitas() == Decimal("0")


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_08_filtro_categoria(logged_in_relatorios_page, app_base_url, persona_relatorios, filtros):
    user = persona_relatorios["user"]
    cat_id = persona_relatorios["cat_transporte"].id
    pag = DespesasCategoriaPage(logged_in_relatorios_page, app_base_url)
    pag.open()
    filtros.abrir()
    filtros.marcar_categoria(cat_id)
    filtros.aplicar()
    esperado = verify_categoria_total(
        user, {"preset": "este_mes", "categoria": [cat_id]}
    )
    assert pag.total_despesas() == esperado


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_09_tipo_despesa(logged_in_relatorios_page, app_base_url, persona_relatorios, filtros):
    user = persona_relatorios["user"]
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    filtros.abrir()
    filtros.desmarcar_todos_tipos()
    filtros.marcar_tipo("despesa")
    filtros.aplicar()
    esperado = verify_fluxo_periodo(user, {"preset": "este_mes", "tipo": ["despesa"]})
    assert fluxo.totais_receitas() == Decimal("0")
    assert fluxo.totais_despesas() == esperado["despesas"]


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_10_tipo_receita(logged_in_relatorios_page, app_base_url, persona_relatorios, filtros):
    user = persona_relatorios["user"]
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    filtros.abrir()
    filtros.desmarcar_todos_tipos()
    filtros.marcar_tipo("receita")
    filtros.aplicar()
    esperado = verify_fluxo_periodo(user, {"preset": "este_mes", "tipo": ["receita"]})
    assert fluxo.totais_despesas() == Decimal("0")
    assert fluxo.totais_receitas() == esperado["receitas"]


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_11_conta_categoria_tipo(logged_in_relatorios_page, app_base_url, persona_relatorios, filtros):
    user = persona_relatorios["user"]
    conta_a = persona_relatorios["conta_a"]
    cat_desp = persona_relatorios["cat_despesa"].id
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    filtros.abrir()
    filtros.desmarcar_todas_contas()
    filtros.marcar_conta(conta_a.id)
    filtros.marcar_categoria(cat_desp)
    filtros.desmarcar_todos_tipos()
    filtros.marcar_tipo("despesa")
    filtros.aplicar()
    esperado = verify_fluxo_periodo(
        user,
        {
            "preset": "este_mes",
            "conta": [conta_a.id],
            "categoria": [cat_desp],
            "tipo": ["despesa"],
        },
    )
    assert fluxo.totais_despesas() == esperado["despesas"]


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_12_limpar_filtros(logged_in_relatorios_page, app_base_url, persona_relatorios, filtros):
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open("?preset=mes_anterior")
    filtros.abrir()
    filtros.limpar()
    assert "preset=este_mes" in logged_in_relatorios_page.url


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_13_badge_contador(logged_in_relatorios_page, app_base_url, persona_relatorios, filtros):
    home = RelatoriosHomePage(logged_in_relatorios_page, app_base_url)
    home.open()
    filtros.abrir()
    filtros.desmarcar_todas_contas()
    filtros.marcar_conta(persona_relatorios["conta_b"].id)
    filtros.aplicar()
    f = filtros_from_params(
        persona_relatorios["user"],
        {"preset": "este_mes", "conta": [persona_relatorios["conta_b"].id]},
    )
    assert filtros.badge_ativos() == f.contagem_filtros_ativos()


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_14_persistencia_entre_abas(logged_in_relatorios_page, app_base_url, persona_relatorios, filtros):
    home = RelatoriosHomePage(logged_in_relatorios_page, app_base_url)
    home.open()
    filtros.abrir()
    filtros.selecionar_preset("ultimos_30d")
    filtros.aplicar()
    def _filtros_qs(url: str) -> dict:
        return parse_qs(urlparse(url).query)

    home.ir_para_aba("Entradas x Saídas")
    qs_fluxo = _filtros_qs(logged_in_relatorios_page.url)
    assert qs_fluxo.get("preset") == ["ultimos_30d"]
    home.ir_para_aba("Por categoria")
    qs_cat = _filtros_qs(logged_in_relatorios_page.url)
    assert qs_cat.get("preset") == qs_fluxo.get("preset")
    assert qs_cat.get("inicio") == qs_fluxo.get("inicio")
    assert qs_cat.get("fim") == qs_fluxo.get("fim")


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_15_orcamentos_nao_herda_qs(logged_in_relatorios_page, app_base_url, filtros):
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open("?preset=ultimos_90d&conta=1")
    home = RelatoriosHomePage(logged_in_relatorios_page, app_base_url)
    home.ir_para_aba("Orçamentos")
    assert "preset=" not in logged_in_relatorios_page.url
    assert "conta=" not in logged_in_relatorios_page.url


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_16_fechar_escape_sem_aplicar(logged_in_relatorios_page, app_base_url, filtros):
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    url_antes = logged_in_relatorios_page.url
    filtros.abrir()
    filtros.selecionar_preset("mes_anterior")
    filtros.fechar_escape()
    assert logged_in_relatorios_page.url == url_antes


@pytest.mark.relatorios
@pytest.mark.relatorios_filtros
@pytest.mark.django_db(transaction=True)
def test_fil_17_custom_mostra_datas(logged_in_relatorios_page, app_base_url, filtros):
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    filtros.abrir()
    filtros.selecionar_preset("custom")
    assert filtros.bloco_datas_visivel()
