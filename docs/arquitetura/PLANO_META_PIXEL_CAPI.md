# Plano: Pixel + API de Conversão da Meta no cadastro

**Data de criação:** 8 de setembro de 2026

## Objetivo

Medir cadastros do programa Primeiros Donos no Gerenciador de Eventos da Meta, com:

- **Pixel** no navegador (PageView + conversão)
- **Conversions API (CAPI)** no servidor (mesmo evento, com e-mail/telefone hasheados)
- **Mesmo `event_id`** nos dois canais, para a Meta deduplicar e não contar o cadastro duas vezes

## Onde está o cadastro hoje

O formulário que importa **não** é `usuarios/templates/usuarios/partials/cadastro.html` (não é referenciado).

O fluxo real é:

1. Landing `/comece/` (`landing_view`)
2. Modal `templates/landing/partials/modal_captura.html`
3. POST `/captura/` (`captura_lead_view` → `registrar_primeiro_dono`)
4. Redirect `/obrigado/` (`obrigado_view`)

Campos disponíveis para matching avançado: nome, e-mail, WhatsApp.

## Estado atual que bloqueia um “colar o snippet”

| Ponto | Situação |
|---|---|
| Pixel / CAPI | Não existem |
| Política de Privacidade | Diz explicitamente que **não** há cookies de marketing nem rastreamento publicitário |
| Banner de cookies | Só informativo (“Entendi”), só no site institucional e no app. **A landing `/comece/` não tem banner** |
| CSP | Não libera `connect.facebook.net`, `www.facebook.com`, `graph.facebook.com` |
| Consentimento persistido | Só aceite de Termos/Privacidade no cadastro (`Consentimento`), sem categoria de marketing |

Colocar o Pixel sem atualizar isso viola a política publicada e enfraquece o matching (e o Event Match Quality).

## Arquitetura recomendada

```
Visitante em /comece/
        │
        ├─ Aceitou cookies de marketing? ── sim ──► carrega Pixel (PageView)
        │
        ▼
POST /captura/ válido
        │
        ├─ Gera event_id (UUID)
        ├─ CAPI: CompleteRegistration (sempre, se CAPI configurada)
        │     hashed email + phone + first_name
        │     + fbp/fbc se existirem
        │     + IP + User-Agent
        ├─ Grava event_id na sessão
        └─ Redirect /obrigado/
                │
                └─ Aceitou marketing? ── sim ──► Pixel CompleteRegistration
                                                   com o mesmo event_id
```

Evento padrão da Meta para criação de conta: **`CompleteRegistration`**.  
Não disparar no clique do botão: só depois do POST válido. Assim não conta tentativa recusada pelo Turnstile ou pelo form.

## O que fazer, na ordem

### 1. Configurar na Meta (fora do código)

No Gerenciador de Eventos:

1. Criar (ou reutilizar) o Pixel
2. Gerar token da Conversions API (nunca no frontend)
3. Verificar o domínio do site de marketing
4. Anotar o código de teste (`TEST…`) para homologação
5. Depois de ir ao ar: ligar deduplicação e conferir Event Match Quality

Guardar só em env, no mesmo padrão do Turnstile:

- `META_PIXEL_ID`
- `META_CAPI_ACCESS_TOKEN`
- `META_CAPI_TEST_EVENT_CODE` (só staging/homologação)

Sem token/id, o código não dispara nada.

### 2. Ajustar LGPD e cookies (antes do snippet)

Não dá para só injetar o script. Precisa, no mínimo:

1. Atualizar a Política de Privacidade:
   - Meta Platforms como destinatário de dados de medição de anúncios
   - cookies `_fbp` / `_fbc`
   - envio de identificadores hasheados (e-mail, telefone, nome) via CAPI
   - transferência internacional
   - como recusar/revogar
2. Bump de `LEGAL_PRIVACY_VERSION`
3. Banner na **landing** (`base_landing.html`), não só no institucional
4. Trocar “Entendi” por escolha real:
   - **Aceitar marketing** → carrega Pixel
   - **Só essenciais** → não carrega Pixel; CAPI ainda pode ir no cadastro se a política/aceite do form cobrir medição da conversão
5. Só carregar `connect.facebook.net` depois do opt-in de marketing

O texto atual do modal (“Ao garantir sua vaga, você concorda com a Política…”) só cobre a CAPI se a política já descrever esse envio. Sem isso, não enviar PII para a Meta.

### 3. Pixel (browser)

Novo partial, incluído no `head` de `templates/landing/base_landing.html` (e, se quiser remarketing no institucional, em `templates/institucional/base.html`):

- Stub `fbq` + `fbq('init', PIXEL_ID)` + `PageView` **somente com consentimento**
- Em `/obrigado/`: `fbq('track', 'CompleteRegistration', {}, {eventID: event_id})`
- Não colocar Pixel no app autenticado (`templates/base.html`) — não mede cadastro e aumenta superfície de rastreamento

### 4. CAPI (servidor, no Django)

Novo serviço, por exemplo `usuarios/services/meta_conversions.py`, chamado em `captura_lead_view` **depois** de `registrar_primeiro_dono` ter sucesso (idealmente `transaction.on_commit`, para não reportar cadastro que deu rollback).

Payload mínimo:

- `event_name`: `CompleteRegistration`
- `event_time`: unix
- `event_id`: o UUID da sessão
- `action_source`: `website`
- `event_source_url`: URL absoluta de `/comece/`
- `user_data`:
  - `em`, `ph`, `fn` em SHA-256 hex (normalizar antes: e-mail lowercase/trim; telefone só dígitos com DDI `55`)
  - `client_ip_address`, `client_user_agent`
  - `fbp` / `fbc` dos cookies, se existirem
- `test_event_code` só quando a env estiver setada

Regras:

- Nunca logar token, e-mail, telefone ou payload em claro
- Timeout curto; falha da Meta **não** quebra o cadastro
- Não chamar em testes (mock / settings vazias)

Endpoint: `POST https://graph.facebook.com/v21.0/{PIXEL_ID}/events`

### 5. CSP

Em `config/settings.py`, liberar (pelo menos):

- `script-src`: `https://connect.facebook.net`
- `img-src`: `https://www.facebook.com`
- `connect-src`: `https://www.facebook.com`, `https://graph.facebook.com`
- `frame-src` se o Pixel usar iframe

Hoje o CSP está em `REPORT_ONLY=True`; mesmo assim vale alinhar as listas para quando for enforce.

### 6. Testes e homologação

- Testes unitários do hasher e do payload (sem HTTP real)
- View de captura: com settings da Meta, o serviço é chamado uma vez; sem settings, não é
- Evento duplicado (reenvio do mesmo e-mail) não deve disparar outro `CompleteRegistration` se o usuário já existia — usar o flag `created` de `registrar_primeiro_dono` (hoje o retorno só tem `setup_url`; precisa expor se foi cadastro novo)
- Homologar no Test Events do Gerenciador: Pixel + CAPI com o mesmo `event_id` aparecem como um evento só

## Fora de escopo (de propósito)

- Pixel dentro do SaaS autenticado
- Eventos `Purchase` / `Subscribe` (não há checkout)
- `Lead` além de `CompleteRegistration` (só adicionar se a campanha exigir formulário ≠ conta criada)
- iOS Advanced Matching extra além de e-mail/telefone/nome

## Critério de pronto

1. Cadastro novo em `/comece/` gera um `CompleteRegistration` no Test Events
2. Pixel e CAPI chegam com o mesmo `event_id`
3. Sem opt-in de marketing, o script da Meta não carrega
4. Política de Privacidade e banner descrevem o que o código faz
5. Cadastro continua funcionando se a Meta estiver fora do ar
6. Secrets só em env; `.env.example` documentado

## Próximo passo de implementação

Quando este plano for aprovado, a ordem de PR sugerida é:

1. Legal + banner de consentimento na landing
2. Serviço CAPI + hook no POST `/captura/`
3. Partial do Pixel + disparo em `/obrigado/`
4. CSP + envs de produção
