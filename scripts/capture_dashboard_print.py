"""
Captura o print da Visão Geral em qualidade máxima (PNG @ 2x), sem recortar.

Importante: janela vs tela cheia NÃO muda o tamanho dos elementos.
O que muda é o viewport CSS e o recorte (com/sem sidebar).

Uso (servidor em http://127.0.0.1:8000):

  .\\.venv\\Scripts\\activate
  python scripts/capture_dashboard_print.py
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "img" / "landing" / "print2.png"
BASE_URL = "http://127.0.0.1:8000"
DASHBOARD_URL = f"{BASE_URL}/relatorios/?preset=ultimos_90d"

# Largura CSS do conteúdo. @2x → ~2560 px físicas (nítido em 2K).
# Um pouco mais estreito = cards maiores na proporção do frame.
VIEWPORT_WIDTH = 1200
DEVICE_SCALE_FACTOR = 2
MAX_CAPTURE_HEIGHT = 3600  # proteção contra página enorme


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": 900},
            device_scale_factor=DEVICE_SCALE_FACTOR,
            locale="pt-BR",
        )
        page = context.new_page()
        page.goto(DASHBOARD_URL, wait_until="domcontentloaded")

        print()
        print("Chromium aberto para captura de marketing.")
        print(f"Largura {VIEWPORT_WIDTH}px @ {DEVICE_SCALE_FACTOR}x (sem zoom — evita recorte)")
        print("1) Faça login se precisar")
        print("2) Ajuste filtros / período na Visão Geral")
        print("3) Volte aqui e pressione Enter")
        print()
        input("Pronto para capturar? Enter… ")

        # Prepara a página: sem sidebar, overflow liberado, altura real do conteúdo
        size = page.evaluate(
            """() => {
              const sidebar = document.getElementById('sidebar');
              if (sidebar) sidebar.style.setProperty('display', 'none', 'important');

              for (const sel of ['html', 'body', '#mainContent', '.app-shell__body']) {
                const el = document.querySelector(sel);
                if (!el) continue;
                el.style.setProperty('overflow', 'visible', 'important');
                el.style.setProperty('height', 'auto', 'important');
                el.style.setProperty('max-height', 'none', 'important');
              }

              const body = document.getElementById('mainContent');
              if (body) {
                body.style.setProperty('margin-left', '0', 'important');
                body.style.setProperty('width', '100%', 'important');
              }

              const target = body || document.body;
              return {
                width: Math.ceil(Math.max(target.scrollWidth, target.getBoundingClientRect().width)),
                height: Math.ceil(Math.max(target.scrollHeight, target.getBoundingClientRect().height)),
              };
            }"""
        )

        capture_h = min(int(size["height"]) + 24, MAX_CAPTURE_HEIGHT)
        capture_w = max(int(size["width"]), VIEWPORT_WIDTH)
        page.set_viewport_size({"width": capture_w, "height": capture_h})
        page.wait_for_timeout(500)

        target = page.locator("#mainContent").first
        if target.count() == 0:
            page.screenshot(path=str(OUT), type="png", full_page=True)
        else:
            # full_page no elemento via bounding box expandido
            target.screenshot(path=str(OUT), type="png")

        browser.close()

    from PIL import Image

    im = Image.open(OUT)
    print(f"Salvo: {OUT}")
    print(f"Tamanho: {im.size[0]}×{im.size[1]}  |  {OUT.stat().st_size // 1024} KB  |  {im.format}")


if __name__ == "__main__":
    main()
