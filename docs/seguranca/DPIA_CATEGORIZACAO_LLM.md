# DPIA — Categorização assistida por IA (Gemini)

> Documento operacional (stub). Revisão jurídica recomendada antes de escala enterprise.

## Descrição do tratamento

Sugestão de categoria para transações financeiras de baixa confiança do pipeline híbrido, via Google Gemini.

## Dados enviados

- Descrição normalizada (truncada, sem PII explícita)
- Tipo da transação, faixa de valor
- Slugs de categorias disponíveis do usuário

## Dados não enviados

- Valor exato, CPF, e-mail, arquivo OFX bruto
- Prompts/respostas completos não são persistidos

## Base legal (indicativa)

Legítimo interesse / execução de contrato, com transparência na política de privacidade e oposição via `privacidade@`.

## Riscos e mitigação

| Risco | Mitigação |
|-------|-----------|
| Transferência internacional (EUA) | Subprocessador documentado; minimização de dados |
| Prompt injection | Delimitadores, truncamento, schema JSON, revisão humana |
| Vazamento em logs | Hash de merchant; sem descrição em logs |

## Retenção

Métricas agregadas em `LLMRequestLog` — 90 dias (`purge_retention_data`).
