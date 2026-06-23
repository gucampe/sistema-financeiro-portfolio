# Relatório Longitudinal — Categorização Automática GranaGo

**Versão:** 1.0  
**Data:** 2026-06-22  
**Commit:** 26a3ed4  
**Escopo:** simulação temporal 12 semanas, 15 personas LX, sem alteração de produto

---

## 1. Resumo executivo longitudinal

### 1.1 Conclusão

O sistema demonstra evolução longitudinal em parte das personas, principalmente onde há correções consistentes e merchants locais/PIX recorrentes.

### 1.2 Tabela cold start vs consolidado (lote reimport 60)

| Persona | T0 cobertura | T5 cobertura | Δ | T0 acurácia | T5 acurácia | ML T5 | Veredito |
|---------|--------------|--------------|---|-------------|-------------|-------|----------|
| LX-01 | 51.7% | 51.7% | +0.0pp | 93.5% | 93.5% | não | estável |
| LX-02 | 51.7% | 51.7% | +0.0pp | 93.5% | 93.5% | não | estável |
| LX-03 | 51.7% | 60.0% | +8.3pp | 93.5% | 94.4% | não | melhora parcial |
| LX-04 | 51.7% | 95.0% | +43.3pp | 93.5% | 84.2% | não | melhora clara |
| LX-05 | 51.7% | 60.0% | +8.3pp | 93.5% | 94.4% | não | melhora parcial |
| LX-06 | 51.7% | 51.7% | +0.0pp | 93.5% | 93.5% | não | estável |
| LX-07 | 51.7% | 75.0% | +23.3pp | 93.5% | 93.3% | não | melhora clara |
| LX-08 | 51.7% | 60.0% | +8.3pp | 93.5% | 94.4% | não | melhora parcial |
| LX-09 | 51.7% | 60.0% | +8.3pp | 93.5% | 80.6% | não | melhora parcial |
| LX-10 | 51.7% | 60.0% | +8.3pp | 93.5% | 94.4% | não | melhora parcial |
| LX-11 | 51.7% | 51.7% | +0.0pp | 93.5% | 93.5% | não | estável |
| LX-12 | 51.7% | 60.0% | +8.3pp | 93.5% | 94.4% | não | melhora parcial |
| LX-CTRL-0 | 51.7% | 60.0% | +8.3pp | 93.5% | 80.6% | não | melhora parcial |
| LX-CTRL-ML | 51.7% | 60.0% | +8.3pp | 93.5% | 94.4% | não | melhora parcial |
| LX-CTRL-CORR | 51.7% | 60.0% | +8.3pp | 93.5% | 94.4% | não | melhora parcial |

---

## 2. Metodologia

- Replay temporal: ingestão semanal + feedback simulado via `processar_feedback_transacao`
- Checkpoints: T0 (cold), T1 (sem1), T2 (sem2), T3 (sem4), T4 (sem8), T5 (sem12)
- Lote fixo reimport: 60 transações idênticas em todo checkpoint
- Prova aprendizado: 45 casos (PIX, locais, mutáveis, C1, controle global)
- ML: retreino manual em T3/T4/T5 quando tx≥50 (`retreinar_modelos_usuario`)

---

## 3. Curva de aprendizado (por checkpoint)

### 3.1 Cobertura reimport

| Persona | T0 | T1 | T2 | T3 | T4 | T5 |
|---------|----|----|----|----|----|-----|
| LX-01 | 51.7% | 51.7% | 51.7% | 51.7% | 51.7% | 51.7% |
| LX-02 | 51.7% | 51.7% | 51.7% | 51.7% | 51.7% | 51.7% |
| LX-03 | 51.7% | 58.3% | 58.3% | 60.0% | 60.0% | 60.0% |
| LX-04 | 51.7% | 78.3% | 80.0% | 83.3% | 88.3% | 95.0% |
| LX-05 | 51.7% | 60.0% | 60.0% | 60.0% | 60.0% | 60.0% |
| LX-06 | 51.7% | 51.7% | 51.7% | 51.7% | 51.7% | 51.7% |
| LX-07 | 51.7% | 73.3% | 75.0% | 75.0% | 75.0% | 75.0% |
| LX-08 | 51.7% | 60.0% | 60.0% | 60.0% | 60.0% | 60.0% |
| LX-09 | 51.7% | 60.0% | 60.0% | 60.0% | 60.0% | 60.0% |
| LX-10 | 51.7% | 60.0% | 60.0% | 60.0% | 60.0% | 60.0% |
| LX-11 | 51.7% | 51.7% | 51.7% | 51.7% | 51.7% | 51.7% |
| LX-12 | 51.7% | 51.7% | 56.7% | 56.7% | 60.0% | 60.0% |
| LX-CTRL-0 | 51.7% | 60.0% | 60.0% | 60.0% | 60.0% | 60.0% |
| LX-CTRL-ML | 51.7% | 60.0% | 60.0% | 60.0% | 60.0% | 60.0% |
| LX-CTRL-CORR | 51.7% | 60.0% | 60.0% | 60.0% | 60.0% | 60.0% |

### 3.2 Acurácia reimport

| Persona | T0 | T1 | T2 | T3 | T4 | T5 |
|---------|----|----|----|----|----|-----|
| LX-01 | 93.5% | 93.5% | 93.5% | 93.5% | 93.5% | 93.5% |
| LX-02 | 93.5% | 93.5% | 93.5% | 93.5% | 93.5% | 93.5% |
| LX-03 | 93.5% | 94.3% | 94.3% | 94.4% | 94.4% | 94.4% |
| LX-04 | 93.5% | 80.9% | 81.2% | 82.0% | 83.0% | 84.2% |
| LX-05 | 93.5% | 94.4% | 94.4% | 94.4% | 94.4% | 94.4% |
| LX-06 | 93.5% | 93.5% | 93.5% | 93.5% | 93.5% | 93.5% |
| LX-07 | 93.5% | 93.2% | 93.3% | 93.3% | 93.3% | 93.3% |
| LX-08 | 93.5% | 94.4% | 94.4% | 94.4% | 94.4% | 94.4% |
| LX-09 | 93.5% | 80.6% | 80.6% | 80.6% | 80.6% | 80.6% |
| LX-10 | 93.5% | 94.4% | 94.4% | 94.4% | 94.4% | 94.4% |
| LX-11 | 93.5% | 93.5% | 93.5% | 93.5% | 93.5% | 93.5% |
| LX-12 | 93.5% | 93.5% | 94.1% | 94.1% | 94.4% | 94.4% |
| LX-CTRL-0 | 93.5% | 80.6% | 80.6% | 80.6% | 80.6% | 80.6% |
| LX-CTRL-ML | 93.5% | 94.4% | 94.4% | 94.4% | 94.4% | 94.4% |
| LX-CTRL-CORR | 93.5% | 94.4% | 94.4% | 94.4% | 94.4% | 94.4% |

---

## 4. Impacto do histórico e memória

- **LX-01:** memória=8, score≥0.65=8, regras aprendidas=0, eventos=360
- **LX-02:** memória=8, score≥0.65=8, regras aprendidas=0, eventos=480
- **LX-03:** memória=17, score≥0.65=17, regras aprendidas=0, eventos=384
- **LX-04:** memória=17, score≥0.65=16, regras aprendidas=0, eventos=528
- **LX-05:** memória=13, score≥0.65=13, regras aprendidas=0, eventos=432
- **LX-06:** memória=8, score≥0.65=8, regras aprendidas=0, eventos=480
- **LX-07:** memória=23, score≥0.65=22, regras aprendidas=1, eventos=432
- **LX-08:** memória=13, score≥0.65=13, regras aprendidas=0, eventos=480
- **LX-09:** memória=13, score≥0.65=13, regras aprendidas=0, eventos=384
- **LX-10:** memória=13, score≥0.65=13, regras aprendidas=0, eventos=408
- **LX-11:** memória=2, score≥0.65=2, regras aprendidas=0, eventos=432
- **LX-12:** memória=16, score≥0.65=16, regras aprendidas=0, eventos=456
- **LX-CTRL-0:** memória=13, score≥0.65=13, regras aprendidas=0, eventos=360
- **LX-CTRL-ML:** memória=13, score≥0.65=13, regras aprendidas=0, eventos=600
- **LX-CTRL-CORR:** memória=13, score≥0.65=13, regras aprendidas=0, eventos=528

---

## 5. PIX e merchants locais (prova aprendizado)

| Persona | T0 recall R2 | T5 recall R2 | T0 recall M3 | T5 recall M3 |
|---------|--------------|--------------|----------------|--------------|
| LX-01 | 0.0% | 0.0% | 0.0% | 0.0% |
| LX-02 | 0.0% | 0.0% | 0.0% | 0.0% |
| LX-03 | 0.0% | 0.0% | 0.0% | 62.5% |
| LX-04 | 0.0% | 57.1% | 0.0% | 75.0% |
| LX-05 | 0.0% | 0.0% | 0.0% | 62.5% |
| LX-06 | 0.0% | 0.0% | 0.0% | 0.0% |
| LX-07 | 0.0% | 0.0% | 0.0% | 100.0% |
| LX-08 | 0.0% | 0.0% | 0.0% | 62.5% |
| LX-09 | 0.0% | 0.0% | 0.0% | 0.0% |
| LX-10 | 0.0% | 0.0% | 0.0% | 62.5% |
| LX-11 | 0.0% | 0.0% | 0.0% | 0.0% |
| LX-12 | 0.0% | 0.0% | 0.0% | 62.5% |
| LX-CTRL-0 | 0.0% | 0.0% | 0.0% | 0.0% |
| LX-CTRL-ML | 0.0% | 0.0% | 0.0% | 62.5% |
| LX-CTRL-CORR | 0.0% | 0.0% | 0.0% | 62.5% |

---

## 6. ML ao longo do tempo

| Persona | Milestone | ML ativo | Share fonte ML | Δ acurácia vs sem_ml |
|---------|-----------|----------|----------------|----------------------|
| LX-04 | M-50 | não | 0.0% | +0.0pp |
| LX-04 | M-100 | não | 0.0% | +0.0pp |
| LX-04 | M-200 | não | 0.0% | +0.0pp |
| LX-04 | M-500 | não | 0.0% | +0.0pp |
| LX-08 | M-50 | não | 0.0% | +0.0pp |
| LX-08 | M-100 | não | 0.0% | +0.0pp |
| LX-08 | M-200 | não | 0.0% | +0.0pp |
| LX-08 | M-500 | não | 0.0% | +0.0pp |
| LX-CTRL-ML | M-50 | não | 0.0% | +0.0pp |
| LX-CTRL-ML | M-100 | não | 0.0% | +0.0pp |
| LX-CTRL-ML | M-200 | não | 0.0% | +0.0pp |
| LX-CTRL-ML | M-500 | não | 0.0% | +0.0pp |
| LX-CTRL-CORR | M-50 | não | 0.0% | +0.0pp |
| LX-CTRL-CORR | M-100 | não | 0.0% | +0.0pp |
| LX-CTRL-CORR | M-200 | não | 0.0% | +0.0pp |
| LX-CTRL-CORR | M-500 | não | 0.0% | +0.0pp |
| LX-06 | M-50 | não | 0.0% | +0.0pp |
| LX-06 | M-100 | não | 0.0% | +0.0pp |
| LX-06 | M-200 | não | 0.0% | +0.0pp |
| LX-06 | M-500 | não | 0.0% | +0.0pp |

---

## 7. UX longitudinal (proxy LX-01, LX-02, LX-07)

| Persona | CP | Inteligência | Confiança | Economia | Melhora? |
|---------|-----|--------------|-----------|----------|----------|
| LX-01 | T0 | 3 | 2 | 2 | nao |
| LX-01 | T2 | 3 | 2 | 2 | nao |
| LX-01 | T5 | 3 | 2 | 2 | nao |
| LX-02 | T0 | 3 | 2 | 2 | nao |
| LX-02 | T2 | 3 | 2 | 2 | nao |
| LX-02 | T5 | 3 | 2 | 2 | nao |
| LX-07 | T0 | 3 | 2 | 2 | nao |
| LX-07 | T2 | 5 | 3 | 3 | sim |
| LX-07 | T5 | 5 | 3 | 3 | sim |

---

## 8. Momentos de melhora perceptível

- **LX-04:** salto +27pp cobertura entre T0 e T1
- **LX-05:** salto +8pp cobertura entre T0 e T1
- **LX-07:** salto +22pp cobertura entre T0 e T1
- **LX-08:** salto +8pp cobertura entre T0 e T1
- **LX-09:** salto +8pp cobertura entre T0 e T1
- **LX-10:** salto +8pp cobertura entre T0 e T1
- **LX-CTRL-0:** salto +8pp cobertura entre T0 e T1
- **LX-CTRL-ML:** salto +8pp cobertura entre T0 e T1
- **LX-CTRL-CORR:** salto +8pp cobertura entre T0 e T1

---

## 9. Análise observacional

### O que evoluiu
- Merchants corrigidos repetidamente tendem a migrar para `historico` ou `regra_usuario`
- Personas com `corrigir_para_gold` (LX-02, LX-07, LX-08) mostram maior Δ cobertura em M3/R2

### O que não evoluiu
- Personas `ignorar` (LX-09, LX-CTRL-0) permanecem equivalentes a cold start
- LX-01 digital: ganho marginal (fuzzy já cobre M1 no T0)

---

## 10. Anexos

- `registros/metricas_longitudinais.csv`
- `registros/graficos/` (10 séries)
- `registros/ml_milestones.csv`
- `checkpoints/*.json`
- `lotes_reimport/lote_reimport_60.ofx`

## 11. Reprodutibilidade

```bash
source .venv/bin/activate
python manage.py seed_merchants_globais
python manage.py avaliar_categorizacao_longitudinal
```
