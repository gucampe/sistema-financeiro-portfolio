from __future__ import annotations

import re
from decimal import Decimal

from playwright.sync_api import Page, expect

from e2e.fixtures.pages.base_page import BasePage
from e2e.helpers.moeda import parse_moeda_ptbr


class FiltrosPortalPage(BasePage):
    BTN_ABRIR = ".js-abrir-filtros-portal"
    FORM = "#form-filtros-panel"
    PRESET = "#filtro-preset-panel"
    PORTAL = "#filtros-portal"
    PANEL = "#filtros-portal-panel"

    def abrir(self) -> None:
        self.page.locator(self.BTN_ABRIR).first.click()
        expect(self.page.locator(self.PORTAL)).to_have_attribute("data-open", "true")

    def fechar_escape(self) -> None:
        self.page.keyboard.press("Escape")
        expect(self.page.locator(self.PORTAL)).to_have_attribute("data-open", "false")

    def selecionar_preset(self, preset: str) -> None:
        self.page.select_option(self.PRESET, value=preset)
        self.page.locator(self.PRESET).dispatch_event("change")

    def marcar_conta(self, conta_id: int, *, checked: bool = True) -> None:
        loc = self.page.locator(
            f'{self.FORM} input[name="conta"][value="{conta_id}"]'
        )
        if checked:
            loc.check()
        else:
            loc.uncheck()

    def desmarcar_todas_contas(self) -> None:
        for cb in self.page.locator(f'{self.FORM} input[name="conta"]').all():
            cb.uncheck()

    def marcar_tipo(self, tipo: str, *, checked: bool = True) -> None:
        loc = self.page.locator(f'{self.FORM} input[name="tipo"][value="{tipo}"]')
        if checked:
            loc.check()
        else:
            loc.uncheck()

    def desmarcar_todos_tipos(self) -> None:
        for cb in self.page.locator(f'{self.FORM} input[name="tipo"]').all():
            cb.uncheck()

    def marcar_categoria(self, categoria_id: int) -> None:
        trigger = self.page.locator(f'{self.FORM} [data-cat-trigger]').first
        trigger.click()
        picker = self.page.locator("#cat-picker-panel")
        expect(picker).to_have_attribute("data-open", "true")
        cb = picker.locator(f'input[name="categoria"][value="{categoria_id}"]')
        cb.check()
        self.page.locator("#cat-picker-panel [data-cat-picker-back]").click()

    def preencher_intervalo_custom(self, inicio: str, fim: str) -> None:
        self.selecionar_preset("custom")
        self.page.locator("#filtro-inicio-panel").fill(inicio)
        self.page.locator("#filtro-fim-panel").fill(fim)

    def aplicar(self) -> None:
        with self.page.expect_navigation(timeout=45000, wait_until="load"):
            self.page.locator(f'{self.FORM} button[type="submit"]').click()

    def limpar(self) -> None:
        with self.page.expect_navigation(timeout=45000, wait_until="load"):
            self.page.locator(f'{self.FORM} a.btn').filter(has_text="Limpar").click()

    def badge_ativos(self) -> int:
        texto = self.page.locator(self.BTN_ABRIR).first.inner_text()
        m = re.search(r"Filtros\s*\((\d+)\)", texto)
        return int(m.group(1)) if m else 0

    def bloco_datas_visivel(self) -> bool:
        bloco = self.page.locator(f'{self.FORM} [data-filtro-datas]').first
        return bloco.is_visible()


class FluxoCaixaPage(BasePage):
    RESUMO = '[aria-label="Resumo do período"]'

    def open(self, query: str = "") -> None:
        self.goto(f"/relatorios/fluxo-caixa/{query}")

    def totais_receitas(self) -> Decimal:
        loc = self.page.locator(f"{self.RESUMO} .grid > div").nth(0).locator(".tabular-nums")
        return parse_moeda_ptbr(loc.inner_text())

    def totais_despesas(self) -> Decimal:
        loc = self.page.locator(f"{self.RESUMO} .grid > div").nth(1).locator(".tabular-nums")
        return parse_moeda_ptbr(loc.inner_text())

    def totais_resultado(self) -> Decimal:
        loc = self.page.locator(f"{self.RESUMO} .grid > div").nth(2).locator(".tabular-nums")
        return parse_moeda_ptbr(loc.inner_text())

    def periodo_exibido(self) -> str:
        return self.page.locator(f"{self.RESUMO} .text-sm.text-gray-500").first.inner_text()


class DespesasCategoriaPage(BasePage):
    HERO = '[aria-label="Resumo de despesas por categoria"]'

    def open(self, query: str = "") -> None:
        self.goto(f"/relatorios/despesas-por-categoria/{query}")

    def total_despesas(self) -> Decimal:
        loc = self.page.locator(f'{self.HERO} article:has-text("Total de despesas") .tabular-nums')
        return parse_moeda_ptbr(loc.inner_text())

    def periodo_exibido(self) -> str:
        return self.page.locator(f"{self.HERO} .text-sm.text-gray-500").first.inner_text()


class PorContaPage(BasePage):
    HERO = '[aria-label="Resumo patrimonial por conta"]'

    def open(self, query: str = "") -> None:
        self.goto(f"/relatorios/por-conta/{query}")

    def patrimonio_total(self) -> Decimal:
        loc = self.page.locator(f'{self.HERO} article:has-text("Patrimônio total") .tabular-nums')
        return parse_moeda_ptbr(loc.inner_text())

    def movimento_periodo(self) -> Decimal:
        loc = self.page.locator(f'{self.HERO} article:has-text("Variação no período") .tabular-nums').first
        return parse_moeda_ptbr(loc.inner_text())

    def periodo_exibido(self) -> str:
        return self.page.locator(f"{self.HERO} .text-sm.text-gray-500").first.inner_text()


class RelatoriosHomePage(BasePage):
    """Visão geral — KPIs do mês."""

    HERO = "#secao-resumo-hero"
    ROOT = "#dashboard-root"

    def open(self, query: str = "") -> None:
        path = "/relatorios/"
        if query:
            path = f"{path}?{query.lstrip('?')}"
        self.goto(path)

    def kpi_receitas(self) -> Decimal:
        loc = self.page.locator(f"{self.HERO} .text-emerald-700 .dash-valor").first
        expect(loc).to_be_visible()
        return parse_moeda_ptbr(loc.inner_text())

    def kpi_despesas(self) -> Decimal:
        loc = self.page.locator(f"{self.HERO} .text-rose-700 .dash-valor").first
        expect(loc).to_be_visible()
        return parse_moeda_ptbr(loc.inner_text())

    def kpi_resultado(self) -> Decimal:
        loc = self.page.locator(f"{self.HERO} .dash-valor").nth(2)
        expect(loc).to_be_visible()
        return parse_moeda_ptbr(loc.inner_text())

    def kpis_hero(self) -> dict[str, Decimal]:
        return {
            "receitas": self.kpi_receitas(),
            "despesas": self.kpi_despesas(),
            "resultado": self.kpi_resultado(),
        }

    def snapshot_kpis_hero(self) -> dict[str, Decimal]:
        return self.kpis_hero()

    def patrimonio(self) -> Decimal:
        sec = self.page.locator("section").filter(has_text="Patrimônio disponível")
        loc = sec.locator(".dash-valor").first
        expect(loc).to_be_visible()
        return parse_moeda_ptbr(loc.inner_text())

    def toggle_ocultar(self) -> None:
        self.page.locator("#btn-toggle-valores").click()

    def valores_ocultos(self) -> bool:
        return self.page.locator(self.ROOT).get_attribute("data-ocultar") == "1"

    def abrir_nova_receita(self) -> None:
        self.page.locator('[data-abrir-transacao="receita"]').first.click()

    def abrir_nova_despesa(self) -> None:
        self.page.locator('[data-abrir-transacao="despesa"]').first.click()

    def ir_para_aba(self, nome: str) -> None:
        with self.page.expect_navigation(timeout=45000, wait_until="load"):
            self.page.locator(".relatorios-tab").filter(has_text=nome).click()

    def query_string(self) -> str:
        url = self.page.url
        return url.split("?", 1)[1] if "?" in url else ""
