from __future__ import annotations

from decimal import Decimal

from playwright.sync_api import Page, expect

from e2e.fixtures.pages.base_page import BasePage
from e2e.helpers.moeda import parse_moeda_ptbr


class DashboardPage(BasePage):
    def open(self) -> None:
        self.goto("/relatorios/")

    def kpi_receitas(self) -> Decimal:
        loc = self.page.locator("#secao-resumo-hero .text-emerald-700 .dash-valor").first
        expect(loc).to_be_visible()
        return parse_moeda_ptbr(loc.inner_text())

    def kpi_despesas(self) -> Decimal:
        loc = self.page.locator("#secao-resumo-hero .text-rose-700 .dash-valor").first
        expect(loc).to_be_visible()
        return parse_moeda_ptbr(loc.inner_text())

    def open_nova_despesa(self) -> None:
        self.page.locator('[data-abrir-transacao="despesa"]').first.click()

    def open_nova_receita(self) -> None:
        self.page.locator('[data-abrir-transacao="receita"]').first.click()
