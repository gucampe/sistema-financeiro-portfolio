from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from categorias.models import Categoria
from categorizacao.models import MemoriaMerchantUsuario, MerchantGlobal, RegraCategorizacao
from categorizacao.services.learning import processar_feedback_transacao
from categorizacao.services.normalizer import extrair_merchant_key, normalizar_texto, preparar_descricao
from categorizacao.services.pipeline import sugerir
from contas.models import Conta
from transacoes.models import Transacao

User = get_user_model()


class NormalizerTests(TestCase):
    def test_normalizar_remove_ruido_bancario(self):
        raw = "COMPRA CARTAO - IFOOD *PIZZARIA SAO PAULO BR"
        norm = normalizar_texto(raw)
        self.assertIn("IFOOD", norm)
        self.assertNotIn("COMPRA CARTAO", norm)

    def test_merchant_key_ifood(self):
        norm, key = preparar_descricao("DEBITO IFOOD COM BR")
        self.assertIn("ifood", key)


class PipelineFuzzyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="cat@test.com",
            nome="Cat Test",
            password="senha12345",
        )
        Categoria.objects.get_or_create(
            nome="Alimentação",
            tipo="despesa",
            padrao=True,
            defaults={"ativa": True},
        )
        MerchantGlobal.objects.create(
            canonical_name="ifood",
            aliases=["ifood", "ifood.com"],
            categoria_padrao_nome="Alimentação",
            tipo="despesa",
            prioridade=100,
        )

    def test_sugerir_ifood_alimentacao(self):
        sug = sugerir(self.user, "COMPRA IFOOD RESTAURANTE", "despesa")
        self.assertIsNotNone(sug)
        self.assertEqual(sug.categoria_nome, "Alimentação")
        self.assertGreaterEqual(sug.confianca, 0.70)


class RegraUsuarioTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="regra@test.com",
            nome="Regra",
            password="senha12345",
        )
        self.cat, _ = Categoria.objects.get_or_create(
            nome="Família Teste Cat",
            tipo="despesa",
            usuario=self.user,
            defaults={"ativa": True},
        )
        RegraCategorizacao.objects.create(
            usuario=self.user,
            tipo_regra="contains",
            padrao="pix maria",
            padrao_normalizado="pix maria",
            categoria=self.cat,
            confianca_base=0.96,
            origem="manual",
        )

    def test_regra_usuario_prioritaria(self):
        sug = sugerir(self.user, "PIX MARIA SILVA", "despesa")
        self.assertIsNotNone(sug)
        self.assertEqual(sug.fonte, "regra_usuario")
        self.assertEqual(sug.categoria_id, self.cat.pk)


class LearningTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="learn@test.com",
            nome="Learn",
            password="senha12345",
        )
        self.conta = Conta.objects.create(
            usuario=self.user,
            nome="Conta",
            tipo="corrente",
        )
        self.cat = Categoria.objects.create(
            nome="Transporte",
            tipo="despesa",
            usuario=self.user,
            ativa=True,
        )

    def test_memoria_merchant_apos_confirmacao(self):
        tx = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat,
            tipo="despesa",
            valor=Decimal("25.00"),
            data="2026-01-15",
            descricao="UBER TRIP SP",
        )
        processar_feedback_transacao(
            usuario=self.user,
            transacao=tx,
            descricao=tx.descricao,
            categoria_final=self.cat,
        )
        key = extrair_merchant_key(normalizar_texto(tx.descricao))
        self.assertTrue(
            MemoriaMerchantUsuario.objects.filter(
                usuario=self.user,
                merchant_key=key,
            ).exists()
        )


class GateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="gate@test.com",
            nome="Gate",
            password="senha12345",
        )
        Categoria.objects.get_or_create(
            nome="Alimentação",
            tipo="despesa",
            padrao=True,
            defaults={"ativa": True},
        )

    def test_gate_bloqueia_quando_admin_desligou(self):
        from categorizacao.services.llm.gate import should_invoke_llm
        from categorizacao.services.pipeline import _construir_contexto

        ctx = _construir_contexto(self.user, "PADARIA LOCAL XYZ", "despesa")
        with self.settings(ENABLE_CATEGORIZACAO_LLM=False):
            gate = should_invoke_llm(ctx, None)
        self.assertFalse(gate.invoke)
        self.assertEqual(gate.reason, "feature_disabled")

    def test_gate_aciona_baixa_confianca(self):
        from categorizacao.services.llm.gate import should_invoke_llm
        from categorizacao.services.pipeline import _construir_contexto
        from categorizacao.types import PredicaoCategorizacao

        ctx = _construir_contexto(self.user, "PADARIA LOCAL XYZ", "despesa")
        pred = PredicaoCategorizacao(
            categoria_id=1,
            categoria_nome="Diversos",
            confianca=0.40,
            fonte="ml",
            merchant_key=None,
            explicacao="",
        )
        with self.settings(ENABLE_CATEGORIZACAO_LLM=True):
            gate = should_invoke_llm(ctx, pred)
        self.assertTrue(gate.invoke)
        self.assertEqual(gate.reason, "low_confidence")

    def test_gate_aciona_ambiguidade_pix(self):
        from categorizacao.services.llm.gate import should_invoke_llm
        from categorizacao.services.pipeline import _construir_contexto
        from categorizacao.types import PredicaoCategorizacao

        ctx = _construir_contexto(self.user, "PIX ENVIADO JOAO SILVA", "despesa")
        pred = PredicaoCategorizacao(
            categoria_id=1,
            categoria_nome="Diversos",
            confianca=0.70,
            fonte="ml",
            merchant_key=None,
            explicacao="",
        )
        with self.settings(ENABLE_CATEGORIZACAO_LLM=True):
            gate = should_invoke_llm(ctx, pred)
        self.assertTrue(gate.invoke)
        self.assertEqual(gate.reason, "structural_ambiguity")


class LLMFallbackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="llm@test.com",
            nome="LLM",
            password="senha12345",
        )
        Categoria.objects.get_or_create(
            nome="Alimentação",
            tipo="despesa",
            padrao=True,
            defaults={"ativa": True},
        )

    def test_classificar_inalterado_sem_flag(self):
        from categorizacao.services.pipeline import _construir_contexto, classificar

        ctx = _construir_contexto(self.user, "PADARIA CENTRAL", "despesa")
        with self.settings(ENABLE_CATEGORIZACAO_LLM=False):
            pred = classificar(ctx)
        self.assertTrue(pred is None or pred.fonte != "llm_gemini")

    def test_llm_nunca_auto_aplica(self):
        from categorizacao.types import PredicaoCategorizacao, PreferenciasCategorizacao, predicao_para_sugestao

        pred = PredicaoCategorizacao(
            categoria_id=1,
            categoria_nome="Alimentação",
            confianca=0.95,
            fonte="llm_gemini",
            merchant_key=None,
            explicacao="Sugestão por IA",
        )
        prefs = PreferenciasCategorizacao(auto_aplicar=True, limiar_auto=0.50)
        sug = predicao_para_sugestao(pred, prefs)
        self.assertFalse(sug.auto_aplicar)

    def test_sugerir_com_mock_llm(self):
        with self.settings(
            ENABLE_CATEGORIZACAO_LLM=True,
            CATEGORIZACAO_LLM_USE_MOCK=True,
            CATEGORIZACAO_LLM_MODEL="mock-llm",
        ):
            sug = sugerir(self.user, "PADARIA CENTRAL LTDA", "despesa")
        self.assertIsNotNone(sug)

    def test_sugerir_avulso_nao_invoca_llm(self):
        from unittest.mock import patch

        with self.settings(
            ENABLE_CATEGORIZACAO_LLM=True,
            CATEGORIZACAO_LLM_USE_MOCK=True,
            CATEGORIZACAO_LLM_MODEL="mock-llm",
        ):
            with patch(
                "categorizacao.services.llm.orchestrator.classificar_com_llm"
            ) as mock_llm:
                sugerir(self.user, "PADARIA CENTRAL LTDA", "despesa", usar_llm=False)
        mock_llm.assert_not_called()

    def test_endpoint_sugerir_nao_invoca_llm(self):
        from unittest.mock import patch

        self.client = Client()
        self.client.force_login(self.user)
        with self.settings(ENABLE_CATEGORIZACAO_LLM=True):
            with patch(
                "categorizacao.services.llm.orchestrator.classificar_com_llm"
            ) as mock_llm:
                resp = self.client.get(
                    reverse("categorizacao:sugerir_categoria"),
                    {"descricao": "padaria central ltda xyz", "tipo": "despesa"},
                )
        self.assertEqual(resp.status_code, 200)
        mock_llm.assert_not_called()

    def test_llm_contexto_quando_ativa(self):
        with self.settings(
            ENABLE_CATEGORIZACAO_LLM=True,
            CATEGORIZACAO_LLM_USE_MOCK=True,
            CATEGORIZACAO_LLM_MODEL="mock-llm",
        ):
            sug = sugerir(self.user, "PADARIA CENTRAL LTDA", "despesa")
        if sug and sug.fonte == "llm_gemini":
            self.assertIn("llm_model", sug.contexto)
