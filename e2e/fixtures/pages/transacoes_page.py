from __future__ import annotations

from datetime import date
from decimal import Decimal

from playwright.sync_api import Page, expect

from e2e.fixtures.pages.base_page import BasePage
class TransacaoModalPage(BasePage):
    OVERLAY = "#overlay-adicionar"

    def wait_modal_open(self) -> None:
        expect(self.page.locator(self.OVERLAY)).to_be_visible()

    def select_conta(self, conta_id: int) -> None:
        self.page.wait_for_selector(
            f"#id_conta_cartao option[value='c:{conta_id}']",
            state="attached",
            timeout=10000,
        )
        self.page.select_option("#id_conta_cartao", value=f"c:{conta_id}")
        self.page.locator("#id_conta_cartao").dispatch_event("change")

    def select_cartao(self, cartao_id: int) -> None:
        self.page.wait_for_selector(
            f"#id_conta_cartao option[value='k:{cartao_id}']",
            state="attached",
            timeout=10000,
        )
        self.page.select_option("#id_conta_cartao", value=f"k:{cartao_id}")
        self.page.locator("#id_conta_cartao").dispatch_event("change")

    def select_categoria(self, categoria_id: int) -> None:
        self._wait_categoria_option(categoria_id)
        self.page.select_option("#categoria", value=str(categoria_id))
        self.page.locator("#categoria").dispatch_event("change")
        self.page.wait_for_function(
            f"""() => document.getElementById('categoria')?.value === '{categoria_id}'""",
            timeout=5000,
        )

    def fill_valor(self, valor: Decimal) -> None:
        self.page.evaluate(
            """(v) => {
                const el = document.getElementById('valor');
                if (window.MoedaInput) {
                    window.MoedaInput.setValueFromDecimal(el, v);
                } else {
                    el.value = v;
                }
            }""",
            str(valor),
        )

    def fill_descricao(self, texto: str) -> None:
        self.page.fill("#descricao", texto)

    def fill_data(self, d: date) -> None:
        self.page.fill("#data", d.isoformat())

    def set_tipo(self, tipo: str) -> None:
        if self.page.locator("#tipo").input_value() != tipo:
            self.page.select_option("#tipo", value=tipo)
            self.page.locator("#tipo").dispatch_event("change")

    def _wait_categoria_option(self, categoria_id: int) -> None:
        self.page.wait_for_function(
            f"""() => {{
                const opt = document.querySelector('#categoria option[value="{categoria_id}"]');
                return opt !== null;
            }}""",
            timeout=15000,
        )

    def salvar(self, wait_reload: bool = True) -> None:
        if wait_reload:
            with self.page.expect_navigation(timeout=45000, wait_until="load"):
                self.page.click("#btn-salvar-transacao")
        else:
            with self.page.expect_response(
                lambda r: "/transacoes" in r.url and r.request.method == "POST",
                timeout=30000,
            ):
                self.page.click("#btn-salvar-transacao")

    def salvar_double_click(self) -> None:
        btn = self.page.locator("#btn-salvar-transacao")
        btn.dblclick()
        self.page.wait_for_timeout(500)

    def criar_transacao(
        self,
        *,
        tipo: str,
        conta_id: int | None,
        cartao_id: int | None,
        categoria_id: int,
        valor: Decimal,
        descricao: str,
        data: date,
    ) -> None:
        self.wait_modal_open()
        self.set_tipo(tipo)
        self._wait_categoria_option(categoria_id)
        if cartao_id:
            self.select_cartao(cartao_id)
        elif conta_id:
            self.select_conta(conta_id)
        self.select_categoria(categoria_id)
        self.fill_valor(valor)
        self.fill_descricao(descricao)
        self.fill_data(data)
        self.salvar()


class HistoricoPage(BasePage):
    def open(self, ano: int | None = None, mes: int | None = None) -> None:
        path = "/transacoes/"
        if ano and mes:
            path += f"?ano={ano}&mes={mes}"
        self.goto(path)

    def editar_por_id(self, transacao_id: int) -> None:
        self.page.evaluate(
            f"() => window.abrirModalEditarTransacao('{transacao_id}')"
        )
        self.page.wait_for_function(
            "() => !document.getElementById('overlay-adicionar')?.classList.contains('hidden')",
            timeout=15000,
        )

    def excluir_por_id(self, transacao_id: int) -> None:
        row = self.page.locator(f"li[data-transacao-id='{transacao_id}']")
        row.scroll_into_view_if_needed()
        row.hover()
        btn = self.page.locator(f".excluir-transacao[data-id='{transacao_id}']")
        btn.evaluate("el => el.click()")
        self.page.click("#confirmar-exclusao")
        self.page.wait_for_load_state("load")
