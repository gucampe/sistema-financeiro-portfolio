# Comparativo — Fallback LLM (Gemini) vs Pipeline Híbrido

**Data:** 2026-06-22  
**Commit:** `26a3ed4`  
**Variante LLM:** mock-llm  

## Resumo executivo

| Métrica | Híbrido | Com LLM | Δ |
|---------|---------|---------|---|
| Cobertura global | 41.2% | 95.3% | +54.1% |
| Acurácia top-1 | 91.4% | 53.1% | -38.3% |
| Recall | 41.6% | 91.5% | +49.9% |
| Latência média (ms) | 23.2 | 43.0 | — |
| Invocações LLM | 0 | 46 | — |

## Buckets críticos (M3 + R2)

| Bucket | Cobertura híbrido | Cobertura LLM | Recall híbrido | Recall LLM |
|--------|-------------------|---------------|----------------|------------|
| M3 | 6.7% | 100.0% | 3.7% | 100.0% |
| R2 | 25.0% | 85.0% | 29.4% | 76.9% |

## Ganhos e regressões

- **Ganhos LLM** (FN→TP): 11
- **Regressões** (TP→FP): 0

## Custo estimado (simulação)

- Por chamada (~450 in / 80 out tokens): **$0.000000**
- Projeção mensal (1000 cat/dia, 15% LLM): **$0.35**

## Kill switch

Defina `ENABLE_CATEGORIZACAO_LLM=False` para desativar instantaneamente o fallback LLM.

## Próximos passos

1. Validar em staging com opt-in interno
2. Benchmark com API real (fora do CI)
3. Monitorar `LLMRequestLog` no admin
