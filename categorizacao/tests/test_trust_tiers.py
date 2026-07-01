"""Testes de trust tiers — calibragem de confiança."""

from __future__ import annotations

from django.test import TestCase

from categorizacao.services.trust_tiers import (
    TIER_ALTO_RISCO,
    TIER_BAIXO_RISCO,
    TIER_MEDIO_RISCO,
    classificar_trust_tier,
    deve_exigir_confirmacao_llm,
)


class TrustTiersTest(TestCase):
    def test_tier1_merchants_obvios(self):
        self.assertEqual(classificar_trust_tier("APLICACAO CDB/RDB"), TIER_BAIXO_RISCO)
        self.assertEqual(classificar_trust_tier("NETFLIX.COM"), TIER_BAIXO_RISCO)
        self.assertEqual(classificar_trust_tier("UBER TRIP"), TIER_BAIXO_RISCO)

    def test_tier3_pix_pf(self):
        self.assertEqual(
            classificar_trust_tier("PIX JOAO SILVA SANTOS", {"is_pix_pf": True}),
            TIER_ALTO_RISCO,
        )

    def test_tier2_generico(self):
        self.assertEqual(classificar_trust_tier("RESTAURANTE LOCAL"), TIER_MEDIO_RISCO)

    def test_llm_tier1_nao_exige_confirmacao_alta_confianca(self):
        self.assertFalse(
            deve_exigir_confirmacao_llm("APLICACAO CDB/RDB", 0.95, {})
        )

    def test_llm_pix_exige_confirmacao_apenas_baixa_confianca(self):
        self.assertTrue(
            deve_exigir_confirmacao_llm(
                "PIX MARIA OLIVEIRA",
                0.40,
                {"is_pix_pf": True},
            )
        )
        self.assertFalse(
            deve_exigir_confirmacao_llm(
                "PIX MARIA OLIVEIRA",
                0.95,
                {"is_pix_pf": True},
            )
        )
