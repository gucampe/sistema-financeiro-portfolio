"""
Bateria QA sênior: transferências entre contas.

Cobre domínio, HTTP/API, integridade, rollback, isolamento multi-usuário,
valores extremos e regressões básicas (receita/despesa/ajuste).
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from categorias.models import Categoria
from contas.models import Conta
from financial_contracts.saldo_contracts import assert_patrimonio_contas, assert_saldo_conta
from transacoes.models import Transacao
from transacoes.services import (
    atualizar_transferencia,
    criar_transferencia,
    excluir_transferencia,
    obter_par_transferencia,
)
from transacoes.tests.helpers.ledger_invariants import assert_saldo_consistente

User = get_user_model()


def _assert_par_integro(user, transfer_id) -> tuple[Transacao, Transacao]:
    qs = Transacao.objects.filter(
        usuario=user, transfer_id=transfer_id, tipo="transferencia"
    )
    assert qs.count() == 2, f"esperado 2 pernas, veio {qs.count()}"
    o, d = obter_par_transferencia(user, transfer_id)
    assert o.papel_transferencia == "origem"
    assert d.papel_transferencia == "destino"
    assert o.valor == d.valor
    assert o.data == d.data
    assert o.descricao == d.descricao
    assert o.conta_id != d.conta_id
    return o, d


def _assert_sem_orfaos(user) -> None:
    tids = (
        Transacao.objects.filter(usuario=user, tipo="transferencia")
        .exclude(transfer_id=None)
        .values_list("transfer_id", flat=True)
        .distinct()
    )
    for tid in tids:
        n = Transacao.objects.filter(usuario=user, transfer_id=tid).count()
        assert n == 2, f"órfão/incompleto transfer_id={tid} count={n}"


class TransferenciaQABase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="qa-transf@test.local", password="x", nome="QA"
        )
        self.other = User.objects.create_user(
            email="qa-other@test.local", password="x", nome="Other"
        )
        self.conta_a = Conta.objects.create(
            usuario=self.user, nome="Corrente", tipo="corrente", ativa=True
        )
        self.conta_b = Conta.objects.create(
            usuario=self.user, nome="Poupança", tipo="poupanca", ativa=True
        )
        self.conta_c = Conta.objects.create(
            usuario=self.user, nome="Carteira", tipo="carteira", ativa=True
        )
        self.conta_other = Conta.objects.create(
            usuario=self.other, nome="Alienígena", tipo="corrente", ativa=True
        )
        self.cat_rec, _ = Categoria.objects.get_or_create(
            usuario=self.user,
            nome="Salário QA",
            tipo="receita",
            defaults={"ativa": True},
        )
        self.cat_desp, _ = Categoria.objects.get_or_create(
            usuario=self.user,
            nome="Mercado QA",
            tipo="despesa",
            defaults={"ativa": True},
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            tipo="receita",
            valor=Decimal("5000.00"),
            descricao="Base",
            data=date(2026, 1, 1),
            categoria=self.cat_rec,
        )
        self.client = Client()
        self.client.force_login(self.user)


class TransferenciaFluxosFelizesTests(TransferenciaQABase):
    def test_valores_centavos_e_grandes(self):
        for valor in (Decimal("0.01"), Decimal("1.99"), Decimal("999999.99")):
            with self.subTest(valor=valor):
                o, d = criar_transferencia(
                    self.user,
                    conta_origem=self.conta_a,
                    conta_destino=self.conta_b,
                    valor=valor,
                    data=date(2026, 2, 1),
                    descricao=f"v={valor}",
                )
                _assert_par_integro(self.user, o.transfer_id)
                excluir_transferencia(self.user, o.transfer_id)

    def test_datas_passada_atual_futura(self):
        hoje = date(2026, 7, 21)
        for d in (hoje - timedelta(days=30), hoje, hoje + timedelta(days=15)):
            with self.subTest(data=d):
                o, _ = criar_transferencia(
                    self.user,
                    conta_origem=self.conta_a,
                    conta_destino=self.conta_b,
                    valor=Decimal("10.00"),
                    data=d,
                )
                self.assertEqual(o.data, d)
                excluir_transferencia(self.user, o.transfer_id)

    def test_todas_combinacoes_contas(self):
        contas = [self.conta_a, self.conta_b, self.conta_c]
        for origem in contas:
            for destino in contas:
                if origem.pk == destino.pk:
                    continue
                with self.subTest(origem=origem.nome, destino=destino.nome):
                    o, d = criar_transferencia(
                        self.user,
                        conta_origem=origem,
                        conta_destino=destino,
                        valor=Decimal("5.00"),
                        data=date(2026, 3, 1),
                    )
                    _assert_par_integro(self.user, o.transfer_id)
                    self.assertEqual(o.conta_id, origem.pk)
                    self.assertEqual(d.conta_id, destino.pk)
                    excluir_transferencia(self.user, o.transfer_id)

    def test_varias_consecutivas_patrimonio_estavel(self):
        patrimonio = Decimal("5000.00")
        for i in range(5):
            criar_transferencia(
                self.user,
                conta_origem=self.conta_a,
                conta_destino=self.conta_b,
                valor=Decimal("100.00"),
                data=date(2026, 4, 1),
                descricao=f"seq-{i}",
            )
        assert_patrimonio_contas(self.user, patrimonio)
        assert_saldo_conta(self.conta_a, Decimal("4500.00"))
        assert_saldo_conta(self.conta_b, Decimal("500.00"))
        _assert_sem_orfaos(self.user)

    def test_crud_completo_via_service(self):
        o, d = criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("200.00"),
            data=date(2026, 5, 1),
            descricao="Inicial",
        )
        tid = o.transfer_id
        atualizar_transferencia(
            self.user,
            tid,
            conta_origem=self.conta_b,
            conta_destino=self.conta_c,
            valor=Decimal("80.00"),
            data=date(2026, 5, 2),
            descricao="Editada",
        )
        o2, d2 = _assert_par_integro(self.user, tid)
        self.assertEqual(o2.conta_id, self.conta_b.pk)
        self.assertEqual(d2.conta_id, self.conta_c.pk)
        self.assertEqual(o2.valor, Decimal("80.00"))
        excluir_transferencia(self.user, tid)
        self.assertEqual(
            Transacao.objects.filter(usuario=self.user, transfer_id=tid).count(), 0
        )
        assert_patrimonio_contas(self.user, Decimal("5000.00"))


class TransferenciaInvalidosTests(TransferenciaQABase):
    def test_origem_igual_destino(self):
        with self.assertRaises(ValidationError):
            criar_transferencia(
                self.user,
                conta_origem=self.conta_a,
                conta_destino=self.conta_a,
                valor=Decimal("10"),
                data=date(2026, 1, 1),
            )

    def test_valor_zero_negativo_none(self):
        for v in (Decimal("0"), Decimal("-1"), None):
            with self.subTest(v=v):
                with self.assertRaises(ValidationError):
                    criar_transferencia(
                        self.user,
                        conta_origem=self.conta_a,
                        conta_destino=self.conta_b,
                        valor=v,
                        data=date(2026, 1, 1),
                    )

    def test_conta_outro_usuario(self):
        with self.assertRaises(ValidationError):
            criar_transferencia(
                self.user,
                conta_origem=self.conta_a,
                conta_destino=self.conta_other,
                valor=Decimal("10"),
                data=date(2026, 1, 1),
            )

    def test_conta_inativa(self):
        self.conta_b.ativa = False
        self.conta_b.save(update_fields=["ativa"])
        with self.assertRaises(ValidationError):
            criar_transferencia(
                self.user,
                conta_origem=self.conta_a,
                conta_destino=self.conta_b,
                valor=Decimal("10"),
                data=date(2026, 1, 1),
            )

    def test_transfer_id_inexistente_atualizar(self):
        with self.assertRaises(ValidationError):
            atualizar_transferencia(
                self.user,
                uuid.uuid4(),
                valor=Decimal("10"),
            )

    def test_transfer_id_inexistente_excluir(self):
        with self.assertRaises(ValidationError):
            excluir_transferencia(self.user, uuid.uuid4())

    def test_nao_permite_criar_perna_unica_via_model(self):
        """Model exige transfer_id+papel, mas não exige par — serviço é a garantia."""
        tid = uuid.uuid4()
        tx = Transacao(
            usuario=self.user,
            conta=self.conta_a,
            tipo="transferencia",
            valor=Decimal("10"),
            descricao="Órfã",
            data=date(2026, 1, 1),
            categoria=self.cat_rec,
            transfer_id=tid,
            papel_transferencia="origem",
        )
        tx.save()
        with self.assertRaises(ValidationError):
            obter_par_transferencia(self.user, tid)
        tx.delete()

    def test_constraint_duplicata_mesmo_papel(self):
        o, _ = criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("10"),
            data=date(2026, 1, 1),
        )
        clone = Transacao(
            usuario=self.user,
            conta=self.conta_c,
            tipo="transferencia",
            valor=Decimal("10"),
            descricao="dup",
            data=date(2026, 1, 1),
            categoria=self.cat_rec,
            transfer_id=o.transfer_id,
            papel_transferencia="origem",
        )
        with self.assertRaises((ValidationError, IntegrityError)):
            with transaction.atomic():
                clone.save()


class TransferenciaHttpTests(TransferenciaQABase):
    def _post_transferir(self, payload, *, ajax=True):
        kwargs = {}
        if ajax:
            kwargs["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"
        return self.client.post(
            reverse("transacoes:transferir"), payload, **kwargs
        )

    def test_post_origem_igual_destino_400(self):
        resp = self._post_transferir(
            {
                "conta_origem": self.conta_a.id,
                "conta_destino": self.conta_a.id,
                "valor": "10,00",
                "data": "2026-01-15",
                "descricao": "igual",
            }
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            Transacao.objects.filter(usuario=self.user, tipo="transferencia").count(), 0
        )

    def test_post_valor_vazio_zero_negativo(self):
        for valor in ("", "0", "0,00", "-5,00"):
            with self.subTest(valor=valor):
                resp = self._post_transferir(
                    {
                        "conta_origem": self.conta_a.id,
                        "conta_destino": self.conta_b.id,
                        "valor": valor,
                        "data": "2026-01-15",
                    }
                )
                self.assertEqual(resp.status_code, 400)

    def test_uuid_invalido(self):
        resp = self._post_transferir(
            {
                "conta_origem": self.conta_a.id,
                "conta_destino": self.conta_b.id,
                "valor": "10,00",
                "data": "2026-01-15",
                "transfer_id": "nao-e-uuid",
            }
        )
        self.assertEqual(resp.status_code, 400)

    def test_transfer_id_inexistente_via_http(self):
        resp = self._post_transferir(
            {
                "conta_origem": self.conta_a.id,
                "conta_destino": self.conta_b.id,
                "valor": "10,00",
                "data": "2026-01-15",
                "transfer_id": str(uuid.uuid4()),
            }
        )
        self.assertEqual(resp.status_code, 400)

    def test_conta_inexistente(self):
        resp = self._post_transferir(
            {
                "conta_origem": 999999,
                "conta_destino": self.conta_b.id,
                "valor": "10,00",
                "data": "2026-01-15",
            }
        )
        self.assertEqual(resp.status_code, 400)

    def test_payload_incompleto(self):
        resp = self._post_transferir({"valor": "10,00"})
        self.assertEqual(resp.status_code, 400)

    def test_campos_extras_ignorados_com_sucesso(self):
        resp = self._post_transferir(
            {
                "conta_origem": self.conta_a.id,
                "conta_destino": self.conta_b.id,
                "valor": "33,33",
                "data": "2026-01-15",
                "descricao": "extra",
                "categoria": self.cat_desp.id,
                "hack": "1",
                "tipo": "receita",
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        _assert_par_integro(self.user, data["transfer_id"])

    def test_editar_via_endpoint_dedicado(self):
        o, _ = criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("50"),
            data=date(2026, 1, 10),
        )
        resp = self._post_transferir(
            {
                "transfer_id": str(o.transfer_id),
                "conta_origem": self.conta_a.id,
                "conta_destino": self.conta_c.id,
                "valor": "77,00",
                "data": "2026-01-20",
                "descricao": "HTTP edit",
            }
        )
        self.assertEqual(resp.status_code, 200)
        o2, d2 = _assert_par_integro(self.user, o.transfer_id)
        self.assertEqual(o2.valor, Decimal("77.00"))
        self.assertEqual(d2.conta_id, self.conta_c.id)

    def test_bloquear_editar_perna_via_editar_transacao_ajax(self):
        o, _ = criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("40"),
            data=date(2026, 1, 10),
        )
        resp = self.client.post(
            reverse("transacoes:editar", args=[o.pk]),
            {
                "tipo": "despesa",
                "conta": self.conta_a.id,
                "categoria": self.cat_desp.id,
                "valor": "99,00",
                "data": "2026-01-10",
                "descricao": "hack perna",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 400)
        _assert_par_integro(self.user, o.transfer_id)
        o.refresh_from_db()
        self.assertEqual(o.valor, Decimal("40"))
        self.assertEqual(o.tipo, "transferencia")

    def test_bloquear_editar_perna_via_editar_transacao_nao_ajax(self):
        o, d = criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("40"),
            data=date(2026, 1, 10),
        )
        resp = self.client.post(
            reverse("transacoes:editar", args=[o.pk]),
            {
                "tipo": "despesa",
                "conta": self.conta_a.id,
                "categoria": self.cat_desp.id,
                "valor": "99,00",
                "data": "2026-01-10",
                "descricao": "hack perna nao ajax",
            },
        )
        self.assertEqual(resp.status_code, 302)
        o.refresh_from_db()
        d.refresh_from_db()
        self.assertEqual(o.tipo, "transferencia")
        self.assertEqual(o.valor, Decimal("40"))
        self.assertEqual(d.tipo, "transferencia")
        self.assertEqual(d.valor, Decimal("40"))
        _assert_par_integro(self.user, o.transfer_id)

    def test_excluir_qualquer_perna_remove_par(self):
        o, d = criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("25"),
            data=date(2026, 1, 10),
        )
        tid = o.transfer_id
        resp = self.client.post(
            reverse("transacoes:excluir", args=[d.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            Transacao.objects.filter(usuario=self.user, transfer_id=tid).count(), 0
        )

    def test_criar_via_formulario_normal_bloqueado(self):
        resp = self.client.post(
            reverse("transacoes:adicionar"),
            {
                "tipo": "transferencia",
                "conta": self.conta_a.id,
                "categoria": self.cat_rec.id,
                "valor": "10,00",
                "data": "2026-01-15",
                "descricao": "bypass",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            Transacao.objects.filter(usuario=self.user, tipo="transferencia").count(), 0
        )

    def test_isolamento_outro_usuario(self):
        o, _ = criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("15"),
            data=date(2026, 1, 10),
        )
        other_client = Client()
        other_client.force_login(self.other)
        resp = other_client.post(
            reverse("transacoes:excluir", args=[o.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 404)
        _assert_par_integro(self.user, o.transfer_id)


class TransferenciaRollbackTests(TransferenciaQABase):
    def test_falha_na_segunda_perna_nao_persiste_nada(self):
        original_save = Transacao.save
        calls = {"n": 0}

        def flaky_save(self_tx, *args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise ValidationError("falha forçada na 2ª perna")
            return original_save(self_tx, *args, **kwargs)

        antes = Transacao.objects.filter(usuario=self.user).count()
        with mock.patch.object(Transacao, "save", flaky_save):
            with self.assertRaises(ValidationError):
                criar_transferencia(
                    self.user,
                    conta_origem=self.conta_a,
                    conta_destino=self.conta_b,
                    valor=Decimal("10"),
                    data=date(2026, 1, 1),
                )
        self.assertEqual(Transacao.objects.filter(usuario=self.user).count(), antes)
        self.assertEqual(
            Transacao.objects.filter(usuario=self.user, tipo="transferencia").count(), 0
        )
        assert_saldo_conta(self.conta_a, Decimal("5000.00"))

    def test_falha_na_edicao_mantem_par_original(self):
        o, d = criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("50"),
            data=date(2026, 1, 1),
            descricao="original",
        )
        tid = o.transfer_id
        original_save = Transacao.save
        calls = {"n": 0}

        def flaky_save(self_tx, *args, **kwargs):
            calls["n"] += 1
            if self_tx.tipo == "transferencia" and calls["n"] >= 1:
                # primeira save da atualização falha
                raise ValidationError("falha forçada na edição")
            return original_save(self_tx, *args, **kwargs)

        with mock.patch.object(Transacao, "save", flaky_save):
            with self.assertRaises(ValidationError):
                atualizar_transferencia(
                    self.user,
                    tid,
                    valor=Decimal("999"),
                    descricao="nao deveria",
                )
        o2, d2 = _assert_par_integro(self.user, tid)
        self.assertEqual(o2.valor, Decimal("50"))
        self.assertEqual(d2.valor, Decimal("50"))
        self.assertEqual(o2.descricao, "original")


class TransferenciaRelatoriosRegressaoTests(TransferenciaQABase):
    def test_transferencia_nao_altera_pl_receita_despesa(self):
        from django.db.models import Sum

        base = Transacao.objects.filter(usuario=self.user)
        rec_antes = base.filter(tipo="receita").aggregate(t=Sum("valor"))["t"] or Decimal("0")
        desp_antes = base.filter(tipo="despesa").aggregate(t=Sum("valor"))["t"] or Decimal("0")

        criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("400"),
            data=date(2026, 6, 1),
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            tipo="despesa",
            valor=Decimal("50"),
            descricao="Despesa regressão",
            data=date(2026, 6, 2),
            categoria=self.cat_desp,
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            tipo="receita",
            valor=Decimal("20"),
            descricao="Receita regressão",
            data=date(2026, 6, 3),
            categoria=self.cat_rec,
        )

        rec = base.filter(tipo="receita").aggregate(t=Sum("valor"))["t"] or Decimal("0")
        desp = base.filter(tipo="despesa").aggregate(t=Sum("valor"))["t"] or Decimal("0")
        self.assertEqual(rec, rec_antes + Decimal("20"))
        self.assertEqual(desp, desp_antes + Decimal("50"))
        # Transferências não entram em receita/despesa
        self.assertEqual(
            base.filter(tipo="transferencia").aggregate(t=Sum("valor"))["t"],
            Decimal("800"),  # duas pernas de 400
        )
        assert_patrimonio_contas(self.user, Decimal("4970.00"))
        assert_saldo_consistente(self.user)
        _assert_sem_orfaos(self.user)


class TransferenciaDuploSubmitTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="qa-race@test.local", password="x", nome="Race"
        )
        self.a = Conta.objects.create(
            usuario=self.user, nome="A", tipo="corrente", ativa=True
        )
        self.b = Conta.objects.create(
            usuario=self.user, nome="B", tipo="poupanca", ativa=True
        )
        cat, _ = Categoria.objects.get_or_create(
            usuario=self.user, nome="R", tipo="receita", defaults={"ativa": True}
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.a,
            tipo="receita",
            valor=Decimal("1000"),
            descricao="base",
            data=date(2026, 1, 1),
            categoria=cat,
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_duplo_post_com_mesma_idempotency_key_cria_um_par(self):
        """Com X-Idempotency-Key, 2 POSTs = 1 transferência (2 pernas)."""
        key = str(uuid.uuid4())
        payload = {
            "conta_origem": self.a.id,
            "conta_destino": self.b.id,
            "valor": "10,00",
            "data": "2026-01-15",
            "descricao": "duplo",
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
            Transacao.objects.filter(usuario=self.user, tipo="transferencia").count(), 2
        )
        _assert_sem_orfaos(self.user)
        assert_patrimonio_contas(self.user, Decimal("1000.00"))
