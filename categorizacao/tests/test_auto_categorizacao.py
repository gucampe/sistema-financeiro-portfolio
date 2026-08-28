"""Garantia da categorização automática após remoção da contribuição global."""

from __future__ import annotations

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from categorias.models import Categoria
from categorizacao.evaluation.datasets import categorias_aceitaveis_set, load_golden_csv
from categorizacao.models import MemoriaMerchantUsuario, MerchantGlobal, RegraCategorizacao
from categorizacao.services.cache import invalidar_cache_global, invalidar_cache_usuario
from categorizacao.services.import_suggestions import aplicar_sugestao_em_linha
from categorizacao.services.learning import processar_feedback_transacao
from categorizacao.services.merchant import invalidar_cache_merchants
from categorizacao.services.pipeline import sugerir, sugerir_batch
from categorizacao.types import (
    PredicaoCategorizacao,
    PreferenciasCategorizacao,
    predicao_para_sugestao,
)
from contas.models import Conta
from transacoes.models import Transacao
from usuarios.forms import PreferenciasFinanceirasForm

User = get_user_model()


def _pred(fonte: str, confianca: float, **kwargs) -> PredicaoCategorizacao:
    return PredicaoCategorizacao(
        categoria_id=kwargs.get("categoria_id", 1),
        categoria_nome=kwargs.get("categoria_nome", "Alimentação"),
        confianca=confianca,
        fonte=fonte,
        merchant_key=kwargs.get("merchant_key"),
        explicacao=kwargs.get("explicacao", "teste"),
        contexto=kwargs.get("contexto") or {},
    )


class AutoAplicarPreferenciasTests(TestCase):
    def test_desligado_nunca_auto_aplica(self):
        prefs = PreferenciasCategorizacao(auto_aplicar=False, limiar_auto=0.50)
        sug = predicao_para_sugestao(_pred("historico", 0.99), prefs)
        self.assertFalse(sug.auto_aplicar)

    def test_ligado_aplica_quando_atinge_limiar(self):
        prefs = PreferenciasCategorizacao(auto_aplicar=True, limiar_auto=0.90)
        sug = predicao_para_sugestao(_pred("historico", 0.91), prefs)
        self.assertTrue(sug.auto_aplicar)

    def test_ligado_nao_aplica_abaixo_do_limiar(self):
        prefs = PreferenciasCategorizacao(auto_aplicar=True, limiar_auto=0.90)
        sug = predicao_para_sugestao(_pred("historico", 0.89), prefs)
        self.assertFalse(sug.auto_aplicar)

    def test_llm_nunca_auto_aplica_mesmo_com_limiar_baixo(self):
        prefs = PreferenciasCategorizacao(auto_aplicar=True, limiar_auto=0.10)
        sug = predicao_para_sugestao(_pred("llm_gemini", 0.99), prefs)
        self.assertFalse(sug.auto_aplicar)

    def test_from_usuario_lê_perfil_sem_contribuicao_global(self):
        user = User.objects.create_user(
            email="prefs-auto@test.com",
            nome="Prefs Auto",
            password="senha12345",
        )
        perfil = user.perfil
        perfil.categorizacao_auto_aplicar = True
        perfil.categorizacao_limiar_auto = 0.85
        perfil.save(update_fields=["categorizacao_auto_aplicar", "categorizacao_limiar_auto"])
        prefs = PreferenciasCategorizacao.from_usuario(user)
        self.assertTrue(prefs.auto_aplicar)
        self.assertEqual(prefs.limiar_auto, 0.85)
        self.assertFalse(hasattr(prefs, "contribuir_globais"))
        self.assertFalse(hasattr(perfil, "categorizacao_contribuir_globais"))


@override_settings(ENABLE_CATEGORIZACAO_LLM=False)
class AutoAplicarPipelineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="pipe-auto@test.com",
            nome="Pipe Auto",
            password="senha12345",
        )
        self.perfil = self.user.perfil
        self.perfil.categorizacao_auto_aplicar = True
        self.perfil.categorizacao_limiar_auto = 0.90
        self.perfil.save(update_fields=["categorizacao_auto_aplicar", "categorizacao_limiar_auto"])
        self.cat = Categoria.objects.get(usuario=self.user, nome="Alimentação", tipo="despesa")
        invalidar_cache_merchants()
        MerchantGlobal.objects.update_or_create(
            canonical_name="ifood",
            defaults={
                "aliases": ["ifood", "ifood.com"],
                "categoria_padrao_nome": "Alimentação",
                "tipo": "despesa",
                "prioridade": 100,
                "ativo": True,
            },
        )
        invalidar_cache_merchants()

    def test_regra_usuario_alta_confianca_auto_aplica(self):
        RegraCategorizacao.objects.create(
            usuario=self.user,
            tipo_regra="contains",
            padrao="padaria do ze",
            padrao_normalizado="padaria do ze",
            categoria=self.cat,
            confianca_base=0.96,
            origem="manual",
            ativa=True,
        )
        invalidar_cache_usuario(self.user.pk)
        sug = sugerir(self.user, "PADARIA DO ZE CENTRO", "despesa")
        self.assertIsNotNone(sug)
        self.assertEqual(sug.fonte, "regra_usuario")
        self.assertEqual(sug.categoria_id, self.cat.pk)
        self.assertTrue(sug.auto_aplicar)

    def test_fuzzy_ifood_auto_aplica_com_opt_in(self):
        sug = sugerir(self.user, "COMPRA CARTAO IFOOD RESTAURANTE", "despesa")
        self.assertIsNotNone(sug)
        self.assertEqual(sug.categoria_nome, "Alimentação")
        self.assertGreaterEqual(sug.confianca, 0.90)
        self.assertTrue(sug.auto_aplicar)

    def test_opt_in_desligado_sugere_mas_nao_auto_aplica(self):
        self.perfil.categorizacao_auto_aplicar = False
        self.perfil.save(update_fields=["categorizacao_auto_aplicar"])
        sug = sugerir(self.user, "COMPRA CARTAO IFOOD RESTAURANTE", "despesa")
        self.assertIsNotNone(sug)
        self.assertEqual(sug.categoria_nome, "Alimentação")
        self.assertFalse(sug.auto_aplicar)

    def test_regra_global_ainda_funciona(self):
        cat_padrao, _ = Categoria.objects.get_or_create(
            nome="Alimentação",
            tipo="despesa",
            padrao=True,
            defaults={"ativa": True},
        )
        RegraCategorizacao.objects.create(
            usuario=None,
            tipo_regra="contains",
            padrao="padaria global",
            padrao_normalizado="padaria global",
            categoria=cat_padrao,
            confianca_base=0.93,
            origem="seed",
            ativa=True,
        )
        invalidar_cache_global()
        sug = sugerir(self.user, "PADARIA GLOBAL LTDA", "despesa")
        self.assertIsNotNone(sug)
        self.assertEqual(sug.fonte, "regra_global")
        self.assertTrue(sug.auto_aplicar)


@override_settings(ENABLE_CATEGORIZACAO_LLM=False)
class AprendizadoPessoalAindaFuncionaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="learn-auto@test.com",
            nome="Learn Auto",
            password="senha12345",
        )
        self.conta = Conta.objects.create(usuario=self.user, nome="Conta", tipo="corrente")
        self.cat = Categoria.objects.get(usuario=self.user, nome="Família")

    def test_confirmacao_gera_memoria_e_proxima_sugestao_historico(self):
        tx = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat,
            tipo="despesa",
            valor=Decimal("32.00"),
            data="2026-01-15",
            descricao="LOJA UNICA AUTOXYZ LTDA",
        )
        processar_feedback_transacao(
            usuario=self.user,
            transacao=tx,
            descricao=tx.descricao,
            categoria_final=self.cat,
        )
        self.assertTrue(MemoriaMerchantUsuario.objects.filter(usuario=self.user).exists())
        sug = sugerir(self.user, "LOJA UNICA AUTOXYZ LTDA", "despesa")
        self.assertIsNotNone(sug)
        self.assertEqual(sug.fonte, "historico")
        self.assertEqual(sug.categoria_id, self.cat.pk)


@override_settings(ENABLE_CATEGORIZACAO_LLM=False)
class GoldenMerchantsSmokeTests(TestCase):
    """Amostra M1 do golden: merchants óbvios continuam classificando após o corte."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="golden-auto@test.com",
            nome="Golden Auto",
            password="senha12345",
        )
        call_command("seed_merchants_globais")
        invalidar_cache_merchants()
        Categoria.objects.get_or_create(
            nome="Alimentação", tipo="despesa", padrao=True, defaults={"ativa": True}
        )

    def test_amostra_m1_tem_sugestao_aceitavel(self):
        casos = [c for c in load_golden_csv() if c.id.startswith("M1-")][:24]
        self.assertGreaterEqual(len(casos), 10)
        acertos = 0
        sem_sugestao = []
        erros = []
        for caso in casos:
            sug = sugerir(self.user, caso.descricao, caso.tipo)
            if sug is None:
                sem_sugestao.append(caso.id)
                continue
            aceitaveis = categorias_aceitaveis_set(caso)
            if caso.categoria_esperada:
                aceitaveis.add(caso.categoria_esperada)
            if sug.categoria_nome in aceitaveis:
                acertos += 1
            else:
                erros.append((caso.id, sug.categoria_nome, caso.categoria_esperada))
        self.assertLessEqual(len(sem_sugestao), 2, f"sem sugestão: {sem_sugestao}")
        self.assertGreaterEqual(acertos / len(casos), 0.80, f"erros={erros} sem={sem_sugestao}")


@override_settings(ENABLE_CATEGORIZACAO_LLM=False)
class EndpointsCategorizacaoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="http-auto@test.com",
            nome="Http Auto",
            password="senha12345",
        )
        self.user.perfil.categorizacao_auto_aplicar = True
        self.user.perfil.categorizacao_limiar_auto = 0.90
        self.user.perfil.save(
            update_fields=["categorizacao_auto_aplicar", "categorizacao_limiar_auto"]
        )
        MerchantGlobal.objects.update_or_create(
            canonical_name="ifood",
            defaults={
                "aliases": ["ifood"],
                "categoria_padrao_nome": "Alimentação",
                "tipo": "despesa",
                "prioridade": 100,
                "ativo": True,
            },
        )
        invalidar_cache_merchants()
        self.client = Client()
        self.client.force_login(self.user)

    def test_api_sugerir_ifood(self):
        resp = self.client.get(
            reverse("categorizacao:sugerir_categoria"),
            {"descricao": "COMPRA IFOOD RESTAURANTE", "tipo": "despesa"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "ok")
        self.assertIsNotNone(body["sugestao"])
        self.assertEqual(body["sugestao"]["categoria_nome"], "Alimentação")
        self.assertTrue(body["sugestao"]["auto_aplicar"])

    def test_batch_import_preenche_linha(self):
        resp = self.client.post(
            reverse("categorizacao:categorizar_import_batch"),
            data=json.dumps(
                {
                    "contexto": "import_ofx",
                    "linhas": [
                        {
                            "indice": 0,
                            "descricao": "COMPRA IFOOD RESTAURANTE",
                            "tipo": "despesa",
                            "valor": "42.90",
                        }
                    ],
                }
            ),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        linha = data["linhas"][0]
        self.assertEqual(linha["categoria_sugerida_nome"], "Alimentação")
        self.assertTrue(linha["categoria_sugerida_pre_preencher"])
        self.assertTrue(linha["categoria_sugerida_auto_aplicar"])

    def test_batch_respeita_prefs_do_usuario(self):
        linhas = [{"descricao": "COMPRA IFOOD RESTAURANTE", "tipo": "despesa"}]
        [sug] = sugerir_batch(self.user, linhas)
        self.assertIsNotNone(sug)
        self.assertTrue(sug.auto_aplicar)

    def test_import_ux_propaga_auto_aplicar(self):
        sug = sugerir(self.user, "COMPRA IFOOD RESTAURANTE", "despesa")
        item = aplicar_sugestao_em_linha({"indice": 0, "descricao": "COMPRA IFOOD"}, sug)
        self.assertTrue(item["categoria_sugerida_auto_aplicar"])
        self.assertTrue(item["categoria_sugerida_pre_preencher"])


class FormularioPreferenciasCategorizacaoTests(TestCase):
    def test_form_expoe_auto_aplicar_e_limiar(self):
        user = User.objects.create_user(
            email="form-auto@test.com",
            nome="Form Auto",
            password="senha12345",
        )
        form = PreferenciasFinanceirasForm(instance=user.perfil, user=user)
        self.assertIn("categorizacao_auto_aplicar", form.fields)
        self.assertIn("categorizacao_limiar_auto", form.fields)
        self.assertNotIn("categorizacao_contribuir_globais", form.fields)

    def test_pagina_configuracoes_mantem_auto_aplicar(self):
        user = User.objects.create_user(
            email="cfg-auto@test.com",
            nome="Cfg Auto",
            password="senha12345",
        )
        client = Client()
        client.force_login(user)
        resp = client.get(reverse("usuarios:configuracoes"))
        html = resp.content.decode()
        self.assertIn("Aplicar categorias automaticamente", html)
        self.assertIn("Limiar de confiança para auto-aplicar", html)
        self.assertNotIn("Contribuir com dados anonimizados", html)
