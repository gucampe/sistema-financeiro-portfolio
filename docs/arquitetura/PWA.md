<!-- Data de criação: 2026-09-15 -->

# PWA v1 — GranaGo

O PWA é **a mesma aplicação Django + HTMX** em `https://app.granago.com.br`, aberta em `display: standalone`. Não existe uma segunda aplicação, SPA, API paralela nem `if PWA: esconder feature`.

**Paridade:** tudo que já funciona no SaaS com internet continua disponível no ícone. **OFX e XLSX são critério de aceite** no PWA instalado (Android e iOS). PDF ainda não está no produto e ficou fora desta v1; quando entrar, herda o PWA automaticamente.

## Arquitetura

```text
Ícone instalado
  → https://app.granago.com.br
  → mesmas views Django + HTMX
  → mesma sessão / CSRF
  → PostgreSQL
```

Landing (`granago.com.br`) **não** recebe manifest, service worker nem CTA de instalação.

## Endpoints

Servidos por [`config/pwa_views.py`](../../config/pwa_views.py), URLs estáveis (sem hash do WhiteNoise):

| URL | Tipo | Cache |
| --- | --- | --- |
| `/manifest.webmanifest` | `application/manifest+json` | `Cache-Control: no-cache` |
| `/sw.js` | `application/javascript` | `Cache-Control: no-cache` |

Com `APP_HOST` definido, esses caminhos respondem **404** na landing.

### Manifest

- `id` em produção: `https://app.granago.com.br/`
- `start_url`: `/` (sem UTM). Anônimo → login; autenticado → dashboard (middleware existente, inalterado).
- `scope`: `/`
- `display`: `standalone`
- `theme_color` / `background_color`: `#f4f5f7` (fallback). A meta HTML continua atualizada por [`static/js/theme.js`](../../static/js/theme.js).
- Ícones 192/512 `purpose: any` e maskable `purpose: maskable`.

### Service worker

Mínimo com handler `fetch` **pass-through** (`fetch(event.request)`), para o `beforeinstallprompt` do Chromium.

Não implementa:

- `caches` / cache de HTML, HTMX, relatórios ou dados financeiros
- `skipWaiting` / `clients.claim`
- offline, fila, sync, IndexedDB

## Ícones

Gerados a partir de [`static/img/icons/logo.svg`](../../static/img/icons/logo.svg) (script [`scripts/gerar_icones_pwa.py`](../../scripts/gerar_icones_pwa.py)):

```text
static/img/icons/pwa/
├── icon-192.png
├── icon-512.png
├── icon-192-maskable.png
├── icon-512-maskable.png
└── apple-touch-icon.png   (180×180, opaco)
```

Maskable e apple-touch: fundo `#f4f5f7` (surface do app). O logo oficial já é verde; fundo `#16a34a` esconderia o símbolo.

## Instalação

Prioridade: **Android Chrome** e **iOS Safari**. Desktop Chrome/Edge quando o navegador oferecer.

- **Chromium:** `beforeinstallprompt` → botão “Instalar app”. Cancelar não conta como instalado. `appinstalled` confirma.
- **iOS Safari:** “Compartilhe esta página e escolha Adicionar à Tela de Início.”
- **Chrome/Firefox no iOS:** orientar a abrir no Safari.
- Infra (manifest, SW, metas) também na tela de **login**.
- CTA de instalação só para **usuário autenticado**, depois do banner de cookies, fora de standalone e fora do cooldown de 14 dias (`localStorage` `granago_pwa_install_dismissed_at`).
- Fallback permanente: Configurações → **Aplicativo**.

## Safe area

`viewport-fit=cover` no [`templates/base.html`](../../templates/base.html). `env(safe-area-inset-*)` no header (padding do `body` só em `display-mode: standalone` / `html.pwa-standalone`) e na sidebar. Sheets já usavam `safe-area-inset-bottom`; com `viewport-fit=cover` passam a valer no iPhone.

Aba normal do navegador não recebe o padding extra do `body`.

## Analytics

Somente [`usuarios/services/produto_eventos.py`](../../usuarios/services/produto_eventos.py) + `POST /produto-evento/` (exige autenticação). Sem GA4/Clarity.

Eventos: `pwa_install_prompt_shown`, `pwa_install_clicked`, `pwa_install_dismissed`, `pwa_installed`, `pwa_opened_standalone`.

`pwa_opened_standalone` representa **usuários autenticados** identificados pela infra atual, não necessariamente todas as aberturas standalone (login ainda não autenticado).

## Infra

[`deploy/nginx/financeiro.conf`](../../deploy/nginx/financeiro.conf): `location = /sw.js` e `= /manifest.webmanifest` no server do app, com `Cache-Control: no-cache` e `CDN-Cache-Control: no-store` (Cloudflare). WhiteNoise segue nos static.

Não há Cache Rule de Cloudflare versionada neste repositório. Após o deploy, conferir no painel se `/sw.js` não está em cache longo. Se o bloco HTTPS tiver sido gerado pelo Certbot, copiar os dois `location =` para o server 443.

Sessão: **não** alterar `SESSION_COOKIE_AGE` (24h). Cookies/CSRF/hosts inalterados.

## Paridade funcional e OFX/XLSX

O PWA não altera views de negócio. Importação OFX e XLSX já usa `input type="file"` (sem depender de drag-and-drop).

Fluxo de aceite em dispositivo real:

```text
PWA instalado → abrir GranaGo → Importar extrato
→ selecionar arquivo → upload → prévia → confirmar
→ processamento → transações criadas
```

Testar OFX e XLSX em Android e iPhone, com internet.

## Fora da v1

Offline, fila, push, IndexedDB financeiro, TWA/Capacitor/stores, PWA na landing, alongar sessão, SPA, importação PDF, screenshots no manifest, cache de HTML/HTMX.

## Checklist manual

### Android (Chrome)

- Instalar; ícone; abrir standalone (sem barra de URL); login; HTMX; CSRF; importar OFX; importar XLSX; prévia; confirmar; relatórios; tema.

### iPhone (Safari)

- Adicionar à Tela de Início; splash/ícone; safe area (notch e home indicator); login; HTMX; CSRF; selecionar arquivo; OFX; XLSX; prévia; confirmar; relatórios; tema.
- Chrome iOS: CTA pede para abrir no Safari.

### Desktop (Chrome/Edge)

- Instalar se o navegador oferecer; abrir standalone; navegação; login; fluxos principais.

Não há e2e de instalação no CI (depende do navegador).

## Testes automatizados

```text
pytest config/tests/test_pwa.py usuarios/tests/test_ajuda.py -k "pwa or ProdutoEvento"
```
