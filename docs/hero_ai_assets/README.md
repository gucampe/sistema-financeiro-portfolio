<!-- Data de criação: 2026-07-31 -->
# Hero AI Assets — GranaGo

Pasta única com artefatos visuais para gerar uma imagem profissional do **Hero** da landing, sem precisar reexplorar o repositório.

**Ferramenta de captura:** Playwright (`docs/hero_ai_assets/_capture_screenshots.py`), escala 2× (alta resolução).  
**Servidor local usado:** `http://127.0.0.1:8000`  
**Usuário de desenvolvimento (app):** `hero-assets@e2e.granago.test` / senha E2E `e2e-pass-123` (persona com dados seeded).

---

## Estrutura

```
hero_ai_assets/
├── 01_brand/          Logo + paleta + tipografia
├── 02_landing/        Screenshots da landing (desktop + mobile)
├── 03_app/            Screenshots reais do SaaS autenticado
├── 04_components/     Recortes da linguagem UI
├── 05_mockups/        Mockups HTML (dashboard + floats do hero)
├── 06_reference/      Fotos institucionais
├── _capture_screenshots.py
└── README.md
```

---

## 01_brand — Identidade

| Arquivo | Importância | Notas |
|---------|-------------|--------|
| `logo.svg` | **Máxima** | Símbolo oficial (carteira verde). Preferir sempre o SVG. |
| `logo.png` | Baixa | 32×32 — só para favicon/OG pequeno. |
| `logo.ico` / `favicon.ico` | Baixa | Favicon ICO 48×48. |
| `brand_colors.md` | **Alta** | Paleta HEX, tipografia, resumo visual. |

**Representam melhor a marca:** `logo.svg` + verdes `#22c55e` / `#16a34a` + tipografia Plus Jakarta Sans (landing).

Não há wordmark vetorial separado nem versão monocromática oficial no repositório — o nome “GranaGo” aparece tipograficamente ao lado do símbolo.

---

## 02_landing — Landing atual

Screenshots Playwright (desktop 1440×900 @2x, mobile 390×844 @2x). Reveal CSS forçado para seções animadas ficarem visíveis.

| Arquivo | Conteúdo |
|---------|----------|
| `01-home-full.png` | Página inteira (scroll) |
| `02-hero.png` | Seção `#hero` (copy + hero visual) |
| `03-programa.png` | Programa Primeiros Donos |
| `04-formulario.png` | Modal de captura (nome/e-mail/WhatsApp) |
| `05-footer.png` | Rodapé |
| `01-home-mobile.png` | Landing completa em viewport mobile |

**Mais importantes para arte do Hero:** `02-hero.png`, `01-home-full.png`, `03-programa.png`.

**Atenção:** `static/img/landing/hero-person.webp` **ainda não existe** no projeto. No hero real há silhueta + floating UI; a foto da pessoa é placeholder até o asset ser publicado. Comentário de template Django pode aparecer no HTML-fonte; ignore na arte.

---

## 03_app — Telas reais do produto

Capturas autenticadas com dados de demo (não vazias).

| Arquivo | Tela |
|---------|------|
| `01-dashboard.png` | Visão Geral (KPIs, patrimônio, cartões, orçamento) |
| `02-transacoes.png` | Transações |
| `03-categorias.png` | Categorias |
| `04-relatorios.png` | Entradas × Saídas (fluxo de caixa) |
| `05-contas.png` | Contas |
| `06-cartoes.png` | Cartões |
| `07-orcamentos.png` | Orçamentos |
| `08-configuracoes.png` | Configurações |
| `09-importacao-ofx.png` | Modal Importar OFX |

**Mais importantes para coerência UI no Hero:** `01-dashboard.png`, `09-importacao-ofx.png`, `02-transacoes.png`, `07-orcamentos.png`.

---

## 04_components — Linguagem visual

Recortes do app:

| Arquivo | O que mostra |
|---------|----------------|
| `sidebar.png` | Logo + nav + CTA verde |
| `header.png` | Topbar do app |
| `buttons.png` | Secundário (Filtros) + primários verdes |
| `cards.png` | KPIs Receitas / Despesas / Resultado |
| `graphs.png` | Card de orçamento / barras de progresso |
| `badges.png` / `chips.png` | Tags semânticas (ex.: Estourado) |
| `inputs.png` | Painel de filtros |
| `modals.png` | Modal de importação OFX |

Use estes arquivos para **raios, sombras, verde de botão e hierarquia tipográfica** — não para inventar um dashboard genérico.

---

## 05_mockups — Mockups existentes

| Arquivo | Notas |
|---------|--------|
| `mockup_dashboard.html` | **Principal** — chrome do app (sidebar, KPIs, chips IA) usado na landing |
| `hero_visual.html` / `hero.html` | Estrutura do Hero Visual (pessoa + floats) |
| `float/*.html` | Cards flutuantes: iFood/Uber style, chart, insight R$, chips IA |

Não há PNG/WebP/SVG de mockup de marketing separados além do HTML acima (e dos screenshots em `02_`/`03_`).

---

## 06_reference — Institucional

| Arquivo | Relevância |
|---------|------------|
| `founder.png` | **Alta** — foto do fundador (768×1024), usada na landing |
| `wallpaper.jpg` | **Baixa** — wallpaper genérico do projeto; **não** representa a identidade GranaGo. Incluído só por existir no repo; preferir **não** enviar à IA. |

Não foram copiados assets do Django Admin.

**Ausente (relevante):** `hero-person.webp` — imagem humana prevista para o Hero Visual.

---

## Quais assets representam melhor a identidade

1. **Logo carteira verde** (`01_brand/logo.svg`)
2. **Verde brand** `#22c55e` → `#16a34a` em CTAs
3. **Fundos mint/branco** `#fbfefc` / `#f8fcf9` / `#ffffff`
4. **Tipografia display** Plus Jakarta Sans, tracking apertado
5. **UI glass/float** da landing + cards brancos arredondados do app
6. **Dashboard real** com sidebar e KPIs verdes/vermelhos
7. **Foto founder** (tom humano, não stock genérico de “finanças”)

Evitar: purple, neon, dark-mode bancário, ilustrações 3D genéricas de moedas.

---

## Envie estes arquivos primeiro

Lista máxima de **10** essenciais para uma IA geradora:

1. `01_brand/logo.svg`
2. `01_brand/brand_colors.md`
3. `02_landing/02-hero.png`
4. `02_landing/01-home-full.png`
5. `03_app/01-dashboard.png`
6. `05_mockups/mockup_dashboard.html`
7. `04_components/buttons.png`
8. `04_components/cards.png`
9. `04_components/sidebar.png`
10. `06_reference/founder.png`

**Complementares (2º lote):** `02_landing/03-programa.png`, `03_app/09-importacao-ofx.png`, `05_mockups/float/*`, `04_components/graphs.png`, `02_landing/01-home-mobile.png`.

---

## Como regenerar screenshots

Com `make dev` (ou `runserver`) em `:8000` e `.venv` ativa:

```bash
source .venv/bin/activate
python docs/hero_ai_assets/_capture_screenshots.py
```

Requer Playwright + Chromium instalados (`requirements-dev.txt`).

---

## Fonte documental extra

Pesquisa consolidada da marca: `docs/marca/BRIEFING_DESIGN_ARTE_HERO.md` e `docs/marca/brand-context.md` (fora desta pasta).
