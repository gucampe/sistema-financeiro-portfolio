"""Testes da auditoria de transferências e idempotência."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from categorias.models import Categoria
from contas.models import Conta
from transacoes.audit_transferencias import auditar_integridade_transferencias
from transacoes.models import Transacao
from transacoes.services import criar_transferencia, obter_categoria_transferencia

User = get_user_model()


class AuditoriaTransferenciasTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="audit-transf@test.local", password="x", nome="Audit"
        )
        self.a = Conta.objects.create(
            usuario=self.user, nome="A", tipo="corrente", ativa=True
        )
        self.b = Conta.objects.create(
            usuario=self.user, nome="B", tipo="poupanca", ativa=True
        )
        self.cat = obter_categoria_transferencia()
        Transacao.objects.create(
            usuario=self.user,
            conta=self.a,
            tipo="receita",
            valor=Decimal("1000"),
            descricao="base",
            data=date(2026, 1, 1),
            categoria=Categoria.objects.create(
                usuario=self.user, nome="R", tipo="receita", ativa=True
            ),
        )

    def test_auditoria_ok_apos_par_valido(self):
        criar_transferencia(
            self.user,
            conta_origem=self.a,
            conta_destino=self.b,
            valor=Decimal("50"),
            data=date(2026, 1, 2),
        )
        r = auditar_integridade_transferencias(usuario=self.user)
        self.assertTrue(r.ok)
        self.assertEqual(r.transfer_ids_ok, 1)

    def test_detecta_orfao(self):
        tid = uuid.uuid4()
        Transacao.objects.create(
            usuario=self.user,
            conta=self.a,
            tipo="transferencia",
            valor=Decimal("10"),
            descricao="órfã",
            data=date(2026, 1, 2),
            categoria=self.cat,
            transfer_id=tid,
            papel_transferencia="origem",
        )
        r = auditar_integridade_transferencias(usuario=self.user)
        self.assertFalse(r.ok)
        self.assertTrue(any(p.codigo == "perna_count" for p in r.problemas))

    def test_detecta_valor_divergente(self):
        o, d = criar_transferencia(
            self.user,
            conta_origem=self.a,
            conta_destino=self.b,
            valor=Decimal("20"),
            data=date(2026, 1, 2),
        )
        # Bypass model.full_clean via update
        Transacao.objects.filter(pk=d.pk).update(valor=Decimal("21"))
        r = auditar_integridade_transferencias(usuario=self.user)
        self.assertFalse(r.ok)
        self.assertTrue(any(p.codigo == "valor_divergente" for p in r.problemas))

    def test_command_fail_on_error(self):
        from django.core.management.base import CommandError

        tid = uuid.uuid4()
        Transacao.objects.create(
            usuario=self.user,
            conta=self.a,
            tipo="transferencia",
            valor=Decimal("10"),
            descricao="órfã",
            data=date(2026, 1, 2),
            categoria=self.cat,
            transfer_id=tid,
            papel_transferencia="origem",
        )
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                "auditar_transferencias",
                email=self.user.email,
                fail_on_error=True,
                stdout=out,
                stderr=out,
            )


class IdempotenciaTransferenciaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="idem-transf@test.local", password="x", nome="Idem"
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.a = Conta.objects.create(
            usuario=self.user, nome="A", tipo="corrente", ativa=True
        )
        self.b = Conta.objects.create(
            usuario=self.user, nome="B", tipo="poupanca", ativa=True
        )

    def test_mesma_chave_nao_duplica(self):
        key = str(uuid.uuid4())
        payload = {
            "conta_origem": self.a.id,
            "conta_destino": self.b.id,
            "valor": "40,00",
            "data": "2026-01-15",
            "descricao": "idem",
        }
        r1 = self.client.post(
            reverse("transacoes:transferir"),
            payload,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_X_IDEMPOTENCY_KEY=key,
        )
        r2 = self.client.post(
            reverse("transacoes:transferir"),
            payload,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_X_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.json()["transfer_id"], r2.json()["transfer_id"])
        self.assertEqual(
            Transacao.objects.filter(usuario=self.user, tipo="transferencia").count(),
            2,
        )

    def test_chaves_diferentes_criam_pares_distintos(self):
        payload = {
            "conta_origem": self.a.id,
            "conta_destino": self.b.id,
            "valor": "10,00",
            "data": "2026-01-15",
            "descricao": "duas",
        }
        self.client.post(
            reverse("transacoes:transferir"),
            payload,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.client.post(
            reverse("transacoes:transferir"),
            payload,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(
            Transacao.objects.filter(usuario=self.user, tipo="transferencia").count(),
            4,
        )

    def test_rotulo_historico_via_contraparte(self):
        o, d = criar_transferencia(
            self.user,
            conta_origem=self.a,
            conta_destino=self.b,
            valor=Decimal("5"),
            data=date(2026, 1, 3),
        )
        self.assertEqual(o.rotulo_historico_transferencia(), f"Transferência para {self.b.nome}")
        self.assertEqual(d.rotulo_historico_transferencia(), f"Recebida de {self.a.nome}")
        self.assertEqual(o.contraparte().pk, d.pk)
