"""Captura determinística dos screenshots da Ajuda."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from playwright.sync_api import Page, expect

from e2e.fixtures.pages.import_pages import ImportOfxPage
from e2e.fixtures.pages.transacoes_page import HistoricoPage, TransacaoModalPage

ROOT = Path(__file__).resolve().parents[2]
AJUDA_IMG_DIR = ROOT / "static" / "img" / "ajuda"

HIDE_CHROME_JS = """
() => {
  const hide = (sel) => {
    document.querySelectorAll(sel).forEach((el) => {
      el.style.setProperty('display', 'none', 'important');
      el.setAttribute('hidden', '');
    });
  };
  hide('#cookie-consent-banner');
  hide('.app-toast-root');
  hide('#ajuda-overlay');
  hide('a[href*="primeiros-passos"]');
  hide('a[href*="primeiros_passos"]');
}
"""

HIGHLIGHT_CATEGORIA_JS = """
() => {
  const bloco = document.getElementById('bloco-categoria');
  if (!bloco) return false;
  bloco.style.outline = '2px solid #22c55e';
  bloco.style.outlineOffset = '4px';
  bloco.style.borderRadius = '12px';
  bloco.scrollIntoView({ block: 'center', inline: 'nearest' });
  return true;
}
"""


def preparar_pagina(page: Page) -> None:
    page.evaluate(HIDE_CHROME_JS)
    page.evaluate(
        """() => {
          if (document.activeElement && document.activeElement.blur) {
            document.activeElement.blur();
          }
          document.querySelectorAll('[data-modal-panel], .modal-panel').forEach((el) => {
            el.style.setProperty('transform', 'none', 'important');
            el.style.setProperty('transition', 'none', 'important');
          });
        }"""
    )
    try:
        page.evaluate("() => document.fonts && document.fonts.ready")
    except Exception:
        pass
    page.wait_for_timeout(250)


def _capturar(page: Page, seletor: str, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    box = page.locator(seletor).bounding_box()
    if not box:
        raise RuntimeError(f"Não foi possível medir {seletor} para o screenshot.")
    pad = 4
    page.screenshot(
        path=str(destino),
        type="png",
        animations="disabled",
        clip={
            "x": max(0, box["x"] - pad),
            "y": max(0, box["y"] - pad),
            "width": box["width"] + pad * 2,
            "height": box["height"] + pad * 2,
        },
    )


def capturar_transacao(page: Page, base_url: str, *, conta_id: int, categoria_id: int) -> Path:
    destino = AJUDA_IMG_DIR / "transacao.png"
    page.goto(f"{base_url}/transacoes/?nova=1", wait_until="domcontentloaded")
    modal = TransacaoModalPage(page, base_url)
    modal.wait_modal_open()
    modal.set_tipo("despesa")
    modal.select_conta(conta_id)
    modal.fill_descricao("Mercado")
    modal.select_categoria(categoria_id)
    modal.fill_valor(Decimal("350.00"))
    modal.fill_data(date.today())
    expect(page.locator("#overlay-adicionar [data-modal-panel]")).to_be_visible()
    page.wait_for_timeout(350)
    preparar_pagina(page)
    _capturar(page, "#overlay-adicionar [data-modal-panel]", destino)
    return destino


def capturar_importacao(page: Page, base_url: str, *, conta_id: int) -> Path:
    destino = AJUDA_IMG_DIR / "importacao.png"
    importacao = ImportOfxPage(page, base_url)
    importacao.abrir()
    importacao.selecionar_conta(conta_id)
    expect(page.locator("#import-ofx-panel")).to_be_visible()
    page.wait_for_timeout(350)
    preparar_pagina(page)
    _capturar(page, "#import-ofx-panel", destino)
    return destino


def capturar_categoria(page: Page, base_url: str, *, transacao_id: int) -> Path:
    destino = AJUDA_IMG_DIR / "categoria.png"
    historico = HistoricoPage(page, base_url)
    historico.open()
    historico.editar_por_id(transacao_id)
    expect(page.locator("#overlay-adicionar [data-modal-panel]")).to_be_visible()
    page.wait_for_function(
        """() => {
            const sel = document.getElementById('categoria');
            return !!sel && !!sel.value;
        }""",
        timeout=15000,
    )
    highlighted = page.evaluate(HIGHLIGHT_CATEGORIA_JS)
    if not highlighted:
        raise RuntimeError("Campo de categoria não encontrado para o screenshot.")
    page.wait_for_timeout(200)
    preparar_pagina(page)
    page.evaluate(HIGHLIGHT_CATEGORIA_JS)
    _capturar(page, "#overlay-adicionar [data-modal-panel]", destino)
    return destino
