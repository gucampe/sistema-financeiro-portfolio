from __future__ import annotations

import re
from decimal import Decimal

from playwright.sync_api import Page, expect

from e2e.fixtures.pages.base_page import BasePage
from e2e.helpers.moeda import parse_moeda_ptbr


class OrcamentosPage(BasePage):
    ROOT = "#orcamentos-root"
    HERO = "#orcamento-hero-resumo"

    def open(self, query: str = "") -> None:
        path = "/relatorios/orcamentos/"
        if query:
            path = f"{path}?{query.lstrip('?')}"
        self.goto(path)

    def painel_percentual(self) -> float | None:
        hero = self.page.locator(self.HERO)
        if hero.count() == 0:
            return None
        texto = hero.inner_text()
        m = re.search(r"(\d+)%", texto)
        return float(m.group(1)) if m else None

    def painel_orcado(self) -> Decimal:
        loc = self.page.locator(self.HERO).locator("dt", has_text="Orçado").locator("..").locator("dd")
        return parse_moeda_ptbr(loc.inner_text())

    def painel_gasto(self) -> Decimal:
        loc = self.page.locator(self.HERO).locator("dt", has_text="Gasto").locator("..").locator("dd")
        return parse_moeda_ptbr(loc.inner_text())

    def contagem_saude(self, tipo: str) -> int:
        label = {"ok": "Saudáveis", "risco": "Em atenção", "excedido": "Estouradas"}[tipo]
        card = self.page.locator(
            'section[aria-label="Resumo do orçamento do mês"] .grid > .card'
        ).filter(has_text=label)
        return int(card.locator("p.tabular-nums.text-2xl").inner_text())

    def card_categoria(self, nome: str):
        return self.page.locator(f'[data-orcamento-card]:has-text("{nome}")')

    def percentual_categoria(self, nome: str) -> str:
        card = self.card_categoria(nome)
        loc = card.locator("p", has_text="Consumido").locator("..").locator(".tabular-nums")
        return loc.inner_text().strip()

    def status_categoria(self, nome: str) -> str:
        card = self.card_categoria(nome)
        badge = card.locator("span.rounded-full").filter(
            has_text=re.compile(r"Saudável|Atenção|Estourado|Pausado|Fora")
        )
        return badge.first.inner_text()

    def abrir_novo_orcamento(self) -> None:
        btn = self.page.locator("#btn-novo-orcamento, #btn-primeiro-orcamento").first
        btn.click()

    def realizado_categoria_id(self, categoria_id: int) -> Decimal:
        card = self.page.locator(
            f'[data-orcamento-card][data-categoria-id="{categoria_id}"]'
        )
        loc = card.locator("p", has_text="Gasto").locator("..").locator("p.tabular-nums")
        return parse_moeda_ptbr(loc.inner_text())


class ModalOrcamentoPage(BasePage):
    OVERLAY = "#overlay-orcamento"
    FORM = "#form-orcamento"

    def wait_open(self) -> None:
        expect(self.page.locator(self.OVERLAY)).to_be_visible()

    def selecionar_categoria(self, categoria_id: int) -> None:
        self.page.select_option("#id_categoria", value=str(categoria_id))

    def preencher_valor(self, valor: Decimal) -> None:
        self.page.evaluate(
            """(v) => {
                const el = document.getElementById('id_valor_planejado');
                if (window.MoedaInput) {
                    window.MoedaInput.setValueFromDecimal(el, v);
                } else {
                    el.value = v;
                }
            }""",
            str(valor),
        )

    def preencher_vigencia(self, inicio_ano: int, inicio_mes: int) -> None:
        """Vigência implícita pela data de criação — mantido por compatibilidade nos testes."""
        return

    def salvar(self) -> None:
        with self.page.expect_navigation(timeout=45000, wait_until="load"):
            self.page.locator(f"{self.FORM} button[type=submit]").click()

    def pausar_orcamento(self, orcamento_id: int) -> None:
        btn = self.page.locator(
            f'.js-toggle-orcamento[data-orcamento-id="{orcamento_id}"]'
        )
        with self.page.expect_navigation(timeout=45000, wait_until="load"):
            btn.click()
