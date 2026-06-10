"""Fixtures determinísticas — par de usuários e recursos de B."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from cartoes.models import Cartao
from categorias.models import Categoria
from contas.models import Conta
from relatorios.models import ExportRelatorioJob
from transacoes.models import Transacao

User = get_user_model()

RecursoTipo = Literal["transacao", "conta", "cartao", "fatura", "export_job"]


@dataclass
class ParUsuarios:
    user_a: object
    user_b: object
    client_a: Client
    client_b: Client
    conta_a: Conta
    conta_b: Conta
    cat_a: Categoria
    cat_b: Categoria
    perfil_a: object


def par_usuarios() -> ParUsuarios:
    user_a = User.objects.create_user(
        email="sec-a@test.local", password="x", nome="Sec A"
    )
    user_b = User.objects.create_user(
        email="sec-b@test.local", password="x", nome="Sec B"
    )
    conta_a = Conta.objects.create(
        usuario=user_a, nome="Conta A", tipo="corrente", ativa=True
    )
    conta_b = Conta.objects.create(
        usuario=user_b, nome="Conta B", tipo="corrente", ativa=True
    )
    cat_a = Categoria.objects.create(
        usuario=user_a, nome="Cat A", tipo="despesa", cor="#111", ativa=True
    )
    cat_b = Categoria.objects.create(
        usuario=user_b, nome="Cat B", tipo="despesa", cor="#222", ativa=True
    )
    from usuarios.models import Perfil

    perfil_a, _ = Perfil.objects.get_or_create(usuario=user_a)
    client_a = Client(enforce_csrf_checks=False)
    client_b = Client(enforce_csrf_checks=False)
    client_a.force_login(user_a)
    client_b.force_login(user_b)
    return ParUsuarios(
        user_a=user_a,
        user_b=user_b,
        client_a=client_a,
        client_b=client_b,
        conta_a=conta_a,
        conta_b=conta_b,
        cat_a=cat_a,
        cat_b=cat_b,
        perfil_a=perfil_a,
    )


def contagem_registros_a(user_a, modelo) -> int:
    return modelo.objects.filter(usuario=user_a).count()


def seed_recurso_b(par: ParUsuarios, tipo: RecursoTipo) -> int:
    if tipo == "transacao":
        tx = Transacao.objects.create(
            usuario=par.user_b,
            conta=par.conta_b,
            categoria=par.cat_b,
            tipo="despesa",
            valor=Decimal("10.00"),
            data=date(2026, 4, 1),
            descricao="SEC-B",
        )
        return tx.pk
    if tipo == "conta":
        return par.conta_b.pk
    if tipo == "cartao":
        cartao = Cartao.objects.create(
            usuario=par.user_b,
            nome="Cartão B",
            dia_fechamento=10,
            dia_vencimento=20,
            conta_padrao=par.conta_b,
            ativa=True,
        )
        return cartao.pk
    if tipo == "fatura":
        cartao_id = seed_recurso_b(par, "cartao")
        cartao = Cartao.objects.get(pk=cartao_id)
        tx = Transacao.objects.create(
            usuario=par.user_b,
            conta=par.conta_b,
            cartao=cartao,
            categoria=par.cat_b,
            tipo="despesa",
            valor=Decimal("20.00"),
            data=date(2026, 4, 5),
            descricao="SEC-B FAT",
        )
        return tx.fatura_id
    if tipo == "export_job":
        job = ExportRelatorioJob.objects.create(
            usuario=par.user_b,
            status=ExportRelatorioJob.STATUS_PENDING,
            filtros_json="{}",
        )
        return job.pk
    raise ValueError(tipo)


def client_csrf_strict(user) -> Client:
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    client.get(reverse("usuarios:configuracoes"))
    return client


def csrf_token(client: Client) -> str:
    return client.cookies["csrftoken"].value


def disparar_import_cross_tenant(par: ParUsuarios) -> tuple[int, int]:
    """POST import com conta de B como A; retorna (contagem_antes, contagem_depois) de A."""
    antes = contagem_registros_a(par.user_a, Transacao)
    url = reverse("transacoes:importar_ofx_confirmar")
    payload = {
        "conta_id": par.conta_b.pk,
        "linhas": [
            {
                "data": "2026-04-01",
                "valor": "99.00",
                "tipo": "despesa",
                "descricao": "Cross tenant",
            }
        ],
    }
    par.client_a.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
    )
    depois = contagem_registros_a(par.user_a, Transacao)
    return antes, depois


def seed_transacao_a(par: ParUsuarios) -> int:
    tx = Transacao.objects.create(
        usuario=par.user_a,
        conta=par.conta_a,
        categoria=par.cat_a,
        tipo="despesa",
        valor=Decimal("15.00"),
        data=date(2026, 5, 1),
        descricao="SEC-A",
    )
    return tx.pk


def seed_cartao_fatura_a(par: ParUsuarios) -> tuple[int, int]:
    cartao = Cartao.objects.create(
        usuario=par.user_a,
        nome="Cartão A",
        dia_fechamento=10,
        dia_vencimento=20,
        conta_padrao=par.conta_a,
        ativa=True,
    )
    tx = Transacao.objects.create(
        usuario=par.user_a,
        conta=par.conta_a,
        cartao=cartao,
        categoria=par.cat_a,
        tipo="despesa",
        valor=Decimal("30.00"),
        data=date(2026, 5, 5),
        descricao="SEC-A FAT",
    )
    return cartao.pk, tx.fatura_id
