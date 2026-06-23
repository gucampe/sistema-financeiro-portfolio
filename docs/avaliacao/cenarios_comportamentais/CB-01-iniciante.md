# Cenário CB-01 — Usuário iniciante

**Setup:** 0 transações, sem regras, sem histórico  
**Objetivo:** medir cobertura inicial só com seed global + fuzzy

## Roteiro

1. Importar `ofx_30_merchants.ofx`
2. Executar benchmark golden via `avaliar_categorizacao`
3. Anotar cobertura preview e FP em merchants M1

## Métricas alvo

- Cobertura M1 ≥ observar valor real
- FP em PIX/ambíguos aceitável para iniciante
