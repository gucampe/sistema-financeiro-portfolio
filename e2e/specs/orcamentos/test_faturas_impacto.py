"""ORC-FAT-E* — impacto de compras cartão e pagamentos de fatura."""

from decimal import Decimal

import pytest

from e2e.fixtures.pages.orcamentos_page import OrcamentosPage
from e2e.helpers.orcamento_contracts import verify_linha_categoria
from financial_contracts.orcamento_contracts import assert_pagamento_excluido_do_realizado
from relatorios.services.filtros import RelatorioFiltros
from django.utils import timezone


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.orcamentos_faturas
@pytest.mark.django_db(transaction=True)
def test_orc_fat_e01_compra_cartao_entra_realizado(logged_in_orcamentos_page, app_base_url, persona_orcamentos):
    user = persona_orcamentos["user"]
    # Moradia: 400 conta + 50 cartão = 450 (pagamento 999 excluído)
    verify_linha_categoria(user, "Orc Moradia", realizado=Decimal("450.00"))
    pag = OrcamentosPage(logged_in_orcamentos_page, app_base_url)
    pag.open()
    card = pag.card_categoria("Orc Moradia")
    assert "450" in card.inner_text().replace(".", "") or "R$ 450" in card.inner_text()


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.orcamentos_faturas
@pytest.mark.django_db(transaction=True)
def test_orc_fat_e02_pagamento_fatura_excluido(persona_orcamentos):
    user = persona_orcamentos["user"]
    cat = persona_orcamentos["cat_moradia"]
    hoje = timezone.localdate()
    filtros = RelatorioFiltros(
        data_inicio=hoje.replace(day=1),
        data_fim=hoje,
        preset="custom",
    )
    assert_pagamento_excluido_do_realizado(user, cat, filtros)
    verify_linha_categoria(user, "Orc Moradia", realizado=Decimal("450.00"))
