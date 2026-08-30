"""Ajuda: deep link, busca sem acento e viewport estreita."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from e2e.factories.personas import E2E_PASSWORD
from e2e.fixtures.pages.faturas_page import FaturaDetalhePage
from e2e.fixtures.pages.login_page import LoginPage


@pytest.mark.ajuda
@pytest.mark.django_db(transaction=True)
def test_ajuda_deep_link_busca_e_voltar(page, app_base_url, persona_basic):
    login = LoginPage(page, app_base_url)
    login.login(persona_basic["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()

    page.goto(f"{app_base_url}/relatorios/?ajuda=mapa", wait_until="domcontentloaded")
    expect(page.locator("#ajuda-overlay")).to_be_visible()
    expect(page.locator("[data-ajuda-artigo-view]")).to_be_visible()
    expect(page.locator("[data-ajuda-artigo-titulo]")).to_have_text(
        "Como o GranaGo organiza seu dinheiro"
    )

    page.locator("[data-ajuda-voltar]").click()
    expect(page.locator("[data-ajuda-home]")).to_be_visible()
    page.locator("[data-ajuda-busca]").fill("cartao")
    expect(page.locator('[data-ajuda-home] [data-ajuda-abrir="cartao"]')).to_be_visible()
    expect(page.locator('[data-ajuda-home] [data-ajuda-abrir="pagar-fatura"]')).to_be_visible()
    expect(page.locator('[data-ajuda-home] [data-ajuda-abrir="transferencia"]')).to_be_hidden()

    page.locator('[data-ajuda-home] [data-ajuda-abrir="cartao"]').click()
    expect(page.locator("[data-ajuda-artigo-view]")).to_be_visible()
    expect(page.locator("[data-ajuda-artigo-titulo]")).to_have_text(
        "Como funciona o cartão de crédito"
    )

    page.locator("[data-ajuda-voltar]").click()
    expect(page.locator("[data-ajuda-home]")).to_be_visible()
    expect(page.locator("[data-ajuda-busca]")).to_have_value("cartao")
    expect(page.locator('[data-ajuda-home] [data-ajuda-abrir="cartao"]')).to_be_visible()
    expect(page.locator('[data-ajuda-home] [data-ajuda-abrir="transferencia"]')).to_be_hidden()


@pytest.mark.ajuda
@pytest.mark.django_db(transaction=True)
def test_ajuda_deep_link_resultado(page, app_base_url, persona_basic):
    login = LoginPage(page, app_base_url)
    login.login(persona_basic["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()

    page.goto(f"{app_base_url}/relatorios/?ajuda=resultado", wait_until="domcontentloaded")
    expect(page.locator("#ajuda-overlay")).to_be_visible()
    expect(page.locator("[data-ajuda-artigo-titulo]")).to_have_text("Como funciona o resultado")
    page.locator("#ajuda-overlay").get_by_role("button", name="Entendi").click()
    expect(page.locator("#ajuda-overlay")).to_be_hidden()


@pytest.mark.ajuda
@pytest.mark.django_db(transaction=True)
def test_ajuda_sem_overflow_no_mobile(page, app_base_url, persona_basic):
    page.set_viewport_size({"width": 390, "height": 844})
    login = LoginPage(page, app_base_url)
    login.login(persona_basic["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()

    page.goto(f"{app_base_url}/relatorios/?ajuda=cartao", wait_until="domcontentloaded")
    expect(page.locator("#ajuda-overlay")).to_be_visible()
    overflow = page.evaluate(
        """() => {
            const corpo = document.querySelector('[data-ajuda-artigo-corpo]');
            const painel = document.querySelector('.modal-panel--ajuda');
            if (!corpo || !painel) return true;
            return corpo.scrollWidth > corpo.clientWidth || painel.scrollWidth > painel.clientWidth;
        }"""
    )
    assert overflow is False


@pytest.mark.ajuda
@pytest.mark.django_db(transaction=True)
def test_ajuda_pagar_fatura_deep_link_e_leia_tambem(page, app_base_url, persona_basic):
    login = LoginPage(page, app_base_url)
    login.login(persona_basic["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()

    page.goto(f"{app_base_url}/relatorios/?ajuda=pagar-fatura", wait_until="domcontentloaded")
    overlay = page.locator("#ajuda-overlay")
    expect(overlay).to_be_visible()
    expect(page.locator("[data-ajuda-artigo-titulo]")).to_have_text("Como pagar a fatura")
    expect(page.get_by_role("link", name="Ir para cartões")).to_be_visible()

    page.locator('[data-ajuda-artigo-view] [data-ajuda-abrir="cartao"]').click()
    expect(overlay).to_be_visible()
    expect(page.locator("[data-ajuda-artigo-titulo]")).to_have_text(
        "Como funciona o cartão de crédito"
    )
    expect(page.locator('[data-ajuda-artigo-view] [data-ajuda-abrir="pagar-fatura"]')).to_be_visible()


@pytest.mark.ajuda
@pytest.mark.django_db(transaction=True)
def test_ajuda_transacao_deep_link_e_leia_tambem(page, app_base_url, persona_basic):
    login = LoginPage(page, app_base_url)
    login.login(persona_basic["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()

    page.goto(f"{app_base_url}/relatorios/?ajuda=transacao", wait_until="domcontentloaded")
    overlay = page.locator("#ajuda-overlay")
    expect(overlay).to_be_visible()
    expect(page.locator("#ajuda-titulo")).to_have_text("Ajuda")
    expect(page.locator("[data-ajuda-artigo-titulo]")).to_have_text("Como funciona uma transação")
    expect(page.get_by_role("link", name="Adicionar transação")).to_be_visible()

    page.locator('[data-ajuda-artigo-view] [data-ajuda-abrir="transferencia"]').click()
    expect(overlay).to_be_visible()
    expect(page.locator("[data-ajuda-artigo-titulo]")).to_have_text(
        "Como funcionam as transferências"
    )


@pytest.mark.ajuda
@pytest.mark.django_db(transaction=True)
def test_ajuda_link_contextual_na_fatura(page, app_base_url, persona_card):
    login = LoginPage(page, app_base_url)
    login.login(persona_card["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()

    cartao = persona_card["cartao"]
    fatura = persona_card["fatura"]
    assert fatura is not None
    FaturaDetalhePage(page, app_base_url).open(cartao.pk, fatura.pk)
    page.locator('a[href="?ajuda=pagar-fatura"]').click()
    expect(page.locator("#ajuda-overlay")).to_be_visible()
    expect(page.locator("[data-ajuda-artigo-titulo]")).to_have_text("Como pagar a fatura")
