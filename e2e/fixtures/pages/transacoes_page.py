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
        # Garante que a seleção sobrevive a rebuild assíncrono de opções (popularCategorias).
        self.page.wait_for_function(
            f"""() => {{
                const sel = document.getElementById('categoria');
                if (!sel || sel.value !== '{categoria_id}') return false;
                const opt = sel.querySelector('option[value="{categoria_id}"]');
                return !!opt;
            }}""",
            timeout=15000,
        )

    def select_categoria_by_name(self, nome: str) -> None:
        self.page.wait_for_selector("#categoria option", state="attached", timeout=15000)
        self.page.select_option("#categoria", label=nome)
        self.page.locator("#categoria").dispatch_event("change")

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

    def limpar_meta_sugestao(self) -> None:
        """Remove metadados do chip de sugestão (simula usuário sem aceitar IA)."""
        self.page.evaluate(
            """() => {
                ['categorizacao_sugerida_id', 'categorizacao_confianca',
                 'categorizacao_fonte', 'categorizacao_merchant_key'].forEach((id) => {
                    const el = document.getElementById(id);
                    if (el) el.value = '';
                });
                const chip = document.getElementById('categorizacao-sugestao-chip');
                if (chip) {
                    chip.classList.add('hidden');
                    chip.innerHTML = '';
                }
            }"""
        )

    def aguardar_sugestao_categorizacao(self, timeout_ms: int = 12000) -> None:
        """Aguarda chip de sugestão (LLM ou híbrido) após preencher descrição."""
        self.page.wait_for_function(
            """() => {
                const chip = document.getElementById('categorizacao-sugestao-chip');
                return chip && !chip.classList.contains('hidden') && chip.textContent.trim().length > 0;
            }""",
            timeout=timeout_ms,
        )

    def fill_data(self, d: date) -> None:
        self.page.fill("#data", d.isoformat())

    def set_tipo(self, tipo: str) -> None:
        if self.page.locator("#tipo").input_value() != tipo:
            self.page.select_option("#tipo", value=tipo)
            self.page.locator("#tipo").dispatch_event("change")
            # Aguarda UI de transferência (origem/destino) quando aplicável.
            if tipo == "transferencia":
                expect(self.page.locator("#bloco-transferencia")).to_be_visible()

    def select_conta_origem(self, conta_id: int) -> None:
        self.page.wait_for_selector(
            f"#conta_origem option[value='{conta_id}']",
            state="attached",
            timeout=10000,
        )
        self.page.select_option("#conta_origem", value=str(conta_id))
        self.page.locator("#conta_origem").dispatch_event("change")

    def select_conta_destino(self, conta_id: int) -> None:
        self.page.wait_for_selector(
            f"#conta_destino option[value='{conta_id}']",
            state="attached",
            timeout=10000,
        )
        self.page.select_option("#conta_destino", value=str(conta_id))
        self.page.locator("#conta_destino").dispatch_event("change")

    def criar_transferencia(
        self,
        *,
        conta_origem_id: int,
        conta_destino_id: int,
        valor: Decimal,
        descricao: str,
        data: date,
        wait_reload: bool = True,
    ) -> None:
        self.wait_modal_open()
        self.set_tipo("transferencia")
        self.select_conta_origem(conta_origem_id)
        self.select_conta_destino(conta_destino_id)
        self.fill_valor(valor)
        self.fill_descricao(descricao)
        self.fill_data(data)
        self.salvar(wait_reload=wait_reload)

    def expect_erro_formulario(self, trecho: str | None = None) -> None:
        erro = self.page.locator("#erro-conta-ajax")
        expect(erro).to_be_visible()
        expect(erro).not_to_be_empty()
        if trecho:
            expect(erro).to_contain_text(trecho)

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
        categoria_id: int | None = None,
        categoria_nome: str | None = None,
        valor: Decimal,
        descricao: str,
        data: date,
    ) -> None:
        self.wait_modal_open()
        self.set_tipo(tipo)
        if cartao_id:
            self.select_cartao(cartao_id)
        elif conta_id:
            self.select_conta(conta_id)
        # Aguarda opções de categoria (fetch listar-ativas) antes de selecionar —
        # evita submit sem categoria quando popularCategorias ainda está em voo.
        if tipo != "transferencia":
            self.page.wait_for_function(
                """() => {
                    const sel = document.getElementById('categoria');
                    return !!sel && [...sel.options].some((o) => o.value);
                }""",
                timeout=15000,
            )
        if categoria_id is not None:
            self._wait_categoria_option(categoria_id)
            self.select_categoria(categoria_id)
        elif categoria_nome:
            self.select_categoria_by_name(categoria_nome)
        else:
            raise ValueError("Informe categoria_id ou categoria_nome")
        self.fill_valor(valor)
        self.fill_descricao(descricao)
        self.fill_data(data)
        # Revalida categoria imediatamente antes do submit (proteção contra rebuild tardio).
        if categoria_id is not None:
            atual = self.page.locator("#categoria").input_value()
            if atual != str(categoria_id):
                self.select_categoria(categoria_id)
        self.salvar()

    def criar_despesa_conta(
        self,
        *,
        conta_id: int,
        categoria_nome: str,
        valor: Decimal,
        descricao: str,
        data: date,
        aguardar_sugestao: bool = True,
        sobrescrever_sugestao: bool = False,
    ) -> None:
        self.wait_modal_open()
        self.set_tipo("despesa")
        self.select_conta(conta_id)
        self.fill_valor(valor)
        self.fill_descricao(descricao)
        if aguardar_sugestao:
            try:
                self.aguardar_sugestao_categorizacao(timeout_ms=15000)
            except Exception:
                pass
        self.select_categoria_by_name(categoria_nome)
        if sobrescrever_sugestao:
            self.limpar_meta_sugestao()
        self.fill_data(data)
        self.salvar()


class HistoricoPage(BasePage):
    def open(self, ano: int | None = None, mes: int | None = None) -> None:
        path = "/transacoes/"
        if ano and mes:
            path += f"?ano={ano}&mes={mes}"
        self.goto(path)

    def open_nova_despesa(self) -> TransacaoModalPage:
        self.open()
        self.page.click("#btn-adicionar")
        modal = TransacaoModalPage(self.page, self.base_url)
        modal.wait_modal_open()
        modal.set_tipo("despesa")
        return modal

    def open_nova_transferencia(self) -> TransacaoModalPage:
        self.open()
        self.page.click("#btn-adicionar")
        modal = TransacaoModalPage(self.page, self.base_url)
        modal.wait_modal_open()
        modal.set_tipo("transferencia")
        return modal

    def primeira_conta_id(self) -> int:
        return int(
            self.page.evaluate(
                """() => {
                    const sel = document.getElementById('id_conta_cartao');
                    if (!sel) return null;
                    const opt = [...sel.options].find((o) => o.value.startsWith('c:'));
                    return opt ? parseInt(opt.value.slice(2), 10) : null;
                }"""
            )
        )

    def editar_por_id(self, transacao_id: int) -> None:
        self.page.evaluate(
            f"() => window.abrirModalEditarTransacao('{transacao_id}')"
        )
        self.page.wait_for_function(
            "() => !document.getElementById('overlay-adicionar')?.classList.contains('hidden')",
            timeout=15000,
        )

    def excluir_por_id(self, transacao_id: int) -> None:
        # Menu contextual (ListaContextual) — evita depender do botão legado .excluir-transacao
        self.page.evaluate(
            f"() => window.solicitarExclusaoTransacao('{transacao_id}')"
        )
        expect(self.page.locator("#modal-confirmar-exclusao")).to_be_visible()
        with self.page.expect_navigation(timeout=45000, wait_until="load"):
            self.page.click("#confirmar-exclusao")
