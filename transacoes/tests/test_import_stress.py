"""
Ledger Stress Test — volume alto, batches sequenciais, reimport repetido.
"""

from __future__ import annotations

import time

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from categorias.models import Categoria
from contas.models import Conta
from transacoes.models import Transacao
from transacoes.ofx_duplicatas import avaliar_duplicatas_importacao
from transacoes.ofx_parse import parse_ofx_bytes
from transacoes.tests.helpers.import_fixtures import build_ofx_bytes
from transacoes.tests.helpers.import_pipeline import importar_ofx_completo
from transacoes.tests.helpers.ledger_invariants import (
    assert_ledger_invariants,
    snapshot_conta,
)
from transacoes.views import _MAX_LINHAS_IMPORT_OFX

User = get_user_model()

_PARSE_10K_BUDGET_S = 45.0
_PIPELINE_2K_BUDGET_S = 60.0
_REIMPORT_ROUNDS = 10


def _build_n_tx(n: int, *, prefix: str) -> bytes:
    txs = []
    for i in range(n):
        txs.append(
            {
                "fitid": f"{prefix}-{i:05d}",
                "trnamt": f"-{(i % 50) + 1}.00",
                "name": f"Stress {prefix} {i}",
                "dtposted": f"2024{(i % 12) + 1:02d}15120000",
            }
        )
    return build_ofx_bytes(txs)


@pytest.mark.importacao_avancada
@pytest.mark.performance_extended
class ImportStressTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="stress-import@test.local", password="x", nome="Stress"
        )
        cls.conta = Conta.objects.create(
            usuario=cls.user, nome="Conta Stress", tipo="corrente", ativa=True
        )
        cls.cat_d = Categoria.objects.create(
            usuario=cls.user, nome="Desp Stress", tipo="despesa", cor="#EF4444", ativa=True
        )
        cls.cat_r = Categoria.objects.create(
            usuario=cls.user, nome="Rec Stress", tipo="receita", cor="#10B981", ativa=True
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.client.force_login(self.user)

    def test_stress_parse_10k_linhas(self):
        """Parser OFX aguenta 10k linhas sem exceção não tratada."""
        raw = _build_n_tx(10_000, prefix="parse10k")
        t0 = time.monotonic()
        linhas = parse_ofx_bytes(raw)
        elapsed = time.monotonic() - t0
        self.assertEqual(len(linhas), 10_000)
        self.assertLess(elapsed, _PARSE_10K_BUDGET_S, f"parse 10k lento: {elapsed:.2f}s")

    def test_stress_dup_evaluation_5k(self):
        """Avaliação REGRA-DUP em 5k linhas mantém consistência."""
        raw = _build_n_tx(5_000, prefix="dup5k")
        linhas = parse_ofx_bytes(raw)
        t0 = time.monotonic()
        dups = avaliar_duplicatas_importacao(self.user, self.conta, linhas)
        elapsed = time.monotonic() - t0
        self.assertEqual(len(dups), 5_000)
        self.assertFalse(any(d.duplicata_por_fitid for d in dups))
        self.assertLess(elapsed, 30.0, f"dup 5k lento: {elapsed:.2f}s")

    def test_stress_pipeline_2000_reimport_10x(self):
        """Pipeline completo no limite (2000) + 10 reimports sem crescimento."""
        raw = _build_n_tx(_MAX_LINHAS_IMPORT_OFX, prefix="full2k")
        t0 = time.monotonic()
        st, body, linhas = importar_ofx_completo(
            self.client,
            self.conta,
            raw,
            categoria_despesa_id=self.cat_d.id,
            categoria_receita_id=self.cat_r.id,
        )
        elapsed = time.monotonic() - t0
        self.assertEqual(st, 200, body)
        self.assertEqual(body.get("criadas"), len(linhas))
        self.assertEqual(len(linhas), _MAX_LINHAS_IMPORT_OFX)
        self.assertLess(elapsed, _PIPELINE_2K_BUDGET_S)

        snap = snapshot_conta(self.conta)
        for r in range(_REIMPORT_ROUNDS):
            st2, body2, linhas2 = importar_ofx_completo(
                self.client,
                self.conta,
                raw,
                categoria_despesa_id=self.cat_d.id,
                categoria_receita_id=self.cat_r.id,
            )
            self.assertEqual(st2, 200, f"reimport round {r}: {body2}")
            self.assertEqual(linhas2, [])
            self.assertEqual(body2.get("criadas"), 0)

        snap_final = snapshot_conta(self.conta)
        self.assertEqual(snap_final["count"], snap["count"])
        self.assertEqual(snap_final["ledger"], snap["ledger"])
        self.assertEqual(snap_final["saldo"], snap["saldo"])
        assert_ledger_invariants(self.user, contas=[self.conta])

    def test_stress_batches_sequenciais_5k_total(self):
        """5 batches de 1000 linhas = 5000 TX sem duplicação crescente."""
        total_esperado = 0
        for batch in range(5):
            raw = _build_n_tx(1000, prefix=f"batch{batch}")
            st, body, linhas = importar_ofx_completo(
                self.client,
                self.conta,
                raw,
                categoria_despesa_id=self.cat_d.id,
                categoria_receita_id=self.cat_r.id,
            )
            self.assertEqual(st, 200, body)
            total_esperado += len(linhas)
            self.assertEqual(
                Transacao.objects.filter(conta=self.conta).count(),
                total_esperado,
            )
            assert_ledger_invariants(self.user, contas=[self.conta])

        self.assertEqual(total_esperado, 5000)
