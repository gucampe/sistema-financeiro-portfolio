<!-- Data de criação: 14 de agosto de 2026 -->

# Contexto do site público — GranaGo

Documento de estado atual (não de intenção). Copy de marketing transcrita **integralmente**. Briefing de front, design e UX por página, a partir do código em produção local neste repositório.

Escopo: o site público (institucional + captura + legais). O SaaS autenticado (`APP_HOST`, login, relatórios, transações) não entra aqui, exceto quando aparece como destino ou mockup.

---

## 1. Arquitetura da superfície pública

O visitante encontra **duas experiências** no mesmo host de marketing, com o mesmo design system e vozes diferentes.

| Superfície | URLs | Job | Tom |
|---|---|---|---|
| Institucional | `/`, `/nossa-historia/`, `/como-funciona/`, `/faq/` | Explicar o produto, construir confiança, levar à captura | Calmo, direto, “você”. Sem escassez, sem preço, sem “IA” no copy principal |
| Captura | `/comece/` (legado `/primeiros-donos/` → 301) | Converter lead do programa Primeiros Donos | Oferta, prova, urgência. IA + importação de extrato em 2 minutos |
| Obrigado | `/obrigado/` | Confirmar vaga e empurrar para o app | Operacional, primeira pessoa do fundador |
| Legais | `/politica-de-privacidade/`, `/termos-de-uso/` | Compliance LGPD / contrato | Formal, índice lateral, breadcrumb |

Funil:

```
Google / direto
    → /  (home institucional)
        → Nossa História | Como Funciona | FAQ
            → CTA “Garantir minha vaga no GranaGo”
                → /comece/
                    → modal Nome / E-mail / WhatsApp
                        → POST /captura/
                            → /obrigado/
                                → app.granago.com.br/login/
```

Anúncios e CTAs do header podem pular direto para `/comece/`. Usuário já autenticado que abre `/comece/` é redirecionado para o home do SaaS.

Hosts: site institucional + landing no host de marketing (`LANDING_HOSTS`); produto em `APP_HOST`. Login no header aponta para `APP_LOGIN_URL` (ex.: `https://app.granago.com.br/login/`).

Sitemap: `/`, `/nossa-historia/`, `/como-funciona/`, `/faq/`, `/politica-de-privacidade/`, `/termos-de-uso/`, `/comece/`.  
`robots.txt` bloqueia `/obrigado/`, `/captura/` e `/admin/`. A página de obrigado também tem `noindex`.

---

## 2. Sistema visual (front / design)

### Stack

- Tipografia: **Plus Jakarta Sans** 400–800 (Google Fonts), `system-ui` de fallback.
- CSS: Tailwind (`static/css/output.css`) + tokens da landing (`static/landing/css/landing.css`, variáveis `--lp-*`) + extensão institucional (`static/institucional/css/institucional.css`).
- JS compartilhado: `landing.js` (reveal, header scrolled, FAQ accordion, modal, máscara de WhatsApp). Institucional adiciona `institucional.js` (menu mobile).
- Fonte da identidade: carteira verde + verde brand. Paleta light-first, ritmada em faixas mint → branco → mint.

### Tokens principais (`--lp-*`)

| Papel | Valor |
|---|---|
| Verde brand | `#22c55e` / dark `#16a34a` / deep `#15803d` |
| Mint / superfícies | `#ecfdf5`, `#f8fcf9`, `#eef8f1` |
| Hero | `#f3faf5` → `#fbfefc` → branco |
| Dor / programa | `#eaf7ef` → `#eff9f2` / `#e8f6ec` → `#f3faf5` |
| Ink | `#0b1220` (títulos), `#1e293b`, body `#475569`, muted `#64748b` |
| Linhas | `#e3efe8` / `#cfe6d7` |
| Radius | 0.75rem → 1.75rem |
| Sombra CTA | verde, `0 14px 36px rgba(22, 163, 74, 0.28)` |
| Container | max 76rem; hero chega a 92rem |
| Seção | `clamp(3.75rem, 11vw, 8rem)` |

### Tipografia de página

| Classe | Uso |
|---|---|
| `.inst-eyebrow` | Label uppercase 13px, tracking 0.08em, verde deep |
| `.inst-display` / `.lp-display` | H1. Institucional ~2–3.35rem; landing ~2.6–4rem |
| `.lp-headline` | H2 de dobra, ~1.85–2.75rem |
| `.lp-title` | H3 de card |
| `.lp-body` / `.inst-lead` | 18px / 1.75–1.8, max ~38rem |

### Componentes recorrentes

- **Botão premium** (`.lp-btn-premium`): verde sólido, sombra brand, hover um pouco mais escuro. CTA primário único por dobra.
- **Faixas** (`.lp-band--*`): cada seção troca de superfície; o ritmo visual substitui divisores pesados.
- **Prints** (`.lp-print-placeholder`): screenshot com chrome de 3 bolinhas (vermelho / âmbar / verde), borda, sombra, hover sutil. Usado na home (visão geral), como funciona (3 prints) e na prova da captura.
- **Mockup HTML** (`.lp-mockup`): UI falsa do app (sidebar + Visão Geral) no hero institucional. Não é screenshot; é markup que espelha o produto.
- **FAQ** (`<details class="lp-faq">`): um aberto por vez (JS fecha os outros). Ícone “+”.
- **Reveal** (`.lp-reveal`): fade/slide no scroll via IntersectionObserver; respeita `prefers-reduced-motion`.
- **Header sticky**: transparente + blur; ganha borda ao scroll (`.is-scrolled`).
- **Cookie banner**: só no aplicativo autenticado. Copy: “Usamos cookies essenciais para sessão e segurança.” CTA “Entendi”. Landing `/comece/`, `/obrigado/` e o site institucional **não** incluem o banner; o cadastro informa cookies (incluindo os da Meta) no formulário.

### Princípios de UX visíveis no código

1. **Uma ação primária.** Header: “Quero minha vaga”. Heros e bandas finais: “Garantir minha vaga no GranaGo”. Secundário: “Entrar” (ghost, some no mobile do header institucional e vai para o drawer).
2. **Pouco atrito cognitivo.** Frases curtas. Sem jargão de banco. Sem Open Finance no posicionamento.
3. **Prova visual cedo.** Home mostra o painel no hero; Como funciona mostra print real a cada passo; Captura mostra print do fundador.
4. **Acessibilidade básica.** Skip link “Pular para o conteúdo” (só institucional), `aria-labelledby` nas seções, FAQ nativo `<details>`, menu mobile com `aria-expanded` / Escape / clique fora.
5. **Mobile-first do chrome.** Nav desktop a partir de 1024px. Abaixo disso: hamburger. Wordmark some abaixo de 360px (só logo).

---

## 3. Chrome compartilhado (institucional)

Presente em `/`, `/nossa-historia/`, `/como-funciona/`, `/faq/` e nas páginas legais (que estendem o mesmo base).

### Header — copy

- Marca: GranaGo (logo + wordmark; aria-label “GranaGo, página inicial”)
- Nav: O GranaGo · Nossa História · Como Funciona · FAQ
- Ações: Entrar · **Quero minha vaga**
- Menu mobile: mesmos links + Entrar + CTA “Quero minha vaga”

### Header — UX / front

- Sticky, 64px (72px no `sm`).
- Item ativo via `nav_current` (`is-active`, verde deep, sem underline).
- CTA primário compacto (`btn-sm`) para não competir com o H1.
- “Entrar” some no mobile do header e reaparece no drawer (`sm:hidden`).
- Drawer: painel abaixo do header, fundo quase branco, links em lista com divisores, CTA full-width no fim.

### Footer — copy

- Marca + “Controle financeiro pessoal simples de manter.”
- Navegação: Nossa História · Como Funciona · FAQ
- Produto: Entrar · Quero minha vaga
- Institucional: Política de Privacidade · Termos de Uso · WhatsApp (se `whatsapp_suporte_url`)
- © {ano} GranaGo

### Footer — UX / front

- 4 colunas a partir de 640px; empilhado no mobile.
- Fundo `#f7fbf8`, borda mint. Títulos de coluna uppercase muted. Links verde deep, underline no hover.
- WhatsApp abre em nova aba (`rel="noopener"`). Número de suporte no código: (11) 93149-6081.

### Banda de CTA final (partial `cta_band.html`)

Padrão (home e FAQ):

- H2: **Pronto para enxergar para onde vai cada real?**
- Lead: O acesso à versão beta é gratuito. Você entra pelo programa de primeiros usuários.
- Botão: **Garantir minha vaga no GranaGo** → `/comece/`

Variantes injetadas por página (ver abaixo). Sempre centralizada, fundo em degradê mint, padding de seção mais curto.

---

## 4. Home — `/`

**Arquivo:** `templates/institucional/home.html`  
**Papel:** primeira dobra do site. Não é página de captura. Deve responder “o que é”, “para quem”, “por que é diferente” e mandar o visitante para `/comece/`.

### Briefing front / design / UX

**Job da página.** Converter curiosidade em entendimento, não em formulário. O formulário mora em `/comece/`. Por isso há **um** CTA no hero e **um** CTA no rodapé da página — nenhum modal.

**Arquitetura de dobras (5):**

1. **Hero split.** Esquerda: eyebrow + H1 de pergunta + lead + CTA. Direita: mockup HTML do painel (variante `hero`). Grid do mesmo sistema da landing (`.lp-hero-grid`). O mockup prova o produto sem screenshot; carrega no first paint. `role="img"` + aria-label “Prévia do painel do GranaGo”.
2. **Problema (centro).** Faixa `.lp-band--pain` (mint). Eyebrow “O problema”, H2 curto, parágrafo de cena, quote grande. Sem print, sem CTA. É a dobra emocional.
3. **Solução + screenshot.** Faixa `.lp-band--muted-light`. Copy centralizado max-w-3xl, depois print `visao-geral.webp` em max-w-4xl com chrome de janela. A screenshot é a evidência da promessa do H2.
4. **Três diferenciais.** Fundo branco. Grid 1 col → 3 cols no `md`. Cards brancos, borda mint, sombra leve. Sem ícones — o título carrega o benefício.
5. **CTA de fechamento.** Mesmo partial padrão.

**SEO.** Title “GranaGo — Controle financeiro pessoal simples”. Canonical `/`. JSON-LD `SoftwareApplication`. H1 é a pergunta da persona, não o nome do produto — o nome entra no lead e no CTA.

**O que esta página deliberadamente não faz.** Não fala de preço, vagas, IA, importação de extrato, WhatsApp de captura. Isso é da `/comece/`. Aqui o produto é “registrar o que entra e o que sai” e “sem conectar o banco”.

### Copy integral

**SEO / social**

- Title: GranaGo — Controle financeiro pessoal simples
- Description: O GranaGo é um app de controle financeiro pessoal. Você registra o que entra e o que sai e passa a ver para onde vai cada real — sem conectar o banco.
- OG description: Você sabe quanto ganhou. Mas sabe pra onde foi cada real? O GranaGo torna isso visível, de um jeito simples de manter.
- Twitter description: App de controle financeiro pessoal simples: veja para onde vai cada real, sem conectar sua conta bancária.

**Hero**

- Eyebrow: Controle financeiro pessoal
- H1: Você sabe quanto ganhou. Mas sabe pra onde foi cada real?
- Lead: O GranaGo é o app para organizar o que entra e o que sai — e mostrar, com clareza, para onde o dinheiro está indo.
- CTA: Garantir minha vaga no GranaGo

**O problema**

- Eyebrow: O problema
- H2: O salário cai. No fim do mês, some.
- Corpo: Você recebe. Paga algumas coisas. Usa o cartão. Faz PIX. Quita as contas. No fim do mês abre o extrato e pensa:
- Quote: “Para onde foi meu dinheiro?”

**A solução**

- Eyebrow: A solução
- H2: O GranaGo transforma seus gastos espalhados em uma visão simples de entender.
- Lead: Nada de planilha infinita nem app que pede o banco inteiro. Você registra o que quer acompanhar e o painel mostra o retrato.
- Screenshot alt: Painel do GranaGo com receitas, despesas, patrimônio e para onde o dinheiro está indo

**Por que continua no dia a dia**

- Eyebrow: Por que continua no dia a dia
- H2: Feito para caber na rotina de verdade
- Card 1 — Simples de manter: Não precisa virar um ritual. O GranaGo nasceu para funcionar mesmo nos períodos em que o trabalho ocupa tudo — quando o controle financeiro costuma ser o primeiro a cair.
- Card 2 — Categorização inteligente: Você descreve a transação. O GranaGo sugere a categoria. Você confirma ou ajusta. Com o uso, a sugestão fica mais precisa — e o trabalho manual diminui.
- Card 3 — Sem burocracia: Não é preciso conectar sua conta bancária. Você escolhe o que entra: um lançamento manual ou, se quiser, a importação de um extrato. O controle dos dados continua com você.

**CTA**

- H2: Pronto para enxergar para onde vai cada real?
- Lead: O acesso à versão beta é gratuito. Você entra pelo programa de primeiros usuários.
- Botão: Garantir minha vaga no GranaGo

---

## 5. Nossa História — `/nossa-historia/`

**Arquivo:** `templates/institucional/nossa_historia.html`  
**Papel:** prova de origem. Transforma o fundador em evidência de que o produto nasceu de quem viveu a mesma dor.

### Briefing front / design / UX

**Job da página.** Empatia e credibilidade. Não ensina o produto (isso é Como funciona) e não converte no meio do texto. A conversão fica só no CTA final, com copy específica desta página.

**Duas dobras + CTA.**

1. **Page hero** (`.inst-page-hero`): mais baixo que o hero da home. Sem visual à direita. Eyebrow + H1 + lead. A marca fala em terceira pessoa (“Quem criou…”), enquadrando a história como institucional.
2. **Carta do fundador.** Grid foto | prosa a partir de 900px. Foto `founder.png` com recorte arredondado, borda, sombra, fundo mint. Figcaption Tailwind: “Gustavo, fundador do GranaGo”. Corpo em 18px / 1.8, parágrafos curtos. O último parágrafo fecha em negrito no produto.
3. **CTA.** Heading e lead próprios, porque o leitor acabou de se identificar com a história.

**Voz.** Hero = marca (“nós”). Bloco da foto = **primeira pessoa**. A figcaption ancora o “eu”, para o texto não parecer anônimo.

**UX de leitura.** Prosa longa de propósito — é a única página “editorial”. Sem cards, sem números, sem prints do app. A foto humana substitui o mockup. Mobile: foto acima do texto (ordem do DOM).

**O que não está nesta página.** Preço, vagas, IA, depoimento em aspas de produto (isso está em `/comece/`). Aqui a prova é narrativa, não print de painel.

### Copy integral

**SEO / social**

- Title: Nossa História — GranaGo
- Description: O GranaGo nasceu da experiência de um desenvolvedor que tentou vários apps de finanças, viu o controle escapar na correria do trabalho e construiu uma solução simples o bastante para durar.
- OG description: Quem está por trás do GranaGo passou pelo mesmo problema: saber quanto ganhava, sem saber para onde ia o dinheiro.
- Twitter description: O GranaGo nasceu de quem também tentou outros apps e precisava de algo simples o bastante para manter.

**Hero**

- Eyebrow: Nossa história
- H1: Quem criou o GranaGo passou pelo mesmo problema.
- Lead: Não começou como um projeto para “revolucionar finanças”. Começou como uma tentativa de entender para onde o próprio dinheiro estava indo.

**Foto**

- Alt: Gustavo, fundador do GranaGo
- Legenda: Gustavo, fundador do GranaGo

**Carta**

Eu sou desenvolvedor. Quando comecei a trabalhar e ganhar o próprio dinheiro, fiz o que muita gente faz: tentei diferentes aplicativos e ferramentas para controlar as finanças.

Nenhum durou. Pediam demais. Eram complexos demais. Não encaixavam numa rotina que já era cheia.

Numa fase de alta demanda no trabalho, o controle financeiro ficou em segundo plano. Não foi uma decisão dramática. Foi o tipo de coisa que se adia um dia, depois uma semana, depois some da lista.

Quando voltei a olhar, o problema já tinha se acumulado em silêncio. Não por um gasto absurdo e óbvio — mas porque, sem visibilidade, o dinheiro escapa sem anúncio.

Foi aí que construí uma solução para mim mesmo. A regra era simples: precisava funcionar mesmo nos períodos caóticos. Se a ferramenta exigisse energia que eu não tinha, ela seria abandonada — como as outras.

Com o tempo, ficou claro que o problema não era só meu. Outras pessoas também sabiam quanto ganhavam, mas não conseguiam explicar para onde tinha ido cada real. Também já tinham tentado um app ou uma planilha. Também tinham desistido.

**O GranaGo nasceu dessa experiência.** Não de uma tese de mercado. Nasceu da necessidade de clareza — e de uma ferramenta simples o bastante para continuar usando quando a vida aperta.

**CTA**

- H2: Se isso parece familiar, o GranaGo foi feito para você
- Lead: A versão beta é gratuita. O próximo passo é o programa de primeiros usuários.
- Botão: Garantir minha vaga no GranaGo

---

## 6. Como Funciona — `/como-funciona/`

**Arquivo:** `templates/institucional/como_funciona.html`  
**Papel:** reduzir o medo de “esses apps são complicados”. Mostrar o caminho mínimo até o valor.

### Briefing front / design / UX

**Job da página.** Tutorial emocional de 3 passos, não um manual. Cada passo = número + H2 + um parágrafo + screenshot real do produto.

**Layout.** `<ol class="inst-steps">`. No desktop (≥1024px), grid texto | print; o passo 2 inverte (`.inst-step--reverse`) para o olhar ziguezaguear. No mobile, sempre texto acima do print.

**Número.** Pílula mint circular (`.inst-step__num`), verde deep, sem “Passo”. O H2 já é a ação.

**Prints.** `dashboard.webp`, `transacoes.webp`, `relatorios.webp` — chrome de janela, lazy-load. Alts descritivos. São a prova de que o passo existe de verdade no produto.

**Hero.** Mesmo padrão page-hero: sem visual, promessa de “três passos / sem configuração longa”, lead que fala com quem já desistiu no cadastro de outro app.

**CTA.** Copy específica: “Se cabe na sua rotina…” — fecha o arco “simples de começar”.

**O que esta página não faz.** Não explica categorias custom, cartões, contas, LLM. Só o caminho feliz: conta → primeira transação → painel.

### Copy integral

**SEO / social**

- Title: Como funciona — GranaGo
- Description: Como usar o GranaGo em três passos: crie sua conta, registre a primeira transação e veja para onde vai cada real. Sem conexão bancária obrigatória.
- OG description: Três passos: conta, primeira transação e o painel. Feito para quem acha que esses apps são complicados demais.
- Twitter description: Crie a conta, registre uma transação e veja o panorama. Sem burocracia.

**Hero**

- Eyebrow: Como funciona
- H1: Três passos. Sem configuração longa.
- Lead: Se você já desistiu de um app de finanças no meio do cadastro, o GranaGo foi pensado para o contrário: começar pequeno e enxergar rápido.

**Passo 1**

- H2: Crie sua conta
- Corpo: Com e-mail e senha. Sem pedir dados bancários, token do banco ou uma lista infinita de permissões. Você entra e já está no seu espaço.
- Alt do print: Painel inicial do GranaGo após o acesso à conta

**Passo 2**

- H2: Registre sua primeira transação
- Corpo: Uma entrada ou uma saída: valor, uma descrição rápida e a categoria. O GranaGo sugere a categoria a partir do que você escreveu — você confirma ou ajusta.
- Alt do print: Tela de transações do GranaGo com lançamentos e categorias

**Passo 3**

- H2: Veja para onde vai cada real
- Corpo: O painel junta o que entrou, o que saiu e as categorias. A pergunta do extrato — “para onde foi meu dinheiro?” — passa a ter uma resposta visível.
- Alt do print: Relatórios do GranaGo mostrando para onde foi o dinheiro

**CTA**

- H2: Se cabe na sua rotina, o próximo passo é experimentar
- Lead: A versão beta é gratuita. Você se inscreve na página do programa de primeiros usuários.
- Botão: Garantir minha vaga no GranaGo

---

## 7. FAQ — `/faq/`

**Arquivo:** `templates/institucional/faq.html`  
**Papel:** desarmar objeções depois do primeiro contato. Página de suporte leve, não de conversão agressiva.

### Briefing front / design / UX

**Job da página.** Responder as 6 perguntas que bloqueiam o “sim”. Ordem das objeções: banco → segurança → esforço diário → preço futuro → “já desisti de app” → competência financeira.

**Layout.** Page-hero + coluna única `max-w-2xl` (leitura estreita). Accordion `<details>`: um aberto por vez. Respostas em `.lp-faq__answer`, tom direto, começam com “Não” quando a crença é falsa.

**JSON-LD `FAQPage`** nas 5 primeiras perguntas (a sexta, “Preciso entender de finanças…”, está no HTML mas não no schema).

**CTA.** Volta ao default da home — a FAQ já fez o trabalho de objeção; o fechamento é o mesmo convite.

**Lead do hero.** Aponta o WhatsApp do rodapé se a dúvida não estiver na lista. Canal de suporte visível sem poluir o accordion.

### Copy integral

**SEO / social**

- Title: Dúvidas frequentes — GranaGo
- Description: O GranaGo precisa conectar o banco? É seguro? Preciso usar todo dia? Respostas diretas sobre o app de controle financeiro pessoal.
- OG description: Respostas sobre segurança, conexão bancária, rotina de uso e a versão beta do GranaGo.
- Twitter description: O GranaGo não exige conexão com sua conta bancária. Veja as respostas mais comuns.

**Hero**

- Eyebrow: Dúvidas frequentes
- H1: Perguntas que costumam aparecer depois do primeiro contato.
- Lead: Respostas diretas, sem enrolação. Se a sua dúvida não estiver aqui, o WhatsApp de suporte está no rodapé.

**Perguntas**

1. **Precisa conectar minha conta bancária?**  
   Não. O GranaGo não exige conexão com a sua conta bancária. Você registra manualmente o que deseja acompanhar — e, se preferir, pode importar um arquivo de extrato. O que entra no sistema é o que você escolhe colocar.

2. **É seguro?**  
   O GranaGo não acessa as suas contas bancárias: não pedimos senha do banco, token nem integração com Open Finance. Os dados que você registra ficam na sua conta, protegidos por login. Nenhum sistema é seguro de forma absoluta — o ponto honesto é este: sem conexão bancária, o GranaGo não tem acesso ao seu banco.

3. **Vou ter que alimentar isso todo dia?**  
   Não. O objetivo é o acompanhamento caber na rotina, não virar mais uma tarefa pesada. Você lança quando fizer sentido — uma transação agora, um conjunto depois, ou um extrato importado. Não é preciso passar horas no sistema para ele ser útil.

4. **E quando virar pago?**  
   Na beta, o acesso é gratuito. Quando houver plano pago, quem entrou na beta terá condições especiais para continuar.

5. **Já tentei apps e desisti. Por que esse seria diferente?**  
   O GranaGo nasceu exatamente disso: alguém que também tentou outras ferramentas, viu o controle escapar na correria e precisava de algo simples o bastante para não abandonar de novo. A aposta não é ter mais recursos. É ter menos atrito — para continuar usando quando a semana aperta.

6. **Preciso entender de finanças para usar?**  
   Não. Você não precisa ser especialista. O GranaGo organiza o que você registra e mostra o panorama. A leitura é “para onde foi o dinheiro”, não um curso de educação financeira.

**CTA:** mesmo da home (Pronto para enxergar… / beta gratuita / Garantir minha vaga).

---

## 8. Captura — `/comece/`

**Arquivo:** `templates/landing/landing.html` + partials em `templates/landing/partials/`  
**Papel:** única página de conversão do programa Primeiros Donos. Header sem nav institucional. Tudo aponta para o modal de captura.

### Briefing front / design / UX

**Job da página.** Tirar o e-mail (e WhatsApp) de quem já sentiu a dor. Ritmo de landing clássica: promessa → dor → prova → oferta com escassez → CTA.

**Chrome.** Header só com logo (aponta para a própria `/comece/`, não para a home institucional), “Entrar” e “Quero minha vaga” (abre modal). Footer mínimo: tagline “Controle Financeiro Essencial”, Privacidade, Termos, Entrar. Sem menu O GranaGo / História / FAQ.

**Dobras montadas hoje (nesta ordem):**

1. Hero (promessa + visual de pessoa + chips flutuantes)
2. Dor (três frases em stagger)
3. Fundador (quote + print + foto)
4. Programa Primeiros Donos (selo PD + card de benefícios + escassez)
5. CTA “Garanta sua vaga” (abre o mesmo modal)

**Não montado na página atual**, mas ainda existe no repositório: `faq.html`, `offer.html`, `benefits.html`, `how_it_works.html`, `audience.html`, `product_preview.html`, `trust_bar.html`, `problem.html`. O FAQ da captura (com garantia de 7 dias e “o preço vai aumentar?”) **não aparece** para o visitante.

**Hero visual.** Foto `hero-person.webp` + UI chips: KPI “Receitas do mês R$ 5.200,00 ↑ 12%”, chip IA “iFood → Alimentação”, card “Para onde seu dinheiro está indo” (Alimentação R$ 892 / Moradia R$ 1.240 / Transporte R$ 456). Crossfade quando a foto carrega (`data-hero-visual` / `is-ready`). Contrasta com o hero institucional, que usa mockup de dashboard.

**Dor.** Três linhas com delay de reveal. Sem CTA — é pausa dramática.

**Fundador.** Não é a carta longa da institucional. É um **depoimento de produto** (importou o extrato, achou R$ 545,05 em supermercado) + print `print2.png` + foto. Avatar pequeno no header do bloco + foto grande no aside.

**Programa.** Selo circular “PD”. Card único, lista com checks. Escassez “50 vagas. Quando acabar, acabou.” `role="status"`.

**CTA.** Diz “Preencha abaixo” mas o form **não está inline** — o botão abre o modal. Fallback se o JS do modal falhar: `#garantir-vaga` (âncora da própria seção) ou `/comece/#garantir-vaga`.

**Modal.** Overlay `max-w-md`. Campos: Nome, E-mail, WhatsApp (máscara `(11) 93149-6081`). Hint do WhatsApp: “Para acompanharmos sua experiência com o GranaGo.” Submit: “Garantir minha vaga no GranaGo” → “Enviando…” (disable + aria-busy). Privacidade: “🔒 Seus dados são protegidos. Não enviamos spam.” Focus no nome ao abrir. Pode abrir on-load se `abrir_modal_captura`.

**Usuário logado:** redirect para relatórios. `never_cache`.

### Copy integral

**SEO / social**

- Title: GranaGo — Veja 3 meses de gastos em 2 minutos
- Description: Para quem toma susto no extrato todo mês e não consegue explicar por quê. Importe os últimos 3 meses e veja tudo por categoria — a IA organiza sozinha. Programa Primeiros Donos.
- OG description: Importe os últimos 3 meses de extrato e veja tudo por categoria — a IA organiza sozinha. Vagas limitadas no programa Primeiros Donos.
- Twitter description: Para quem toma susto no extrato todo mês. Acesso gratuito no programa Primeiros Donos.

**Header**

- Quero minha vaga · Entrar

**Hero**

- H1: Veja 3 meses de gastos em **2 minutos.**
- P1: O GranaGo é a plataforma de controle financeiro que importa seu extrato e usa IA para organizar tudo por categoria — **você só olha**.
- P2: Feito para quem ***toma susto no extrato*** todo mês e não consegue explicar por quê.
- CTA: Garantir minha vaga no GranaGo

**Chips do hero (texto de UI, não copy de venda)**

- Receitas do mês · R$ 5.200,00 · ↑ 12%
- iFood → Alimentação
- Para onde seu dinheiro está indo · Alimentação R$ 892 · Moradia R$ 1.240 · Transporte R$ 456
- Alt da pessoa: Pessoa usando o GranaGo no celular

**Dor**

- Você recebe o salário.
- Algumas semanas depois, ele some.
- Quando olha o extrato, não consegue explicar por quê — e no mês seguinte acontece tudo de novo.

**Fundador**

- Nome: Gustavo — fundador do GranaGo
- Contexto: Minha própria experiência antes de lançar o produto
- Quote: Importei o extrato. Em segundos, o app já tinha organizado tudo por categoria — não precisei fazer nada. Fui direto procurar o que eu achava que estava me pesando: transporte. Era irrelevante. O que pesava eram R$545,05 em supermercado que eu tinha feito e esquecido, mas que iam aparecer na fatura e me pegar de surpresa. Tudo isso em 2 minutos.
- Alt do print: Painel do GranaGo — visão geral com receitas, despesas e categorias
- Alt da foto: Gustavo, fundador do GranaGo

**Programa**

- H2: O Programa **Primeiros Donos**
- P1: O GranaGo está chegando ao mercado. Antes do lançamento oficial, estou reunindo um grupo pequeno de pessoas que vivem o mesmo problema — não sabem para onde vai o dinheiro, já tentaram app ou planilha e desistiram.
- P2: Essas pessoas vão usar o produto antes de todo mundo.
- H3: O que você recebe:
  - Acesso completo ao GranaGo durante o programa
  - 50% de desconto para continuar depois — R$4/mês em vez de R$8
  - Seu feedback define o que melhora primeiro
- Escassez: 50 vagas. Quando acabar, acabou.

**CTA da dobra**

- H2: Garanta sua vaga no GranaGo
- P1: Preencha abaixo. Você recebe o acesso ao GranaGo direto no e-mail — em instantes.
- P2: WhatsApp só para te guiar no primeiro acesso.
- Botão: Garantir minha vaga no GranaGo
- Rodapé: 🔒 Seus dados são protegidos. Não enviamos spam.

**Modal**

- Kicker: GranaGo
- Título: Garanta sua vaga
- Subtitle: Você recebe o acesso no e-mail — em instantes.
- Labels: Nome · E-mail · WhatsApp
- Hint WhatsApp: Para acompanharmos sua experiência com o GranaGo.
- Submit: Garantir minha vaga no GranaGo
- Privacidade: 🔒 Seus dados são protegidos. Não enviamos spam.

**Footer**

- Controle Financeiro Essencial
- Privacidade · Termos · Entrar
- © {ano} GranaGo

---

## 9. Obrigado — `/obrigado/`

**Arquivo:** `templates/landing/obrigado.html`  
**Papel:** confirmação pós-lead e empurrão para configurar a conta. `noindex, nofollow`.

### Briefing front / design / UX

**Job da página.** Reduzir ansiedade (“será que deu certo?”) e dar o próximo passo único: **Configurar minha conta**. O e-mail é plano B; o WhatsApp é plano C.

**Layout.** Header da landing + bloco central `max-w-2xl`. Badge de check, H1, CTA para `app_login_url`, bloco de ajuda (e-mail / spam / WhatsApp), card de dica de onboarding.

**Personalização.** Se `lead_nome` existe, o assunto do e-mail vira “{Nome}, seu acesso ao GranaGo chegou”. Senão, placeholder `[Nome]`.

**UX.** Uma ação primária. Ajuda em parágrafos curtos, primeira pessoa (“Também enviei”, “Me chama”). Card mint com o ritual da primeira sessão (importar 3 meses) — alinha a captura (promessa de 2 minutos) com o onboarding real.

### Copy integral

**SEO**

- Title: Vaga garantida — GranaGo
- Description: Vaga garantida no programa Primeiros Donos. Configure sua conta agora.
- robots: noindex, nofollow

**Página**

- H1: Vaga garantida. Configure sua conta agora.
- CTA: Configurar minha conta →
- Também enviei o link de acesso para o seu e-mail — procura pelo assunto: **{Nome}, seu acesso ao GranaGo chegou**. Útil se precisar entrar mais tarde ou em outro dispositivo.
- Não encontrou? Confere a caixa de spam.
- Ainda assim não achou? Pode ter sido um erro na digitação do e-mail. Me chama no WhatsApp: **(11) 93149-6081**
- H2: Quando entrar no GranaGo:
- Começa pela importação do extrato — importa os últimos 3 meses se conseguir. É o que vai te dar o panorama completo na primeira olhada.

---

## 10. Legais

**Arquivos:** `usuarios/templates/usuarios/legal/privacidade.html`, `termos.html`  
**Base:** `base_legal.html` → institucional (mesmo header/footer).  
**Redirects permanentes:** `/privacidade/` → `/politica-de-privacidade/`; `/termos/` → `/termos-de-uso/`.

### Briefing front / design / UX

**Job.** Legibilidade de contrato, não conversão. Hero legal mais baixo, breadcrumb “Início / Privacidade|Termos”, data de atualização, lead curto. Corpo em layout **índice + artigo**.

**Índice.** `<aside>` com `<details>`. No desktop (≥1024px) o JS abre o índice; no mobile fica colapsado em “Nesta página”. Âncoras por seção.

**Tom visual.** Mesma família tipográfica, mas densidade de prosa jurídica. Notas (`.lp-legal-note`) para esclarecimentos. Controlador descrito como pessoa física, sem nome civil nem CNPJ nas páginas públicas; canais `ola@` e `privacidade@granago.com.br`.

**Copy de chrome (não o corpo jurídico completo)**

**Privacidade**

- Title: Política de Privacidade — GranaGo
- H1: Política de Privacidade
- Meta: Última atualização: 14 de agosto de 2026
- Lead: Esta política explica como o **GranaGo** trata dados pessoais ao oferecer ferramentas de organização financeira pessoal, em conformidade com a Lei Geral de Proteção de Dados (Lei nº 13.709/2018 — LGPD).
- Índice: 1. Controlador · 2. Como o serviço funciona · 3. Dados que tratamos · 4. Bases legais · 5. Parceiros e infraestrutura · [6. Categorização com IA, se LLM ativo] · Segurança · Cookies · Retenção · Seus direitos · Contato

**Termos**

- Title: Termos de Uso — GranaGo
- H1: Termos de Uso
- Meta: Última atualização: 14 de agosto de 2026
- Lead: Estes Termos regulam o uso da plataforma **GranaGo**, um software de organização financeira pessoal. Ao criar uma conta ou utilizar o serviço, você declara ter lido, compreendido e concordado com as condições abaixo.
- Índice: 1. Introdução · 2. Acesso e conta · 3. Funcionalidades · 4. Importação de dados · 5. Suas responsabilidades · 6. Propriedade intelectual · 7. Disponibilidade · 8. Privacidade · 9. Segurança · 10. Limitação de responsabilidade · 11. Alterações · 12. Contato

O corpo integral está nos templates legais. Este briefing não o duplica para não misturar contrato com copy de produto.

---

## 11. Mapa de CTAs e vocabulário

| Onde | Rótulo | Destino | Tipo |
|---|---|---|---|
| Header institucional / mobile | Quero minha vaga | `/comece/` | link |
| Header captura | Quero minha vaga | modal | botão |
| Hero home, CTA bandas, hero captura, modal, CTA captura | Garantir minha vaga no GranaGo | `/comece/` ou modal | link / botão |
| Header / footer | Entrar | `APP_LOGIN_URL` | secundário |
| Obrigado | Configurar minha conta → | login do app | primário |

Vocabulário estável no institucional: “para onde vai cada real”, “simples de manter”, “sem conectar o banco”, “versão beta”, “programa de primeiros usuários”.  
Vocabulário da captura: “2 minutos”, “IA”, “importa seu extrato”, “você só olha”, “Primeiros Donos”, “50 vagas”, “R$4/mês”.

Os dois vocabulários convivem de propósito: institucional vende clareza; captura vende o programa.

---

## 12. Assets visuais em uso no site público

| Asset | Onde |
|---|---|
| `static/img/icons/logo.svg` | headers, footers, favicon, mockup |
| `static/img/icons/logo.png` | og:image |
| `static/img/landing/founder.png` | Nossa História + bloco fundador da captura |
| `static/img/landing/hero-person.webp` | hero da `/comece/` |
| `static/img/landing/print2.png` | prova na `/comece/` |
| `static/img/institucional/visao-geral.webp` | home, dobra solução |
| `static/img/institucional/dashboard.webp` | Como funciona, passo 1 |
| `static/img/institucional/transacoes.webp` | Como funciona, passo 2 |
| `static/img/institucional/relatorios.webp` | Como funciona, passo 3 |
| Mockup HTML `mockup_dashboard.html` | hero da home |

---

## 13. Inconsistências úteis para o próximo trabalho de design/copy

Fatos do estado atual — não são tarefas, são tensões visíveis:

1. **Duas promessas de produto.** Institucional: lançamento manual, “você registra”. Captura: importar extrato + IA em 2 minutos. A home admite importação só no card “Sem burocracia”, como opcional.
2. **Duas histórias do fundador.** Institucional: carta em 1ª pessoa sobre abandono de apps. Captura: quote de insight (R$ 545,05 em supermercado) após importar o extrato.
3. **CTA da captura diz “Preencha abaixo”** mas o form está no modal, não abaixo.
4. **FAQ da landing não está montado.** O FAQ institucional é o que o visitante encontra. O partial da captura ainda fala em garantia de 7 dias e reajuste de preço — copy desalinhada da FAQ viva.
5. **Cookie consent** só no aplicativo autenticado. `/comece/`, `/obrigado/` e o institucional não exibem o banner; o aviso de cookies de anúncios fica no formulário de cadastro.
6. **Header da captura** não oferece caminho de volta ao site institucional (logo aponta para `/comece/`).
7. **Documentos antigos** (`docs/marca/landing-copy.md`) ainda falam em R$48/ano, R$493 em compras e “50% … R$48/ano em vez de R$97”. O ar vivo da captura é R$4/mês vs R$8 e R$545,05 em supermercado.
8. **JSON-LD da FAQ institucional** omite a 6ª pergunta.

---

## 14. Arquivos-fonte (para quem for implementar)

| Peça | Caminho |
|---|---|
| Rotas | `usuarios/urls.py` |
| Views / contexto (WhatsApp, login, nav) | `usuarios/views.py` |
| Base institucional | `templates/institucional/base.html` |
| Base captura | `templates/landing/base_landing.html` |
| CSS tokens + landing | `static/landing/css/landing.css` |
| CSS institucional | `static/institucional/css/institucional.css` |
| JS captura / reveal / modal / FAQ | `static/landing/js/landing.js` |
| JS menu mobile | `static/institucional/js/institucional.js` |
| Posicionamento de marca (estratégia, não o site vivo) | `docs/marca/brand-context.md` |
