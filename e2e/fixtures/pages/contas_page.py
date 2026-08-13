from __future__ import annotations

from playwright.sync_api import expect

from e2e.fixtures.pages.base_page import BasePage


class ContasPage(BasePage):
    def open(self) -> None:
        self.goto("/contas/")
        self.page.wait_for_load_state("domcontentloaded")
        expect(self.page.locator("#btn-adicionar-conta")).to_be_visible()

    def criar_conta(self, nome: str, tipo: str = "corrente") -> None:
        self.page.locator("#btn-adicionar-conta").click()
        overlay = self.page.locator("#overlay-modal-conta")
        expect(overlay).to_be_visible()
        self.page.fill("#conta_nome", nome)
        self.page.select_option("#conta_tipo", tipo)
        self.page.locator("#form-modal-conta button[type=submit]").click()
        self.page.wait_for_load_state("domcontentloaded")
        expect(self.item_ativa(nome)).to_be_visible(timeout=15000)

    def item_ativa(self, nome: str):
        return self.page.locator(f'#lista-contas-ativas .conta-item[data-conta-nome="{nome}"]')

    def item_arquivada(self, nome: str):
        return self.page.locator(
            f'#lista-contas-arquivadas .conta-item[data-conta-nome="{nome}"]'
        )

    def arquivar(self, nome: str) -> None:
        item = self.item_ativa(nome)
        item.hover()
        item.locator(".lista-contextual-menu-trigger").click(force=True)
        self.page.locator('[data-lista-acao="arquivar"]').click()
        self.page.wait_for_load_state("domcontentloaded")
        expect(self.item_arquivada(nome)).to_be_visible(timeout=15000)
