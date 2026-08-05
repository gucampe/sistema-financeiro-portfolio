# GranaGo — Paleta e identidade visual

**Data de criação:** 2026-07-31  
**Fonte:** `static/landing/css/landing.css`, `tailwind.config.js`, `docs/marca/brand-context.md`

---

## Resumo da identidade

- **Nome:** GranaGo  
- **Símbolo:** carteira verde (logo SVG oficial)  
- **Tom:** próximo, direto, sem jargão — humano e sério  
- **Sensação visual:** limpo, mint/esverdeado suave, crescimento e ordem financeira  
- **Não usar:** purple-on-white, glow excessivo, estética de banco pomposa ou de “app de jogos”

---

## Cores principais (brand)

| Token / uso | HEX | Notas |
|-------------|-----|--------|
| Verde brand | `#22c55e` | Principal — CTAs, links, foco, progresso (`--lp-green` / `brand-500`) |
| Verde escuro | `#16a34a` | Hover / ênfase (`--lp-green-dark` / `brand-600`) |
| Verde profundo | `#15803d` | Acentos fortes (`--lp-green-deep`) |

Gradiente típico de botão/marca: `#22c55e` → `#16a34a`.

---

## Cores secundárias (mint / superfícies brand)

| Token | HEX | Uso |
|-------|-----|-----|
| Mint | `#ecfdf5` | Fundo suave, bands |
| Mint soft | `#f8fcf9` | Backgrounds leves |
| Mint band | `#eef8f1` | Faixas de seção |
| Surface | `#fbfefc` | Superfície principal |
| Surface alt | `#f4faf6` | Alternância de seções |

Hero / banda clara (landing): gradiente `#f3faf5` → `#fbfefc` → `#ffffff`.

CTA escuro (landing): gradiente `#0b1220` → `#123524` → `#14532d`.

---

## Neutros e texto

| Token | HEX | Uso |
|-------|-----|-----|
| Ink | `#0b1220` | Títulos fortes |
| Ink 2 | `#1e293b` | Texto principal / slate-800 |
| Body | `#475569` | Corpo (slate-600) |
| Muted | `#64748b` | Legendas (slate-500) |
| Line | `#e3efe8` | Bordas suaves esverdeadas |
| Line strong | `#cfe6d7` | Bordas mais visíveis |
| White | `#ffffff` | Fundos / cards |

App (Tailwind): texto em escala `gray`/`slate` (`#334155` citado no brand-context como texto principal).

---

## Semântica (app)

| Significado | Direção de cor |
|-------------|----------------|
| Receitas | Verde / esmeralda |
| Despesas | Vermelho / rosa |
| Categorias | Paleta diversa (azuis, verdes, índigos, vermelhos, laranjas, rosas, cinzas) |

---

## Backgrounds recomendados para arte

1. Branco puro `#ffffff`  
2. Mint soft `#f8fcf9` / surface `#fbfefc`  
3. Gradiente vertical claro: `#f3faf5` → `#ffffff`  
4. Evitar fundo flat único sem nuance — a landing usa leve gradiente mint

---

## Tipografia

| Contexto | Família | Notas |
|----------|---------|--------|
| Landing | **Plus Jakarta Sans** | `font-family: "Plus Jakarta Sans", system-ui, sans-serif` |
| App (config) | Inter / system | Base do produto autenticado |
| Fallback | `system-ui`, sans-serif | |

Pesos típicos na landing: semibold/bold em headlines; regular/medium no corpo. Tracking apertado em títulos (`tracking-tight`).

---

## Raios e sombra (linguagem UI)

- Raios: `0.75rem` → `1.75rem` (`--lp-radius-*`)  
- Sombras suaves slate (`rgba(15, 23, 42, …)`), CTA com glow verde `rgba(22, 163, 74, 0.28)`  
- Floats do hero: glass `rgba(255,255,255,0.74)` + blur ~14px

---

## Arquivos de marca nesta pasta

| Arquivo | Uso |
|---------|-----|
| `logo.svg` | **Principal** — enviar à IA |
| `logo.png` | Favicon/pequeno (32×32) — complementar |
| `favicon.ico` | Favicon ICO (48×48) |

Não há outras variações oficiais de logo no repositório além destas.
