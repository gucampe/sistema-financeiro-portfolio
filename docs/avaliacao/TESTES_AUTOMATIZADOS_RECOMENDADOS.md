# Testes automatizados adicionais recomendados (não implementados)

## Lacunas vs cobertura atual

| Área | Hoje | Deveria existir |
|------|------|-----------------|
| Golden regression | Ausente | `test_golden_categorizacao.py` parametrizado por CSV |
| Preview OFX sugestões | Sem assert | Assert `categoria_sugerida_*` em fixture |
| Ablation | Script avaliação | Testes unitários por camada |
| Learning loop | 1 teste | Sequência aceita/corrigida → regra aprendida |
| E2E categorização | Import sem assert cat | Playwright: select pré-preenchido IFOOD |
| Performance | Carga no command | pytest: preview 500 linhas < 3s |

## Cenários prioritários

1. Regression golden M1 (40 casos) — bloquear queda de acurácia
2. Contract API preview — schema estável
3. Integration learning — segunda import melhora após feedback
4. IDOR — usuário A não acessa regras de B
5. Fuzzy boundary — score 84 vs 86

## Cobertura alvo

- Pipeline layers: 80%+ branches
- Views categorização: 90%+
- Fluxo import com sugestão: happy path + correção por superfície
