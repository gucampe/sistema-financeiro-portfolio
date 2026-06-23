from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from categorizacao.services.learning import processar_feedback_transacao
from transacoes.models import Transacao


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

    if not created:
        return

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
