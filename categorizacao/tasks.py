from __future__ import annotations

import logging
import threading

from celery import shared_task

logger = logging.getLogger(__name__)


def dispatch_recategorizacao(usuario_id: int, categoria_nome: str = "Diversos", limite: int = 500):
    backend = _get_backend()
    if backend == "celery":
        recategorizar_lote_task.delay(usuario_id, categoria_nome, limite)
    else:
        threading.Thread(
            target=_run_recategorizacao,
            args=(usuario_id, categoria_nome, limite),
            daemon=True,
        ).start()


def _get_backend() -> str:
    from django.conf import settings
    return getattr(settings, "CATEGORIZACAO_JOB_BACKEND", "thread").lower()


def _run_recategorizacao(usuario_id: int, categoria_nome: str, limite: int):
    from usuarios.models import Usuario
    from categorizacao.services.recategorizacao import recategorizar_transacoes

    try:
        usuario = Usuario.objects.get(pk=usuario_id)
        recategorizar_transacoes(
            usuario=usuario,
            categoria_nome=categoria_nome,
            dry_run=False,
            limite=limite,
        )
    except Exception:
        logger.exception("recategorizacao falhou usuario=%s", usuario_id)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=2,
    acks_late=True,
)
def recategorizar_lote_task(self, usuario_id: int, categoria_nome: str = "Diversos", limite: int = 500):
    _run_recategorizacao(usuario_id, categoria_nome, limite)


@shared_task
def agregar_globais_task():
    from categorizacao.services.learning import agregar_contribuicoes_globais
    return agregar_contribuicoes_globais()
