"""
Property-based tests — invariantes do ledger de importação.
"""

from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from categorias.models import Categoria
from contas.models import Conta
from transacoes.models import Transacao
from transacoes.ofx_parse import parse_ofx_bytes
from transacoes.tests.helpers.import_expectativa import expectativa_importacao
from transacoes.tests.helpers.import_fixtures import build_ofx_bytes
from transacoes.tests.helpers.import_pipeline import (
    confirmar,
    importar_ofx_completo,
    linhas_confirmar_padrao_ui,
    preview_ofx,
)
from transacoes.tests.helpers.ledger_invariants import (
    assert_isolamento_contas,
    assert_ledger_invariants,
    snapshot_conta,
    snapshot_usuario,
)

User = get_user_model()

_PROPERTY_RUNS = 24


@pytest.mark.importacao_avancada
class ImportInvariantsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="inv-import@test.local", password="x", nome="Inv"
        )
        cls.conta_a = Conta.objects.create(
            usuario=cls.user, nome="Inv A", tipo="corrente", ativa=True
        )
        cls.conta_b = Conta.objects.create(
            usuario=cls.user, nome="Inv B", tipo="poupanca", ativa=True
        )
        cls.cat_d = Categoria.objects.create(
            usuario=cls.user, nome="Desp Inv", tipo="despesa", cor="#EF4444", ativa=True
        )
        cls.cat_r = Categoria.objects.create(
            usuario=cls.user, nome="Rec Inv", tipo="receita", cor="#10B981", ativa=True
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.client.force_login(self.user)
        self.rng = random.Random(99)

    def _build_random_ofx(self, n: int, *, prefix: str) -> bytes:
        txs = []
        for i in range(n):
            txs.append(
                {
                    "fitid": f"{prefix}-{i}",
                    "trnamt": self.rng.choice(["-10.00", "-25.00", "50.00"]),
                    "name": f"Prop {prefix} {i}",
                    "dtposted": f"2024{(i % 12) + 1:02d}15120000",
                }
            )
        return build_ofx_bytes(txs)

    def test_invariante_1_idempotencia_reimport(self):
        """Reimportar mesmo arquivo → mesma contagem, zero novas."""
        for run in range(_PROPERTY_RUNS):
            prefix = f"idemp-{run}"
            n = self.rng.randint(2, 8)
            raw = self._build_random_ofx(n, prefix=prefix)
            Transacao.objects.filter(conta=self.conta_a).delete()

            st, body, _ = importar_ofx_completo(
                self.client,
                self.conta_a,
                raw,
                categoria_despesa_id=self.cat_d.id,
                categoria_receita_id=self.cat_r.id,
            )
            self.assertEqual(st, 200, body)
            snap_1 = snapshot_conta(self.conta_a)
            count_1 = snap_1["count"]

            linhas = parse_ofx_bytes(raw)
            exp = expectativa_importacao(self.user, self.conta_a, linhas)
            self.assertEqual(exp["criadas_se_confirmar_padrao_ui"], 0)

            st2, body2, linhas2 = importar_ofx_completo(
                self.client,
                self.conta_a,
                raw,
                categoria_despesa_id=self.cat_d.id,
                categoria_receita_id=self.cat_r.id,
            )
            self.assertEqual(st2, 200, body2)
            self.assertEqual(linhas2, [])
            self.assertEqual(body2.get("criadas"), 0)

            snap_2 = snapshot_conta(self.conta_a)
            self.assertEqual(snap_2["count"], count_1)
            self.assertEqual(snap_2["ledger"], snap_1["ledger"])
            self.assertEqual(snap_2["saldo"], snap_1["saldo"])
            assert_ledger_invariants(self.user, contas=[self.conta_a])

    def test_invariante_2_conservacao_saldo(self):
        """Após cada importação aleatória, saldo == soma tipada."""
        for run in range(_PROPERTY_RUNS):
            raw = self._build_random_ofx(self.rng.randint(1, 6), prefix=f"saldo-{run}")
            importar_ofx_completo(
                self.client,
                self.conta_a,
                raw,
                categoria_despesa_id=self.cat_d.id,
                categoria_receita_id=self.cat_r.id,
            )
            assert_ledger_invariants(self.user, contas=[self.conta_a])

    def test_invariante_3_isolamento_contas(self):
        """Import em conta_a não altera conta_b."""
        snap_antes = snapshot_usuario(self.user, contas=[self.conta_a, self.conta_b])
        for run in range(12):
            raw = self._build_random_ofx(self.rng.randint(1, 5), prefix=f"iso-{run}")
            importar_ofx_completo(
                self.client,
                self.conta_a,
                raw,
                categoria_despesa_id=self.cat_d.id,
                categoria_receita_id=self.cat_r.id,
            )
            assert_isolamento_contas(
                self.user,
                self.conta_a,
                [self.conta_b],
                snap_antes,
            )
        assert_ledger_invariants(self.user)

    def test_invariante_4_rollback_total(self):
        """Erro no batch → count inalterado."""
        raw = self._build_random_ofx(2, prefix="rb")
        importar_ofx_completo(
            self.client,
            self.conta_a,
            raw,
            categoria_despesa_id=self.cat_d.id,
            categoria_receita_id=self.cat_r.id,
        )
        count_antes = Transacao.objects.filter(conta=self.conta_a).count()

        st, _ = confirmar(
            self.client,
            self.conta_a,
            [
                {
                    "indice": 0,
                    "data": "2024-01-01",
                    "valor": "1.00",
                    "tipo": "despesa",
                    "descricao": "Boa",
                    "categoria_id": self.cat_d.id,
                },
                {
                    "indice": 1,
                    "data": "2024-99-99",
                    "valor": "2.00",
                    "tipo": "despesa",
                    "descricao": "Ruim",
                    "categoria_id": self.cat_d.id,
                },
            ],
        )
        self.assertEqual(st, 400)
        self.assertEqual(
            Transacao.objects.filter(conta=self.conta_a).count(),
            count_antes,
        )
        assert_ledger_invariants(self.user)

    def test_invariante_dup_nao_duplica_saldo(self):
        """Duplicatas no preview não aumentam saldo ao reimportar."""
        seed_tx = {
            "fitid": "prop-dup-seed",
            "trnamt": "-77.00",
            "name": "Seed Dup",
            "dtposted": "20240301120000",
        }
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            categoria=self.cat_d,
            tipo="despesa",
            valor=Decimal("77.00"),
            data=date(2024, 3, 1),
            descricao="Seed Dup",
            ofx_fitid="prop-dup-seed",
        )
        saldo_antes = self.conta_a.saldo_atual_calc
        raw = build_ofx_bytes([seed_tx])
        status, preview = preview_ofx(self.client, self.conta_a, raw)
        self.assertEqual(status, 200)
        linhas = linhas_confirmar_padrao_ui(
            preview,
            categoria_despesa_id=self.cat_d.id,
            categoria_receita_id=self.cat_r.id,
        )
        self.assertEqual(linhas, [])
        st, body = confirmar(self.client, self.conta_a, linhas)
        self.assertEqual(st, 200)
        self.assertEqual(body.get("criadas"), 0)
        self.conta_a.refresh_from_db()
        self.assertEqual(self.conta_a.saldo_atual_calc, saldo_antes)
        assert_ledger_invariants(self.user)
