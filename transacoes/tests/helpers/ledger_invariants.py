"""
Invariantes globais do ledger de importação.

Usado por fuzz, property, stress, concorrência e real-world tests.
"""

from __future__ import annotations

from decimal import Decimal

from contas.models import Conta
from financial_contracts.saldo_contracts import calcular_saldo_esperado
from transacoes.models import Transacao
from transacoes.ofx_duplicatas import chave_fingerprint_linha


def snapshot_conta(conta: Conta) -> dict:
    """Estado mínimo reproduzível de uma conta."""
    txs = Transacao.objects.filter(conta=conta, usuario=conta.usuario)
    return {
        "count": txs.count(),
        "saldo": calcular_saldo_esperado(conta),
        "ledger": list(
            txs.order_by("data", "pk").values(
                "data", "valor", "tipo", "descricao", "ofx_fitid", "conta_id"
            )
        ),
    }


def snapshot_usuario(user, *, contas: list[Conta] | None = None) -> dict[int, dict]:
    qs = Conta.objects.filter(usuario=user, ativa=True)
    if contas is not None:
        ids = {c.pk for c in contas}
        qs = qs.filter(pk__in=ids)
    return {c.pk: snapshot_conta(c) for c in qs}


def assert_saldo_consistente(user, *, contas: list[Conta] | None = None) -> None:
    """INVARIANTE 2: saldo == receitas - despesas + ajustes ± transferências."""
    qs = Conta.objects.filter(usuario=user, ativa=True)
    if contas is not None:
        qs = qs.filter(pk__in=[c.pk for c in contas])
    for conta in qs:
        esperado = calcular_saldo_esperado(conta)
        atual = conta.saldo_atual_calc
        assert atual == esperado, (
            f"Saldo inconsistente conta={conta.pk}: "
            f"saldo_atual_calc={atual} calcular_saldo={esperado}"
        )


def assert_sem_duplicatas(user, *, contas: list[Conta] | None = None) -> None:
    """FITID único por conta; fingerprint heurístico único por conta."""
    qs = Conta.objects.filter(usuario=user, ativa=True)
    if contas is not None:
        qs = qs.filter(pk__in=[c.pk for c in contas])
    for conta in qs:
        txs = Transacao.objects.filter(conta=conta, usuario=user)
        fitids = [
            f
            for f in txs.exclude(ofx_fitid__isnull=True)
            .exclude(ofx_fitid="")
            .values_list("ofx_fitid", flat=True)
        ]
        assert len(fitids) == len(set(fitids)), (
            f"FITID duplicado na conta {conta.pk}"
        )
        chaves: set[tuple] = set()
        for t in txs:
            chave = chave_fingerprint_linha(t.data, t.valor, t.descricao)
            assert chave not in chaves, (
                f"Fingerprint duplicado na conta {conta.pk}: {chave}"
            )
            chaves.add(chave)


def assert_integridade_transacoes(user, *, contas: list[Conta] | None = None) -> None:
    """Toda transação tem conta válida e pertence ao usuário."""
    qs = Transacao.objects.filter(usuario=user)
    if contas is not None:
        qs = qs.filter(conta__in=contas)
    for t in qs.iterator(chunk_size=500):
        assert t.conta_id is not None, f"Transação {t.pk} sem conta_id"
        assert t.conta.usuario_id == user.pk, (
            f"Transação {t.pk} com conta de outro usuário"
        )
        assert t.valor >= 0, f"Transação {t.pk} com valor negativo armazenado"
        assert t.descricao.strip(), f"Transação {t.pk} sem descrição"


def assert_isolamento_contas(
    user,
    conta_alvo: Conta,
    contas_isoladas: list[Conta],
    snapshot_antes: dict[int, dict],
) -> None:
    """INVARIANTE 3: import em conta_alvo não altera contas isoladas."""
    for conta in contas_isoladas:
        if conta.pk == conta_alvo.pk:
            continue
        antes = snapshot_antes[conta.pk]
        depois = snapshot_conta(conta)
        assert depois["count"] == antes["count"], (
            f"Conta {conta.pk} teve count alterado por import em {conta_alvo.pk}"
        )
        assert depois["saldo"] == antes["saldo"], (
            f"Conta {conta.pk} teve saldo alterado por import em {conta_alvo.pk}"
        )
        assert depois["ledger"] == antes["ledger"], (
            f"Conta {conta.pk} teve ledger alterado por import em {conta_alvo.pk}"
        )


def assert_ledger_invariants(user, *, contas: list[Conta] | None = None) -> None:
    """Executa todos os invariantes globais."""
    assert_saldo_consistente(user, contas=contas)
    assert_sem_duplicatas(user, contas=contas)
    assert_integridade_transacoes(user, contas=contas)
