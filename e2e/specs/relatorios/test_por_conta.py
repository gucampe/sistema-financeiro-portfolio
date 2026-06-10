"""REL-CTA-UI-* — patrimônio por conta."""

from decimal import Decimal

import pytest

from e2e.fixtures.pages.relatorios_page import FiltrosPortalPage, PorContaPage
from e2e.helpers.relatorio_contracts import verify_conta_movimento, verify_conta_patrimonio


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_cta_ui_01_patrimonio_vs_movimento(logged_in_relatorios_page, app_base_url, persona_relatorios):
    user = persona_relatorios["user"]
    pag = PorContaPage(logged_in_relatorios_page, app_base_url)
    pag.open()
    patrimonio = verify_conta_patrimonio(user, {"preset": "este_mes"})
    assert pag.patrimonio_total() == patrimonio
    assert pag.movimento_periodo() == verify_conta_movimento(user, {"preset": "este_mes"})


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_cta_ui_02_conta_sem_movimento_periodo(logged_in_relatorios_page, app_base_url, persona_relatorios):
    user = persona_relatorios["user"]
    pag = PorContaPage(logged_in_relatorios_page, app_base_url)
    pag.open()
    filtros = FiltrosPortalPage(logged_in_relatorios_page, app_base_url)
    filtros.abrir()
    filtros.selecionar_preset("mes_anterior")
    filtros.desmarcar_todas_contas()
    filtros.marcar_conta(persona_relatorios["conta_b"].id)
    filtros.aplicar()
    assert pag.movimento_periodo() == Decimal("0")
    assert pag.patrimonio_total() == verify_conta_patrimonio(user, {"preset": "mes_anterior"})
