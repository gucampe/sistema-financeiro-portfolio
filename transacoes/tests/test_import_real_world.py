"""
Real-world imports — parsers normalizam ou rejeitam com erro controlado.
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
from transacoes.tests.helpers.import_fixtures import (
    build_ofx_real_world_latin1,
    build_ofx_real_world_messy,
    build_xlsx_real_world_missing_header_col,
    build_xlsx_real_world_messy,
)
from transacoes.tests.helpers.import_pipeline import (
    importar_ofx_completo,
    preview_ofx,
    preview_xlsx,
)
from transacoes.tests.helpers.ledger_invariants import assert_ledger_invariants
from transacoes.xlsx_parse import parse_planilha_padrao_bytes

User = get_user_model()


@pytest.mark.importacao_avancada
class ImportRealWorldTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="rw-import@test.local", password="x", nome="RW"
        )
        cls.conta = Conta.objects.create(
            usuario=cls.user, nome="Conta RW", tipo="corrente", ativa=True
        )
        cls.cat_d = Categoria.objects.create(
            usuario=cls.user, nome="Desp RW", tipo="despesa", cor="#EF4444", ativa=True
        )
        cls.cat_r = Categoria.objects.create(
            usuario=cls.user, nome="Rec RW", tipo="receita", cor="#10B981", ativa=True
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.client.force_login(self.user)

    def test_ofx_messy_parse_normaliza_ou_rejeita(self):
        raw = build_ofx_real_world_messy()
        try:
            linhas = parse_ofx_bytes(raw)
        except (ValueError, OfxParserException) as exc:
            self.fail(f"OFX messy deveria parsear: {exc}")
        self.assertEqual(len(linhas), 3)
        datas = [ln.data for ln in linhas]
        self.assertEqual(len(set(datas)), 3)

    def test_ofx_messy_pipeline_completo(self):
        raw = build_ofx_real_world_messy()
        st, body, linhas = importar_ofx_completo(
            self.client,
            self.conta,
            raw,
            categoria_despesa_id=self.cat_d.id,
            categoria_receita_id=self.cat_r.id,
        )
        self.assertEqual(st, 200, body)
        self.assertEqual(body.get("criadas"), len(linhas))
        self.assertEqual(Transacao.objects.filter(conta=self.conta).count(), len(linhas))
        assert_ledger_invariants(self.user, contas=[self.conta])

    def test_ofx_latin1_encoding(self):
        raw = build_ofx_real_world_latin1()
        try:
            linhas = parse_ofx_bytes(raw)
        except (ValueError, OfxParserException, UnicodeDecodeError):
            status, preview = preview_ofx(self.client, self.conta, raw)
            self.assertEqual(status, 400)
            return
        self.assertGreaterEqual(len(linhas), 1)
        status, preview = preview_ofx(self.client, self.conta, raw)
        self.assertIn(status, (200, 400))
        if status == 200:
            assert_ledger_invariants(self.user, contas=[self.conta])

    def test_xlsx_messy_parse_e_preview(self):
        raw = build_xlsx_real_world_messy()
        linhas = parse_planilha_padrao_bytes(raw)
        self.assertEqual(len(linhas), 3)
        status, preview = preview_xlsx(self.client, self.conta, raw)
        self.assertEqual(status, 200)
        self.assertEqual(len(preview["linhas"]), 3)

        from transacoes.tests.helpers.import_pipeline import (
            confirmar,
            linhas_confirmar_padrao_ui,
        )

        linhas_conf = linhas_confirmar_padrao_ui(
            preview,
            categoria_despesa_id=self.cat_d.id,
            categoria_receita_id=self.cat_r.id,
        )
        st, body = confirmar(self.client, self.conta, linhas_conf)
        self.assertEqual(st, 200)
        self.assertEqual(body.get("criadas"), 3)
        assert_ledger_invariants(self.user, contas=[self.conta])

    def test_xlsx_linha_invalida_rejeita_completo(self):
        raw = build_xlsx_real_world_missing_header_col()
        with self.assertRaises(ValueError):
            parse_planilha_padrao_bytes(raw)
        count_antes = Transacao.objects.filter(conta=self.conta).count()
        status, _ = preview_xlsx(self.client, self.conta, raw)
        self.assertEqual(status, 400)
        self.assertEqual(Transacao.objects.filter(conta=self.conta).count(), count_antes)
        assert_ledger_invariants(self.user, contas=[self.conta])
