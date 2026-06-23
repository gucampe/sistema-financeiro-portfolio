from __future__ import annotations

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from categorizacao.models import (
    AgregacaoMerchantGlobal,
    EventoCategorizacao,
    MemoriaMerchantUsuario,
    RegraCategorizacao,
)
from categorizacao.services.cache import invalidar_cache_usuario
from categorizacao.services.normalizer import normalizar_padrao_regra, preparar_descricao

K_ANONIMITY = 10


def registrar_evento(
    *,
    usuario,
    acao: str,
    descricao: str = "",
    merchant_key: str = "",
    categoria_sugerida=None,
    categoria_final=None,
    confianca: float | None = None,
    fonte: str = "",
    transacao=None,
    contexto: dict | None = None,
) -> EventoCategorizacao:
    return EventoCategorizacao.objects.create(
        usuario=usuario,
        transacao=transacao,
        descricao_original=(descricao or "")[:255],
        merchant_key=(merchant_key or "")[:120],
        categoria_sugerida=categoria_sugerida,
        categoria_final=categoria_final,
        confianca=confianca,
        fonte=fonte or "",
        acao=acao,
        contexto=contexto or {},
    )


@transaction.atomic
def processar_feedback_transacao(
    *,
    usuario,
    transacao,
    descricao: str,
    categoria_final,
    categoria_sugerida_id: int | None = None,
    confianca: float | None = None,
    fonte: str = "",
    merchant_key: str = "",
    contexto: dict | None = None,
) -> None:
    if not merchant_key:
        _, merchant_key = preparar_descricao(descricao)

    if categoria_sugerida_id and categoria_sugerida_id == categoria_final.pk:
        acao = "aceita"
        _atualizar_memoria(usuario, merchant_key, categoria_final, confirmacao=True)
    elif categoria_sugerida_id:
        acao = "corrigida"
        _atualizar_memoria(usuario, merchant_key, categoria_final, confirmacao=False)
        _talvez_criar_regra_aprendida(usuario, merchant_key, categoria_final)
    else:
        acao = "aceita"
        _atualizar_memoria(usuario, merchant_key, categoria_final, confirmacao=True)

    categoria_sugerida = None
    if categoria_sugerida_id:
        from categorias.models import Categoria

        categoria_sugerida = Categoria.objects.filter(pk=categoria_sugerida_id).first()

    registrar_evento(
        usuario=usuario,
        acao=acao,
        descricao=descricao,
        merchant_key=merchant_key,
        categoria_sugerida=categoria_sugerida,
        categoria_final=categoria_final,
        confianca=confianca,
        fonte=fonte,
        transacao=transacao,
        contexto=contexto,
    )

    prefs = getattr(getattr(usuario, "perfil", None), "categorizacao_contribuir_globais", False)
    if prefs and merchant_key and acao in ("aceita", "corrigida"):
        _contribuir_agregacao_global(merchant_key, categoria_final)


def _atualizar_memoria(usuario, merchant_key: str, categoria, confirmacao: bool) -> None:
    if not merchant_key:
        return
    memoria, _ = MemoriaMerchantUsuario.objects.get_or_create(
        usuario=usuario,
        merchant_key=merchant_key,
        defaults={"categoria": categoria},
    )
    if memoria.categoria_id != categoria.pk:
        memoria.categoria = categoria
        memoria.confirmacoes = 0
        memoria.correcoes = 0
    if confirmacao:
        memoria.confirmacoes = F("confirmacoes") + 1
        memoria.ultima_confirmacao = timezone.now()
    else:
        memoria.correcoes = F("correcoes") + 1
    memoria.save()
    memoria.refresh_from_db()
    memoria.recalcular_score()
    memoria.save(update_fields=["score"])
    invalidar_cache_usuario(usuario.pk)


def _talvez_criar_regra_aprendida(usuario, merchant_key: str, categoria) -> None:
    if not merchant_key:
        return
    correcoes = (
        EventoCategorizacao.objects.filter(
            usuario=usuario,
            merchant_key=merchant_key,
            acao="corrigida",
            categoria_final=categoria,
        ).count()
    )
    if correcoes < 2:
        return
    padrao_norm = normalizar_padrao_regra(merchant_key)
    if RegraCategorizacao.objects.filter(
        usuario=usuario,
        padrao_normalizado=padrao_norm,
        tipo_regra="merchant_exact",
        ativa=True,
    ).exists():
        return
    RegraCategorizacao.objects.create(
        usuario=usuario,
        tipo_regra="merchant_exact",
        padrao=merchant_key,
        padrao_normalizado=padrao_norm,
        categoria=categoria,
        tipo_transacao=categoria.tipo if categoria.tipo in ("receita", "despesa") else None,
        prioridade=50,
        confianca_base=0.92,
        origem="aprendida",
        ativa=True,
    )
    invalidar_cache_usuario(usuario.pk)


def _contribuir_agregacao_global(merchant_key: str, categoria) -> None:
    tipo = categoria.tipo if categoria.tipo in ("receita", "despesa") else "despesa"
    obj, created = AgregacaoMerchantGlobal.objects.get_or_create(
        merchant_key=merchant_key,
        categoria_padrao_nome=categoria.nome,
        tipo=tipo,
        defaults={"ocorrencias": 1, "usuarios_distintos": 1},
    )
    if not created:
        AgregacaoMerchantGlobal.objects.filter(pk=obj.pk).update(
            ocorrencias=F("ocorrencias") + 1,
        )


def agregar_contribuicoes_globais(min_usuarios: int = K_ANONIMITY) -> int:
    """Promove agregações com k-anonymity para regras globais (batch)."""
    from categorias.models import Categoria

    criadas = 0
    agregacoes = AgregacaoMerchantGlobal.objects.filter(
        usuarios_distintos__gte=min_usuarios,
        ocorrencias__gte=min_usuarios,
    )
    for ag in agregacoes:
        cat = Categoria.objects.filter(
            padrao=True,
            nome__iexact=ag.categoria_padrao_nome,
            tipo=ag.tipo,
            ativa=True,
        ).first()
        if not cat:
            continue
        padrao_norm = normalizar_padrao_regra(ag.merchant_key)
        if RegraCategorizacao.objects.filter(
            usuario__isnull=True,
            padrao_normalizado=padrao_norm,
            tipo_regra="merchant_exact",
            ativa=True,
        ).exists():
            continue
        RegraCategorizacao.objects.create(
            usuario=None,
            tipo_regra="merchant_exact",
            padrao=ag.merchant_key,
            padrao_normalizado=padrao_norm,
            categoria=cat,
            tipo_transacao=ag.tipo,
            prioridade=10,
            confianca_base=0.82,
            origem="seed",
            ativa=True,
        )
        criadas += 1
    return criadas
