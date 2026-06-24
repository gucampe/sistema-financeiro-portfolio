from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect

from e2e.fixtures.pages.base_page import BasePage


class ImportOfxPage(BasePage):
    OVERLAY = "#overlay-importar-ofx"
    TBODY = "#import-ofx-tbody"
    ERRO_UPLOAD = "#import-ofx-erro-upload"

    def __init__(self, page, base_url: str) -> None:
        super().__init__(page, base_url)
        self.last_preview: dict | None = None

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

    def linha_por_descricao_parcial(self, trecho: str):
        rows = self.page.locator(f"{self.TBODY} tr")
        for i in range(rows.count()):
            row = rows.nth(i)
            desc = row.locator(".import-ofx-descricao").input_value()
            if trecho.strip() in (desc or ""):
                return row
        return None

    def categoria_preview(self, row) -> tuple[str, str, str]:
        """Retorna (nome_categoria, fonte_sugestao, explicacao) da linha no preview."""
        sel = row.locator(".import-ofx-categoria")
        cat_id = sel.input_value() or sel.get_attribute("data-sugestao-id") or ""
        if cat_id:
            cat_nome = sel.locator(f'option[value="{cat_id}"]').inner_text().strip()
        else:
            cat_nome = ""
        fonte = sel.get_attribute("data-sugestao-fonte") or ""
        explicacao = sel.get_attribute("data-sugestao-explicacao") or sel.get_attribute("title") or ""
        return cat_nome, fonte.strip(), explicacao.strip()

    def preview_ofx(self, conta_id: int, ofx_path: str | Path) -> dict:
        self.abrir()
        self.selecionar_conta(conta_id)
        self.upload(ofx_path)
        with self.page.expect_response(
            lambda r: "importar/ofx/preview" in r.url and r.request.method == "POST"
        ) as resp_info:
            self.page.click("#btn-import-ofx-preview")
        self.page.wait_for_selector("#import-ofx-step-preview:not(.hidden)", timeout=30000)
        response = resp_info.value
        self.last_preview = response.json()
        return self.last_preview

    def linha_json_por_trecho(self, trecho: str) -> dict | None:
        if not self.last_preview:
            return None
        for linha in self.last_preview.get("linhas", []):
            if trecho.strip() in (linha.get("descricao") or ""):
                return linha
        return None

    def sugestao_preview_json(self, trecho: str) -> tuple[str, str, str]:
        """Nome, fonte e explicação a partir do JSON do preview (fonte de verdade)."""
        linha = self.linha_json_por_trecho(trecho)
        if not linha:
            return "", "", ""
        return (
            str(linha.get("categoria_sugerida_nome") or "").strip(),
            str(linha.get("categoria_sugerida_fonte") or "").strip(),
            str(linha.get("categoria_sugerida_explicacao") or "").strip(),
        )


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
