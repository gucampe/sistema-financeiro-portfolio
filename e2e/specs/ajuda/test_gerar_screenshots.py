"""Gera os PNGs da Ajuda em static/img/ajuda/.

Uso:
  source .venv/bin/activate
  python -m pytest e2e/specs/ajuda/test_gerar_screenshots.py --browser chromium -s
"""

from __future__ import annotations

import pytest

from e2e.factories.ajuda_demo import AJUDA_DEMO_PASSWORD, seed_ajuda_demo
from e2e.fixtures.pages.login_page import LoginPage
from e2e.helpers.ajuda_screenshots import (
    capturar_categoria,
    capturar_importacao,
    capturar_transacao,
)


@pytest.fixture
def browser_context_args(browser_context_args):
    return {**browser_context_args, "device_scale_factor": 2}


@pytest.fixture
def ajuda_demo(db):
    return seed_ajuda_demo()


@pytest.mark.ajuda_screenshots
@pytest.mark.django_db(transaction=True)
def test_gerar_screenshots_ajuda(page, app_base_url, ajuda_demo):
    page.set_viewport_size({"width": 880, "height": 920})
    login = LoginPage(page, app_base_url)
    login.login(ajuda_demo["user"].email, AJUDA_DEMO_PASSWORD)
    login.expect_redirect_dashboard()

    transacao = capturar_transacao(
        page,
        app_base_url,
        conta_id=ajuda_demo["conta"].pk,
        categoria_id=ajuda_demo["categorias"]["mercado"].pk,
    )
    importacao = capturar_importacao(page, app_base_url, conta_id=ajuda_demo["conta"].pk)
    categoria = capturar_categoria(
        page,
        app_base_url,
        transacao_id=ajuda_demo["transacao_mercado"].pk,
    )

    for caminho in (transacao, importacao, categoria):
        assert caminho.exists(), caminho
        assert caminho.stat().st_size > 1000, caminho
