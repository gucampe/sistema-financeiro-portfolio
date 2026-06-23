# Rollout — Fallback LLM (Gemini) na Categorização

## Quem controla a IA

**Somente o admin** (via variáveis de ambiente / deploy). Usuários finais **não** ligam ou desligam a IA.

| Variável | Default | Descrição |
|----------|---------|-----------|
| `ENABLE_CATEGORIZACAO_LLM` | `False` | Master switch — liga/desliga IA para todo o sistema |
| `GEMINI_API_KEY` | `""` | Chave API Google |
| `CATEGORIZACAO_LLM_USE_MOCK` | `False` | Mock para CI/dev (sem chamadas reais) |
| `CATEGORIZACAO_LLM_MOSTRAR_BADGE` | `True` | Exibe badge "IA" na interface quando a sugestão veio do Gemini |
| `CATEGORIZACAO_LLM_DAILY_BUDGET_USD` | `0` | 0 = sem cap rígido |
| `CATEGORIZACAO_LLM_TRIGGER_MAX` | `0.65` | Confiança máxima do híbrido para acionar LLM |

## Kill switch

```bash
ENABLE_CATEGORIZACAO_LLM=False
```

Retorno imediato ao pipeline híbrido puro.

## Fases de rollout

| Fase | Ambiente | Escopo | Critério de avanço |
|------|----------|--------|-------------------|
| 0 | Local/CI | Mock provider | Testes passando |
| 1 | Staging | Admin liga flag + API real | Benchmark M3+R2: cobertura +15pp |
| 2 | Staging | Equipe interna | Latência p95 &lt; 3s |
| 3 | Produção | Flag ligada pelo admin | Taxa acionamento estável |
| 4 | Produção | Monitoramento contínuo | Custo dentro do budget |
| 5 | GA | Documentação LGPD atualizada | Política de privacidade |

## Monitoramento

- **Admin Django:** `LLMRequestLog` + `/admin/categorizacao/metricas/`
- **Comando:** `python manage.py avaliar_categorizacao_llm --compare-models`
- **Longitudinal com LLM:** `python manage.py avaliar_categorizacao_longitudinal --with-llm --quick`

## Degradação

1. Cache hit → retorno imediato  
2. Circuit breaker aberto → híbrido  
3. Budget diário excedido → híbrido até o dia seguinte  
4. Timeout/erro API → híbrido + log  

## LGPD

Processamento via Google Gemini documentado em `docs/auditoria/RELATORIO_SEGURANCA_LGPD.md` (seção 4.6.1). Base legal: legítimo interesse / execução de contrato, com transparência via badge quando habilitado pelo admin.
