from __future__ import annotations

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from cartoes.models import Fatura
from cartoes.services.gestao_faturas import recalcular_fatura

from .models import Transacao


@receiver(pre_save, sender=Transacao)
def guardar_faturas_anteriores(sender, instance: Transacao, **kwargs):
    if not instance.pk:
        instance._old_fatura_id = None
        instance._old_pagamento_de_fatura_id = None
        return
    anterior = (
        Transacao.objects.filter(pk=instance.pk)
        .values("fatura_id", "pagamento_de_fatura_id")
        .first()
    )
    instance._old_fatura_id = anterior["fatura_id"] if anterior else None
    instance._old_pagamento_de_fatura_id = (
        anterior["pagamento_de_fatura_id"] if anterior else None
    )


def _recalcular_ids(fatura_ids):
    ids = [fid for fid in fatura_ids if fid]
    for fatura in Fatura.objects.filter(pk__in=set(ids)):
        recalcular_fatura(fatura)


@receiver(post_save, sender=Transacao)
def recalcular_faturas_pos_save(sender, instance: Transacao, **kwargs):
    _recalcular_ids(
        [
            getattr(instance, "_old_fatura_id", None),
            getattr(instance, "_old_pagamento_de_fatura_id", None),
            instance.fatura_id,
            instance.pagamento_de_fatura_id,
        ]
    )


@receiver(post_delete, sender=Transacao)
def recalcular_faturas_pos_delete(sender, instance: Transacao, **kwargs):
    _recalcular_ids([instance.fatura_id, instance.pagamento_de_fatura_id])
