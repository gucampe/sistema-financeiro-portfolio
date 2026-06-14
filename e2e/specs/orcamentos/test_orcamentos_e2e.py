"""ORC-* — planejamento orçamentário."""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from playwright.sync_api import expect

from relatorios.models import OrcamentoCategoria
from relatorios.services.filtros import RelatorioFiltros
from relatorios.services.orcamentos import listar_orcamentos_mes
from financial_contracts.orcamento_contracts import assert_pagamento_excluido_do_realizado


@pytest.mark.orcamentos
@pytest.mark.django_db(transaction=True)
def test_orc_01_criar_orcamento_via_api(persona_basic):
    user = persona_basic["user"]
    cat = persona_basic["cat_despesa"]
    hoje = timezone.localdate()
    OrcamentoCategoria.objects.create(
        usuario=user,
        categoria=cat,
        valor_planejado=Decimal("300.00"),
        ativo=True,
    )
    linhas = listar_orcamentos_mes(user, hoje.year, hoje.month)
    alvo = next((l for l in linhas if l.categoria_id == cat.id), None)
    assert alvo is not None
    assert alvo.planejado == Decimal("300.00")


@pytest.mark.orcamentos
@pytest.mark.django_db(transaction=True)
def test_orc_06_pagamento_fatura_excluido_realizado(persona_card):
    user = persona_card["user"]
    cat = persona_card["cat_despesa"]
    hoje = timezone.localdate()
    filtros = RelatorioFiltros(
        data_inicio=date(hoje.year, hoje.month, 1),
        data_fim=hoje,
        preset="custom",
    )
    assert_pagamento_excluido_do_realizado(user, cat, filtros)


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.django_db(transaction=True)
def test_orc_02_tela_orcamentos_carrega(logged_in_orcamentos_page, app_base_url):
    page = logged_in_orcamentos_page
    page.goto(f"{app_base_url}/relatorios/orcamentos/")
    expect(page.locator("#orcamentos-root")).to_be_visible()
    expect(page.get_by_role("heading", name="Por categoria")).to_be_visible()
