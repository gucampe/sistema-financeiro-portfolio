"""Testes da UX de importação — preview sem auto-cat + batch sob demanda."""

from __future__ import annotations

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from categorias.models import Categoria
from categorizacao.models import CategorizacaoUXEvent
from contas.models import Conta

User = get_user_model()


class ImportUXBatchTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="ux@test.com",
            password="teste123",
            nome="UX Test",
        )
        self.conta = Conta.objects.create(usuario=self.user, nome="Conta UX", tipo="corrente")
        Categoria.objects.get_or_create(
            usuario=self.user, nome="Diversos", tipo="despesa", defaults={"ativa": True}
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_preview_nao_traz_categorizacao_automatica(self):
        from transacoes.views import _payload_preview_importacao
        from transacoes.ofx_parse import LinhaOfx
        from datetime import date

        linhas = [
            LinhaOfx(
                data=date.today(),
                valor=Decimal("-50.00"),
                tipo="despesa",
                descricao="PIX TESTE UX",
                ofx_fitid="abc123",
            )
        ]
        payload = _payload_preview_importacao(self.user, self.conta, linhas)
        self.assertTrue(payload.get("categorizacao_pendente"))
        self.assertNotIn("categoria_sugerida_id", payload["linhas"][0])

    def test_categorizar_import_batch_cria_eventos(self):
        url = reverse("categorizacao:categorizar_import_batch")
        body = {
            "contexto": "import_ofx",
            "linhas": [
                {
                    "indice": 0,
                    "descricao": "SUPERMERCADO XYZ",
                    "tipo": "despesa",
                    "valor": "120.50",
                }
            ],
        }
        res = self.client.post(
            url,
            data=json.dumps(body),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("resumo", data)
        self.assertEqual(CategorizacaoUXEvent.objects.filter(evento="ia_click").count(), 1)
        self.assertEqual(CategorizacaoUXEvent.objects.filter(evento="ia_complete").count(), 1)

    def test_aplicar_sugestao_define_nivel_confianca(self):
        from categorizacao.services.import_suggestions import aplicar_sugestao_em_linha
        from categorizacao.types import SugestaoCategorizacao

        item_alta = aplicar_sugestao_em_linha(
            {"indice": 0, "descricao": "SUPERMERCADO XYZ"},
            SugestaoCategorizacao(
                categoria_id=1,
                categoria_nome="Alimentação",
                confianca=0.95,
                fonte="historico",
                explicacao="",
                auto_aplicar=False,
                merchant_key="",
                contexto={},
            ),
        )
        self.assertEqual(item_alta["categoria_sugerida_nivel_confianca"], "alta")
        self.assertTrue(item_alta["categoria_sugerida_pre_preencher"])

        item_media = aplicar_sugestao_em_linha(
            {"indice": 1, "descricao": "RESTAURANTE LOCAL XYZ"},
            SugestaoCategorizacao(
                categoria_id=2,
                categoria_nome="Alimentação",
                confianca=0.62,
                fonte="llm_gemini",
                explicacao="",
                auto_aplicar=False,
                merchant_key="",
                contexto={},
            ),
        )
        self.assertEqual(item_media["categoria_sugerida_nivel_confianca"], "media")
        self.assertTrue(item_media["categoria_sugerida_pre_preencher"])

    def test_cdb_rdb_alta_confianca_llm_preenche(self):
        from categorizacao.services.import_suggestions import aplicar_sugestao_em_linha
        from categorizacao.types import SugestaoCategorizacao

        item = aplicar_sugestao_em_linha(
            {"indice": 0, "descricao": "APLICACAO CDB/RDB"},
            SugestaoCategorizacao(
                categoria_id=5,
                categoria_nome="Aplicações e investimentos",
                confianca=0.95,
                fonte="llm_gemini",
                explicacao="",
                auto_aplicar=False,
                merchant_key="",
                contexto={"requires_user_confirmation": True},
            ),
        )
        self.assertEqual(item["categoria_sugerida_trust_tier"], 1)
        self.assertEqual(item["categoria_sugerida_nivel_confianca"], "alta")
        self.assertTrue(item["categoria_sugerida_pre_preencher"])
        self.assertFalse(item["categoria_sugerida_requires_confirmacao"])

    def test_pix_pf_llm_permance_conservador(self):
        from categorizacao.services.import_suggestions import aplicar_sugestao_em_linha
        from categorizacao.types import SugestaoCategorizacao

        item = aplicar_sugestao_em_linha(
            {"indice": 0, "descricao": "PIX JOAO SILVA SANTOS"},
            SugestaoCategorizacao(
                categoria_id=3,
                categoria_nome="Família",
                confianca=0.95,
                fonte="llm_gemini",
                explicacao="",
                auto_aplicar=False,
                merchant_key="",
                contexto={"is_pix_pf": True, "requires_user_confirmation": True},
            ),
        )
        self.assertEqual(item["categoria_sugerida_trust_tier"], 3)
        self.assertTrue(item["categoria_sugerida_pre_preencher"])
        self.assertEqual(item["categoria_sugerida_nivel_confianca"], "alta")
        self.assertFalse(item["categoria_sugerida_requires_confirmacao"])
