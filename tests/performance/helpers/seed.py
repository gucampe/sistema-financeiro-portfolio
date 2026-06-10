"""
Seeds pequenos e controlados para testes de performance (PR ≤ 50 itens).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from cartoes.models import Cartao
from cartoes.services.faturas import obter_ou_criar_fatura
from categorias.models import Categoria
from contas.models import Conta
from transacoes.models import Transacao
from transacoes.services import criar_transacao_saldo_inicial

User = get_user_model()

_PERF_PASSWORD = "perf-test-x"


def _hoje() -> date:
    return timezone.localdate()


def seed_perf_user(email: str = "perf@test.local") -> dict:
    """Usuário base com conta e categorias padrão."""
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"nome": "Perf Test", "is_active": True},
    )
    if created:
        user.set_password(_PERF_PASSWORD)
        user.save()

    conta, _ = Conta.objects.get_or_create(
        usuario=user,
        nome="Conta Perf",
        defaults={"tipo": "corrente", "ativa": True},
    )
    if created or not Transacao.objects.filter(conta=conta, tipo="ajuste").exists():
        criar_transacao_saldo_inicial(user, conta, Decimal("5000.00"), _hoje().replace(day=1))

    cat_desp, _ = Categoria.objects.get_or_create(
        usuario=user,
        nome="Perf Despesa Base",
        defaults={"tipo": "despesa", "ativa": True, "cor": "#EF4444"},
    )
    cat_rec, _ = Categoria.objects.get_or_create(
        usuario=user,
        nome="Perf Receita Base",
        defaults={"tipo": "receita", "ativa": True, "cor": "#10B981"},
    )

    return {
        "user": user,
        "conta": conta,
        "cat_desp": cat_desp,
        "cat_rec": cat_rec,
    }


def seed_cartoes_dashboard(user, conta, cat_desp, *, n_cartoes: int = 5) -> int:
    """N cartões ativos com compra no mês — hotspot resumo_cartoes_dashboard."""
    hoje = _hoje()
    for i in range(n_cartoes):
        cartao, _ = Cartao.objects.get_or_create(
            usuario=user,
            nome=f"Cartão Perf {i + 1}",
            defaults={
                "dia_fechamento": 5,
                "dia_vencimento": 12,
                "conta_padrao": conta,
                "ativa": True,
                "limite": Decimal("3000.00"),
            },
        )
        fatura = obter_ou_criar_fatura(cartao, hoje)
        if not Transacao.objects.filter(
            usuario=user, cartao=cartao, descricao=f"Perf compra cartão {i + 1}"
        ).exists():
            Transacao.objects.create(
                usuario=user,
                conta=conta,
                cartao=cartao,
                fatura=fatura,
                categoria=cat_desp,
                tipo="despesa",
                valor=Decimal(f"{(i + 1) * 10}.00"),
                data=hoje.replace(day=min(10 + i, 28)),
                descricao=f"Perf compra cartão {i + 1}",
            )
    return n_cartoes


def seed_categorias_despesa(user, conta, *, n_categorias: int = 8) -> tuple[list[Categoria], int]:
    """N categorias com despesas no mês — hotspot despesas-por-categoria."""
    hoje = _hoje()
    cats: list[Categoria] = []
    for i in range(n_categorias):
        cat, _ = Categoria.objects.get_or_create(
            usuario=user,
            nome=f"Perf Cat {i + 1}",
            defaults={"tipo": "despesa", "ativa": True, "cor": "#6366F1"},
        )
        cats.append(cat)
        if not Transacao.objects.filter(usuario=user, categoria=cat, descricao=f"Perf cat {i + 1}").exists():
            Transacao.objects.create(
                usuario=user,
                conta=conta,
                categoria=cat,
                tipo="despesa",
                valor=Decimal(f"{(i + 1) * 25}.00"),
                data=hoje.replace(day=min(5 + i, 28)),
                descricao=f"Perf cat {i + 1}",
            )
    return cats, n_categorias


def seed_transacoes_mes(user, conta, cat_desp, cat_rec, *, n: int = 12) -> int:
    """N transações no mês corrente — hotspot /transacoes/."""
    hoje = _hoje()
    for i in range(n):
        desc = f"Perf tx {i + 1}"
        if Transacao.objects.filter(usuario=user, descricao=desc).exists():
            continue
        cat = cat_rec if i % 3 == 0 else cat_desp
        tipo = "receita" if i % 3 == 0 else "despesa"
        Transacao.objects.create(
            usuario=user,
            conta=conta,
            categoria=cat,
            tipo=tipo,
            valor=Decimal(f"{(i + 1) * 5}.00"),
            data=hoje.replace(day=min(1 + (i % 27), 28)),
            descricao=desc,
        )
    return n


def seed_transacoes_periodo(
    user,
    conta,
    cat_desp,
    *,
    dias: int = 90,
    por_dia: int = 1,
) -> int:
    """Transações espalhadas em `dias` — hotspot fluxo-caixa / série."""
    hoje = _hoje()
    total = 0
    for d in range(dias):
        dia = hoje - timedelta(days=d)
        for j in range(por_dia):
            desc = f"Perf fluxo {dia.isoformat()} #{j}"
            if Transacao.objects.filter(usuario=user, descricao=desc).exists():
                continue
            Transacao.objects.create(
                usuario=user,
                conta=conta,
                categoria=cat_desp,
                tipo="despesa",
                valor=Decimal("10.00"),
                data=dia,
                descricao=desc,
            )
            total += 1
    return total


def seed_transacoes_volume(user, conta, cat_desp, cat_rec, *, n: int = 500) -> int:
    """Volume alto para testes EXTENDED."""
    hoje = _hoje()
    existentes = Transacao.objects.filter(usuario=user, descricao__startswith="Perf vol ").count()
    for i in range(existentes, n):
        cat = cat_rec if i % 4 == 0 else cat_desp
        tipo = "receita" if i % 4 == 0 else "despesa"
        Transacao.objects.create(
            usuario=user,
            conta=conta,
            categoria=cat,
            tipo=tipo,
            valor=Decimal(f"{(i % 100) + 1}.00"),
            data=hoje - timedelta(days=i % 90),
            descricao=f"Perf vol {i + 1}",
        )
    return n
