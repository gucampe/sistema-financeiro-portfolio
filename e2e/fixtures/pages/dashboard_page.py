from __future__ import annotations

from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from e2e.fixtures.pages.base_page import BasePage
from e2e.helpers.moeda import parse_moeda_ptbr


class DashboardPage(BasePage):
    HERO = "#secao-resumo-hero"

    def open(self) -> None:
        self.goto("/relatorios/")

    def _hero_desktop(self) -> Locator:
        return self.page.locator(f"{self.HERO} > article")

    def _hero_mobile(self) -> Locator:
        return self.page.locator("#dashboard-masonry .dash-mobile")

    def kpi_receitas(self) -> Decimal:
        if self._hero_desktop().is_visible():
            loc = self._hero_desktop().locator("div.grid > div").nth(0).locator(".dash-valor")
        else:
            loc = self._hero_mobile().locator(".dash-mobile__summary-meta .text-emerald-600 .dash-valor")
        expect(loc).to_be_visible()
        return parse_moeda_ptbr(loc.inner_text())

    def kpi_despesas(self) -> Decimal:
        if self._hero_desktop().is_visible():
            loc = self._hero_desktop().locator("div.grid > div").nth(1).locator(".dash-valor")
        else:
            loc = self._hero_mobile().locator(".dash-mobile__summary-meta .text-rose-600 .dash-valor")
        expect(loc).to_be_visible()
        return parse_moeda_ptbr(loc.inner_text())

    def open_nova_despesa(self) -> None:
        self.click_first_visible('[data-abrir-transacao="despesa"]')

    def open_nova_receita(self) -> None:
        self.click_first_visible('[data-abrir-transacao="receita"]')
