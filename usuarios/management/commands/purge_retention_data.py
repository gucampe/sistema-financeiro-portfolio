"""Remove dados além do prazo de retenção (LGPD / operação)."""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from config.llm_settings import (
    AUDIT_LOG_RETENTION_DAYS,
    CATEGORIZACAO_LLM_LOG_RETENTION_DAYS,
    CATEGORIZACAO_UX_EVENT_RETENTION_DAYS,
    PRODUTO_EVENTO_RETENTION_DAYS,
)
from relatorios.services.export.cleanup import limpar_exports_expirados
from usuarios.models import AuditLog, ProdutoEvento


class Command(BaseCommand):
    help = "Purge de LLMRequestLog, CategorizacaoUXEvent, ProdutoEvento, AuditLog e exports órfãos."

    def handle(self, *args, **options):
        now = timezone.now()
        stats: dict[str, int] = {}

        try:
            from categorizacao.models import CategorizacaoUXEvent, LLMRequestLog

            cutoff_llm = now - timedelta(days=CATEGORIZACAO_LLM_LOG_RETENTION_DAYS)
            stats["llm_request_log"] = LLMRequestLog.objects.filter(
                criado_em__lt=cutoff_llm
            ).delete()[0]

            cutoff_ux = now - timedelta(days=CATEGORIZACAO_UX_EVENT_RETENTION_DAYS)
            stats["categorizacao_ux_event"] = CategorizacaoUXEvent.objects.filter(
                criado_em__lt=cutoff_ux
            ).delete()[0]
        except Exception as exc:
            self.stderr.write(f"Aviso: purge IA parcial — {exc}")

        cutoff_audit = now - timedelta(days=AUDIT_LOG_RETENTION_DAYS)
        stats["audit_log"] = AuditLog.objects.filter(criado_em__lt=cutoff_audit).delete()[0]

        cutoff_produto = now - timedelta(days=PRODUTO_EVENTO_RETENTION_DAYS)
        stats["produto_evento"] = ProdutoEvento.objects.filter(criado_em__lt=cutoff_produto).delete()[0]

        export_stats = limpar_exports_expirados()
        stats.update(export_stats)

        self.stdout.write(
            self.style.SUCCESS(
                "Purge concluído: "
                + ", ".join(f"{k}={v}" for k, v in sorted(stats.items()))
            )
        )
