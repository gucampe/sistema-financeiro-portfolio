"""
Concorrência de importação — dois confirms simultâneos na mesma conta.
"""

from __future__ import annotations

import json
import threading
import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TransactionTestCase
from django.urls import reverse

from categorias.models import Categoria
from contas.models import Conta
from financial_contracts.saldo_contracts import calcular_saldo_esperado
from transacoes.models import Transacao
from transacoes.tests.helpers.import_fixtures import build_ofx_concorrente
from transacoes.tests.helpers.import_pipeline import (
    linhas_confirmar_padrao_ui,
    preview_ofx,
)
from transacoes.tests.helpers.ledger_invariants import assert_ledger_invariants

User = get_user_model()

_N_TX = 12


@pytest.mark.importacao_avancada
@pytest.mark.concurrency
class ImportConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="conc-import@test.local", password="x", nome="Conc"
        )
        self.conta = Conta.objects.create(
            usuario=self.user, nome="Conta Conc", tipo="corrente", ativa=True
        )
        self.cat_d = Categoria.objects.create(
            usuario=self.user, nome="Desp Conc", tipo="despesa", cor="#EF4444", ativa=True
        )
        self.cat_r = Categoria.objects.create(
            usuario=self.user, nome="Rec Conc", tipo="receita", cor="#10B981", ativa=True
        )
        self.raw = build_ofx_concorrente(_N_TX, prefix="conc-unit")
        self.url_confirmar = reverse("transacoes:importar_ofx_confirmar")

    def _client_logado(self) -> Client:
        c = Client(enforce_csrf_checks=False)
        c.force_login(self.user)
        return c

    def test_concorrencia_dois_confirms_mesma_conta(self):
        """Dois threads confirmam o mesmo preview — no máximo N transações, saldo determinístico."""
        client = self._client_logado()
        status, preview = preview_ofx(client, self.conta, self.raw)
        self.assertEqual(status, 200)
        linhas = linhas_confirmar_padrao_ui(
            preview,
            categoria_despesa_id=self.cat_d.id,
            categoria_receita_id=self.cat_r.id,
        )
        self.assertEqual(len(linhas), _N_TX)

        count_antes = Transacao.objects.filter(conta=self.conta).count()
        saldo_antes = calcular_saldo_esperado(self.conta)
        payload = json.dumps({"conta_id": self.conta.pk, "linhas": linhas})
        resultados: list[tuple[int, dict]] = []
        lock = threading.Lock()

        def _confirmar_thread():
            c = self._client_logado()
            r = c.post(
                self.url_confirmar,
                data=payload,
                content_type="application/json",
            )
            try:
                body = r.json()
            except Exception:
                body = {"status": "error"}
            with lock:
                resultados.append((r.status_code, body))

        t1 = threading.Thread(target=_confirmar_thread)
        t2 = threading.Thread(target=_confirmar_thread)
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)
        self.assertFalse(t1.is_alive())
        self.assertFalse(t2.is_alive())

        count_depois = Transacao.objects.filter(conta=self.conta).count()
        criadas = count_depois - count_antes

        self.assertGreaterEqual(criadas, 1)
        self.assertLessEqual(criadas, _N_TX)

        ok_count = sum(1 for st, b in resultados if st == 200 and b.get("status") == "ok")
        err_count = len(resultados) - ok_count
        self.assertGreaterEqual(ok_count, 1)
        if err_count:
            for st, b in resultados:
                if st == 400:
                    self.assertIn(b.get("status"), ("error", None))

        self.conta.refresh_from_db()
        saldo_depois = calcular_saldo_esperado(self.conta)
        txs_novas = Transacao.objects.filter(conta=self.conta).order_by("pk")[
            count_antes:
        ]
        delta_real = sum(
            t.valor if t.tipo == "receita" else -t.valor if t.tipo == "despesa" else t.valor
            for t in txs_novas
        )
        self.assertEqual(saldo_depois, saldo_antes + delta_real)

        assert_ledger_invariants(self.user, contas=[self.conta])

        fitids = list(
            Transacao.objects.filter(conta=self.conta)
            .exclude(ofx_fitid__isnull=True)
            .values_list("ofx_fitid", flat=True)
        )
        self.assertEqual(len(fitids), len(set(fitids)))
