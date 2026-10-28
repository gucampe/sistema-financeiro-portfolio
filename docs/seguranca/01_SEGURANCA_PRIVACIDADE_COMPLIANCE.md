# Segurança, Privacidade e Compliance — GranaGo

**Atualizado em:** 24 de julho de 2026  
**Premissa atual:** beta fechado (invite-only), **sem cadastro público**.  
**Escopo deste documento:** inventário factual do que já existe no código/infra versus o que ainda falta para abertura pública do SaaS.

Itens adiados de propósito até a abertura pública (Consentimento versionado, Turnstile, MFA, verificação de e-mail) estão marcados como **Falta (abertura pública)** — não bloqueiam o beta fechado.

---

## 1. Consentimento LGPD

Tratamento de dados e aceite explícito.

### Já feito

* Política de Privacidade (versão inicial) — `/privacidade/`
* Termos de Uso (versão inicial) — `/termos/`
* Arquitetura multi-tenant (isolamento por `usuario` / dono, com testes de IDOR)
* HTTPS (origin Let’s Encrypt + Cloudflare Full strict)
* Cookies Secure (`SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` em produção)
* Links públicos para Termos e Política (login, footer da landing, cross-links nos legais)
* Banner de cookies informativo (cookies essenciais; `localStorage`; link para `#cookies` na privacidade)

### Parcial

* Política de Cookies — **sem página `/cookies/` dedicada** (decisão atual: seção na Política de Privacidade + banner). Avaliar se basta para abertura pública ou se exige documento próprio.

### Falta (abertura pública)

* Tela de consentimento no cadastro
* Model/persistência de aceite (`Consentimento` ainda não existe)
* Versionamento dos documentos (hoje só “Última atualização: julho de 2026” no texto)
* Data do aceite
* IP do aceite
* Reaceite quando houver nova versão (hoje a cláusula de alteração é só textual nos Termos)

---

## 2. Documentação Jurídica

Separado do fluxo técnico de consentimento.

### Já feito

* Primeira versão dos Termos
* Primeira versão da Política
* Páginas públicas no ar (`/termos/`, `/privacidade/`)

### Parcial

* Publicação “definitiva” — páginas públicas existem, mas ainda com placeholders societários (`[RAZÃO SOCIAL]`, CNPJ `[●]`)
* Procedimento para alteração dos termos — há cláusula textual (§ alterações / uso continuado); **não há runbook operacional** (bump de versão, notificação, re-aceite)

### Falta

* Revisão jurídica
* Versionamento semântico persistido
* Histórico de versões
* Preenchimento definitivo de razão social / CNPJ / contatos reais
* Runbook de alteração + enforcement de reaceite (ligado à seção 1)

---

## 3. Cloudflare Turnstile

Proteção antibot em superfícies públicas.

### Já feito

* Cloudflare (DNS Proxied, Always HTTPS, cache bypass em `app.*`)
* Proxy (CF → nginx → Gunicorn; `cloudflare-realip` para Axes/logs)
* HTTPS

### Parcial

* Estratégia — **decisão de produto:** Turnstile só antes de cadastro aberto / superfícies públicas abusáveis; no beta fechado não bloqueia. Ainda falta escolher pontos exatos (cadastro gratuito vs checkout vs ambos).

### Falta (abertura pública)

* Implementar Turnstile onde fizer sentido (não há integração no código hoje)
* Reset de senha (hoje sem CAPTCHA)
* Formulário de contato (não existe — só `mailto:` nos legais; se for criado, proteger)
* Monitorar impacto na conversão

---

## 4. MFA

Segundo fator sobre a base de autenticação já existente.

### Já feito (base de autenticação — não é MFA)

* Login (e-mail/senha)
* Recuperação de senha (fluxo Django + SMTP Resend em produção)
* Axes (bloqueio por IP + username; lockout customizado)
* Proteção extra do `/admin/` via nginx basic auth (não substitui MFA)

### Falta (abertura pública / endurecimento)

* MFA obrigatório para staff
* MFA opcional para usuários
* Backup codes
* Fluxo de perda do autenticador

---

## 5. ACL da mídia

Acesso a arquivos privados (fotos de perfil, exports).

### Já feito

* Estrutura de mídia (`MEDIA_ROOT`, fotos de perfil, exports)
* Serving autenticado em produção (`PROTECT_MEDIA` + `protected_media`; nginx **sem** alias público de `/media/`)
* Ownership revisado (foto só do dono; export só do `ExportJob.usuario`; path traversal bloqueado)
* Testes automatizados (`config/tests/test_media_views.py` — cross-user, anon, owner, traversal)

### Parcial

* Auditoria completa — auditoria VPS/mídia registrada (ex.: A05); falta fechar achados remanescentes e revalidar pós go-live
* Bypass de staff — `is_staff` / `is_superuser` têm acesso total à mídia; inventário/revisão de contas staff ainda pendente

### Falta

* Garantir política explícita: staff bypass restrito ou justificado e documentado
* Revisão periódica de ownership + contas privilegiadas
* Re-auditoria consolidada pós endurecimentos recentes

---

## 6. Segurança operacional

Controles de infraestrutura e hardening.

### Já feito

* HTTPS
* HSTS (incl. subdomains + preload em produção)
* Sentry (DSN em produção; issue de smoke validada)
* Backup (script GPG + offsite R2; restore documentado)
* Uptime (synthetic monitoring GitHub Actions → `/health/`)
* Cloudflare
* Axes
* Multi-tenant
* fail2ban / UFW / unattended-upgrades (hardening VPS)
* Health check com payload mínimo (`/health/`, token opcional)

### Parcial

* CSP — implementada com `django-csp`, porém em produção ainda **report-only** (+ `unsafe-inline`)
* Auditoria VPS — formal em 2026-07-05 + remediações; HTTPS/Sentry/backup vieram depois; **não há re-auditoria “final” consolidada** pós go-live completo
* Usuários Linux / permissões — user `financeiro` e sudo mínimo documentados; **separação app/deploy (P2) não aplicada**
* SSH — PasswordAuthentication indevido do cloud-init foi corrigido no hardening; sem re-scan documentado após o go-live TLS

### Falta

* Auditoria final da VPS (pós TLS + Sentry + backup + R2)
* Auditoria atualizada de usuários Linux
* Re-auditoria SSH
* Revisão de permissões (incl. inventário `is_staff`)
* CSP em modo enforce (após estabilizar report-only)
* Hardening final (incl. USER_SEPARATION_P2, se for adotado)

---

## 7. Privacidade

Direitos do titular e minimização.

### Já feito

* Não envio de PII ao Sentry (`send_default_pii=False`)
* Scrubbing de eventos/logs (`_scrub_sentry_event`, helpers de sanitização)
* Política de retenção documentada (texto na privacidade) **e** automatizada (`purge_retention_data` + cron: LLM/UX/AuditLog/exports TTL)
* Processo de exclusão de conta (UI em configurações + limpeza de mídia/exports + `AuditLog`)
* Exportação de dados LGPD (pacote ZIP `titular_lgpd` via `ExportJob`)
* Canal de privacidade (`PRIVACIDADE_EMAIL` + mailto nos legais; SLA descrito no texto)

### Parcial

* Direito ao esquecimento — coberto operacionalmente pela **exclusão de conta** (cascade + limpeza de arquivos); não há fluxo separado de anonimização/esquecimento parcial

### Falta

* Completar placeholders jurídicos no canal/controlador (razão social, CNPJ, e-mail real de produção se ainda for default)
* DPIA formal da categorização LLM (hoje há stub em `docs/seguranca/DPIA_CATEGORIZACAO_LLM.md`) — relevante se IA for GA na abertura pública
* Opt-out de IA na UI (se/quando o LLM estiver ligado para o público)

---

## 8. Segurança do cadastro

Superfície de onboarding público (ainda desligada).

### Já feito

* Axes (protege login; não há signup para proteger)
* Recuperação de senha
* Rate limiting no login (Axes + `limit_req` nginx em `/login/` e `/admin/`)
* Rate limiting pontual em exports e batch de IA

### Falta (abertura pública)

* Cadastro público (hoje: template órfão sem rota; beta invite-only)
* Verificação de e-mail
* Consentimento (ligado à seção 1)
* Turnstile (caso adotado — seção 3)
* Rate limiting específico de signup / reset (além do padrão Django + Axes no login)
* Fluxo de confirmação de cadastro

---

## 9. Controles relacionados (fora da lista original)

Itens que já existem no projeto e fazem parte do mesmo pilar:

| Item | Status | Notas |
|------|--------|--------|
| `AuditLog` mínimo | Feito | `delete_account`, `export_requested`, `password_change`, `login_failed` |
| Admin com basic auth (nginx) | Feito | Camada extra; não é MFA |
| Host split landing/app | Feito | `HostRoutingMiddleware`, `APP_HOST` / `LANDING_HOSTS` |
| Maintenance mode | Feito | Flag + middleware |
| Plano de incidentes | Parcial | Stub em `docs/seguranca/PLANO_INCIDENTES.md` |
| Redação PII para LLM | Feito (código) | `redact_pii_for_llm`; depende de política/DPIA se IA for GA |
| Backup offsite R2 | Feito | Parte da continuidade |
| CSRF failure brandada | Feito | `CSRF_FAILURE_VIEW` |
| Separação user deploy (P2) | Falta | Documentado fora do repositório |

---

## Priorização sugerida (por estágio)

### Beta fechado (estado atual — manter)

Já cobre o essencial: HTTPS/HSTS, Axes, mídia protegida, políticas públicas (ainda com placeholders), export LGPD, exclusão, retenção+purge, Sentry scrub, backup/R2, uptime, Cloudflare.

### Antes da abertura pública (bloqueadores)

1. Preencher/revisar juridicamente Termos e Política (sem placeholders)
2. Cadastro público + consentimento versionado (aceite, IP, data, reaceite)
3. Verificação de e-mail
4. Turnstile (ou equivalente) nos pontos públicos abusáveis
5. MFA obrigatório para staff (mínimo)
6. Fechar bypass staff de mídia + inventário de contas privilegiadas
7. CSP enforce (se report-only estiver estável)
8. DPIA LLM se categorização com IA for GA

### Pós-abertura / escala

* MFA opcional para usuários + backup codes + recovery
* Política de cookies dedicada (se a avaliação exigir)
* Re-auditoria VPS final + USER_SEPARATION_P2
* Plano de incidentes formal
* Monitoramento de conversão com Turnstile
* Histórico público de versões dos documentos legais

---

## Referências no repositório

* Páginas legais: `usuarios/templates/usuarios/legal/`
* Mídia protegida: `config/media_views.py`
* Export LGPD: `relatorios/export/domains/titular.py`
* Exclusão de conta: `usuarios/views.py` (`excluir_conta`)
* Observabilidade/Sentry: `config/observability.py`
* Relatório histórico LGPD: `docs/seguranca/RELATORIO_SEGURANCA_LGPD.md`
* Backup/restore: `docs/operacao/BACKUP_RESTORE.md`
* Setup R2/Sentry/uptime: `docs/operacao/SETUP_BACKUP_SENTRY_UPTIME.md`
* Plano histórico (fases): `.cursor/plans/plano_ação_segurança_lgpd_eec2c918.plan.md`
