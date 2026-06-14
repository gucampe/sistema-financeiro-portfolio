"""ORC-REC-E*, ORC-VIG-E* — recorrência e vigência."""

from decimal import Decimal

import pytest
from playwright.sync_api import expect

from e2e.fixtures.pages.orcamentos_page import ModalOrcamentoPage, OrcamentosPage
from e2e.helpers.orcamento_contracts import verify_linha_categoria, verify_painel_mes
from relatorios.models import OrcamentoCategoria


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.django_db(transaction=True)
def test_orc_rec_e01_card_mostra_planejado(logged_in_orcamentos_page, app_base_url, persona_orcamentos):
    user = persona_orcamentos["user"]
    pag = OrcamentosPage(logged_in_orcamentos_page, app_base_url)
    pag.open()
    verify_linha_categoria(user, "Orc Moradia", planejado=Decimal("1000.00"))
    card = pag.card_categoria("Orc Moradia")
    expect(card).to_contain_text("R$ 1.000")


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.django_db(transaction=True)
def test_orc_vig_e01_futuro_nao_listado_mes_atual(logged_in_orcamentos_page, app_base_url, persona_orcamentos):
    from e2e.helpers.orcamento_contracts import linha_por_nome

    user = persona_orcamentos["user"]
    assert linha_por_nome(user, "Orc Futuro") is None
    pag = OrcamentosPage(logged_in_orcamentos_page, app_base_url)
    pag.open()
    expect(pag.card_categoria("Orc Futuro")).to_have_count(0)


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.django_db(transaction=True)
def test_orc_vig_e02_criar_orcamento_modal(logged_in_orcamentos_page, app_base_url, persona_orcamentos):
    user = persona_orcamentos["user"]
    cat = persona_orcamentos["cat_futuro"]
    OrcamentoCategoria.objects.filter(usuario=user, categoria=cat).delete()

    pag = OrcamentosPage(logged_in_orcamentos_page, app_base_url)
    pag.open()
    pag.abrir_novo_orcamento()
    modal = ModalOrcamentoPage(logged_in_orcamentos_page, app_base_url)
    modal.wait_open()
    modal.selecionar_categoria(cat.id)
    modal.preencher_valor(Decimal("350.00"))
    modal.salvar()
    verify_linha_categoria(user, "Orc Futuro", planejado=Decimal("350.00"))


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.django_db(transaction=True)
def test_orc_vig_e03_pausar_orcamento(logged_in_orcamentos_page, app_base_url, persona_orcamentos):
    from e2e.helpers.orcamento_contracts import linha_por_nome

    user = persona_orcamentos["user"]
    orc = OrcamentoCategoria.objects.get(
        usuario=user, categoria=persona_orcamentos["cat_transporte"]
    )
    pag = OrcamentosPage(logged_in_orcamentos_page, app_base_url)
    pag.open()
    modal = ModalOrcamentoPage(logged_in_orcamentos_page, app_base_url)
    modal.pausar_orcamento(orc.id)
    orc.refresh_from_db()
    assert orc.ativo is False
    linha = linha_por_nome(user, "Orc Transporte")
    assert linha is not None
    assert linha.ativo is False
    assert linha.planejado == Decimal("0")
    pag.open()
    card = pag.card_categoria("Orc Transporte")
    expect(card).to_have_count(1)
    expect(card).to_contain_text("Pausado")
    expect(card.get_by_role("button", name="Reativar")).to_be_visible()
