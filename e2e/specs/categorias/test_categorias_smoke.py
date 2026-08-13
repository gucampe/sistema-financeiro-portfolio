"""E2E smoke — CRUD mínimo de categorias (criar despesa → arquivar)."""

import pytest
from playwright.sync_api import expect

from e2e.fixtures.pages.categorias_page import CategoriasPage


@pytest.mark.cadastro_smoke
@pytest.mark.django_db(transaction=True)
def test_categorias_criar_despesa_arquivar(logged_in_page, app_base_url):
    page = logged_in_page
    cats = CategoriasPage(page, app_base_url)
    cats.open()
    nome = "Categoria Smoke E2E"
    cats.criar_despesa(nome)
    expect(cats.item_ativa(nome)).to_be_visible()
    cats.arquivar(nome)
    expect(cats.item_ativa(nome)).to_have_count(0)
