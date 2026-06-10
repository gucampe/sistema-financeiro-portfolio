"""MIG-* — integridade após migrations."""

import pytest
from django.core.management import call_command
from django.db import connection

from e2e.factories.personas import seed_persona_basic
from financial_contracts.saldo_contracts import assert_saldo_conta


@pytest.mark.migration
@pytest.mark.django_db(transaction=True)
def test_mig_01_migrate_e_contratos_saldo():
    call_command("migrate", verbosity=0, interactive=False)
    data = seed_persona_basic(f"mig-{connection.settings_dict['NAME']}@e2e.test")
    conta = data["conta"]
    assert_saldo_conta(conta, conta.saldo_atual_calc)


@pytest.mark.migration
@pytest.mark.django_db(transaction=True)
def test_mig_03_dados_historicos_validos(persona_basic):
    conta = persona_basic["conta"]
    saldo = conta.saldo_atual_calc
    assert saldo is not None
