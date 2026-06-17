"""Invalidação de cache de agregações do dashboard."""

from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from cartoes.models import Fatura
from contas.models import Conta
from relatorios.models import OrcamentoCategoria
from relatorios.services.dashboard_cache import invalidate_dashboard_user
from transacoes.models import Transacao


def _invalidate(sender, instance, **kwargs):
    user_id = getattr(instance, "usuario_id", None)
    if user_id:
        invalidate_dashboard_user(user_id)


for model in (Transacao, Conta, Fatura, OrcamentoCategoria):
    post_save.connect(_invalidate, sender=model, dispatch_uid=f"dash_cache_save_{model.__name__}")
    post_delete.connect(_invalidate, sender=model, dispatch_uid=f"dash_cache_del_{model.__name__}")
