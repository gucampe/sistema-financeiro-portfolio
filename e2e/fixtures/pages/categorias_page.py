from __future__ import annotations

from playwright.sync_api import expect

from e2e.fixtures.pages.base_page import BasePage


class CategoriasPage(BasePage):
    def open(self) -> None:
        self.goto("/categorias/")
        self.page.wait_for_load_state("domcontentloaded")
        expect(self.page.locator("#btn-adicionar-categoria")).to_be_visible()

    def criar_despesa(self, nome: str) -> None:
        self.page.locator("#btn-adicionar-categoria").click()
        overlay = self.page.locator("#overlay-adicionar-categoria")
        expect(overlay).to_be_visible(timeout=15000)
        self.page.select_option("#tipo", "despesa")
        self.page.fill("#nome", nome)
        self.page.locator('#icon-grid [data-value="fa-utensils"]').click()
        self.page.locator('#color-grid [data-value="#EF4444"]').click()
        self.page.locator("#form-adicionar-categoria button[type=submit]").click()
        expect(self.item_ativa(nome)).to_be_visible(timeout=15000)

    def item_ativa(self, nome: str):
        return self.page.locator(
            f'#lista-despesa [data-categoria-item][data-categoria-nome="{nome}"]'
        )

    def arquivar(self, nome: str) -> None:
        item = self.item_ativa(nome)
        item.hover()
        item.locator(".lista-contextual-menu-trigger").click(force=True)
        self.page.locator('[data-lista-acao="arquivar"]').click()
        confirm = self.page.locator("#btn-confirmar-acao")
        expect(confirm).to_be_visible()
        confirm.click()
        expect(self.item_ativa(nome)).to_have_count(0, timeout=15000)
