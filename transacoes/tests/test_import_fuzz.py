"""
Fuzz testing de importação OFX/XLSX — invariantes nunca podem quebrar.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from ofxparse import OfxParserException

from categorias.models import Categoria
from contas.models import Conta
from transacoes.models import Transacao
from transacoes.ofx_parse import parse_ofx_bytes
from transacoes.tests.helpers.fuzz_generators import ImportFuzzGenerator
from transacoes.tests.helpers.import_pipeline import (
    confirmar,
    importar_ofx_completo,
    linhas_confirmar_padrao_ui,
    preview_ofx,
    preview_xlsx,
)
from transacoes.tests.helpers.ledger_invariants import (
    assert_ledger_invariants,
    snapshot_usuario,
)
from transacoes.xlsx_parse import parse_planilha_padrao_bytes

User = get_user_model()

_FUZZ_ITERATIONS = 60
_ALLOWED_PARSE_ERRORS = (ValueError, OfxParserException, UnicodeDecodeError)


@pytest.mark.importacao_avancada
class ImportFuzzTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="fuzz-import@test.local", password="x", nome="Fuzz"
        )
        cls.conta = Conta.objects.create(
            usuario=cls.user, nome="Conta Fuzz", tipo="corrente", ativa=True
        )
        cls.conta_b = Conta.objects.create(
            usuario=cls.user, nome="Conta Fuzz B", tipo="poupanca", ativa=True
        )
        cls.cat_d = Categoria.objects.create(
            usuario=cls.user, nome="Desp Fuzz", tipo="despesa", cor="#EF4444", ativa=True
        )
        cls.cat_r = Categoria.objects.create(
            usuario=cls.user, nome="Rec Fuzz", tipo="receita", cor="#10B981", ativa=True
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.client.force_login(self.user)
        self.gen = ImportFuzzGenerator(seed=42)

    def _count_conta(self) -> int:
        return Transacao.objects.filter(conta=self.conta).count()

    def test_fuzz_ofx_xlsx_invariantes(self):
        """Entradas aleatórias não quebram invariantes nem criam persistência parcial."""
        for kind, raw in self.gen.iter_cases(_FUZZ_ITERATIONS):
            snap_antes = snapshot_usuario(self.user, contas=[self.conta, self.conta_b])
            count_antes = self._count_conta()

            # --- parse direto (nunca exceção não tratada) ---
            if kind.startswith("ofx"):
                try:
                    parse_ofx_bytes(raw)
                except _ALLOWED_PARSE_ERRORS:
                    pass
                except Exception as exc:
                    self.fail(f"parse_ofx_bytes exceção inesperada ({kind}): {exc}")
            else:
                try:
                    parse_planilha_padrao_bytes(raw)
                except (ValueError, Exception) as exc:
                    if not isinstance(exc, ValueError):
                        self.fail(f"parse_planilha exceção inesperada ({kind}): {exc}")

            # --- preview HTTP (200 ou 400, nunca 500) ---
            if kind.startswith("ofx"):
                status, body = preview_ofx(self.client, self.conta, raw)
            else:
                status, body = preview_xlsx(self.client, self.conta, raw)

            self.assertIn(status, (200, 400), f"status inesperado {status} ({kind})")
            self.assertNotEqual(status, 500)

            if status == 200 and body.get("status") == "ok":
                linhas = linhas_confirmar_padrao_ui(
                    body,
                    categoria_despesa_id=self.cat_d.id,
                    categoria_receita_id=self.cat_r.id,
                )
                st_conf, body_conf = confirmar(self.client, self.conta, linhas)
                self.assertIn(st_conf, (200, 400))
                if st_conf == 400:
                    self.assertEqual(self._count_conta(), count_antes)

            else:
                self.assertEqual(self._count_conta(), count_antes)

            assert_ledger_invariants(self.user, contas=[self.conta, self.conta_b])
            snap_depois_b = snapshot_usuario(self.user, contas=[self.conta_b])
            self.assertEqual(snap_antes[self.conta_b.pk], snap_depois_b[self.conta_b.pk])

    def test_fuzz_confirmar_invalido_rollback_total(self):
        """Lote inválido nunca persiste parcialmente."""
        raw = self.gen.ofx_valid(3, prefix="rollback")
        importar_ofx_completo(
            self.client,
            self.conta,
            raw,
            categoria_despesa_id=self.cat_d.id,
            categoria_receita_id=self.cat_r.id,
        )
        count_ok = self._count_conta()

        for valor_ruim in ("nao-num", "", "-5.00", "x"):
            st, _ = confirmar(
                self.client,
                self.conta,
                [
                    {
                        "indice": 0,
                        "data": "2024-01-01",
                        "valor": "10.00",
                        "tipo": "despesa",
                        "descricao": "OK",
                        "categoria_id": self.cat_d.id,
                    },
                    {
                        "indice": 1,
                        "data": "data-ruim",
                        "valor": valor_ruim,
                        "tipo": "despesa",
                        "descricao": "Ruim",
                        "categoria_id": self.cat_d.id,
                    },
                ],
            )
            self.assertEqual(st, 400)
            self.assertEqual(self._count_conta(), count_ok)

        assert_ledger_invariants(self.user)
