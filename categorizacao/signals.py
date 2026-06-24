from __future__ import annotations

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from categorizacao.services.learning import processar_feedback_transacao
from transacoes.models import Transacao


@receiver(pre_save, sender=Transacao)
def _cache_estado_anterior_transacao(sender, instance: Transacao, **kwargs):
    if not instance.pk:
        return
    prev = (
        Transacao.objects.filter(pk=instance.pk)
        .values("categoria_id", "descricao")
        .first()
    )
    if prev:
        instance._categorizacao_prev = prev


@receiver(post_save, sender=Transacao)
def aprender_categorizacao_transacao(sender, instance: Transacao, created, **kwargs):
    meta = getattr(instance, "_categorizacao_meta", None)
    if meta is not None:
        processar_feedback_transacao(
            usuario=instance.usuario,
            transacao=instance,
            descricao=instance.descricao,
            categoria_final=instance.categoria,
            categoria_sugerida_id=meta.get("categoria_sugerida_id"),
            confianca=meta.get("confianca"),
            fonte=meta.get("fonte", ""),
            merchant_key=meta.get("merchant_key", ""),
            contexto=meta.get("contexto"),
        )
        return

    if created:
        processar_feedback_transacao(
            usuario=instance.usuario,
            transacao=instance,
            descricao=instance.descricao,
            categoria_final=instance.categoria,
            categoria_sugerida_id=None,
            confianca=None,
            fonte="",
            merchant_key="",
        )
        return

    prev = getattr(instance, "_categorizacao_prev", None)
    if not prev:
        return

    categoria_mudou = prev.get("categoria_id") != instance.categoria_id
    descricao_mudou = (prev.get("descricao") or "") != (instance.descricao or "")
    if not categoria_mudou and not descricao_mudou:
        return

    processar_feedback_transacao(
        usuario=instance.usuario,
        transacao=instance,
        descricao=instance.descricao,
        categoria_final=instance.categoria,
        categoria_sugerida_id=prev.get("categoria_id") if categoria_mudou else None,
        confianca=None,
        fonte="manual_edit",
        merchant_key="",
        contexto={"edit": True, "descricao_mudou": descricao_mudou},
    )
