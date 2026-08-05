#!/usr/bin/env python3
"""Script temporário de captura de assets — docs/hero_ai_assets (não é código de produto)."""
from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent
LANDING = BASE / "02_landing"
APP = BASE / "03_app"
COMP = BASE / "04_components"
URL = "http://127.0.0.1:8000"
EMAIL = "hero-assets@e2e.granago.test"
PASSWORD = "e2e-pass-123"


def shot(page, path: Path, full_page: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=full_page, type="png")
    print(f"OK {path.relative_to(BASE)}")


def clip_locator(locator, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    locator.screenshot(path=str(path), type="png")
    print(f"OK {path.relative_to(BASE)}")


FORCE_VISIBLE_JS = """
document.querySelectorAll('.lp-reveal').forEach(el => {
  el.classList.add('is-visible');
  el.style.opacity = '1';
  el.style.transform = 'none';
  el.style.visibility = 'visible';
});
document.querySelectorAll('[data-hero-visual], .lp-hero-visual').forEach(el => {
  el.classList.add('is-visible', 'is-ready');
});
"""


def wait_ready(page) -> None:
    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception:
        pass
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    # Cookie banner polui screenshots de marketing
    try:
        btn = page.locator("#cookie-consent-accept, button:has-text('Entendi')").first
        if btn.count() and btn.is_visible():
            btn.click(timeout=2000)
            time.sleep(0.3)
    except Exception:
        pass
    try:
        page.evaluate(FORCE_VISIBLE_JS)
    except Exception:
        pass
    time.sleep(0.4)


def capture_landing(page) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(f"{URL}/", wait_until="domcontentloaded")
    wait_ready(page)

    shot(page, LANDING / "01-home-full.png", full_page=True)

    hero = page.locator("#hero")
    if hero.count():
        clip_locator(hero, LANDING / "02-hero.png")
    else:
        shot(page, LANDING / "02-hero.png")

    programa = page.locator("#programa")
    if programa.count():
        clip_locator(programa, LANDING / "03-programa.png")

    btn = page.locator(
        "[data-captura-open], .js-open-captura, a[href='#captura'], button:has-text('Quero meu acesso')"
    ).first
    if btn.count():
        btn.click()
        time.sleep(0.6)
    dialog = page.locator("#modal-captura, .lp-modal, [role='dialog']").first
    if dialog.count() and dialog.is_visible():
        clip_locator(dialog, LANDING / "04-formulario.png")
    else:
        shot(page, LANDING / "04-formulario.png")

    page.keyboard.press("Escape")
    time.sleep(0.3)

    footer = page.locator("footer").first
    if footer.count():
        clip_locator(footer, LANDING / "05-footer.png")

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{URL}/", wait_until="domcontentloaded")
    wait_ready(page)
    shot(page, LANDING / "01-home-mobile.png", full_page=True)


def login(page) -> bool:
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(f"{URL}/login/", wait_until="domcontentloaded")
    wait_ready(page)
    page.fill("#email", EMAIL)
    page.fill("#senha", PASSWORD)
    page.click('button[type="submit"]')
    try:
        page.wait_for_url("**/relatorios/**", timeout=20000)
        return True
    except Exception as exc:
        print(f"LOGIN_FAIL: {exc}")
        # fallback: any authenticated shell
        if "/login" not in page.url:
            return True
        shot(page, APP / "_login_failed.png", full_page=True)
        return False


def capture_app(page) -> None:
    routes = [
        ("01-dashboard.png", "/relatorios/"),
        ("09-importacao-ofx.png", None),  # handled specially below
        ("02-transacoes.png", "/transacoes/"),
        ("03-categorias.png", "/categorias/"),
        ("04-relatorios.png", "/relatorios/fluxo-caixa/"),
        ("05-contas.png", "/contas/"),
        ("06-cartoes.png", "/cartoes/"),
        ("07-orcamentos.png", "/relatorios/orcamentos/"),
        ("08-configuracoes.png", "/configuracoes/"),
    ]
    for name, path in routes:
        if path is None:
            continue
        page.goto(f"{URL}{path}", wait_until="domcontentloaded")
        wait_ready(page)
        shot(page, APP / name, full_page=True)

    page.goto(f"{URL}/transacoes/", wait_until="domcontentloaded")
    wait_ready(page)
    ofx_btn = page.locator("#btn-importar-ofx")
    if ofx_btn.count():
        ofx_btn.click()
        time.sleep(0.8)
        ofx_modal = page.locator("#modal-importar-ofx").first
        if ofx_modal.count() and ofx_modal.is_visible():
            clip_locator(ofx_modal, APP / "09-importacao-ofx.png")
        else:
            visible = page.locator(".modal.show, [role='dialog']:visible").first
            if visible.count():
                clip_locator(visible, APP / "09-importacao-ofx.png")
            else:
                shot(page, APP / "09-importacao-ofx.png", full_page=True)
    else:
        shot(page, APP / "09-importacao-ofx.png", full_page=True)


def capture_components(page) -> None:
    page.goto(f"{URL}/relatorios/", wait_until="domcontentloaded")
    wait_ready(page)

    sidebar = page.locator("#sidebar").first
    if sidebar.count():
        clip_locator(sidebar, COMP / "sidebar.png")

    header = page.locator("header").first
    if header.count():
        clip_locator(header, COMP / "header.png")

    # KPI / cards area — first grid under main
    main = page.locator("main").first
    if main.count():
        grids = main.locator("div.grid")
        if grids.count() >= 1:
            clip_locator(grids.nth(0), COMP / "cards.png")
        chart_card = page.locator("canvas").first
        if chart_card.count():
            parent = chart_card.locator(
                "xpath=ancestor::div[contains(@class,'rounded') or contains(@class,'card') or contains(@class,'bg-white')][1]"
            )
            if parent.count():
                clip_locator(parent, COMP / "graphs.png")
            else:
                clip_locator(chart_card, COMP / "graphs.png")

    page.goto(f"{URL}/transacoes/", wait_until="domcontentloaded")
    wait_ready(page)

    # Action buttons strip near top of main
    actions = page.locator("main a.btn, main button.btn, main .btn").first
    if actions.count():
        row = page.locator("main").locator("div.flex").filter(has=page.locator(".btn, a.btn, button.btn")).first
        if row.count():
            clip_locator(row, COMP / "buttons.png")
        else:
            clip_locator(actions, COMP / "buttons.png")

    formish = page.locator("main form, main [class*='filter']").first
    if formish.count():
        clip_locator(formish, COMP / "inputs.png")
    else:
        inp = page.locator("input:visible, select:visible").first
        if inp.count():
            clip_locator(inp, COMP / "inputs.png")

    badge = page.locator("[class*='badge'], .chip, [class*='chip'], .tag").first
    if badge.count():
        clip_locator(badge, COMP / "badges.png")
        clip_locator(badge, COMP / "chips.png")

    page.goto(f"{URL}/categorias/", wait_until="domcontentloaded")
    wait_ready(page)
    cat = page.locator("main li, main [class*='badge'], main [style*='background']").first
    if cat.count():
        if not (COMP / "chips.png").exists():
            clip_locator(cat, COMP / "chips.png")
        if not (COMP / "badges.png").exists():
            clip_locator(cat, COMP / "badges.png")

    page.goto(f"{URL}/transacoes/", wait_until="domcontentloaded")
    wait_ready(page)
    ofx_btn = page.locator("#btn-importar-ofx")
    if ofx_btn.count():
        ofx_btn.click()
        time.sleep(0.7)
        modal = page.locator("#modal-importar-ofx, .modal.show, [role='dialog']:visible").first
        if modal.count() and modal.is_visible():
            clip_locator(modal, COMP / "modals.png")
        else:
            shot(page, COMP / "modals.png")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            device_scale_factor=2,
            locale="pt-BR",
            color_scheme="light",
        )
        page = context.new_page()
        page.set_default_timeout(20000)

        print("=== LANDING ===")
        capture_landing(page)

        print("=== APP ===")
        if login(page):
            capture_app(page)
            print("=== COMPONENTS ===")
            capture_components(page)
        else:
            print("App screenshots skipped — login failed")

        browser.close()
    print("DONE")


if __name__ == "__main__":
    main()
