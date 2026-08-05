<!-- Data de criação: 2026-07-30 -->
# Briefing de Design e Arte — GranaGo

Documento de pesquisa consolidada a partir do código, assets e documentação existentes no repositório `sistema_financeiro`.  
**Escopo:** apenas fatos encontrados no projeto. Onde não houver evidência: **Não encontrado.**

---

## 1. Identidade visual

### Logo — arquivos e localização

| Arquivo | Caminho completo | Formato / dimensões |
|---------|------------------|---------------------|
| Logo SVG (principal) | `/home/gucampe/Documentos/Projetos/sistema_financeiro/static/img/icons/logo.svg` | SVG, `viewBox="0 0 245 272"`, width/height declarados 245×272 |
| Logo PNG | `static/img/icons/logo.png` | PNG 32×32, RGBA |
| Favicon ICO | `static/img/icons/logo.ico` | ICO 48×48, RGBA |

### Descrição do símbolo (SVG)

- Símbolo: **carteira verde** (confirmado em `docs/marca/brand-context.md`: “Logo: carteira verde”).
- Preenchimentos SVG observados: verdes `#1AB243`, `#1BB241`, `#1DB344`, `#0AAB2B`, `#03A11A`, `#13AC2E`, `#189328`; detalhe interno claro `#FBFEFC`.
- Forma: carteira com aba superior e detalhe circular (fecho/moeda) na área frontal.

### Versões / variações

- SVG vetorial (uso preferencial em favicon SVG e UI).
- PNG 32×32 (ex.: `og:image` na landing aponta para `logo.png`).
- ICO 48×48.
- **Não encontrado:** wordmark tipográfico separado, versão monocromática documentada, versão negativa formal, guidelines de clear-space em arquivo dedicado.

### Favicon

- App (`templates/base.html`): `rel="icon" type="image/svg+xml"` → `static/img/icons/logo.svg`
- Landing (`templates/landing/base_landing.html`): idem, `logo.svg`

### Uso do logotipo (no código)

- Header landing: `logo.svg` 36×36 + texto “GranaGo” (`text-brand-600`).
- Footer landing: `logo.svg` 32×32 + “GranaGo”.
- Sidebar app: logo + texto “GranaGo” (`.app-sidebar__brand`).
- Header mobile app: `.app-header-brand__mark` + texto.
- Mockup HTML da landing: logo 22×22 dentro do chrome do mockup.
- Open Graph / Twitter: `logo.png`.

### Proporções

- SVG intrínseco ≈ **245:272** (próximo a retrato vertical do símbolo da carteira).
- Em UI o símbolo é exibido em quadrados (22–36 px), não o wordmark completo embutido no SVG.

---

## 2. Paleta de cores

### Fonte de verdade

1. `tailwind.config.js` — tokens Tailwind (`brand`, `surface`, `fg`, `danger`, `warning`, `success`, `primary`).
2. `static/css/input.css` — CSS vars espelhando theme.
3. `static/landing/css/landing.css` — tokens `--lp-*` específicos da landing.
4. `docs/marca/brand-context.md` — descrição semântica da paleta.

### Primária / brand

| Token | HEX | RGB (aprox.) | Uso |
|-------|-----|--------------|-----|
| `brand.50` / `--lp-mint` | `#ecfdf5` | 236, 253, 245 | fundos mint, soft |
| `brand.100` | `#d1fae5` | 209, 250, 229 | — |
| `brand.200` | `#a7f3d0` | 167, 243, 208 | — |
| `brand.300` | `#6ee7b7` | 110, 231, 183 | — |
| `brand.400` | `#34d399` | 52, 211, 153 | accents / bars |
| `brand.500` / `--lp-green` / `--color-brand-500` | `#22c55e` | 34, 197, 94 | botões, gradientes, destaques |
| `brand.600` / `--lp-green-dark` / `--color-brand-600` | `#16a34a` | 22, 163, 74 | texto brand, hover, success DEFAULT |
| `brand.700` / `--lp-green-deep` / `--color-brand-700` | `#15803d` | 21, 128, 61 | textos/ênfases profundas |
| `brand.800` | `#166534` | 22, 101, 52 | — |
| `brand.900` | `#14532d` | 20, 83, 45 | fundos CTA escuros |

`primary.*` no Tailwind é **duplicata** da escala `brand`.

### Superfícies / backgrounds

| Token | HEX | Uso |
|-------|-----|-----|
| `surface.DEFAULT` / `--color-surface` | `#f4f5f7` | `.page-shell` do app |
| `surface.muted` | `#f1f5f4` | superfície muted |
| `surface.elevated` | `#ffffff` | elevado |
| `--lp-white` | `#ffffff` | landing |
| `--lp-surface` | `#fbfefc` | landing |
| `--lp-surface-alt` | `#f4faf6` | faixa dor |
| `--lp-mint-soft` | `#f8fcf9` | — |
| `--lp-mint-band` | `#eef8f1` | — |

### Textos / neutros (ink)

| Token | HEX | Uso |
|-------|-----|-----|
| `fg.DEFAULT` | `#334155` | texto app (slate-700) |
| `fg.muted` | `#64748b` | legendas |
| `fg.subtle` | `#475569` | — |
| `fg.oninverse` | `#f8fafc` | texto sobre fundo escuro |
| `--lp-ink` | `#0b1220` | títulos landing |
| `--lp-ink-2` | `#1e293b` | corpo forte |
| `--lp-body` | `#475569` | corpo |
| `--lp-muted` | `#64748b` | secundário |

Brand-context também cita escala slate `#334155` / `#64748b`.

### Bordas

| Token | Valor | Uso |
|-------|-------|-----|
| `--lp-line` | `#e3efe8` | bordas landing |
| `--lp-line-strong` | `#cfe6d7` | bordas mais fortes |
| Tailwind `gray-100`–`gray-300` | padrão | cards/inputs app |
| `danger.border` | `rgba(220, 38, 38, 0.25)` | — |
| `warning.border` | `rgba(245, 158, 11, 0.4)` | — |
| `success.border` | `rgba(22, 163, 74, 0.15)` | — |

### Semântica

| Papel | Token | HEX |
|-------|-------|-----|
| Sucesso | `success.DEFAULT` | `#16a34a` (+ soft `#ecfdf5`) |
| Erro / danger | `danger.DEFAULT` | `#dc2626` (+ soft `#fef2f2`) |
| Alerta / warning | `warning.DEFAULT` | `#f59e0b` (+ soft `#fffbeb`) |
| Tab despesa ativa | `bg-red-500` | classes utilitárias |
| Tab receita ativa | `bg-brand-600` | — |

### Categorias (safelist Tailwind)

Cores fixas em `tailwind.config.js` para categorias:

`#1D4ED8`, `#2563EB`, `#3B82F6`, `#059669`, `#10B981`, `#22C55E`, `#4F46E5`, `#6366F1`, `#DC2626`, `#EF4444`, `#F97316`, `#F59E0B`, `#EC4899`, `#4B5563`, `#6B7280`, `#9CA3AF`

### Logo (SVG) — verdes adicionais

`#1AB243`, `#1BB241`, `#1DB344`, `#0AAB2B`, `#03A11A`, `#13AC2E`, `#189328`, detalhe `#FBFEFC`.

### Accent

Não há token nomeado “accent” separado; o accent efetivo é a escala **brand/green**. Sidebar usa `--sidebar-accent: var(--color-brand-600)`.

---

## 3. Tipografia

### App (SaaS autenticado)

- **Configurado em** `tailwind.config.js` → `fontFamily.sans`: **Inter**, depois system stack (`ui-sans-serif`, `system-ui`, Segoe UI, Roboto, Helvetica Neue, Arial).
- **Carregamento Google Fonts de Inter:** **Não encontrado** em templates. Na prática o app tende a cair no fallback do sistema, salvo cache/CDN externo não versionado no repo.

### Landing

- Fonte: **Plus Jakarta Sans** (Google Fonts), pesos **400, 500, 600, 700, 800**.
- Aplicada em `.lp-main` (`static/landing/css/landing.css`).
- Link: `templates/landing/base_landing.html`.

### Escala tipográfica da landing (classes)

| Classe | Tamanho | Peso | Letter-spacing | Line-height | Uso |
|--------|---------|------|----------------|-------------|-----|
| `.lp-display` | `clamp(2.6rem, 6.2vw, 4rem)` | 600 | -0.045em | 1.02 | H1 hero |
| `.lp-headline` | `clamp(1.85rem, 3.8vw, 2.75rem)` | 600 | -0.038em | 1.12 | seções |
| `.lp-title` | `clamp(1.125rem, 2vw, 1.3125rem)` | 600 | -0.02em | 1.35 | subtítulos |
| `.lp-body` | `1.125rem` | — | — | 1.75 | corpo |
| `.lp-body-sm` | `1.0625rem` | — | — | 1.7 | corpo menor |
| `.lp-hero-sub > p` | `clamp(1.125rem, 2.1vw, 1.25rem)` | 400 | — | 1.65 | apoio hero |
| Brand wordmark UI | ~1.05–1.25rem | 600–700 | -0.02em | — | sidebar/header |

### App — tipografia utilitária

- Botões: `text-sm font-semibold`.
- Inputs: `text-sm`.
- Sidebar labels: ~0.8125–0.9375rem.

---

## 4. Componentes

Catalogados a partir de `static/css/input.css`, templates e docs.

### Botões (`input.css`)

| Classe | Aparência / variantes |
|--------|------------------------|
| `.btn` | base: rounded-lg, px-4 py-2.5, text-sm font-semibold |
| `.btn-primary` | gradiente brand-500→600, sombra verde, hover brightness |
| `.btn-primary-solid` | brand-600 sólido |
| `.btn-secondary` | borda gray, fundo branco |
| `.btn-slate` | gradiente slate |
| `.btn-emerald` | gradiente emerald |
| `.btn-danger` / `.btn-danger-soft` | vermelho |
| `.btn-dark` | gray-900 |
| `.btn-warning-soft` | amber soft |
| `.btn-ghost` | link brand |
| `.btn-sm` / `.btn-block` | tamanho / largura |
| Landing `.lp-btn-premium` | elevação hover + seta animada |

Estados: hover, active (`scale`), focus-visible ring brand, disabled opacity.

### Cards

- `.card` — rounded-2xl, branco/90, shadow-md, ring
- `.card-dense` — border gray, shadow-sm
- `.card-header` — border-b
- Landing: `.lp-card--offer`, `.lp-card--programa`, float cards glass

### Inputs / selects

- `.input` — rounded-lg, border gray-300, focus ring brand
- `.input-moeda` / `[data-moeda-input]` — alinhado à direita
- Select nativo com chevron Heroicons (data-URI)
- Combobox / `[data-combobox-trigger]`, `[data-cat-trigger]`
- Doc: `docs/ui/MOEDA_INPUT.md`

### Modais

- `.modal-overlay`, `.modal-panel`, `__body`, `__footer`
- JS: `static/js/modal.js` (`GranaGoModal`)
- Doc: `docs/ui/MODAIS.md`
- Fade 300ms; painel scale 95→100
- Exemplos: transação, cartão, conta, orçamento, captura landing, export

### Tabelas

- `.table-scroll` — overflow + ring
- Listas de histórico/faturas em templates de domínio

### Badges / chips / tabs

- Landing float: `.lp-float-chip`, badge, AI chip, indicator
- Tabs categorias: `.tab-cat--despesa-active`, `--receita-active`, `--inactive`

### Gráficos / dashboard

- Chart.js via `static/js/chart_loader.js` (`GranaGoChartLoader`)
- Masonry dashboard (`#dashboard-masonry`)
- Mockup HTML de dashboard na landing
- Mini chart CSS no hero float (`.lp-float-chart`)

### Navegação

- Sidebar (`templates/base/sidebar.html` + `static/css/sidebar.css`)
- Header brand mobile/desktop
- Navegação de mês/período (`navegacao_mes_periodo.html`)
- Relatórios: `navegacao_relatorios.html`

### Alertas / toasts

- `.app-toast-root`, `.app-toast` (opacity transition)
- Messages Django nos formulários
- Cookie consent partials

### Avatars

- Landing founder: foto circular + foto lateral
- Header usuário (iniciais / foto perfil) — templates header

### Sheets / listas contextuais

- `lista_contextual_sheet.html`, `static/js/lista_contextual.js`
- Sheets de ações cartão/conta

---

## 5. Landing Page

### Estrutura atual (`templates/landing/landing.html`)

1. Header  
2. Hero (copy + Hero Visual)  
3. Linha de dor  
4. Prova social (fundador + prints placeholder + depoimento)  
5. Programa Primeiros Donos  
6. CTA final (fundo escuro)  
7. Footer  
8. Modal de captura  

Página adicional: `templates/landing/obrigado.html`.

### Screenshots de marketing

**Não encontrado** (nenhum PNG/WebP de tela real em `static/img/landing/` além de `founder.png`).

### Mockups

- `templates/landing/partials/mockup_dashboard.html` — mockup HTML/CSS do app (sidebar, chrome, URL `app.granago.com.br`, painel). Variantes: `hero`, `featured`. **Atualmente não incluso no hero** (substituído por `hero_visual.html`); o partial continua no repo; uso em `product_preview.html` (partial legado, não incluído na `landing.html` atual).

### Imagens

- `static/img/landing/founder.png` — 768×1024 (JPEG apesar da extensão .png), foto do fundador.
- `static/img/landing/hero-person.webp` — **referenciado no HTML, arquivo Não encontrado** no disco.

### Ilustrações

**Não encontrado** (além do logo SVG e mockup HTML).

### CTAs (textos existentes)

- “Quero meu acesso gratuito ao GranaGo →”
- Header: “Quero acesso” / “Entrar”
- Obrigado: “Configurar minha conta →”

### Seções legacy (existem como partials, não montadas na landing atual)

`benefits.html`, `how_it_works.html`, `offer.html`, `audience.html`, `faq.html`, `problem.html`, `product_preview.html`, `trust_bar.html` — presentes em `templates/landing/partials/`.

---

## 6. Prints do aplicativo

**Não encontrado:** prints/screenshots estáticos de telas do app em assets de marketing.

### Telas existentes como templates (código UI, não imagens)

| Área | Templates / localização |
|------|-------------------------|
| Dashboard / Relatórios (home) | `relatorios/templates/relatorios/` + home via URL `relatorios:home` |
| Despesas por categoria | `despesas_categoria.html` |
| Fluxo de caixa | `fluxo_caixa.html` |
| Por conta | `por_conta.html` |
| Orçamentos | `orcamentos.html` + `modal_orcamento.html` |
| Export hub | `relatorios/templates/relatorios/export/` |
| Transações / histórico | `transacoes/templates/transacoes/partials/historico*.html` |
| Importação OFX / planilha | `importar_ofx.html`, `importar_planilha.html` |
| Categorias | `categorias/templates/categorias/home.html` |
| Contas | `contas/templates/contas/home.html` |
| Cartões / faturas | `cartoes/templates/cartoes/` |
| Categorização / regras | `categorizacao/templates/categorizacao/` |
| Configurações / perfil | `usuarios/templates/usuarios/configuracoes/` |
| Primeiros passos (onboarding) | `usuarios/templates/usuarios/primeiros_passos/` |
| Login | `usuarios/templates/usuarios/partials/login.html` |
| Legal | privacidade, termos, password reset |

### Metas (produto)

- Mencionado em `docs/ui/MODAIS.md` como módulo futuro (“metas, planejamentos”).
- **Não encontrado:** templates/telas de “Metas” como feature implementada.

### Preferências

- Em `configuracoes.html` (preferências financeiras, avatar, etc.).

### Investimentos

- Domínio de export existe (`relatorios/export/domains/investimentos.py`); templates dedicados de UI de investimentos: **parcial / Não encontrado** como área de navegação principal na sidebar (sidebar lista Relatórios, Transações, Categorias, Contas, Cartões).

---

## 7. Mockups

| Item | Tipo | Local | Descrição |
|------|------|-------|-----------|
| `mockup_dashboard.html` | HTML/CSS | `templates/landing/partials/` | Janela de app com sidebar GranaGo, nav, painel “Visão Geral”, chrome semântico |
| PSD | — | — | **Não encontrado** |
| Figma/Sketch | — | — | **Não encontrado** |
| Mockup PNG/WebP de device | — | — | **Não encontrado** |
| `hero-person.webp` | previsto | `static/img/landing/` | Slot no Hero; **arquivo Não encontrado** |

---

## 8. Design System

### Existe?

Há **sistema parcial**: tokens Tailwind + componentes utilitários em `input.css` + design tokens da landing em `landing.css` + docs de UI pontuais. **Não encontrado** um Design System documentado unificado (Storybook, página de tokens, etc.).

### Espaçamentos (landing)

- `--lp-space-section`: `clamp(5rem, 11vw, 8rem)`
- `--lp-space-section-tight`: `clamp(3.5rem, 8vw, 5.5rem)`
- Container padding: 1.25rem / 2rem (sm+)
- Hero container ampliado: max-width 92rem, padding lateral reduzido

### Radius

Landing: `--lp-radius-sm` 0.75rem → `--lp-radius-2xl` 1.75rem.  
App: tipicamente `rounded-lg` / `rounded-2xl`.

### Sombras

`--lp-shadow-xs` … `--lp-shadow-lg`, `--lp-shadow-mockup`, `--lp-shadow-cta`; botões app com sombras brand.

### Grid / containers

- `--lp-max`: 76rem (geral)
- Hero: até 92rem
- Grid hero desktop: 1fr / 1fr
- App: `.page-shell`, sidebar collapse 72px

### Breakpoints

Tailwind padrão (sm 640, md 768, lg 1024, etc.). Landing usa 640 / 1023 / 1024 com frequência.

### Animações (tokens)

- `--lp-ease`: `cubic-bezier(0.22, 1, 0.36, 1)`
- `--lp-duration`: 0.55s
- `--lp-hero-crossfade`: 400ms

### Z-index (`input.css`)

`--z-header` 30, `--z-modal` 50, `--z-modal-dropdown` 60, `--z-combobox-floating` 70, `--z-sidebar-overlay` 190, `--z-sidebar` 200, `--z-modal-import` 230, `--z-toast` 260.

---

## 9. Ícones

### Biblioteca principal (app)

- **Font Awesome Free 6.5.2** (subset): `static/vendor/fontawesome/`
- Estilo: **solid** (`fa-solid` / `fas`), weight 900
- Uso: ações (editar, lixeira, import, invoice), categorias (`fa-tag` default), onboarding, etc.

### Chevron padrão

- Heroicons mini chevron-down (SVG data-URI em `--icon-chevron-down`).

### Ícones de contas

- Instituições: PNGs em `contas/static/contas/icons/instituicoes/` (Nubank, Itaú, BB, Bradesco, Caixa, Santander, Inter, PicPay, Mercado Pago, Sicoob, Sicredi).
- Genéricos SVG: `bank`, `briefcase`, `building`, `cash`, `piggy`, `wallet` em `contas/static/contas/icons/genericos/`.

### Mockup landing

- Ícones SVG inline stroke (~2–2.25) no mockup HTML (não Font Awesome).

### Tamanho padrão

- Frequente: `text-sm`, `text-xs`, `text-[15px]`, widths 14–22px em SVGs de UI.

---

## 10. Animações

| Nome / local | Tipo | Notas |
|--------------|------|-------|
| `.lp-reveal` / `.is-visible` | fade + translateY | IntersectionObserver em `landing.js` |
| `lp-float-enter` | opacity | cards do Hero |
| `lp-float-drift` | transform translate + scale | float lento independente |
| Crossfade person / silhouette | opacity 400ms | `is-ready` |
| `.lp-btn-premium` hover | translateY + shadow + seta | — |
| Modal overlay | opacity 300ms + panel scale | `modal.js` |
| Toast | opacity | — |
| Sidebar collapse | width/opacity | `sidebar.css` |
| Combobox / sheets | vários | JS de domínio |
| `prefers-reduced-motion` | desliga reveals/floats | landing |

---

## 11. Assets (inventário)

### Marca

- `static/img/icons/logo.svg`
- `static/img/icons/logo.png`
- `static/img/icons/logo.ico`

### Landing / institucional

- `static/img/landing/founder.png` (768×1024)
- `static/img/landing/hero-person.webp` — **Não encontrado** (só referência)

### Outros

- `static/img/wallpaper.jpg` — JPEG 5000×2435; EXIF description: *“The challenger stands in front of the spooky castle, digital painting.”* (aparenta asset genérico; **não** documentado como marca GranaGo)

### Contas / bancos

- PNGs instituições + SVGs genéricos (lista na seção 9)

### Admin Django

- `static/admin/img/*` (ícones Django padrão; não são marca)

### Vendor

- Font Awesome webfonts/CSS

---

## 12. Branding

Fonte principal: **`docs/marca/brand-context.md`**.

| Tema | Conteúdo encontrado |
|------|---------------------|
| Nome | GranaGo |
| Categoria | Controle Financeiro Essencial |
| Grande ideia | “Você não gasta demais. Você não enxerga o suficiente.” |
| Missão (DMEV) | Clareza e controle real via plataforma simples, acessível e fácil de manter |
| Posicionamento | Blue ocean vs apps complexos / Open Finance; simplicidade |
| Tom de voz | Próximo, direto, sem jargão; humano e sério; sem pompa de banco, sem leveza de game |
| Persona | 25–40 anos, classe média, R$3–8k, Solution Aware; dor do extrato |
| Tribo futura | “Donos do Próprio Dinheiro” |
| Slogan-like | Variações: “Saiba para onde vai cada real”; landing atual: “Veja 3 meses de gastos em 2 minutos.” |
| Precificação documentada | R$97/ano; Primeiros Donos: R$48/ano após programa (landing-copy) |

Copy operacional da captura: **`docs/marca/landing-copy.md`**.

---

## 13. Produto (resumo só com fatos do repo)

**Proposta de valor:** plataforma SaaS de controle financeiro pessoal simples — registrar/organizar receitas e despesas por categorias, ver para onde vai o dinheiro; categorização automática que aprende com o uso (“a IA trabalha por baixo dos panos para que o usuário só precise olhar” — brand-context).

**Funcionalidades evidenciadas no código:**

- Transações (CRUD, histórico)
- Importação OFX e planilha
- Categorias personalizáveis + regras de categorização
- Contas e ícones de instituições
- Cartões e faturas
- Relatórios: visão geral, despesas por categoria, fluxo de caixa, por conta
- Orçamentos por categoria
- Exportações
- Onboarding “primeiros passos”
- Configurações / privacidade / termos
- Programa de captura “Primeiros Donos” (landing)

**Diferenciais documentados:** simplicidade e facilidade de manutenção; categorização inteligente sem automação forçada; sem posicionar Open Finance como limitação (feature futura premium).

**Promessa principal (landing atual):** ver 3 meses de gastos em 2 minutos; importar extrato; IA organiza por categoria; acesso por e-mail.

---

## 14. Hero (estado atual)

### Composição

- Grid 50/50 (desktop): `.lp-hero-copy` | `.lp-hero-visual`
- Alinhamento topo; copy com `padding-top` extra
- Fundo hero: gradientes mint/verdes suaves

### Hierarquia de copy

1. H1: “Veja 3 meses de gastos em **2 minutos.**” (mark verde no “2 minutos”)
2. Três linhas de apoio (mesmo estilo; negrito em “você só olha”; negrito+itálico em “toma susto no extrato”)
3. CTA: “Quero meu acesso gratuito ao GranaGo →”

### Hero Visual — estrutura HTML

```
.lp-hero-visual[data-hero-visual]
  .lp-hero-visual__stage
    .lp-hero-spotlight
    .lp-hero-person-slot
      .lp-hero-person-slot__glow
      .lp-hero-person-slot__silhouette
      img.lp-hero-person[data-hero-person] → hero-person.webp
    .lp-floating-ui
      float items (category, insight, ai, badge, chart, indicator)
```

Arquivo: `templates/landing/partials/hero_visual.html`.

### Elementos flutuantes (textos)

| Tipo | Conteúdo |
|------|----------|
| Categoria | iFood → Alimentação |
| Categoria | Uber → Transporte |
| Insight | R$493 / esquecidos |
| AI chip | IA classificou esta compra |
| Badge | Organizado automaticamente |
| Mini chart | “Categorias” + barras CSS |
| Indicator | Mercado |

Estilo: glassmorphism leve, blur, sombra, órbita assimétrica; insight com `--focus`.

### Imagens do Hero

- Pessoa: **prevista** em `static/img/landing/hero-person.webp` — **arquivo Não encontrado**; silhueta CSS + spotlight enquanto `is-missing`.
- Mockup dashboard: **não** renderizado no Hero atual.

---

## 15. Briefing para IA Geradora de Imagem

Consolidado **somente** a partir do que existe no projeto:

### Identidade a respeitar

- Marca **GranaGo**; símbolo **carteira verde** (SVG em verdes ~`#1AB243`–`#03A11A`).
- Cor dominante de produto: verde Tailwind brand **`#22c55e` → `#16a34a` → `#15803d`**.
- Superfícies claras, levemente esverdeadas (`#fbfefc`, `#f4faf6`, `#ecfdf5`), texto slate (`#0b1220` / `#334155` / `#64748b`).

### Sensação / linguagem (brand-context + landing)

- Simplicidade, clareza, confiança, leveza tecnológica — **sem** estética de banco pomposo ou de game.
- Promessa: visibilidade de gastos; “você só olha”; dor do extrato / salário que “some”.
- Persona 25–40, classe média BR; cena com extrato/banco/celular.

### Composição exigida pelo Hero atual (código)

- Pessoa olhando/usando **celular** (alt text: “Pessoa usando o GranaGo no celular”).
- Imagem com **fundo transparente** (PNG/WebP), ~80–90% do stage, levemente deslocada à esquerda.
- Espaço negativo reservado para **rosto, mãos e smartphone** (cards HTML orbitam fora dessa zona).
- Aspecto do slot: retrato ~3:4; stage ~4:5.
- Destino do arquivo: `static/img/landing/hero-person.webp` (ou ajuste só do `src`).

### UI do produto (referência visual, se aparecer tela no celular)

- App web com sidebar, logo carteira + “GranaGo”, verde brand, URL mock `app.granago.com.br`.
- Mockup HTML disponível em `mockup_dashboard.html` como referência de UI (não é foto).
- Glass cards flutuantes (já em HTML) mostram: categorias de gasto, insight **R$493 esquecidos**, chips de IA — a imagem da pessoa **não** deve incorporar esses cards.

### Tipografia do entorno (página, não da imagem)

- Landing: Plus Jakarta Sans.
- App config: Inter (sem load explícito no HTML encontrado).

### Referências fotográficas existentes

- `founder.png` (768×1024): foto do fundador Gustavo — uso na prova social; **não** é o asset do Hero Visual.

### Ausências explícitas (não inventar)

- Screenshots reais de marketing: **Não encontrado**
- PSD / Figma do Hero: **Não encontrado**
- `hero-person.webp`: **Não encontrado**
- Design System visual completo com guidelines de fotografia: **Não encontrado**
- Wordmark tipográfico oficial além do texto HTML “GranaGo”: **Não encontrado**

### Resumo operacional para o gerador

Gerar **uma única pessoa realista** (PNG/WebP transparente), olhando para um smartphone, composição vertical, luz suave, tons compatíveis com verde/menta e neutros claros do GranaGo, espaço livre no centro do frame para rosto/mãos/aparelho, **sem** UI flutuante, **sem** texto, **sem** logo grande na imagem (o logo e os cards já existem em HTML ao redor).

---

*Fim do relatório. Gerado por pesquisa no repositório em 2026-07-30; sem alterações de código.*
