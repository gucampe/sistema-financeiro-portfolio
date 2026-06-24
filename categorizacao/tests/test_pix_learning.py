from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from categorias.models import Categoria
from categorizacao.models import MemoriaMerchantUsuario
from categorizacao.services.learning import processar_feedback_transacao
from categorizacao.services.llm.gate import merge_predictions, should_invoke_llm
from categorizacao.services.memory_lookup import buscar_memoria_humana
from categorizacao.services.pipeline import _construir_contexto, classificar, sugerir
from categorizacao.services.pix_identity import (
    fingerprint_pix_person,
    is_pix_pessoa_fisica,
    keys_sao_similares,
)
from categorizacao.types import PredicaoCategorizacao
from contas.models import Conta
from transacoes.models import Transacao

User = get_user_model()

MATHEUS_FULL = "PIX ENVIADO                        Matheus Philip Ferreira R"
MATHEUS_CPF = "PIX ENVIADO                        54 017 824 Matheus Philip"


class PixIdentityTests(TestCase):
    def test_detecta_pix_pf(self):
        self.assertTrue(is_pix_pessoa_fisica(MATHEUS_FULL))
        self.assertFalse(is_pix_pessoa_fisica("PIX ENVIADO 99 FOOD LTDA"))

    def test_fingerprint_estavel_variantes_matheus(self):
        fp1 = fingerprint_pix_person(MATHEUS_FULL)
        fp2 = fingerprint_pix_person(MATHEUS_CPF)
        self.assertTrue(fp1.startswith("pix_person:"))
        self.assertIn("matheus", fp1)
        self.assertIn("matheus", fp2)
        self.assertTrue(keys_sao_similares(fp1, fp2))

    def test_merchant_keys_fragmentadas_sao_similares(self):
        class _U:
            pk = 1

        ctx_full = _construir_contexto(_U(), MATHEUS_FULL, "despesa")
        ctx_cpf = _construir_contexto(_U(), MATHEUS_CPF, "despesa")
        self.assertNotEqual(ctx_full.merchant_key, ctx_cpf.merchant_key)
        self.assertTrue(keys_sao_similares(ctx_full.pix_person_key, ctx_cpf.pix_person_key))


class HumanMemoryPriorityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="pix-learn@test.com",
            nome="Pix Learn",
            password="senha12345",
        )
        self.cat, _ = Categoria.objects.get_or_create(
            nome="Cuidados pessoais PIX",
            tipo="despesa",
            usuario=self.user,
            defaults={"ativa": True},
        )
        self.conta = Conta.objects.create(
            usuario=self.user,
            nome="Conta PIX",
            tipo="corrente",
            ativa=True,
        )
        MemoriaMerchantUsuario.objects.create(
            usuario=self.user,
            merchant_key=fingerprint_pix_person(MATHEUS_FULL),
            categoria=self.cat,
            confirmacoes=2,
            correcoes=0,
            score=1.0,
            origem="human",
        )

    def test_historico_reutiliza_variante_cpf(self):
        ctx = _construir_contexto(self.user, MATHEUS_CPF, "despesa", Decimal("45"))
        pred = classificar(ctx)
        self.assertIsNotNone(pred)
        self.assertEqual(pred.fonte, "historico")
        self.assertEqual(pred.categoria_nome, self.cat.nome)

    @override_settings(ENABLE_CATEGORIZACAO_LLM=True)
    def test_gate_bloqueia_llm_com_memoria_humana(self):
        ctx = _construir_contexto(self.user, MATHEUS_CPF, "despesa")
        pred = classificar(ctx)
        gate = should_invoke_llm(ctx, pred)
        self.assertFalse(gate.invoke)
        self.assertIn("human", gate.reason)

    def test_merge_nao_sobrescreve_historico(self):
        ctx = _construir_contexto(self.user, MATHEUS_FULL, "despesa")
        pred_h = PredicaoCategorizacao(
            categoria_id=self.cat.pk,
            categoria_nome=self.cat.nome,
            confianca=0.98,
            fonte="historico",
            merchant_key="matheus philip ferreira",
            explicacao="teste",
            contexto={"human_memory": True},
        )
        pred_llm = PredicaoCategorizacao(
            categoria_id=999,
            categoria_nome="Família",
            confianca=0.95,
            fonte="llm_gemini",
            merchant_key="x",
            explicacao="llm",
        )
        merged = merge_predictions(pred_h, pred_llm, ctx=ctx)
        self.assertEqual(merged.fonte, "historico")


class LearningSourceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="learn-src@test.com",
            nome="Learn Src",
            password="senha12345",
        )
        self.cat_a, _ = Categoria.objects.get_or_create(
            nome="Cat A",
            tipo="despesa",
            usuario=self.user,
            defaults={"ativa": True},
        )
        self.cat_b, _ = Categoria.objects.get_or_create(
            nome="Cat B",
            tipo="despesa",
            usuario=self.user,
            defaults={"ativa": True},
        )
        self.conta = Conta.objects.create(
            usuario=self.user,
            nome="Conta",
            tipo="corrente",
            ativa=True,
        )

    def _tx(self, descricao: str, categoria) -> Transacao:
        return Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=categoria,
            tipo="despesa",
            valor=Decimal("10"),
            data="2026-01-01",
            descricao=descricao,
        )

    def test_import_passivo_llm_nao_reforca_memoria(self):
        tx = self._tx(MATHEUS_FULL, self.cat_b)
        MemoriaMerchantUsuario.objects.filter(usuario=self.user).delete()
        processar_feedback_transacao(
            usuario=self.user,
            transacao=tx,
            descricao=MATHEUS_FULL,
            categoria_final=self.cat_b,
            categoria_sugerida_id=self.cat_b.pk,
            fonte="llm_gemini",
        )
        mem = MemoriaMerchantUsuario.objects.filter(usuario=self.user).first()
        self.assertIsNone(mem)

    def test_correcao_llm_gera_memoria_humana(self):
        tx = self._tx(MATHEUS_FULL, self.cat_a)
        processar_feedback_transacao(
            usuario=self.user,
            transacao=tx,
            descricao=MATHEUS_FULL,
            categoria_final=self.cat_a,
            categoria_sugerida_id=self.cat_b.pk,
            fonte="llm_gemini",
        )
        mem, _ = buscar_memoria_humana(_construir_contexto(self.user, MATHEUS_FULL, "despesa"))
        self.assertIsNotNone(mem)
        self.assertGreaterEqual(mem.confirmacoes, 1)
        self.assertEqual(mem.origem, "human")

    def test_cadastro_manual_gera_memoria(self):
        tx = self._tx(MATHEUS_FULL, self.cat_a)
        processar_feedback_transacao(
            usuario=self.user,
            transacao=tx,
            descricao=MATHEUS_FULL,
            categoria_final=self.cat_a,
        )
        mem = MemoriaMerchantUsuario.objects.filter(usuario=self.user).first()
        self.assertIsNotNone(mem)
        self.assertGreaterEqual(mem.confirmacoes, 1)


class PixColdStartConservativeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="cold@test.com",
            nome="Cold",
            password="senha12345",
        )

    @override_settings(ENABLE_CATEGORIZACAO_LLM=True)
    @patch("categorizacao.services.llm.orchestrator._invoke_llm")
    def test_llm_pix_nao_preenche_automaticamente(self, mock_llm):
        from categorias.models import Categoria

        cat, _ = Categoria.objects.get_or_create(
            nome="Diversos Cold",
            tipo="despesa",
            usuario=self.user,
            defaults={"ativa": True},
        )
        mock_llm.return_value = PredicaoCategorizacao(
            categoria_id=cat.pk,
            categoria_nome=cat.nome,
            confianca=0.7,
            fonte="llm_gemini",
            merchant_key="x",
            explicacao="sugestão IA",
        )
        sug = sugerir(self.user, MATHEUS_CPF, "despesa")
        self.assertIsNotNone(sug)
        self.assertEqual(sug.fonte, "llm_gemini")
        self.assertTrue(sug.contexto.get("requires_user_confirmation"))
        self.assertFalse(sug.auto_aplicar)
