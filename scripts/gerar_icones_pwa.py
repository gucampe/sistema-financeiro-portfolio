"""Gera ícones PWA a partir de static/img/icons/logo.svg (sem alterar o SVG).

Data de criação: 2026-09-15
Uso (na raiz, com .venv): python scripts/gerar_icones_pwa.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = ROOT / "static" / "img" / "icons" / "logo.svg"
OUT_DIR = ROOT / "static" / "img" / "icons" / "pwa"
BRAND_BG = (244, 245, 247, 255)  # #f4f5f7 — o logo já é verde; fundo da marca, não do símbolo
RENDER = 1024


def _render_logo_png() -> Image.Image:
    svg = SVG_PATH.read_text(encoding="utf-8")
    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{
    margin: 0;
    padding: 0;
    width: {RENDER}px;
    height: {RENDER}px;
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  svg {{ width: 92%; height: 92%; }}
</style>
</head>
<body>{svg}</body>
</html>"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": RENDER, "height": RENDER},
            device_scale_factor=1,
        )
        page.set_content(html, wait_until="load")
        png = page.screenshot(omit_background=True, type="png")
        browser.close()
    from io import BytesIO

    img = Image.open(BytesIO(png)).convert("RGBA")
    return img


def _fit(src: Image.Image, canvas: int, fill_ratio: float) -> Image.Image:
    box = max(1, int(canvas * fill_ratio))
    fitted = src.copy()
    fitted.thumbnail((box, box), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    x = (canvas - fitted.width) // 2
    y = (canvas - fitted.height) // 2
    out.paste(fitted, (x, y), fitted)
    return out


def _maskable(src: Image.Image, canvas: int) -> Image.Image:
    # Zona segura maskable ≈ círculo central de 80% do lado.
    out = Image.new("RGBA", (canvas, canvas), BRAND_BG)
    logo = _fit(src, canvas, 0.62)
    out.alpha_composite(logo)
    return out.convert("RGB")


def main() -> None:
    if not SVG_PATH.is_file():
        raise SystemExit(f"SVG não encontrado: {SVG_PATH}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    logo = _render_logo_png()

    _fit(logo, 192, 0.92).save(OUT_DIR / "icon-192.png", "PNG")
    _fit(logo, 512, 0.92).save(OUT_DIR / "icon-512.png", "PNG")
    _maskable(logo, 192).save(OUT_DIR / "icon-192-maskable.png", "PNG")
    _maskable(logo, 512).save(OUT_DIR / "icon-512-maskable.png", "PNG")
    _maskable(logo, 180).save(OUT_DIR / "apple-touch-icon.png", "PNG")
    print(f"Ícones gravados em {OUT_DIR}")


if __name__ == "__main__":
    main()
