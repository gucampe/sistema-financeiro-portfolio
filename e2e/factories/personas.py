"""Personas determinísticas para E2E e staging."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from cartoes.models import Cartao
from categorias.models import Categoria
from contas.models import Conta
from relatorios.models import OrcamentoCategoria
from relatorios.tests.helpers.kpi_home import kpi_home
from transacoes.models import Transacao
from transacoes.services import criar_transacao_saldo_inicial

User = get_user_model()

E2E_PASSWORD = "e2e-pass-123"


def _hoje() -> date:
    return timezone.localdate()


def _categoria_despesa(user, nome: str = "E2E Despesas") -> Categoria:
    cat, _ = Categoria.objects.get_or_create(
        usuario=user,
        nome=nome,
        defaults={
            "tipo": "despesa",
            "ativa": True,
            "padrao": False,
            "cor": "#4F46E5",
            "icone": "fa-tag",
        },
    )
    return cat


def _categoria_receita(user, nome: str = "E2E Receitas") -> Categoria:
    cat, _ = Categoria.objects.get_or_create(
        usuario=user,
        nome=nome,
        defaults={
            "tipo": "receita",
            "ativa": True,
            "padrao": False,
            "cor": "#10B981",
            "icone": "fa-tag",
        },
    )
    return cat


def seed_persona_empty(email: str = "empty@e2e.granago.test") -> User:
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"nome": "E2E Empty", "is_active": True},
    )
    if created:
        user.set_password(E2E_PASSWORD)
        user.save()
    return user


def seed_persona_basic(email: str = "basic@e2e.granago.test") -> dict:
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"nome": "E2E Basic", "is_active": True},
    )
    if created:
        user.set_password(E2E_PASSWORD)
        user.save()

    conta, _ = Conta.objects.get_or_create(
        usuario=user,
        nome="Conta E2E",
        defaults={"tipo": "corrente", "ativa": True, "icone": "bank"},
    )
    conta_b, _ = Conta.objects.get_or_create(
        usuario=user,
        nome="Conta E2E B",
        defaults={"tipo": "poupanca", "ativa": True, "icone": "piggy-bank"},
    )
    if created or not Transacao.objects.filter(conta=conta, tipo="ajuste").exists():
        criar_transacao_saldo_inicial(
            user,
            conta,
            Decimal("1000.00"),
            _hoje().replace(day=1),
        )

    cat_desp = _categoria_despesa(user)
    cat_rec = _categoria_receita(user)

    hoje = _hoje()
    if not Transacao.objects.filter(usuario=user, descricao="E2E receita seed").exists():
        Transacao.objects.create(
            usuario=user,
            conta=conta,
            categoria=cat_rec,
            tipo="receita",
            valor=Decimal("500.00"),
            data=hoje.replace(day=min(10, hoje.day) or 1),
            descricao="E2E receita seed",
        )
        Transacao.objects.create(
            usuario=user,
            conta=conta,
            categoria=cat_desp,
            tipo="despesa",
            valor=Decimal("150.00"),
            data=hoje.replace(day=min(12, hoje.day) or 1),
            descricao="E2E despesa seed",
        )

    return {
        "user": user,
        "password": E2E_PASSWORD,
        "conta": conta,
        "conta_b": conta_b,
        "cat_despesa": cat_desp,
        "cat_receita": cat_rec,
    }


def seed_persona_ecossistema(email: str = "ecossistema@e2e.granago.test") -> dict:
    """Persona GLOB-E: conta única, orçamento cadastrado, sem lançamentos do mês."""
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"nome": "E2E Ecossistema", "is_active": True},
    )
    if created:
        user.set_password(E2E_PASSWORD)
        user.save()

    hoje = _hoje()
    inicio_mes = hoje.replace(day=1)
    conta, _ = Conta.objects.get_or_create(
        usuario=user,
        nome="Conta Ecossistema E2E",
        defaults={"tipo": "corrente", "ativa": True, "icone": "bank"},
    )
    if created or not Transacao.objects.filter(conta=conta, tipo="ajuste").exists():
        criar_transacao_saldo_inicial(user, conta, Decimal("1000.00"), inicio_mes)

    cat_desp = _categoria_despesa(user, "Eco Despesas")
    cat_rec = _categoria_receita(user, "Eco Receitas")

    OrcamentoCategoria.objects.get_or_create(
        usuario=user,
        categoria=cat_desp,
        defaults={
            "valor_planejado": Decimal("500.00"),
            "inicio_ano": hoje.year,
            "inicio_mes": hoje.month,
            "ativo": True,
        },
    )

    return {
        "user": user,
        "password": E2E_PASSWORD,
        "conta": conta,
        "cat_despesa": cat_desp,
        "cat_receita": cat_rec,
    }


def seed_persona_card_user(email: str = "card@e2e.granago.test") -> dict:
    data = seed_persona_basic(email)
    user = data["user"]
    conta = data["conta"]
    cat = data["cat_despesa"]

    cartao, _ = Cartao.objects.get_or_create(
        usuario=user,
        nome="Cartão E2E",
        defaults={
            "dia_fechamento": 5,
            "dia_vencimento": 12,
            "conta_padrao": conta,
            "ativa": True,
            "limite": Decimal("5000.00"),
        },
    )

    hoje = _hoje()
    if not Transacao.objects.filter(usuario=user, descricao="E2E compra cartao").exists():
        Transacao.objects.create(
            usuario=user,
            conta=conta,
            cartao=cartao,
            categoria=cat,
            tipo="despesa",
            valor=Decimal("250.00"),
            data=hoje.replace(day=min(3, hoje.day) or 1),
            descricao="E2E compra cartao",
        )

    fatura = None
    txs = Transacao.objects.filter(usuario=user, cartao=cartao, descricao="E2E compra cartao")
    if txs.exists():
        fatura = txs.first().fatura

    return {**data, "cartao": cartao, "fatura": fatura}


def seed_persona_cartao_b(email: str = "cartao-b@e2e.granago.test") -> dict:
    """Dois cartões na mesma conta — cenários E2E-FAT-05..10."""
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"nome": "E2E Cartão B", "is_active": True},
    )
    if created:
        user.set_password(E2E_PASSWORD)
        user.save()

    conta, _ = Conta.objects.get_or_create(
        usuario=user,
        nome="Conta E2E Dupla",
        defaults={"tipo": "corrente", "ativa": True, "icone": "bank"},
    )
    if created or not Transacao.objects.filter(conta=conta, tipo="ajuste").exists():
        criar_transacao_saldo_inicial(
            user,
            conta,
            Decimal("5000.00"),
            _hoje().replace(day=1),
        )

    cat = _categoria_despesa(user, "E2E Desp Cartões")
    cat_orc, _ = Categoria.objects.get_or_create(
        usuario=user,
        nome="E2E Orc Cartão",
        tipo="despesa",
        defaults={"ativa": True, "cor": "#6366F1", "icone": "fa-tag"},
    )
    OrcamentoCategoria.objects.get_or_create(
        usuario=user,
        categoria=cat_orc,
        defaults={
            "valor_planejado": Decimal("500.00"),
            "inicio_ano": _hoje().year,
            "inicio_mes": _hoje().month,
            "ativo": True,
        },
    )

    cartao_a, _ = Cartao.objects.get_or_create(
        usuario=user,
        nome="Cartão E2E A",
        defaults={
            "dia_fechamento": 10,
            "dia_vencimento": 20,
            "conta_padrao": conta,
            "ativa": True,
            "limite": Decimal("8000.00"),
        },
    )
    cartao_b, _ = Cartao.objects.get_or_create(
        usuario=user,
        nome="Cartão E2E B",
        defaults={
            "dia_fechamento": 25,
            "dia_vencimento": 5,
            "conta_padrao": conta,
            "ativa": True,
            "limite": Decimal("8000.00"),
        },
    )

    return {
        "user": user,
        "password": E2E_PASSWORD,
        "conta": conta,
        "cat_despesa": cat,
        "cat_orcamento": cat_orc,
        "cartao_a": cartao_a,
        "cartao_b": cartao_b,
        "cartao": cartao_a,
    }


def seed_persona_relatorios(email: str = "relatorios@e2e.granago.test") -> dict:
    """Dados para FIL-* e REL-X-*: 2 contas, múltiplos períodos e cartão."""
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"nome": "E2E Relatórios", "is_active": True},
    )
    if created:
        user.set_password(E2E_PASSWORD)
        user.save()

    conta_a, _ = Conta.objects.get_or_create(
        usuario=user,
        nome="Conta Rel A",
        defaults={"tipo": "corrente", "ativa": True, "icone": "bank"},
    )
    conta_b, _ = Conta.objects.get_or_create(
        usuario=user,
        nome="Conta Rel B",
        defaults={"tipo": "poupanca", "ativa": True, "icone": "piggy-bank"},
    )

    hoje = _hoje()
    inicio_mes = hoje.replace(day=1)
    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]

    if not Transacao.objects.filter(conta=conta_a, tipo="ajuste").exists():
        criar_transacao_saldo_inicial(user, conta_a, Decimal("1000.00"), inicio_mes)

    cat_desp = _categoria_despesa(user, "E2E Despesas")
    cat_rec = _categoria_receita(user, "E2E Receitas")
    cat_trans, _ = Categoria.objects.get_or_create(
        usuario=user,
        nome="Rel Transporte",
        tipo="despesa",
        defaults={"ativa": True, "cor": "#F59E0B", "icone": "fa-car"},
    )
    cat_lazer, _ = Categoria.objects.get_or_create(
        usuario=user,
        nome="Rel Lazer",
        tipo="despesa",
        defaults={"ativa": True, "cor": "#EC4899", "icone": "fa-gamepad"},
    )

    primeiro_mes_atual = inicio_mes
    ultimo_mes_anterior = primeiro_mes_atual - timedelta(days=1)
    data_mes_anterior = ultimo_mes_anterior.replace(
        day=min(15, ultimo_mes_anterior.day)
    )
    data_fora = hoje - timedelta(days=120)

    seed_key = "E2E rel seed"
    if not Transacao.objects.filter(usuario=user, descricao=seed_key).exists():
        Transacao.objects.create(
            usuario=user,
            conta=conta_a,
            categoria=cat_rec,
            tipo="receita",
            valor=Decimal("500.00"),
            data=hoje.replace(day=min(8, ultimo_dia)),
            descricao=seed_key,
        )
        Transacao.objects.create(
            usuario=user,
            conta=conta_a,
            categoria=cat_desp,
            tipo="despesa",
            valor=Decimal("150.00"),
            data=hoje.replace(day=min(9, ultimo_dia)),
            descricao="E2E rel despesa A",
        )
        Transacao.objects.create(
            usuario=user,
            conta=conta_b,
            categoria=cat_trans,
            tipo="despesa",
            valor=Decimal("80.00"),
            data=hoje.replace(day=min(11, ultimo_dia)),
            descricao="E2E rel despesa B",
        )
        Transacao.objects.create(
            usuario=user,
            conta=conta_a,
            categoria=cat_rec,
            tipo="receita",
            valor=Decimal("200.00"),
            data=data_mes_anterior,
            descricao="E2E rel receita mes anterior",
        )
        Transacao.objects.create(
            usuario=user,
            conta=conta_a,
            categoria=cat_rec,
            tipo="receita",
            valor=Decimal("999.00"),
            data=data_fora,
            descricao="E2E rel fora periodo",
        )

    cartao, _ = Cartao.objects.get_or_create(
        usuario=user,
        nome="Cartão Rel E2E",
        defaults={
            "dia_fechamento": 5,
            "dia_vencimento": 12,
            "conta_padrao": conta_a,
            "ativa": True,
            "limite": Decimal("8000.00"),
        },
    )

    if not Transacao.objects.filter(usuario=user, descricao="E2E rel compra cartao").exists():
        Transacao.objects.create(
            usuario=user,
            conta=conta_a,
            cartao=cartao,
            categoria=cat_desp,
            tipo="despesa",
            valor=Decimal("250.00"),
            data=hoje.replace(day=min(4, ultimo_dia)),
            descricao="E2E rel compra cartao",
        )

    if not Transacao.objects.filter(
        usuario=user, descricao="E2E rel compra competencia prox"
    ).exists():
        Transacao.objects.create(
            usuario=user,
            conta=conta_a,
            cartao=cartao,
            categoria=cat_lazer,
            tipo="despesa",
            valor=Decimal("120.00"),
            data=hoje.replace(day=min(10, ultimo_dia)),
            descricao="E2E rel compra competencia prox",
        )

    OrcamentoCategoria.objects.get_or_create(
        usuario=user,
        categoria=cat_desp,
        defaults={
            "valor_planejado": Decimal("300.00"),
            "inicio_ano": hoje.year,
            "inicio_mes": hoje.month,
            "ativo": True,
        },
    )

    return {
        "user": user,
        "password": E2E_PASSWORD,
        "conta_a": conta_a,
        "conta_b": conta_b,
        "conta": conta_a,
        "cat_despesa": cat_desp,
        "cat_receita": cat_rec,
        "cat_transporte": cat_trans,
        "cat_lazer": cat_lazer,
        "cartao": cartao,
        "kpi_home": kpi_home(user),
    }


def seed_persona_orcamentos(email: str = "orcamentos@e2e.granago.test") -> dict:
    """Persona ORC-*: múltiplos status, vigência e impacto de faturas."""
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"nome": "E2E Orçamentos", "is_active": True},
    )
    if created:
        user.set_password(E2E_PASSWORD)
        user.save()

    conta, _ = Conta.objects.get_or_create(
        usuario=user,
        nome="Conta Orc E2E",
        defaults={"tipo": "corrente", "ativa": True, "icone": "bank"},
    )

    hoje = _hoje()
    inicio_mes = hoje.replace(day=1)
    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    if hoje.month == 12:
        prox_ano, prox_mes = hoje.year + 1, 1
    else:
        prox_ano, prox_mes = hoje.year, hoje.month + 1

    def _cat(nome: str) -> Categoria:
        cat, _ = Categoria.objects.get_or_create(
            usuario=user,
            nome=nome,
            tipo="despesa",
            defaults={"ativa": True, "cor": "#6366F1", "icone": "fa-tag"},
        )
        return cat

    cat_moradia = _cat("Orc Moradia")
    cat_transporte = _cat("Orc Transporte")
    cat_lazer = _cat("Orc Lazer")
    cat_futuro = _cat("Orc Futuro")

    OrcamentoCategoria.objects.update_or_create(
        usuario=user,
        categoria=cat_moradia,
        defaults={
            "valor_planejado": Decimal("1000.00"),
            "inicio_ano": hoje.year,
            "inicio_mes": hoje.month,
            "ativo": True,
        },
    )
    OrcamentoCategoria.objects.update_or_create(
        usuario=user,
        categoria=cat_transporte,
        defaults={
            "valor_planejado": Decimal("200.00"),
            "inicio_ano": hoje.year,
            "inicio_mes": hoje.month,
            "ativo": True,
        },
    )
    OrcamentoCategoria.objects.update_or_create(
        usuario=user,
        categoria=cat_lazer,
        defaults={
            "valor_planejado": Decimal("150.00"),
            "inicio_ano": hoje.year,
            "inicio_mes": hoje.month,
            "ativo": True,
        },
    )
    OrcamentoCategoria.objects.update_or_create(
        usuario=user,
        categoria=cat_futuro,
        defaults={
            "valor_planejado": Decimal("500.00"),
            "inicio_ano": prox_ano,
            "inicio_mes": prox_mes,
            "ativo": True,
        },
    )

    seed_key = "E2E orc seed"
    if not Transacao.objects.filter(usuario=user, descricao=seed_key).exists():
        Transacao.objects.create(
            usuario=user,
            conta=conta,
            categoria=cat_moradia,
            tipo="despesa",
            valor=Decimal("400.00"),
            data=hoje.replace(day=min(8, ultimo_dia)),
            descricao=seed_key,
        )
        Transacao.objects.create(
            usuario=user,
            conta=conta,
            categoria=cat_transporte,
            tipo="despesa",
            valor=Decimal("180.00"),
            data=hoje.replace(day=min(9, ultimo_dia)),
            descricao="E2E orc transporte",
        )
        Transacao.objects.create(
            usuario=user,
            conta=conta,
            categoria=cat_lazer,
            tipo="despesa",
            valor=Decimal("200.00"),
            data=hoje.replace(day=min(10, ultimo_dia)),
            descricao="E2E orc lazer estourado",
        )

    cartao, _ = Cartao.objects.get_or_create(
        usuario=user,
        nome="Cartão Orc E2E",
        defaults={
            "dia_fechamento": 5,
            "dia_vencimento": 12,
            "conta_padrao": conta,
            "ativa": True,
            "limite": Decimal("5000.00"),
        },
    )

    if not Transacao.objects.filter(usuario=user, descricao="E2E orc compra cartao").exists():
        Transacao.objects.create(
            usuario=user,
            conta=conta,
            cartao=cartao,
            categoria=cat_moradia,
            tipo="despesa",
            valor=Decimal("50.00"),
            data=hoje.replace(day=min(4, ultimo_dia)),
            descricao="E2E orc compra cartao",
        )

    fatura = None
    txs_cartao = Transacao.objects.filter(usuario=user, cartao=cartao).first()
    if txs_cartao:
        fatura = txs_cartao.fatura
        if fatura and not Transacao.objects.filter(
            usuario=user, descricao="E2E orc pagamento fatura"
        ).exists():
            Transacao.objects.create(
                usuario=user,
                conta=conta,
                categoria=cat_moradia,
                tipo="despesa",
                valor=Decimal("999.00"),
                data=hoje.replace(day=min(11, ultimo_dia)),
                descricao="E2E orc pagamento fatura",
                pagamento_de_fatura=fatura,
            )

    return {
        "user": user,
        "password": E2E_PASSWORD,
        "conta": conta,
        "cat_moradia": cat_moradia,
        "cat_transporte": cat_transporte,
        "cat_lazer": cat_lazer,
        "cat_futuro": cat_futuro,
        "cartao": cartao,
        "fatura": fatura,
    }
