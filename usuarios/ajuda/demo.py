"""Massa fictícia e reproduzível para screenshots da Ajuda."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from cartoes.models import Cartao
from categorias.models import Categoria
from contas.models import Conta
from transacoes.models import Transacao
from transacoes.services import criar_transacao_saldo_inicial
from usuarios.models import Perfil

User = get_user_model()

AJUDA_DEMO_EMAIL = "ajuda-screenshots@e2e.granago.test"
AJUDA_DEMO_NOME = "Alex"
AJUDA_DEMO_PASSWORD = "e2e-pass-123"


def _hoje() -> date:
    return timezone.localdate()


def _categoria(user, nome: str, tipo: str, cor: str, icone: str) -> Categoria:
    cat, _ = Categoria.objects.get_or_create(
        usuario=user,
        nome=nome,
        tipo=tipo,
        defaults={"ativa": True, "cor": cor, "icone": icone},
    )
    return cat


def seed_ajuda_demo(*, email: str = AJUDA_DEMO_EMAIL) -> dict:
    """Cria (ou reutiliza) um usuário fictício só para capturas da Ajuda."""
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"nome": AJUDA_DEMO_NOME, "is_active": True},
    )
    if created:
        user.set_password(AJUDA_DEMO_PASSWORD)
        user.save()

    perfil, _ = Perfil.objects.get_or_create(usuario=user)
    if not perfil.ocultar_atalho_primeiros_passos:
        perfil.ocultar_atalho_primeiros_passos = True
        perfil.save(update_fields=["ocultar_atalho_primeiros_passos"])

    conta, _ = Conta.objects.get_or_create(
        usuario=user,
        nome="Banco Principal",
        defaults={"tipo": "corrente", "ativa": True, "icone": "bank"},
    )
    hoje = _hoje()
    if not Transacao.objects.filter(conta=conta, tipo="ajuste", descricao="Saldo inicial").exists():
        criar_transacao_saldo_inicial(user, conta, Decimal("4850.00"), hoje.replace(day=1))

    cat_salario = _categoria(user, "Salário", "receita", "#10B981", "fa-wallet")
    cat_mercado = _categoria(user, "Mercado", "despesa", "#F59E0B", "fa-basket-shopping")
    cat_restaurante = _categoria(user, "Restaurante", "despesa", "#EF4444", "fa-utensils")
    cat_streaming = _categoria(user, "Streaming", "despesa", "#6366F1", "fa-tv")
    cat_compras = _categoria(user, "Compras", "despesa", "#EC4899", "fa-bag-shopping")

    lancamentos = (
        ("Salário", cat_salario, "receita", Decimal("5000.00"), min(5, hoje.day) or 1),
        ("Mercado", cat_mercado, "despesa", Decimal("350.00"), min(8, hoje.day) or 1),
        ("Restaurante", cat_restaurante, "despesa", Decimal("120.00"), min(12, hoje.day) or 1),
        ("Streaming", cat_streaming, "despesa", Decimal("39.90"), min(15, hoje.day) or 1),
    )
    transacoes = {}
    for descricao, categoria, tipo, valor, dia in lancamentos:
        tx, _ = Transacao.objects.get_or_create(
            usuario=user,
            descricao=descricao,
            defaults={
                "conta": conta,
                "categoria": categoria,
                "tipo": tipo,
                "valor": valor,
                "data": hoje.replace(day=dia),
            },
        )
        transacoes[descricao] = tx

    cartao, _ = Cartao.objects.get_or_create(
        usuario=user,
        nome="Cartão principal",
        defaults={
            "dia_fechamento": 10,
            "dia_vencimento": 17,
            "conta_padrao": conta,
            "ativa": True,
            "limite": Decimal("5000.00"),
        },
    )
    if not Transacao.objects.filter(usuario=user, descricao="Mercado Livre").exists():
        Transacao.objects.create(
            usuario=user,
            conta=conta,
            cartao=cartao,
            categoria=cat_compras,
            tipo="despesa",
            valor=Decimal("249.90"),
            data=hoje.replace(day=min(6, hoje.day) or 1),
            descricao="Mercado Livre",
        )

    return {
        "user": user,
        "password": AJUDA_DEMO_PASSWORD,
        "conta": conta,
        "cartao": cartao,
        "categorias": {
            "salario": cat_salario,
            "mercado": cat_mercado,
            "restaurante": cat_restaurante,
            "streaming": cat_streaming,
            "compras": cat_compras,
        },
        "transacao_mercado": transacoes["Mercado"],
    }
