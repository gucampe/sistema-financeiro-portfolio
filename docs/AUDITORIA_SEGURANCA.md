# Auditoria de Autenticação, Segurança e Multi-Tenant

**Projeto:** GranaGo — SaaS de gestão financeira pessoal  
**Data:** 15/06/2026  
**Escopo:** Autenticação, autorização, isolamento de dados, sessões, CSRF, preparação SaaS

---

## Resumo executivo

O sistema possui **base sólida de segurança multi-tenant**: todas as views financeiras exigem autenticação, queries de detalhe/edição/exclusão filtram por `usuario=request.user`, e há suíte de testes de IDOR/CSRF. Foram encontrados **2 problemas críticos** (bloqueio de usuário inativo e backend duplicado) e **corrigidos nesta auditoria**. O projeto ainda opera em perfil de desenvolvimento e carece de fluxos SaaS futuros (billing, cadastro público, reset de senha).

---

## 1. Autenticação

### Login ✅

| Item | Status |
|------|--------|
| Usa `authenticate()` + `login()` do Django | ✅ |
| Login por e-mail (`EmailBackend`) | ✅ |
| Mensagem genérica em falha (anti-enumeração) | ✅ |
| CSRF no formulário | ✅ |
| Redirect fixo para `relatorios:home` (sem open redirect) | ✅ |
| Rate limiting / brute-force | ❌ Pendente |

**Arquivos:** `usuarios/views.py`, `usuarios/backends.py`, `usuarios/templates/usuarios/partials/login.html`

### Logout ✅

- `LogoutView` padrão do Django invalida a sessão.
- UI usa **POST + CSRF** (`templates/base/header_nav_right.html`) — boa prática contra logout CSRF.

### Alteração de senha ✅

- `ConfiguracoesPasswordChangeForm` (extends `PasswordChangeForm`).
- Protegida com `@login_required`.
- `update_session_auth_hash()` evita logout após troca.
- Validadores de senha do Django ativos.

### Recuperação de senha ❌ Pendente

- **Não implementada.**
- Link no login aponta para `#` (placeholder).
- Sem `django.contrib.auth.urls` (reset/confirm).
- Sem configuração `EMAIL_*` — envio de e-mail indisponível.
- **Recomendação:** implementar após definir provedor de e-mail (Resend, SES, etc.).

### Cadastro público ❌ Pendente

- Template `cadastro.html` existe, mas sem view/URL.
- Usuários criados via admin Django + comando `criar_superusuario`.

---

## 2. Proteção de rotas

### Inventário (47 endpoints)

| App | Total | Protegidas | Públicas |
|-----|-------|------------|----------|
| `usuarios` | 4 | 2 | 2 (login, logout) |
| `contas` | 4 | 4 | 0 |
| `categorias` | 8 | 8 | 0 |
| `cartoes` | 7 | 7 | 0 |
| `transacoes` | 9 | 9 | 0 |
| `relatorios` | 14 | 14 | 0 |
| `config` | 1 | 0 | 1 (redirect legado → home) |

### Mecanismos

- FBVs: `@login_required`
- CBVs: `LoginRequiredMixin` / `RelatorioFiltrosMixin(LoginRequiredMixin)`
- APIs AJAX: todas com `LoginRequiredMixin`
- Anônimos em rotas privadas → **302 para `/login/`**

### Views públicas intencionais

1. `login_view` — entrada do sistema
2. `LogoutView` — saída
3. `legacy_dashboard_redirect` — redireciona para home (que exige login)

**Nenhuma view financeira exposta sem autenticação.**

---

## 3. Multi-tenant — isolamento de dados

### Models financeiros

| Model | FK `usuario` | Isolamento |
|-------|--------------|------------|
| `Transacao` | Obrigatório | Total |
| `Conta` | Obrigatório | Total |
| `Cartao` | Obrigatório | Total |
| `Fatura` | Obrigatório | Total |
| `OrcamentoCategoria` | Obrigatório | Total |
| `ExportRelatorioJob` | Obrigatório | Total |
| `Perfil` | OneToOne | Total |
| `Categoria` | Opcional (nullable) | **Parcial** — globais `padrao=True` compartilhadas |

### Padrão de queries nas views

Todas as operações sensíveis usam:

```python
get_object_or_404(Modelo, pk=..., usuario=request.user)
```

Listagens usam:

```python
Modelo.objects.filter(usuario=request.user)
```

Relatórios/APIs usam `transacoes_base_qs(usuario)` + `parse_relatorio_filtros()` que descarta IDs de conta/categoria de outros usuários.

### Validação em camada de model

- `Transacao.clean()` valida que conta, cartão, fatura e categoria pertencem ao mesmo usuário (ou categoria padrão).
- Forms de preferências (`PreferenciasFinanceirasForm`) rejeitam conta/categoria de outro tenant.

### Testes de IDOR existentes ✅

`usuarios/tests/test_seguranca.py` cobre:
- Editar/excluir transação de outro usuário → 404
- Arquivar conta, excluir cartão, ver fatura → 404
- Export job de outro usuário → 404
- Import em conta de outro usuário → 404
- CSRF em endpoints mutáveis → 403

### Entidades sem model dedicado

- **Metas:** não existe model
- **Investimentos:** tipo de conta (`Conta.tipo=investimento`), sem model separado
- **Import jobs:** processamento direto em views, sem model de job

---

## 4. Segurança geral Django

### Sessão

| Config | Antes | Depois |
|--------|-------|--------|
| `SESSION_COOKIE_AGE` | 24h | 24h |
| `SESSION_EXPIRE_AT_BROWSER_CLOSE` | False | Configurável via env |
| `SESSION_COOKIE_HTTPONLY` | Default (True) | Explícito True |
| `SESSION_COOKIE_SAMESITE` | Default | `Lax` |
| `SESSION_COOKIE_SECURE` | Não | **True quando `DEBUG=False`** |

### CSRF ✅

- Middleware ativo.
- Formulários com `{% csrf_token %}`.
- AJAX envia `X-CSRFToken` (dash, cartões, export).
- Teste `test_unit_sec_16` valida 403 sem token.

### Produção

| Item | Status |
|------|--------|
| `SECRET_KEY` via env | ✅ Corrigido (decouple) |
| `DEBUG` via env | ✅ Corrigido |
| `ALLOWED_HOSTS` via env | ✅ Corrigido |
| `CSRF_TRUSTED_ORIGINS` via env | ✅ Adicionado |
| HTTPS (`SECURE_SSL_REDIRECT`, HSTS) | ✅ Quando `DEBUG=False` |
| Mídia servida publicamente | ✅ Apenas em `DEBUG` (`config/urls.py`) |

### Uploads

- Foto de perfil: limite 2 MB, MIME types restritos (`usuarios/forms.py`).
- Export CSV: download via `FileResponse` com filtro `usuario=request.user`.
- Arquivos em `media/exports/` e `media/perfis/` — **não expostos em produção** (sem `static()` em `DEBUG=False`).

---

## 5. User model

### Modelo customizado ✅

`usuarios.Usuario` extends `AbstractUser`:
- Login por `email` (sem `username`)
- Campos: `nome`, `data_nascimento`, `ativo`, `criado_em`
- `Perfil` (OneToOne) para preferências e avatar

### Campo `ativo` vs `is_active` ⚠️

- Admin expõe `ativo` (campo custom) e `is_active` (herdado do AbstractUser).
- **Problema encontrado:** `ModelBackend` autenticava por e-mail ignorando `ativo`.
- **Correção:** `EmailBackend.user_can_authenticate()` agora exige `ativo=True`; `ModelBackend` removido dos backends.

### Impacto futuro (sem migração agora)

O custom user model **já está em uso** — não há necessidade de migração futura. Recomenda-se sincronizar `ativo` ↔ `is_active` no admin ou via signal para evitar confusão operacional.

---

## 6. Estrutura SaaS

### O que NÃO existe ainda

| Recurso | Status |
|---------|--------|
| Planos / pricing | ❌ |
| Trial | ❌ |
| Assinatura / billing | ❌ |
| Status de acesso por pagamento | ❌ |
| Onboarding | ❌ |
| Verificação de e-mail | ❌ |
| Multi-organização (workspace) | ❌ |

### O que já prepara o terreno

- Isolamento por `usuario` em todos os models financeiros
- Campo `ativo` para desabilitar acesso (agora efetivo no login)
- Usuários criados apenas pelo admin (controle de provisionamento)
- Testes de contrato de segurança documentados (rate limit, auditoria — skipped)

### Recomendação arquitetural futura

```
Usuario
  └── Assinatura (plano, status, trial_ends_at, stripe_customer_id)
        └── limites por plano (contas, cartões, importações/mês)
```

Implementar como app `billing` separado, sem alterar o isolamento atual por `usuario`.

---

## O que está bom

1. **Isolamento multi-tenant consistente** — padrão `usuario=request.user` em todas as views financeiras.
2. **Suíte de testes de segurança** — IDOR, CSRF, import cross-tenant, forms com validação de tenant.
3. **Validação em profundidade** — `Transacao.clean()`, forms de preferências, filtros de relatório.
4. **Logout seguro** — POST + CSRF.
5. **Custom user model** — login por e-mail, sem username legado.
6. **Categorias globais** — design intencional (`padrao=True`) para defaults do sistema.
7. **Mídia protegida em produção** — servida apenas com `DEBUG=True`.
8. **Troca de senha** — fluxo Django padrão com renovação de sessão.

---

## Problemas críticos (corrigidos)

### CRIT-01: Usuário com `ativo=False` ainda autenticava

**Causa:** `django.contrib.auth.backends.ModelBackend` usava `USERNAME_FIELD=email` e ignorava o campo `ativo`.

**Correção:**
- `EmailBackend.user_can_authenticate()` verifica `ativo`
- `EmailBackend.get_user()` invalida sessão de usuário inativo
- Removido `ModelBackend` duplicado de `AUTHENTICATION_BACKENDS`
- Teste `test_unit_sec_02b_usuario_inativo_nao_autentica` adicionado

### CRIT-02: Queries secundárias sem filtro explícito de usuário

**Risco:** Baixo (objeto pai já validado), mas violava defesa em profundidade.

**Correção:**
- `categorias/views.py` — contagem de transações por categoria
- `transacoes/views.py` — deduplicação OFX por FITID

---

## Problemas médios (não corrigidos — recomendações)

| # | Problema | Recomendação |
|---|----------|--------------|
| MED-01 | `SECRET_KEY` hardcoded como default em dev | Definir `SECRET_KEY` no `.env` de produção |
| MED-02 | `ALLOWED_HOSTS=*` em dev | Restringir em produção via env |
| MED-03 | Sem rate limit no login | `django-axes` ou throttle no reverse proxy |
| MED-04 | `ativo` e `is_active` duplicados | Signal de sincronização ou unificar no admin |
| MED-05 | Sem auditoria de ações sensíveis | Log de pagamento de fatura, exclusões (teste skip AUD-01) |
| MED-06 | Export job em thread sem fila | Aceitável no MVP; migrar para Celery/RQ em escala |
| MED-07 | Sem 2FA | Considerar para SaaS financeiro em fase 2 |

---

## Pendências futuras

- [ ] Recuperação de senha (reset por e-mail)
- [ ] Verificação de e-mail no cadastro
- [ ] Cadastro público / onboarding
- [ ] Billing (Stripe/Pagar.me) + planos
- [ ] Rate limiting no login
- [ ] Auditoria de ações (pagamento fatura, exclusões)
- [ ] 2FA (TOTP)
- [ ] Sincronização `ativo` ↔ `is_active`
- [ ] Split settings dev/prod (opcional — env vars já cobrem o essencial)

---

## Correções realizadas nesta auditoria

| Arquivo | Alteração |
|---------|-----------|
| `usuarios/backends.py` | `user_can_authenticate()` checa `ativo`; `get_user()` invalida inativos |
| `config/settings.py` | `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS` via env; cookies seguros em produção; removido `ModelBackend` duplicado |
| `categorias/views.py` | Filtro `usuario=request.user` em contagem de transações |
| `transacoes/views.py` | Filtro `usuario=request.user` em queries OFX/FITID |
| `usuarios/tests/test_seguranca.py` | Teste de bloqueio de usuário inativo |

---

## Recomendações arquiteturais

1. **Manter isolamento por `usuario`** — não introduzir queries sem filtro de tenant; considerar manager base `TenantQuerySet` no futuro.
2. **Billing como app separado** — `Assinatura` ligada ao `Usuario`, sem alterar models financeiros.
3. **Provisionamento admin-only até checkout** — fluxo atual (admin cria → usuário acessa) é adequado para pré-lançamento.
4. **E-mail transacional** — pré-requisito para reset de senha e notificações SaaS.
5. **Categorias globais** — manter `padrao=True`; nunca permitir edição/exclusão por usuários comuns.
6. **Importações** — considerar model `ImportJob` com `usuario` para rastreabilidade e limites por plano.
7. **Produção** — deploy com `DEBUG=False`, `SECRET_KEY` forte, `ALLOWED_HOSTS` restrito, `CSRF_TRUSTED_ORIGINS` com domínio real.

---

## Checklist de deploy seguro

```bash
# Variáveis obrigatórias em produção
DEBUG=False
SECRET_KEY=<chave-aleatoria-50+chars>
ALLOWED_HOSTS=app.seudominio.com
CSRF_TRUSTED_ORIGINS=https://app.seudominio.com
```

Com `DEBUG=False`, o sistema ativa automaticamente:
- `SESSION_COOKIE_SECURE`
- `CSRF_COOKIE_SECURE`
- `SECURE_SSL_REDIRECT`
- `SECURE_HSTS_*`
