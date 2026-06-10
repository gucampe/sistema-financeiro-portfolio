from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect

from e2e.fixtures.pages.base_page import BasePage


class ImportOfxPage(BasePage):
    OVERLAY = "#overlay-importar-ofx"
    TBODY = "#import-ofx-tbody"
    ERRO_UPLOAD = "#import-ofx-erro-upload"

    def abrir(self) -> None:
        self.page.goto(f"{self.base_url}/transacoes/")
        self.page.click("#btn-importar-ofx")
        expect(self.page.locator(self.OVERLAY)).to_be_visible()

    def selecionar_conta(self, conta_id: int) -> None:
        self.page.select_option("#import-ofx-conta", value=str(conta_id))
        self.page.locator("#import-ofx-conta").dispatch_event("change")

    def upload(self, path: str | Path) -> None:
        self.page.set_input_files("#import-ofx-arquivo", str(path))

    def aguardar_preview(self) -> None:
        with self.page.expect_response(lambda r: "importar/ofx/preview" in r.url):
            self.page.click("#btn-import-ofx-preview")
        self.page.wait_for_selector("#import-ofx-step-preview:not(.hidden)", timeout=15000)

    def linhas_preview_count(self) -> int:
        return self.page.locator(f"{self.TBODY} tr").count()

    def linha_marcada(self, indice: int) -> bool:
        cb = self.page.locator(f"{self.TBODY} tr").nth(indice).locator(".import-ofx-incluir")
        return cb.is_checked()

    def confirmar(self) -> None:
        with self.page.expect_response(lambda r: "importar/ofx/confirmar" in r.url):
            self.page.click("#btn-import-ofx-confirmar")
        self.page.wait_for_load_state("load")

    def tentar_confirmar_sem_linhas(self) -> str:
        """Clica em confirmar sem linhas marcadas; o cliente bloqueia antes do POST."""
        self.page.click("#btn-import-ofx-confirmar")
        loc = self.page.locator("#import-ofx-erro-preview")
        expect(loc).to_be_visible()
        return loc.inner_text().strip()

    def erro_visivel(self) -> str:
        loc = self.page.locator(self.ERRO_UPLOAD)
        expect(loc).to_be_visible()
        return loc.inner_text().strip()


class ImportPlanilhaPage(BasePage):
    OVERLAY = "#overlay-importar-planilha"
    TBODY = "#import-planilha-tbody"

    def abrir(self) -> None:
        self.page.goto(f"{self.base_url}/transacoes/")
        self.page.click("#btn-importar-planilha")
        expect(self.page.locator(self.OVERLAY)).to_be_visible()

    def selecionar_conta(self, conta_id: int) -> None:
        self.page.select_option("#import-planilha-conta", value=str(conta_id))
        self.page.locator("#import-planilha-conta").dispatch_event("change")

    def upload(self, path: str | Path) -> None:
        self.page.set_input_files("#import-planilha-arquivo", str(path))

    def aguardar_preview(self) -> None:
        with self.page.expect_response(lambda r: "importar/planilha/preview" in r.url):
            self.page.click("#btn-import-planilha-preview")
        self.page.wait_for_selector(
            "#import-planilha-step-preview:not(.hidden)", timeout=15000
        )

    def linhas_preview_count(self) -> int:
        return self.page.locator(f"{self.TBODY} tr").count()

    def confirmar(self) -> None:
        with self.page.expect_response(
            lambda r: "importar" in r.url and "confirmar" in r.url
        ):
            self.page.click("#btn-import-planilha-confirmar")
        self.page.wait_for_load_state("load")
