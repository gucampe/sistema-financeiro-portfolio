# Input monetário padronizado (pt-BR)

## Visão geral

Todos os campos de valor monetário do sistema usam a mesma máscara **R$ 0,00** em tempo real, com envio ao backend em decimal com ponto (`1234.56`).

## Frontend

| Arquivo | Função |
|---------|--------|
| `static/js/moeda_input.js` | Máscara, API global `window.MoedaInput` |
| `static/css/input.css` | Classe `.input-moeda` (alinhamento à direita) |
| `templates/base.html` | Carrega `moeda_input.js` em todas as páginas |

### Como usar em templates

```html
<input type="text" name="valor" class="input input-moeda"
       data-moeda-input autocomplete="off" inputmode="decimal">
```

Campo **opcional** (ex.: pagamento parcial de fatura — vazio = valor total):

```html
<input ... data-moeda-input data-moeda-allow-empty="1">
```

### API JavaScript

- `MoedaInput.init(input)` — aplica máscara em um elemento
- `MoedaInput.initAll(root?)` — varre `[data-moeda-input]`
- `MoedaInput.setValueFromDecimal(input, "42.50")` — preenche ao editar
- `MoedaInput.parseToDecimalString("R$ 1,23")` → `"1.23"`

No **submit** de qualquer formulário, valores são convertidos automaticamente (fase capture).

### Campos atualizados

| Módulo | Campo | Template / origem |
|--------|-------|-------------------|
| Transações | `valor` | `transacoes/partials/adicionar_transacao.html` |
| Transações | `valor` | `TransacaoForm` (página editar) |
| Transações | valor por linha | `importar_ofx.js`, `importar_planilha.js` |
| Contas | `saldo_inicial` | `contas/partials/modal_conta.html` |
| Cartões | `limite` | `cartoes/partials/modal_cartao.html` |
| Cartões | `valor` (pagar fatura) | `cartoes/fatura_detalhe.html` |

**Categorias** e **relatórios** não possuem inputs de valor monetário (apenas exibição com `{% load moeda %}`).

## Backend

| Arquivo | Função |
|---------|--------|
| `core/moeda.py` | `parse_decimal_moeda_br()` |
| `core/forms_ui.py` | `MoedaTextInput`, `MOEDA_INPUT_CLASSES` |
| `transacoes/forms.py` | `clean_valor()` |
| `contas/views.py` | saldo inicial na criação |
| `cartoes/views.py` | limite do cartão, pagamento de fatura |

O parser aceita tanto o formato enviado pelo JS (`1234.56`) quanto digitação BR (`1.234,56`, `R$ 10,50`).

## Comportamento da máscara

- Centavos acumulados à direita via teclado (`keydown` / `beforeinput`), **sem** extrair dígitos do texto `R$ 0,00` (evita `3` virar `R$ 30,00`).
- Digitação incremental: `1` → `R$ 0,01`, `12` → `R$ 0,12`, `3` → `R$ 0,03`, etc.
- Backspace/Delete remove o último dígito.
- Valor interno em `data-moeda-cents` no input.
- Máximo de 12 dígitos (até R$ 9.999.999.999,99).
- Foco em campo obrigatório vazio exibe `R$ 0,00`.

## Testes

```bash
python manage.py test core.tests.test_moeda
```
