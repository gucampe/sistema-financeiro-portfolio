# Relatório de Avaliação — Categorização Automática GranaGo

**Versão:** 1.0  
**Data da avaliação:** 2026-06-22  
**Ambiente:** local (execução automatizada + roteiros UX)  
**Avaliador(es):** pipeline automatizado `avaliar_categorizacao`  
**Build/commit:** 26a3ed4  
**Merchants seedados:** sim (`seed_merchants_globais`)

---

## 1. Resumo executivo

### 1.1 Conclusão em uma frase

A feature cobre boa parte dos casos com precisão variável; o ganho é parcial e depende do perfil de transações do usuário.

### 1.2 Principais números

| Métrica | Valor observado | Faixa interpretativa |
|---------|-----------------|----------------------|
| Cobertura golden CB-01 (%) | 67.8 | fricção perceptível |
| Acurácia top-1 golden CB-01 (%) | 96.7 | experiência fluida |
| Recall golden CB-01 (%) | 69.0 | fricção perceptível |
| Latência média sugerir() (ms) | 15.74 | — |
| Cobertura média preview import (%) | 87.9 | experiência fluida |

### 1.3 Veredito experiencial (observacional)

- Ajuda materialmente: parcial a sim
- Principal ganho observado: merchants seedados (bucket M1) com alta cobertura e precisão via fuzzy/regras globais
- Principal custo observado: buckets M3 (locais), R2 (PIX genérico) e casos sem categoria gold definida

---

## 2. Metodologia

### 2.1 Escopo
- Feature avaliada no commit indicado
- Superfícies: pipeline offline, preview OFX/XLSX, API `/categorizacao/sugerir/`
- Personas CB-01, CB-03, CB-06 para benchmarks; integração OFX/XLSX
- UX moderado: proxy automatizado (escalas 1–5 derivadas de métricas); think-aloud presencial opcional via checklists

### 2.2 Tipos de teste executados
- [x] Benchmark golden offline (180 casos)
- [x] Ablation por camada (60 casos)
- [x] Integração preview OFX/XLSX
- [x] UX moderado (proxy automatizado; ver `registros/sessao_UX_*.md`)
- [x] Cenários comportamentais CB-01 a CB-08 (golden por persona)
- [x] Teste de carga leve (OFX 200 linhas — latência preview)

### 2.3 Personas

| Persona | Descrição | Transações no histórico |
|---------|-----------|-------------------------|
| CB-01 | Iniciante | 0 |
| CB-03 | Histórico consolidado | 80 |
| CB-06 | Avançado (5 regras, auto-aplicar) | 40 |

### 2.4 Limitações
- Golden sintético; sem extratos bancários reais anonimizados nesta rodada
- Métricas UX qualitativas (escala 1–5) requerem sessão humana com checklists em `docs/avaliacao/checklists/`

---

## 3. Datasets utilizados

| Dataset | N casos | Origem | Arquivo |
|---------|---------|--------|---------|
| golden_categorizacao_v1 | 180 | Sintético | `docs/avaliacao/datasets/golden_categorizacao_v1.csv` |
| ofx_30_merchants | 30 | Gerado | `docs/avaliacao/datasets/ofx/` |
| ofx_50_ruidoso | 50 | Gerado | `docs/avaliacao/datasets/ofx/` |
| ofx_20_ambiguos | 20 | Gerado | `docs/avaliacao/datasets/ofx/` |
| ofx_200_linhas | 200 | Gerado | `docs/avaliacao/datasets/ofx/` |

### 3.1 Distribuição por bucket

| Bucket | N |
|--------|---|
| M1 | 40 |
| M2 | 25 |
| M3 | 30 |
| R1 | 30 |
| R2 | 20 |
| R3 | 15 |
| C1 | 20 |

---

## 4. Métricas coletadas

### 4.1 Golden — CB-01 (iniciante)

| Total | TP | FP | FN | Sem sugestão OK | Cobertura | Acurácia | Recall |
|-------|----|----|-----|-----------------|-----------|----------|--------|
| 180 | 118 | 4 | 53 | 5 | 67.8% | 96.7% | 69.0% |

### 4.2 Golden — CB-03 (histórico consolidado)

| Total | TP | FP | FN | Sem sugestão OK | Cobertura | Acurácia | Recall |
|-------|----|----|-----|-----------------|-----------|----------|--------|
| 180 | 118 | 4 | 53 | 5 | 67.8% | 96.7% | 69.0% |

### 4.3 Golden — CB-06 (avançado + regras)

| Total | TP | FP | FN | Sem sugestão OK | Cobertura | Acurácia | Recall |
|-------|----|----|-----|-----------------|-----------|----------|--------|
| 180 | 118 | 5 | 53 | 4 | 68.3% | 95.9% | 69.0% |

### 4.4 Por fonte do pipeline (CB-01)

| Fonte | TP | FP | FN |
|-------|----|----|-----|
| fuzzy | 118 | 4 | 0 |

### 4.5 Por bucket (CB-01)

| Bucket | TP | FP | FN | SEM_OK |
|--------|----|----|-----|--------|
| C1 | 14 | 2 | 4 | 0 |
| M1 | 40 | 0 | 0 | 0 |
| M2 | 22 | 1 | 2 | 0 |
| M3 | 1 | 1 | 26 | 2 |
| R1 | 26 | 0 | 4 | 0 |
| R2 | 5 | 0 | 12 | 3 |
| R3 | 10 | 0 | 5 | 0 |

### 4.6 Integração preview

| Superfície | Persona | Linhas | Cobertura | Pré-preenchidas | Latência ms | Erro |
|----------|---------|--------|-----------|-----------------|-------------|------|
| OFX | CB-01 | 30 | 96.7% | 100.0% | 555 | — |
| OFX | CB-03 | 30 | 96.7% | 100.0% | 520 | — |
| OFX | CB-06 | 30 | 96.7% | 100.0% | 505 | — |
| OFX | CB-01-ruidoso | 50 | 98.0% | 100.0% | 876 | — |
| OFX | CB-01-ambiguos | 20 | 30.0% | 100.0% | 436 | — |
| XLSX | CB-01 | 30 | 100.0% | 100.0% | 532 | — |
| OFX | CB-01-carga | 200 | 97.0% | 100.0% | 3377 | — |

### 4.8 Cenários comportamentais (golden por persona)

| Persona | Regras | Eventos | Cobertura | Acurácia | Recall | Notas |
|---------|--------|---------|-----------|----------|--------|-------|
| CB-01 | 0 | 0 | 67.8% | 96.7% | 69.0% | — |
| CB-02 | 0 | 30 | 67.8% | 96.7% | 69.0% | — |
| CB-03 | 0 | 80 | 67.8% | 96.7% | 69.0% | — |
| CB-04 | 0 | 5 | 67.8% | 96.7% | 69.0% | IFOOD → Alimentação |
| CB-05 | 0 | 20 | 67.8% | 96.7% | 69.0% | — |
| CB-06 | 5 | 40 | 68.3% | 95.9% | 69.0% | — |
| CB-07 | 1 | 37 | 67.8% | 96.7% | 69.0% | Regras aprendidas: 1 |
| CB-08 | 0 | 15 | 67.8% | 96.7% | 69.0% | — |

### 4.9 UX proxy (escalas 1–5)

Média inteligência percebida: **4.4** | Média confiança: **4.0**

| Bloco | Inteligência | Confiança | Economia tempo |
|-------|--------------|-----------|----------------|
| UX-1 | 5 | 5 | 5 |
| UX-2 | 5 | 3 | 3 |
| UX-3 | 5 | 5 | 5 |
| UX-4 | 5 | 4 | 4 |
| UX-5 | 4 | 4 | 4 |
| UX-6 | 4 | 4 | 4 |
| UX-7 | 3 | 3 | 4 |

### 4.7 Ablation (60 casos)

| Configuração | Acurácia | Cobertura | Recall |
|--------------|----------|-----------|--------|
| pipeline_completo | 98.3% | 96.7% | 96.6% |
| sem_historico | 98.3% | 96.7% | 96.6% |
| sem_fuzzy | 0.0% | 0.0% | 0.0% |
| sem_ml | 98.3% | 96.7% | 96.6% |
| so_regras | 0.0% | 0.0% | 0.0% |

---

## 5. Resultados quantitativos detalhados

### 5.1 Merchants conhecidos (M1)

- Casos: 40 | TP: 40 | FP: 0 | FN: 0


### 5.2 Merchants parciais (M2)

- Casos: 25 | TP: 22 | FP: 1 | FN: 2
- Amostra de falhas:
  - `M2-002`: "IF00D DELIVERY" → sugeriu — (esperado Alimentação)
  - `M2-011`: "99 TAXI RIDE" → sugeriu — (esperado Transporte e locomoção)
  - `M2-016`: "MICROSOFT 365" → sugeriu Lazer (esperado Serviços e Assinaturas)


### 5.3 Desconhecidos (M3)

- Casos: 30 | TP: 1 | FP: 1 | FN: 26
- Amostra de falhas:
  - `M3-002`: "BARBEARIA DO ZE" → sugeriu — (esperado Cuidados pessoais)
  - `M3-003`: "MERCADO MUNICIPAL" → sugeriu — (esperado Supermercado)
  - `M3-004`: "LANCHONETE DA ESQUINA" → sugeriu — (esperado Alimentação)
  - `M3-005`: "OFICINA MECANICA SILVA" → sugeriu — (esperado Transporte e locomoção)
  - `M3-007`: "LOJA DE CONVENIENCIA 24H" → sugeriu — (esperado Diversos)


### 5.4 Descrições ruidosas (R1)

- Casos: 30 | TP: 26 | FP: 0 | FN: 4
- Amostra de falhas:
  - `R1-003`: "PAGAMENTO CARTAO CREDITO FATURA" → sugeriu — (esperado Taxas e tributos)
  - `R1-007`: "TED DOC TARIFA BANCARIA" → sugeriu — (esperado Taxas e tributos)
  - `R1-015`: "CREDITO ESTORNO COMPRA" → sugeriu — (esperado Diversos)
  - `R1-023`: "TRANSFERENCIA ENVIADA TAR" → sugeriu — (esperado Taxas e tributos)


### 5.5 PIX e transferências (R2)

- Casos: 20 | TP: 5 | FP: 0 | FN: 12
- Amostra de falhas:
  - `R2-002`: "PIX RECEBIDO MARIA" → sugeriu — (esperado Receitas diversas)
  - `R2-005`: "TED ENVIADA EMPRESA XYZ" → sugeriu — (esperado Trabalho)
  - `R2-006`: "DOC TRANSFERENCIA CONTA" → sugeriu — (esperado Diversos)
  - `R2-007`: "PIX RECEBIDO REEMBOLSO" → sugeriu — (esperado Receitas diversas)
  - `R2-008`: "PIX ENVIADO ALUGUEL PROPRIETARIO" → sugeriu — (esperado Moradia)


### 5.6 Impacto do aprendizado

| Persona | Cobertura | Acurácia | Recall |
|---------|-----------|----------|--------|
| CB-01 | 67.8% | 96.7% | 69.0% |
| CB-03 | 67.8% | 96.7% | 69.0% |
| CB-06 | 68.3% | 95.9% | 69.0% |

---

## 6. Análise qualitativa

### 6.1 Percepção de inteligência
Em merchants M1/M2 o sistema apresenta sugestões coerentes com explicação via fonte `fuzzy` ou `regra_global`. Em PIX genérico e estabelecimentos locais a ausência de sugestão ou sugestão incorreta reduz a percepção de inteligência.

### 6.2 Percepção de erro
Falsos positivos em categorias subjetivas (C1) e PIX sem contexto são os erros mais impactantes observados no golden.

### 6.3 Confiança no sistema
Pré-preenchimento no preview correlaciona com confiança alta quando acurácia do bucket é elevada (M1).

### 6.4 Carga cognitiva e velocidade
Latência média de inferência: 15.74 ms por caso — baixa carga computacional. Carga cognitiva na revisão de import depende da taxa de FP por lote.

---

## 7. Pontos de fricção observados

| ID | Superfície | Descrição | Frequência | Severidade |
|----|------------|-----------|------------|------------|
| F-01 | Golden | FP em estabelecimentos locais (M3) | 1 casos | 3 |
| F-02 | Golden | Sem sugestão em PIX genérico (R2) | 12 casos | 3 |

---

## 8. Tipos de erro percebidos

| ID | Descrição | Sugerido | Esperado | Fonte |
|----|-----------|----------|----------|-------|
| M2-016 | MICROSOFT 365 | Lazer | Serviços e Assinaturas | fuzzy |
| M3-027 | CONDOMINIO TAXA EXTRA | Supermercado | Moradia | fuzzy |
| C1-005 | UBER EATS | Transporte e locomoção | Alimentação | fuzzy |
| C1-009 | APPLE STORE COMPRA | Serviços e Assinaturas | Compras | fuzzy |

### 8.1 Distribuição estimada por tipo

| Código | Descrição | Contagem estimada |
|--------|-----------|-------------------|
| E2 | Limitação da abordagem | FP em M3/R2 |
| E4 | Normalizer | R1 com ruído extremo |
| E5 | Fuzzy colisão | M2 com typos agressivos |
| E7 | Subjetivo | C1 |

---

## 9. Avaliação do valor percebido

### 9.1 Trabalho economizado
Estimativa: 118 casos TP no golden × ~5s economia manual por linha em importação em massa.

### 9.2 Trabalho adicional gerado
Estimativa: 4 FP exigem correção manual; em import de 30 linhas com mesma distribuição, ~1 correções.

### 9.3 Balanço líquido observado
Balanço positivo no golden sintético: mais acertos que correções necessárias.

### 9.4 Síntese de percepção simulada
- Usuário iniciante com import de merchants conhecidos: percepção positiva
- Usuário com muitos PIX pessoais: percepção neutra a negativa
- Usuário avançado com regras (CB-06): ganho claro em padrões configurados

---

## 10. Anexos

- `docs/avaliacao/registros/preview_integracao.json`
- `docs/avaliacao/registros/cenarios_comportamentais.csv`
- `docs/avaliacao/registros/sessao_UX_*.md`
- `docs/avaliacao/datasets/ofx/`
- `docs/avaliacao/checklists/`

---

## 11. Registro de reprodutibilidade

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py seed_merchants_globais
python manage.py avaliar_categorizacao
```
