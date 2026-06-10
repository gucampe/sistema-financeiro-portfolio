"""TZ-* — timezone e competência (unit/integration via pytest-django)."""

from datetime import date, datetime, timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from cartoes.services.faturas import obter_ou_criar_fatura
from financial_contracts.competencia_contracts import (
    assert_competencia_cartao_vencimento,
    assert_data_competencia_em_fatura,
)
from transacoes.models import Transacao


@pytest.mark.timezone
@pytest.mark.django_db(transaction=True)
def test_tz_01_compra_ultimo_dia_mes(persona_card):
    user = persona_card["user"]
    conta = persona_card["conta"]
    cartao = persona_card["cartao"]
    cat = persona_card["cat_despesa"]

    with freeze_time("2026-05-31 23:59:00", tz_offset=-3):
        tx = Transacao.objects.create(
            usuario=user,
            conta=conta,
            cartao=cartao,
            categoria=cat,
            tipo="despesa",
            valor="50.00",
            data=timezone.localdate(),
            descricao="TZ-01",
        )
    tx.refresh_from_db()
    assert_data_competencia_em_fatura(tx)
    assert_competencia_cartao_vencimento(tx.fatura)


@pytest.mark.timezone
@pytest.mark.django_db(transaction=True)
def test_tz_04_virada_ano(persona_basic):
    user = persona_basic["user"]
    conta = persona_basic["conta"]
    cat = persona_basic["cat_receita"]

    with freeze_time("2026-01-15 12:00:00", tz_offset=-3):
        tx = Transacao.objects.create(
            usuario=user,
            conta=conta,
            categoria=cat,
            tipo="receita",
            valor="100.00",
            data=date(2026, 1, 15),
            descricao="TZ-04",
        )
    assert tx.data.year == 2026
