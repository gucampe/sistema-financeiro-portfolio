from __future__ import annotations

from decimal import Decimal

from playwright.sync_api import Page, expect

from e2e.fixtures.pages.base_page import BasePage
from e2e.helpers.moeda import parse_moeda_ptbr
class FaturaDetalhePage(BasePage):
    def open(self, cartao_id: int, fatura_id: int) -> None:
        self.goto(f"/cartoes/{cartao_id}/faturas/{fatura_id}/")

    def pagar(self, valor: Decimal | None = None) -> None:
        if valor is not None:
            self.page.evaluate(
                """(v) => {
                    const el = document.querySelector('form[action*="pagar"] input[name="valor"]');
                    if (el && window.MoedaInput) {
                        window.MoedaInput.setValueFromDecimal(el, v);
                    } else if (el) {
                        el.value = v;
                    }
                }""",
                str(valor),
            )
        self.page.get_by_role("button", name="Pagar fatura").or_(
            self.page.get_by_role("button", name="Pagar restante")
        ).click()
        self.page.wait_for_load_state("load")

    def status_text(self) -> str:
        return self.page.locator("text=Status da fatura").locator("..").inner_text()

    def saldo_restante(self) -> str:
        return self.page.locator("text=Falta pagar").locator("..").inner_text()

    def acao_pagar_visivel(self) -> bool:
        form = self.page.locator('form[action*="pagar"]')
        btn = form.get_by_role("button", name="Pagar fatura").or_(
            form.get_by_role("button", name="Pagar restante")
        )
        return form.count() > 0 and btn.is_visible()

    def saldo_restante_valor(self) -> Decimal:
        bloco = self.page.locator("text=Falta pagar").locator("..")
        if bloco.count() > 0:
            valor_el = bloco.locator("p.tabular-nums").first
            if valor_el.count() > 0:
                return parse_moeda_ptbr(valor_el.inner_text())
        saldo_col = self.page.locator("text=Saldo").locator("..").locator("p").last
        return parse_moeda_ptbr(saldo_col.inner_text())

    def falta_pagar_ausente(self) -> bool:
        """Saldo restante zero — equivalente a nada a pagar."""
        return self.saldo_restante_valor() == Decimal("0")

    def indicador_atraso_presente(self) -> bool:
        return self.page.locator("span.bg-rose-50").count() > 0
