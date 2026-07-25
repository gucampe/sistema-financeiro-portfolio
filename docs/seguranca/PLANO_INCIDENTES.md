# Plano de resposta a incidentes (stub)

## Classificação

| Nível | Exemplo | Prazo inicial |
|-------|---------|---------------|
| P1 | Vazamento de dados de titulares | 1h |
| P2 | Indisponibilidade prolongada | 4h |
| P3 | Bug sem exposição de dados | 24h |

## Fluxo P1 (dados pessoais)

1. Conter (revogar chaves, isolar serviço, bloquear conta comprometida).
2. Avaliar escopo (logs Sentry, AuditLog, LLMRequestLog — sem payloads).
3. Notificar responsável interno e, se aplicável, ANPD/titulares conforme orientação jurídica.
4. Registrar timeline e ações corretivas.
5. Post-mortem em até 5 dias úteis.

## Contatos

- Técnico: equipe de desenvolvimento
- Privacidade: `privacidade@granago.app` (configurável via `PRIVACIDADE_EMAIL`)

## Evidências

- Sentry (erros sanitizados)
- AuditLog (`delete_account`, `export_requested`, `password_change`, `login_failed`)
- Neon PITR / backups — ver `docs/operacao/BACKUP_RESTORE.md`
