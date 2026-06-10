"""MU-* — placeholders multi-usuário (futuro)."""

import pytest

from e2e.factories.personas import seed_persona_basic


@pytest.mark.multi_user
@pytest.mark.skip(reason="multi-user not implemented")
def test_mu_01_invited_cria_despesa():
    seed_persona_basic()


@pytest.mark.multi_user
@pytest.mark.skip(reason="multi-user not implemented")
def test_mu_04_auditoria_pagamento_fatura():
    pass
