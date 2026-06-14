"""GLOB-U-01..09 — Fluxos cross-app globais (conta corrente)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categorias.models import Categoria
from contas.models import Conta
from financial_contracts.saldo_contracts import assert_exclusao_reverte_saldo
from relatorios.models import OrcamentoCategoria
from relatorios.tests.helpers.ecossistema import (
    assert_delta_ecossistema,
    assert_ecossistema_coerente,
    snapshot_ecossistema,
)
from transacoes.models import Transacao
from transacoes.services import criar_transacao_saldo_inicial
from usuarios.tests.helpers.seguranca_fixtures import client_csrf_strict, csrf_token

User = get_user_model()


@pytest.mark.ecossistema
class GlobEcossistemaUnitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="glob-u@test.local", nome="Glob U", password="x"
        )
        self.conta = Conta.objects.create(
            usuario=self.user, nome="Conta Glob", tipo="corrente", ativa=True
        )
        self.hoje = timezone.localdate()
        self.inicio_mes = self.hoje.replace(day=1)
        criar_transacao_saldo_inicial(
            self.user, self.conta, Decimal("1000.00"), self.inicio_mes
        )
        self.cat_desp = Categoria.objects.create(
            usuario=self.user,
            nome="Glob Despesa",
            tipo="despesa",
            ativa=True,
            cor="#EF4444",
        )
        self.cat_rec = Categoria.objects.create(
            usuario=self.user,
            nome="Glob Receita",
            tipo="receita",
            ativa=True,
            cor="#10B981",
        )
        self.cat_alt = Categoria.objects.create(
            usuario=self.user,
            nome="Glob Despesa Alt",
            tipo="despesa",
            ativa=True,
            cor="#6366F1",
        )
        OrcamentoCategoria.objects.create(
            usuario=self.user,
            categoria=self.cat_desp,
            valor_planejado=Decimal("500.00"),
            ativo=True,
        )
        OrcamentoCategoria.objects.create(
            usuario=self.user,
            categoria=self.cat_alt,
            valor_planejado=Decimal("300.00"),
            ativo=True,
        )

    def _snap(self, categoria=None, categoria_b=None):
        return snapshot_ecossistema(
            self.user,
            conta=self.conta,
            categoria=categoria or self.cat_desp,
            categoria_b=categoria_b,
        )

    def test_glob_u_08_baseline_vazio_coerente(self):
        """Baseline: só saldo inicial — ecossistema coerente."""
        snap = self._snap()
        assert_ecossistema_coerente(snap)
        self.assertEqual(snap.receitas, Decimal("0"))
        self.assertEqual(snap.despesas, Decimal("0"))
        self.assertEqual(snap.orc_realizado, Decimal("0"))

    def test_glob_u_01_criar_despesa_reflexo_global(self):
        antes = self._snap()
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("80.00"),
            data=self.hoje,
            descricao="GLOB-U-01",
        )
        depois = self._snap()
        assert_delta_ecossistema(
            antes,
            depois,
            delta_despesas=Decimal("80.00"),
            delta_saldo=Decimal("-80.00"),
            delta_orc=Decimal("80.00"),
            delta_cat_linha=Decimal("80.00"),
        )

    def test_glob_u_02_criar_receita_reflexo_global(self):
        antes = self._snap()
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("200.00"),
            data=self.hoje,
            descricao="GLOB-U-02",
        )
        depois = self._snap()
        assert_delta_ecossistema(
            antes,
            depois,
            delta_receitas=Decimal("200.00"),
            delta_saldo=Decimal("200.00"),
            delta_orc=Decimal("0"),
            delta_cat_linha=Decimal("0"),
        )

    def test_glob_u_03_encadeamento_coerente_apos_despesa(self):
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("50.00"),
            data=self.hoje,
            descricao="GLOB-U-03",
        )
        snap = self._snap()
        assert_ecossistema_coerente(snap)

    def test_glob_u_04_editar_valor_reflexo_global(self):
        tx = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("30.00"),
            data=self.hoje,
            descricao="GLOB-U-04",
        )
        antes = self._snap()
        tx.valor = Decimal("55.00")
        tx.save(update_fields=["valor"])
        depois = self._snap()
        assert_delta_ecossistema(
            antes,
            depois,
            delta_despesas=Decimal("25.00"),
            delta_saldo=Decimal("-25.00"),
            delta_orc=Decimal("25.00"),
            delta_cat_linha=Decimal("25.00"),
        )

    def test_glob_u_05_editar_categoria_reflexo_global(self):
        tx = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("40.00"),
            data=self.hoje,
            descricao="GLOB-U-05",
        )
        antes = self._snap(categoria_b=self.cat_alt)
        tx.categoria = self.cat_alt
        tx.save(update_fields=["categoria"])
        depois = self._snap(categoria_b=self.cat_alt)
        assert_delta_ecossistema(
            antes,
            depois,
            delta_despesas=Decimal("0"),
            delta_saldo=Decimal("0"),
            delta_orc=Decimal("-40.00"),
            delta_cat_linha=Decimal("-40.00"),
            delta_orc_b=Decimal("40.00"),
            delta_cat_linha_b=Decimal("40.00"),
        )

    def test_glob_u_06_excluir_despesa_reflexo_global(self):
        tx = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("22.00"),
            data=self.hoje,
            descricao="GLOB-U-06",
        )
        antes = self._snap()
        tx.delete()
        depois = self._snap()
        assert_delta_ecossistema(
            antes,
            depois,
            delta_despesas=Decimal("-22.00"),
            delta_saldo=Decimal("22.00"),
            delta_orc=Decimal("-22.00"),
            delta_cat_linha=Decimal("-22.00"),
        )
        assert_exclusao_reverte_saldo(self.conta, antes.saldo_conta + Decimal("22.00"))

    def test_glob_u_07_excluir_receita_reflexo_global(self):
        tx = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("75.00"),
            data=self.hoje,
            descricao="GLOB-U-07",
        )
        antes = self._snap()
        tx.delete()
        depois = self._snap()
        assert_delta_ecossistema(
            antes,
            depois,
            delta_receitas=Decimal("-75.00"),
            delta_saldo=Decimal("-75.00"),
            delta_orc=Decimal("0"),
            delta_cat_linha=Decimal("0"),
        )

    def test_glob_u_09_excluir_via_http_reflexo_global(self):
        tx = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("33.00"),
            data=self.hoje,
            descricao="GLOB-U-09",
        )
        antes = self._snap()
        client = client_csrf_strict(self.user)
        token = csrf_token(client)
        url = reverse("transacoes:excluir", kwargs={"pk": tx.pk})
        resp = client.post(url, {"csrfmiddlewaretoken": token})
        self.assertEqual(resp.status_code, 302)
        depois = self._snap()
        assert_delta_ecossistema(
            antes,
            depois,
            delta_despesas=Decimal("-33.00"),
            delta_saldo=Decimal("33.00"),
            delta_orc=Decimal("-33.00"),
            delta_cat_linha=Decimal("-33.00"),
        )
