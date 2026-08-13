"""E2E smoke — CRUD mínimo de contas (criar → listar → arquivar)."""

import pytest
from playwright.sync_api import expect

from e2e.fixtures.pages.contas_page import ContasPage


@pytest.mark.cadastro_smoke
@pytest.mark.django_db(transaction=True)
def test_contas_criar_listar_arquivar(logged_in_page, app_base_url):
    page = logged_in_page
    contas = ContasPage(page, app_base_url)
    contas.open()
    nome = "Conta Smoke E2E"
    contas.criar_conta(nome)
    expect(contas.item_ativa(nome)).to_be_visible()
    contas.arquivar(nome)
    expect(contas.item_arquivada(nome)).to_be_visible()
