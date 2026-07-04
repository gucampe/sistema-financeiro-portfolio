# Rollout — Fallback LLM (Gemini) na Categorização

## Variáveis operacionais (MVP — manter no env)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `ENABLE_CATEGORIZACAO_LLM` | `False` | Kill switch único |
| `GEMINI_API_KEY` | `""` | Chave API Google (obrigatória em produção se LLM ligado) |
| `CATEGORIZACAO_LLM_MODEL` | `gemini-2.5-flash-lite` | Modelo ativo |

Constantes no código (`config/llm_settings.py`, **sem env**): timeout 8s, retries 1, trigger_max 0.65, cache_ttl 168h, min_confidence 0.55, retenção logs 90d.

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
